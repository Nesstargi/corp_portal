from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.test import RequestFactory, TestCase

from catalog.models import Brand, FeatureTag, ProductCategory, ProductCharacteristic
from learning.models import LearningMaterial, PresentationImport
from promotions.models import Promotion, PromotionSource
from telegram_bot.models import (
    TelegramAudienceGroup,
    TelegramBroadcast,
    TelegramChatCollection,
    TelegramSubscriber,
)

import config.urls  # noqa: F401


class AdminAccessTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username="manager",
            password="password",
            is_staff=True,
        )
        self.superuser = User.objects.create_superuser(
            username="owner",
            password="password",
        )

    def build_request(self, user):
        request = self.factory.get("/admin/")
        request.current_app = admin.site.name
        request.user = user
        return request

    def test_admin_management_is_hidden_from_regular_staff(self):
        request = self.build_request(self.staff_user)
        app_names = [app["name"] for app in admin.site.get_app_list(request)]

        self.assertNotIn("Доступ", app_names)
        self.assertFalse(admin.site._registry[User].has_module_permission(request))

    def test_admin_management_is_visible_for_superuser(self):
        request = self.build_request(self.superuser)
        app_names = [app["name"] for app in admin.site.get_app_list(request)]

        self.assertIn("Доступ", app_names)
        self.assertTrue(admin.site._registry[User].has_module_permission(request))

    def test_admin_users_cannot_be_bulk_deleted(self):
        request = self.build_request(self.superuser)
        user_admin = admin.site._registry[User]

        self.assertNotIn("delete_selected", user_admin.get_actions(request))
        self.assertFalse(user_admin.has_delete_permission(request, self.superuser))
        self.assertTrue(user_admin.has_delete_permission(request, self.staff_user))

    def test_presentation_import_is_not_registered_or_visible_on_dashboard(self):
        self.assertNotIn(PresentationImport, admin.site._registry)

        request = self.build_request(self.superuser)
        model_names = {
            model["name"]
            for section in admin.site.get_app_list(request)
            for model in section["models"]
        }

        self.assertNotIn("Импорт презентаций", model_names)

    def test_promotion_google_sheets_import_is_hidden_from_dashboard(self):
        request = self.build_request(self.superuser)
        model_names = {
            model["name"]
            for section in admin.site.get_app_list(request)
            for model in section["models"]
        }

        self.assertNotIn("Импорт акций из Google Sheets", model_names)
        self.assertIn(PromotionSource, admin.site._registry)

    def test_required_dashboard_sections_and_models_are_preserved(self):
        request = self.build_request(self.superuser)
        dashboard = {
            section["name"]: {model["name"] for model in section["models"]}
            for section in admin.site.get_app_list(request)
        }

        self.assertEqual(
            dashboard,
            {
                "Справочники товаров": {"Категории товаров", "Бренды", "Метки"},
                "Контент сайта": {"База знаний", "Акции"},
                "Telegram": {
                    "Рассылки",
                    "Подписчики и чаты",
                    "Группы подписчиков",
                    "Объединения Telegram-групп",
                },
                "Доступ": {"Администраторы", "Роли и права"},
            },
        )

        required_registered_models = {
            Brand,
            FeatureTag,
            ProductCategory,
            ProductCharacteristic,
            LearningMaterial,
            Promotion,
            TelegramAudienceGroup,
            TelegramBroadcast,
            TelegramChatCollection,
            TelegramSubscriber,
            User,
            Group,
        }
        self.assertTrue(required_registered_models.issubset(admin.site._registry))
