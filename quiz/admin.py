from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Quiz, QuizQuestion, normalize_answer_options


class QuizOptionsWidget(forms.Textarea):
    def render(self, name, value, attrs=None, renderer=None):
        textarea = super().render(name, value, attrs=attrs, renderer=renderer)
        return mark_safe(
            '<div class="quiz-options-root">'
            f"{textarea}"
            '<div class="quiz-options-editor" data-quiz-options-editor></div>'
            "</div>"
        )


class QuizQuestionAdminForm(forms.ModelForm):
    class Meta:
        model = QuizQuestion
        fields = "__all__"
        widgets = {
            "options_data": QuizOptionsWidget(attrs={"class": "quiz-options-json", "rows": 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["prompt"].label = "Текст вопроса"
        self.fields["prompt"].help_text = (
            "Формулируй вопрос так, чтобы сотрудник действительно вспоминал материал, а не угадывал."
        )
        self.fields["explanation"].help_text = (
            "Это пояснение увидят после ответа. Оно должно обучать, а не просто сообщать правильный вариант."
        )
        self.fields["options_data"].required = False
        self.fields["options_data"].help_text = (
            "Ниже появится редактор вариантов ответа. Отметь один правильный вариант."
        )

    def clean_options_data(self):
        cleaned_options = normalize_answer_options(self.cleaned_data.get("options_data") or [])
        correct_count = sum(1 for item in cleaned_options if item["is_correct"])

        if len(cleaned_options) < 2:
            raise forms.ValidationError(
                "Добавь хотя бы два непустых варианта ответа, чтобы вопрос был полезным."
            )

        if correct_count != 1:
            raise forms.ValidationError(
                "У вопроса должен быть ровно один правильный вариант ответа."
            )

        return cleaned_options


class QuizQuestionInline(admin.StackedInline):
    model = QuizQuestion
    form = QuizQuestionAdminForm
    extra = 1
    verbose_name = "Вопрос"
    verbose_name_plural = "Вопросы теста"
    fieldsets = (
        (
            "Содержимое вопроса",
            {
                "fields": ("sort_order", "prompt", "explanation", "options_data"),
                "description": (
                    "Сначала задай вопрос, затем добавь варианты ответа. "
                    "После ответа сотрудник увидит пояснение, почему правильный вариант именно такой."
                ),
            },
        ),
    )


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    inlines = (QuizQuestionInline,)
    autocomplete_fields = ("material",)
    list_display = ("title", "material", "question_count", "is_published", "updated_at")
    list_display_links = ("title",)
    list_editable = ("is_published",)
    list_filter = ("is_published", "updated_at")
    search_fields = ("title", "summary", "intro", "material__title")
    readonly_fields = ("public_link", "created_at", "updated_at")
    fieldsets = (
        (
            "Карточка теста",
            {
                "fields": ("title", "summary", "intro", "completion_message"),
                "description": (
                    "Тест здесь работает как мягкий формат самопроверки: помоги сотруднику понять материал, "
                    "а не просто проверить себя по галочкам."
                ),
            },
        ),
        (
            "Связь с обучением",
            {
                "fields": ("material", "sort_order"),
                "description": (
                    "Если привязать тест к материалу, на странице обучения появится блок "
                    "«Проверить себя» с кнопкой запуска."
                ),
            },
        ),
        (
            "Публикация",
            {
                "fields": ("is_published", "public_link", "created_at", "updated_at"),
            },
        ),
    )

    class Media:
        css = {
            "all": ("css/quiz-admin.css",),
        }
        js = ("js/quiz-admin.js",)

    @admin.display(description="Вопросов")
    def question_count(self, obj):
        return obj.question_total

    @admin.display(description="Ссылка на тест")
    def public_link(self, obj):
        if not obj.pk or not obj.is_published:
            return "Ссылка появится после сохранения и публикации."

        return format_html(
            '<a href="{}" target="_blank" rel="noreferrer">Открыть тест на сайте</a>',
            reverse("learning_quiz_detail", args=[obj.slug]),
        )
