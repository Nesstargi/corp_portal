from types import MethodType

from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.db.models import Q


ADMIN_DASHBOARD_SECTIONS = (
    {
        "app_label": "content_workspace",
        "name": "Контент сайта",
        "description": "Материалы базы знаний и действующие предложения для сотрудников.",
        "models": (
            {
                "app_label": "learning",
                "object_name": "LearningMaterial",
                "name": "База знаний",
                "description": "Инструкции, товарные карточки, обзоры, скрипты продаж и обучающие материалы.",
            },
            {
                "app_label": "promotions",
                "object_name": "Promotion",
                "name": "Акции",
                "description": "Промоцены, подарки, сроки действия, промокоды и условия предложений.",
            },
        ),
    },
    {
        "app_label": "catalog_workspace",
        "name": "Справочники товаров",
        "description": "Категории, бренды и метки, которые используются в карточках и базе знаний.",
        "models": (
            {
                "app_label": "catalog",
                "object_name": "ProductCategory",
                "name": "Категории товаров",
                "description": "Разделы ассортимента: пылесосы, смартфоны, техника для кухни и другие группы.",
            },
            {
                "app_label": "catalog",
                "object_name": "Brand",
                "name": "Бренды",
                "description": "Производители и торговые марки, по которым можно связывать материалы.",
            },
            {
                "app_label": "catalog",
                "object_name": "FeatureTag",
                "name": "Метки",
                "description": "Метки вроде «работает с Алисой», «самоочистка», «быстрая зарядка».",
            },
        ),
    },
    {
        "app_label": "telegram_workspace",
        "name": "Telegram",
        "description": "Подписчики, группы, объединения групп и ручные рассылки в Telegram.",
        "models": (
            {
                "app_label": "telegram_bot",
                "object_name": "TelegramBroadcast",
                "name": "Рассылки",
                "description": "Ручные уведомления для подписчиков, групп или выбранной аудитории.",
            },
            {
                "app_label": "telegram_bot",
                "object_name": "TelegramSubscriber",
                "name": "Подписчики и чаты",
                "description": "Личные подписчики, группы, супергруппы и каналы, где работает бот.",
            },
            {
                "app_label": "telegram_bot",
                "object_name": "TelegramAudienceGroup",
                "name": "Группы подписчиков",
                "description": "Сегменты личных подписчиков для точечных рассылок.",
            },
            {
                "app_label": "telegram_bot",
                "object_name": "TelegramChatCollection",
                "name": "Объединения Telegram-групп",
                "description": "Наборы групповых чатов для быстрых отправок.",
            },
        ),
    },
    {
        "app_label": "admins_workspace",
        "name": "Доступ",
        "description": "Доступы в админку, роли и права. Раздел видят только супер-администраторы.",
        "superuser_only": True,
        "models": (
            {
                "app_label": "auth",
                "object_name": "User",
                "name": "Администраторы",
                "description": "Пользователи с доступом к админке и супер-администраторы.",
            },
            {
                "app_label": "auth",
                "object_name": "Group",
                "name": "Роли и права",
                "description": "Группы прав для сотрудников, которым нужен ограниченный доступ.",
            },
        ),
    },
)


def _find_model(app_dict, app_label, object_name):
    app_config = app_dict.get(app_label)
    if not app_config:
        return None

    for model_info in app_config.get("models", []):
        if model_info.get("object_name") == object_name:
            return model_info

    return None


def _build_admin_dashboard_app_list(site, request, app_label=None):
    app_dict = site._build_app_dict(request, app_label)
    dashboard_app_list = []

    for section in ADMIN_DASHBOARD_SECTIONS:
        if section.get("superuser_only") and not request.user.is_superuser:
            continue

        if app_label and not any(
            model_config["app_label"] == app_label for model_config in section["models"]
        ):
            continue

        section_models = []
        for model_config in section["models"]:
            if app_label and model_config["app_label"] != app_label:
                continue

            model_info = _find_model(
                app_dict,
                model_config["app_label"],
                model_config["object_name"],
            )
            if not model_info:
                continue

            model_info = model_info.copy()
            model_info["name"] = model_config["name"]
            model_info["description"] = model_config["description"]
            section_models.append(model_info)

        if section_models:
            dashboard_app_list.append(
                {
                    "name": section["name"],
                    "app_label": section["app_label"],
                    "app_url": "",
                    "has_module_perms": True,
                    "description": section["description"],
                    "models": section_models,
                }
            )

    return dashboard_app_list


class SuperuserOnlyAdminMixin:
    def _has_superuser_access(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_module_permission(self, request):
        return self._has_superuser_access(request)

    def has_view_permission(self, request, obj=None):
        return self._has_superuser_access(request)

    def has_add_permission(self, request):
        return self._has_superuser_access(request)

    def has_change_permission(self, request, obj=None):
        return self._has_superuser_access(request)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and getattr(obj, "pk", None) == request.user.pk:
            return False
        return self._has_superuser_access(request)


class AdminUserAdmin(SuperuserOnlyAdminMixin, UserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_superuser",
        "is_active",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(Q(is_staff=True) | Q(is_superuser=True))

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if obj.pk == request.user.pk:
            obj.is_active = True
            obj.is_staff = True
            obj.is_superuser = True
        super().save_model(request, obj, form, change)


class AdminGroupAdmin(SuperuserOnlyAdminMixin, GroupAdmin):
    pass


def configure_admin_access_models(site):
    for model in (User, Group):
        try:
            site.unregister(model)
        except NotRegistered:
            pass

    site.register(User, AdminUserAdmin)
    site.register(Group, AdminGroupAdmin)


def configure_admin_site(site):
    configure_admin_access_models(site)
    site.get_app_list = MethodType(_build_admin_dashboard_app_list, site)
    site.index_template = "admin/index.html"
