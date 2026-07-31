from datetime import date, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Promotion, PromotionImportRun, PromotionSource
from .admin import PromotionAdminForm
from .services import (
    ImportResult,
    ImportValidationError,
    fetch_source_rows,
    import_promotions_from_source,
    map_row_to_promotion,
    preview_promotions_from_source,
    upsert_mapped_promotion,
)


class PromotionAdminScriptTests(TestCase):
    def test_preview_inserts_field_values_as_text(self):
        script_path = finders.find("js/promotion-admin.js")

        self.assertIsNotNone(script_path)
        script = Path(script_path).read_text(encoding="utf-8")
        self.assertNotIn("chipsContainer.innerHTML", script)
        self.assertNotIn("footerContainer.innerHTML", script)
        self.assertIn("element.textContent = chip", script)
        self.assertIn("element.textContent = item", script)

    def test_manual_promotion_does_not_enable_source_sync_by_default(self):
        form = PromotionAdminForm()

        self.assertFalse(form.fields["sync_with_source"].initial)


class PromotionAdminDuplicateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin",
            password="password",
        )
        self.client.force_login(self.user)
        self.promotion = Promotion.objects.create(
            title="Проверка копирования",
            is_published=True,
        )
        self.duplicate_url = reverse(
            "admin:promotions_promotion_duplicate",
            args=[self.promotion.pk],
        )

    def test_get_duplicate_view_only_shows_confirmation(self):
        response = self.client.get(self.duplicate_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Создать копию")
        self.assertEqual(Promotion.objects.count(), 1)

    def test_post_duplicate_view_creates_unpublished_copy(self):
        response = self.client.post(self.duplicate_url)

        self.assertEqual(response.status_code, 302)
        clone = Promotion.objects.exclude(pk=self.promotion.pk).get()
        self.assertEqual(clone.title, "Проверка копирования (копия)")
        self.assertFalse(clone.is_published)


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

    def test_map_row_normalizes_real_sheet_discount_format(self):
        source = PromotionSource(sheet_url="https://example.com/promotions.csv")

        mapped = map_row_to_promotion(
            source,
            94,
            {
                "Начало": "03,07,2026",
                "Финиш": "20.07.2026",
                "Тип акции": "АВД",
                "Бренд": "XIAOMI ",
                "Товар": "Xiaomi Redmi 15 6GB/128GB",
                "Промоцена": "469",
                "СКИДКА/ ПОДАРОК": "230",
            },
        )

        self.assertEqual(mapped["promotion_kind"], Promotion.KIND_PROMO_PRICE)
        self.assertEqual(mapped["badge"], "АВД")
        self.assertEqual(mapped["brand"], "Xiaomi")
        self.assertEqual(mapped["start_date"], date(2026, 7, 3))
        self.assertEqual(mapped["benefit_value"], "230")
        self.assertEqual(mapped["details"].count("230"), 1)

    def test_map_row_skips_repeated_header_inside_sheet(self):
        source = PromotionSource(sheet_url="https://example.com/promotions.csv")

        mapped = map_row_to_promotion(
            source,
            5,
            {
                "Начало": "начало",
                "Финиш": "конец",
                "Бренд": "Бренд",
                "Товар": "Товар",
                "Промоцена": "Цена",
                "СКИДКА/ ПОДАРОК": "Скидка / подарок",
            },
        )

        self.assertIsNone(mapped)

    def test_imported_details_are_escaped_before_safe_template_rendering(self):
        source = PromotionSource(sheet_url="https://example.com/promotions.csv")

        mapped = map_row_to_promotion(
            source,
            6,
            {
                "Товар": "Телефон <img src=x onerror=alert(1)>",
                "Описание": "<script>alert('xss')</script>\nВторая строка",
            },
        )

        self.assertNotIn("<script>", mapped["details"])
        self.assertNotIn("<img", mapped["details"])
        self.assertIn("&lt;script&gt;", mapped["details"])
        self.assertIn("<br>", mapped["details"])

    def test_map_row_detects_gift_from_benefit_and_keeps_open_end_condition(self):
        source = PromotionSource(sheet_url="https://example.com/promotions.csv")

        mapped = map_row_to_promotion(
            source,
            253,
            {
                "Начало": "17.07.2026",
                "Финиш": "пока не закончатся подарки",
                "Бренд": "XIAOMI",
                "Товар": "Xiaomi Redmi Pad 2",
                "Промоцена": "749",
                "СКИДКА/ ПОДАРОК": "дарим Xiaomi Smart Plug 2",
            },
        )

        self.assertEqual(mapped["promotion_kind"], Promotion.KIND_GIFT)
        self.assertIsNone(mapped["end_date"])
        self.assertIn("пока не закончатся подарки", mapped["details"])

    def test_explicit_preorder_type_wins_over_numeric_discount(self):
        source = PromotionSource(sheet_url="https://example.com/promotions.csv")

        mapped = map_row_to_promotion(
            source,
            56,
            {
                "Тип акции": "предзаказы",
                "Бренд": "Huawei",
                "Товар": "Huawei Pura 90s Pro",
                "Промоцена": "2999",
                "СКИДКА/ ПОДАРОК": "500",
            },
        )

        self.assertEqual(mapped["promotion_kind"], Promotion.KIND_PREORDER)

    def test_source_row_key_is_bounded_and_deterministic(self):
        source = PromotionSource(sheet_url="https://example.com/promotions.csv")
        raw_row = {
            "ID": "Очень длинный идентификатор " * 20,
            "Товар": "Тестовый товар",
        }

        first = map_row_to_promotion(source, 2, raw_row)
        second = map_row_to_promotion(source, 2, raw_row)

        self.assertEqual(first["source_row_key"], second["source_row_key"])
        self.assertLessEqual(len(first["source_row_key"]), 180)

    def test_source_row_key_distinguishes_plus_model_suffix(self):
        source = PromotionSource(sheet_url="https://example.com/promotions.csv")

        regular = map_row_to_promotion(
            source,
            82,
            {"Товар": "Xiaomi Redmi Note 15 Pro 5G", "Бренд": "Xiaomi"},
        )
        plus = map_row_to_promotion(
            source,
            83,
            {"Товар": "Xiaomi Redmi Note 15 Pro+ 5G", "Бренд": "Xiaomi"},
        )

        self.assertNotEqual(regular["source_row_key"], plus["source_row_key"])

    def test_color_is_added_to_imported_title_and_key(self):
        source = PromotionSource(sheet_url="https://example.com/promotions.csv")

        black = map_row_to_promotion(
            source,
            145,
            {
                "Товар": "Умные часы Honor Watch 5 (STL-B19)",
                "Бренд": "Honor",
                "Цвет": "чёрный",
                "Промоцена": "399",
            },
        )
        green = map_row_to_promotion(
            source,
            147,
            {
                "Товар": "Умные часы Honor Watch 5 (STL-B19)",
                "Бренд": "Honor",
                "Цвет": "зелёный",
                "Промоцена": "499",
            },
        )

        self.assertEqual(black["title"], "Умные часы Honor Watch 5 (STL-B19) — чёрный")
        self.assertEqual(green["title"], "Умные часы Honor Watch 5 (STL-B19) — зелёный")
        self.assertNotEqual(black["source_row_key"], green["source_row_key"])

    @override_settings(
        PROMOTION_IMPORT_ROW_OVERRIDES={
            "sheet-id": (
                {
                    "match": {
                        "title": "Honor Watch 5",
                        "promo_price": "399",
                    },
                    "set": {"color": "чёрный"},
                },
            )
        }
    )
    def test_local_rule_adds_color_missing_from_google_sheet(self):
        source = PromotionSource(
            sheet_url="https://docs.google.com/spreadsheets/d/sheet-id/edit?gid=0"
        )

        mapped = map_row_to_promotion(
            source,
            145,
            {
                "Товар": "Honor Watch 5",
                "Промоцена": "399",
            },
        )

        self.assertEqual(mapped["title"], "Honor Watch 5 — чёрный")
        self.assertEqual(
            mapped["raw_data"]["Цвет (правило импорта)"],
            "чёрный",
        )

    @override_settings(
        PROMOTION_IMPORT_ROW_OVERRIDES={
            "sheet-id": (
                {
                    "match": {
                        "title": "Huawei Mate 80 Pro 16GB/512GB",
                        "promo_price": "3299",
                        "start_date": "07.07.2026",
                        "end_date": "03.08.2026",
                    },
                    "skip": True,
                },
            )
        }
    )
    def test_local_rule_can_skip_row_without_changing_google_sheet(self):
        source = PromotionSource(
            sheet_url="https://docs.google.com/spreadsheets/d/sheet-id/edit?gid=0"
        )

        mapped = map_row_to_promotion(
            source,
            45,
            {
                "Начало": "07.07.2026",
                "Финиш": "03.08.2026",
                "Товар": "Huawei Mate 80 Pro 16GB/512GB",
                "Промоцена": "3299",
            },
        )

        self.assertIsNone(mapped)

    @patch("promotions.services.load_payload")
    def test_fetch_source_rows_preserves_value_under_blank_header(self, load_payload):
        csv_text = (
            "Начало,Финиш,Тип акции,Бренд,Товар,Промоцена,СКИДКА/ ПОДАРОК,\n"
            "01.07.2026,31.07.2026,Подарок,Honor,Honor 600,1999,Часы в подарок,неполка\n"
        )
        load_payload.return_value = (csv_text.encode("utf-8"), "utf-8")
        source = PromotionSource(sheet_url="https://example.com/promotions.csv")

        rows = fetch_source_rows(source)

        self.assertEqual(rows[0][1]["Колонка 8"], "неполка")

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


class PromotionImportSafetyTests(TestCase):
    def setUp(self):
        self.source = PromotionSource.objects.create(
            name="Основная таблица",
            sheet_url="https://example.com/promotions.csv",
        )

    @patch("promotions.services.fetch_source_rows")
    def test_exact_duplicate_rows_are_skipped_once(self, fetch_rows):
        first = {
            "ID": "promo-1",
            "Тип акции": "Подарок",
            "Бренд": "Honor",
            "Товар": "Honor 600",
            "Промоцена": "1999",
            "СКИДКА/ ПОДАРОК": "Часы в подарок",
        }
        second = dict(first, **{"Тип акции": "ПОДАРОК"})
        fetch_rows.return_value = [(11, first), (248, second)]

        result = import_promotions_from_source(self.source)

        self.assertEqual(Promotion.objects.filter(source=self.source).count(), 1)
        self.assertEqual(result.created, 1)
        self.assertEqual(result.duplicates, 1)
        self.assertEqual(result.skipped, 1)
        self.assertTrue(result.warnings)
        import_run = PromotionImportRun.objects.get(source=self.source)
        self.assertEqual(import_run.status, PromotionImportRun.STATUS_SUCCESS)
        self.assertEqual(import_run.created_count, 1)
        self.assertEqual(import_run.duplicate_count, 1)
        self.assertTrue(import_run.finished_at)

    @patch("promotions.services.fetch_source_rows")
    def test_conflicting_duplicate_keys_abort_before_writes(self, fetch_rows):
        common = {
            "ID": "promo-1",
            "Бренд": "Honor",
            "Товар": "Honor Watch 5",
            "СКИДКА/ ПОДАРОК": "200",
        }
        fetch_rows.return_value = [
            (145, dict(common, **{"Промоцена": "499"})),
            (147, dict(common, **{"Промоцена": "399"})),
        ]

        with self.assertRaises(ImportValidationError):
            import_promotions_from_source(self.source)

        self.assertFalse(Promotion.objects.filter(source=self.source).exists())
        self.source.refresh_from_db()
        self.assertIn("строки 145 и 147", self.source.last_import_error)
        import_run = PromotionImportRun.objects.get(source=self.source)
        self.assertEqual(import_run.status, PromotionImportRun.STATUS_ERROR)
        self.assertIn("строки 145 и 147", import_run.error)
        self.assertTrue(import_run.finished_at)

    @patch("promotions.services.fetch_source_rows")
    def test_invalid_date_range_aborts_before_writes(self, fetch_rows):
        fetch_rows.return_value = [
            (
                7,
                {
                    "Товар": "Акция с ошибкой",
                    "Начало": "31.07.2026",
                    "Финиш": "01.07.2026",
                },
            )
        ]

        with self.assertRaisesMessage(ImportValidationError, "Строка 7"):
            import_promotions_from_source(self.source)

        self.assertFalse(Promotion.objects.filter(source=self.source).exists())

    @patch("promotions.services.fetch_source_rows")
    def test_unrecognized_end_date_aborts_instead_of_becoming_open_ended(self, fetch_rows):
        fetch_rows.return_value = [
            (
                8,
                {
                    "Товар": "Акция с опечаткой",
                    "Начало": "01.07.2026",
                    "Финиш": "31.02.2026",
                },
            )
        ]

        with self.assertRaisesMessage(ImportValidationError, "31.02.2026"):
            import_promotions_from_source(self.source)

        self.assertFalse(Promotion.objects.filter(source=self.source).exists())

    @patch("promotions.services.fetch_source_rows")
    def test_color_variants_with_different_prices_are_imported_separately(self, fetch_rows):
        common = {
            "Начало": "23.06.2026",
            "Финиш": "04.08.2026",
            "Бренд": "Honor",
            "Товар": "Умные часы Honor Watch 5 (STL-B19)",
            "СКИДКА/ ПОДАРОК": "200",
        }
        fetch_rows.return_value = [
            (145, dict(common, **{"Цвет": "чёрный", "Промоцена": "399"})),
            (147, dict(common, **{"Цвет": "зелёный", "Промоцена": "499"})),
        ]

        result = import_promotions_from_source(self.source)

        self.assertEqual(result.created, 2)
        self.assertEqual(result.duplicates, 0)
        self.assertEqual(
            set(Promotion.objects.values_list("title", flat=True)),
            {
                "Умные часы Honor Watch 5 (STL-B19) — чёрный",
                "Умные часы Honor Watch 5 (STL-B19) — зелёный",
            },
        )

    @patch("promotions.services.fetch_source_rows")
    def test_preview_reports_changes_without_writing(self, fetch_rows):
        fetch_rows.return_value = [
            (
                2,
                {
                    "ID": "promo-1",
                    "Товар": "Тестовая акция",
                    "Промоцена": "100",
                    "СКИДКА/ ПОДАРОК": "20",
                },
            )
        ]

        result = preview_promotions_from_source(self.source)

        self.assertEqual(result.created, 1)
        self.assertFalse(Promotion.objects.filter(source=self.source).exists())
        self.source.refresh_from_db()
        self.assertIsNone(self.source.last_imported_at)
        import_run = PromotionImportRun.objects.get(source=self.source)
        self.assertTrue(import_run.is_dry_run)
        self.assertEqual(import_run.status, PromotionImportRun.STATUS_SUCCESS)
        self.assertEqual(import_run.created_count, 1)

    @patch("promotions.services.fetch_source_rows")
    def test_empty_export_is_blocked_by_minimum_expected_rows(self, fetch_rows):
        fetch_rows.return_value = []

        with self.assertRaisesMessage(ImportValidationError, "установлен минимум 1"):
            import_promotions_from_source(self.source)

        self.assertFalse(Promotion.objects.filter(source=self.source).exists())
        self.assertEqual(
            PromotionImportRun.objects.get(source=self.source).status,
            PromotionImportRun.STATUS_ERROR,
        )

    @patch("promotions.services.fetch_source_rows")
    def test_large_drop_is_blocked_before_existing_promotions_are_changed(self, fetch_rows):
        for number in range(1, 5):
            Promotion.objects.create(
                source=self.source,
                source_row_key=f"promo-{number}",
                title=f"Акция {number}",
                is_published=True,
            )
        fetch_rows.return_value = [
            (2, {"ID": "promo-1", "Товар": "Акция 1 обновлённая"}),
        ]

        with self.assertRaisesMessage(ImportValidationError, "пропало 3 (75%)"):
            import_promotions_from_source(self.source)

        self.assertEqual(
            Promotion.objects.filter(source=self.source, is_published=True).count(),
            4,
        )
        self.assertEqual(
            Promotion.objects.get(source=self.source, source_row_key="promo-1").title,
            "Акция 1",
        )

    @patch("promotions.services.fetch_source_rows")
    def test_drop_at_configured_limit_is_allowed_and_missing_row_is_unpublished(self, fetch_rows):
        for number in range(1, 3):
            Promotion.objects.create(
                source=self.source,
                source_row_key=f"promo-{number}",
                title=f"Акция {number}",
                is_published=True,
            )
        fetch_rows.return_value = [
            (2, {"ID": "promo-1", "Товар": "Акция 1"}),
        ]

        result = import_promotions_from_source(self.source)

        self.assertEqual(result.unpublished, 1)
        self.assertTrue(
            Promotion.objects.get(source=self.source, source_row_key="promo-1").is_published
        )
        self.assertFalse(
            Promotion.objects.get(source=self.source, source_row_key="promo-2").is_published
        )

    @patch("promotions.services.fetch_source_rows")
    def test_explicit_empty_source_setting_can_unpublish_all_rows(self, fetch_rows):
        self.source.minimum_expected_rows = 0
        self.source.max_missing_percent = 100
        self.source.save(update_fields=["minimum_expected_rows", "max_missing_percent"])
        Promotion.objects.create(
            source=self.source,
            source_row_key="promo-1",
            title="Завершённая выгрузка",
            is_published=True,
        )
        fetch_rows.return_value = []

        result = import_promotions_from_source(self.source)

        self.assertEqual(result.unpublished, 1)
        self.assertFalse(Promotion.objects.get(source=self.source).is_published)


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

    @patch("promotions.admin.preview_promotions_from_source")
    def test_selected_source_can_be_checked_without_import(self, preview_source):
        preview_source.return_value = ImportResult(created=3, duplicates=1)
        source = PromotionSource.objects.create(
            name="Основная таблица",
            sheet_url="https://docs.google.com/spreadsheets/d/demo/edit",
        )

        response = self.client.post(
            reverse("admin:promotions_promotionsource_changelist"),
            {
                "action": "preview_selected_sources",
                "_selected_action": [str(source.pk)],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        preview_source.assert_called_once_with(source)
        self.assertContains(response, "Проверка: Основная таблица: создано 3")
        self.assertContains(response, "дубликатов 1")

    def test_new_source_archives_missing_rows_by_default_and_shows_health(self):
        source = PromotionSource.objects.create(
            name="Новый источник",
            sheet_url="https://example.com/promotions.csv",
        )

        response = self.client.get(
            reverse("admin:promotions_promotionsource_changelist")
        )

        self.assertTrue(source.archive_missing_on_import)
        self.assertContains(response, "Ещё не запускался")

    def test_source_form_shows_import_safety_settings_and_history_link(self):
        source = PromotionSource.objects.create(
            name="Защищённый источник",
            sheet_url="https://example.com/promotions.csv",
        )

        response = self.client.get(
            reverse("admin:promotions_promotionsource_change", args=[source.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Минимум распознанных акций")
        self.assertContains(response, "Максимум пропавших акций за один импорт")
        self.assertContains(response, "Открыть историю этого источника")

    def test_import_history_admin_shows_mode_status_and_result(self):
        source = PromotionSource.objects.create(
            name="Источник с историей",
            sheet_url="https://example.com/promotions.csv",
        )
        PromotionImportRun.objects.create(
            source=source,
            is_dry_run=True,
            status=PromotionImportRun.STATUS_SUCCESS,
            created_count=3,
            updated_count=2,
            skipped_count=1,
            finished_at=timezone.now(),
        )

        response = self.client.get(
            reverse("admin:promotions_promotionimportrun_changelist"),
            {"source__id__exact": source.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "История импорта акций")
        self.assertNotContains(response, "для изменения")
        self.assertContains(response, "Источник с историей")
        self.assertContains(response, "Проверка")
        self.assertContains(response, "Успешно")
        self.assertContains(response, "+3 / ~2 / −0; пропущено 1")

        detail_response = self.client.get(
            reverse(
                "admin:promotions_promotionimportrun_change",
                args=[PromotionImportRun.objects.get(source=source).pk],
            )
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Просмотреть Запуск импорта акций")
        self.assertNotContains(detail_response, 'name="_save"')


class PromotionSyncCommandTests(TestCase):
    def setUp(self):
        self.first = PromotionSource.objects.create(
            name="Первый источник",
            sheet_url="https://example.com/first.csv",
        )
        self.second = PromotionSource.objects.create(
            name="Второй источник",
            sheet_url="https://example.com/second.csv",
        )

    @patch("promotions.management.commands.sync_promotion_sources.import_promotions_from_source")
    def test_dry_run_is_forwarded_to_import_service(self, import_source):
        import_source.return_value = ImportResult(created=2)
        stdout = StringIO()

        call_command(
            "sync_promotion_sources",
            source=self.first.pk,
            dry_run=True,
            stdout=stdout,
        )

        import_source.assert_called_once_with(self.first, dry_run=True)
        self.assertIn("Проверка: Первый источник", stdout.getvalue())

    @patch("promotions.management.commands.sync_promotion_sources.import_promotions_from_source")
    def test_failure_of_one_source_does_not_skip_the_next(self, import_source):
        def import_side_effect(source, *, dry_run=False):
            if source.pk == self.first.pk:
                raise RuntimeError("нет связи")
            return ImportResult(created=1)

        import_source.side_effect = import_side_effect
        stdout = StringIO()
        stderr = StringIO()

        with self.assertRaises(CommandError):
            call_command(
                "sync_promotion_sources",
                stdout=stdout,
                stderr=stderr,
            )

        self.assertEqual(import_source.call_count, 2)
        self.assertIn("Второй источник: создано 1", stdout.getvalue())
        self.assertIn("Первый источник", stderr.getvalue())


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

    def test_changelist_shows_actual_lifecycle_statuses(self):
        today = timezone.localdate()
        Promotion.objects.create(
            title="Действующая акция",
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=1),
        )
        Promotion.objects.create(
            title="Завершённая акция",
            end_date=today - timedelta(days=1),
        )

        response = self.client.get(reverse("admin:promotions_promotion_changelist"))

        self.assertContains(response, "Действует")
        self.assertContains(response, "Завершена")

    def test_finished_promotion_has_no_broken_public_link_in_admin(self):
        promotion = Promotion.objects.create(
            title="Завершённая акция без ссылки",
            end_date=timezone.localdate() - timedelta(days=1),
        )

        response = self.client.get(reverse("admin:promotions_promotion_changelist"))

        self.assertContains(response, "Срок завершён — на сайте скрыта.")
        self.assertNotContains(response, f'href="{promotion.get_absolute_url()}"')

    def test_lifecycle_filter_returns_only_finished_promotions(self):
        today = timezone.localdate()
        active = Promotion.objects.create(
            title="Действующая акция",
            end_date=today + timedelta(days=1),
        )
        finished = Promotion.objects.create(
            title="Завершённая акция",
            end_date=today - timedelta(days=1),
        )

        response = self.client.get(
            reverse("admin:promotions_promotion_changelist"),
            {"lifecycle": "finished"},
        )

        queryset = response.context["cl"].queryset
        self.assertEqual(list(queryset), [finished])
        self.assertNotIn(active, queryset)

    def test_publish_action_skips_finished_promotions(self):
        today = timezone.localdate()
        active = Promotion.objects.create(
            title="Актуальная акция",
            is_published=False,
            end_date=today + timedelta(days=1),
        )
        finished = Promotion.objects.create(
            title="Завершённая акция",
            is_published=False,
            end_date=today - timedelta(days=1),
        )

        response = self.client.post(
            reverse("admin:promotions_promotion_changelist"),
            {
                "action": "publish_selected",
                "_selected_action": [str(active.pk), str(finished.pk)],
            },
            follow=True,
        )

        active.refresh_from_db()
        finished.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(active.is_published)
        self.assertFalse(finished.is_published)
        self.assertContains(response, "Завершённые акции не опубликованы: 1")
