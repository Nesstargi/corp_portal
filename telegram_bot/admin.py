from django import forms
from django.contrib import admin, messages

from .models import TelegramBroadcast, TelegramSubscriber
from .services import send_broadcast_notification


class TelegramBroadcastAdminForm(forms.ModelForm):
    send_now = forms.BooleanField(
        required=False,
        label="Сразу отправить в Telegram",
        help_text="После сохранения уведомление уйдет всем активным подписчикам бота.",
    )

    class Meta:
        model = TelegramBroadcast
        fields = "__all__"


@admin.register(TelegramSubscriber)
class TelegramSubscriberAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "chat_id",
        "is_active",
        "is_blocked",
        "last_interaction_at",
    )
    list_filter = ("is_active", "is_blocked", "language_code")
    search_fields = ("username", "first_name", "last_name", "chat_id")
    list_editable = ("is_active", "is_blocked")
    readonly_fields = ("started_at", "last_interaction_at")
    fieldsets = (
        (
            "Подписчик",
            {
                "fields": (
                    "chat_id",
                    "username",
                    "first_name",
                    "last_name",
                    "language_code",
                )
            },
        ),
        (
            "Статус",
            {
                "fields": ("is_active", "is_blocked"),
            },
        ),
        (
            "Служебная информация",
            {
                "fields": ("started_at", "last_interaction_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(TelegramBroadcast)
class TelegramBroadcastAdmin(admin.ModelAdmin):
    form = TelegramBroadcastAdminForm
    list_display = ("title", "is_sent", "sent_count", "failed_count", "sent_at")
    list_filter = ("is_sent", "created_at", "sent_at")
    search_fields = ("title", "message")
    readonly_fields = ("sent_count", "failed_count", "last_error", "created_at", "updated_at", "sent_at")
    actions = ("send_selected_broadcasts",)
    fieldsets = (
        (
            "Уведомление",
            {
                "fields": ("title", "message", "link_url", "send_now"),
            },
        ),
        (
            "Статус отправки",
            {
                "fields": (
                    "is_sent",
                    "sent_count",
                    "failed_count",
                    "last_error",
                    "sent_at",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.action(description="Отправить выбранные уведомления в Telegram")
    def send_selected_broadcasts(self, request, queryset):
        total_sent = 0
        total_failed = 0

        for broadcast in queryset:
            report = send_broadcast_notification(broadcast)
            total_sent += report.sent
            total_failed += report.failed

        self.message_user(
            request,
            f"Уведомления отправлены. Успешно: {total_sent}, не удалось: {total_failed}.",
            level=messages.SUCCESS if total_sent else messages.WARNING,
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if form.cleaned_data.get("send_now"):
            report = send_broadcast_notification(obj)
            self.message_user(
                request,
                f"Уведомление отправлено. Успешно: {report.sent}, не удалось: {report.failed}.",
                level=messages.SUCCESS if report.sent else messages.WARNING,
            )

