import json

from django.test import TestCase
from django.urls import reverse

from learning.models import LearningMaterial

from .admin import QuizQuestionAdminForm
from .models import Quiz, QuizQuestion


class QuizFlowTests(TestCase):
    def setUp(self):
        self.material = LearningMaterial.objects.create(
            title="Dreame L10s Ultra",
            summary="Материал про позиционирование модели.",
            material_type="product",
            is_published=True,
        )
        self.quiz = Quiz.objects.create(
            title="Проверь, как запомнился Dreame L10s Ultra",
            summary="Небольшая самопроверка после чтения материала.",
            intro="Отвечай спокойно: после каждого вопроса портал сразу объяснит правильный вариант.",
            material=self.material,
            is_published=True,
        )
        self.question_one = QuizQuestion.objects.create(
            quiz=self.quiz,
            sort_order=10,
            prompt="Что лучше подчеркнуть, если клиенту важна минимальная ручная работа после уборки?",
            explanation="Правильный акцент здесь — станция самообслуживания, потому что она снимает с клиента часть рутины.",
            options_data=[
                {"text": "Только дизайн корпуса", "is_correct": False},
                {"text": "Станцию самообслуживания", "is_correct": True},
                {"text": "Любую случайную скидку", "is_correct": False},
            ],
        )
        self.question_two = QuizQuestion.objects.create(
            quiz=self.quiz,
            sort_order=20,
            prompt="Какой аргумент лучше использовать для клиента с животными?",
            explanation="Для такого сценария важен акцент на регулярной уборке шерсти и уменьшении ручного труда.",
            options_data=[
                {"text": "Сказать только про красивую упаковку", "is_correct": False},
                {"text": "Подчеркнуть удобство регулярной уборки шерсти", "is_correct": True},
            ],
        )

    def test_question_admin_form_requires_exactly_one_correct_option(self):
        form = QuizQuestionAdminForm(
            data={
                "quiz": str(self.quiz.pk),
                "sort_order": "30",
                "prompt": "Тестовый вопрос",
                "explanation": "Пояснение",
                "options_data": json.dumps(
                    [
                        {"text": "Вариант 1", "is_correct": True},
                        {"text": "Вариант 2", "is_correct": True},
                    ]
                ),
            },
            instance=QuizQuestion(quiz=self.quiz),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("ровно один правильный", form.errors["options_data"][0])

    def test_learning_detail_hides_linked_quiz_card(self):
        response = self.client.get(reverse("learning_detail", args=[self.material.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Тесты по этому материалу")
        self.assertNotContains(response, self.quiz.title)
        self.assertNotContains(response, "Проверить себя")

    def test_quiz_detail_is_temporarily_disabled(self):
        response = self.client.get(reverse("learning_quiz_detail", args=[self.quiz.slug]))

        self.assertEqual(response.status_code, 404)

    def test_quiz_reset_is_temporarily_disabled(self):
        response = self.client.post(reverse("learning_quiz_reset", args=[self.quiz.slug]))

        self.assertEqual(response.status_code, 404)
