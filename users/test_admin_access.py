from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

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

        self.assertNotIn("Администраторы", app_names)
        self.assertFalse(admin.site._registry[User].has_module_permission(request))

    def test_admin_management_is_visible_for_superuser(self):
        request = self.build_request(self.superuser)
        app_names = [app["name"] for app in admin.site.get_app_list(request)]

        self.assertIn("Администраторы", app_names)
        self.assertTrue(admin.site._registry[User].has_module_permission(request))

    def test_promotion_google_sheets_import_is_visible_on_dashboard(self):
        request = self.build_request(self.superuser)
        app_list = admin.site.get_app_list(request)
        content_section = next(app for app in app_list if app["name"] == "Контент сайта")
        model_names = [model["name"] for model in content_section["models"]]

        self.assertIn("Импорт акций из Google Sheets", model_names)
