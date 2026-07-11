import json
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .admin import LearningBlockAdminForm, LearningBlockInline
from .models import LearningBlock, LearningMaterial


class LearningAdminBlockEditorRedesignTests(TestCase):
    requested_block_types = (
        "text",
        "image",
        "video",
        "feature",
        "sales_script",
        "specification",
        "comparison_table",
        "table",
    )

    @staticmethod
    def create_material(**overrides):
        values = {
            "title": "Материал для проверки редактора",
            "summary": "Краткое описание для карточки.",
            "material_type": "instruction",
            "is_published": True,
        }
        values.update(overrides)
        return LearningMaterial.objects.create(**values)

    @staticmethod
    def block_form_data(material, block_type, **overrides):
        values = {
            "material": str(material.pk),
            "sort_order": "10",
            "block_type": block_type,
            "title": "Проверочный блок",
            "text": "",
            "video_url": "",
            "caption": "",
            "items_data": json.dumps([]),
        }
        values.update(overrides)
        return values

    def test_new_block_form_has_exactly_eight_requested_choices(self):
        form = LearningBlockAdminForm()

        choice_keys = tuple(value for value, _label in form.fields["block_type"].choices)

        self.assertEqual(choice_keys, self.requested_block_types)
        self.assertEqual(len(choice_keys), 8)

    def test_existing_legacy_block_keeps_its_choice_when_saved(self):
        material = self.create_material()
        block = LearningBlock.objects.create(
            material=material,
            sort_order=10,
            block_type="quote",
            title="Старый блок-цитата",
            text="Содержимое старого блока должно сохраниться.",
        )
        form = LearningBlockAdminForm(
            data=self.block_form_data(
                material,
                "quote",
                title=block.title,
                text=block.text,
            ),
            instance=block,
        )

        choice_keys = tuple(value for value, _label in form.fields["block_type"].choices)
        self.assertIn("quote", choice_keys)
        self.assertTrue(form.is_valid(), form.errors)

        saved_block = form.save()
        saved_block.refresh_from_db()
        self.assertEqual(saved_block.block_type, "quote")
        self.assertEqual(saved_block.text, "Содержимое старого блока должно сохраниться.")

    def test_block_inline_does_not_add_an_empty_form_automatically(self):
        self.assertEqual(LearningBlockInline.extra, 0)

    def test_sales_script_renders_new_description_and_legacy_pitch(self):
        material = self.create_material()
        LearningBlock.objects.create(
            material=material,
            sort_order=10,
            block_type="sales_script",
            title="Скрипты и возражения",
            items_data=[
                {
                    "title": "Новый формат",
                    "description": "Описание из нового поля description.",
                },
                {
                    "title": "Старый формат",
                    "pitch": "Старый текст из поля pitch.",
                },
            ],
        )

        response = self.client.get(reverse("learning_detail", args=[material.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Описание из нового поля description.")
        self.assertContains(response, "Старый текст из поля pitch.")

    def test_comparison_with_blank_middle_model_keeps_value_alignment(self):
        material = self.create_material()
        form = LearningBlockAdminForm(
            data=self.block_form_data(
                material,
                "comparison_table",
                title="Сравнение трёх позиций",
                items_data=json.dumps(
                    {
                        "models": ["Товар A", "", "Товар C"],
                        "rows": [
                            {
                                "parameter": "Мощность",
                                "values": [
                                    "Значение товара A",
                                    "Значение пустой колонки",
                                    "Значение товара C",
                                ],
                            }
                        ],
                    }
                ),
            ),
            instance=LearningBlock(material=material),
        )

        self.assertTrue(form.is_valid(), form.errors)
        block = form.save()
        self.assertEqual(block.items_data["models"], ["Товар A", "Товар C"])
        self.assertEqual(
            block.items_data["rows"][0]["values"],
            ["Значение товара A", "Значение товара C"],
        )

        response = self.client.get(reverse("learning_detail", args=[material.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Значение товара A")
        self.assertContains(response, "Значение товара C")
        self.assertNotContains(response, "Значение пустой колонки")

    def test_product_content_is_rendered_without_blocks(self):
        material = self.create_material(
            material_type="product",
            content="<p>Старый общий текст товара без блочного содержимого.</p>",
        )

        response = self.client.get(reverse("learning_detail", args=[material.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Старый общий текст товара без блочного содержимого.")

    def test_legacy_single_image_caption_is_not_duplicated(self):
        image_bytes = (
            b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00"
            b"\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        caption = "Единственная подпись старого изображения"

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            material = self.create_material()
            LearningBlock.objects.create(
                material=material,
                sort_order=10,
                block_type="image",
                title="Старое одиночное изображение",
                caption=caption,
                image=SimpleUploadedFile(
                    "legacy-image.gif",
                    image_bytes,
                    content_type="image/gif",
                ),
            )

            response = self.client.get(reverse("learning_detail", args=[material.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode("utf-8").count(caption), 1)

    def test_youtube_video_block_is_embedded(self):
        material = self.create_material()
        block = LearningBlock.objects.create(
            material=material,
            sort_order=10,
            block_type="video",
            title="Видеообзор",
            video_url="https://www.youtube.com/watch?v=video123",
        )

        response = self.client.get(reverse("learning_detail", args=[material.pk]))

        self.assertEqual(
            block.video_embed_url,
            "https://www.youtube-nocookie.com/embed/video123"
            "?rel=0&modestbranding=1&playsinline=1",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<iframe", html=False)
        self.assertContains(
            response,
            "https://www.youtube-nocookie.com/embed/video123",
        )
        self.assertNotContains(response, "Открыть видео")
