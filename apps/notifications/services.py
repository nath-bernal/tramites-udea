import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _

from .models import Notification

logger = logging.getLogger(__name__)


def notify(user, req, build_message):
    """Crea la notificación en la app y envía el correo en el idioma del destinatario.

    ``build_message`` es una función sin argumentos que arma el texto; se ejecuta con el
    idioma del usuario activado para que ``gettext`` lo traduzca.
    """
    with translation.override(user.language or settings.LANGUAGE_CODE):
        message = build_message()
        subject = _("Trámite Claro: %(number)s") % {"number": req.number or ""}
        link = f"{settings.SITE_URL}{reverse('requests:detail', args=[req.pk])}"
        body = f"{message}\n\n{link}\n\n— " + _("Trámite Claro (prototipo académico)")
    notification = Notification.objects.create(user=user, request=req, message=message)
    if user.email:
        try:
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
        except Exception:  # el correo nunca debe romper el flujo del trámite
            logger.exception("No se pudo enviar el correo de notificación a %s", user.email)
    return notification


def _department_members(department):
    User = get_user_model()
    return User.objects.filter(role=User.Role.STAFF, department=department, is_active=True)


def notify_event(event):
    """Avisa al estudiante y, si la solicitud entra a una bandeja, a esa dependencia."""
    from apps.requests.models import Outcome, Status

    req = event.request
    procedure = req.procedure
    to_status = event.to_status
    stage = event.stage

    def student_message():
        params = {"number": req.number, "procedure": procedure.display_name}
        if to_status == Status.SUBMITTED:
            return _("Tu solicitud %(number)s de %(procedure)s fue radicada.") % params
        if to_status == Status.IN_REVIEW:
            if event.from_status == Status.NEEDS_CHANGES:
                return _("Tu solicitud %(number)s volvió a revisión con tus ajustes.") % params
            params["department"] = stage.department.display_name
            return _("Tu solicitud %(number)s pasó a revisión en %(department)s.") % params
        if to_status == Status.NEEDS_CHANGES:
            params["comment"] = event.comment
            return _("Tu solicitud %(number)s requiere ajustes: %(comment)s") % params
        if to_status == Status.FINALIZED:
            if req.outcome == Outcome.APPROVED:
                if procedure.issues_certificate:
                    return (
                        _(
                            "Tu solicitud %(number)s fue aprobada. Ya puedes descargar tus "
                            "certificados."
                        )
                        % params
                    )
                return _("Tu solicitud %(number)s fue aprobada.") % params
            return _("Tu solicitud %(number)s fue rechazada.") % params
        return None

    if to_status in (Status.SUBMITTED, Status.IN_REVIEW, Status.NEEDS_CHANGES, Status.FINALIZED):
        notify(req.student, req, student_message)

    if to_status in (Status.SUBMITTED, Status.IN_REVIEW) and stage is not None:

        def staff_message():
            return _("Nueva solicitud %(number)s de %(procedure)s en tu bandeja.") % {
                "number": req.number,
                "procedure": procedure.display_name,
            }

        for member in _department_members(stage.department):
            notify(member, req, staff_message)


def notify_overdue(req):
    """Alerta a la dependencia de la etapa actual que la solicitud superó su plazo."""

    def message():
        return _("La solicitud %(number)s superó el plazo de su etapa (vencía el %(due)s).") % {
            "number": req.number,
            "due": req.stage_due_date.strftime("%d/%m/%Y"),
        }

    return [
        notify(member, req, message) for member in _department_members(req.current_stage.department)
    ]
