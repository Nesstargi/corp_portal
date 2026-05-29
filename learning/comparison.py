from collections import OrderedDict
import re

from django.utils.html import strip_tags
from django.utils.text import Truncator

from .models import LearningMaterial


PRODUCT_MATERIAL_TYPE = "product"
TOKEN_RE = re.compile(r"[0-9a-zа-яё]+", re.IGNORECASE)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
SPACE_RE = re.compile(r"\s+")


def get_product_compare_queryset():
    return LearningMaterial.objects.filter(
        is_published=True,
        material_type=PRODUCT_MATERIAL_TYPE,
    ).prefetch_related(
        "brands",
        "blocks__gallery_images",
        "categories",
        "feature_tags",
        "product_features",
        "product_specifications",
    )


def clean_compare_text(value):
    cleaned = strip_tags(value or "").replace("\xa0", " ")
    return SPACE_RE.sub(" ", cleaned).strip()


def build_lookup_key(value):
    return " ".join(TOKEN_RE.findall(clean_compare_text(value).casefold()))


def summarize_compare_text(value, limit=170):
    cleaned = clean_compare_text(value)
    if not cleaned:
        return ""

    parts = SENTENCE_RE.split(cleaned, maxsplit=1)
    first_part = parts[0] if parts else cleaned
    return Truncator(first_part).chars(limit)


def score_product_match(query_key, title_key):
    if not query_key or not title_key:
        return 0
    if query_key == title_key:
        return 1000
    if title_key.startswith(query_key):
        return 900
    if query_key in title_key:
        return 800

    query_tokens = set(query_key.split())
    title_tokens = set(title_key.split())
    shared_tokens = query_tokens & title_tokens

    if not shared_tokens:
        return 0

    score = len(shared_tokens) * 120
    if query_tokens and query_tokens.issubset(title_tokens):
        score += 80
    score += int(100 * len(shared_tokens) / len(query_tokens))
    return score


def resolve_product_material(query, products):
    query_key = build_lookup_key(query)
    if not query_key:
        return None

    scored = sorted(
        (
            (score_product_match(query_key, build_lookup_key(product.title)), product)
            for product in products
        ),
        key=lambda item: (-item[0], len(item[1].title), item[1].title.casefold()),
    )
    if not scored or scored[0][0] <= 0:
        return None
    return scored[0][1]


def suggest_product_titles(query, products, limit=5):
    query_key = build_lookup_key(query)
    if not query_key:
        return []

    scored = sorted(
        (
            (score_product_match(query_key, build_lookup_key(product.title)), product.title)
            for product in products
        ),
        key=lambda item: (-item[0], len(item[1]), item[1].casefold()),
    )
    return [title for score, title in scored if score > 0][:limit]


def build_block_summary(material):
    for block in material.blocks.all():
        if block.block_type not in {"text", "feature", "quote"}:
            continue

        summary_source = block.text or block.caption
        if not summary_source and block.block_type == "feature":
            for item in block.structured_items:
                summary_source = item.get("description") or item.get("pitch")
                if summary_source:
                    break

        summary = summarize_compare_text(summary_source, limit=220)
        if summary:
            return summary

    return ""


def build_product_card(material):
    return {
        "material": material,
        "summary": summarize_compare_text(
            material.product_short_summary
            or material.summary
            or material.product_full_description
            or material.content
            or build_block_summary(material),
            limit=220,
        ),
        "brands": list(material.brands.all()),
        "categories": list(material.categories.all()),
        "feature_tags": list(material.feature_tags.all()),
    }


def build_row_status(has_left, has_right):
    if has_left and has_right:
        return "different"
    if has_left:
        return "left-only"
    return "right-only"


def build_spec_map(material):
    spec_map = OrderedDict()

    for spec in material.product_specifications.all():
        key = build_lookup_key(spec.name)
        if not key:
            continue

        value = clean_compare_text(spec.value)
        if not value:
            continue

        entry = spec_map.setdefault(
            key,
            {
                "name": clean_compare_text(spec.name) or spec.name,
                "values": [],
            },
        )
        if value not in entry["values"]:
            entry["values"].append(value)

    for block in material.blocks.all():
        if block.block_type != "specification":
            continue

        structured_items = block.structured_items
        if structured_items:
            for item in structured_items:
                name = clean_compare_text(item.get("name"))
                value = clean_compare_text(item.get("value"))
                key = build_lookup_key(name)

                if not key or not value:
                    continue

                entry = spec_map.setdefault(
                    key,
                    {
                        "name": name or item.get("name") or block.title,
                        "values": [],
                    },
                )
                if value not in entry["values"]:
                    entry["values"].append(value)
            continue

        name = clean_compare_text(block.title)
        value = clean_compare_text(block.caption or block.text)
        key = build_lookup_key(name)

        if not key or not value:
            continue

        entry = spec_map.setdefault(
            key,
            {
                "name": name or block.title,
                "values": [],
            },
        )
        if value not in entry["values"]:
            entry["values"].append(value)

    for item in spec_map.values():
        item["value"] = "; ".join(item["values"])

    return spec_map


def build_feature_summary(description, client_pitch):
    description_summary = summarize_compare_text(description, limit=150)
    pitch_summary = summarize_compare_text(client_pitch, limit=120)

    if description_summary and pitch_summary:
        return f"{description_summary} В продаже: {pitch_summary}"
    if description_summary:
        return description_summary
    if pitch_summary:
        return f"В продаже: {pitch_summary}"
    return "Фишка добавлена в карточку без пояснения."


