from urllib.parse import parse_qs, urlparse

from django.db import models
from django.urls import reverse

from catalog.models import Brand, FeatureTag, KnowledgeArea, ProductCategory, ProductCharacteristic


class LearningMaterial(models.Model):
    TELEGRAM_AUDIENCE_CHOICES = [
        ("all", "Всем личным подписчикам"),
        ("all_with_groups", "Всем личным подписчикам и всем Telegram-группам"),
        ("group_chats", "Только Telegram-группам"),
        ("custom", "Только выбранной аудитории"),
    ]

    MATERIAL_TYPE_CHOICES = [
        ("process", "Процесс"),
        ("product", "Товар"),
        ("instruction", "Инструкция"),
        ("promotion", "Акция"),
        ("credit", "Кредитный продукт"),
        ("reference", "Справочник"),
    ]

    title = models.CharField("Название материала", max_length=220)
    summary = models.TextField("Краткое описание для превью", blank=True)
    content = models.TextField("Общий текст материала", blank=True)
    product_full_description = models.TextField("Полное описание товара", blank=True)
    product_video_review_url = models.URLField(
        "Ссылка на видеообзор YouTube",
        blank=True,
    )
    product_text_review = models.TextField("Обзор текстом", blank=True)
    product_short_summary = models.TextField("Краткое резюмирование", blank=True)
    material_type = models.CharField(
        "Тип материала",
        max_length=30,
        choices=MATERIAL_TYPE_CHOICES,
        default="instruction",
    )
    cover_image = models.ImageField(
        "Главное изображение",
        upload_to="learning/covers/",
        blank=True,
        null=True,
    )
    brands = models.ManyToManyField(
        Brand,
        verbose_name="Какие бренды связаны",
        related_name="learning_materials",
        blank=True,
    )
    categories = models.ManyToManyField(
        ProductCategory,
        verbose_name="Какие категории товаров связаны",
        related_name="learning_materials",
        blank=True,
    )
    areas = models.ManyToManyField(
        KnowledgeArea,
        verbose_name="К каким темам относится",
        related_name="learning_materials",
        blank=True,
    )
    feature_tags = models.ManyToManyField(
        FeatureTag,
        verbose_name="Какие фишки и метки показать",
        related_name="learning_materials",
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
        verbose_name="Группы личных подписчиков Telegram",
        related_name="learning_materials",
        blank=True,
    )
    telegram_target_subscribers = models.ManyToManyField(
        "telegram_bot.TelegramSubscriber",
        verbose_name="Отдельные получатели Telegram",
        related_name="direct_learning_materials",
        blank=True,
    )
    telegram_target_group_chats = models.ManyToManyField(
        "telegram_bot.TelegramSubscriber",
        verbose_name="Отдельные Telegram-группы",
        related_name="group_learning_materials",
        blank=True,
    )
    telegram_target_chat_collections = models.ManyToManyField(
        "telegram_bot.TelegramChatCollection",
        verbose_name="Объединения Telegram-групп",
        related_name="learning_materials",
        blank=True,
    )
    telegram_include_group_chats = models.BooleanField(
        "Также отправлять в группы Telegram",
        default=False,
    )
    created_at = models.DateTimeField("Когда создано", auto_now_add=True)
    updated_at = models.DateTimeField("Когда изменено", auto_now=True)
    is_published = models.BooleanField("Показывать на сайте", default=True)

    class Meta:
        ordering = ["title"]
        verbose_name = "Материал для обучения"
        verbose_name_plural = "Материалы для обучения"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("learning_detail", args=[self.pk])

    @property
    def telegram_summary(self):
        return (
            self.summary
            or self.product_short_summary
            or self.product_full_description
            or self.content
            or ""
        ).strip()

    @property
    def product_video_embed_url(self):
        raw_url = (self.product_video_review_url or "").strip()
        if not raw_url:
            return ""

        parsed = urlparse(raw_url)
        host = parsed.netloc.lower()
        video_id = ""

        if "youtu.be" in host:
            video_id = parsed.path.strip("/")
        elif "youtube.com" in host or "youtube-nocookie.com" in host:
            if parsed.path == "/watch":
                video_id = parse_qs(parsed.query).get("v", [""])[0]
            elif parsed.path.startswith("/shorts/") or parsed.path.startswith("/embed/"):
                video_id = parsed.path.strip("/").split("/")[-1]

        if video_id:
            return (
                "https://www.youtube-nocookie.com/embed/"
                f"{video_id}?rel=0&modestbranding=1&playsinline=1"
            )

        return ""

    @property
    def has_structured_product_content(self):
        return any(
            [
                self.product_full_description,
                self.product_video_review_url,
                self.product_text_review,
                self.product_short_summary,
                self.product_description_images.exists(),
                self.product_review_images.exists(),
                self.product_features.exists(),
                self.product_sales_scripts.exists(),
                self.product_specifications.exists(),
            ]
        )


