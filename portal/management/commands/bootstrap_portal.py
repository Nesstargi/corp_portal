from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from wagtail.models import Locale, Page, Site

from portal.models import HomePage, LearningIndexPage, NewsIndexPage


class Command(BaseCommand):
    help = "Создает стартовую структуру портала для Wagtail, если ее еще нет."

    def handle(self, *args, **options):
        root = Page.get_first_root_node()

        homepage = HomePage.objects.first()
        if homepage is None:
            default_homepage = Page.objects.filter(depth=2, slug="home").first()
            if default_homepage and default_homepage.specific_class is Page:
                default_homepage.delete()

            homepage = HomePage.objects.create(
                title="CorpPortal",
                draft_title="CorpPortal",
                slug="home",
                content_type=ContentType.objects.get_for_model(HomePage),
                locale=Locale.get_default(),
                path="00010001",
                depth=2,
                numchild=0,
                url_path="/home/",
                intro=(
                    "Корпоративный портал для новостей, обучения, акций, продуктовых "
                    "обновлений и внутренних материалов."
                ),
            )
            homepage.save_revision().publish()
            self.stdout.write(self.style.SUCCESS("Создана домашняя страница портала."))

        site, created = Site.objects.get_or_create(
            hostname="localhost",
            defaults={
                "site_name": "CorpPortal",
                "root_page": homepage,
                "is_default_site": True,
            },
        )
        if not created:
            site.root_page = homepage
            site.site_name = "CorpPortal"
            site.is_default_site = True
            site.save()

        if not NewsIndexPage.objects.child_of(homepage).filter(slug="news").exists():
            news_index = NewsIndexPage(
                title="Новости",
                slug="news",
                intro="Новости о продуктах, акциях, процессах и жизни компании.",
            )
            homepage.add_child(instance=news_index)
            news_index.save_revision().publish()
            self.stdout.write(self.style.SUCCESS("Создан раздел новостей."))

        if not LearningIndexPage.objects.child_of(homepage).filter(slug="learning").exists():
            learning_index = LearningIndexPage(
                title="Обучающие материалы",
                slug="learning",
                intro=(
                    "Материалы по брендам, категориям, 1С, акциям, кредитным продуктам "
                    "и внутренним процессам."
                ),
            )
            homepage.add_child(instance=learning_index)
            learning_index.save_revision().publish()
            self.stdout.write(self.style.SUCCESS("Создан раздел обучения."))

        self.stdout.write(self.style.SUCCESS("Стартовая структура портала готова."))
