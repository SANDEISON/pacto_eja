from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from .bootstrap_form_mixin import BootstrapFormMixin


class ProfileUserForm(BootstrapFormMixin, forms.ModelForm):
    full_name = forms.CharField(label="Nome completo", max_length=150)

    class Meta:
        model = get_user_model()
        fields = ("full_name", "email")
        labels = {"email": "E-mail"}
        widgets = {"email": forms.EmailInput(attrs={"autocomplete": "email"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_email = self.instance.email
        self.fields["full_name"].initial = self.instance.get_full_name()
        self._apply_bootstrap_classes()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        User = get_user_model()
        conflicts = User.objects.exclude(pk=self.instance.pk).filter(Q(email__iexact=email) | Q(username__iexact=email))
        if conflicts.exists():
            raise forms.ValidationError("Já existe uma conta cadastrada com este e-mail.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data["full_name"].strip()
        user.first_name, _, user.last_name = full_name.partition(" ")
        if user.username.lower() == (self._original_email or "").lower():
            user.username = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
