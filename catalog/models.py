from django.db import models
from django.utils.text import slugify


class BaseDirectory(models.Model):
    name = models.CharField("Название", max_length=120, unique=True)
    slug = models.SlugField("Внутренний адрес", max_length=140, unique=True, blank=True)
    description = models.TextField("Короткое пояснение", blank=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def build_unique_slug(self):
        base_slug = slugify(self.slug or self.name, allow_unicode=True)
        if not base_slug:
            base_slug = self.__class__.__name__.lower()

        slug = base_slug
        queryset = self.__class__.objects.all()
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        counter = 2
        while queryset.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def save(self, *args, **kwargs):
        self.slug = self.build_unique_slug()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(BaseDirectory):
    class Meta(BaseDirectory.Meta):
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"


class ProductCharacteristic(BaseDirectory):
    class Meta(BaseDirectory.Meta):
        verbose_name = "Характеристика"
        verbose_name_plural = "Характеристики"


class ProductCategory(BaseDirectory):
    characteristics = models.ManyToManyField(
        "ProductCharacteristic",
        through="ProductCategoryCharacteristic",
        verbose_name="Назначенные характеристики",
        related_name="product_categories",
        blank=True,
    )

    class Meta(BaseDirectory.Meta):
        verbose_name = "Категория товара"
        verbose_name_plural = "Категории товаров"


class ProductCategoryCharacteristic(models.Model):
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.CASCADE,
        related_name="characteristic_links",
        verbose_name="Категория товара",
    )
    characteristic = models.ForeignKey(
        ProductCharacteristic,
        on_delete=models.CASCADE,
        related_name="category_links",
        verbose_name="Характеристика",
    )
    sort_order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["sort_order", "characteristic__name"]
        unique_together = ("category", "characteristic")
        verbose_name = "Связь категории и характеристики"
        verbose_name_plural = "Связи категорий и характеристик"

    def __str__(self):
        return f"{self.category.name} -> {self.characteristic.name}"


class KnowledgeArea(BaseDirectory):
    class Meta(BaseDirectory.Meta):
        verbose_name = "Область знаний"
        verbose_name_plural = "Области знаний"


class FeatureTag(BaseDirectory):
    class Meta(BaseDirectory.Meta):
        verbose_name = "Фишка или метка"
        verbose_name_plural = "Фишки и метки"
