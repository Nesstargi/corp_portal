from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from learning.models import LearningMaterial
from news.models import News
from promotions.models import Promotion


class SearchViewTests(TestCase):
    def test_search_excludes_preorders_from_promotion_results(self):
        Promotion.objects.create(
            title="Телевизор Samsung",
            is_published=True,
            promotion_kind=Promotion.KIND_PREORDER,
        )
        Promotion.objects.create(
            title="Скидка Samsung",
            is_published=True,
        )

        response = self.client.get(reverse("search"), {"query": "Samsung"})

        titles = {item.title for item in response.context["promotion_results"]}

        self.assertEqual(titles, {"Скидка Samsung"})

    def test_search_exposes_total_results_count(self):
        News.objects.create(title="Apple news", is_published=True)
        LearningMaterial.objects.create(title="Apple learning", is_published=True)
        Promotion.objects.create(title="Apple promo", is_published=True)

        response = self.client.get(reverse("search"), {"query": "Apple"})

        self.assertEqual(response.context["news_count"], 1)
        self.assertEqual(response.context["learning_count"], 1)
        self.assertEqual(response.context["promotion_count"], 1)
        self.assertEqual(response.context["total_results"], 3)

    def test_search_excludes_finished_promotions(self):
        Promotion.objects.create(
            title="Samsung завершённая акция",
            is_published=True,
            end_date=timezone.localdate() - timedelta(days=1),
        )
        Promotion.objects.create(
            title="Samsung актуальная акция",
            is_published=True,
            end_date=timezone.localdate() + timedelta(days=1),
        )

        response = self.client.get(reverse("search"), {"query": "Samsung"})

        titles = {item.title for item in response.context["promotion_results"]}
        self.assertEqual(titles, {"Samsung актуальная акция"})
        self.assertEqual(response.context["promotion_count"], 1)
