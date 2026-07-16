from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

from ..forms import ProfilePasswordChangeForm


class ProfilePasswordChangeView(PasswordChangeView):
    template_name = "profile/password_change.html"
    form_class = ProfilePasswordChangeForm
    success_url = reverse_lazy("profile")

    def form_valid(self, form):
        messages.success(self.request, "Sua senha foi alterada com sucesso.")
        return super().form_valid(form)
