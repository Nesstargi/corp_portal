from django.urls import path

from .views import news_detail, news_list


urlpatterns = [
    path("", news_list, name="news_list"),
    path("<int:pk>/", news_detail, name="news_detail"),
]
