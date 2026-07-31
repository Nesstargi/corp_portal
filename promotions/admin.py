from datetime import timedelta

from django import forms
from django.contrib import admin, messages
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, strip_tags

from catalog.admin_mixins import (
    AdminDuplicateMixin,
    AdminPresentationMixin,
    AdminTemplatesAndFiltersMixin,
    render_admin_card_preview,
)
from catalog.widgets import RichTextToolbarWidget

from .models import Promotion, PromotionImportRun, PromotionSource
from .services import import_promotions_from_source, preview_promotions_from_source


class PromotionAdminForm(forms.ModelForm):
    @staticmethod
    def _format_period(start_date, end_date):
        if start_date and end_date:
            return f"с {start_date:%d.%m.%Y} по {end_date:%d.%m.%Y}"
        if start_date:
            return f"с {start_date:%d.%m.%Y}"
        if end_date:
            return f"до {end_date:%d.%m.%Y}"
        return ""

    @classmethod
    def build_auto_summary(cls, cleaned_data):
        title = str(cleaned_data.get("title") or "").strip()
        if not title:
            return ""

        promotion_kind = cleaned_data.get("promotion_kind")
        promo_price = Promotion._format_offer_value(cleaned_data.get("promo_price"))
        gift_value = str(cleaned_data.get("benefit_value") or "").strip()
        period = cls._format_period(
            cleaned_data.get("start_date"),
            cleaned_data.get("end_date"),
        )

        if promotion_kind == Promotion.KIND_GIFT:
            parts = [f"Подарок к {title}"]
            if gift_value:
                parts.append(f"— {gift_value}")
            if period:
                parts.append(period)
            return " ".join(parts).strip() + "."

        if promotion_kind == Promotion.KIND_PREORDER:
            parts = [f"Предзаказ на {title}"]
            if promo_price:
                parts.append(promo_price)
            if period:
                parts.append(period)
            return " ".join(parts).strip() + "."

        parts = [f"Скидка на {title}"]
        if promo_price:
            parts.append(promo_price)
        if period:
            parts.append(period)
        return " ".join(parts).strip() + "."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["benefit_value"].label = "Подарок"
        self.fields["benefit_value"].help_text = (
            "Заполняй только для акций с подарком. "
            "Например: Наушники, сертификат или набор аксессуаров."
        )
        self.fields["cta_label"].help_text = (
            "Текст кнопки на странице акции. "
            "Например: Открыть условия, Перейти к товару, Смотреть предложение."
        )
        self.fields["cta_url"].help_text = (
            "Ссылка, куда ведёт кнопка на странице акции. "
            "Если ссылка заполнена, а текст кнопки нет, портал подставит «Открыть акцию»."
        )
        self.fields["is_featured"].help_text = (
            "Такие акции поднимаются выше в списке и считаются более приоритетными."
        )
        self.fields["is_published"].help_text = (
            "Главный переключатель публикации. Даже при включённом переключателе акция "
            "не показывается после даты окончания."
        )
        self.fields["start_date"].help_text = (
            "До этой даты акция считается будущей, но уже может отображаться в разделе «Акции»."
        )
        self.fields["end_date"].help_text = (
            "Акция видна по эту дату включительно и автоматически исчезает с сайта на следующий день. "
            "Оставляй поле пустым только для действительно бессрочной акции."
        )
        self.fields["sync_with_source"].help_text = (
            "Импорт из Google-таблицы перезаписывает название, тип, цены, даты и публикацию. "
            "Выключи синхронизацию перед ручной правкой этих данных."
        )
        if not self.instance.pk:
            self.fields["sync_with_source"].initial = False

    class Meta:
        model = Promotion
        fields = "__all__"
        widgets = {
            "promotion_kind": forms.Select(attrs={"size": "1"}),
            "summary": RichTextToolbarWidget(attrs={"rows": 5}),
            "details": RichTextToolbarWidget(attrs={"rows": 10}),
        }

    def clean(self):
        cleaned_data = super().clean()
        promotion_kind = cleaned_data.get("promotion_kind")
        promo_price = str(
            cleaned_data.get("promo_price", getattr(self.instance, "promo_price", "")) or ""
        ).strip()
        benefit_value = str(
            cleaned_data.get("benefit_value", getattr(self.instance, "benefit_value", "")) or ""
        ).strip()
        start_date = cleaned_data.get("start_date", getattr(self.instance, "start_date", None))
        end_date = cleaned_data.get("end_date", getattr(self.instance, "end_date", None))

        if "promo_price" in self.fields and promotion_kind == Promotion.KIND_PROMO_PRICE:
            if not promo_price:
                self.add_error("promo_price", "Для акции со скидкой укажи промоцену.")

        if (
            "benefit_value" in self.fields
            and promotion_kind == Promotion.KIND_GIFT
            and not benefit_value
        ):
            self.add_error("benefit_value", "Для акции с подарком опиши, что получает клиент.")

        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "Дата окончания не может быть раньше даты начала.")

        summary = str(cleaned_data.get("summary") or "").strip()
        if "summary" in self.fields and not summary:
            cleaned_data["summary"] = self.build_auto_summary(cleaned_data)

        return cleaned_data


