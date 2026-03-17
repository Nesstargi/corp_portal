from django.core.management.base import BaseCommand, CommandError

from promotions.models import PromotionSource
from promotions.services import import_promotions_from_source


class Command(BaseCommand):
    help = "Импортирует акции из настроенных источников Google Sheets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=int,
            help="ID конкретного источника, который нужно импортировать.",
        )

    def handle(self, *args, **options):
        queryset = PromotionSource.objects.filter(is_active=True)

        if options["source"]:
            queryset = queryset.filter(pk=options["source"])

        if not queryset.exists():
            raise CommandError("Активные источники для импорта не найдены.")

        for source in queryset:
            try:
                result = import_promotions_from_source(source)
            except Exception as exc:
                source.last_import_error = str(exc)
                source.save(update_fields=["last_import_error", "updated_at"])
                raise CommandError(
                    f"Ошибка импорта источника '{source.name}': {exc}"
                ) from exc

            self.stdout.write(
                self.style.SUCCESS(
                    (
                        f"{source.name}: создано {result.created}, "
                        f"обновлено {result.updated}, "
                        f"пропущено {result.skipped}, "
                        f"снято с публикации {result.unpublished}."
                    )
                )
            )
