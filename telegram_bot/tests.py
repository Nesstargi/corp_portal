import json
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import TelegramSubscriber


@override_settings(TELEGRAM_BOT_TOKEN="test-token", TELEGRAM_WEBHOOK_SECRET="secret")
class TelegramWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("telegram_bot.services._send_message_to_subscriber")
    def test_start_creates_active_subscriber(self, mock_send_message):
        payload = {
            "update_id": 1,
            "message": {
                "message_id": 10,
                "text": "/start",
                "chat": {"id": 12345, "type": "private"},
                "from": {
                    "id": 12345,
                    "is_bot": False,
                    "first_name": "Egor",
                    "username": "nestarg",
                    "language_code": "ru",
                },
            },
        }

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="secret",
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        subscriber = TelegramSubscriber.objects.get(chat_id=12345)
        self.assertTrue(subscriber.is_active)
        self.assertEqual(subscriber.username, "nestarg")
        mock_send_message.assert_called_once()
