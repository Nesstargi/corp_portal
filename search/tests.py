from django.test import TestCase
from django.urls import reverse

from learning.models import LearningBlock, LearningMaterial


class SearchViewTests(TestCase):
    def test_search_finds_learning_material_by_structured_block_items(self):
        material = LearningMaterial.objects.create(
            title="Dreame X40 Ultra",
            summary="Флагманский робот-пылесос.",
            material_type="product",
            is_published=True,
        )
        LearningBlock.objects.create(
            material=material,
            sort_order=10,
            block_type="feature",
            title="Ключевые преимущества",
            items_data=[
                {
                    "title": "Станция самоочистки",
                    "description": "Помогает реже вмешиваться в ежедневный уход за техникой.",
                    "pitch": "Подчеркни минимальный ручной труд после уборки.",
                }
            ],
        )

        response = self.client.get(reverse("search"), {"query": "самоочистки"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, material.title)
        self.assertContains(response, "Найдено результатов: 1")
        self.assertContains(response, "grid grid--three")
        self.assertContains(response, "simple-card")
