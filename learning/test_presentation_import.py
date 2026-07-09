from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZipFile

from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .admin import PresentationImportAdmin
from .models import LearningBlock, PresentationImport
from .presentation_import import extract_pptx_slides


def build_pptx_bytes():
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "ppt/presentation.xml",
            (
                '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                "<p:sldIdLst>"
                '<p:sldId id="256" r:id="rId1"/>'
                '<p:sldId id="257" r:id="rId2"/>'
                '<p:sldId id="258" r:id="rId3"/>'
                "</p:sldIdLst>"
                "</p:presentation>"
            ),
        )
        archive.writestr(
            "ppt/_rels/presentation.xml.rels",
            (
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="slide" Target="slides/slide1.xml"/>'
                '<Relationship Id="rId2" Type="slide" Target="slides/slide2.xml"/>'
                '<Relationship Id="rId3" Type="slide" Target="slides/slide3.xml"/>'
                "</Relationships>"
            ),
        )
        archive.writestr(
            "ppt/slides/slide1.xml",
            build_slide_xml("Первый слайд", "Ключевой тезис", "Деталь для материала"),
        )
        archive.writestr(
            "ppt/slides/slide2.xml",
            build_slide_xml("Второй слайд", "Ещё один тезис"),
        )
        archive.writestr(
            "ppt/slides/slide3.xml",
            build_slide_xml(image_rel_id="rIdImage1"),
        )
        archive.writestr(
            "ppt/slides/_rels/slide3.xml.rels",
            (
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rIdImage1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image1.png"/>'
                "</Relationships>"
            ),
        )
        archive.writestr("ppt/media/image1.png", tiny_png_bytes())
    return buffer.getvalue()


def build_slide_xml(*paragraphs, image_rel_id=""):
    paragraph_xml = "".join(
        f"<a:p><a:r><a:t>{paragraph}</a:t></a:r></a:p>"
        for paragraph in paragraphs
    )
    image_xml = (
        '<p:pic><p:blipFill><a:blip r:embed="'
        f"{image_rel_id}"
        '"/></p:blipFill></p:pic>'
        if image_rel_id
        else ""
    )
    return (
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<p:cSld><p:spTree><p:sp><p:txBody>"
        f"{paragraph_xml}"
        "</p:txBody></p:sp>"
        f"{image_xml}"
        "</p:spTree></p:cSld>"
        "</p:sld>"
    )


def tiny_png_bytes():
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
        b"\x89\x00\x00\x00\nIDATx\x9cc\xf8\xff\xff?\x00\x05"
        b"\xfe\x02\xfeA\x8d\xa3\x15\x00\x00\x00\x00IEND\xaeB`\x82"
    )


class PresentationImportTests(TestCase):
    def test_extract_pptx_slides_reads_text_in_slide_order(self):
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "source.pptx"
            file_path.write_bytes(build_pptx_bytes())

            slides = extract_pptx_slides(file_path)

        self.assertEqual(
            [slide.title for slide in slides],
            ["Первый слайд", "Второй слайд", "Слайд 3"],
        )
        self.assertEqual(slides[0].paragraphs, ["Ключевой тезис", "Деталь для материала"])
        self.assertEqual(slides[2].images[0].filename, "image1.png")

    def test_admin_import_creates_learning_material_with_slide_blocks(self):
        with TemporaryDirectory() as temp_dir:
            with override_settings(MEDIA_ROOT=temp_dir):
                presentation_import = PresentationImport.objects.create(
                    title="Материал из презентации",
                    presentation=SimpleUploadedFile(
                        "demo.pptx",
                        build_pptx_bytes(),
                        content_type=(
                            "application/vnd.openxmlformats-officedocument."
                            "presentationml.presentation"
                        ),
                    ),
                )

                model_admin = PresentationImportAdmin(PresentationImport, admin.site)
                model_admin._create_material_from_presentation(presentation_import)

                presentation_import.refresh_from_db()
                material = presentation_import.material

                self.assertEqual(material.title, "Материал из презентации")
                self.assertFalse(material.is_published)
                self.assertIn("Ключевой тезис", material.summary)
                self.assertEqual(LearningBlock.objects.filter(material=material).count(), 3)
                self.assertTrue(
                    LearningBlock.objects.filter(
                        material=material,
                        title="Первый слайд",
                        text__contains="Деталь для материала",
                    ).exists()
                )
                self.assertTrue(
                    LearningBlock.objects.filter(
                        material=material,
                        block_type="image",
                        gallery_images__image__contains="slide-3-1-image1.png",
                    ).exists()
                )

    def test_admin_import_preview_report_describes_slides_without_material(self):
        with TemporaryDirectory() as temp_dir:
            with override_settings(MEDIA_ROOT=temp_dir):
                presentation_import = PresentationImport.objects.create(
                    title="Материал для предпросмотра",
                    presentation=SimpleUploadedFile(
                        "demo.pptx",
                        build_pptx_bytes(),
                        content_type=(
                            "application/vnd.openxmlformats-officedocument."
                            "presentationml.presentation"
                        ),
                    ),
                )

                model_admin = PresentationImportAdmin(PresentationImport, admin.site)
                slides = model_admin._extract_slides(presentation_import)
                report = model_admin._build_import_preview_report(presentation_import, slides)

                self.assertIsNone(presentation_import.material)
                self.assertIn("Предварительный разбор презентации", report)
                self.assertIn("Слайдов с содержимым: 3", report)
                self.assertIn("Слайд 1: Первый слайд", report)
                self.assertIn("Изображений: 1", report)

    def test_admin_import_adds_ocr_text_block_when_enabled(self):
        with TemporaryDirectory() as temp_dir:
            with override_settings(
                MEDIA_ROOT=temp_dir,
                PRESENTATION_OCR_ENABLED=True,
                PRESENTATION_OCR_LANGUAGES="rus+eng",
                PRESENTATION_OCR_TIMEOUT=20,
            ):
                presentation_import = PresentationImport.objects.create(
                    title="Материал с OCR",
                    presentation=SimpleUploadedFile(
                        "demo.pptx",
                        build_pptx_bytes(),
                        content_type=(
                            "application/vnd.openxmlformats-officedocument."
                            "presentationml.presentation"
                        ),
                    ),
                )

                model_admin = PresentationImportAdmin(PresentationImport, admin.site)
                with patch(
                    "learning.presentation_import._recognize_image_text",
                    return_value="Распознанный текст с картинки",
                ):
                    model_admin._create_material_from_presentation(presentation_import)

                presentation_import.refresh_from_db()
                material = presentation_import.material

                self.assertTrue(
                    LearningBlock.objects.filter(
                        material=material,
                        title__contains="текст с изображений",
                        text__contains="Распознанный текст с картинки",
                    ).exists()
                )
                self.assertIn("Слайдов с распознанным текстом: 1", presentation_import.import_report)
