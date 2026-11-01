"""Única puerta para cambiar el estado de una solicitud.

Cada transición valida que sea permitida y que el actor tenga permiso, crea su
``RequestEvent`` y dispara las notificaciones. Las vistas nunca cambian ``status``
directamente.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.notifications.services import notify_event

from .models import ACTIVE_STATUSES, Outcome, Request, RequestDocument, RequestEvent, Status

ALLOWED_TRANSITIONS = {
    Status.DRAFT: {Status.SUBMITTED},
    Status.SUBMITTED: {Status.IN_REVIEW, Status.NEEDS_CHANGES, Status.APPROVED, Status.REJECTED},
    # IN_REVIEW → IN_REVIEW ocurre al pasar a la siguiente etapa.
    Status.IN_REVIEW: {Status.IN_REVIEW, Status.NEEDS_CHANGES, Status.APPROVED, Status.REJECTED},
    Status.NEEDS_CHANGES: {Status.IN_REVIEW},
    Status.APPROVED: {Status.FINALIZED},
    Status.REJECTED: {Status.FINALIZED},
    Status.FINALIZED: set(),
}


class TransitionError(Exception):
    """La transición pedida no es válida para el estado actual."""


# --- Consultas con permisos --------------------------------------------------------------


def visible_requests(user):
    """Solicitudes que el usuario puede ver.

    - Estudiante: solo las suyas.
    - Funcionario: solo las de su dependencia que están en su etapa actual.
    - Administrador: todas.
    """
    qs = Request.objects.select_related("procedure", "student", "current_stage__department")
    if user.is_admin_role:
        return qs
    if user.is_official:
        if not user.department_id:
            return qs.none()
        return qs.filter(
            status__in=ACTIVE_STATUSES, current_stage__department_id=user.department_id
        )
    return qs.filter(student=user)


def can_review(user, req):
    return (
        user.is_official
        and user.department_id is not None
        and req.is_active
        and req.current_stage is not None
        and req.current_stage.department_id == user.department_id
    )


def missing_documents(req):
    uploaded = set(req.documents.values_list("required_document_id", flat=True))
    return [
        doc for doc in req.procedure.documents.all() if doc.is_required and doc.pk not in uploaded
    ]


# --- Edición por el estudiante -------------------------------------------------------------


def _check_owner_can_edit(req, actor):
    if actor.pk != req.student_id:
        raise PermissionDenied
    if not req.is_editable:
        raise TransitionError(_("La solicitud ya no se puede editar."))


def create_request(student, procedure):
    if not student.is_student:
        raise PermissionDenied
    if not procedure.is_active:
        raise TransitionError(_("Este trámite no está disponible."))
    return Request.objects.create(student=student, procedure=procedure)


def update_form_data(req, actor, form_data):
    _check_owner_can_edit(req, actor)
    req.form_data = form_data
    req.save(update_fields=["form_data", "updated_at"])


def attach_document(req, actor, required_document, uploaded_file):
    """Guarda o reemplaza el archivo de un documento requerido (ya validado por el formulario)."""
    _check_owner_can_edit(req, actor)
    if required_document.procedure_id != req.procedure_id:
        raise ValidationError(_("El documento no pertenece a este trámite."))
    existing = req.documents.filter(required_document=required_document).first()
    if existing:
        existing.file.delete(save=False)
        existing.delete()
    return RequestDocument.objects.create(
        request=req,
        required_document=required_document,
        file=uploaded_file,
        original_name=uploaded_file.name[:255],
    )


def delete_draft(req, actor):
    if actor.pk != req.student_id:
        raise PermissionDenied
    if req.status != Status.DRAFT:
        raise TransitionError(_("Solo se pueden eliminar borradores."))
    for doc in req.documents.all():
        doc.file.delete(save=False)
    req.delete()


# --- Transiciones ------------------------------------------------------------------------


def _record(req, to_status, actor, comment="", stage=None):
    if to_status not in ALLOWED_TRANSITIONS[req.status]:
        raise TransitionError(
            _("No se puede pasar de «%(from)s» a «%(to)s».")
            % {"from": Status(req.status).label, "to": Status(to_status).label}
        )
    event = RequestEvent.objects.create(
        request=req,
        from_status=req.status,
        to_status=to_status,
        stage=stage or req.current_stage,
        actor=actor,
        comment=comment,
    )
    req.status = to_status
    return event


def _next_number(year):
    # Suficiente para el prototipo; la restricción unique evita duplicados si hay carrera.
    prefix = f"TC-{year}-"
    last = (
        Request.objects.filter(number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    seq = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{seq:06d}"


def _check_documents(req):
    missing = missing_documents(req)
    if missing:
        raise ValidationError(
            _("Faltan documentos obligatorios: %(docs)s.")
            % {"docs": ", ".join(doc.display_name for doc in missing)}
        )


def _check_reviewer(req, actor):
    if not can_review(actor, req):
        raise PermissionDenied


def _require_comment(comment):
    if not comment.strip():
        raise ValidationError(_("Debes escribir un comentario para el estudiante."))


@transaction.atomic
def submit(req, actor):
    """BORRADOR → RADICADA en la primera etapa."""
    _check_owner_can_edit(req, actor)
    if req.status != Status.DRAFT:
        raise TransitionError(_("La solicitud ya fue radicada."))
    _check_documents(req)
    stage = req.procedure.first_stage()
    if stage is None:
        raise TransitionError(_("El trámite no tiene etapas configuradas."))
    now = timezone.now()
    req.number = _next_number(timezone.localdate(now).year)
    req.current_stage = stage
    req.submitted_at = now
    req.stage_entered_at = now
    event = _record(req, Status.SUBMITTED, actor, stage=stage)
    req.save()
    notify_event(event)
    return req


@transaction.atomic
def resubmit(req, actor, comment=""):
    """REQUIERE_AJUSTES → EN_REVISION en la misma etapa."""
    if req.status != Status.NEEDS_CHANGES:
        raise TransitionError(_("La solicitud no tiene ajustes pendientes."))
    _check_owner_can_edit(req, actor)
    _check_documents(req)
    req.stage_entered_at = timezone.now()
    event = _record(req, Status.IN_REVIEW, actor, comment)
    req.save()
    notify_event(event)
    return req


@transaction.atomic
def approve(req, actor, comment=""):
    """Aprueba la etapa actual: pasa a la siguiente o, si es la última, aprueba y finaliza."""
    _check_reviewer(req, actor)
    next_stage = req.current_stage.next_stage()
    if next_stage:
        req.current_stage = next_stage
        req.stage_entered_at = timezone.now()
        event = _record(req, Status.IN_REVIEW, actor, comment, stage=next_stage)
        req.save()
        notify_event(event)
        return req
    _record(req, Status.APPROVED, actor, comment)
    req.outcome = Outcome.APPROVED
    req.resolved_at = timezone.now()
    req.save()
    return _finalize(req, actor)


@transaction.atomic
def reject(req, actor, comment):
    _check_reviewer(req, actor)
    _require_comment(comment)
    _record(req, Status.REJECTED, actor, comment)
    req.outcome = Outcome.REJECTED
    req.resolved_at = timezone.now()
    req.save()
    return _finalize(req, actor)


@transaction.atomic
def request_changes(req, actor, comment):
    _check_reviewer(req, actor)
    _require_comment(comment)
    event = _record(req, Status.NEEDS_CHANGES, actor, comment)
    req.save()
    notify_event(event)
    return req


def _finalize(req, actor):
    """APROBADA | RECHAZADA → FINALIZADA. Si aplica, emite los certificados."""
    comment = ""
    if req.outcome == Outcome.APPROVED and req.procedure.issues_certificate:
        from apps.certificates.services import issue_certificates

        certificates = issue_certificates(req)
        comment = _("Certificados emitidos: %(langs)s.") % {
            "langs": ", ".join(c.get_language_display() for c in certificates)
        }
    event = _record(req, Status.FINALIZED, actor, comment)
    req.save()
    notify_event(event)
    return req
