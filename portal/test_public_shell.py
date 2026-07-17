from pathlib import Path

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


class PublicShellTests(TestCase):
    def test_home_exposes_theme_switcher_and_mobile_navigation(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, "data-theme-toggle")
        self.assertContains(response, "public-theme-switcher.js")
        self.assertContains(response, "data-nav-toggle")
        self.assertContains(response, "data-nav-backdrop")

    def test_public_theme_keeps_backdrop_below_sticky_header(self):
        stylesheet_path = finders.find("css/public-theme.css")

        self.assertIsNotNone(stylesheet_path)
        stylesheet = Path(stylesheet_path).read_text(encoding="utf-8")
        self.assertIn("z-index: 1300;", stylesheet)
        self.assertIn("z-index: 1100;", stylesheet)

    def test_theme_switcher_persists_the_selected_public_theme(self):
        script_path = finders.find("js/public-theme-switcher.js")

        self.assertIsNotNone(script_path)
        script = Path(script_path).read_text(encoding="utf-8")
        self.assertIn('var storageKey = "corpportal-public-theme";', script)
        self.assertIn("window.localStorage.setItem(storageKey, theme)", script)
        self.assertIn("document.documentElement.dataset.publicTheme", script)
