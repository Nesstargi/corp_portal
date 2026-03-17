from django.shortcuts import get_object_or_404, render

from catalog.models import Brand, KnowledgeArea, ProductCategory

from .models import LearningMaterial


def learning_list(request):
    selected_brand = request.GET.get("brand", "")
    selected_category = request.GET.get("category", "")
    selected_area = request.GET.get("area", "")
    selected_type = request.GET.get("type", "")

    materials = (
        LearningMaterial.objects.filter(is_published=True)
        .prefetch_related("brands", "categories", "areas", "feature_tags", "blocks")
        .order_by("title")
    )

    if selected_brand:
        materials = materials.filter(brands__slug=selected_brand)
    if selected_category:
        materials = materials.filter(categories__slug=selected_category)
    if selected_area:
        materials = materials.filter(areas__slug=selected_area)
    if selected_type:
        materials = materials.filter(material_type=selected_type)

    return render(
        request,
        "learning/learning_list.html",
        {
            "materials": materials.distinct(),
            "brands": Brand.objects.all(),
            "product_categories": ProductCategory.objects.all(),
            "knowledge_areas": KnowledgeArea.objects.all(),
            "material_types": LearningMaterial.MATERIAL_TYPE_CHOICES,
            "selected_brand": selected_brand,
            "selected_category": selected_category,
            "selected_area": selected_area,
            "selected_type": selected_type,
        },
    )


def learning_detail(request, pk):
    material = get_object_or_404(
        LearningMaterial.objects.prefetch_related(
            "brands",
            "categories",
            "areas",
            "feature_tags",
            "blocks",
            "product_description_images",
            "product_review_images",
            "product_features",
            "product_sales_scripts",
            "product_specifications",
        ),
        pk=pk,
        is_published=True,
    )
    return render(request, "learning/learning_detail.html", {"material": material})
