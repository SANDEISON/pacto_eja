from django.contrib.auth.forms import PasswordChangeForm

from .bootstrap_form_mixin import BootstrapFormMixin


class ProfilePasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap_classes()
