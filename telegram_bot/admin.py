from django import forms
from django.contrib import admin, messages

from .models import TelegramAudienceGroup, TelegramBroadcast, TelegramSubscriber
from .services import send_broadcast_notification


class TelegramBroadcastAdminForm(forms.ModelForm):
    send_now = forms.BooleanField(
        required=False,
        label="Сразу отправить в Telegram",
        help_text="После сохранения уведомление уйдет выбранной аудитории бота.",
    )

    class Meta:
        model = TelegramBroadcast
        fields = "__all__"


@admin.register(TelegramAudienceGroup)
class TelegramAudienceGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "subscriber_count")
    search_fields = ("name", "description")

    def subscriber_count(self, obj):
        return obj.subscribers.count()

    subscriber_count.short_description = "Подписчиков"


@admin.register(TelegramSubscriber)
class TelegramSubscriberAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "chat_id",
        "is_active",
        "is_blocked",
        "group_list",
        "last_interaction_at",
    )
    list_filter = ("is_active", "is_blocked", "language_code", "groups")
    search_fields = ("username", "first_name", "last_name", "chat_id")
    list_editable = ("is_active", "is_blocked")
    readonly_fields = ("started_at", "last_interaction_at")
    filter_horizontal = ("groups",)
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
                    "groups",
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

    def group_list(self, obj):
        return ", ".join(obj.groups.values_list("name", flat=True)) or "—"

    group_list.short_description = "Группы"


@admin.register(TelegramBroadcast)
class TelegramBroadcastAdmin(admin.ModelAdmin):
    form = TelegramBroadcastAdminForm
    list_display = (
        "title",
        "target_mode",
        "is_sent",
        "sent_count",
        "failed_count",
        "sent_at",
    )
    list_filter = ("is_sent", "target_mode", "created_at", "sent_at", "target_groups")
    search_fields = ("title", "message")
    readonly_fields = (
        "sent_count",
        "failed_count",
        "last_error",
        "created_at",
        "updated_at",
        "sent_at",
    )
    filter_horizontal = ("target_groups",)
    actions = ("send_selected_broadcasts",)
    fieldsets = (
        (
            "Уведомление",
            {
                "fields": (
                    "title",
                    "message",
                    "link_url",
                    "target_mode",
                    "target_groups",
                    "send_now",
                ),
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

    class Media:
        css = {
            "all": ("css/admin-enhancements.css",),
        }
        js = ("js/admin-enhancements.js",)

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
        request._telegram_send_now = form.cleaned_data.get("send_now", False)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        if not getattr(request, "_telegram_send_now", False):
            return

        report = send_broadcast_notification(form.instance)
        self.message_user(
            request,
            f"Уведомление отправлено. Успешно: {report.sent}, не удалось: {report.failed}.",
            level=messages.SUCCESS if report.sent else messages.WARNING,
        )