def format_import_result(source, result, *, preview=False):
    prefix = "Проверка: " if preview else ""
    return (
        f"{prefix}{source.name}: создано {result.created}, "
        f"обновлено {result.updated}, "
        f"пропущено {result.skipped}, "
        f"дубликатов {result.duplicates}, "
        f"снято с публикации {result.unpublished}."
    )


def show_import_warnings(request, source, result):
    for warning in result.warnings:
        messages.warning(request, f"{source.name}: {warning}")


@admin.action(description="Импортировать акции из выбранных источников")
def import_selected_sources(modeladmin, request, queryset):
    imported = 0

    for source in queryset:
        try:
            result = import_promotions_from_source(source)
        except Exception as exc:
            messages.error(request, f"{source.name}: {exc}")
            continue

        imported += 1
        messages.success(request, format_import_result(source, result))
        show_import_warnings(request, source, result)

    if not imported:
        messages.warning(request, "Импорт не был выполнен ни для одного источника.")


@admin.action(description="Проверить импорт без сохранения")
def preview_selected_sources(modeladmin, request, queryset):
    checked = 0

    for source in queryset:
        try:
            result = preview_promotions_from_source(source)
        except Exception as exc:
            messages.error(request, f"Проверка {source.name}: {exc}")
            continue

        checked += 1
        messages.info(request, format_import_result(source, result, preview=True))
        show_import_warnings(request, source, result)

    if not checked:
        messages.warning(request, "Проверка не была выполнена ни для одного источника.")


