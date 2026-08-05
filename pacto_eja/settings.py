import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

from core.menu import educator_management_access, management_access, staff_only


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)

INSECURE_DEFAULT_SECRET_KEY = "django-insecure-change-me-in-production"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", INSECURE_DEFAULT_SECRET_KEY)
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in {"1", "true", "yes"}
if not DEBUG and SECRET_KEY == INSECURE_DEFAULT_SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG=False")

ALLOWED_HOSTS = [host.strip() for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# Public path used by the STI reverse proxy. The proxy must strip this prefix
# before forwarding the request to Gunicorn.
FORCE_SCRIPT_NAME = os.environ.get("DJANGO_FORCE_SCRIPT_NAME", "").rstrip("/") or None

INSTALLED_APPS = [
    "django_components",
    "django_adminlte4",  # must precede django.contrib.admin so the theme overrides win
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "pacto_eja.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": False,
        "OPTIONS": {
            "loaders": [
                "django_components.template_loader.Loader",
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django_adminlte4.context_processors.adminlte",
            ],
        },
    }
]

WSGI_APPLICATION = "pacto_eja.wsgi.application"
ASGI_APPLICATION = "pacto_eja.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "db_pacto_eja"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Maceio"
USE_I18N = True
USE_TZ = True

STATIC_URL = f"{FORCE_SCRIPT_NAME}/static/" if FORCE_SCRIPT_NAME else "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedStaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

LOGIN_URL = "accounts:signin"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "accounts:signin"

ADMINLTE = {
    "title": "Pacto EJA",
    "title_postfix": " | Educação que transforma",
    "logo": "<b>Pacto</b> EJA",
    "logo_alt_text": "Pacto EJA",
    "logo_img": "img/logo.svg",
    "logo_img_alt": "Pacto EJA",
    "logo_img_class": "brand-image",
    "admin_brand": "Pacto EJA — Administração",
    "admin_enabled": True,
    "assets_mode": "static",
    "sidebar_theme": "light",
    "classes_sidebar": "bg-white shadow-sm",
    "classes_body": "bg-body-tertiary",
    "navbar_search": False,
    "color_mode_toggle": True,
    "sidebar_docs_url": None,
    "footer_left": "<strong>Pacto EJA</strong> — Programa de Formação de Educadores",
    "footer_right": "Educação que transforma",
    "menu": [
        {"text": "Início", "route": "dashboard", "icon": "bi bi-house-door-fill"},
        {"header": "GESTÃO", "can": staff_only},
        {"text": "Formações", "url": "#formacoes", "icon": "bi bi-mortarboard-fill", "can": staff_only},
        {"text": "Educadores", "route": "educator_list", "icon": "bi bi-people-fill", "can": educator_management_access},
        {"text": "Relatórios", "url": "#relatorios", "icon": "bi bi-bar-chart-fill", "can": staff_only},
        {"header": "SISTEMA", "can": management_access},
        {
            "text": "Administrar",
            "icon": "bi bi-briefcase-fill",
            "can": management_access,
            "submenu": [
                {"text": "Usuários", "route": "user_list", "icon": "bi bi-people", "can": "auth.view_user"},
                {"text": "Grupos", "route": "group_list", "icon": "bi bi-collection", "can": "auth.view_group"},
            ],
        },
        {"text": "Meu perfil", "route": "profile", "icon": "bi bi-person-circle"},
        {"text": "Sair", "route": "accounts:logout", "icon": "bi bi-box-arrow-right", "method": "post"},
    ],
}
