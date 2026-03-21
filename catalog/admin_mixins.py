from django.contrib import admin, messages
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe


class AdminPresentationMixin:
    image_field_name = "cover_image"
    image_recommendation = (1600, 900)

    def _get_image(self, obj):
        field = getattr(obj, self.image_field_name, None)
        if not field:
            return None
        try:
            return field.url
        except ValueError:
            return None

    @admin.display(description="Обложка")
    def cover_thumb(self, obj):
        image_url = self._get_image(obj)
        if not image_url:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="width:64px;height:64px;object-fit:cover;'
            'border-radius:12px;border:1px solid #e6e6e6;" />',
            image_url,
        )

    @admin.display(description="Превью изображения")
    def cover_preview(self, obj):
        image_url = self._get_image(obj)
        image_width, image_height = self.image_recommendation
        if image_url:
            image_markup = format_html(
                '<div class="admin-image-preview__canvas">'
                '<img src="{}" alt="" />'
                '<div class="admin-image-preview__placeholder is-hidden">Изображение пока не добавлено.</div>'
                "</div>",
                image_url,
            )
        else:
            image_markup = mark_safe(
                '<div class="admin-image-preview__canvas">'
                '<img src="" alt="" class="is-hidden" />'
                '<div class="admin-image-preview__placeholder">Изображение пока не добавлено.</div>'
                "</div>"
            )
        return format_html(
            '<div class="admin-image-preview{}" data-preview-field="{}" '
            'data-recommended-width="{}" data-recommended-height="{}">'
            "{}"
            '<div class="admin-image-preview__meta">Рекомендуемый размер: {} x {} px</div>'
            '<div class="admin-image-preview__meta admin-image-preview__dimensions is-hidden"></div>'
            '<div class="admin-image-preview__warning is-hidden"></div>'
            "</div>",
            "" if image_url else " is-empty",
            self.image_field_name,
            image_width,
            image_height,
            image_markup,
            image_width,
            image_height,
        )

    @admin.display(description="Статус")
    def published_badge(self, obj):
        if getattr(obj, "is_published", False):
            return format_html(
                '<span class="admin-status-badge is-live">{}</span>',
                "Опубликовано",
            )
        return format_html(
            '<span class="admin-status-badge is-draft">{}</span>',
            "Скрыто",
        )

    @admin.display(description="Ссылка")
    def public_link(self, obj):
        if not getattr(obj, "pk", None):
            return "Сначала сохрани запись."

        get_absolute_url = getattr(obj, "get_absolute_url", None)
        if not callable(get_absolute_url):
            return "У записи пока нет публичной страницы."

        return format_html(
            '<a class="admin-inline-link" href="{}" target="_blank" rel="noopener noreferrer">'
            "Открыть на сайте</a>",
            obj.get_absolute_url(),
        )


def render_admin_card_preview(title, description="", chips=None, footer=None):
    chips = [chip for chip in (chips or []) if chip]
    footer = [item for item in (footer or []) if item]

    chips_html = format_html_join(
        "",
        '<span class="admin-card-preview__chip">{}</span>',
        ((chip,) for chip in chips),
    )
    footer_html = format_html_join(
        "",
        '<span class="admin-card-preview__meta">{}</span>',
        ((item,) for item in footer),
    )

    return format_html(
        '<div class="admin-card-preview">'
        '<div class="admin-card-preview__chips{}">{}</div>'
        '<div class="admin-card-preview__title">{}</div>'
        '<div class="admin-card-preview__description">{}</div>'
        '<div class="admin-card-preview__footer{}">{}</div>'
        "</div>",
        " is-hidden" if not chips else "",
        chips_html,
        title or "Без названия",
        description or "Краткое описание появится здесь после заполнения формы.",
        " is-hidden" if not footer else "",
        footer_html,
    )


