from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import CPFAuthenticationForm, SignUpForm


class SignInView(LoginView):
    template_name = "accounts/signin.html"
    authentication_form = CPFAuthenticationForm
    redirect_authenticated_user = True


class SignOutView(LogoutView):
    http_method_names = ["post", "options"]
    next_page = reverse_lazy("accounts:signin")


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Sua conta foi criada. Boas-vindas ao Pacto EJA!")
        return redirect("dashboard")
    return render(request, "accounts/signup.html", {"form": form})
