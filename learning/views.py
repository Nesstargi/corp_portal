from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from catalog.models import Brand, FeatureTag, ProductCategory
from portal.recommendations import build_related_content_for_learning
from .models import LearningMaterial


def learning_list(request):
    selected_brand = request.GET.get("brand", "")
    selected_category = request.GET.get("category", "")
    selected_feature = request.GET.get("feature", "")

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

    return render(
        request,
        "learning/learning_list.html",
        {
            "materials": materials.distinct(),
            "brands": Brand.objects.all(),
            "product_categories": ProductCategory.objects.all(),
            "feature_tags": FeatureTag.objects.all(),
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
