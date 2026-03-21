import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone
from django.utils.html import escape, strip_tags

from .models import TelegramBroadcast, TelegramChatCollection, TelegramSubscriber


class TelegramBotError(Exception):
    pass


@dataclass
class TelegramSendReport:
    total: int = 0
    sent: int = 0
    failed: int = 0


@dataclass
class TelegramMessagePayload:
    text: str
    button_url: str = ""
    button_text: str = "Открыть"
    image_url: str = ""


def telegram_enabled():
    return bool(settings.TELEGRAM_BOT_TOKEN)


def _api_url(method):
    return f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"


def _perform_api_call(method, payload=None):
    if not telegram_enabled():
        raise TelegramBotError("Токен Telegram-бота не настроен.")

    data = None
    headers = {}
    if payload is not None:
        data = urlencode(payload).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    request = Request(_api_url(method), data=data, headers=headers, method="POST")

    try:
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise TelegramBotError(detail or str(exc)) from exc
    except URLError as exc:
        raise TelegramBotError(str(exc)) from exc

    parsed = json.loads(body)
    if not parsed.get("ok"):
        raise TelegramBotError(parsed.get("description", "Неизвестная ошибка Telegram API"))
    return parsed.get("result")


def _make_absolute_url(path):
    if not path:
        return ""
    return f"{settings.SITE_URL.rstrip('/')}{path}"


def _absolute_media_url(file_field):
    if not file_field:
        return ""
    url = getattr(file_field, "url", "")
    return _make_absolute_url(url) if url else ""


def _truncate_plain_text(text, limit=900):
    clean_text = strip_tags(text or "").strip()
    if len(clean_text) <= limit:
        return clean_text
    return f"{clean_text[: limit - 1].rstrip()}…"


def _build_reply_markup(button_text="", button_url=""):
    if not button_text or not button_url:
        return ""
    return json.dumps(
        {
            "inline_keyboard": [
                [
                    {
                        "text": button_text,
                        "url": button_url,
                    }
                ]
            ]
        },
        ensure_ascii=False,
    )


def _active_private_subscribers_queryset():
    return TelegramSubscriber.objects.filter(
        is_active=True,
        is_blocked=False,
        chat_type=TelegramSubscriber.CHAT_TYPE_PRIVATE,
    ).distinct()


def _active_group_chats_queryset():
    return TelegramSubscriber.objects.filter(
        is_active=True,
        is_blocked=False,
        chat_type__in=[
            TelegramSubscriber.CHAT_TYPE_GROUP,
            TelegramSubscriber.CHAT_TYPE_SUPERGROUP,
        ],
    ).distinct()


def get_target_group_chats(target_chat_collections=None):
    queryset = _active_group_chats_queryset()
    if target_chat_collections is None:
        return queryset

    collection_ids = list(target_chat_collections.values_list("id", flat=True))
    if not collection_ids:
        return queryset

    return queryset.filter(chat_collections__in=collection_ids).distinct()


def get_target_subscribers(
    target_mode="all",
    target_groups=None,
    include_group_chats=False,
    target_chat_collections=None,
):
    queryset = _active_private_subscribers_queryset()
    group_chats_queryset = get_target_group_chats(target_chat_collections)

    if target_mode == "group_chats":
        return group_chats_queryset

    if target_mode == "groups":
        if target_groups is None:
            return queryset.none()
        group_ids = list(target_groups.values_list("id", flat=True))
        if not group_ids:
            return queryset.none()
        queryset = queryset.filter(groups__in=group_ids).distinct()

    if include_group_chats:
        return (queryset | group_chats_queryset).distinct()

    return queryset


def _send_prepared_message_to_subscriber(subscriber, payload):
    reply_markup = _build_reply_markup(payload.button_text, payload.button_url)

    try:
        if payload.image_url:
            request_payload = {
                "chat_id": subscriber.chat_id,
                "photo": payload.image_url,
                "caption": payload.text[:1024],
                "parse_mode": "HTML",
            }
            if reply_markup:
                request_payload["reply_markup"] = reply_markup
            _perform_api_call("sendPhoto", request_payload)
        else:
            request_payload = {
                "chat_id": subscriber.chat_id,
                "text": payload.text,
                "parse_mode": "HTML",
                "disable_web_page_preview": "false",
            }
            if reply_markup:
                request_payload["reply_markup"] = reply_markup
            _perform_api_call("sendMessage", request_payload)
    except TelegramBotError as exc:
        error_text = str(exc).lower()
        if (
            "bot was blocked by the user" in error_text
            or "chat not found" in error_text
            or "bot was kicked" in error_text
            or "group chat was upgraded" in error_text
        ):
            subscriber.is_active = False
            subscriber.is_blocked = True
            subscriber.save(update_fields=["is_active", "is_blocked", "last_interaction_at"])
        raise


