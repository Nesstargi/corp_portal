from django.test import TestCase
from django.urls import reverse

from news.models import News


class PublicSearchRedesignTests(TestCase):
    def test_search_form_has_visible_label_shared_controls_and_result_count(self):
        News.objects.create(title="Apple update", is_published=True)

        response = self.client.get(reverse("search"), {"query": "Apple"})

        self.assertContains(response, '<label for="portal-search-query">')
        self.assertContains(response, 'class="form-control"')
        self.assertContains(response, 'class="filters__actions search-bar__actions"')
        self.assertContains(response, "Найдено результатов: 1")
        self.assertContains(response, "Сбросить")
