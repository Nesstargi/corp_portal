from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_backfill_directory_slugs"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductCharacteristic",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True, verbose_name="Название")),
                ("slug", models.SlugField(blank=True, max_length=140, unique=True, verbose_name="Внутренний адрес")),
                ("description", models.TextField(blank=True, verbose_name="Короткое пояснение")),
            ],
            options={
                "verbose_name": "Характеристика",
                "verbose_name_plural": "Характеристики",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="ProductCategoryCharacteristic",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("category", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="characteristic_links", to="catalog.productcategory", verbose_name="Категория товара")),
                ("characteristic", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="category_links", to="catalog.productcharacteristic", verbose_name="Характеристика")),
            ],
            options={
                "verbose_name": "Связь категории и характеристики",
                "verbose_name_plural": "Связи категорий и характеристик",
                "ordering": ["sort_order", "characteristic__name"],
                "unique_together": {("category", "characteristic")},
            },
        ),
        migrations.AddField(
            model_name="productcategory",
            name="characteristics",
            field=models.ManyToManyField(blank=True, related_name="product_categories", through="catalog.ProductCategoryCharacteristic", to="catalog.productcharacteristic", verbose_name="Назначенные характеристики"),
        ),
    ]
