from django.test import TestCase
from django.urls import reverse

from .models import News


class NewsPublicListRedesignTests(TestCase):
    def test_list_is_paginated_by_twelve_and_excludes_unpublished_news(self):
        for index in range(13):
            News.objects.create(title=f"News {index:02d}", is_published=True)
        News.objects.create(title="Hidden news", is_published=False)

        response = self.client.get(reverse("news_list"), {"page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result_count"], 13)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["news"]), 1)
        self.assertNotContains(response, "Hidden news")
        self.assertContains(response, "Страница 2 из 2")

    def test_pagination_query_drops_page_and_preserves_other_parameters(self):
        for index in range(13):
            News.objects.create(title=f"News {index:02d}", is_published=True)

        response = self.client.get(
            reverse("news_list"),
            {"source": "internal", "page": 2},
        )

        self.assertEqual(response.context["query_without_page"], "source=internal")
        self.assertContains(response, "?source=internal&amp;page=1")

