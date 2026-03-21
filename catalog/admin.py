from django.contrib import admin

from .models import (
    Brand,
    FeatureTag,
    KnowledgeArea,
    ProductCategory,
    ProductCategoryCharacteristic,
    ProductCharacteristic,
)


class ProductCategoryCharacteristicInline(admin.TabularInline):
    model = ProductCategoryCharacteristic
    extra = 1
    verbose_name = "Характеристика категории"
    verbose_name_plural = "Характеристики, которые будут подтягиваться в товарах"
    fields = ("sort_order", "characteristic")
    autocomplete_fields = ("characteristic",)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    fields = ("name", "description")


@admin.register(ProductCharacteristic)
class ProductCharacteristicAdmin(admin.ModelAdmin):
    list_display = ("name", "category_count")
    search_fields = ("name", "description")
    fields = ("name", "description")

    @admin.display(description="Категорий использует")
    def category_count(self, obj):
        return obj.product_categories.count()


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "characteristic_count")
    search_fields = ("name",)
    fields = ("name", "description")
    inlines = (ProductCategoryCharacteristicInline,)

    @admin.display(description="Характеристик назначено")
    def characteristic_count(self, obj):
        return obj.characteristics.count()


@admin.register(KnowledgeArea)
class KnowledgeAreaAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    fields = ("name", "description")


@admin.register(FeatureTag)
class FeatureTagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    fields = ("name", "description")
