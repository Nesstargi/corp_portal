from django import forms
from django.contrib import admin

from catalog.widgets import RichTextToolbarWidget

from .models import News, NewsBlock


class NewsBlockAdminForm(forms.ModelForm):
    class Meta:
        model = NewsBlock
        fields = "__all__"
        widgets = {
            "text": RichTextToolbarWidget(),
        }


class NewsBlockInline(admin.StackedInline):
    model = NewsBlock
    form = NewsBlockAdminForm
    extra = 1
    verbose_name = "Блок содержимого"
    verbose_name_plural = "Блоки содержимого"
    fieldsets = (
        (
            "Основное",
            {
                "fields": ("sort_order", "block_type", "title", "caption"),
                "description": "Например: текст, изображение, видео, цитата или файл.",
            },
        ),
        (
            "Содержимое блока",
            {
                "fields": ("text", "image", "video_url", "document"),
            },
        ),
    )


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "created_at", "is_published")
    list_filter = ("category", "is_published", "created_at")
    search_fields = ("title", "summary", "content")
    list_editable = ("is_published",)
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("brands", "product_categories", "feature_tags")
    inlines = [NewsBlockInline]
    fieldsets = (
        (
            "Основная информация",
            {
                "fields": ("title", "summary", "content", "cover_image"),
            },
        ),
        (
            "Где и как показывать",
            {
                "fields": ("category", "is_published"),
            },
        ),
        (
            "Связь с товарами и фишками",
            {
                "fields": ("brands", "product_categories", "feature_tags"),
            },
        ),
        (
            "Служебная информация",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
