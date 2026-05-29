from django.test import TestCase
from django.urls import reverse


class NewsListLayoutTests(TestCase):
    def test_empty_news_list_uses_sticky_page_shell_layout(self):
        response = self.client.get(reverse("news_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="site-shell"')
        self.assertContains(response, 'class="site-main"')
        self.assertContains(response, "Новостей пока нет.")
        self.assertContains(response, "empty-state")
