from collections import defaultdict

from django import forms
from django.contrib import admin, messages
from django.forms.models import BaseInlineFormSet
from django.utils.html import format_html
from django.utils.html import strip_tags

from catalog.admin_mixins import (
    AdminDuplicateMixin,
    AdminPresentationMixin,
    AdminTemplatesAndFiltersMixin,
    render_admin_card_preview,
)
from catalog.models import ProductCategoryCharacteristic
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
        help_text="Материал можно отправить личным подписчикам, Telegram-группам или выбранной аудитории.",
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

    def clean(self):
        cleaned_data = super().clean()
        material_type = cleaned_data.get("material_type")

        if material_type == "product":
            required_fields = {
                "summary": "Добавь краткое описание для карточки товара.",
                "product_full_description": "Добавь полное описание товара.",
                "product_short_summary": "Добавь краткое резюмирование.",
            }
            for field_name, message in required_fields.items():
                if not str(cleaned_data.get(field_name) or "").strip():
                    self.add_error(field_name, message)

            categories = cleaned_data.get("categories")
            if not categories:
                self.add_error("categories", "Выбери хотя бы одну категорию товара.")

        if cleaned_data.get("send_telegram_notification"):
            audience = cleaned_data.get("telegram_audience")
            groups = cleaned_data.get("telegram_target_groups")
            subscribers = cleaned_data.get("telegram_target_subscribers")
            group_chats = cleaned_data.get("telegram_target_group_chats")
            collections = cleaned_data.get("telegram_target_chat_collections")
            if audience == "custom":
                has_groups = bool(groups and groups.exists())
                has_subscribers = bool(subscribers and subscribers.exists())
                has_group_chats = bool(group_chats and group_chats.exists())
                has_collections = bool(collections and collections.exists())
                if not any([has_groups, has_subscribers, has_group_chats, has_collections]):
                    self.add_error(
                        "telegram_target_groups",
                        "Для выбранной аудитории укажи хотя бы одного получателя, группу подписчиков, Telegram-группу или объединение групп.",
                    )

        return cleaned_data


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


class ProductSpecificationInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        material_type = str(
            self.data.get("material_type") or getattr(self.instance, "material_type", "")
        )
        if material_type != "product":
            return

        filled_specifications = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue

            characteristic = form.cleaned_data.get("characteristic")
            value = str(form.cleaned_data.get("value") or "").strip()

            if characteristic and value:
                filled_specifications += 1
                continue

            if characteristic and not value:
                form.add_error("value", "Укажи значение характеристики.")
            elif value and not characteristic:
                form.add_error("characteristic", "Выбери характеристику из базы.")

        if filled_specifications == 0:
            raise forms.ValidationError(
                "Для товарного материала добавь хотя бы одну характеристику со значением."
            )


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
    formset = ProductSpecificationInlineFormSet
    extra = 0
    classes = ("product-only", "section-product-specifications")
    verbose_name = "Характеристика"
    verbose_name_plural = "7. Характеристики"
    fields = ("sort_order", "characteristic", "value")
    autocomplete_fields = ("characteristic",)


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
class LearningMaterialAdmin(
    AdminDuplicateMixin,
    AdminTemplatesAndFiltersMixin,
    AdminPresentationMixin,
    admin.ModelAdmin,
):
    form = LearningMaterialAdminForm
    change_form_template = "admin/learning/learningmaterial/change_form.html"
    image_recommendation = (1600, 900)
    template_presets = (
        {
            "key": "product",
            "label": "Создать: товар",
            "initial": {
                "material_type": "product",
                "title": "Новый товарный материал",
                "summary": "Короткое описание товара для карточки.",
            },
        },
        {
            "key": "process",
            "label": "Создать: процесс",
            "initial": {
                "material_type": "process",
                "title": "Новый процесс",
                "summary": "Коротко опиши, чему посвящён материал.",
            },
        },
        {
            "key": "instruction",
            "label": "Создать: инструкция",
            "initial": {
                "material_type": "instruction",
                "title": "Новая инструкция",
                "summary": "Коротко опиши, что сотрудник найдёт внутри.",
            },
        },
    )
    quick_filters = (
        {"label": "Все", "key": "is_published__exact", "value": ""},
        {"label": "Опубликованные", "key": "is_published__exact", "value": "1"},
        {"label": "Скрытые", "key": "is_published__exact", "value": "0"},
        {"label": "Товары", "key": "material_type__exact", "value": "product"},
        {"label": "Процессы", "key": "material_type__exact", "value": "process"},
        {"label": "Без обложки", "key": "cover_image__isnull", "value": "True"},
    )
    list_display = (
        "cover_thumb",
        "title",
        "material_type_badge",
        "is_published",
        "updated_at",
        "public_link",
    )
    list_display_links = ("title",)
    list_editable = ("is_published",)
    list_filter = ("material_type", "is_published", "updated_at")
    search_fields = (
        "title",
        "summary",
        "content",
        "product_full_description",
        "product_text_review",
        "product_short_summary",
    )
    readonly_fields = (
        "cover_preview",
        "card_preview",
        "public_link",
        "duplicate_link",
        "history_link",
        "created_at",
        "updated_at",
    )
    filter_horizontal = (
        "brands",
        "categories",
        "areas",
        "feature_tags",
        "telegram_target_groups",
        "telegram_target_subscribers",
        "telegram_target_group_chats",
        "telegram_target_chat_collections",
    )
    actions = (
        "publish_selected",
        "unpublish_selected",
        "duplicate_selected",
        "send_selected_to_telegram",
    )
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
                "fields": ("title", "summary", ("cover_image", "cover_preview"), "card_preview"),
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
                    "public_link",
                    "duplicate_link",
                    "history_link",
                    "send_telegram_notification",
                    "telegram_audience",
                    "telegram_target_groups",
                    "telegram_target_subscribers",
                    "telegram_target_group_chats",
                    "telegram_target_chat_collections",
                ),
                "classes": ("article-section", "section-material-mode"),
                "description": (
                    "Если включить отправку, опубликованный материал можно направить "
                    "всем личным подписчикам, всем подписчикам вместе с Telegram-группами, "
                    "только Telegram-группам или только выбранной аудитории."
                ),
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
            "all": ("css/learning-product-admin.css", "css/admin-enhancements.css"),
        }
        js = ("js/admin-enhancements.js", "js/learning-product-admin.js")

    @admin.display(description="Как будет выглядеть карточка")
    def card_preview(self, obj):
        description = strip_tags(
            obj.summary
            or obj.product_short_summary
            or obj.product_full_description
            or obj.content
            or ""
        ).strip()
        chips = [obj.get_material_type_display()]
        if obj.pk:
            chips.extend(tag.name for tag in obj.feature_tags.all()[:2])
        return render_admin_card_preview(
            obj.title,
            description[:180],
            chips=chips,
        )

    @admin.display(description="Тип")
    def material_type_badge(self, obj):
        colors = {
            "product": "is-blue",
            "process": "is-green",
            "instruction": "is-violet",
            "promotion": "is-orange",
            "credit": "is-orange",
            "reference": "is-violet",
        }
        return format_html(
            '<span class="admin-type-badge {}">{}</span>',
            colors.get(obj.material_type, "is-violet"),
            obj.get_material_type_display(),
        )

    @admin.action(description="Опубликовать выбранные материалы")
    def publish_selected(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"Опубликовано материалов: {updated}.", level=messages.SUCCESS)

    @admin.action(description="Скрыть выбранные материалы")
    def unpublish_selected(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"Скрыто материалов: {updated}.", level=messages.SUCCESS)

    @admin.action(description="Создать копии выбранных материалов")
    def duplicate_selected(self, request, queryset):
        duplicated = 0

        for material in queryset:
            self.clone_object(request, material)
            duplicated += 1

        self.message_user(request, f"Создано копий материалов: {duplicated}.", level=messages.SUCCESS)

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
        category_characteristics_map = defaultdict(list)

        for link in (
            ProductCategoryCharacteristic.objects.select_related("characteristic")
            .order_by("category_id", "sort_order", "characteristic__name")
        ):
            category_characteristics_map[str(link.category_id)].append(
                {
                    "id": link.characteristic_id,
                    "name": link.characteristic.name,
                    "sort_order": link.sort_order,
                }
            )

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
                    "category_characteristics_map": dict(category_characteristics_map),
                }
            )

            product_specs_inline = context.get("product_specs_inline")
            if product_specs_inline:
                context["product_specs_prefix"] = product_specs_inline.formset.prefix

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

    def clone_related_objects(self, request, source, clone):
        related_sets = (
            ("product_description_images", "material"),
            ("product_review_images", "material"),
            ("product_features", "material"),
            ("product_sales_scripts", "material"),
            ("product_specifications", "material"),
            ("blocks", "material"),
        )

        for related_name, relation_field in related_sets:
            for item in getattr(source, related_name).all():
                item.pk = None
                setattr(item, relation_field, clone)
                item.save()

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "telegram_target_subscribers":
            from telegram_bot.models import TelegramSubscriber

            kwargs["queryset"] = TelegramSubscriber.objects.filter(
                chat_type=TelegramSubscriber.CHAT_TYPE_PRIVATE
            )
        elif db_field.name == "telegram_target_group_chats":
            from telegram_bot.models import TelegramSubscriber

            kwargs["queryset"] = TelegramSubscriber.objects.filter(
                chat_type__in=(
                    TelegramSubscriber.CHAT_TYPE_GROUP,
                    TelegramSubscriber.CHAT_TYPE_SUPERGROUP,
                )
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)
