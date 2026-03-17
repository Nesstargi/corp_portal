from django.db import models
from django.utils.text import slugify


class BaseDirectory(models.Model):
    name = models.CharField("Название", max_length=120, unique=True)
    slug = models.SlugField("Внутренний адрес", max_length=140, unique=True, blank=True)
    description = models.TextField("Короткое пояснение", blank=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(BaseDirectory):
    class Meta(BaseDirectory.Meta):
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"


class ProductCategory(BaseDirectory):
    class Meta(BaseDirectory.Meta):
        verbose_name = "Категория товара"
        verbose_name_plural = "Категории товаров"


class KnowledgeArea(BaseDirectory):
    class Meta(BaseDirectory.Meta):
        verbose_name = "Область знаний"
        verbose_name_plural = "Области знаний"


class FeatureTag(BaseDirectory):
    class Meta(BaseDirectory.Meta):
        verbose_name = "Фишка или метка"
        verbose_name_plural = "Фишки и метки"
