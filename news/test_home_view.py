from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from learning.models import LearningMaterial


class HomeViewTests(TestCase):
    def test_home_uses_latest_learning_materials_by_created_at(self):
        oldest = LearningMaterial.objects.create(title="Zulu", is_published=True)
        older = LearningMaterial.objects.create(title="Alpha", is_published=True)
        newer = LearningMaterial.objects.create(title="Mike", is_published=True)
        newest = LearningMaterial.objects.create(title="Bravo", is_published=True)

        now = timezone.now()
        LearningMaterial.objects.filter(pk=oldest.pk).update(created_at=now - timedelta(days=4))
        LearningMaterial.objects.filter(pk=older.pk).update(created_at=now - timedelta(days=3))
        LearningMaterial.objects.filter(pk=newer.pk).update(created_at=now - timedelta(days=2))
        LearningMaterial.objects.filter(pk=newest.pk).update(created_at=now - timedelta(days=1))

        response = self.client.get(reverse("home"))

        titles = [item.title for item in response.context["latest_learning"]]

        self.assertEqual(titles, ["Bravo", "Mike", "Alpha"])
