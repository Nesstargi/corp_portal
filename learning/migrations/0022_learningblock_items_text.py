from django.db import migrations, models


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


def populate_items_text(apps, schema_editor):
    LearningBlock = apps.get_model("learning", "LearningBlock")
    for block in LearningBlock.objects.all().iterator():
        block.items_text = flatten_json_text(block.items_data)
        block.save(update_fields=["items_text"])


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0021_alter_learningblock_block_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="learningblock",
            name="items_text",
            field=models.TextField(blank=True, editable=False, verbose_name="Текст внутренних элементов"),
        ),
        migrations.RunPython(populate_items_text, migrations.RunPython.noop),
    ]
