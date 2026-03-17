from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config import views as config_views
from news import views as news_views
from search import views as search_views

admin.site.site_header = "Панель управления CorpPortal"
admin.site.site_title = "CorpPortal"
admin.site.index_title = "Материалы, новости и справочники"


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", config_views.healthcheck, name="healthcheck"),
    path("", news_views.home, name="home"),
    path("news/", include("news.urls")),
    path("promotions/", include("promotions.urls")),
    path("learning/", include("learning.urls")),
    path("search/", search_views.search, name="search"),
]

if settings.SERVE_MEDIA:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
