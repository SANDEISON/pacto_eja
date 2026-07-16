from .dashboard import dashboard
from .error_pages import error_400, error_403, error_404, error_500, error_preview
from .educator_create_view import EducatorCreateView
from .educator_delete_view import EducatorDeleteView
from .educator_list_view import EducatorListView
from .educator_update_view import EducatorUpdateView
from .escolas_por_cidade import escolas_por_cidade
from .group_create_view import GroupCreateView
from .group_delete_view import GroupDeleteView
from .group_list_view import GroupListView
from .group_update_view import GroupUpdateView
from .profile import profile
from .profile_password_change_view import ProfilePasswordChangeView
from .user_create_view import UserCreateView
from .user_delete_view import UserDeleteView
from .user_list_view import UserListView
from .user_update_view import UserUpdateView

__all__ = [
    "cadastro_educador",
    "cadastro_educador_success",
    "cidades_por_estado",
    "cpf_lookup",
    "dashboard",
    "error_400",
    "error_403",
    "error_404",
    "error_500",
    "error_preview",
    "EducatorCreateView",
    "EducatorDeleteView",
    "EducatorListView",
    "EducatorUpdateView",
    "escolas_por_cidade",
    "GroupCreateView",
    "GroupDeleteView",
    "GroupListView",
    "GroupUpdateView",
    "profile",
    "ProfilePasswordChangeView",
    "UserCreateView",
    "UserDeleteView",
    "UserListView",
    "UserUpdateView",
]
from .cadastro_educador import cadastro_educador
from .cadastro_educador_success import cadastro_educador_success
from .cidades_por_estado import cidades_por_estado
from .cpf_lookup import cpf_lookup
