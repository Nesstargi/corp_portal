from pathlib import Path
from urllib.parse import parse_qs, urlparse

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from catalog.models import Brand, FeatureTag, KnowledgeArea, ProductCategory, ProductCharacteristic


def flatten_json_text(value):
    parts = []

    def collect(item):
        if isinstance(item, dict):
            for nested_value in item.values():
                collect(nested_value)
        elif isinstance(item, list):
            for nested_value in item:
                collect(nested_value)
        elif item not in (None, ""):
            parts.append(str(item))

    collect(value)
    return " ".join(part.strip() for part in parts if part and part.strip())


def build_youtube_embed_url(raw_url):
    raw_url = (raw_url or "").strip()
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
        verbose_name = "Материал базы знаний"
        verbose_name_plural = "База знаний"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("learning_detail", args=[self.pk])

    @property
    def toc_blocks(self):
        return [
            {
                "number": index,
                "title": block.title.strip(),
            }
            for index, block in enumerate(self.blocks.all(), start=1)
            if block.title.strip()
        ]

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
        return build_youtube_embed_url(self.product_video_review_url)

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
        ("feature", "Фишка"),
        ("sales_script", "Скрипт продаж"),
        ("instruction_step", "Шаг инструкции"),
        ("specification", "Характеристика"),
        ("table", "Таблица"),
        ("comparison_table", "Сравнительная таблица"),
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
    items_data = models.JSONField("Внутренние элементы блока", blank=True, default=list)
    items_text = models.TextField("Текст внутренних элементов", blank=True, editable=False)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Блок материала"
        verbose_name_plural = "Блоки материала"

    def __str__(self):
        return f"{self.material.title} [{self.get_block_type_display()}]"

    def save(self, *args, **kwargs):
        self.items_text = flatten_json_text(self.items_data)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "items_data" in update_fields:
            kwargs["update_fields"] = set(update_fields) | {"items_text"}
        super().save(*args, **kwargs)

    @property
    def structured_items(self):
        if not isinstance(self.items_data, list):
            return []

        cleaned_items = []
        for item in self.items_data:
            if not isinstance(item, dict):
                continue
            cleaned_items.append(
                {
                    "sort_order": str(item.get("sort_order") or "").strip(),
                    "characteristic_id": str(item.get("characteristic_id") or "").strip(),
                    "title": str(item.get("title") or "").strip(),
                    "description": str(item.get("description") or "").strip(),
                    "pitch": str(item.get("pitch") or "").strip(),
                    "name": str(item.get("name") or "").strip(),
                    "value": str(item.get("value") or "").strip(),
                }
            )
        return cleaned_items

    @property
    def comparison_table(self):
        if not isinstance(self.items_data, dict):
            return {"models": [], "rows": []}

        raw_models = self.items_data.get("models") or []
        models = [
            str(model or "").strip()
            for model in raw_models
            if str(model or "").strip()
        ]
        rows = []

        for row in self.items_data.get("rows") or []:
            if not isinstance(row, dict):
                continue

            parameter = str(row.get("parameter") or "").strip()
            raw_values = row.get("values") or []
            if not isinstance(raw_values, list):
                raw_values = []
            values = [
                str(raw_values[index] or "").strip()
                if index < len(raw_values)
                else ""
                for index in range(len(models))
            ]

            if parameter or any(values):
                rows.append(
                    {
                        "parameter": parameter,
                        "values": values,
                    }
                )

        return {"models": models, "rows": rows}

    @property
    def manual_table(self):
        if not isinstance(self.items_data, dict):
            return {"headers": [], "rows": []}

        raw_headers = self.items_data.get("headers") or []
        if not isinstance(raw_headers, list):
            raw_headers = []
        headers = [
            str(raw_headers[index] or "").strip()
            if index < len(raw_headers)
            else ""
            for index in range(2)
        ]
        rows = []

        for row in self.items_data.get("rows") or []:
            if not isinstance(row, dict):
                continue

            left = str(row.get("left") or "").strip()
            right = str(row.get("right") or "").strip()
            if left or right:
                rows.append({"left": left, "right": right})

        return {"headers": headers, "rows": rows}

    @property
    def gallery_items(self):
        items = [
            {
                "image": gallery_item.image,
                "caption": gallery_item.caption,
            }
            for gallery_item in self.gallery_images.all()
            if gallery_item.image
        ]

        if not items and self.image:
            items.append(
                {
                    "image": self.image,
                    "caption": self.caption,
                }
            )

        return items


class LearningBlockGalleryImage(models.Model):
    block = models.ForeignKey(
        LearningBlock,
        related_name="gallery_images",
        on_delete=models.CASCADE,
        verbose_name="Блок",
    )
    sort_order = models.PositiveIntegerField("Порядок в слайдере", default=0)
    image = models.ImageField(
        "Изображение",
        upload_to="learning/blocks/gallery/",
    )
    caption = models.CharField("Подпись", max_length=255, blank=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Изображение блока"
        verbose_name_plural = "Изображения блока"

    def __str__(self):
        return self.caption or f"{self.block} - изображение"


def validate_presentation_file(value):
    extension = Path(value.name or "").suffix.lower()
    if extension != ".pptx":
        raise ValidationError("Загрузите презентацию в формате .pptx.")


class PresentationImport(models.Model):
    title = models.CharField("Название материала", max_length=220, blank=True)
    presentation = models.FileField(
        "Презентация .pptx",
        upload_to="learning/presentations/",
        validators=[validate_presentation_file],
        help_text="После сохранения из текста слайдов будет создан материал базы знаний.",
    )
    publish_material = models.BooleanField(
        "Сразу опубликовать материал",
        default=False,
        help_text="Если выключено, материал создастся скрытым и его можно будет проверить перед публикацией.",
    )
    material = models.OneToOneField(
        LearningMaterial,
        verbose_name="Созданный материал",
        related_name="presentation_import",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    import_report = models.TextField("Отчёт импорта", blank=True)
    created_at = models.DateTimeField("Загружено", auto_now_add=True)
    updated_at = models.DateTimeField("Изменено", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Импорт презентации"
        verbose_name_plural = "Импорт презентаций"

    def __str__(self):
        return self.title or Path(self.presentation.name or "Презентация").stem

    @property
    def resolved_title(self):
        if self.title:
            return self.title
        return Path(self.presentation.name or "Материал из презентации").stem or "Материал из презентации"
