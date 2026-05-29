from django.test import TestCase
from django.urls import reverse


class LearningCompareViewTests(TestCase):
    def test_compare_view_is_temporarily_disabled(self):
        response = self.client.get(reverse("learning_compare"))

        self.assertEqual(response.status_code, 404)
