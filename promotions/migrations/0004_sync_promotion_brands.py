from django.db import migrations
from django.utils.text import slugify


def build_unique_slug(Brand, value):
    base_slug = slugify(value, allow_unicode=True) or "brand"
    slug = base_slug
    counter = 2
    while Brand.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def sync_promotion_brands(apps, schema_editor):
    Promotion = apps.get_model("promotions", "Promotion")
    Brand = apps.get_model("catalog", "Brand")

    for promotion in Promotion.objects.exclude(brand="").iterator():
        brand_name = str(promotion.brand or "").strip()
        if not brand_name:
            continue

        existing = Brand.objects.filter(name__iexact=brand_name).first()
        if existing:
            continue

        Brand.objects.create(
            name=brand_name,
            slug=build_unique_slug(Brand, brand_name),
            description="",
        )


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_featuretag"),
        ("promotions", "0003_promotion_benefit_value_promotion_cover_image_and_more"),
    ]

    operations = [
        migrations.RunPython(sync_promotion_brands, migrations.RunPython.noop),
    ]
