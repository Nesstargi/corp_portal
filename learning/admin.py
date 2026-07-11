from django import forms
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.forms.models import BaseInlineFormSet
from django.forms.widgets import ClearableFileInput
from django.http import HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.html import format_html_join
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

from catalog.admin_mixins import (
    AdminDuplicateMixin,
    AdminPresentationMixin,
    AdminTemplatesAndFiltersMixin,
    render_admin_card_preview,
)
from catalog.models import ProductCategoryCharacteristic, ProductCharacteristic
from catalog.widgets import RichTextToolbarWidget
from telegram_bot.models import TelegramSubscriber
from telegram_bot.services import (
    send_learning_notification,
    send_learning_notification_to_group_chats,
    send_learning_notification_to_private_subscribers,
    telegram_enabled,
)

from .models import (
    LearningBlock,
    LearningBlockGalleryImage,
    LearningMaterial,
    PresentationImport,
)
from .block_schema import (
    ADMIN_BLOCK_TYPE_KEYS,
    BLOCK_TYPE_DEFINITIONS,
    block_has_content,
    get_admin_block_schema,
    get_block_empty_message,
    normalize_block_items_data,
)
from .presentation_import import (
    PresentationImportError,
    build_ocr_html,
    build_slide_html,
    build_summary,
    extract_pptx_slides,
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
            "summary": RichTextToolbarWidget(attrs={"rows": 5}),
            "content": RichTextToolbarWidget(),
            "product_full_description": RichTextToolbarWidget(),
            "product_text_review": RichTextToolbarWidget(),
            "product_short_summary": RichTextToolbarWidget(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].label = "Название материала базы знаний"
        self.fields["summary"].label = "Краткое описание"
        self.fields["summary"].help_text = "Показывается в списке базы знаний и на главной странице."
        self.fields["material_type"].label = "Формат материала"
        self.fields["brands"].label = "Бренд"
        self.fields["categories"].label = "Категория товара"
        self.fields["feature_tags"].label = "Метки"
        self.fields["feature_tags"].help_text = (
            "Метки помогают находить и связывать материалы. Например: самоочистка или быстрая зарядка."
        )
        if not self.instance.pk:
            self.fields["is_published"].initial = False

    def clean(self):
        cleaned_data = super().clean()
        material_type = cleaned_data.get("material_type")

        if material_type == "product":
            if not str(cleaned_data.get("summary") or "").strip():
                self.add_error("summary", "Добавь краткое описание для карточки товара.")

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


class MultipleFileInput(ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if not data:
            return []

        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data]

        return [single_file_clean(data, initial)]


class BlockItemsWidget(forms.Textarea):
    def render(self, name, value, attrs=None, renderer=None):
        textarea = super().render(name, value, attrs=attrs, renderer=renderer)
        return mark_safe(
            '<div class="learning-block-items-root">'
            f"{textarea}"
            '<div class="learning-block-items-editor" data-block-items-editor></div>'
            "</div>"
        )


class LearningBlockAdminForm(forms.ModelForm):
    gallery_uploads = MultipleFileField(
        required=False,
        label="Добавить изображения в галерею",
        help_text="Можно выбрать сразу несколько файлов. На странице они соберутся в слайдер.",
    )

    class Meta:
        model = LearningBlock
        fields = "__all__"
        widgets = {
            "text": RichTextToolbarWidget(),
            "items_data": BlockItemsWidget(attrs={"class": "learning-block-items-json", "rows": 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        admin_choices = [
            (key, BLOCK_TYPE_DEFINITIONS[key]["label"])
            for key in ADMIN_BLOCK_TYPE_KEYS
        ]
        current_type = str(getattr(self.instance, "block_type", "") or "")
        if self.instance.pk and current_type not in ADMIN_BLOCK_TYPE_KEYS:
            legacy_labels = dict(LearningBlock.BLOCK_TYPE_CHOICES)
            admin_choices.append(
                (current_type, f"{legacy_labels.get(current_type, current_type)} — старый блок")
            )
        self.fields["block_type"].choices = admin_choices
        self.fields["block_type"].label = "Тип блока"
        self.fields["title"].label = "Заголовок секции"
        self.fields["title"].help_text = (
            "Необязательно. Например: Фишки модели, Скрипты продаж, Ключевые характеристики."
        )
        self.fields["caption"].label = "Короткая подпись"
        self.fields["caption"].help_text = "Необязательное пояснение под медиа или таблицей."
        self.fields["text"].help_text = (
            "Основной текст для обычного текстового блока или цитаты."
        )
        self.fields["items_data"].required = False
        self.fields["items_data"].help_text = (
            "Для фишек, скриптов продаж, характеристик и таблиц ниже появится удобный редактор."
        )
        self.fields["video_url"].help_text = "Вставь ссылку на видеообзор или ролик."

    def clean_items_data(self):
        items_data = self.cleaned_data.get("items_data") or []
        block_type = self.cleaned_data.get("block_type") or self.instance.block_type

        characteristic_name_map = {}

        if block_type == "specification":
            characteristic_ids = {
                int(str(item.get("characteristic_id") or "").strip())
                for item in items_data
                if isinstance(item, dict) and str(item.get("characteristic_id") or "").strip().isdigit()
            }
            if characteristic_ids:
                characteristic_name_map = dict(
                    ProductCharacteristic.objects.filter(pk__in=characteristic_ids).values_list(
                        "id", "name"
                    )
                )

        return normalize_block_items_data(
            block_type,
            items_data,
            characteristic_name_map=characteristic_name_map,
        )

class LearningBlockInlineFormSet(BaseInlineFormSet):
    def save(self, commit=True):
        instances = super().save(commit=commit)

        if not commit:
            return instances

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue

            block = form.instance
            if not block.pk:
                continue

            if block.block_type == "image" and block.image and not block.gallery_images.exists():
                LearningBlockGalleryImage.objects.create(
                    block=block,
                    sort_order=10,
                    image=block.image.name,
                    caption=block.caption,
                )
                block.image = None
                block.save(update_fields=["image"])

            uploads = form.cleaned_data.get("gallery_uploads") or []
            if not uploads:
                continue

            next_sort_order = (
                block.gallery_images.order_by("-sort_order").values_list("sort_order", flat=True).first()
                or 0
            )
            for index, uploaded_file in enumerate(uploads, start=1):
                LearningBlockGalleryImage.objects.create(
                    block=block,
                    sort_order=next_sort_order + index * 10,
                    image=uploaded_file,
                )

        return instances


class LearningBlockInline(admin.StackedInline):
    model = LearningBlock
    form = LearningBlockAdminForm
    formset = LearningBlockInlineFormSet
    extra = 0
    classes = ("section-general-blocks",)
    verbose_name = "Блок"
    verbose_name_plural = "Содержимое материала"
    readonly_fields = ("gallery_preview",)
    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "sort_order",
                    "block_type",
                    "title",
                    "caption",
                ),
                "description": (
                    "Выбери тип блока и заполни только нужные поля. "
                    "Для фишек, скриптов продаж, характеристик и таблиц ниже появится отдельный удобный редактор."
                ),
            },
        ),
        (
            "Содержимое блока",
            {
                "fields": (
                    "items_data",
                    "text",
                    "gallery_uploads",
                    "gallery_preview",
                    "image",
                    "video_url",
                    "document",
                ),
            },
        ),
    )

    @admin.display(description="Текущая галерея")
    def gallery_preview(self, obj):
        if not obj or not obj.pk:
            return "Сохрани блок, и сюда подтянется загруженная галерея."

        gallery_items = list(obj.gallery_images.all())
        if not gallery_items and not obj.image:
            return "Изображения ещё не загружены."

        previews = []
        for item in gallery_items:
            if not item.image:
                continue
            previews.append(
                (
                    item.image.url,
                    item.caption or "",
                )
            )

        if not previews and obj.image:
            previews.append((obj.image.url, obj.caption or ""))

        return format_html(
            '<div class="learning-gallery-preview">{}</div>',
            format_html_join(
                "",
                (
                    '<figure class="learning-gallery-preview__item">'
                    '<img src="{}" alt="{}" />'
                    "{}</figure>"
                ),
                (
                    (
                        url,
                        caption or "Изображение блока",
                        format_html(
                            '<figcaption>{}</figcaption>',
                            caption,
                        )
                        if caption
                        else "",
                    )
                    for url, caption in previews
                ),
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
    template_presets = ()
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
    autocomplete_fields = (
        "brands",
        "categories",
        "feature_tags",
    )
    filter_horizontal = (
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
        "send_selected_to_telegram_groups",
    )
    inlines = [LearningBlockInline]
    fieldsets = (
        (
            "Карточка базы знаний",
            {
                "fields": (
                    "title",
                    "summary",
                    "material_type",
                    ("cover_image", "cover_preview"),
                ),
                "classes": ("article-section", "section-preview"),
                "description": (
                    "Сначала название, короткое описание для карточки и тип материала. "
                    "Затем можно собирать саму страницу."
                ),
            },
        ),
        (
            "Публикация",
            {
                "fields": (
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
                    "Этот блок лучше настраивать в самом конце, когда материал уже готов к публикации. "
                    "При необходимости отсюда же можно сразу отправить его в Telegram."
                ),
            },
        ),
        (
            "Связи материала",
            {
                "fields": (
                    "categories",
                    "brands",
                    "feature_tags",
                ),
                "classes": ("article-section", "section-links"),
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

    def get_urls(self):
        custom_urls = [
            path(
                "category-characteristics/",
                self.admin_site.admin_view(self.category_characteristics_view),
                name="learning_learningmaterial_category_characteristics",
            ),
        ]
        return custom_urls + super().get_urls()

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            "feature_tags",
        )

    @staticmethod
    def _truthy_text(value):
        return bool(strip_tags(str(value or "")).strip())

    @staticmethod
    def _clean_id_values(values):
        cleaned = []
        for value in values or []:
            value = str(value or "").strip()
            if value.isdigit():
                cleaned.append(value)
        return cleaned

    def _form_value(self, form, obj, field_name):
        if form and field_name in form.fields:
            value = form[field_name].value()
            if value not in (None, ""):
                return value
        return getattr(obj, field_name, "") if obj else ""

    def _form_m2m_ids(self, form, obj, field_name):
        if form and field_name in form.fields:
            value = form[field_name].value()
            if value:
                return self._clean_id_values(value if isinstance(value, (list, tuple)) else [value])

        if obj and obj.pk:
            return [str(pk) for pk in getattr(obj, field_name).values_list("pk", flat=True)]

        return []

    def _selected_category_ids(self, request, obj, form):
        posted_ids = self._clean_id_values(request.POST.getlist("categories"))
        if posted_ids:
            return posted_ids
        return self._form_m2m_ids(form, obj, "categories")

    def _build_category_characteristics_map(self, category_ids):
        category_ids = self._clean_id_values(category_ids)
        if not category_ids:
            return {}

        category_characteristics_map = {}
        for link in (
            ProductCategoryCharacteristic.objects.select_related("characteristic")
            .filter(category_id__in=category_ids)
            .order_by("category_id", "sort_order", "characteristic__name")
        ):
            category_characteristics_map.setdefault(str(link.category_id), []).append(
                {
                    "id": link.characteristic_id,
                    "name": link.characteristic.name,
                    "sort_order": link.sort_order,
                }
            )
        return category_characteristics_map

    def category_characteristics_view(self, request):
        category_ids = self._clean_id_values(
            [
                *request.GET.getlist("category"),
                *request.GET.get("categories", "").split(","),
            ]
        )
        return JsonResponse(
            {
                "categoryCharacteristics": self._build_category_characteristics_map(category_ids),
                "allCharacteristics": list(
                    ProductCharacteristic.objects.order_by("name").values("id", "name")
                ),
            }
        )

    def _material_has_any_links(self, form, obj):
        return any(
            self._form_m2m_ids(form, obj, field_name)
            for field_name in ("brands", "categories", "areas", "feature_tags")
        )

    def _material_blocks(self, obj):
        if not obj or not obj.pk:
            return []
        return list(obj.blocks.prefetch_related("gallery_images").all())

    def _material_has_legacy_content(self, form, obj):
        return any(
            self._truthy_text(self._form_value(form, obj, field_name))
            for field_name in (
                "content",
                "product_full_description",
                "product_text_review",
                "product_short_summary",
                "product_video_review_url",
            )
        )

    def _build_admin_steps(self, form, obj):
        title_ready = self._truthy_text(self._form_value(form, obj, "title"))
        summary_ready = self._truthy_text(self._form_value(form, obj, "summary"))
        links_ready = self._material_has_any_links(form, obj)
        blocks = self._material_blocks(obj)
        content_ready = any(block_has_content(block) for block in blocks) or self._material_has_legacy_content(form, obj)
        publication_ready = bool(self._form_value(form, obj, "is_published"))

        raw_steps = (
            ("Карточка", title_ready and summary_ready),
            ("Связи", links_ready),
            ("Содержимое", content_ready),
            ("Публикация", publication_ready),
        )
        first_pending_seen = False
        steps = []
        for index, (label, is_done) in enumerate(raw_steps, start=1):
            status = "done" if is_done else "pending"
            if not is_done and not first_pending_seen:
                status = "active"
                first_pending_seen = True
            steps.append({"number": index, "label": label, "status": status})
        return steps

    def _build_readiness_checks(self, form, obj):
        material_type = self._form_value(form, obj, "material_type")
        title_ready = self._truthy_text(self._form_value(form, obj, "title"))
        summary_ready = self._truthy_text(self._form_value(form, obj, "summary"))
        categories_ready = bool(self._form_m2m_ids(form, obj, "categories"))
        links_ready = self._material_has_any_links(form, obj)
        blocks = self._material_blocks(obj)
        empty_blocks = [block for block in blocks if not block_has_content(block)]
        content_ready = bool(blocks and len(empty_blocks) < len(blocks)) or self._material_has_legacy_content(form, obj)
        cover_ready = bool(self._form_value(form, obj, "cover_image"))

        checks = [
            {
                "label": "Карточка заполнена",
                "ok": title_ready and summary_ready,
                "hint": "Нужны название и краткое описание для списка материалов.",
            },
            {
                "label": "Связи выбраны",
                "ok": categories_ready if material_type == "product" else links_ready,
                "hint": (
                    "Для товарного материала обязательна категория; для остальных полезны тема, бренд или метка."
                    if material_type == "product"
                    else "Добавь тему, бренд, категорию или фишку, чтобы материал легче находился."
                ),
            },
            {
                "label": "Содержимое добавлено",
                "ok": content_ready,
                "hint": "Добавь хотя бы один заполненный блок страницы.",
            },
            {
                "label": "Пустые блоки проверены",
                "ok": not empty_blocks,
                "hint": (
                    "; ".join(
                        f"{block.title or block.get_block_type_display()}: {get_block_empty_message(block)}"
                        for block in empty_blocks[:3]
                    )
                    or "Все блоки выглядят заполненными."
                ),
            },
            {
                "label": "Обложка добавлена",
                "ok": cover_ready,
                "hint": "Обложка не обязательна, но карточка в списке выглядит заметнее.",
                "optional": True,
            },
        ]
        return checks

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

    @admin.action(description="Отправить выбранные материалы в личные сообщения Telegram")
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
            report = send_learning_notification_to_private_subscribers(material)
            total_sent += report.sent
            total_failed += report.failed

        self.message_user(
            request,
            "Рассылка материалов в личные сообщения завершена. "
            f"Успешно: {total_sent}, не удалось: {total_failed}, пропущено неопубликованных: {skipped}.",
            level=messages.SUCCESS if total_sent else messages.WARNING,
        )

    @admin.action(description="Отправить выбранные материалы в Telegram-группы")
    def send_selected_to_telegram_groups(self, request, queryset):
        if not telegram_enabled():
            self.message_user(
                request,
                "Токен Telegram-бота не настроен.",
                level=messages.ERROR,
            )
            return

        available_group_chats = TelegramSubscriber.objects.filter(
            is_active=True,
            is_blocked=False,
            chat_type__in=(
                TelegramSubscriber.CHAT_TYPE_GROUP,
                TelegramSubscriber.CHAT_TYPE_SUPERGROUP,
            ),
        ).order_by("chat_title", "chat_id")
        selected_group_ids = request.POST.getlist("telegram_group_chats")
        error_message = ""

        if "send_to_groups_confirm" in request.POST:
            selected_group_chats = available_group_chats.filter(pk__in=selected_group_ids)

            if not selected_group_chats.exists():
                error_message = "Выбери хотя бы одну доступную Telegram-группу."
            else:
                total_sent = 0
                total_failed = 0
                skipped = 0

                for material in queryset:
                    if not material.is_published:
                        skipped += 1
                        continue
                    report = send_learning_notification_to_group_chats(
                        material,
                        selected_group_chats,
                    )
                    total_sent += report.sent
                    total_failed += report.failed

                self.message_user(
                    request,
                    "Рассылка материалов в Telegram-группы завершена. "
                    f"Успешно: {total_sent}, не удалось: {total_failed}, "
                    f"пропущено неопубликованных: {skipped}.",
                    level=messages.SUCCESS if total_sent else messages.WARNING,
                )
                return

        context = {
            **self.admin_site.each_context(request),
            "title": "Отправка материалов в Telegram-группы",
            "opts": self.model._meta,
            "materials": queryset,
            "available_group_chats": available_group_chats,
            "selected_group_ids": selected_group_ids,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "changelist_url": reverse("admin:learning_learningmaterial_changelist"),
            "error_message": error_message,
        }
        return TemplateResponse(
            request,
            "admin/learning/learningmaterial/send_to_groups.html",
            context,
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
            form = adminform.form
            selected_category_ids = self._selected_category_ids(request, obj, form)

            context.update(
                {
                    "learning_block_schema": get_admin_block_schema(),
                    "learning_block_palette": [
                        {"key": key, "label": BLOCK_TYPE_DEFINITIONS[key]["label"]}
                        for key in ADMIN_BLOCK_TYPE_KEYS
                    ],
                    "preview_fieldset": self._find_fieldset(adminform, "section-preview"),
                    "material_mode_fieldset": self._find_fieldset(
                        adminform, "section-material-mode"
                    ),
                    "links_fieldset": self._find_fieldset(
                        adminform, "section-links"
                    ),
                    "system_fieldset": self._find_fieldset(adminform, "section-system"),
                    "general_blocks_inline": self._find_inline(
                        inline_admin_formsets, "section-general-blocks"
                    ),
                    "category_characteristics_map": self._build_category_characteristics_map(
                        selected_category_ids
                    ),
                    "all_product_characteristics": list(
                        ProductCharacteristic.objects.order_by("name").values("id", "name")
                    ),
                    "product_characteristic_add_url": reverse("admin:catalog_productcharacteristic_add"),
                    "category_characteristics_url": reverse(
                        "admin:learning_learningmaterial_category_characteristics"
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

    def clone_related_objects(self, request, source, clone):
        block_clone_map = {}

        related_sets = (
            ("product_description_images", "material"),
            ("product_review_images", "material"),
            ("product_features", "material"),
            ("product_sales_scripts", "material"),
            ("product_specifications", "material"),
        )

        for related_name, relation_field in related_sets:
            for item in getattr(source, related_name).all():
                item.pk = None
                setattr(item, relation_field, clone)
                item.save()

        for block in source.blocks.all():
            original_pk = block.pk
            block.pk = None
            block.material = clone
            block.save()
            block_clone_map[original_pk] = block

        for original_pk, cloned_block in block_clone_map.items():
            for gallery_item in LearningBlockGalleryImage.objects.filter(block_id=original_pk):
                gallery_item.pk = None
                gallery_item.block = cloned_block
                gallery_item.save()

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


class PresentationImportAdmin(admin.ModelAdmin):
    change_form_template = "admin/learning/presentationimport/change_form.html"
    list_display = (
        "title_or_file",
        "material_link",
        "publish_material",
        "created_at",
    )
    list_filter = ("publish_material", "created_at")
    search_fields = ("title", "presentation", "material__title")
    readonly_fields = (
        "material_link",
        "import_report",
        "created_at",
        "updated_at",
    )
    fields = (
        "title",
        "presentation",
        "publish_material",
        "material_link",
        "import_report",
        "created_at",
        "updated_at",
    )
    actions = ("recreate_materials",)

    @admin.display(description="Презентация")
    def title_or_file(self, obj):
        return obj.resolved_title

    @admin.display(description="Материал базы знаний")
    def material_link(self, obj):
        if not obj or not obj.material_id:
            return "Материал будет создан после сохранения презентации."

        return format_html(
            '<a href="{}">Открыть материал в админке</a>',
            reverse("admin:learning_learningmaterial_change", args=[obj.material_id]),
        )

    @admin.action(description="Пересоздать материалы из выбранных презентаций")
    def recreate_materials(self, request, queryset):
        recreated = 0
        failed = 0

        for presentation_import in queryset:
            try:
                self._create_material_from_presentation(
                    presentation_import,
                    replace_existing=True,
                )
            except PresentationImportError as exc:
                failed += 1
                presentation_import.import_report = str(exc)
                presentation_import.save(update_fields=["import_report", "updated_at"])
                continue
            recreated += 1

        self.message_user(
            request,
            f"Пересоздано материалов: {recreated}. Ошибок: {failed}.",
            level=messages.SUCCESS if recreated else messages.WARNING,
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.material_id:
            return

        try:
            slides = self._extract_slides(obj)
            if "_preview_import" in request.POST:
                obj.import_report = self._build_import_preview_report(obj, slides)
                obj.save(update_fields=["import_report", "updated_at"])
                self.message_user(
                    request,
                    "Предварительный разбор презентации готов. Проверь отчет и сохрани еще раз, чтобы создать материал.",
                    level=messages.INFO,
                )
                return

            self._create_material_from_presentation(obj, slides=slides)
        except PresentationImportError as exc:
            obj.import_report = str(exc)
            obj.save(update_fields=["import_report", "updated_at"])
            self.message_user(request, str(exc), level=messages.ERROR)
            return

        self.message_user(
            request,
            "Материал базы знаний создан из презентации.",
            level=messages.SUCCESS,
        )

    def response_add(self, request, obj, post_url_continue=None):
        if "_preview_import" in request.POST:
            return HttpResponseRedirect(
                reverse("admin:learning_presentationimport_change", args=[obj.pk])
            )
        return super().response_add(request, obj, post_url_continue=post_url_continue)

    def response_change(self, request, obj):
        if "_preview_import" in request.POST:
            return HttpResponseRedirect(
                reverse("admin:learning_presentationimport_change", args=[obj.pk])
            )
        return super().response_change(request, obj)

    def _extract_slides(self, obj):
        return extract_pptx_slides(
            obj.presentation.path,
            enable_ocr=settings.PRESENTATION_OCR_ENABLED,
            ocr_languages=settings.PRESENTATION_OCR_LANGUAGES,
            ocr_timeout=settings.PRESENTATION_OCR_TIMEOUT,
            ocr_tesseract_cmd=settings.PRESENTATION_OCR_TESSERACT_CMD,
            ocr_tessdata_dir=settings.PRESENTATION_OCR_TESSDATA_DIR,
        )

    def _build_import_preview_report(self, obj, slides):
        lines = [
            f"Предварительный разбор презентации «{obj.resolved_title}».",
            f"Слайдов с содержимым: {len(slides)}.",
            f"Изображений: {sum(len(slide.images) for slide in slides)}.",
            f"Слайдов с распознанным текстом: {sum(1 for slide in slides if slide.ocr_paragraphs)}.",
            "",
            "Что будет создано:",
        ]
        for slide in slides[:12]:
            parts = []
            if slide.paragraphs:
                parts.append(f"текстовых абзацев: {len(slide.paragraphs)}")
            if slide.images:
                parts.append(f"изображений: {len(slide.images)}")
            if slide.ocr_paragraphs:
                parts.append(f"OCR-абзацев: {len(slide.ocr_paragraphs)}")
            lines.append(f"- Слайд {slide.number}: {slide.title} ({', '.join(parts) or 'без блоков'})")

        if len(slides) > 12:
            lines.append(f"- Еще слайдов: {len(slides) - 12}.")

        return "\n".join(lines)

    def _create_material_from_presentation(self, obj, replace_existing=False, slides=None):
        slides = slides or self._extract_slides(obj)

        with transaction.atomic():
            if replace_existing and obj.material_id:
                obj.material.delete()
                obj.material = None

            material = LearningMaterial.objects.create(
                title=obj.resolved_title,
                summary=build_summary(slides),
                content=(
                    "<p>Материал автоматически создан из загруженной презентации. "
                    "Проверь текст и при необходимости дополни блоки.</p>"
                ),
                material_type="instruction",
                is_published=obj.publish_material,
            )

            for index, slide in enumerate(slides, start=1):
                base_sort_order = index * 100

                if slide.paragraphs:
                    LearningBlock.objects.create(
                        material=material,
                        sort_order=base_sort_order + 10,
                        block_type="text",
                        title=slide.title,
                        text=build_slide_html(slide),
                        caption=f"Слайд {slide.number}",
                    )

                if slide.images:
                    image_block = LearningBlock.objects.create(
                        material=material,
                        sort_order=base_sort_order + 20,
                        block_type="image",
                        title=slide.title,
                        caption=f"Слайд {slide.number}",
                    )
                    for image_index, image in enumerate(slide.images, start=1):
                        LearningBlockGalleryImage.objects.create(
                            block=image_block,
                            sort_order=image_index * 10,
                            image=ContentFile(
                                image.content,
                                name=f"slide-{slide.number}-{image_index}-{image.filename}",
                            ),
                            caption=f"Слайд {slide.number}",
                        )

                if slide.ocr_paragraphs:
                    LearningBlock.objects.create(
                        material=material,
                        sort_order=base_sort_order + 30,
                        block_type="text",
                        title=(
                            f"{slide.title}: текст с изображений"
                            if slide.title
                            else f"Слайд {slide.number}: текст с изображений"
                        ),
                        text=build_ocr_html(slide),
                        caption=f"Слайд {slide.number}, распознано с изображений",
                    )

            obj.material = material
            image_count = sum(len(slide.images) for slide in slides)
            ocr_slide_count = sum(1 for slide in slides if slide.ocr_paragraphs)
            obj.import_report = (
                f"Создан материал «{material.title}». "
                f"Импортировано слайдов: {len(slides)}. "
                f"Изображений: {image_count}. "
                f"Слайдов с распознанным текстом: {ocr_slide_count}."
            )
            obj.save(update_fields=["material", "import_report", "updated_at"])
