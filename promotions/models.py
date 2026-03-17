from collections import Counter
from datetime import datetime
from urllib.parse import parse_qs, urlencode, urlparse

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class PromotionSource(models.Model):
    IMPORT_MODE_SINGLE_SHEET = "single_sheet"
    IMPORT_MODE_LAST_WORKSHEETS = "last_worksheets"
    IMPORT_MODE_CHOICES = (
        (
            IMPORT_MODE_SINGLE_SHEET,
            "Один лист: каждая строка становится отдельной акцией",
        ),
        (
            IMPORT_MODE_LAST_WORKSHEETS,
            "Последние листы книги: каждый лист становится отдельным предзаказом",
        ),
    )

    name = models.CharField("Название источника", max_length=180)
    sheet_url = models.URLField(
        "Ссылка на Google Sheets или CSV",
        help_text=(
            "Подходит обычная ссылка на Google-таблицу или прямая CSV-ссылка. "
            "Для первого этапа таблица должна быть доступна по ссылке."
        ),
    )
    worksheet_gid = models.CharField(
        "GID листа",
        max_length=32,
        blank=True,
        help_text="Если в ссылке уже есть gid, это поле можно не заполнять.",
    )
    header_row = models.PositiveIntegerField(
        "Строка с заголовками",
        default=1,
    )
    import_mode = models.CharField(
        "Как импортировать",
        max_length=32,
        choices=IMPORT_MODE_CHOICES,
        default=IMPORT_MODE_SINGLE_SHEET,
    )
    worksheets_to_import = models.PositiveIntegerField(
        "Сколько последних листов брать",
        default=1,
        help_text="Используется только для режима предзаказов из нескольких листов.",
    )
    is_active = models.BooleanField("Источник активен", default=True)
    auto_publish_imported = models.BooleanField(
        "Сразу показывать импортированные акции на сайте",
        default=True,
    )
    archive_missing_on_import = models.BooleanField(
        "Снимать с публикации пропавшие из таблицы акции",
        default=False,
    )
    last_imported_at = models.DateTimeField(
        "Последний успешный импорт",
        blank=True,
        null=True,
    )
    last_import_error = models.TextField("Последняя ошибка импорта", blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Источник акций"
        verbose_name_plural = "Источники акций"

    def __str__(self):
        return self.name

    @property
    def spreadsheet_id(self):
        parsed = urlparse(self.sheet_url)
        host = parsed.netloc.lower()
        path = parsed.path

        if "docs.google.com" not in host or "/spreadsheets/d/" not in path:
            return ""

        parts = [part for part in path.split("/") if part]
        try:
            document_index = parts.index("d")
            return parts[document_index + 1]
        except (ValueError, IndexError):
            return ""

    @property
    def resolved_gid(self):
        if self.worksheet_gid:
            return self.worksheet_gid

        parsed = urlparse(self.sheet_url)
        fragment_gid = parse_qs(parsed.fragment).get("gid", [""])[0]
        query_gid = parse_qs(parsed.query).get("gid", [""])[0]
        return fragment_gid or query_gid or "0"

    @property
    def csv_url(self):
        if self.spreadsheet_id:
            query = urlencode({"format": "csv", "gid": self.resolved_gid})
            return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/export?{query}"

        return self.sheet_url

    @property
    def xlsx_url(self):
        if self.spreadsheet_id:
            query = urlencode({"format": "xlsx"})
            return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/export?{query}"
        return self.sheet_url

    @property
    def import_url(self):
        if self.import_mode == self.IMPORT_MODE_LAST_WORKSHEETS:
            return self.xlsx_url
        return self.csv_url


class Promotion(models.Model):
    KIND_PROMO_PRICE = "promo_price"
    KIND_GIFT = "gift"
    KIND_PREORDER = "preorder"
    KIND_CHOICES = (
        ("", "Не указан"),
        (KIND_PROMO_PRICE, "Промоцена / скидка / промо"),
        (KIND_GIFT, "Подарок"),
        (KIND_PREORDER, "Предзаказ"),
    )

    source = models.ForeignKey(
        PromotionSource,
        related_name="promotions",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Источник",
    )
    source_row_key = models.CharField(
        "Ключ строки источника",
        max_length=180,
        blank=True,
        db_index=True,
    )
    sync_with_source = models.BooleanField(
        "Обновлять при следующем импорте",
        default=True,
        help_text="Если выключить, импорт больше не будет перезаписывать эту акцию.",
    )
    title = models.CharField("Название акции", max_length=220)
    slug = models.SlugField("Внутренний адрес", max_length=240, unique=True, blank=True)
    promotion_kind = models.CharField(
        "Тип акции",
        max_length=24,
        blank=True,
        choices=KIND_CHOICES,
    )
    badge = models.CharField(
        "Короткая метка",
        max_length=80,
        blank=True,
        help_text="Например: Хит, 0-0-24, Trade-in, Cashback.",
    )
    summary = models.TextField("Краткое описание для списка", blank=True)
    details = models.TextField("Подробные условия", blank=True)
    brand = models.CharField("Бренд", max_length=120, blank=True)
    category = models.CharField("Категория", max_length=120, blank=True)
    promo_code = models.CharField("Промокод", max_length=80, blank=True)
    cta_label = models.CharField("Текст кнопки", max_length=80, blank=True)
    cta_url = models.URLField("Ссылка кнопки", blank=True)
    start_date = models.DateField("Дата начала", blank=True, null=True)
    end_date = models.DateField("Дата окончания", blank=True, null=True)
    sort_order = models.PositiveIntegerField("Порядок на странице", default=0)
    is_featured = models.BooleanField("Выделять как важную", default=False)
    is_published = models.BooleanField("Показывать на сайте", default=True)
    raw_data = models.JSONField(
        "Исходные данные из таблицы",
        default=dict,
        blank=True,
    )
    imported_at = models.DateTimeField("Когда импортировано", blank=True, null=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["sort_order", "-is_featured", "title"]
        verbose_name = "Акция"
        verbose_name_plural = "Акции"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "promotion"
            slug = base_slug
            counter = 2

            while Promotion.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        if not self.cta_label and self.cta_url:
            self.cta_label = "Открыть акцию"

        super().save(*args, **kwargs)

    @property
    def is_active_now(self):
        today = timezone.localdate()
        if self.start_date and self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return self.is_published

    @property
    def extra_data_items(self):
        excluded = {
            "title",
            "name",
            "название",
            "summary",
            "кратко",
            "краткое описание",
            "description",
            "details",
            "подробности",
            "условия",
            "brand",
            "бренд",
            "category",
            "категория",
            "promo_code",
            "промокод",
            "cta_url",
            "ссылка",
            "link",
            "url",
            "start_date",
            "дата начала",
            "end_date",
            "дата окончания",
            "preorder_entries",
        }
        return [
            (key, value)
            for key, value in (self.raw_data or {}).items()
            if value and key.strip().lower() not in excluded
        ]

    @property
    def preorder_entries(self):
        entries = (self.raw_data or {}).get("preorder_entries", [])
        if not isinstance(entries, list):
            return []
        return [entry for entry in entries if isinstance(entry, dict)]

    @property
    def is_preorder(self):
        return self.promotion_kind == self.KIND_PREORDER or bool(self.preorder_entries)

    @property
    def preorder_sheet_name(self):
        return (self.raw_data or {}).get("Лист таблицы", "")

    @property
    def preorder_entries_count(self):
        return len(self.preorder_entries)

    @property
    def preorder_model_names(self):
        models = []
        seen = set()
        for entry in self.preorder_entries:
            name = str(entry.get("model", "")).strip()
            if not name:
                continue
            normalized = name.casefold()
            if normalized in seen:
                continue
            seen.add(normalized)
            models.append(name)
        return models

    @property
    def preorder_models_preview(self):
        return self.preorder_model_names[:3]

    @property
    def preorder_models_count(self):
        return len(self.preorder_model_names)

    @property
    def preorder_status_counts(self):
        counter = Counter()
        for entry in self.preorder_entries:
            status = str(entry.get("status") or entry.get("product_status") or "").strip()
            if status:
                counter[status] += 1
        return counter.most_common(4)

    @property
    def preorder_primary_status(self):
        statuses = self.preorder_status_counts
        if not statuses:
            return ""
        return statuses[0][0]

    @property
    def preorder_latest_order_date(self):
        parsed_dates = []
        for entry in self.preorder_entries:
            value = str(entry.get("order_date", "")).strip()
            if not value:
                continue
            for date_format in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
                try:
                    parsed_dates.append(datetime.strptime(value, date_format).date())
                    break
                except ValueError:
                    continue
        if not parsed_dates:
            return None
        return max(parsed_dates)
