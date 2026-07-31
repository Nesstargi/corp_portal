from django.db.models import Q
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.html import strip_tags
from django.utils.text import Truncator

from learning.models import LearningMaterial
from news.models import News
from promotions.models import Promotion


def _truncate_summary(value, limit=160):
    cleaned = strip_tags(value or "").strip()
    if not cleaned:
        return ""
    return Truncator(cleaned).chars(limit)


def _combine_queries(queries):
    filtered_queries = [query for query in queries if query is not None]
    if not filtered_queries:
        return None

    combined = filtered_queries[0]
    for query in filtered_queries[1:]:
        combined |= query
    return combined


def _build_m2m_query(field_name, values):
    values = [value for value in values if value]
    if not values:
        return None
    return Q(**{f"{field_name}__in": values})


def _build_ci_string_query(field_name, values):
    queries = [
        Q(**{f"{field_name}__iexact": value.strip()})
        for value in values
        if value is not None and str(value).strip()
    ]
    return _combine_queries(queries)


def _serialize_news(item):
    meta_parts = [item.get_category_display()]
    if item.created_at:
        meta_parts.append(date_format(timezone.localtime(item.created_at), "d.m.Y"))

    return {
        "kind": "news",
        "label": "Новость",
        "title": item.title,
        "url": item.get_absolute_url(),
        "meta": " · ".join(part for part in meta_parts if part),
        "summary": _truncate_summary(item.summary or item.content),
    }


def _serialize_learning(item):
    return {
        "kind": "learning",
        "label": "База знаний",
        "title": item.title,
        "url": item.get_absolute_url(),
        "meta": item.get_material_type_display(),
        "summary": _truncate_summary(
            item.summary
            or item.product_short_summary
            or item.product_full_description
            or item.content
        ),
    }


def _serialize_promotion(item):
    meta_parts = [part for part in [item.brand, item.category] if part]
    if not meta_parts and item.formatted_active_period:
        meta_parts.append(item.formatted_active_period)

    return {
        "kind": "promotion",
        "label": "Акция",
        "title": item.title,
        "url": item.get_absolute_url(),
        "meta": " · ".join(meta_parts),
        "summary": _truncate_summary(
            item.benefit_summary or item.card_summary or item.summary or item.details
        ),
    }


def _get_related_news(*, brand_ids=None, category_ids=None, feature_tag_ids=None, exclude_pk=None, limit=1):
    query = _combine_queries(
        [
            _build_m2m_query("brands", brand_ids or []),
            _build_m2m_query("product_categories", category_ids or []),
            _build_m2m_query("feature_tags", feature_tag_ids or []),
        ]
    )
    if query is None:
        return []

    return list(
        News.objects.filter(is_published=True)
        .exclude(pk=exclude_pk)
        .filter(query)
        .distinct()
        .order_by("-created_at")[:limit]
    )


def _get_related_learning(
    *,
    brand_ids=None,
    category_ids=None,
    area_ids=None,
    feature_tag_ids=None,
    exclude_pk=None,
    limit=1,
):
    query = _combine_queries(
        [
            _build_m2m_query("brands", brand_ids or []),
            _build_m2m_query("categories", category_ids or []),
            _build_m2m_query("areas", area_ids or []),
            _build_m2m_query("feature_tags", feature_tag_ids or []),
        ]
    )
    if query is None:
        return []

    return list(
        LearningMaterial.objects.filter(is_published=True)
        .exclude(pk=exclude_pk)
        .filter(query)
        .distinct()
        .order_by("-created_at", "title")[:limit]
    )


def _get_related_promotions(*, brand_names=None, category_names=None, exclude_pk=None, limit=1):
    query = _combine_queries(
        [
            _build_ci_string_query("brand", brand_names or []),
            _build_ci_string_query("category", category_names or []),
        ]
    )
    if query is None:
        return []

    return list(
        Promotion.objects.visible_on_site()
        .exclude(pk=exclude_pk)
        .filter(query)
        .order_by("-is_featured", "sort_order", "title")[:limit]
    )


def build_related_content_for_news(news):
    brand_ids = list(news.brands.values_list("id", flat=True))
    category_ids = list(news.product_categories.values_list("id", flat=True))
    feature_tag_ids = list(news.feature_tags.values_list("id", flat=True))
    brand_names = list(news.brands.values_list("name", flat=True))
    category_names = list(news.product_categories.values_list("name", flat=True))

    related_items = []
    related_items.extend(
        _serialize_learning(item)
        for item in _get_related_learning(
            brand_ids=brand_ids,
            category_ids=category_ids,
            feature_tag_ids=feature_tag_ids,
            limit=2,
        )
    )
    related_items.extend(
        _serialize_promotion(item)
        for item in _get_related_promotions(
            brand_names=brand_names,
            category_names=category_names,
            limit=1,
        )
    )
    related_items.extend(
        _serialize_news(item)
        for item in _get_related_news(
            brand_ids=brand_ids,
            category_ids=category_ids,
            feature_tag_ids=feature_tag_ids,
            exclude_pk=news.pk,
            limit=1,
        )
    )
    return related_items


def build_related_content_for_learning(material):
    brand_ids = list(material.brands.values_list("id", flat=True))
    category_ids = list(material.categories.values_list("id", flat=True))
    area_ids = list(material.areas.values_list("id", flat=True))
    feature_tag_ids = list(material.feature_tags.values_list("id", flat=True))
    brand_names = list(material.brands.values_list("name", flat=True))
    category_names = list(material.categories.values_list("name", flat=True))

    related_items = []
    related_items.extend(
        _serialize_learning(item)
        for item in _get_related_learning(
            brand_ids=brand_ids,
            category_ids=category_ids,
            area_ids=area_ids,
            feature_tag_ids=feature_tag_ids,
            exclude_pk=material.pk,
            limit=2,
        )
    )
    related_items.extend(
        _serialize_news(item)
        for item in _get_related_news(
            brand_ids=brand_ids,
            category_ids=category_ids,
            feature_tag_ids=feature_tag_ids,
            limit=1,
        )
    )
    related_items.extend(
        _serialize_promotion(item)
        for item in _get_related_promotions(
            brand_names=brand_names,
            category_names=category_names,
            limit=1,
        )
    )
    return related_items


def build_related_content_for_promotion(promotion):
    brand_names = [promotion.brand]
    category_names = [promotion.category]

    if brand_names[0] or category_names[0]:
        related_news_query = _combine_queries(
            [
                _build_ci_string_query("brands__name", brand_names),
                _build_ci_string_query("product_categories__name", category_names),
            ]
        )
        related_learning_query = _combine_queries(
            [
                _build_ci_string_query("brands__name", brand_names),
                _build_ci_string_query("categories__name", category_names),
            ]
        )
        related_news = (
            list(
                News.objects.filter(is_published=True)
                .filter(related_news_query)
                .distinct()
                .order_by("-created_at")[:1]
            )
            if related_news_query is not None
            else []
        )
        related_learning = (
            list(
                LearningMaterial.objects.filter(is_published=True)
                .filter(related_learning_query)
                .distinct()
                .order_by("-created_at", "title")[:1]
            )
            if related_learning_query is not None
            else []
        )
    else:
        related_news = []
        related_learning = []

    related_items = []
    related_items.extend(
        _serialize_promotion(item)
        for item in _get_related_promotions(
            brand_names=brand_names,
            category_names=category_names,
            exclude_pk=promotion.pk,
            limit=2,
        )
    )
    related_items.extend(_serialize_learning(item) for item in related_learning)
    related_items.extend(_serialize_news(item) for item in related_news)
    return related_items
