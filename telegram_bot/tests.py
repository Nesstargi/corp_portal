import json
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from learning.models import LearningMaterial
from news.models import News

from .models import (
    TelegramAudienceGroup,
    TelegramBroadcast,
    TelegramChatCollection,
    TelegramSubscriber,
)
from .services import send_broadcast_notification


@override_settings(
    TELEGRAM_BOT_TOKEN="test-token",
    TELEGRAM_WEBHOOK_SECRET="secret",
    SITE_URL="https://example.com",
)
class TelegramWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("telegram_bot.services._send_plain_text_to_subscriber")
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

    @patch("telegram_bot.services._send_plain_text_to_subscriber")
    def test_latest_command_returns_latest_news_and_materials(self, mock_send_message):
        News.objects.create(title="Новая модель", summary="Анонс", is_published=True)
        LearningMaterial.objects.create(
            title="Материал по бренду",
            summary="Коротко",
            is_published=True,
        )

        payload = {
            "update_id": 2,
            "message": {
                "message_id": 11,
                "text": "/latest",
                "chat": {"id": 54321, "type": "private"},
                "from": {
                    "id": 54321,
                    "is_bot": False,
                    "first_name": "Anna",
                    "username": "anna",
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
        sent_text = mock_send_message.call_args[0][1]
        self.assertIn("Новая модель", sent_text)
        self.assertIn("Материал по бренду", sent_text)

    @patch("telegram_bot.services._send_plain_text_to_subscriber")
    def test_start_command_activates_group_chat(self, mock_send_message):
        payload = {
            "update_id": 3,
            "message": {
                "message_id": 12,
                "text": "/start",
                "chat": {"id": -1001234567890, "type": "supergroup", "title": "Команда продаж"},
                "from": {
                    "id": 777,
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
        subscriber = TelegramSubscriber.objects.get(chat_id=-1001234567890)
        self.assertTrue(subscriber.is_active)
        self.assertEqual(subscriber.chat_type, TelegramSubscriber.CHAT_TYPE_SUPERGROUP)
        self.assertEqual(subscriber.chat_title, "Команда продаж")
        mock_send_message.assert_called_once()


@override_settings(TELEGRAM_BOT_TOKEN="test-token")
class TelegramAudienceTests(TestCase):
    @patch("telegram_bot.services._send_prepared_message_to_subscriber")
    def test_group_targeted_broadcast_hits_only_selected_group(self, mock_send):
        retail = TelegramAudienceGroup.objects.create(name="Розница")
        office = TelegramAudienceGroup.objects.create(name="Офис")

        subscriber_retail = TelegramSubscriber.objects.create(chat_id=1, username="retail")
        subscriber_retail.groups.add(retail)

        subscriber_office = TelegramSubscriber.objects.create(chat_id=2, username="office")
        subscriber_office.groups.add(office)

        broadcast = TelegramBroadcast.objects.create(
            title="Тест",
            message="Сообщение",
            target_mode="groups",
        )
        broadcast.target_groups.add(retail)

        report = send_broadcast_notification(broadcast)

        self.assertEqual(report.sent, 1)
        self.assertEqual(report.failed, 0)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args[0][0].pk, subscriber_retail.pk)

    @patch("telegram_bot.services._send_prepared_message_to_subscriber")
    def test_broadcast_can_include_group_chats(self, mock_send):
        subscriber_private = TelegramSubscriber.objects.create(chat_id=11, username="retail")
        subscriber_group = TelegramSubscriber.objects.create(
            chat_id=-100555,
            chat_type=TelegramSubscriber.CHAT_TYPE_SUPERGROUP,
            chat_title="Продажи",
        )

        broadcast = TelegramBroadcast.objects.create(
            title="Тест",
            message="Сообщение",
            target_mode="all",
            include_group_chats=True,
        )

        report = send_broadcast_notification(broadcast)

        self.assertEqual(report.sent, 2)
        self.assertEqual(report.failed, 0)
        self.assertEqual(mock_send.call_count, 2)
        sent_ids = {call.args[0].pk for call in mock_send.call_args_list}
        self.assertEqual(sent_ids, {subscriber_private.pk, subscriber_group.pk})

    @patch("telegram_bot.services._send_prepared_message_to_subscriber")
    def test_group_chats_only_broadcast_hits_only_group_chats(self, mock_send):
        TelegramSubscriber.objects.create(chat_id=21, username="private_user")
        subscriber_group = TelegramSubscriber.objects.create(
            chat_id=-100777,
            chat_type=TelegramSubscriber.CHAT_TYPE_GROUP,
            chat_title="Салон 1",
        )

        broadcast = TelegramBroadcast.objects.create(
            title="Только группы",
            message="Сообщение",
            target_mode="group_chats",
        )

        report = send_broadcast_notification(broadcast)

        self.assertEqual(report.sent, 1)
        self.assertEqual(report.failed, 0)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args[0][0].pk, subscriber_group.pk)

    @patch("telegram_bot.services._send_prepared_message_to_subscriber")
    def test_group_chat_collection_limits_group_delivery(self, mock_send):
        target_group = TelegramSubscriber.objects.create(
            chat_id=-100888,
            chat_type=TelegramSubscriber.CHAT_TYPE_SUPERGROUP,
            chat_title="Целевая группа",
        )
        TelegramSubscriber.objects.create(
            chat_id=-100999,
            chat_type=TelegramSubscriber.CHAT_TYPE_SUPERGROUP,
            chat_title="Лишняя группа",
        )
        collection = TelegramChatCollection.objects.create(name="Тестовое объединение")
        collection.chats.add(target_group)

        broadcast = TelegramBroadcast.objects.create(
            title="Группы по объединению",
            message="Сообщение",
            target_mode="group_chats",
        )
        broadcast.target_chat_collections.add(collection)

        report = send_broadcast_notification(broadcast)

        self.assertEqual(report.sent, 1)
        self.assertEqual(report.failed, 0)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args[0][0].pk, target_group.pk)
