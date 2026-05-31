from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from telegram_bot.models import TelegramSubscriber
from telegram_bot.services import TelegramSendReport

from .models import LearningMaterial


@override_settings(TELEGRAM_BOT_TOKEN="test-token")
class LearningMaterialTelegramAdminActionTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="owner",
            password="password",
        )
        self.client.force_login(self.superuser)
        self.material = LearningMaterial.objects.create(
            title="Материал для Telegram",
            summary="Короткое описание.",
            is_published=True,
        )
        self.changelist_url = reverse("admin:learning_learningmaterial_changelist")

    def test_changelist_has_separate_private_and_group_actions(self):
        response = self.client.get(self.changelist_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Отправить выбранные материалы в личные сообщения Telegram",
        )
        self.assertContains(
            response,
            "Отправить выбранные материалы в Telegram-группы",
        )

    def test_group_action_opens_active_group_selector(self):
        active_group = TelegramSubscriber.objects.create(
            chat_id=-100101,
            chat_type=TelegramSubscriber.CHAT_TYPE_SUPERGROUP,
            chat_title="Активная группа",
        )
        TelegramSubscriber.objects.create(
            chat_id=-100202,
            chat_type=TelegramSubscriber.CHAT_TYPE_GROUP,
            chat_title="Отключенная группа",
            is_active=False,
        )
        TelegramSubscriber.objects.create(
            chat_id=303,
            chat_type=TelegramSubscriber.CHAT_TYPE_PRIVATE,
            username="private_user",
        )

        response = self.client.post(
            self.changelist_url,
            {
                "action": "send_selected_to_telegram_groups",
                "_selected_action": [str(self.material.pk)],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Выберите Telegram-группы")
        self.assertContains(response, active_group.chat_title)
        self.assertNotContains(response, "Отключенная группа")
        self.assertNotContains(response, "@private_user")

    @patch("learning.admin.send_learning_notification_to_group_chats")
    def test_group_action_sends_to_checked_group_after_confirmation(self, send_to_groups):
        send_to_groups.return_value = TelegramSendReport(total=1, sent=1)
        selected_group = TelegramSubscriber.objects.create(
            chat_id=-100404,
            chat_type=TelegramSubscriber.CHAT_TYPE_SUPERGROUP,
            chat_title="Выбранная группа",
        )
        TelegramSubscriber.objects.create(
            chat_id=-100505,
            chat_type=TelegramSubscriber.CHAT_TYPE_GROUP,
            chat_title="Лишняя группа",
        )

        response = self.client.post(
            self.changelist_url,
            {
                "action": "send_selected_to_telegram_groups",
                "_selected_action": [str(self.material.pk)],
                "telegram_group_chats": [str(selected_group.pk)],
                "send_to_groups_confirm": "1",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        send_to_groups.assert_called_once()
        material, group_chats = send_to_groups.call_args.args
        self.assertEqual(material.pk, self.material.pk)
        self.assertEqual(list(group_chats), [selected_group])
        self.assertContains(response, "Рассылка материалов в Telegram-группы завершена")

    @patch("learning.admin.send_learning_notification_to_private_subscribers")
    def test_private_action_uses_private_delivery(self, send_to_private):
        send_to_private.return_value = TelegramSendReport(total=1, sent=1)

        response = self.client.post(
            self.changelist_url,
            {
                "action": "send_selected_to_telegram",
                "_selected_action": [str(self.material.pk)],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        send_to_private.assert_called_once_with(self.material)
        self.assertContains(response, "Рассылка материалов в личные сообщения завершена")
