from django.urls import path

from .views import promotion_detail, promotion_list


urlpatterns = [
    path("", promotion_list, name="promotion_list"),
    path("<slug:slug>/", promotion_detail, name="promotion_detail"),
]
