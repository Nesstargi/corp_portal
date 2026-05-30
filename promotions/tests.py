from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Promotion, PromotionSource
from .services import ImportResult, map_row_to_promotion, upsert_mapped_promotion


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

    def test_reimport_keeps_manually_filled_kind_and_dates_when_sheet_values_are_empty(self):
        source = PromotionSource.objects.create(
            name="Основная таблица",
            sheet_url="https://example.com/promotions.csv",
        )
        promotion = Promotion.objects.create(
            source=source,
            source_row_key="manual-values",
            title="Ручная правка",
            promotion_kind=Promotion.KIND_GIFT,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
        )

        upsert_mapped_promotion(
            source,
            {
                "source": source,
                "source_row_key": "manual-values",
                "promotion_kind": "",
                "start_date": None,
                "end_date": None,
            },
            ImportResult(),
            [],
        )

        promotion.refresh_from_db()
        self.assertEqual(promotion.promotion_kind, Promotion.KIND_GIFT)
        self.assertEqual(promotion.start_date, date(2026, 6, 1))
        self.assertEqual(promotion.end_date, date(2026, 6, 30))


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


class PromotionAdminListEditingTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="owner",
            password="password",
        )
        self.client.force_login(self.superuser)

    def test_changelist_contains_inline_kind_and_date_fields(self):
        Promotion.objects.create(title="Акция из таблицы")

        response = self.client.get(reverse("admin:promotions_promotion_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="form-0-promotion_kind"')
        self.assertContains(response, 'size="1"')
        self.assertContains(response, 'name="form-0-start_date"')
        self.assertContains(response, 'name="form-0-end_date"')

    def test_bulk_action_sets_kind_for_selected_promotions(self):
        first = Promotion.objects.create(title="Первая акция")
        second = Promotion.objects.create(title="Вторая акция")

        response = self.client.post(
            reverse("admin:promotions_promotion_changelist"),
            {
                "action": "set_kind_gift",
                "_selected_action": [str(first.pk), str(second.pk)],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(Promotion.objects.values_list("promotion_kind", flat=True)),
            {Promotion.KIND_GIFT},
        )

    def test_changelist_saves_inline_kind_and_dates(self):
        promotion = Promotion.objects.create(title="Акция для быстрой правки")

        response = self.client.post(
            reverse("admin:promotions_promotion_changelist"),
            {
                "_save": "Сохранить",
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "1",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": str(promotion.pk),
                "form-0-promotion_kind": Promotion.KIND_GIFT,
                "form-0-start_date": "2026-06-01",
                "form-0-end_date": "2026-06-30",
                "form-0-is_published": "on",
                "form-0-sync_with_source": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        promotion.refresh_from_db()
        self.assertEqual(promotion.promotion_kind, Promotion.KIND_GIFT)
        self.assertEqual(promotion.start_date, date(2026, 6, 1))
        self.assertEqual(promotion.end_date, date(2026, 6, 30))
