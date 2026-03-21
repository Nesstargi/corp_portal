from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html, strip_tags

from catalog.admin_mixins import (
    AdminDuplicateMixin,
    AdminPresentationMixin,
    AdminTemplatesAndFiltersMixin,
    render_admin_card_preview,
)
from catalog.widgets import RichTextToolbarWidget

from .models import Promotion, PromotionSource
from .services import import_promotions_from_source


class PromotionAdminForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = "__all__"
        widgets = {
            "summary": RichTextToolbarWidget(attrs={"rows": 5}),
            "details": RichTextToolbarWidget(attrs={"rows": 10}),
        }

    def clean(self):
        cleaned_data = super().clean()
        promotion_kind = cleaned_data.get("promotion_kind")
        promo_price = str(cleaned_data.get("promo_price") or "").strip()
        benefit_value = str(cleaned_data.get("benefit_value") or "").strip()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if promotion_kind == Promotion.KIND_PROMO_PRICE:
            if not promo_price:
                self.add_error("promo_price", "Для акции со скидкой укажи промоцену.")
            if not benefit_value:
                self.add_error("benefit_value", "Для акции со скидкой укажи выгоду для клиента.")

        if promotion_kind == Promotion.KIND_GIFT and not benefit_value:
            self.add_error("benefit_value", "Для акции с подарком опиши, что получает клиент.")

        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "Дата окончания не может быть раньше даты начала.")

        return cleaned_data


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
        messages.success(
            request,
            (
                f"{source.name}: создано {result.created}, "
                f"обновлено {result.updated}, "
                f"пропущено {result.skipped}, "
                f"снято с публикации {result.unpublished}."
            ),
        )

    if not imported:
        messages.warning(request, "Импорт не был выполнен ни для одного источника.")


@admin.register(PromotionSource)
class PromotionSourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "import_mode",
        "is_active",
        "last_imported_at",
        "last_import_error_short",
        "resolved_gid",
    )
    list_filter = ("is_active", "auto_publish_imported", "archive_missing_on_import")
    search_fields = ("name", "sheet_url")
    actions = [import_selected_sources]
    readonly_fields = ("import_url_preview", "last_imported_at", "last_import_error")
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
                    "Можно вставить обычную ссылку на Google Sheets или прямую CSV-ссылку."
                ),
            },
        ),
        (
            "Как импортировать",
            {
                "fields": ("auto_publish_imported", "archive_missing_on_import"),
            },
        ),
        (
            "Состояние импорта",
            {
                "fields": ("last_imported_at", "last_import_error"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Ссылка импорта, которую использует портал")
    def import_url_preview(self, obj):
        return obj.import_url if obj and obj.pk else "Появится после сохранения источника."

    @admin.display(description="Коротко об ошибке")
    def last_import_error_short(self, obj):
        if not obj.last_import_error:
            return "Ошибок нет"
        return obj.last_import_error[:60]


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
        {"label": "Все", "key": "is_published__exact", "value": ""},
        {"label": "Опубликованные", "key": "is_published__exact", "value": "1"},
        {"label": "Скрытые", "key": "is_published__exact", "value": "0"},
        {"label": "Скидка", "key": "promotion_kind__exact", "value": "promo_price"},
        {"label": "Подарок", "key": "promotion_kind__exact", "value": "gift"},
        {"label": "Без изображения", "key": "cover_image__isnull", "value": "True"},
        {"label": "Важные", "key": "is_featured__exact", "value": "1"},
    )
    list_display = (
        "cover_thumb",
        "title",
        "promotion_kind_badge",
        "badge",
        "brand",
        "published_badge",
        "formatted_promo_price_admin",
        "formatted_benefit_value_admin",
        "start_date",
        "end_date",
        "is_featured",
        "sync_with_source",
        "public_link",
    )
    list_filter = (
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
    list_editable = ("is_featured", "sync_with_source")
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
    )
    actions = ("publish_selected", "unpublish_selected", "duplicate_selected")
    fieldsets = (
        (
            "Что увидит сотрудник",
            {
                "fields": (
                    "title",
                    "promotion_kind",
                    "badge",
                    ("cover_image", "cover_preview"),
                    "card_preview",
                    "summary",
                    "details",
                ),
            },
        ),
        (
            "Параметры акции",
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
            },
        ),
        (
            "Кнопка и публикация",
            {
                "fields": (
                    "cta_label",
                    "cta_url",
                    "is_featured",
                    "is_published",
                    "public_link",
                    "duplicate_link",
                    "history_link",
                    "sync_with_source",
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
        js = ("js/admin-enhancements.js",)

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

    @admin.action(description="Опубликовать выбранные акции")
    def publish_selected(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"Опубликовано акций: {updated}.", level=messages.SUCCESS)

    @admin.action(description="Скрыть выбранные акции")
    def unpublish_selected(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"Скрыто акций: {updated}.", level=messages.SUCCESS)

    @admin.action(description="Создать копии выбранных акций")
    def duplicate_selected(self, request, queryset):
        duplicated = 0

        for promotion in queryset:
            self.clone_object(request, promotion)
            duplicated += 1

        self.message_user(request, f"Создано копий акций: {duplicated}.", level=messages.SUCCESS)
