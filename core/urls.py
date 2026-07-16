from django.urls import path

from . import views


urlpatterns = [
    path("cadastro-educadores/", views.cadastro_educador, name="cadastro_educador"),
    path("cadastro-educadores/concluido/", views.cadastro_educador_success, name="cadastro_educador_success"),
    path("cadastro-educadores/api/cpf/", views.cpf_lookup, name="cadastro_educador_cpf_lookup"),
    path("cadastro-educadores/api/cidades/", views.cidades_por_estado, name="cadastro_educador_cidades"),
    path("cadastro-educadores/api/escolas/", views.escolas_por_cidade, name="cadastro_educador_escolas"),
    path("", views.dashboard, name="dashboard"),
    path("perfil/", views.profile, name="profile"),
    path("perfil/alterar-senha/", views.ProfilePasswordChangeView.as_view(), name="profile_password_change"),
    path("erro/<int:status_code>/", views.error_preview, name="error_preview"),
    path("administracao/usuarios/", views.UserListView.as_view(), name="user_list"),
    path("administracao/usuarios/cadastrar/", views.UserCreateView.as_view(), name="user_create"),
    path("administracao/usuarios/<int:pk>/editar/", views.UserUpdateView.as_view(), name="user_update"),
    path("administracao/usuarios/<int:pk>/excluir/", views.UserDeleteView.as_view(), name="user_delete"),
    path("administracao/educadores/", views.EducatorListView.as_view(), name="educator_list"),
    path("administracao/educadores/cadastrar/", views.EducatorCreateView.as_view(), name="educator_create"),
    path("administracao/educadores/<int:pk>/editar/", views.EducatorUpdateView.as_view(), name="educator_update"),
    path("administracao/educadores/<int:pk>/excluir/", views.EducatorDeleteView.as_view(), name="educator_delete"),
    path("administracao/grupos/", views.GroupListView.as_view(), name="group_list"),
    path("administracao/grupos/cadastrar/", views.GroupCreateView.as_view(), name="group_create"),
    path("administracao/grupos/<int:pk>/editar/", views.GroupUpdateView.as_view(), name="group_update"),
    path("administracao/grupos/<int:pk>/excluir/", views.GroupDeleteView.as_view(), name="group_delete"),
]
