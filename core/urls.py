from django.urls import path
from django.views.generic import RedirectView

from . import views


urlpatterns = [
    path("cadastro-educadores/", views.cadastro_educador, name="cadastro_educador"),
    path("cadastro-educadores/concluido/", views.cadastro_educador_success, name="cadastro_educador_success"),
    path("cadastro-educadores/api/cpf/", views.cpf_lookup, name="cadastro_educador_cpf_lookup"),
    path("cadastro-educadores/api/cidades/", views.cidades_por_estado, name="cadastro_educador_cidades"),
    path("cadastro-educadores/api/escolas/", views.escolas_por_cidade, name="cadastro_educador_escolas"),
    path("", RedirectView.as_view(pattern_name="cadastro_educador", permanent=False), name="home"),
    path("painel/", views.dashboard, name="dashboard"),
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
    path("administracao/cidades/", views.CatalogListView.as_view(catalog_key="cidades"), name="city_list"),
    path("administracao/cores-racas/", views.CatalogListView.as_view(catalog_key="cores-racas"), name="race_color_list"),
    path("administracao/cadastros-educadores/", views.CatalogListView.as_view(catalog_key="cadastros-educadores"), name="educator_model_list"),
    path("administracao/escolas/", views.CatalogListView.as_view(catalog_key="escolas"), name="school_list"),
    path("administracao/estados/", views.CatalogListView.as_view(catalog_key="estados"), name="state_list"),
    path("administracao/niveis/", views.CatalogListView.as_view(catalog_key="niveis"), name="level_list"),
    path("administracao/modalidades/", views.CatalogListView.as_view(catalog_key="modalidades"), name="modality_list"),
    path("administracao/situacoes/", views.CatalogListView.as_view(catalog_key="situacoes"), name="situation_list"),
    path("administracao/cadastros-educadores/<int:pk>/editar/", views.educator_profile_update, name="educator_profile_update"),
    path("administracao/<str:catalog_key>/cadastrar/", views.CatalogCreateView.as_view(), name="catalog_create"),
    path("administracao/<str:catalog_key>/<int:pk>/editar/", views.CatalogUpdateView.as_view(), name="catalog_update"),
    path("administracao/<str:catalog_key>/<int:pk>/excluir/", views.CatalogDeleteView.as_view(), name="catalog_delete"),
]