class PromotionLifecycleFilter(admin.SimpleListFilter):
    title = "Фактический статус"
    parameter_name = "lifecycle"

    def lookups(self, request, model_admin):
        return (
            ("active", "Действует"),
            ("upcoming", "Скоро начнётся"),
            ("finished", "Завершена"),
            ("hidden", "Скрыта вручную"),
            ("open_ended", "Без даты окончания"),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        if self.value() == "active":
            return queryset.filter(is_published=True).active_on(today)
        if self.value() == "upcoming":
            return queryset.filter(is_published=True).upcoming_on(today)
        if self.value() == "finished":
            return queryset.finished_before(today)
        if self.value() == "hidden":
            return queryset.filter(is_published=False).not_expired(today)
        if self.value() == "open_ended":
            return queryset.filter(end_date__isnull=True)
        return queryset


@admin.register(PromotionSource)
class PromotionSourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "import_health",
        "import_mode",
        "is_active",
        "last_imported_at",
        "last_import_error_short",
        "resolved_gid",
    )
    list_filter = ("is_active", "auto_publish_imported", "archive_missing_on_import")
    search_fields = ("name", "sheet_url")
    actions = [preview_selected_sources, import_selected_sources]
    readonly_fields = (
        "import_url_preview",
        "import_history_link",
        "last_imported_at",
        "last_import_error",
    )
    fieldsets = (
        (
            "Основная информация",
            {
                "fields": ("name", "is_active"),
            },
        ),
        (
            "Подключение к таблице",
            {
                "fields": (
                    "sheet_url",
                    "import_mode",
                    "worksheet_gid",
                    "header_row",
                    "worksheets_to_import",
                    "import_url_preview",
                ),
                "description": (
                    "Для первого этапа таблица должна быть доступна по ссылке. "
                    "Можно вставить обычную ссылку на Google Sheets или прямую CSV-ссылку. "
                    "Для стабильного обновления строк рекомендуется колонка «ID» или «Код акции»."
                ),
            },
        ),
        (
            "Как импортировать",
            {
                "fields": (
                    "auto_publish_imported",
                    "archive_missing_on_import",
                    "minimum_expected_rows",
                    "max_missing_percent",
                ),
                "description": (
                    "Перед первым импортом запустите действие «Проверить импорт без сохранения»: "
                    "оно покажет дубликаты, конфликты и ожидаемые изменения. "
                    "Защитные пороги останавливают подозрительно пустую или неполную выгрузку."
                ),
            },
        ),
        (
            "Состояние импорта",
            {
                "fields": (
                    "import_history_link",
                    "last_imported_at",
                    "last_import_error",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Ссылка импорта, которую использует портал")
    def import_url_preview(self, obj):
        return obj.import_url if obj and obj.pk else "Появится после сохранения источника."

    @admin.display(description="История запусков")
    def import_history_link(self, obj):
        if not obj or not obj.pk:
            return "Появится после сохранения источника."
        url = reverse("admin:promotions_promotionimportrun_changelist")
        return format_html(
            '<a href="{}?source__id__exact={}">Открыть историю этого источника</a>',
            url,
            obj.pk,
        )

    @admin.display(description="Коротко об ошибке")
    def last_import_error_short(self, obj):
        if not obj.last_import_error:
            return "Ошибок нет"
        return obj.last_import_error[:60]

    @admin.display(description="Состояние")
    def import_health(self, obj):
        if not obj.is_active:
            css_class, label = "is-draft", "Отключён"
        elif obj.last_import_error:
            css_class, label = "is-finished", "Ошибка"
        elif not obj.last_imported_at:
            css_class, label = "is-upcoming", "Ещё не запускался"
        elif obj.last_imported_at < timezone.now() - timedelta(hours=24):
            css_class, label = "is-upcoming", "Давно не обновлялся"
        else:
            css_class, label = "is-live", "Работает"
        return format_html(
            '<span class="admin-status-badge {}">{}</span>',
            css_class,
            label,
        )


@admin.register(PromotionImportRun)
class PromotionImportRunAdmin(admin.ModelAdmin):
    list_display = (
        "started_at",
        "source",
        "run_mode",
        "status_badge",
        "result_summary",
        "duration_display",
    )
    list_filter = ("status", "is_dry_run", "source", "started_at")
    search_fields = ("source__name", "error")
    list_select_related = ("source",)
    date_hierarchy = "started_at"
    ordering = ("-started_at",)
    readonly_fields = (
        "source",
        "is_dry_run",
        "status",
        "created_count",
        "updated_count",
        "skipped_count",
        "unpublished_count",
        "duplicate_count",
        "warnings",
        "error",
        "started_at",
        "finished_at",
        "duration_display",
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "title": "История импорта акций",
        }
        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Режим")
    def run_mode(self, obj):
        return "Проверка" if obj.is_dry_run else "Импорт"

    @admin.display(description="Статус")
    def status_badge(self, obj):
        styles = {
            PromotionImportRun.STATUS_RUNNING: ("is-upcoming", "Выполняется"),
            PromotionImportRun.STATUS_SUCCESS: ("is-live", "Успешно"),
            PromotionImportRun.STATUS_ERROR: ("is-finished", "Ошибка"),
        }
        css_class, label = styles[obj.status]
        return format_html(
            '<span class="admin-status-badge {}">{}</span>',
            css_class,
            label,
        )

    @admin.display(description="Результат")
    def result_summary(self, obj):
        if obj.status == PromotionImportRun.STATUS_ERROR:
            return obj.error[:80] or "Ошибка без описания"
        if obj.status == PromotionImportRun.STATUS_RUNNING:
            return "Ожидание завершения"
        return (
            f"+{obj.created_count} / ~{obj.updated_count} / "
            f"−{obj.unpublished_count}; пропущено {obj.skipped_count}"
        )

    @admin.display(description="Длительность")
    def duration_display(self, obj):
        seconds = obj.duration_seconds
        if seconds is None:
            return "—"
        return f"{seconds:.2f} с"


@admin.register(Promotion)
class PromotionAdmin(
    AdminDuplicateMixin,
    AdminTemplatesAndFiltersMixin,
    AdminPresentationMixin,
    admin.ModelAdmin,
):
    form = PromotionAdminForm
    image_recommendation = (1600, 900)
    template_presets = (
        {
            "key": "discount",
            "label": "Создать: акция со скидкой",
            "initial": {
                "promotion_kind": "promo_price",
                "badge": "Скидка",
                "title": "Новая акция со скидкой",
            },
        },
        {
            "key": "gift",
            "label": "Создать: акция с подарком",
            "initial": {
                "promotion_kind": "gift",
                "badge": "Подарок",
                "title": "Новая акция с подарком",
            },
        },
    )
    quick_filters = (
        {"label": "Все", "key": "lifecycle", "value": ""},
        {"label": "Действуют", "key": "lifecycle", "value": "active"},
        {"label": "Скоро", "key": "lifecycle", "value": "upcoming"},
        {"label": "Завершены", "key": "lifecycle", "value": "finished"},
        {"label": "Скрытые", "key": "lifecycle", "value": "hidden"},
        {"label": "Скидка", "key": "promotion_kind__exact", "value": "promo_price"},
        {"label": "Подарок", "key": "promotion_kind__exact", "value": "gift"},
        {"label": "Без изображения", "key": "cover_image__isnull", "value": "True"},
        {"label": "Важные", "key": "is_featured__exact", "value": "1"},
    )
    list_display = (
        "cover_thumb",
        "title",
        "lifecycle_badge",
        "promotion_kind",
        "badge",
        "brand",
        "is_published",
        "formatted_promo_price_admin",
        "formatted_benefit_value_admin",
        "start_date",
        "end_date",
        "is_featured",
        "sync_with_source",
        "public_link",
    )
    list_display_links = ("title",)
    list_filter = (
        PromotionLifecycleFilter,
        "promotion_kind",
        "is_published",
        "is_featured",
        "sync_with_source",
        "brand",
        "category",
        "source",
    )
    search_fields = (
        "title",
        "summary",
        "details",
        "brand",
        "category",
        "promo_code",
    )
    list_editable = (
        "promotion_kind",
        "start_date",
        "end_date",
        "is_published",
        "is_featured",
        "sync_with_source",
    )
    readonly_fields = (
        "cover_preview",
        "card_preview",
        "public_link",
        "duplicate_link",
        "history_link",
        "created_at",
        "updated_at",
        "imported_at",
        "source",
        "source_row_key",
        "lifecycle_badge",
    )
    actions = (
        "set_kind_promo_price",
        "set_kind_gift",
        "set_kind_preorder",
        "clear_kind",
        "publish_selected",
        "unpublish_selected",
        "unpublish_finished_selected",
        "duplicate_selected",
    )
    fieldsets = (
        (
            "1. Основа акции",
            {
                "fields": (
                    "title",
                    "promotion_kind",
                ),
            },
        ),
        (
            "2. Параметры акции",
            {
                "fields": (
                    "brand",
                    "category",
                    "promo_price",
                    "benefit_value",
                    "promo_code",
                    "start_date",
                    "end_date",
                    "sort_order",
                ),
                "description": "Поле «Подарок» показывается только для акций с подарком.",
            },
        ),
        (
            "3. Как увидит сотрудник",
            {
                "fields": (
                    "badge",
                    ("cover_image", "cover_preview"),
                    "card_preview",
                    "summary",
                    "details",
                ),
                "description": (
                    "Краткое описание можно не писать вручную: портал сам соберёт шаблонный текст "
                    "по типу акции, названию, цене, подарку и датам."
                ),
            },
        ),
        (
            "4. Кнопка и публикация",
            {
                "fields": (
                    "cta_label",
                    "cta_url",
                    "is_featured",
                    "is_published",
                    "lifecycle_badge",
                    "public_link",
                    "duplicate_link",
                    "history_link",
                    "sync_with_source",
                ),
                "description": (
                    "Кнопка показывается на детальной странице акции. "
                    "Здесь же настраивается, видна ли акция на сайте и можно ли обновлять её из импорта."
                ),
            },
        ),
        (
            "Откуда приехала акция",
            {
                "fields": ("source", "source_row_key", "imported_at"),
                "classes": ("collapse",),
            },
        ),
        (
            "Служебная информация",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    class Media:
        css = {
            "all": ("css/admin-enhancements.css",),
        }
        js = ("js/admin-enhancements.js", "js/promotion-admin.js")

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "promotion_kind" and formfield:
            formfield.widget.attrs["size"] = "1"
        return formfield

    @admin.display(description="Как будет выглядеть карточка")
    def card_preview(self, obj):
        description = strip_tags(obj.benefit_summary or obj.card_summary or obj.summary or "").strip()
        chips = [obj.badge, obj.brand]
        footer = [obj.formatted_promo_price, obj.formatted_benefit_value]
        return render_admin_card_preview(
            obj.title,
            description[:180],
            chips=chips,
            footer=footer,
        )

    @admin.display(description="Тип")
    def promotion_kind_badge(self, obj):
        colors = {
            "promo_price": "is-orange",
            "gift": "is-blue",
            "preorder": "is-violet",
        }
        label = obj.get_promotion_kind_display() if obj.promotion_kind else "Не указан"
        return format_html(
            '<span class="admin-type-badge {}">{}</span>',
            colors.get(obj.promotion_kind, "is-violet"),
            label,
        )

    @admin.display(description="Промоцена")
    def formatted_promo_price_admin(self, obj):
        return obj.formatted_promo_price or "—"

    @admin.display(description="Выгода")
    def formatted_benefit_value_admin(self, obj):
        return obj.formatted_benefit_value or "—"

    def _set_promotion_kind(self, request, queryset, kind, label):
        updated = queryset.update(promotion_kind=kind, updated_at=timezone.now())
        self.message_user(
            request,
            f"Для выбранных акций установлен тип «{label}»: {updated}.",
            level=messages.SUCCESS,
        )

    @admin.display(description="Фактический статус")
    def lifecycle_badge(self, obj):
        statuses = {
            "active": ("is-live", "Действует"),
            "upcoming": ("is-upcoming", "Скоро начнётся"),
            "finished": ("is-finished", "Завершена"),
            "hidden": ("is-draft", "Скрыта вручную"),
        }
        css_class, label = statuses[obj.lifecycle_status]
        return format_html(
            '<span class="admin-status-badge {}">{}</span>',
            css_class,
            label,
        )

    @admin.display(description="Ссылка")
    def public_link(self, obj):
        if not getattr(obj, "pk", None):
            return "Сначала сохрани запись."
        if obj.lifecycle_status == "finished":
            return "Срок завершён — на сайте скрыта."
        if obj.lifecycle_status == "hidden":
            return "Публикация выключена."
        if obj.is_preorder:
            return "Предзаказы не показываются в разделе акций."
        return super().public_link(obj)

    @admin.action(description="Назначить тип: промоцена / скидка")
    def set_kind_promo_price(self, request, queryset):
        self._set_promotion_kind(
            request,
            queryset,
            Promotion.KIND_PROMO_PRICE,
            "Промоцена / скидка / промо",
        )

    @admin.action(description="Назначить тип: подарок")
    def set_kind_gift(self, request, queryset):
        self._set_promotion_kind(request, queryset, Promotion.KIND_GIFT, "Подарок")

    @admin.action(description="Назначить тип: предзаказ")
    def set_kind_preorder(self, request, queryset):
        self._set_promotion_kind(request, queryset, Promotion.KIND_PREORDER, "Предзаказ")

    @admin.action(description="Очистить тип акции")
    def clear_kind(self, request, queryset):
        self._set_promotion_kind(request, queryset, "", "Не указан")

    @admin.action(description="Опубликовать выбранные акции")
    def publish_selected(self, request, queryset):
        today = timezone.localdate()
        finished = queryset.finished_before(today).count()
        updated = queryset.not_expired(today).update(is_published=True)
        self.message_user(request, f"Опубликовано акций: {updated}.", level=messages.SUCCESS)
        if finished:
            self.message_user(
                request,
                f"Завершённые акции не опубликованы: {finished}. Сначала продли дату окончания.",
                level=messages.WARNING,
            )

    @admin.action(description="Скрыть выбранные акции")
    def unpublish_selected(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"Скрыто акций: {updated}.", level=messages.SUCCESS)

    @admin.action(description="Снять с публикации выбранные завершённые акции")
    def unpublish_finished_selected(self, request, queryset):
        updated = queryset.finished_before().filter(is_published=True).update(is_published=False)
        self.message_user(
            request,
            f"Снято с публикации завершённых акций: {updated}.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Создать копии выбранных акций")
    def duplicate_selected(self, request, queryset):
        duplicated = 0

        for promotion in queryset:
            self.clone_object(request, promotion)
            duplicated += 1

        self.message_user(request, f"Создано копий акций: {duplicated}.", level=messages.SUCCESS)