def _send_plain_text_to_subscriber(subscriber, text, button_url="", button_text="Открыть"):
    payload = TelegramMessagePayload(text=text, button_url=button_url, button_text=button_text)
    _send_prepared_message_to_subscriber(subscriber, payload)


def send_payload_to_subscribers(payload, subscribers=None):
    subscribers = subscribers if subscribers is not None else _active_private_subscribers_queryset()
    report = TelegramSendReport(total=subscribers.count())

    for subscriber in subscribers:
        try:
            _send_prepared_message_to_subscriber(subscriber, payload)
            report.sent += 1
        except TelegramBotError:
            report.failed += 1

    return report


def _format_header(icon, title, subtitle):
    lines = [f"{icon} <b>{escape(title)}</b>"]
    if subtitle:
        lines.append(f"<b>{escape(subtitle)}</b>")
    return lines


def build_news_payload(news):
    url = _make_absolute_url(news.get_absolute_url())
    lines = _format_header("📰", "Новая новость", news.title)

    summary = _truncate_plain_text(news.telegram_summary, limit=500)
    if summary:
        lines.append(escape(summary))

    return TelegramMessagePayload(
        text="\n".join(lines),
        button_url=url,
        button_text="Открыть новость",
        image_url=_absolute_media_url(news.cover_image),
    )


def build_learning_payload(material):
    url = _make_absolute_url(material.get_absolute_url())
    lines = _format_header("📘", "Новый материал", material.title)

    summary = _truncate_plain_text(material.telegram_summary, limit=500)
    if summary:
        lines.append(escape(summary))

    return TelegramMessagePayload(
        text="\n".join(lines),
        button_url=url,
        button_text="Открыть материал",
        image_url=_absolute_media_url(material.cover_image),
    )


def build_broadcast_payload(broadcast):
    lines = _format_header("📢", broadcast.title, "")
    message = _truncate_plain_text(broadcast.message, limit=700)
    if message:
        lines.append(escape(message))

    return TelegramMessagePayload(
        text="\n".join(lines),
        button_url=broadcast.link_url,
        button_text="Открыть ссылку",
    )


def send_news_notification(news):
    subscribers = get_target_subscribers(
        news.telegram_audience,
        news.telegram_target_groups,
        include_group_chats=news.telegram_include_group_chats,
        target_chat_collections=news.telegram_target_chat_collections,
    )
    return send_payload_to_subscribers(build_news_payload(news), subscribers=subscribers)


def send_learning_notification(material):
    subscribers = get_target_subscribers(
        material.telegram_audience,
        material.telegram_target_groups,
        include_group_chats=material.telegram_include_group_chats,
        target_chat_collections=material.telegram_target_chat_collections,
    )
    return send_payload_to_subscribers(build_learning_payload(material), subscribers=subscribers)


def send_broadcast_notification(broadcast):
    subscribers = get_target_subscribers(
        broadcast.target_mode,
        broadcast.target_groups,
        include_group_chats=broadcast.include_group_chats,
        target_chat_collections=broadcast.target_chat_collections,
    )
    report = send_payload_to_subscribers(build_broadcast_payload(broadcast), subscribers=subscribers)
    broadcast.is_sent = True
    broadcast.sent_count = report.sent
    broadcast.failed_count = report.failed
    broadcast.sent_at = timezone.now()
    broadcast.last_error = ""
    broadcast.save(
        update_fields=[
            "is_sent",
            "sent_count",
            "failed_count",
            "sent_at",
            "last_error",
            "updated_at",
        ]
    )
    return report


def update_subscriber_from_message(message):
    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return None

    subscriber, _ = TelegramSubscriber.objects.get_or_create(chat_id=chat_id)
    subscriber.chat_type = chat.get("type", TelegramSubscriber.CHAT_TYPE_PRIVATE) or TelegramSubscriber.CHAT_TYPE_PRIVATE
    subscriber.chat_title = chat.get("title", "") or ""
    if subscriber.chat_type == TelegramSubscriber.CHAT_TYPE_PRIVATE:
        subscriber.username = from_user.get("username", "") or ""
        subscriber.first_name = from_user.get("first_name", "") or ""
        subscriber.last_name = from_user.get("last_name", "") or ""
        subscriber.language_code = from_user.get("language_code", "") or ""
    else:
        subscriber.username = ""
        subscriber.first_name = ""
        subscriber.last_name = ""
        subscriber.language_code = ""
    subscriber.is_blocked = False
    subscriber.save()
    return subscriber


