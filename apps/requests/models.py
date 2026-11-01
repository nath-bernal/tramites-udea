import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import ProcedureStage, ProcedureType, RequiredDocument

from .deadlines import add_business_days, business_days_between


class Status(models.TextChoices):
    DRAFT = "DRAFT", _("Borrador")
    SUBMITTED = "SUBMITTED", _("Radicada")
    IN_REVIEW = "IN_REVIEW", _("En revisión")
    NEEDS_CHANGES = "NEEDS_CHANGES", _("Requiere ajustes")
    APPROVED = "APPROVED", _("Aprobada")
    REJECTED = "REJECTED", _("Rechazada")
    FINALIZED = "FINALIZED", _("Finalizada")


# Estados en los que la solicitud está en la bandeja de una dependencia.
ACTIVE_STATUSES = (Status.SUBMITTED, Status.IN_REVIEW)


class Outcome(models.TextChoices):
    APPROVED = "APPROVED", _("Aprobada")
    REJECTED = "REJECTED", _("Rechazada")


class Request(models.Model):
    number = models.CharField(_("radicado"), max_length=20, unique=True, null=True, blank=True)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="procedure_requests",
        verbose_name=_("estudiante"),
    )
    procedure = models.ForeignKey(
        ProcedureType, on_delete=models.PROTECT, related_name="requests", verbose_name=_("trámite")
    )
    status = models.CharField(
        _("estado"), max_length=15, choices=Status.choices, default=Status.DRAFT
    )
    outcome = models.CharField(_("resultado"), max_length=10, choices=Outcome.choices, blank=True)
    current_stage = models.ForeignKey(
        ProcedureStage,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("etapa actual"),
    )
    form_data = models.JSONField(_("datos del formulario"), default=dict, blank=True)
    created_at = models.DateTimeField(_("creada"), auto_now_add=True)
    updated_at = models.DateTimeField(_("actualizada"), auto_now=True)
    submitted_at = models.DateTimeField(_("radicada el"), null=True, blank=True)
    stage_entered_at = models.DateTimeField(_("ingreso a la etapa"), null=True, blank=True)
    resolved_at = models.DateTimeField(_("resuelta el"), null=True, blank=True)

    class Meta:
        verbose_name = _("solicitud")
        verbose_name_plural = _("solicitudes")
        ordering = ["-created_at"]

    def __str__(self):
        return self.number or _("Borrador #%(id)s") % {"id": self.pk}

    @property
    def is_active(self):
        return self.status in ACTIVE_STATUSES

    @property
    def is_editable(self):
        return self.status in (Status.DRAFT, Status.NEEDS_CHANGES)

    @property
    def stage_due_date(self):
        if not (self.is_active and self.current_stage and self.stage_entered_at):
            return None
        entered = timezone.localdate(self.stage_entered_at)
        return add_business_days(entered, self.current_stage.deadline_days)

    @property
    def deadline_state(self):
        """'overdue', 'due_soon' u 'on_time' para la etapa actual; None si no aplica."""
        due = self.stage_due_date
        if due is None:
            return None
        today = timezone.localdate()
        if today > due:
            return "overdue"
        if business_days_between(today, due) <= 1:
            return "due_soon"
        return "on_time"

    @property
    def days_elapsed(self):
        if not self.submitted_at:
            return 0
        end = self.resolved_at or timezone.now()
        return (end - self.submitted_at).days

    @property
    def days_in_stage(self):
        if not self.stage_entered_at:
            return 0
        return (timezone.now() - self.stage_entered_at).days

    def form_items(self):
        """Pares (etiqueta, valor legible) de los datos del formulario."""
        items = []
        for field in self.procedure.fields.all():
            if field.key in self.form_data:
                items.append((field.display_label, field.display_value(self.form_data[field.key])))
        return items


def upload_to(instance, filename):
    """Nombre aleatorio para que la ruta no sea adivinable ni revele datos."""
    ext = Path(filename).suffix.lower()
    return f"requests/{uuid.uuid4().hex}{ext}"


class RequestDocument(models.Model):
    request = models.ForeignKey(
        Request, on_delete=models.CASCADE, related_name="documents", verbose_name=_("solicitud")
    )
    required_document = models.ForeignKey(
        RequiredDocument,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("documento requerido"),
    )
    file = models.FileField(_("archivo"), upload_to=upload_to)
    original_name = models.CharField(_("nombre original"), max_length=255)
    uploaded_at = models.DateTimeField(_("cargado el"), auto_now_add=True)

    class Meta:
        verbose_name = _("documento de la solicitud")
        verbose_name_plural = _("documentos de la solicitud")
        constraints = [
            models.UniqueConstraint(
                fields=["request", "required_document"], name="one_file_per_required_document"
            )
        ]

    def __str__(self):
        return self.original_name


class RequestEvent(models.Model):
    """Historial de cambios: fuente de la línea de tiempo y de los indicadores."""

    request = models.ForeignKey(
        Request, on_delete=models.CASCADE, related_name="events", verbose_name=_("solicitud")
    )
    from_status = models.CharField(
        _("estado anterior"), max_length=15, choices=Status.choices, blank=True
    )
    to_status = models.CharField(_("estado nuevo"), max_length=15, choices=Status.choices)
    stage = models.ForeignKey(
        ProcedureStage,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("etapa"),
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("actor"),
    )
    comment = models.TextField(_("comentario"), blank=True)
    created_at = models.DateTimeField(_("fecha"), default=timezone.now)

    class Meta:
        verbose_name = _("evento")
        verbose_name_plural = _("eventos")
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.request} {self.from_status}→{self.to_status}"
