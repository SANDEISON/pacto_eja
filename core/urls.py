from django.urls import path

from . import views
from . import management_views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("erro/<int:status_code>/", views.error_preview, name="error_preview"),
    path("administracao/usuarios/", management_views.UserListView.as_view(), name="user_list"),
    path("administracao/usuarios/cadastrar/", management_views.UserCreateView.as_view(), name="user_create"),
    path("administracao/usuarios/<int:pk>/editar/", management_views.UserUpdateView.as_view(), name="user_update"),
    path("administracao/usuarios/<int:pk>/excluir/", management_views.UserDeleteView.as_view(), name="user_delete"),
    path("administracao/grupos/", management_views.GroupListView.as_view(), name="group_list"),
    path("administracao/grupos/cadastrar/", management_views.GroupCreateView.as_view(), name="group_create"),
    path("administracao/grupos/<int:pk>/editar/", management_views.GroupUpdateView.as_view(), name="group_update"),
    path("administracao/grupos/<int:pk>/excluir/", management_views.GroupDeleteView.as_view(), name="group_delete"),
]
