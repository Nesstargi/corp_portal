from django.db import migrations
from django.utils.text import slugify


def unique_slug_for(instance, model):
    base_slug = slugify(instance.slug or instance.name, allow_unicode=True)
    if not base_slug:
        base_slug = model.__name__.lower()

    slug = base_slug
    counter = 2
    while model.objects.exclude(pk=instance.pk).filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def backfill_slugs(apps, schema_editor):
    model_names = ("Brand", "ProductCategory", "KnowledgeArea", "FeatureTag")

    for model_name in model_names:
        model = apps.get_model("catalog", model_name)
        for instance in model.objects.all().order_by("id"):
            new_slug = unique_slug_for(instance, model)
            if instance.slug != new_slug:
                instance.slug = new_slug
                instance.save(update_fields=["slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_featuretag"),
    ]

    operations = [
        migrations.RunPython(backfill_slugs, migrations.RunPython.noop),
    ]
