import secrets
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class CertificateKind(models.TextChoices):
    STUDIES = "studies", _("Certificado de estudios")
    GRADES = "grades", _("Certificado de notas")
    CONTENTS = "contents", _("Certificado de contenidos")


class Language(models.TextChoices):
    ES = "es", _("Español")
    EN = "en", _("Inglés")


class CertificateTemplate(models.Model):
    """Plantilla HTML del cuerpo del certificado. Variables disponibles:

    ``student_name``, ``document``, ``program``, ``number``, ``issued_date``, ``code``.
    """

    kind = models.CharField(_("tipo"), max_length=10, choices=CertificateKind.choices)
    language = models.CharField(_("idioma"), max_length=2, choices=Language.choices)
    title = models.CharField(_("título"), max_length=200)
    body_html = models.TextField(
        _("cuerpo (HTML)"),
        help_text=_(
            "Plantilla de Django. Variables: {{ student_name }}, {{ document }}, {{ program }}, "
            "{{ number }}, {{ issued_date }}, {{ code }}."
        ),
    )
    is_active = models.BooleanField(_("activa"), default=True)

    class Meta:
        verbose_name = _("plantilla de certificado")
        verbose_name_plural = _("plantillas de certificado")
        ordering = ["kind", "language"]
        constraints = [
            models.UniqueConstraint(fields=["kind", "language"], name="unique_template_kind_lang")
        ]

    def __str__(self):
        return f"{self.get_kind_display()} ({self.language.upper()})"


# Alfabeto sin caracteres ambiguos (0/O, 1/I/L).
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_verification_code():
    """Código no adivinable de 12 caracteres (~59 bits), p. ej. ``K7QH-2M9X-RT4C``."""
    raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(12))
    return f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}"


def certificate_upload_to(instance, filename):
    return f"certificates/{uuid.uuid4().hex}.pdf"


class IssuedCertificate(models.Model):
    request = models.ForeignKey(
        "requests.Request",
        on_delete=models.PROTECT,
        related_name="certificates",
        verbose_name=_("solicitud"),
    )
    kind = models.CharField(_("tipo"), max_length=10, choices=CertificateKind.choices)
    language = models.CharField(_("idioma"), max_length=2, choices=Language.choices)
    code = models.CharField(
        _("código de verificación"), max_length=14, unique=True, default=generate_verification_code
    )
    pdf = models.FileField(_("archivo PDF"), upload_to=certificate_upload_to)
    issued_at = models.DateTimeField(_("emitido el"), auto_now_add=True)

    class Meta:
        verbose_name = _("certificado emitido")
        verbose_name_plural = _("certificados emitidos")
        ordering = ["-issued_at", "language"]

    def __str__(self):
        return f"{self.code} · {self.get_kind_display()} ({self.language.upper()})"
