from django.urls import path

from .views import learning_detail, learning_list


urlpatterns = [
    path("", learning_list, name="learning_list"),
    path("<int:pk>/", learning_detail, name="learning_detail"),
]