class AdminTemplatesAndFiltersMixin:
    change_list_template = "admin/change_list_with_tools.html"
    template_presets = ()
    quick_filters = ()

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        preset_key = request.GET.get("template", "").strip()
        presets = {preset["key"]: preset for preset in self.template_presets}
        preset = presets.get(preset_key)
        if preset:
            initial.update(preset.get("initial", {}))
        return initial

    def _build_query_url(self, request, key, value):
        query = request.GET.copy()
        if value in ("", None):
            query.pop(key, None)
        else:
            query[key] = value
        encoded = query.urlencode()
        return "?" + encoded if encoded else ""

    def get_quick_filter_links(self, request):
        links = []
        filter_keys = [item["key"] for item in self.quick_filters]
        current_filters = {
            key: request.GET.get(key, "")
            for key in filter_keys
            if request.GET.get(key, "") not in ("", None)
        }

        for item in self.quick_filters:
            key = item["key"]
            value = item.get("value", "")
            query = request.GET.copy()

            for filter_key in filter_keys:
                query.pop(filter_key, None)

            if value not in ("", None):
                query[key] = value

            encoded = query.urlencode()
            url = "?" + encoded if encoded else ""

            if value in ("", None):
                is_active = not current_filters
            else:
                is_active = current_filters == {key: str(value)}

            links.append(
                {
                    "label": item["label"],
                    "url": url,
                    "is_active": is_active,
                }
            )
        return links

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["admin_template_presets"] = self.template_presets
        extra_context["admin_quick_filter_links"] = self.get_quick_filter_links(request)
        return super().changelist_view(request, extra_context=extra_context)


class AdminDuplicateMixin:
    def get_urls(self):
        opts = self.model._meta
        custom_urls = [
            path(
                "<path:object_id>/duplicate/",
                self.admin_site.admin_view(self.duplicate_view),
                name=f"{opts.app_label}_{opts.model_name}_duplicate",
            ),
        ]
        return custom_urls + super().get_urls()

    @admin.display(description="Копия записи")
    def duplicate_link(self, obj):
        if not getattr(obj, "pk", None):
            return "Сначала сохрани запись."
        opts = self.model._meta
        return format_html(
            '<a class="admin-inline-link" href="{}">Создать копию этой записи</a>',
            reverse(f"admin:{opts.app_label}_{opts.model_name}_duplicate", args=[obj.pk]),
        )

    @admin.display(description="История")
    def history_link(self, obj):
        if not getattr(obj, "pk", None):
            return "Сначала сохрани запись."
        opts = self.model._meta
        return format_html(
            '<a class="admin-inline-link" href="{}">История изменений</a>',
            reverse(f"admin:{opts.app_label}_{opts.model_name}_history", args=[obj.pk]),
        )

    def duplicate_view(self, request, object_id):
        if not self.has_add_permission(request):
            raise PermissionDenied

        obj = self.get_object(request, unquote(object_id))
        if obj is None:
            raise PermissionDenied

        clone = self.clone_object(request, obj)
        self.message_user(request, "Копия записи создана.", level=messages.SUCCESS)
        opts = self.model._meta
        return HttpResponseRedirect(
            reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[clone.pk])
        )

    def clone_object(self, request, obj):
        source = self.model.objects.get(pk=obj.pk)
        clone = self.model.objects.get(pk=obj.pk)
        m2m_values = {
            field.name: list(getattr(source, field.name).all())
            for field in source._meta.many_to_many
        }

        clone.pk = None
        if hasattr(clone, "id"):
            clone.id = None
        if hasattr(clone, "title"):
            clone.title = f"{clone.title} (копия)"
        if hasattr(clone, "slug"):
            clone.slug = ""
        if hasattr(clone, "is_published"):
            clone.is_published = False
        if hasattr(clone, "sync_with_source"):
            clone.sync_with_source = False
        if hasattr(clone, "source"):
            clone.source = None
        if hasattr(clone, "source_row_key"):
            clone.source_row_key = ""
        if hasattr(clone, "imported_at"):
            clone.imported_at = None

        clone.save()

        for field_name, values in m2m_values.items():
            getattr(clone, field_name).set(values)

        self.clone_related_objects(request, source=source, clone=clone)
        return clone

    def clone_related_objects(self, request, source, clone):
        return None
