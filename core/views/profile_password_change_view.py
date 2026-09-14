from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

from ..forms import ProfilePasswordChangeForm


class ProfilePasswordChangeView(PasswordChangeView):
    """Permite que o usuário autenticado substitua a própria senha."""
    template_name = "profile/password_change.html"
    form_class = ProfilePasswordChangeForm
    success_url = reverse_lazy("profile")

    def form_valid(self, form):
        """Confirma a alteração e mantém a sessão autenticada pelo Django."""
        messages.success(self.request, "Sua senha foi alterada com sucesso.")
        return super().form_valid(form)
