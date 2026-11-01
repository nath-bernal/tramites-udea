from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import home, set_language

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("idioma/", set_language, name="set_language"),
    path("cuentas/", include("apps.accounts.urls")),
    path("tramites/", include("apps.catalog.urls")),
    path("solicitudes/", include("apps.requests.urls")),
    path("notificaciones/", include("apps.notifications.urls")),
    path("certificados/", include("apps.certificates.urls")),
    path("indicadores/", include("apps.metrics.urls")),
]
