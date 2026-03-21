from django.db import models
from django.urls import reverse

from catalog.models import Brand, FeatureTag, ProductCategory


class News(models.Model):
    TELEGRAM_AUDIENCE_CHOICES = [
        ("all", "Всем подписчикам"),
        ("groups", "Только выбранным группам"),
        ("group_chats", "Только Telegram-группам"),
    ]

    CATEGORY_CHOICES = [
        ("product", "Новые модели"),
        ("corporate", "Корпоративные новости"),
        ("promotion", "Акции и спецпредложения"),
        ("instruction", "Инструкции и обновления"),
    ]

    title = models.CharField("Название новости", max_length=200)
    summary = models.TextField("Короткий анонс", blank=True)
    content = models.TextField("Основной текст", blank=True)
    category = models.CharField(
        "Тип новости",
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="corporate",
    )
    cover_image = models.ImageField(
        "Главное изображение",
        upload_to="news/covers/",
        blank=True,
        null=True,
    )
    brands = models.ManyToManyField(
        Brand,
        verbose_name="Какие бренды связаны",
        related_name="news_items",
        blank=True,
    )
    product_categories = models.ManyToManyField(
        ProductCategory,
        verbose_name="Какие категории товаров связаны",
        related_name="news_items",
        blank=True,
    )
    feature_tags = models.ManyToManyField(
        FeatureTag,
        verbose_name="Какие фишки и метки показать",
        related_name="news_items",
        blank=True,
    )
    telegram_audience = models.CharField(
        "Кому отправлять в Telegram",
        max_length=20,
        choices=TELEGRAM_AUDIENCE_CHOICES,
        default="all",
    )
    telegram_target_groups = models.ManyToManyField(
        "telegram_bot.TelegramAudienceGroup",
        verbose_name="Группы подписчиков Telegram",
        related_name="news_items",
        blank=True,
    )
    telegram_target_chat_collections = models.ManyToManyField(
        "telegram_bot.TelegramChatCollection",
        verbose_name="Объединения Telegram-групп",
        related_name="news_items",
        blank=True,
    )
    telegram_include_group_chats = models.BooleanField(
        "Также отправлять в группы Telegram",
        default=False,
    )
    created_at = models.DateTimeField("Когда создано", auto_now_add=True)
    updated_at = models.DateTimeField("Когда изменено", auto_now=True, null=True, blank=True)
    is_published = models.BooleanField("Показывать на сайте", default=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Новость"
        verbose_name_plural = "Новости"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("news_detail", args=[self.pk])

    @property
    def telegram_summary(self):
        return (self.summary or self.content or "").strip()


class NewsBlock(models.Model):
    BLOCK_TYPE_CHOICES = [
        ("text", "Текст"),
        ("image", "Изображение"),
        ("video", "Видео"),
        ("quote", "Цитата"),
        ("file", "Файл"),
    ]

    news = models.ForeignKey(
        News,
        related_name="blocks",
        on_delete=models.CASCADE,
        verbose_name="Новость",
    )
    sort_order = models.PositiveIntegerField("Порядок на странице", default=0)
    block_type = models.CharField(
        "Что добавить",
        max_length=20,
        choices=BLOCK_TYPE_CHOICES,
        default="text",
    )
    title = models.CharField("Заголовок блока", max_length=200, blank=True)
    text = models.TextField("Текст", blank=True)
    image = models.ImageField(
        "Изображение",
        upload_to="news/blocks/images/",
        blank=True,
        null=True,
    )
    video_url = models.URLField("Ссылка на видео", blank=True)
    document = models.FileField(
        "Файл",
        upload_to="news/blocks/files/",
        blank=True,
        null=True,
    )
    caption = models.CharField("Подпись или пояснение", max_length=255, blank=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Блок новости"
        verbose_name_plural = "Блоки новости"

    def __str__(self):
        return f"{self.news.title} [{self.get_block_type_display()}]"
