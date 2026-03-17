from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Promotion


PROMOTION_TYPE_TABS = (
    ("", "Все акции"),
    ("promo_price", "Промоцена"),
    ("gift", "Подарок"),
    ("preorder", "Предзаказы"),
)


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
    selected_category = request.GET.get("category", "").strip()
    selected_status = request.GET.get("status", "").strip()
    selected_promo_type = request.GET.get("promo_type", "").strip()

    promotions = Promotion.objects.filter(is_published=True).order_by(
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
        promotions = promotions.filter(brand__iexact=selected_brand)

    if selected_category:
        promotions = promotions.filter(category__iexact=selected_category)

    today = timezone.localdate()
    if selected_status == "active":
        promotions = promotions.filter(
            Q(start_date__isnull=True) | Q(start_date__lte=today),
            Q(end_date__isnull=True) | Q(end_date__gte=today),
        )
    elif selected_status == "upcoming":
        promotions = promotions.filter(start_date__gt=today)
    elif selected_status == "finished":
        promotions = promotions.filter(end_date__lt=today)

    promotion_type_tabs = build_promo_type_tabs(request, promotions)
    promotions = apply_promo_type_filter(promotions, selected_promo_type)

    brands = (
        Promotion.objects.exclude(brand="")
        .order_by("brand")
        .values_list("brand", flat=True)
        .distinct()
    )
    categories = (
        Promotion.objects.exclude(category="")
        .order_by("category")
        .values_list("category", flat=True)
        .distinct()
    )

    return render(
        request,
        "promotions/promotion_list.html",
        {
            "promotions": promotions,
            "brands": brands,
            "categories": categories,
            "search_query": search_query,
            "selected_brand": selected_brand,
            "selected_category": selected_category,
            "selected_status": selected_status,
            "selected_promo_type": selected_promo_type,
            "promotion_type_tabs": promotion_type_tabs,
        },
    )


def promotion_detail(request, slug):
    promotion = get_object_or_404(Promotion, slug=slug, is_published=True)
    return render(
        request,
        "promotions/promotion_detail.html",
        {"promotion": promotion},
    )
