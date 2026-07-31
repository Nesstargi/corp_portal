from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Promotion


class PromotionPublicFiltersRedesignTests(TestCase):
    def create_promotion(self, title, **kwargs):
        defaults = {
            "is_published": True,
            "start_date": timezone.localdate() - timedelta(days=1),
            "end_date": timezone.localdate() + timedelta(days=1),
        }
        defaults.update(kwargs)
        return Promotion.objects.create(title=title, **defaults)

    def test_status_and_promo_type_are_whitelisted(self):
        promo_price = self.create_promotion(
            "Promo price",
            promotion_kind=Promotion.KIND_PROMO_PRICE,
        )
        gift = self.create_promotion(
            "Gift",
            promotion_kind=Promotion.KIND_GIFT,
        )

        response = self.client.get(
            reverse("promotion_list"),
            {"status": "not-a-status", "promo_type": "not-a-type"},
        )

        self.assertEqual(set(response.context["promotions"]), {promo_price, gift})
        self.assertEqual(response.context["selected_status"], "")
        self.assertEqual(response.context["selected_promo_type"], "")
        self.assertFalse(response.context["has_active_filters"])

    def test_brand_options_are_case_insensitive_and_filter_all_variants(self):
        samsung = self.create_promotion("Samsung A", brand="Samsung")
        samsung_lower = self.create_promotion("Samsung B", brand="samsung")
        samsung_spaced = self.create_promotion("Samsung C", brand=" Samsung ")
        self.create_promotion("Hidden", brand="Hidden", is_published=False)

        response = self.client.get(
            reverse("promotion_list"),
            {"brand": "SAMSUNG"},
        )

        self.assertEqual(response.context["brands"], ["Samsung"])
        self.assertEqual(response.context["selected_brand"], "Samsung")
        self.assertEqual(
            set(response.context["promotions"]),
            {samsung, samsung_lower, samsung_spaced},
        )
        self.assertEqual(response.context["result_count"], 3)

    def test_pagination_and_tab_urls_preserve_filters_but_drop_page(self):
        for index in range(11):
            self.create_promotion(
                f"Samsung gift {index:02d}",
                brand="Samsung",
                promotion_kind=Promotion.KIND_GIFT,
            )

        response = self.client.get(
            reverse("promotion_list"),
            {
                "q": "Samsung",
                "brand": "Samsung",
                "status": "active",
                "promo_type": "gift",
                "page": 2,
            },
        )

        self.assertEqual(response.context["result_count"], 11)
        self.assertEqual(len(response.context["promotions"]), 1)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertNotIn("page=", response.context["query_without_page"])
        self.assertIn("q=Samsung", response.context["query_without_page"])
        self.assertIn("brand=Samsung", response.context["query_without_page"])
        self.assertIn("status=active", response.context["query_without_page"])
        self.assertIn("promo_type=gift", response.context["query_without_page"])

        tabs = {tab["key"]: tab for tab in response.context["promotion_type_tabs"]}
        promo_price_url = tabs["promo_price"]["url"]
        self.assertNotIn("page=", promo_price_url)
        self.assertIn("q=Samsung", promo_price_url)
        self.assertIn("brand=Samsung", promo_price_url)
        self.assertIn("status=active", promo_price_url)
        self.assertIn("promo_type=promo_price", promo_price_url)

