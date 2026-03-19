import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags

from .models import TelegramBroadcast, TelegramSubscriber


class TelegramBotError(Exception):
    pass


@dataclass
class TelegramSendReport:
    total: int = 0
    sent: int = 0
    failed: int = 0


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
    base_url = settings.SITE_URL.rstrip("/")
    return f"{base_url}{path}"


def _truncate_plain_text(text, limit=900):
    clean_text = strip_tags(text or "").strip()
    if len(clean_text) <= limit:
        return clean_text
    return f"{clean_text[: limit - 1].rstrip()}…"


def _send_message_to_subscriber(subscriber, text):
    try:
        _perform_api_call(
            "sendMessage",
            {
                "chat_id": subscriber.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": "false",
            },
        )
    except TelegramBotError as exc:
        error_text = str(exc).lower()
        if "bot was blocked by the user" in error_text or "chat not found" in error_text:
            subscriber.is_active = False
            subscriber.is_blocked = True
            subscriber.save(update_fields=["is_active", "is_blocked", "last_interaction_at"])
        raise


def send_text_to_subscribers(text, subscribers=None):
    subscribers = subscribers or TelegramSubscriber.objects.filter(
        is_active=True,
        is_blocked=False,
    )
    report = TelegramSendReport(total=subscribers.count())

    for subscriber in subscribers:
        try:
            _send_message_to_subscriber(subscriber, text)
            report.sent += 1
        except TelegramBotError:
            report.failed += 1

    return report


def format_news_message(news):
    url = _make_absolute_url(news.get_absolute_url())
    lines = [
        "📰 <b>Новая новость</b>",
        f"<b>{news.title}</b>",
    ]

    summary = _truncate_plain_text(news.telegram_summary, limit=500)
    if summary:
        lines.append(summary)

    if url:
        lines.append("")
        lines.append(f"<a href=\"{url}\">Открыть новость</a>")

    return "\n".join(lines)


def format_learning_message(material):
    url = _make_absolute_url(material.get_absolute_url())
    lines = [
        "📘 <b>Новый материал</b>",
        f"<b>{material.title}</b>",
    ]

    summary = _truncate_plain_text(material.telegram_summary, limit=500)
    if summary:
        lines.append(summary)

    if url:
        lines.append("")
        lines.append(f"<a href=\"{url}\">Открыть материал</a>")

    return "\n".join(lines)


def format_broadcast_message(broadcast):
    lines = [f"📢 <b>{broadcast.title}</b>"]
    message = _truncate_plain_text(broadcast.message, limit=700)
    if message:
        lines.append(message)

    if broadcast.link_url:
        lines.append("")
        lines.append(f"<a href=\"{broadcast.link_url}\">Открыть ссылку</a>")

    return "\n".join(lines)


def send_news_notification(news):
    return send_text_to_subscribers(format_news_message(news))


def send_learning_notification(material):
    return send_text_to_subscribers(format_learning_message(material))


def send_broadcast_notification(broadcast):
    report = send_text_to_subscribers(format_broadcast_message(broadcast))
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
    subscriber.username = from_user.get("username", "") or ""
    subscriber.first_name = from_user.get("first_name", "") or ""
    subscriber.last_name = from_user.get("last_name", "") or ""
    subscriber.language_code = from_user.get("language_code", "") or ""
    subscriber.is_blocked = False
    subscriber.save()
    return subscriber


def handle_update(update):
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat = message.get("chat") or {}
    if chat.get("type") != "private":
        return

    subscriber = update_subscriber_from_message(message)
    if subscriber is None:
        return

    text = (message.get("text") or "").strip().lower()
    if text.startswith("/start"):
        subscriber.is_active = True
        subscriber.is_blocked = False
        subscriber.save(update_fields=["is_active", "is_blocked", "last_interaction_at"])
        _send_message_to_subscriber(
            subscriber,
            "Привет! Ты подписан на уведомления портала.\n\n"
            "Я буду присылать новые новости и материалы.\n"
            "Если захочешь отключиться, отправь /stop.",
        )
        return

    if text.startswith("/stop"):
        subscriber.is_active = False
        subscriber.save(update_fields=["is_active", "last_interaction_at"])
        _send_message_to_subscriber(
            subscriber,
            "Уведомления отключены. Если захочешь включить их снова, отправь /start.",
        )
        return

    if text.startswith("/status"):
        status_text = (
            "Уведомления включены." if subscriber.is_active else "Уведомления сейчас выключены."
        )
        _send_message_to_subscriber(
            subscriber,
            f"{status_text}\n\n/start — включить\n/stop — выключить",
        )
        return

    _send_message_to_subscriber(
        subscriber,
        "Я используюсь для уведомлений корпоративного портала.\n\n"
        "/start — включить уведомления\n"
        "/stop — выключить уведомления\n"
        "/status — проверить статус",
    )


def configure_webhook(webhook_url):
    payload = {"url": webhook_url}
    if settings.TELEGRAM_WEBHOOK_SECRET:
        payload["secret_token"] = settings.TELEGRAM_WEBHOOK_SECRET
    return _perform_api_call("setWebhook", payload)


def clear_webhook():
    return _perform_api_call("deleteWebhook")

