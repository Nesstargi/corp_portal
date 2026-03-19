from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse

from telegram_bot.services import TelegramBotError, configure_webhook


class Command(BaseCommand):
    help = "Настраивает webhook Telegram-бота на текущий сайт."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            dest="base_url",
            help="Базовый URL сайта, например https://testcorpportal.xyz",
        )

    def handle(self, *args, **options):
        base_url = (options.get("base_url") or settings.SITE_URL).rstrip("/")
        if not base_url:
            raise CommandError("Не указан SITE_URL или --base-url.")

        webhook_url = f"{base_url}{reverse('telegram_webhook')}"

        try:
            configure_webhook(webhook_url)
        except TelegramBotError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f"Webhook настроен: {webhook_url}"))

