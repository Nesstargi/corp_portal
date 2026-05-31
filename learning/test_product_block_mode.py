import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from catalog.models import ProductCategory, ProductCharacteristic

from .admin import (
    LearningBlockAdminForm,
    LearningMaterialAdminForm,
)
from .models import (
    LearningBlock,
    LearningBlockGalleryImage,
    LearningMaterial,
)


class LearningProductBlockModeTests(TestCase):
    def setUp(self):
        self.category = ProductCategory.objects.create(name="Пылесосы")
        self.characteristic = ProductCharacteristic.objects.create(name="Мощность всасывания")

    def test_product_admin_form_allows_saving_without_strict_structured_sections(self):
        form = LearningMaterialAdminForm(
            data={
                "title": "Гибкая карточка товара",
                "summary": "Короткое описание для карточки.",
                "material_type": "product",
                "is_published": "on",
                "telegram_audience": "all",
                "categories": [str(self.category.pk)],
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_structured_block_widget_is_rendered_as_visible_editor(self):
        form = LearningBlockAdminForm()
        rendered = str(form["items_data"])

        self.assertFalse(form.fields["items_data"].widget.is_hidden)
        self.assertIn("data-block-items-editor", rendered)
        self.assertIn("learning-block-items-json", rendered)
        self.assertEqual(form.fields["title"].label, "Заголовок секции")
        self.assertIn("удобный редактор", form.fields["items_data"].help_text)

    def test_material_summary_uses_rich_text_editor_with_italic_control(self):
        form = LearningMaterialAdminForm()
        rendered = str(form["summary"])

        self.assertIn("data-rich-text-widget", rendered)
        self.assertIn('data-command="bold"', rendered)
        self.assertIn('data-command="italic"', rendered)
        self.assertIn('data-command="insertUnorderedList"', rendered)

    def test_specification_form_resolves_characteristic_name_from_catalog(self):
        material = LearningMaterial.objects.create(
            title="Тестовый товар",
            summary="Карточка для проверки характеристик.",
            material_type="product",
            is_published=True,
        )
        form = LearningBlockAdminForm(
            data={
                "material": str(material.pk),
                "sort_order": "10",
                "block_type": "specification",
                "title": "Характеристики",
                "caption": "",
                "text": "",
                "video_url": "",
                "items_data": json.dumps(
                    [
                        {
                            "characteristic_id": str(self.characteristic.pk),
                            "name": "",
                            "value": "7000 Па",
                        }
                    ]
                ),
            },
            instance=LearningBlock(material=material),
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data["items_data"][0]["name"],
            "Мощность всасывания",
        )

    def test_product_detail_keeps_legacy_product_sections_when_blocks_exist(self):
        material = LearningMaterial.objects.create(
            title="Dreame H15 Pro",
            summary="Моющий вертикальный пылесос для быстрой уборки.",
            material_type="product",
            product_full_description="<p>Этот старый структурный текст должен сохраниться рядом с новыми блоками.</p>",
            is_published=True,
        )
        material.categories.add(self.category)
        LearningBlock.objects.create(
            material=material,
            sort_order=10,
            block_type="text",
            title="С чего начать продажу",
            text="<p>Начинай разговор с удобства ежедневной влажной уборки и быстрой подготовки техники к работе.</p>",
        )

        response = self.client.get(reverse("learning_detail", args=[material.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "С чего начать продажу")
        self.assertContains(response, "удобства ежедневной влажной уборки")
        self.assertContains(response, "Вернуться к списку материалов")
        self.assertContains(
            response,
            "Этот старый структурный текст должен сохраниться рядом с новыми блоками.",
        )

    def test_product_detail_renders_summary_formatting(self):
        material = LearningMaterial.objects.create(
            title="Карточка с оформленным описанием",
            summary="<p><strong>Главное</strong>: <em>коротко</em>.</p><ul><li>Первый тезис</li></ul>",
            material_type="instruction",
            is_published=True,
        )

        response = self.client.get(reverse("learning_detail", args=[material.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<strong>Главное</strong>", html=True)
        self.assertContains(response, "<em>коротко</em>", html=True)
        self.assertContains(response, "<li>Первый тезис</li>", html=True)

    def test_product_detail_renders_specialized_block_types(self):
        material = LearningMaterial.objects.create(
            title="Dreame Z20 Aqua",
            summary="Товар собран только из блоков.",
            material_type="product",
            is_published=True,
        )
        material.categories.add(self.category)
        LearningBlock.objects.create(
            material=material,
            sort_order=10,
            block_type="feature",
            title="Фишки модели",
            items_data=[
                {
                    "title": "Два валика для сложных загрязнений",
                    "description": "Лучше подбирает мусор вдоль плинтусов и на швах плитки.",
                    "pitch": "Подчеркни, что уборка получается ровнее даже в проходных зонах.",
                }
            ],
        )
        LearningBlock.objects.create(
            material=material,
            sort_order=20,
            block_type="sales_script",
            title="Сценарии разговора",
            items_data=[
                {
                    "title": "Скрипт для быстрой презентации",
                    "pitch": "Если клиенту важна быстрая ежедневная влажная уборка, начни с удобства запуска и самоочистки.",
                }
            ],
        )
        LearningBlock.objects.create(
            material=material,
            sort_order=30,
            block_type="specification",
            title="Характеристики",
            items_data=[
                {
                    "name": "Мощность всасывания",
                    "value": "210 AW",
                }
            ],
        )

        response = self.client.get(reverse("learning_detail", args=[material.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Два валика для сложных загрязнений")
        self.assertContains(response, "Подчеркни, что уборка получается ровнее даже в проходных зонах.")
        self.assertContains(response, "Скрипт для быстрой презентации")
        self.assertContains(response, "Мощность всасывания")
        self.assertContains(response, "210 AW")

    def test_comparison_table_block_form_keeps_models_and_rows(self):
        material = LearningMaterial.objects.create(
            title="Сравнение линейки",
            summary="Материал с таблицей отличий.",
            material_type="instruction",
            is_published=True,
        )
        form = LearningBlockAdminForm(
            data={
                "material": str(material.pk),
                "sort_order": "10",
                "block_type": "comparison_table",
                "title": "Dreame G10: отличия",
                "caption": "",
                "text": "",
                "video_url": "",
                "items_data": json.dumps(
                    {
                        "models": ["Dreame G10", "Dreame G10 Pro"],
                        "rows": [
                            {
                                "parameter": "Мощность всасывания",
                                "values": ["7 000 Па", "16 000 Па"],
                            }
                        ],
                    }
                ),
            },
            instance=LearningBlock(material=material),
        )

        self.assertTrue(form.is_valid(), form.errors)
        block = form.save(commit=False)
        self.assertEqual(block.items_data["models"], ["Dreame G10", "Dreame G10 Pro"])
        self.assertEqual(block.items_data["rows"][0]["parameter"], "Мощность всасывания")
        self.assertEqual(block.items_data["rows"][0]["values"], ["7 000 Па", "16 000 Па"])

    def test_comparison_table_block_renders_on_detail_page(self):
        material = LearningMaterial.objects.create(
            title="Dreame G10: сравнение моделей",
            summary="Три модели одной линейки в одном материале.",
            material_type="instruction",
            is_published=True,
        )
        LearningBlock.objects.create(
            material=material,
            sort_order=10,
            block_type="comparison_table",
            title="Таблица характеристик",
            items_data={
                "models": ["Dreame G10", "Dreame G10 Pro", "Dreame G10 Combo"],
                "rows": [
                    {
                        "parameter": "Позиционирование",
                        "values": [
                            "базовая модель",
                            "лучшая мойка твёрдых полов",
                            "универсальный 2-в-1",
                        ],
                    },
                    {
                        "parameter": "Мощность всасывания",
                        "values": ["7 000 Па", "16 000 Па", "16 000 Па"],
                    },
                ],
            },
        )

        response = self.client.get(reverse("learning_detail", args=[material.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Таблица характеристик")
        self.assertContains(response, "Dreame G10 Pro")
        self.assertContains(response, "Позиционирование")
        self.assertContains(response, "лучшая мойка твёрдых полов")
        self.assertContains(response, "16 000 Па")

    def test_product_detail_renders_image_block_as_slider_when_gallery_has_several_images(self):
        material = LearningMaterial.objects.create(
            title="Dreame X50 Ultra",
            summary="Галерея в товарном блоке.",
            material_type="product",
            is_published=True,
        )
        material.categories.add(self.category)
        gallery_block = LearningBlock.objects.create(
            material=material,
            sort_order=10,
            block_type="image",
            title="Галерея товара",
        )

        image_bytes = (
            b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00"
            b"\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        LearningBlockGalleryImage.objects.create(
            block=gallery_block,
            sort_order=10,
            image=SimpleUploadedFile("first.gif", image_bytes, content_type="image/gif"),
            caption="Первый ракурс",
        )
        LearningBlockGalleryImage.objects.create(
            block=gallery_block,
            sort_order=20,
            image=SimpleUploadedFile("second.gif", image_bytes, content_type="image/gif"),
            caption="Второй ракурс",
        )

        response = self.client.get(reverse("learning_detail", args=[material.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-image-slider')
        self.assertContains(response, "Первый ракурс")
        self.assertContains(response, "Второй ракурс")
