from django import forms
from django.contrib import admin, messages

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
class NewsAdmin(admin.ModelAdmin):
    form = NewsAdminForm
    list_display = ("title", "category", "created_at", "is_published")
    list_filter = ("category", "is_published", "created_at")
    search_fields = ("title", "summary", "content")
    list_editable = ("is_published",)
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("brands", "product_categories", "feature_tags")
    inlines = [NewsBlockInline]
    actions = ("send_selected_to_telegram",)
    fieldsets = (
        (
            "Основная информация",
            {
                "fields": ("title", "summary", "content", "cover_image"),
            },
        ),
        (
            "Где и как показывать",
            {
                "fields": ("category", "is_published"),
            },
        ),
        (
            "Уведомление в Telegram",
            {
                "fields": ("send_telegram_notification",),
                "description": "Работает только для опубликованных новостей и пользователей, которые уже написали боту.",
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
