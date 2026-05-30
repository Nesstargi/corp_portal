from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Promotion, PromotionSource
from .services import ImportResult, map_row_to_promotion


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


class PromotionSourceAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="owner",
            password="password",
        )
        self.client.force_login(self.superuser)

    @patch("promotions.admin.import_promotions_from_source")
    def test_selected_google_sheets_source_can_be_imported_from_admin(self, import_source):
        import_source.return_value = ImportResult(created=2, updated=1)
        source = PromotionSource.objects.create(
            name="Основная таблица",
            sheet_url="https://docs.google.com/spreadsheets/d/demo/edit",
        )

        response = self.client.post(
            reverse("admin:promotions_promotionsource_changelist"),
            {
                "action": "import_selected_sources",
                "_selected_action": [str(source.pk)],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        import_source.assert_called_once_with(source)
        self.assertContains(response, "Основная таблица: создано 2, обновлено 1")
