from django.test import TestCase

from .models import Promotion, PromotionSource
from .services import map_row_to_promotion


class PromotionSlugTests(TestCase):
    def test_save_transliterates_cyrillic_title_into_ascii_slug(self):
        promotion = Promotion.objects.create(title="Весенняя акция")

        self.assertEqual(promotion.slug, "vesennyaya-aktsiya")

    def test_save_keeps_duplicate_cyrillic_slugs_unique(self):
        Promotion.objects.create(title="Весенняя акция")
        promotion = Promotion.objects.create(title="Весенняя акция")

        self.assertEqual(promotion.slug, "vesennyaya-aktsiya-2")


class PromotionImportMappingTests(TestCase):
    def test_map_row_to_promotion_builds_ascii_row_key_from_cyrillic_title(self):
        source = PromotionSource(sheet_url="https://example.com/promotions.csv")

        mapped = map_row_to_promotion(
            source,
            7,
            {
                "Название": "Скидка на холодильник",
            },
        )

        self.assertIsNotNone(mapped)
        self.assertEqual(mapped["source_row_key"], "skidka-na-kholodilnik")

    def test_map_row_to_promotion_transliterates_explicit_cyrillic_row_key(self):
        source = PromotionSource(sheet_url="https://example.com/promotions.csv")

        mapped = map_row_to_promotion(
            source,
            3,
            {
                "Код акции": "Акция №7",
                "Название": "Подарок за покупку",
            },
        )

        self.assertIsNotNone(mapped)
        self.assertEqual(mapped["source_row_key"], "aktsiya-no7")
