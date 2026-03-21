from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify


def build_unique_slug(ProductCharacteristic, value):
    base_slug = slugify(value, allow_unicode=True) or "characteristic"
    slug = base_slug
    counter = 2
    while ProductCharacteristic.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def backfill_product_spec_characteristics(apps, schema_editor):
    ProductCharacteristic = apps.get_model("catalog", "ProductCharacteristic")
    ProductSpecification = apps.get_model("learning", "ProductSpecification")

    for specification in ProductSpecification.objects.all().iterator():
        name = str(specification.name or "").strip()
        if not name:
            continue

        characteristic = ProductCharacteristic.objects.filter(name__iexact=name).first()
        if characteristic is None:
            characteristic = ProductCharacteristic.objects.create(
                name=name,
                slug=build_unique_slug(ProductCharacteristic, name),
                description="",
            )

        specification.characteristic_id = characteristic.pk
        specification.name = characteristic.name
        specification.save(update_fields=["characteristic", "name"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0005_productcharacteristic_productcategorycharacteristic_and_more"),
        ("learning", "0005_learningmaterial_telegram_audience_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="productspecification",
            name="characteristic",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="material_specifications", to="catalog.productcharacteristic", verbose_name="Характеристика"),
        ),
        migrations.RunPython(backfill_product_spec_characteristics, migrations.RunPython.noop),
    ]
