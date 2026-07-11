from django.db.models import Prefetch
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from catalog.models import Brand, FeatureTag, ProductCategory
from portal.recommendations import build_related_content_for_learning
from .models import LearningMaterial


def learning_list(request):
    selected_brand = request.GET.get("brand", "").strip()
    selected_category = request.GET.get("category", "").strip()
    selected_feature = request.GET.get("feature", "").strip()

    brands = (
        Brand.objects.filter(learning_materials__is_published=True)
        .distinct()
        .order_by("name")
    )
    product_categories = (
        ProductCategory.objects.filter(learning_materials__is_published=True)
        .distinct()
        .order_by("name")
    )
    feature_tags = (
        FeatureTag.objects.filter(learning_materials__is_published=True)
        .distinct()
        .order_by("name")
    )

    if selected_brand and not brands.filter(slug=selected_brand).exists():
        selected_brand = ""
    if selected_category and not product_categories.filter(slug=selected_category).exists():
        selected_category = ""
    if selected_feature and not feature_tags.filter(slug=selected_feature).exists():
        selected_feature = ""

    materials = (
        LearningMaterial.objects.filter(is_published=True)
        .prefetch_related(
            "brands",
            "categories",
            "feature_tags",
            "blocks__gallery_images",
        )
        .order_by("title")
    )

    if selected_brand:
        materials = materials.filter(brands__slug=selected_brand)
    if selected_category:
        materials = materials.filter(categories__slug=selected_category)
    if selected_feature:
        materials = materials.filter(feature_tags__slug=selected_feature)

    paginator = Paginator(materials.distinct(), 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)

    active_filters = {
        "brand": selected_brand,
        "category": selected_category,
        "feature": selected_feature,
    }
    active_filter_items = []
    if selected_brand:
        active_filter_items.append(
            {"label": "Бренд", "value": brands.get(slug=selected_brand).name}
        )
    if selected_category:
        active_filter_items.append(
            {
                "label": "Категория",
                "value": product_categories.get(slug=selected_category).name,
            }
        )
    if selected_feature:
        active_filter_items.append(
            {"label": "Фишка", "value": feature_tags.get(slug=selected_feature).name}
        )

    return render(
        request,
        "learning/learning_list.html",
        {
            "materials": page_obj,
            "page_obj": page_obj,
            "result_count": paginator.count,
            "query_without_page": query_params.urlencode(),
            "active_filters": active_filters,
            "active_filter_items": active_filter_items,
            "has_active_filters": any(active_filters.values()),
            "brands": brands,
            "product_categories": product_categories,
            "feature_tags": feature_tags,
            "selected_brand": selected_brand,
            "selected_category": selected_category,
            "selected_feature": selected_feature,
        },
    )


def learning_compare(request):
    raise Http404("Сравнение товаров временно отключено.")


def learning_detail(request, pk):
    material = get_object_or_404(
        LearningMaterial.objects.prefetch_related(
            "brands",
            "categories",
            "areas",
            "feature_tags",
            "blocks__gallery_images",
            "product_description_images",
            "product_review_images",
            "product_features",
            "product_sales_scripts",
            "product_specifications",
        ),
        pk=pk,
        is_published=True,
    )
    return render(
        request,
        "learning/learning_detail.html",
        {
            "material": material,
            "related_content": build_related_content_for_learning(material),
        },
    )
