from django.db.models import Q
from django.shortcuts import render

from learning.models import LearningMaterial
from news.models import News
from promotions.models import Promotion


def search(request):
    search_query = request.GET.get("query", "").strip()
    news_results = News.objects.none()
    promotion_results = Promotion.objects.none()
    learning_results = LearningMaterial.objects.none()

    if search_query:
        news_results = (
            News.objects.filter(is_published=True)
            .filter(
                Q(title__icontains=search_query)
                | Q(summary__icontains=search_query)
                | Q(content__icontains=search_query)
                | Q(blocks__text__icontains=search_query)
                | Q(brands__name__icontains=search_query)
                | Q(product_categories__name__icontains=search_query)
            )
            .distinct()
        )
        promotion_results = (
            Promotion.objects.filter(is_published=True)
            .filter(
                Q(title__icontains=search_query)
                | Q(summary__icontains=search_query)
                | Q(details__icontains=search_query)
                | Q(brand__icontains=search_query)
                | Q(category__icontains=search_query)
                | Q(promo_code__icontains=search_query)
                | Q(badge__icontains=search_query)
            )
            .distinct()
        )
        learning_results = (
            LearningMaterial.objects.filter(is_published=True)
            .filter(
                Q(title__icontains=search_query)
                | Q(summary__icontains=search_query)
                | Q(content__icontains=search_query)
                | Q(product_full_description__icontains=search_query)
                | Q(product_text_review__icontains=search_query)
                | Q(product_short_summary__icontains=search_query)
                | Q(blocks__text__icontains=search_query)
                | Q(product_features__title__icontains=search_query)
                | Q(product_features__description__icontains=search_query)
                | Q(product_features__client_pitch__icontains=search_query)
                | Q(product_sales_scripts__title__icontains=search_query)
                | Q(product_sales_scripts__script_text__icontains=search_query)
                | Q(product_specifications__name__icontains=search_query)
                | Q(product_specifications__value__icontains=search_query)
                | Q(brands__name__icontains=search_query)
                | Q(categories__name__icontains=search_query)
                | Q(areas__name__icontains=search_query)
            )
            .distinct()
        )

    return render(
        request,
        "search/search.html",
        {
            "search_query": search_query,
            "news_results": news_results,
            "promotion_results": promotion_results,
            "learning_results": learning_results,
        },
    )
