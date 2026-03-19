from django import forms
from django.contrib import admin, messages

from catalog.widgets import RichTextToolbarWidget
from telegram_bot.services import send_learning_notification, telegram_enabled

from .models import (
    LearningBlock,
    LearningMaterial,
    ProductDescriptionImage,
    ProductFeature,
    ProductReviewImage,
    ProductSalesScript,
    ProductSpecification,
)


class LearningMaterialAdminForm(forms.ModelForm):
    send_telegram_notification = forms.BooleanField(
        required=False,
        label="Отправить в Telegram после сохранения",
        help_text="Материал уйдет всем пользователям, которые уже запускали бота.",
    )

    class Meta:
        model = LearningMaterial
        fields = "__all__"
        widgets = {
            "content": RichTextToolbarWidget(),
            "product_full_description": RichTextToolbarWidget(),
            "product_text_review": RichTextToolbarWidget(),
            "product_short_summary": RichTextToolbarWidget(attrs={"rows": 5}),
        }


class LearningBlockAdminForm(forms.ModelForm):
    class Meta:
        model = LearningBlock
        fields = "__all__"
        widgets = {
            "text": RichTextToolbarWidget(),
        }


class ProductFeatureAdminForm(forms.ModelForm):
    class Meta:
        model = ProductFeature
        fields = "__all__"
        widgets = {
            "description": RichTextToolbarWidget(attrs={"rows": 5}),
            "client_pitch": RichTextToolbarWidget(attrs={"rows": 4}),
        }


class ProductSalesScriptAdminForm(forms.ModelForm):
    class Meta:
        model = ProductSalesScript
        fields = "__all__"
        widgets = {
            "script_text": RichTextToolbarWidget(attrs={"rows": 4}),
        }


class ProductDescriptionImageInline(admin.StackedInline):
    model = ProductDescriptionImage
    extra = 1
    classes = ("product-only", "section-description-images")
    verbose_name = "Изображение полного описания"
    verbose_name_plural = "Изображения для полного описания"
    fieldsets = (
        (
            "Изображение",
            {
                "fields": ("sort_order", "image", "caption"),
                "description": "Добавь изображения, которые идут после полного описания.",
            },
        ),
    )


class ProductReviewImageInline(admin.StackedInline):
    model = ProductReviewImage
    extra = 1
    classes = ("product-only", "section-review-images")
    verbose_name = "Изображение текстового обзора"
    verbose_name_plural = "Изображения для текстового обзора"
    fieldsets = (
        (
            "Изображение",
            {
                "fields": ("sort_order", "image", "caption"),
                "description": "Добавь изображения, которые идут после текстового обзора.",
            },
        ),
    )


class ProductFeatureInline(admin.StackedInline):
    model = ProductFeature
    form = ProductFeatureAdminForm
    extra = 1
    classes = ("product-only", "section-product-features")
    verbose_name = "Фишка товара"
    verbose_name_plural = "5. Фишки и как преподносить клиенту"
    fieldsets = (
        (
            "Фишка",
            {
                "fields": ("sort_order", "title", "description", "client_pitch"),
                "description": "Сначала название и описание фишки, ниже фраза в формате цитаты: как это подать клиенту.",
            },
        ),
    )


class ProductSalesScriptInline(admin.StackedInline):
    model = ProductSalesScript
    form = ProductSalesScriptAdminForm
    extra = 1
    classes = ("product-only", "section-product-scripts")
    verbose_name = "Скрипт продаж"
    verbose_name_plural = "6. Скрипты продаж"
    fieldsets = (
        (
            "Скрипт",
            {
                "fields": ("sort_order", "title", "script_text"),
                "description": "Укажи название скрипта и сам текст, который будет показан отдельной цитатой.",
            },
        ),
    )


class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 3
    classes = ("product-only", "section-product-specifications")
    verbose_name = "Характеристика"
    verbose_name_plural = "7. Характеристики"
    fields = ("sort_order", "name", "value")


