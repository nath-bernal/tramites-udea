from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class Department(models.Model):
    """Dependencia que revisa una etapa de un trámite."""

    name = models.CharField(_("nombre"), max_length=120, unique=True)
    name_en = models.CharField(_("nombre en inglés"), max_length=120, blank=True)

    class Meta:
        verbose_name = _("dependencia")
        verbose_name_plural = _("dependencias")
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def display_name(self):
        from apps.catalog.i18n import pick

        return pick(self.name, self.name_en)


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", _("Estudiante")
        STAFF = "staff", _("Funcionario")
        ADMIN = "admin", _("Administrador")

    role = models.CharField(_("rol"), max_length=10, choices=Role.choices, default=Role.STUDENT)
    document_number = models.CharField(_("documento"), max_length=20, blank=True)
    program = models.CharField(_("programa"), max_length=150, blank=True)
    department = models.ForeignKey(
        Department,
        verbose_name=_("dependencia"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="members",
        help_text=_("Solo para funcionarios."),
    )
    language = models.CharField(
        _("idioma preferido"),
        max_length=2,
        choices=[("es", "Español"), ("en", "English")],
        default="es",
    )

    class Meta:
        verbose_name = _("usuario")
        verbose_name_plural = _("usuarios")

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_official(self):
        return self.role == self.Role.STAFF

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    def __str__(self):
        return self.get_full_name() or self.username
