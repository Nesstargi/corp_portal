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
from telegram_bot.services import send_news_notification, telegram_enabled

from .models import News, NewsBlock


class NewsBlockAdminForm(forms.ModelForm):
    class Meta:
        model = NewsBlock
        fields = "__all__"
        widgets = {
            "text": RichTextToolbarWidget(),
        }


class NewsAdminForm(forms.ModelForm):
    send_telegram_notification = forms.BooleanField(
        required=False,
        label="Отправить в Telegram после сохранения",
        help_text="Новость уйдет всем пользователям, которые уже запускали бота.",
    )

    class Meta:
        model = News
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        if not str(cleaned_data.get("summary") or "").strip() and not str(
            cleaned_data.get("content") or ""
        ).strip():
            self.add_error("summary", "Добавь хотя бы короткий анонс или основной текст новости.")
            self.add_error("content", "Добавь хотя бы основной текст или короткий анонс новости.")

        if cleaned_data.get("category") == "product":
            brands = cleaned_data.get("brands")
            categories = cleaned_data.get("product_categories")
            if not brands and not categories:
                self.add_error(
                    "brands",
                    "Для новости о новой модели укажи хотя бы бренд или категорию товара.",
                )

        if cleaned_data.get("send_telegram_notification"):
            audience = cleaned_data.get("telegram_audience")
            groups = cleaned_data.get("telegram_target_groups")
            collections = cleaned_data.get("telegram_target_chat_collections")
            if audience == "groups" and (not groups or not groups.exists()):
                self.add_error(
                    "telegram_target_groups",
                    "Выбери хотя бы одну группу подписчиков Telegram.",
                )
            if audience == "group_chats" and collections and hasattr(collections, "exists") and not collections.exists():
                cleaned_data["telegram_target_chat_collections"] = collections

        return cleaned_data


class NewsBlockInline(admin.StackedInline):
    model = NewsBlock
    form = NewsBlockAdminForm
    extra = 1
    verbose_name = "Блок содержимого"
    verbose_name_plural = "Блоки содержимого"
    fieldsets = (
        (
            "Основное",
            {
                "fields": ("sort_order", "block_type", "title", "caption"),
                "description": "Например: текст, изображение, видео, цитата или файл.",
            },
        ),
        (
            "Содержимое блока",
            {
                "fields": ("text", "image", "video_url", "document"),
            },
        ),
    )