class LearningBlockInline(admin.StackedInline):
    model = LearningBlock
    form = LearningBlockAdminForm
    extra = 1
    classes = ("general-only", "section-general-blocks")
    verbose_name = "Блок содержимого"
    verbose_name_plural = "Дополнительные блоки для обычного материала"
    fieldsets = (
        (
            "Основное",
            {
                "fields": ("sort_order", "block_type", "title", "caption"),
                "description": "Выбери, что именно нужно вставить в материал.",
            },
        ),
        (
            "Содержимое блока",
            {
                "fields": ("text", "image", "video_url", "document"),
            },
        ),
    )


@admin.register(LearningMaterial)
class LearningMaterialAdmin(admin.ModelAdmin):
    form = LearningMaterialAdminForm
    change_form_template = "admin/learning/learningmaterial/change_form.html"
    list_display = ("title", "material_type", "updated_at", "is_published")
    list_filter = ("material_type", "is_published", "updated_at")
    search_fields = (
        "title",
        "summary",
        "content",
        "product_full_description",
        "product_text_review",
        "product_short_summary",
    )
    list_editable = ("is_published",)
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = (
        "brands",
        "categories",
        "areas",
        "feature_tags",
        "telegram_target_groups",
    )
    actions = ("send_selected_to_telegram",)
    inlines = [
        ProductDescriptionImageInline,
        ProductReviewImageInline,
        ProductFeatureInline,
        ProductSalesScriptInline,
        ProductSpecificationInline,
        LearningBlockInline,
    ]
    fieldsets = (
        (
            "1. Краткое описание для превью и название",
            {
                "fields": ("title", "summary", "cover_image"),
                "classes": ("article-section", "section-preview"),
                "description": "Сначала название, затем короткое описание для карточки и списка материалов.",
            },
        ),
        (
            "2. Полное описание",
            {
                "fields": ("product_full_description",),
                "classes": ("article-section", "product-only", "section-full-description"),
                "description": "Основной текст о товаре. Изображения этого раздела добавляются сразу следующим блоком.",
            },
        ),
        (
            "3. Видеообзор",
            {
                "fields": ("product_video_review_url",),
                "classes": ("article-section", "product-only", "section-video-review"),
                "description": "Вставь обычную ссылку на YouTube. На сайте видео будет встроено и красиво выровнено по центру.",
            },
        ),
        (
            "4. Обзор текстом",
            {
                "fields": ("product_text_review",),
                "classes": ("article-section", "product-only", "section-text-review"),
                "description": "Здесь размещается подробный обзор текста. Изображения к нему добавляются следующим блоком.",
            },
        ),
        (
            "Тип материала и публикация",
            {
                "fields": (
                    "material_type",
                    "is_published",
                    "send_telegram_notification",
                    "telegram_audience",
                    "telegram_target_groups",
                ),
                "classes": ("article-section", "section-material-mode"),
                "description": "Если включить отправку, опубликованный материал уйдет всем пользователям Telegram-бота.",
            },
        ),
        (
            "8. Краткое резюмирование",
            {
                "fields": ("product_short_summary",),
                "classes": ("article-section", "product-only", "section-short-summary"),
                "description": "Коротко подведи итог: кому подходит товар и в чем его главная ценность.",
            },
        ),
        (
            "Связи с брендами, темами и метками",
            {
                "fields": (
                    "brands",
                    "categories",
                    "areas",
                    "feature_tags",
                ),
                "classes": ("article-section", "section-links"),
            },
        ),
        (
            "Обычный режим для не товарных материалов",
            {
                "fields": ("content",),
                "classes": ("article-section", "general-only", "section-general-content"),
                "description": "Этот раздел нужен для процессов, инструкций и других материалов, которые не оформляются как карточка товара.",
            },
        ),
        (
            "Служебная информация",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse", "section-system"),
            },
        ),
    )

    class Media:
        css = {
            "all": ("css/learning-product-admin.css",),
        }
        js = ("js/learning-product-admin.js",)

    @admin.action(description="Отправить выбранные материалы в Telegram")
    def send_selected_to_telegram(self, request, queryset):
        if not telegram_enabled():
            self.message_user(
                request,
                "Токен Telegram-бота не настроен.",
                level=messages.ERROR,
            )
            return

        total_sent = 0
        total_failed = 0
        skipped = 0

        for material in queryset:
            if not material.is_published:
                skipped += 1
                continue
            report = send_learning_notification(material)
            total_sent += report.sent
            total_failed += report.failed

        self.message_user(
            request,
            "Рассылка материалов завершена. "
            f"Успешно: {total_sent}, не удалось: {total_failed}, пропущено неопубликованных: {skipped}.",
            level=messages.SUCCESS if total_sent else messages.WARNING,
        )

    @staticmethod
    def _has_class(item, class_name):
        return class_name in (item.classes or "").split()

    def _find_fieldset(self, adminform, class_name):
        for fieldset in adminform:
            if self._has_class(fieldset, class_name):
                return fieldset
        return None

    def _find_inline(self, inline_admin_formsets, class_name):
        for inline_admin_formset in inline_admin_formsets:
            if self._has_class(inline_admin_formset, class_name):
                return inline_admin_formset
        return None

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        adminform = context.get("adminform")
        inline_admin_formsets = context.get("inline_admin_formsets", [])

        if adminform:
            context.update(
                {
                    "preview_fieldset": self._find_fieldset(adminform, "section-preview"),
                    "full_description_fieldset": self._find_fieldset(
                        adminform, "section-full-description"
                    ),
                    "video_review_fieldset": self._find_fieldset(
                        adminform, "section-video-review"
                    ),
                    "text_review_fieldset": self._find_fieldset(
                        adminform, "section-text-review"
                    ),
                    "short_summary_fieldset": self._find_fieldset(
                        adminform, "section-short-summary"
                    ),
                    "material_mode_fieldset": self._find_fieldset(
                        adminform, "section-material-mode"
                    ),
                    "links_fieldset": self._find_fieldset(
                        adminform, "section-links"
                    ),
                    "general_content_fieldset": self._find_fieldset(
                        adminform, "section-general-content"
                    ),
                    "system_fieldset": self._find_fieldset(adminform, "section-system"),
                    "description_images_inline": self._find_inline(
                        inline_admin_formsets, "section-description-images"
                    ),
                    "review_images_inline": self._find_inline(
                        inline_admin_formsets, "section-review-images"
                    ),
                    "product_features_inline": self._find_inline(
                        inline_admin_formsets, "section-product-features"
                    ),
                    "product_scripts_inline": self._find_inline(
                        inline_admin_formsets, "section-product-scripts"
                    ),
                    "product_specs_inline": self._find_inline(
                        inline_admin_formsets, "section-product-specifications"
                    ),
                    "general_blocks_inline": self._find_inline(
                        inline_admin_formsets, "section-general-blocks"
                    ),
                }
            )

        return super().render_change_form(
            request,
            context,
            add=add,
            change=change,
            form_url=form_url,
            obj=obj,
        )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        if not form.cleaned_data.get("send_telegram_notification"):
            return

        if not telegram_enabled():
            self.message_user(
                request,
                "Материал сохранен, но токен Telegram-бота не настроен.",
                level=messages.WARNING,
            )
            return

        if not form.instance.is_published:
            self.message_user(
                request,
                "Материал сохранен, но не отправлен: сначала включи показ на сайте.",
                level=messages.WARNING,
            )
            return

        report = send_learning_notification(form.instance)
        self.message_user(
            request,
            f"Материал отправлен в Telegram. Успешно: {report.sent}, не удалось: {report.failed}.",
            level=messages.SUCCESS if report.sent else messages.WARNING,
        )
