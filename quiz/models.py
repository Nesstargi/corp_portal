from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


def normalize_answer_options(raw_options):
    cleaned_options = []

    if not isinstance(raw_options, list):
        return cleaned_options

    for item in raw_options:
        if not isinstance(item, dict):
            continue

        text = str(item.get("text") or "").strip()
        raw_is_correct = item.get("is_correct")
        if isinstance(raw_is_correct, str):
            is_correct = raw_is_correct.strip().lower() in {"1", "true", "yes", "on"}
        else:
            is_correct = bool(raw_is_correct)

        if not text:
            continue

        cleaned_options.append(
            {
                "text": text,
                "is_correct": is_correct,
            }
        )

    return cleaned_options


class Quiz(models.Model):
    title = models.CharField("Название теста", max_length=220)
    slug = models.SlugField("Внутренний адрес", max_length=240, unique=True, blank=True)
    summary = models.TextField("Краткое описание", blank=True)
    intro = models.TextField(
        "Вступление перед стартом",
        blank=True,
        help_text="Коротко объясни, чему поможет этот тест и на что обратить внимание.",
    )
    material = models.ForeignKey(
        "learning.LearningMaterial",
        related_name="quizzes",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Связанный обучающий материал",
    )
    completion_message = models.TextField(
        "Сообщение после прохождения",
        blank=True,
        default=(
            "Пройди вопросы ещё раз, если хочешь лучше закрепить материал. "
            "Тест здесь нужен не для оценки, а для самопроверки."
        ),
    )
    sort_order = models.PositiveIntegerField("Порядок показа", default=0)
    is_published = models.BooleanField("Показывать на сайте", default=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["sort_order", "title"]
        verbose_name = "Тест для самопроверки"
        verbose_name_plural = "Тесты для самопроверки"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "quiz"
            slug = base_slug
            counter = 2

            while Quiz.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("learning_quiz_detail", args=[self.slug])

    @property
    def question_total(self):
        prefetched_questions = getattr(self, "_prefetched_objects_cache", {}).get("questions")
        if prefetched_questions is not None:
            return len(prefetched_questions)
        return self.questions.count()


class QuizQuestion(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        related_name="questions",
        on_delete=models.CASCADE,
        verbose_name="Тест",
    )
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    prompt = models.TextField("Вопрос")
    explanation = models.TextField(
        "Объяснение правильного варианта",
        help_text="Это объяснение появится и при правильном, и при неправильном ответе.",
    )
    options_data = models.JSONField(
        "Варианты ответа",
        blank=True,
        default=list,
    )

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Вопрос теста"
        verbose_name_plural = "Вопросы теста"

    def __str__(self):
        return f"{self.quiz.title}: {self.prompt[:80]}"

    @property
    def answer_options(self):
        return normalize_answer_options(self.options_data)

    @property
    def correct_option(self):
        return next((item for item in self.answer_options if item["is_correct"]), None)

    @property
    def correct_option_text(self):
        correct_option = self.correct_option
        return correct_option["text"] if correct_option else ""

    def clean(self):
        cleaned_options = self.answer_options
        correct_count = sum(1 for item in cleaned_options if item["is_correct"])

        if len(cleaned_options) < 2:
            raise ValidationError(
                {
                    "options_data": (
                        "Добавь хотя бы два непустых варианта ответа, чтобы вопрос был полезным."
                    )
                }
            )

        if correct_count != 1:
            raise ValidationError(
                {
                    "options_data": (
                        "У вопроса должен быть ровно один правильный вариант ответа."
                    )
                }
            )