class ProductDescriptionImage(models.Model):
    material = models.ForeignKey(
        LearningMaterial,
        related_name="product_description_images",
        on_delete=models.CASCADE,
        verbose_name="Материал",
    )
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    image = models.ImageField(
        "Изображение",
        upload_to="learning/product/description/",
    )
    caption = models.CharField("Подпись", max_length=255, blank=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Изображение для полного описания"
        verbose_name_plural = "Изображения для полного описания"

    def __str__(self):
        return self.caption or f"{self.material.title} - описание"


class ProductReviewImage(models.Model):
    material = models.ForeignKey(
        LearningMaterial,
        related_name="product_review_images",
        on_delete=models.CASCADE,
        verbose_name="Материал",
    )
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    image = models.ImageField(
        "Изображение",
        upload_to="learning/product/review/",
    )
    caption = models.CharField("Подпись", max_length=255, blank=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Изображение для текстового обзора"
        verbose_name_plural = "Изображения для текстового обзора"

    def __str__(self):
        return self.caption or f"{self.material.title} - обзор"


class ProductFeature(models.Model):
    material = models.ForeignKey(
        LearningMaterial,
        related_name="product_features",
        on_delete=models.CASCADE,
        verbose_name="Материал",
    )
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    title = models.CharField("Название фишки", max_length=220)
    description = models.TextField("Описание фишки", blank=True)
    client_pitch = models.TextField("Как преподносить клиенту", blank=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Фишка товара"
        verbose_name_plural = "Фишки товара"

    def __str__(self):
        return self.title


class ProductSalesScript(models.Model):
    material = models.ForeignKey(
        LearningMaterial,
        related_name="product_sales_scripts",
        on_delete=models.CASCADE,
        verbose_name="Материал",
    )
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    title = models.CharField("Название скрипта", max_length=220)
    script_text = models.TextField("Текст скрипта")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Скрипт продаж"
        verbose_name_plural = "Скрипты продаж"

    def __str__(self):
        return self.title


class ProductSpecification(models.Model):
    material = models.ForeignKey(
        LearningMaterial,
        related_name="product_specifications",
        on_delete=models.CASCADE,
        verbose_name="Материал",
    )
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    characteristic = models.ForeignKey(
        ProductCharacteristic,
        related_name="material_specifications",
        on_delete=models.SET_NULL,
        verbose_name="Характеристика",
        blank=True,
        null=True,
    )
    name = models.CharField("Название характеристики", max_length=220)
    value = models.CharField("Значение", max_length=255)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Характеристика товара"
        verbose_name_plural = "Характеристики товара"

    def save(self, *args, **kwargs):
        if self.characteristic:
            self.name = self.characteristic.name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.characteristic.name if self.characteristic else self.name


class LearningBlock(models.Model):
    BLOCK_TYPE_CHOICES = [
        ("text", "Текст"),
        ("image", "Изображение"),
        ("video", "Видео"),
        ("quote", "Цитата"),
        ("file", "Файл"),
    ]

    material = models.ForeignKey(
        LearningMaterial,
        related_name="blocks",
        on_delete=models.CASCADE,
        verbose_name="Материал",
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
        upload_to="learning/blocks/images/",
        blank=True,
        null=True,
    )
    video_url = models.URLField("Ссылка на видео", blank=True)
    document = models.FileField(
        "Файл",
        upload_to="learning/blocks/files/",
        blank=True,
        null=True,
    )
    caption = models.CharField("Подпись или пояснение", max_length=255, blank=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Блок материала"
        verbose_name_plural = "Блоки материала"

    def __str__(self):
        return f"{self.material.title} [{self.get_block_type_display()}]"
