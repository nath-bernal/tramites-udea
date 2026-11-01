from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("usuario"),
    )
    request = models.ForeignKey(
        "requests.Request",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("solicitud"),
    )
    message = models.TextField(_("mensaje"))
    is_read = models.BooleanField(_("leída"), default=False)
    created_at = models.DateTimeField(_("fecha"), auto_now_add=True)

    class Meta:
        verbose_name = _("notificación")
        verbose_name_plural = _("notificaciones")
        ordering = ["-created_at"]

    def __str__(self):
        return self.message[:60]
