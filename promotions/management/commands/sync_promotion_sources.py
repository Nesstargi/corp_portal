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
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Проверить импорт и показать результат без изменения акций.",
        )

    def handle(self, *args, **options):
        queryset = PromotionSource.objects.filter(is_active=True)

        if options["source"]:
            queryset = queryset.filter(pk=options["source"])

        if not queryset.exists():
            raise CommandError("Активные источники для импорта не найдены.")

        failed_sources = []
        dry_run = options["dry_run"]

        for source in queryset:
            try:
                result = import_promotions_from_source(source, dry_run=dry_run)
            except Exception as exc:
                if not dry_run:
                    source.last_import_error = str(exc)
                    source.save(update_fields=["last_import_error", "updated_at"])
                failed_sources.append(source.name)
                self.stderr.write(
                    self.style.ERROR(f"Ошибка импорта источника '{source.name}': {exc}")
                )
                continue

            self.stdout.write(
                self.style.SUCCESS(
                    (
                        f"{'Проверка: ' if dry_run else ''}{source.name}: "
                        f"создано {result.created}, "
                        f"обновлено {result.updated}, "
                        f"пропущено {result.skipped}, "
                        f"дубликатов {result.duplicates}, "
                        f"снято с публикации {result.unpublished}."
                    )
                )
            )
            for warning in result.warnings:
                self.stdout.write(self.style.WARNING(f"{source.name}: {warning}"))

        if failed_sources:
            raise CommandError(
                "Не удалось обработать источники: " + ", ".join(failed_sources)
            )
