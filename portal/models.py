from datetime import date

from django.db import models
from django.utils.text import slugify
from modelcluster.fields import ParentalManyToManyField
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.embeds.blocks import EmbedBlock
from wagtail.fields import StreamField
from wagtail.images import get_image_model_string
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Page
from wagtail.search import index
from wagtail.snippets.models import register_snippet


CONTENT_STREAM_BLOCKS = [
    ("heading", blocks.CharBlock(form_classname="title")),
    (
        "paragraph",
        blocks.RichTextBlock(
            features=[
                "h2",
                "h3",
                "bold",
                "italic",
                "link",
                "ol",
                "ul",
                "hr",
                "document-link",
                "embed",
            ]
        ),
    ),
    ("image", ImageChooserBlock()),
    ("video", EmbedBlock()),
    ("quote", blocks.BlockQuoteBlock()),
    ("document", DocumentChooserBlock()),
]


class BaseSnippet(models.Model):
    name = models.CharField("Название", max_length=120, unique=True)
    slug = models.SlugField("Слаг", max_length=140, unique=True, blank=True)
    description = models.TextField("Описание", blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("description"),
    ]

    class Meta:
        abstract = True
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


@register_snippet
class Brand(BaseSnippet):
    class Meta(BaseSnippet.Meta):
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"


@register_snippet
class ProductCategory(BaseSnippet):
    class Meta(BaseSnippet.Meta):
        verbose_name = "Товарная категория"
        verbose_name_plural = "Товарные категории"


@register_snippet
class KnowledgeArea(BaseSnippet):
    class Meta(BaseSnippet.Meta):
        verbose_name = "Область знаний"
        verbose_name_plural = "Области знаний"


class HomePage(Page):
    intro = models.TextField(
        "Вступление",
        blank=True,
        default=(
            "Единая точка доступа к новостям компании, обучающим материалам, "
            "акциям и внутренним справочникам."
        ),
    )

    max_count = 1
    subpage_types = ["portal.NewsIndexPage", "portal.LearningIndexPage"]

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]


class NewsIndexPage(Page):
    intro = models.TextField(
        "Описание раздела",
        blank=True,
        default="Новости о новых моделях, внутренних изменениях, акциях и жизни компании.",
    )

    parent_page_types = ["portal.HomePage"]
    subpage_types = ["portal.NewsPage"]

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["news_items"] = (
            NewsPage.objects.live()
            .public()
            .descendant_of(self)
            .order_by("-publish_date", "-first_published_at")
        )
        return context


class NewsPage(Page):
    CATEGORY_CHOICES = [
        ("product", "Новые модели"),
        ("corporate", "Корпоративные новости"),
        ("promotion", "Акции и спецпредложения"),
        ("instruction", "Инструкции и обновления процессов"),
    ]

    summary = models.TextField("Краткое описание", max_length=300, blank=True)
    category = models.CharField(
        "Категория новости",
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="corporate",
    )
    publish_date = models.DateField("Дата публикации", default=date.today)
    hero_image = models.ForeignKey(
        get_image_model_string(),
        verbose_name="Главное изображение",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    brands = ParentalManyToManyField("portal.Brand", blank=True)
    categories = ParentalManyToManyField("portal.ProductCategory", blank=True)
    body = StreamField(CONTENT_STREAM_BLOCKS, blank=True, verbose_name="Содержимое")

    parent_page_types = ["portal.NewsIndexPage"]
    subpage_types = []

    search_fields = Page.search_fields + [
        index.SearchField("summary"),
        index.SearchField("body"),
        index.FilterField("category"),
        index.FilterField("publish_date"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("summary"),
        MultiFieldPanel(
            [
                FieldPanel("category"),
                FieldPanel("publish_date"),
                FieldPanel("hero_image"),
            ],
            heading="Публикация",
        ),
        MultiFieldPanel(
            [
                FieldPanel("brands"),
                FieldPanel("categories"),
            ],
            heading="Связанные товары",
        ),
        FieldPanel("body"),
    ]


class LearningIndexPage(Page):
    intro = models.TextField(
        "Описание раздела",
        blank=True,
        default=(
            "Материалы по процессам компании, 1С, брендам, кредитным продуктам "
            "и товарным категориям."
        ),
    )

    parent_page_types = ["portal.HomePage"]
    subpage_types = ["portal.LearningMaterialPage"]

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)

        selected_brand = request.GET.get("brand", "")
        selected_category = request.GET.get("category", "")
        selected_area = request.GET.get("area", "")
        selected_type = request.GET.get("type", "")

        materials = (
            LearningMaterialPage.objects.live()
            .public()
            .descendant_of(self)
            .order_by("title")
        )

        if selected_brand:
            materials = materials.filter(brands__slug=selected_brand)
        if selected_category:
            materials = materials.filter(categories__slug=selected_category)
        if selected_area:
            materials = materials.filter(areas__slug=selected_area)
        if selected_type:
            materials = materials.filter(material_type=selected_type)

        context.update(
            {
                "materials": materials.distinct(),
                "brands": Brand.objects.all(),
                "product_categories": ProductCategory.objects.all(),
                "knowledge_areas": KnowledgeArea.objects.all(),
                "material_types": LearningMaterialPage.MATERIAL_TYPE_CHOICES,
                "selected_brand": selected_brand,
                "selected_category": selected_category,
                "selected_area": selected_area,
                "selected_type": selected_type,
            }
        )
        return context


class LearningMaterialPage(Page):
    MATERIAL_TYPE_CHOICES = [
        ("process", "Процесс"),
        ("product", "Товар"),
        ("instruction", "Инструкция"),
        ("promotion", "Акция"),
        ("credit", "Кредитный продукт"),
        ("reference", "Справочник"),
    ]

    summary = models.TextField("Краткое описание", max_length=300, blank=True)
    material_type = models.CharField(
        "Тип материала",
        max_length=30,
        choices=MATERIAL_TYPE_CHOICES,
        default="instruction",
    )
    hero_image = models.ForeignKey(
        get_image_model_string(),
        verbose_name="Обложка",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    brands = ParentalManyToManyField("portal.Brand", blank=True)
    categories = ParentalManyToManyField("portal.ProductCategory", blank=True)
    areas = ParentalManyToManyField("portal.KnowledgeArea", blank=True)
    body = StreamField(CONTENT_STREAM_BLOCKS, blank=True, verbose_name="Содержимое")

    parent_page_types = ["portal.LearningIndexPage"]
    subpage_types = []

    search_fields = Page.search_fields + [
        index.SearchField("summary"),
        index.SearchField("body"),
        index.FilterField("material_type"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("summary"),
        MultiFieldPanel(
            [
                FieldPanel("material_type"),
                FieldPanel("hero_image"),
            ],
            heading="Карточка материала",
        ),
        MultiFieldPanel(
            [
                FieldPanel("brands"),
                FieldPanel("categories"),
                FieldPanel("areas"),
            ],
            heading="Фильтры и связки",
        ),
        FieldPanel("body"),
    ]
