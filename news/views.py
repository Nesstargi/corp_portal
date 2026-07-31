from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from learning.models import LearningMaterial
from promotions.models import Promotion
from portal.recommendations import build_related_content_for_news

from .models import News


def home(request):
    latest_news = News.objects.filter(is_published=True).prefetch_related(
        "brands", "product_categories", "feature_tags"
    )[:3]
    latest_promotions = (
        Promotion.objects.visible_on_site()
        .order_by("-is_featured", "sort_order", "title")[:3]
    )
    latest_learning = (
        LearningMaterial.objects.filter(is_published=True)
        .order_by("-created_at")
        .prefetch_related("brands", "categories", "feature_tags")[:3]
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
    news_queryset = (
        News.objects.filter(is_published=True)
        .prefetch_related("brands", "product_categories", "feature_tags", "blocks")
        .order_by("-created_at")
    )
    paginator = Paginator(news_queryset, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "news/news_list.html",
        {
            "news": page_obj,
            "page_obj": page_obj,
            "result_count": paginator.count,
            "query_without_page": query_params.urlencode(),
        },
    )


def news_detail(request, pk):
    news = get_object_or_404(
        News.objects.prefetch_related(
            "brands", "product_categories", "feature_tags", "blocks"
        ),
        pk=pk,
        is_published=True,
    )
    return render(
        request,
        "news/news_detail.html",
        {
            "news": news,
            "related_content": build_related_content_for_news(news),
        },
    )
