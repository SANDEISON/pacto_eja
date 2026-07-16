from django.urls import path

from . import views


app_name = "accounts"

urlpatterns = [
    path("entrar/", views.SignInView.as_view(), name="signin"),
    path("cadastrar/", views.signup, name="signup"),
    path("sair/", views.SignOutView.as_view(), name="logout"),
]
