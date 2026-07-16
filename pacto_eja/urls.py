from django.contrib import admin
from django.urls import include, path

from core import views as core_views


handler400 = "core.views.error_400"
handler403 = "core.views.error_403"
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("conta/", include("accounts.urls")),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include("core.urls")),
]

admin.site.site_header = "Pacto EJA — Administração"
admin.site.site_title = "Pacto EJA Admin"
admin.site.index_title = "Gestão do sistema"
