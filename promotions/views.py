from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from portal.recommendations import build_related_content_for_promotion

from .models import Promotion


PROMOTION_TYPE_TABS = (
    ("", "Все акции"),
    ("promo_price", "Промоцена"),
    ("gift", "Подарок"),
)

VALID_PROMOTION_STATUSES = {"", "active", "upcoming"}
VALID_PROMOTION_TYPES = {key for key, _label in PROMOTION_TYPE_TABS}
PROMOTION_STATUS_LABELS = {
    "active": "Активные",
    "upcoming": "Скоро начнутся",
}
PROMOTION_TYPE_LABELS = dict(PROMOTION_TYPE_TABS)


def build_brand_filter_options(queryset):
    grouped_brands = {}

    for raw_brand in queryset.values_list("brand", flat=True):
        brand = raw_brand.strip()
        if not brand:
            continue

        normalized = brand.casefold()
        entry = grouped_brands.setdefault(
            normalized,
            {"labels": {}, "raw_values": []},
        )
        entry["labels"][brand] = entry["labels"].get(brand, 0) + 1
        if raw_brand not in entry["raw_values"]:
            entry["raw_values"].append(raw_brand)

    def label_priority(item):
        label, count = item
        is_mixed_case = not label.islower() and not label.isupper()
        return (
            -count,
            0 if label.istitle() else 1 if is_mixed_case else 2,
            label.casefold(),
            label,
        )

    brand_options = []
    brand_lookup = {}
    for normalized, entry in grouped_brands.items():
        canonical_label = sorted(entry["labels"].items(), key=label_priority)[0][0]
        brand_options.append(canonical_label)
        brand_lookup[normalized] = {
            "label": canonical_label,
            "raw_values": entry["raw_values"],
        }

    brand_options.sort(key=str.casefold)
    return brand_options, brand_lookup


def apply_promo_type_filter(queryset, promo_type):
    if promo_type == "promo_price":
        return queryset.filter(
            Q(promotion_kind=Promotion.KIND_PROMO_PRICE)
            | Q(badge__icontains="промоц")
            | Q(badge__icontains="промо")
            | Q(badge__icontains="скид")
            | Q(summary__icontains="промоц")
            | Q(summary__icontains="промо")
            | Q(summary__icontains="скид")
            | Q(details__icontains="промоц")
            | Q(details__icontains="промо")
            | Q(details__icontains="скид")
        )

    if promo_type == "gift":
        return queryset.filter(
            Q(promotion_kind=Promotion.KIND_GIFT)
            | Q(badge__icontains="подар")
            | Q(summary__icontains="подар")
            | Q(details__icontains="подар")
            | Q(title__icontains="подар")
        )

    if promo_type == "preorder":
        return queryset.filter(
            Q(promotion_kind=Promotion.KIND_PREORDER)
            | Q(badge__icontains="предзаказ")
            | Q(summary__icontains="предзаказ")
            | Q(details__icontains="предзаказ")
            | Q(title__icontains="предзаказ")
        )

    return queryset


def build_promo_type_tabs(request, queryset):
    tabs = []

    for key, label in PROMOTION_TYPE_TABS:
        params = request.GET.copy()
        params.pop("page", None)
        if key:
            params["promo_type"] = key
        else:
            params.pop("promo_type", None)

        query_string = params.urlencode()
        url = f"?{query_string}" if query_string else request.path

        tabs.append(
            {
                "key": key,
                "label": label,
                "count": apply_promo_type_filter(queryset, key).count(),
                "url": url,
            }
        )

    return tabs


def promotion_list(request):
    search_query = request.GET.get("q", "").strip()
    selected_brand = request.GET.get("brand", "").strip()
    selected_status = request.GET.get("status", "").strip()
    selected_promo_type = request.GET.get("promo_type", "").strip()
    if selected_status not in VALID_PROMOTION_STATUSES:
        selected_status = ""
    if selected_promo_type not in VALID_PROMOTION_TYPES:
        selected_promo_type = ""
    today = timezone.localdate()

    filter_source = Promotion.objects.visible_on_site(today)
    brands, brand_lookup = build_brand_filter_options(filter_source)
    selected_brand_entry = brand_lookup.get(selected_brand.casefold())
    if selected_brand and selected_brand_entry:
        selected_brand = selected_brand_entry["label"]
    elif selected_brand:
        selected_brand = ""

    promotions = filter_source.order_by(
        "-is_featured", "sort_order", "title"
    )

    if search_query:
        promotions = promotions.filter(
            Q(title__icontains=search_query)
            | Q(summary__icontains=search_query)
            | Q(details__icontains=search_query)
            | Q(brand__icontains=search_query)
            | Q(category__icontains=search_query)
            | Q(promo_code__icontains=search_query)
        )

    if selected_brand:
        promotions = promotions.filter(
            brand__in=brand_lookup[selected_brand.casefold()]["raw_values"]
        )

    if selected_status == "active":
        promotions = promotions.active_on(today)
    elif selected_status == "upcoming":
        promotions = promotions.upcoming_on(today)

    promotion_type_tabs = build_promo_type_tabs(request, promotions)
    promotions = apply_promo_type_filter(promotions, selected_promo_type)

    paginator = Paginator(promotions, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)

    active_filters = {
        "q": search_query,
        "brand": selected_brand,
        "status": selected_status,
        "promo_type": selected_promo_type,
    }
    active_filter_items = []
    if search_query:
        active_filter_items.append({"label": "Поиск", "value": search_query})
    if selected_brand:
        active_filter_items.append({"label": "Бренд", "value": selected_brand})
    if selected_status:
        active_filter_items.append(
            {
                "label": "Статус",
                "value": PROMOTION_STATUS_LABELS[selected_status],
            }
        )
    if selected_promo_type:
        active_filter_items.append(
            {
                "label": "Тип",
                "value": PROMOTION_TYPE_LABELS[selected_promo_type],
            }
        )

    return render(
        request,
        "promotions/promotion_list.html",
        {
            "promotions": page_obj,
            "page_obj": page_obj,
            "result_count": paginator.count,
            "query_without_page": query_params.urlencode(),
            "active_filters": active_filters,
            "active_filter_items": active_filter_items,
            "has_active_filters": any(active_filters.values()),
            "brands": brands,
            "search_query": search_query,
            "selected_brand": selected_brand,
            "selected_status": selected_status,
            "selected_promo_type": selected_promo_type,
            "promotion_type_tabs": promotion_type_tabs,
        },
    )


def promotion_detail(request, slug):
    promotion = get_object_or_404(
        Promotion.objects.visible_on_site(),
        slug=slug,
    )
    return render(
        request,
        "promotions/promotion_detail.html",
        {
            "promotion": promotion,
            "related_content": build_related_content_for_promotion(promotion),
        },
    )
