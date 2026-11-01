from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Department

from .i18n import pick


class ProcedureType(models.Model):
    """Tipo de trámite del catálogo. Sus etapas, documentos y campos se configuran en /admin."""

    code = models.SlugField(_("código"), unique=True)
    name = models.CharField(_("nombre"), max_length=150)
    name_en = models.CharField(_("nombre en inglés"), max_length=150, blank=True)
    description = models.TextField(_("descripción"))
    description_en = models.TextField(_("descripción en inglés"), blank=True)
    requirements = models.TextField(
        _("requisitos"), blank=True, help_text=_("Un requisito por línea.")
    )
    requirements_en = models.TextField(_("requisitos en inglés"), blank=True)
    estimated_days = models.PositiveIntegerField(_("tiempo estimado (días hábiles)"), default=10)
    issues_certificate = models.BooleanField(
        _("emite certificado"),
        default=False,
        help_text=_(
            "Si está activo, al aprobarse se generan certificados PDF. El formulario debe tener "
            "los campos 'certificate_kind' y 'certificate_language'."
        ),
    )
    is_active = models.BooleanField(_("activo"), default=True)
    order = models.PositiveIntegerField(_("orden"), default=0)

    class Meta:
        verbose_name = _("tipo de trámite")
        verbose_name_plural = _("tipos de trámite")
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def display_name(self):
        return pick(self.name, self.name_en)

    @property
    def display_description(self):
        return pick(self.description, self.description_en)

    @property
    def requirement_list(self):
        text = pick(self.requirements, self.requirements_en)
        return [line.strip() for line in text.splitlines() if line.strip()]

    def ordered_stages(self):
        return list(self.stages.select_related("department").order_by("order"))

    def first_stage(self):
        return self.stages.order_by("order").first()

    def total_deadline_days(self):
        return sum(stage.deadline_days for stage in self.stages.all())


class ProcedureStage(models.Model):
    procedure = models.ForeignKey(
        ProcedureType, on_delete=models.CASCADE, related_name="stages", verbose_name=_("trámite")
    )
    order = models.PositiveIntegerField(_("orden"))
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="stages", verbose_name=_("dependencia")
    )
    deadline_days = models.PositiveIntegerField(
        _("plazo (días hábiles)"), default=5, validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = _("etapa")
        verbose_name_plural = _("etapas")
        ordering = ["procedure", "order"]
        constraints = [
            models.UniqueConstraint(fields=["procedure", "order"], name="unique_stage_order")
        ]

    def __str__(self):
        return f"{self.procedure} · {self.order}. {self.department}"

    def next_stage(self):
        return self.procedure.stages.filter(order__gt=self.order).order_by("order").first()


class RequiredDocument(models.Model):
    procedure = models.ForeignKey(
        ProcedureType,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("trámite"),
    )
    name = models.CharField(_("nombre"), max_length=150)
    name_en = models.CharField(_("nombre en inglés"), max_length=150, blank=True)
    is_required = models.BooleanField(_("obligatorio"), default=True)
    allowed_formats = models.CharField(
        _("formatos permitidos"),
        max_length=50,
        default="pdf,jpg,png",
        help_text=_("Extensiones separadas por coma. Soportadas: pdf, jpg, png."),
    )
    order = models.PositiveIntegerField(_("orden"), default=0)

    class Meta:
        verbose_name = _("documento requerido")
        verbose_name_plural = _("documentos requeridos")
        ordering = ["procedure", "order", "id"]

    def __str__(self):
        return self.name

    @property
    def display_name(self):
        return pick(self.name, self.name_en)

    @property
    def extensions(self):
        return [ext.strip().lower().lstrip(".") for ext in self.allowed_formats.split(",") if ext]


class ProcedureField(models.Model):
    """Campo adicional del formulario de radicación de un trámite."""

    class FieldType(models.TextChoices):
        TEXT = "text", _("Texto corto")
        TEXTAREA = "textarea", _("Texto largo")
        SELECT = "select", _("Lista de opciones")

    procedure = models.ForeignKey(
        ProcedureType, on_delete=models.CASCADE, related_name="fields", verbose_name=_("trámite")
    )
    key = models.SlugField(_("clave"), help_text=_("Identificador interno, p. ej. 'reason'."))
    label = models.CharField(_("etiqueta"), max_length=150)
    label_en = models.CharField(_("etiqueta en inglés"), max_length=150, blank=True)
    field_type = models.CharField(
        _("tipo"), max_length=10, choices=FieldType.choices, default=FieldType.TEXT
    )
    choices = models.TextField(
        _("opciones"),
        blank=True,
        help_text=_("Solo para listas. Una opción por línea: valor|Etiqueta|Label in English"),
    )
    is_required = models.BooleanField(_("obligatorio"), default=True)
    order = models.PositiveIntegerField(_("orden"), default=0)

    class Meta:
        verbose_name = _("campo del formulario")
        verbose_name_plural = _("campos del formulario")
        ordering = ["procedure", "order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["procedure", "key"], name="unique_field_key")
        ]

    def __str__(self):
        return self.label

    @property
    def display_label(self):
        return pick(self.label, self.label_en)

    def parsed_choices(self):
        """Lista de tuplas (valor, etiqueta en el idioma activo)."""
        result = []
        for line in self.choices.splitlines():
            parts = [p.strip() for p in line.split("|")]
            if not parts[0]:
                continue
            es = parts[1] if len(parts) > 1 else parts[0]
            en = parts[2] if len(parts) > 2 else ""
            result.append((parts[0], pick(es, en)))
        return result

    def display_value(self, value):
        if self.field_type == self.FieldType.SELECT:
            return dict(self.parsed_choices()).get(value, value)
        return value
