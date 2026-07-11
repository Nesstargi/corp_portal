from django.test import TestCase
from django.urls import reverse

from catalog.models import Brand, FeatureTag, ProductCategory

from .models import LearningMaterial


class LearningPublicFiltersRedesignTests(TestCase):
    def setUp(self):
        self.apple = Brand.objects.create(name="Apple")
        self.samsung = Brand.objects.create(name="Samsung")
        self.phones = ProductCategory.objects.create(name="Смартфоны")
        self.tablets = ProductCategory.objects.create(name="Планшеты")
        self.camera = FeatureTag.objects.create(name="Камера")
        self.stylus = FeatureTag.objects.create(name="Стилус")

    def create_material(self, title, *, published=True, brand=None, category=None, feature=None):
        material = LearningMaterial.objects.create(
            title=title,
            is_published=published,
        )
        if brand:
            material.brands.add(brand)
        if category:
            material.categories.add(category)
        if feature:
            material.feature_tags.add(feature)
        return material

    def test_filters_are_combined_with_and(self):
        expected = self.create_material(
            "Apple camera phone",
            brand=self.apple,
            category=self.phones,
            feature=self.camera,
        )
        self.create_material(
            "Wrong feature",
            brand=self.apple,
            category=self.phones,
            feature=self.stylus,
        )
        self.create_material(
            "Wrong brand",
            brand=self.samsung,
            category=self.phones,
            feature=self.camera,
        )

        response = self.client.get(
            reverse("learning_list"),
            {
                "brand": self.apple.slug,
                "category": self.phones.slug,
                "feature": self.camera.slug,
            },
        )

        self.assertEqual(list(response.context["materials"]), [expected])
        self.assertEqual(response.context["result_count"], 1)
        self.assertTrue(response.context["has_active_filters"])

    def test_invalid_slugs_are_ignored_and_unpublished_options_are_hidden(self):
        visible = self.create_material(
            "Visible",
            brand=self.apple,
            category=self.phones,
            feature=self.camera,
        )
        self.create_material(
            "Hidden",
            published=False,
            brand=self.samsung,
            category=self.tablets,
            feature=self.stylus,
        )

        response = self.client.get(
            reverse("learning_list"),
            {"brand": "missing", "category": "missing", "feature": "missing"},
        )

        self.assertEqual(list(response.context["materials"]), [visible])
        self.assertEqual(response.context["selected_brand"], "")
        self.assertEqual(response.context["selected_category"], "")
        self.assertEqual(response.context["selected_feature"], "")
        self.assertFalse(response.context["has_active_filters"])
        self.assertEqual(list(response.context["brands"]), [self.apple])
        self.assertEqual(list(response.context["product_categories"]), [self.phones])
        self.assertEqual(list(response.context["feature_tags"]), [self.camera])

    def test_pagination_uses_twelve_items_and_preserves_filters_without_page(self):
        for index in range(13):
            self.create_material(f"Material {index:02d}", brand=self.apple)

        response = self.client.get(
            reverse("learning_list"),
            {"brand": self.apple.slug, "page": 2},
        )

        self.assertEqual(response.context["result_count"], 13)
        self.assertEqual(len(response.context["materials"]), 1)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(response.context["query_without_page"], f"brand={self.apple.slug}")