def _build_latest_text():
    from learning.models import LearningMaterial
    from news.models import News

    latest_news = News.objects.filter(is_published=True).order_by("-created_at")[:3]
    latest_learning = LearningMaterial.objects.filter(is_published=True).order_by("-updated_at")[:3]

    lines = ["🆕 <b>Последние обновления портала</b>"]

    if latest_news:
        lines.append("")
        lines.append("<b>Новости</b>")
        for item in latest_news:
            lines.append(
                f"• <a href=\"{escape(_make_absolute_url(item.get_absolute_url()))}\">{escape(item.title)}</a>"
            )

    if latest_learning:
        lines.append("")
        lines.append("<b>Материалы</b>")
        for item in latest_learning:
            lines.append(
                f"• <a href=\"{escape(_make_absolute_url(item.get_absolute_url()))}\">{escape(item.title)}</a>"
            )

    if len(lines) == 1:
        lines.append("")
        lines.append("Пока ничего не опубликовано.")

    return "\n".join(lines)


def handle_update(update):
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat = message.get("chat") or {}
    subscriber = update_subscriber_from_message(message)
    if subscriber is None:
        return

    text = (message.get("text") or "").strip().lower()
    is_private_chat = chat.get("type") == TelegramSubscriber.CHAT_TYPE_PRIVATE

    if text.startswith("/start"):
        subscriber.is_active = True
        subscriber.is_blocked = False
        subscriber.save(update_fields=["is_active", "is_blocked", "last_interaction_at"])
        if is_private_chat:
            _send_plain_text_to_subscriber(
                subscriber,
                "Привет! Ты подписан на уведомления портала.\n\n"
                "Я буду присылать новые новости и материалы.\n"
                "Команды:\n"
                "/latest — последние новости и материалы\n"
                "/status — статус подписки\n"
                "/stop — отключить уведомления",
                button_url=settings.SITE_URL,
                button_text="Открыть портал",
            )
        else:
            _send_plain_text_to_subscriber(
                subscriber,
                "Группа подключена к уведомлениям портала.\n\n"
                "Теперь сюда можно присылать новости, материалы и ручные уведомления.\n"
                "Команды:\n"
                "/latest — последние новости и материалы\n"
                "/status — статус группы\n"
                "/stop — отключить уведомления для этой группы",
                button_url=settings.SITE_URL,
                button_text="Открыть портал",
            )
        return

    if text.startswith("/stop"):
        subscriber.is_active = False
        subscriber.save(update_fields=["is_active", "last_interaction_at"])
        _send_plain_text_to_subscriber(
            subscriber,
            "Уведомления отключены. Если захочешь включить их снова, отправь /start.",
            button_url=settings.SITE_URL,
            button_text="Открыть портал",
        )
        return

    if text.startswith("/status"):
        if is_private_chat:
            status_text = (
                "Уведомления включены." if subscriber.is_active else "Уведомления сейчас выключены."
            )
        else:
            status_text = (
                "Уведомления для группы включены."
                if subscriber.is_active
                else "Уведомления для группы сейчас выключены."
            )
        _send_plain_text_to_subscriber(
            subscriber,
            f"{status_text}\n\n/start — включить\n/stop — выключить\n/latest — последние материалы",
            button_url=settings.SITE_URL,
            button_text="Открыть портал",
        )
        return

    if text.startswith("/latest"):
        _send_plain_text_to_subscriber(
            subscriber,
            _build_latest_text(),
            button_url=settings.SITE_URL,
            button_text="Перейти в портал",
        )
        return

    if not is_private_chat:
        return

    _send_plain_text_to_subscriber(
        subscriber,
        "Я используюсь для уведомлений корпоративного портала.\n\n"
        "/start — включить уведомления\n"
        "/stop — выключить уведомления\n"
        "/status — проверить статус\n"
        "/latest — последние новости и материалы",
        button_url=settings.SITE_URL,
        button_text="Открыть портал",
    )


def configure_webhook(webhook_url):
    payload = {"url": webhook_url}
    if settings.TELEGRAM_WEBHOOK_SECRET:
        payload["secret_token"] = settings.TELEGRAM_WEBHOOK_SECRET
    return _perform_api_call("setWebhook", payload)


def clear_webhook():
    return _perform_api_call("deleteWebhook")