@admin.register(News)
class NewsAdmin(
    AdminDuplicateMixin,
    AdminTemplatesAndFiltersMixin,
    AdminPresentationMixin,
    admin.ModelAdmin,
):
    form = NewsAdminForm
    image_recommendation = (1600, 900)
    template_presets = (
        {
            "key": "product-launch",
            "label": "Создать: новая модель",
            "initial": {
                "category": "product",
                "title": "Новая модель",
                "summary": "Короткий анонс новой модели для карточки новости.",
            },
        },
        {
            "key": "corporate",
            "label": "Создать: корпоративная новость",
            "initial": {
                "category": "corporate",
                "title": "Корпоративная новость",
                "summary": "Коротко опиши, что произошло и почему это важно команде.",
            },
        },
        {
            "key": "promotion",
            "label": "Создать: новость об акции",
            "initial": {
                "category": "promotion",
                "title": "Новая акция",
                "summary": "Кратко опиши выгоду и сроки действия акции.",
            },
        },
    )
    quick_filters = (
        {"label": "Все", "key": "is_published__exact", "value": ""},
        {"label": "Опубликованные", "key": "is_published__exact", "value": "1"},
        {"label": "Скрытые", "key": "is_published__exact", "value": "0"},
        {"label": "Новые модели", "key": "category__exact", "value": "product"},
        {"label": "Без обложки", "key": "cover_image__isnull", "value": "True"},
    )
    list_display = (
        "cover_thumb",
        "title",
        "category_badge",
        "is_published",
        "created_at",
        "updated_at",
        "public_link",
    )
    list_display_links = ("title",)
    list_editable = ("is_published",)
    list_filter = ("category", "is_published", "created_at")
    search_fields = ("title", "summary", "content")
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
        "product_categories",
        "feature_tags",
        "telegram_target_groups",
        "telegram_target_chat_collections",
    )
    inlines = [NewsBlockInline]
    actions = (
        "publish_selected",
        "unpublish_selected",
        "duplicate_selected",
        "send_selected_to_telegram",
    )
    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "title",
                    "summary",
                    "content",
                    ("cover_image", "cover_preview"),
                    "card_preview",
                ),
            },
        ),
        (
            "Где и как показывать",
            {
                "fields": (
                    "category",
                    "is_published",
                    "public_link",
                    "duplicate_link",
                    "history_link",
                ),
            },
        ),
        (
            "Уведомление в Telegram",
            {
                "fields": (
                    "send_telegram_notification",
                    "telegram_audience",
                    "telegram_target_groups",
                    "telegram_target_chat_collections",
                    "telegram_include_group_chats",
                ),
                "description": (
                    "Работает только для опубликованных новостей. "
                    "Личные уведомления уходят тем, кто уже запускал бота, "
                    "а групповые — в те Telegram-группы, где бот был активирован командой."
                ),
            },
        ),
        (
            "Связь с товарами и фишками",
            {
                "fields": ("brands", "product_categories", "feature_tags"),
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
        summary = strip_tags(obj.summary or obj.content or "").strip()
        chips = [obj.get_category_display()]
        chips.extend(tag.name for tag in obj.feature_tags.all()[:2]) if obj.pk else None
        footer = []
        if obj.pk and obj.created_at:
            footer.append(obj.created_at.strftime("%d.%m.%Y"))
        return render_admin_card_preview(
            obj.title,
            summary[:180],
            chips=chips,
            footer=footer,
        )

    @admin.display(description="Тип")
    def category_badge(self, obj):
        colors = {
            "product": "is-blue",
            "corporate": "is-violet",
            "promotion": "is-orange",
            "instruction": "is-green",
        }
        return format_html(
            '<span class="admin-type-badge {}">{}</span>',
            colors.get(obj.category, "is-violet"),
            obj.get_category_display(),
        )

    @admin.action(description="Опубликовать выбранные новости")
    def publish_selected(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"Опубликовано новостей: {updated}.", level=messages.SUCCESS)

    @admin.action(description="Скрыть выбранные новости")
    def unpublish_selected(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"Скрыто новостей: {updated}.", level=messages.SUCCESS)

    @admin.action(description="Создать копии выбранных новостей")
    def duplicate_selected(self, request, queryset):
        duplicated = 0

        for news in queryset:
            self.clone_object(request, news)
            duplicated += 1

        self.message_user(request, f"Создано копий новостей: {duplicated}.", level=messages.SUCCESS)

    @admin.action(description="Отправить выбранные новости в Telegram")
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

        for news in queryset:
            if not news.is_published:
                skipped += 1
                continue
            report = send_news_notification(news)
            total_sent += report.sent
            total_failed += report.failed

        self.message_user(
            request,
            "Рассылка новостей завершена. "
            f"Успешно: {total_sent}, не удалось: {total_failed}, пропущено неопубликованных: {skipped}.",
            level=messages.SUCCESS if total_sent else messages.WARNING,
        )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        if not form.cleaned_data.get("send_telegram_notification"):
            return

        if not telegram_enabled():
            self.message_user(
                request,
                "Новость сохранена, но токен Telegram-бота не настроен.",
                level=messages.WARNING,
            )
            return

        if not form.instance.is_published:
            self.message_user(
                request,
                "Новость сохранена, но не отправлена: сначала включи показ на сайте.",
                level=messages.WARNING,
            )
            return

        report = send_news_notification(form.instance)
        self.message_user(
            request,
            f"Новость отправлена в Telegram. Успешно: {report.sent}, не удалось: {report.failed}.",
            level=messages.SUCCESS if report.sent else messages.WARNING,
        )

    def clone_related_objects(self, request, source, clone):
        for block in source.blocks.all():
            block.pk = None
            block.news = clone
            block.save()
