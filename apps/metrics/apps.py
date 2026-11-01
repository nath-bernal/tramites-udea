from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MetricsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.metrics"
    verbose_name = _("Indicadores")
