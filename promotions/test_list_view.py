from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Promotion


class PromotionListViewTests(TestCase):
    def test_default_status_shows_only_active_and_upcoming_promotions(self):
        today = timezone.localdate()
        Promotion.objects.create(
            title="Active promotion",
            is_published=True,
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=1),
        )
        Promotion.objects.create(
            title="Upcoming promotion",
            is_published=True,
            start_date=today + timedelta(days=2),
        )
        Promotion.objects.create(
            title="Finished promotion",
            is_published=True,
            end_date=today - timedelta(days=1),
        )

        response = self.client.get(reverse("promotion_list"))

        titles = {item.title for item in response.context["promotions"]}

        self.assertEqual(titles, {"Active promotion", "Upcoming promotion"})

    def test_finished_promotions_cannot_be_restored_by_status_parameter(self):
        today = timezone.localdate()
        Promotion.objects.create(
            title="Active promotion",
            is_published=True,
            end_date=today + timedelta(days=1),
        )
        Promotion.objects.create(
            title="Finished promotion",
            is_published=True,
            end_date=today - timedelta(days=1),
        )

        response = self.client.get(reverse("promotion_list"), {"status": "all"})

        titles = {item.title for item in response.context["promotions"]}

        self.assertEqual(titles, {"Active promotion"})
        self.assertEqual(response.context["selected_status"], "")

    def test_finished_promotion_detail_returns_not_found(self):
        promotion = Promotion.objects.create(
            title="Finished promotion",
            is_published=True,
            end_date=timezone.localdate() - timedelta(days=1),
        )

        response = self.client.get(
            reverse("promotion_detail", kwargs={"slug": promotion.slug})
        )

        self.assertEqual(response.status_code, 404)

    def test_upcoming_promotion_detail_remains_available(self):
        promotion = Promotion.objects.create(
            title="Upcoming promotion",
            is_published=True,
            start_date=timezone.localdate() + timedelta(days=1),
        )

        response = self.client.get(
            reverse("promotion_detail", kwargs={"slug": promotion.slug})
        )

        self.assertEqual(response.status_code, 200)

    def test_brand_filter_options_ignore_unpublished_promotions(self):
        Promotion.objects.create(
            title="Visible promotion",
            is_published=True,
            brand="Visible brand",
        )
        Promotion.objects.create(
            title="Hidden promotion",
            is_published=False,
            brand="Hidden brand",
        )

        response = self.client.get(reverse("promotion_list"))

        brands = list(response.context["brands"])

        self.assertIn("Visible brand", brands)
        self.assertNotIn("Hidden brand", brands)
