from dataclasses import dataclass
from html import escape
import posixpath
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree


PRESENTATION_NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


@dataclass
class SlideImage:
    filename: str
    content: bytes
    ocr_text: str = ""


@dataclass
class SlideContent:
    number: int
    title: str
    paragraphs: list[str]
    images: list[SlideImage]
    ocr_paragraphs: list[str]


class PresentationImportError(ValueError):
    pass


def _natural_slide_sort_key(path):
    match = re.search(r"slide(\d+)\.xml$", path)
    return int(match.group(1)) if match else 0


def _collapse_spaces(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_text_key(value):
    return _collapse_spaces(value).casefold()


def _read_xml(zip_file, path):
    try:
        return ElementTree.fromstring(zip_file.read(path))
    except KeyError:
        return None
    except ElementTree.ParseError:
        return None


def _ordered_slide_paths(zip_file):
    presentation = _read_xml(zip_file, "ppt/presentation.xml")
    rels = _read_xml(zip_file, "ppt/_rels/presentation.xml.rels")

    if presentation is not None and rels is not None:
        rel_map = {
            rel.attrib.get("Id"): rel.attrib.get("Target", "")
            for rel in rels.findall("rel:Relationship", PRESENTATION_NS)
        }
        paths = []
        for slide_id in presentation.findall(".//p:sldId", PRESENTATION_NS):
            rel_id = slide_id.attrib.get(f"{{{PRESENTATION_NS['r']}}}id")
            target = rel_map.get(rel_id, "")
            if not target:
                continue

            slide_path = PurePosixPath("ppt") / target
            normalized_path = str(slide_path)
            if normalized_path in zip_file.namelist():
                paths.append(normalized_path)

        if paths:
            return paths

    return sorted(
        (
            name
            for name in zip_file.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        ),
        key=_natural_slide_sort_key,
    )


def _extract_slide_paragraphs(slide_xml):
    paragraphs = []

    for paragraph in slide_xml.findall(".//a:p", PRESENTATION_NS):
        parts = [
            text_node.text or ""
            for text_node in paragraph.findall(".//a:t", PRESENTATION_NS)
        ]
        text = _collapse_spaces(" ".join(parts))
        if text:
            paragraphs.append(text)

    cleaned = []
    seen = set()
    for paragraph in paragraphs:
        key = paragraph.casefold()
        if key in seen:
            continue
        cleaned.append(paragraph)
        seen.add(key)

    return cleaned


def _slide_relationship_path(slide_path):
    slide_name = PurePosixPath(slide_path).name
    return f"ppt/slides/_rels/{slide_name}.rels"


def _resolve_slide_target(slide_path, target):
    base_dir = PurePosixPath(slide_path).parent
    return posixpath.normpath(str(base_dir / target))


def _extract_slide_image_rel_ids(slide_xml):
    rel_ids = []
    seen = set()

    for image_node in slide_xml.findall(".//a:blip", PRESENTATION_NS):
        rel_id = (
            image_node.attrib.get(f"{{{PRESENTATION_NS['r']}}}embed")
            or image_node.attrib.get(f"{{{PRESENTATION_NS['r']}}}link")
        )
        if not rel_id or rel_id in seen:
            continue
        rel_ids.append(rel_id)
        seen.add(rel_id)

    return rel_ids


def _resolve_tesseract_command(tesseract_cmd=""):
    candidates = [
        tesseract_cmd,
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)

    return ""


def _recognize_image_text(
    image,
    *,
    languages="rus+eng",
    timeout=20,
    tesseract_cmd="",
    tessdata_dir="",
):
    resolved_tesseract = _resolve_tesseract_command(tesseract_cmd)
    if not resolved_tesseract:
        return ""

    with TemporaryDirectory() as temp_dir:
        image_path = Path(temp_dir) / image.filename
        with image_path.open("wb") as image_file:
            image_file.write(image.content)

        command = [resolved_tesseract, str(image_path), "stdout"]
        if tessdata_dir:
            command.extend(["--tessdata-dir", tessdata_dir])
        if languages:
            command.extend(["-l", languages])

        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""

    if result.returncode != 0:
        return ""

    return (result.stdout or "").strip()


def _split_ocr_text(value):
    lines = [
        _collapse_spaces(line)
        for line in str(value or "").splitlines()
        if _collapse_spaces(line)
    ]
    if lines:
        return lines

    collapsed = _collapse_spaces(value)
    return [collapsed] if collapsed else []


def _extract_slide_images(
    zip_file,
    slide_path,
    slide_xml,
    *,
    enable_ocr=False,
    ocr_languages="rus+eng",
    ocr_timeout=20,
    ocr_tesseract_cmd="",
    ocr_tessdata_dir="",
):
    rel_path = _slide_relationship_path(slide_path)
    rels = _read_xml(zip_file, rel_path)
    if rels is None:
        return []

    image_relationships = {}
    for relationship in rels.findall("rel:Relationship", PRESENTATION_NS):
        relationship_type = relationship.attrib.get("Type", "")
        if "image" not in relationship_type:
            continue

        rel_id = relationship.attrib.get("Id", "")
        target = relationship.attrib.get("Target", "")
        if not rel_id or not target:
            continue

        image_relationships[rel_id] = _resolve_slide_target(slide_path, target)

    if not image_relationships:
        return []

    ordered_rel_ids = _extract_slide_image_rel_ids(slide_xml)
    if not ordered_rel_ids:
        ordered_rel_ids = list(image_relationships.keys())

    images = []
    seen_paths = set()
    for rel_id in ordered_rel_ids:
        image_path = image_relationships.get(rel_id)
        if not image_path or image_path in seen_paths:
            continue

        try:
            content = zip_file.read(image_path)
        except KeyError:
            continue

        image = SlideImage(
            filename=PurePosixPath(image_path).name,
            content=content,
        )
        if enable_ocr:
            image.ocr_text = _recognize_image_text(
                image,
                languages=ocr_languages,
                timeout=ocr_timeout,
                tesseract_cmd=ocr_tesseract_cmd,
                tessdata_dir=ocr_tessdata_dir,
            )
        images.append(image)
        seen_paths.add(image_path)

    return images


def extract_pptx_slides(
    file_path,
    *,
    enable_ocr=False,
    ocr_languages="rus+eng",
    ocr_timeout=20,
    ocr_tesseract_cmd="",
    ocr_tessdata_dir="",
):
    try:
        with ZipFile(file_path) as zip_file:
            slide_paths = _ordered_slide_paths(zip_file)
            slides = []

            for index, slide_path in enumerate(slide_paths, start=1):
                slide_xml = _read_xml(zip_file, slide_path)
                if slide_xml is None:
                    continue

                paragraphs = _extract_slide_paragraphs(slide_xml)
                images = _extract_slide_images(
                    zip_file,
                    slide_path,
                    slide_xml,
                    enable_ocr=enable_ocr,
                    ocr_languages=ocr_languages,
                    ocr_timeout=ocr_timeout,
                    ocr_tesseract_cmd=ocr_tesseract_cmd,
                    ocr_tessdata_dir=ocr_tessdata_dir,
                )
                if not paragraphs and not images:
                    continue

                existing_text_keys = {
                    _normalize_text_key(paragraph) for paragraph in paragraphs
                }
                ocr_paragraphs = []
                for image in images:
                    for paragraph in _split_ocr_text(image.ocr_text):
                        key = _normalize_text_key(paragraph)
                        if not key or key in existing_text_keys:
                            continue
                        ocr_paragraphs.append(paragraph)
                        existing_text_keys.add(key)

                title = (paragraphs[0] if paragraphs else f"Слайд {index}")[:200]
                body = paragraphs[1:] if len(paragraphs) > 1 else paragraphs[:1]
                slides.append(
                    SlideContent(
                        number=index,
                        title=title or f"Слайд {index}",
                        paragraphs=body,
                        images=images,
                        ocr_paragraphs=ocr_paragraphs,
                    )
                )
    except (BadZipFile, OSError) as exc:
        raise PresentationImportError(
            "Не удалось прочитать презентацию. Загрузите файл .pptx."
        ) from exc

    if not slides:
        raise PresentationImportError(
        "В презентации не найдено содержимое для создания материала."
        )

    return slides


def build_slide_html(slide):
    return "\n".join(f"<p>{escape(paragraph)}</p>" for paragraph in slide.paragraphs)


def build_ocr_html(slide):
    return "\n".join(f"<p>{escape(paragraph)}</p>" for paragraph in slide.ocr_paragraphs)


def build_summary(slides):
    for slide in slides:
        for paragraph in [*slide.paragraphs, *slide.ocr_paragraphs]:
            if paragraph and paragraph != slide.title:
                return paragraph[:300]
    return slides[0].title[:300]