def build_feature_map(material):
    feature_map = OrderedDict()

    for feature in material.product_features.all():
        key = build_lookup_key(feature.title)
        if not key:
            continue

        summary = build_feature_summary(feature.description, feature.client_pitch)
        entry = feature_map.setdefault(
            key,
            {
                "title": clean_compare_text(feature.title) or feature.title,
                "notes": [],
            },
        )
        if summary and summary not in entry["notes"]:
            entry["notes"].append(summary)

    for block in material.blocks.all():
        if block.block_type != "feature":
            continue

        structured_items = block.structured_items
        if structured_items:
            for item in structured_items:
                title = clean_compare_text(item.get("title")) or "Фишка"
                key = build_lookup_key(title)
                if not key:
                    continue

                summary = build_feature_summary(item.get("description"), item.get("pitch"))
                entry = feature_map.setdefault(
                    key,
                    {
                        "title": title,
                        "notes": [],
                    },
                )
                if summary and summary not in entry["notes"]:
                    entry["notes"].append(summary)
            continue

        title = clean_compare_text(block.title) or "Фишка"
        key = build_lookup_key(title)
        if not key:
            continue

        summary = build_feature_summary(block.text, block.caption)
        entry = feature_map.setdefault(
            key,
            {
                "title": title,
                "notes": [],
            },
        )
        if summary and summary not in entry["notes"]:
            entry["notes"].append(summary)

    if not feature_map:
        for tag in material.feature_tags.all():
            key = build_lookup_key(tag.name)
            if not key:
                continue

            feature_map[key] = {
                "title": tag.name,
                "notes": ["Отмечено в карточке товара как важная фишка или метка."],
            }

    for item in feature_map.values():
        item["summary"] = Truncator(" ".join(item["notes"])).chars(240)

    return feature_map


def build_spec_rows(left_product, right_product):
    left_specs = build_spec_map(left_product)
    right_specs = build_spec_map(right_product)
    ordered_keys = list(left_specs.keys()) + [
        key for key in right_specs.keys() if key not in left_specs
    ]

    rows = []
    same_count = 0

    for key in ordered_keys:
        left_spec = left_specs.get(key)
        right_spec = right_specs.get(key)

        left_value = left_spec["value"] if left_spec else ""
        right_value = right_spec["value"] if right_spec else ""

        if left_spec and right_spec and left_value == right_value:
            same_count += 1
            continue

        rows.append(
            {
                "name": (left_spec or right_spec)["name"],
                "left": left_value,
                "right": right_value,
                "status": build_row_status(bool(left_value), bool(right_value)),
            }
        )

    return rows, same_count


def build_feature_rows(left_product, right_product):
    left_features = build_feature_map(left_product)
    right_features = build_feature_map(right_product)
    ordered_keys = list(left_features.keys()) + [
        key for key in right_features.keys() if key not in left_features
    ]

    rows = []
    same_count = 0

    for key in ordered_keys:
        left_feature = left_features.get(key)
        right_feature = right_features.get(key)

        left_value = left_feature["summary"] if left_feature else ""
        right_value = right_feature["summary"] if right_feature else ""

        if left_feature and right_feature and left_value == right_value:
            same_count += 1
            continue

        rows.append(
            {
                "name": (left_feature or right_feature)["title"],
                "left": left_value,
                "right": right_value,
                "status": build_row_status(bool(left_value), bool(right_value)),
            }
        )

    return rows, same_count


def build_side_highlights(comparison, side):
    other_side = "right" if side == "left" else "left"
    highlights = []
    used_names = set()

    for row in comparison["feature_rows"]:
        side_value = row[side]
        if not side_value:
            continue

        name_key = row["name"].casefold()
        if name_key in used_names:
            continue

        highlights.append(
            {
                "title": row["name"],
                "detail": side_value,
                "kind": "feature",
            }
        )
        used_names.add(name_key)

        if len(highlights) >= 3:
            return highlights

    for row in comparison["spec_rows"]:
        side_value = row[side]
        if not side_value:
            continue

        name_key = row["name"].casefold()
        if name_key in used_names:
            continue

        if row[other_side]:
            detail = f"{side_value} против {row[other_side]}"
        else:
            detail = f"{side_value}; у другой модели этого пункта нет в карточке"

        highlights.append(
            {
                "title": row["name"],
                "detail": detail,
                "kind": "spec",
            }
        )
        used_names.add(name_key)

        if len(highlights) >= 4:
            return highlights

    summary = comparison[side]["summary"]
    if not highlights and summary:
        highlights.append(
            {
                "title": "Общий акцент",
                "detail": summary,
                "kind": "summary",
            }
        )

    return highlights


def build_product_comparison(left_product, right_product):
    spec_rows, same_spec_count = build_spec_rows(left_product, right_product)
    feature_rows, same_feature_count = build_feature_rows(left_product, right_product)

    comparison = {
        "left": build_product_card(left_product),
        "right": build_product_card(right_product),
        "spec_rows": spec_rows,
        "same_spec_count": same_spec_count,
        "feature_rows": feature_rows,
        "same_feature_count": same_feature_count,
    }
    comparison["left_highlights"] = build_side_highlights(comparison, "left")
    comparison["right_highlights"] = build_side_highlights(comparison, "right")
    return comparison
