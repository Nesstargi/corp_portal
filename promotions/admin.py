from django import forms
from django.contrib import admin, messages

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
class PromotionAdmin(admin.ModelAdmin):
    form = PromotionAdminForm
    list_display = (
        "title",
        "promotion_kind",
        "badge",
        "brand",
        "category",
        "promo_price",
        "benefit_value",
        "start_date",
        "end_date",
        "is_featured",
        "is_published",
        "sync_with_source",
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
    list_editable = ("is_featured", "is_published", "sync_with_source")
    readonly_fields = ("created_at", "updated_at", "imported_at", "source", "source_row_key")
    fieldsets = (
        (
            "Что увидит сотрудник",
            {
                "fields": (
                    "title",
                    "promotion_kind",
                    "badge",
                    "cover_image",
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
