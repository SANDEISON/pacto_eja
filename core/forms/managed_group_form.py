from django import forms
from django.contrib.auth.models import Group

from .bootstrap_form_mixin import BootstrapFormMixin


class ManagedGroupForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Group
        fields = ("name", "permissions")
        labels = {"name": "Nome", "permissions": "Permissões"}
        widgets = {"permissions": forms.SelectMultiple(attrs={"size": 14})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["permissions"].queryset = self.fields["permissions"].queryset.select_related(
            "content_type"
        ).order_by("content_type__app_label", "content_type__model", "codename")
        self._apply_bootstrap_classes()
