from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Quiz


def get_quiz_progress_key(quiz):
    return f"quiz-progress-{quiz.pk}"


def get_quiz_progress(request, quiz):
    progress = request.session.get(get_quiz_progress_key(quiz), {})
    answers = progress.get("answers")
    if not isinstance(answers, dict):
        answers = {}
    return {"answers": answers}


def save_quiz_progress(request, quiz, progress):
    request.session[get_quiz_progress_key(quiz)] = progress
    request.session.modified = True


def clear_quiz_progress(request, quiz):
    request.session.pop(get_quiz_progress_key(quiz), None)
    request.session.modified = True


def build_step_items(questions, answers_map, current_step):
    step_items = []

    for index, question in enumerate(questions, start=1):
        answer_state = answers_map.get(str(question.pk)) or {}
        step_items.append(
            {
                "number": index,
                "is_current": index == current_step,
                "is_answered": bool(answer_state),
                "is_correct": bool(answer_state.get("is_correct")),
            }
        )

    return step_items


def build_question_feedback(question, selected_index):
    options = question.answer_options
    selected_option = options[selected_index]
    is_correct = bool(selected_option["is_correct"])

    return {
        "is_correct": is_correct,
        "tone": "correct" if is_correct else "incorrect",
        "title": "Да, это правильный ответ." if is_correct else "Нет, ответ неправильный.",
        "selected_option_text": selected_option["text"],
        "correct_option_text": question.correct_option_text,
        "explanation": question.explanation,
    }


def build_summary_items(questions, answers_map):
    summary_items = []

    for index, question in enumerate(questions, start=1):
        answer_state = answers_map.get(str(question.pk)) or {}
        selected_index = answer_state.get("selected_index")
        options = question.answer_options
        selected_option_text = ""

        if isinstance(selected_index, int) and 0 <= selected_index < len(options):
            selected_option_text = options[selected_index]["text"]

        summary_items.append(
            {
                "number": index,
                "prompt": question.prompt,
                "is_answered": bool(answer_state),
                "is_correct": bool(answer_state.get("is_correct")),
                "selected_option_text": selected_option_text,
                "correct_option_text": question.correct_option_text,
                "explanation": question.explanation,
            }
        )

    return summary_items


def resolve_current_step(step_param, questions, answers_map):
    question_total = len(questions)
    if not question_total:
        return 1, False

    if step_param == "summary":
        return question_total + 1, True

    if step_param:
        try:
            requested_step = int(step_param)
        except ValueError:
            requested_step = 0
        if requested_step >= 1:
            if requested_step > question_total:
                return question_total + 1, True
            return requested_step, False

    for index, question in enumerate(questions, start=1):
        if str(question.pk) not in answers_map:
            return index, False

    return question_total + 1, True


def quiz_detail(request, slug):
    raise Http404("Тесты временно отключены.")


@require_POST
def quiz_reset(request, slug):
    raise Http404("Тесты временно отключены.")
