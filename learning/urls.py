from django.urls import path

from quiz.views import quiz_detail, quiz_reset

from .views import learning_compare, learning_detail, learning_list


urlpatterns = [
    path("", learning_list, name="learning_list"),
    path("compare/", learning_compare, name="learning_compare"),
    path("tests/<slug:slug>/", quiz_detail, name="learning_quiz_detail"),
    path("tests/<slug:slug>/reset/", quiz_reset, name="learning_quiz_reset"),
    path("<int:pk>/", learning_detail, name="learning_detail"),
]
