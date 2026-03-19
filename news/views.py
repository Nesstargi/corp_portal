from django.shortcuts import get_object_or_404, render

from learning.models import LearningMaterial
from promotions.models import Promotion

from .models import News


def home(request):
    latest_news = News.objects.filter(is_published=True).prefetch_related(
        "brands", "product_categories", "feature_tags"
    )[:3]
    latest_promotions = (
        Promotion.objects.filter(is_published=True)
        .exclude(promotion_kind=Promotion.KIND_PREORDER)
        .order_by("-is_featured", "sort_order", "title")[:3]
    )
    latest_learning = (
        LearningMaterial.objects.filter(is_published=True)
        .prefetch_related("brands", "categories", "areas", "feature_tags")[:3]
    )
    return render(
        request,
        "home.html",
        {
            "latest_news": latest_news,
            "latest_promotions": latest_promotions,
            "latest_learning": latest_learning,
        },
    )


def news_list(request):
    news = (
        News.objects.filter(is_published=True)
        .prefetch_related("brands", "product_categories", "feature_tags", "blocks")
        .order_by("-created_at")
    )
    return render(request, "news/news_list.html", {"news": news})


def news_detail(request, pk):
    news = get_object_or_404(
        News.objects.prefetch_related(
            "brands", "product_categories", "feature_tags", "blocks"
        ),
        pk=pk,
        is_published=True,
    )
    return render(request, "news/news_detail.html", {"news": news})
