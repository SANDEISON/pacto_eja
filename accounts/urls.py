from django.urls import path

from . import views


app_name = "accounts"

urlpatterns = [
    path("entrar/", views.SignInView.as_view(), name="signin"),
    path("recuperar-senha/", views.recover_password, name="password_recovery"),
    path("cadastrar/", views.signup, name="signup"),
    path("cadastrar/confirmacao-enviada/", views.signup_confirmation_sent, name="signup_confirmation_sent"),
    path("cadastrar/confirmar-email/", views.signup_confirm, name="signup_confirm"),
    path("sair/", views.SignOutView.as_view(), name="logout"),
]
