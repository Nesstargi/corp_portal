from django import forms


class RichTextToolbarWidget(forms.Textarea):
    template_name = "admin/widgets/rich_text_toolbar.html"

    def __init__(self, attrs=None):
        base_attrs = {
            "rows": 8,
        }
        if attrs:
            base_attrs.update(attrs)
        super().__init__(attrs=base_attrs)

    class Media:
        css = {
            "all": ("css/admin-rich-text.css",),
        }
        js = ("js/admin-rich-text.js",)
