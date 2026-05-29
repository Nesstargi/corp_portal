from django.test import TestCase

from catalog.models import Brand, FeatureTag, ProductCategory
from learning.models import LearningMaterial
from news.models import News
from promotions.models import Promotion

from .recommendations import (
    build_related_content_for_learning,
    build_related_content_for_news,
    build_related_content_for_promotion,
)


class RecommendationTests(TestCase):
    def test_build_related_content_for_news_uses_shared_brand_category_and_tag(self):
        brand = Brand.objects.create(name="Samsung")
        category = ProductCategory.objects.create(name="Смартфоны")
        tag = FeatureTag.objects.create(name="Новинка")

        news = News.objects.create(title="Главная новость", is_published=True)
        news.brands.add(brand)
        news.product_categories.add(category)
        news.feature_tags.add(tag)

        related_news = News.objects.create(title="Похожая новость", is_published=True)
        related_news.brands.add(brand)

        learning = LearningMaterial.objects.create(title="Обучение Samsung", is_published=True)
        learning.brands.add(brand)
        learning.feature_tags.add(tag)

        promotion = Promotion.objects.create(
            title="Акция Samsung",
            is_published=True,
            brand="Samsung",
            category="Смартфоны",
        )
        Promotion.objects.create(
            title="Чужая акция",
            is_published=True,
            brand="LG",
            category="Телевизоры",
        )

        items = build_related_content_for_news(news)
        titles = {item["title"] for item in items}

        self.assertIn("Обучение Samsung", titles)
        self.assertIn("Акция Samsung", titles)
        self.assertIn("Похожая новость", titles)
        self.assertNotIn("Главная новость", titles)

    def test_build_related_content_for_learning_excludes_current_material(self):
        brand = Brand.objects.create(name="Apple")

        current = LearningMaterial.objects.create(title="Текущий материал", is_published=True)
        current.brands.add(brand)

        related = LearningMaterial.objects.create(title="Похожий материал", is_published=True)
        related.brands.add(brand)

        items = build_related_content_for_learning(current)
        titles = {item["title"] for item in items}

        self.assertIn("Похожий материал", titles)
        self.assertNotIn("Текущий материал", titles)

    def test_build_related_content_for_promotion_uses_same_brand_and_category(self):
        brand = Brand.objects.create(name="Xiaomi")
        category = ProductCategory.objects.create(name="Пылесосы")

        target = Promotion.objects.create(
            title="Главная акция",
            is_published=True,
            brand="Xiaomi",
            category="Пылесосы",
        )
        related_promotion = Promotion.objects.create(
            title="Похожая акция",
            is_published=True,
            brand="Xiaomi",
            category="Пылесосы",
        )

        news = News.objects.create(title="Новость Xiaomi", is_published=True)
        news.brands.add(brand)
        news.product_categories.add(category)

        learning = LearningMaterial.objects.create(title="Материал Xiaomi", is_published=True)
        learning.brands.add(brand)
        learning.categories.add(category)

        items = build_related_content_for_promotion(target)
        titles = {item["title"] for item in items}

        self.assertIn("Похожая акция", titles)
        self.assertIn("Новость Xiaomi", titles)
        self.assertIn("Материал Xiaomi", titles)
        self.assertNotIn("Главная акция", titles)
