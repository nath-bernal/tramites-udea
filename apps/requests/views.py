from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.accounts.permissions import role_required
from apps.catalog.models import ProcedureType
from apps.certificates.pdf import CertificateRenderError
from apps.certificates.services import CertificateError

from . import services
from .forms import RequestForm, ReviewForm
from .models import ACTIVE_STATUSES, RequestDocument, Status


def _error_messages(exc):
    return exc.messages if isinstance(exc, ValidationError) else [str(exc)]


@role_required("is_student")
def my_requests(request):
    requests_qs = services.visible_requests(request.user)
    return render(request, "requests/my_requests.html", {"requests": requests_qs})


def _save_form(req, user, form):
    services.update_form_data(req, user, form.form_data())
    for doc, uploaded in form.uploaded_documents():
        services.attach_document(req, user, doc, uploaded)


def _handle_submission(request, req, action):
    """Radica o reenvía según el botón presionado; devuelve True si quedó enviada."""
    if action != "submit":
        messages.success(request, _("Borrador guardado."))
        return False
    try:
        if req.status == Status.DRAFT:
            services.submit(req, request.user)
            messages.success(
                request, _("Solicitud radicada con el número %(number)s.") % {"number": req.number}
            )
        else:
            services.resubmit(req, request.user, request.POST.get("response", ""))
            messages.success(request, _("Ajustes enviados. Tu solicitud volvió a revisión."))
        return True
    except (ValidationError, services.TransitionError) as exc:
        for msg in _error_messages(exc):
            messages.error(request, msg)
        return False


@role_required("is_student")
def new_request(request, code):
    procedure = get_object_or_404(ProcedureType, code=code, is_active=True)
    form = RequestForm(request.POST or None, request.FILES or None, procedure=procedure)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            req = services.create_request(request.user, procedure)
            _save_form(req, request.user, form)
        if _handle_submission(request, req, request.POST.get("action")):
            return redirect("requests:detail", pk=req.pk)
        return redirect("requests:edit", pk=req.pk)
    return render(
        request, "requests/form.html", {"form": form, "procedure": procedure, "req": None}
    )


@role_required("is_student")
def edit_request(request, pk):
    req = get_object_or_404(services.visible_requests(request.user), pk=pk)
    if not req.is_editable:
        return redirect("requests:detail", pk=req.pk)
    form = RequestForm(
        request.POST or None, request.FILES or None, procedure=req.procedure, request_obj=req
    )
    if request.method == "POST" and form.is_valid():
        _save_form(req, request.user, form)
        if _handle_submission(request, req, request.POST.get("action")):
            return redirect("requests:detail", pk=req.pk)
        return redirect("requests:edit", pk=req.pk)
    last_comment = req.events.filter(to_status=Status.NEEDS_CHANGES).last()
    return render(
        request,
        "requests/form.html",
        {
            "form": form,
            "procedure": req.procedure,
            "req": req,
            "missing": services.missing_documents(req),
            "last_comment": last_comment,
        },
    )


@role_required("is_student")
@require_POST
def delete_request(request, pk):
    req = get_object_or_404(services.visible_requests(request.user), pk=pk)
    try:
        services.delete_draft(req, request.user)
        messages.success(request, _("Borrador eliminado."))
    except services.TransitionError as exc:
        messages.error(request, str(exc))
    return redirect("requests:my_requests")


def _stage_steps(req):
    """Estado de cada etapa para el indicador de progreso."""
    steps = []
    current_order = req.current_stage.order if req.current_stage else None
    for stage in req.procedure.ordered_stages():
        if req.status == Status.FINALIZED or req.status in (Status.APPROVED, Status.REJECTED):
            state = "done" if stage.order <= (current_order or 0) else "skipped"
            if req.outcome == "REJECTED" and stage.order == current_order:
                state = "rejected"
        elif current_order is None:
            state = "pending"
        elif stage.order < current_order:
            state = "done"
        elif stage.order == current_order:
            state = "current"
        else:
            state = "pending"
        steps.append({"stage": stage, "state": state})
    return steps


@role_required("is_student", "is_official", "is_admin_role")
def request_detail(request, pk):
    req = get_object_or_404(services.visible_requests(request.user), pk=pk)
    context = {
        "req": req,
        "events": req.events.select_related("actor", "stage__department"),
        "steps": _stage_steps(req),
        "documents": req.documents.select_related("required_document"),
        "certificates": req.certificates.all() if req.status == Status.FINALIZED else [],
        "can_review": services.can_review(request.user, req),
        "review_form": ReviewForm(),
    }
    return render(request, "requests/detail.html", context)


@role_required("is_official")
@require_POST
def review(request, pk):
    req = get_object_or_404(services.visible_requests(request.user), pk=pk)
    form = ReviewForm(request.POST)
    if not form.is_valid():
        messages.error(request, _("Acción no válida."))
        return redirect("requests:detail", pk=pk)
    action = form.cleaned_data["action"]
    comment = form.cleaned_data["comment"]
    actions = {
        "approve": services.approve,
        "reject": services.reject,
        "changes": services.request_changes,
    }
    try:
        actions[action](req, request.user, comment)
    except (ValidationError, services.TransitionError, CertificateError) as exc:
        for msg in _error_messages(exc):
            messages.error(request, msg)
        return redirect("requests:detail", pk=pk)
    except CertificateRenderError as exc:
        messages.error(request, _("No se pudo generar el PDF del certificado: %(e)s") % {"e": exc})
        return redirect("requests:detail", pk=pk)
    labels = {
        "approve": _("Etapa aprobada."),
        "reject": _("Solicitud rechazada."),
        "changes": _("Se pidieron ajustes al estudiante."),
    }
    messages.success(request, f"{req.number}: {labels[action]}")
    return redirect("requests:inbox")


@role_required("is_official", "is_admin_role")
def inbox(request):
    qs = services.visible_requests(request.user).filter(status__in=ACTIVE_STATUSES)
    procedure = request.GET.get("procedure", "")
    deadline = request.GET.get("deadline", "")
    if procedure:
        qs = qs.filter(procedure__code=procedure)
    rows = sorted(qs, key=lambda r: r.stage_entered_at)
    if deadline:
        rows = [r for r in rows if r.deadline_state == deadline]
    context = {
        "rows": rows,
        "procedures": ProcedureType.objects.filter(is_active=True),
        "selected_procedure": procedure,
        "selected_deadline": deadline,
        "overdue_count": sum(1 for r in rows if r.deadline_state == "overdue"),
    }
    if request.headers.get("HX-Request") and request.headers.get("HX-Target") == "inbox-table":
        return render(request, "requests/_inbox_table.html", context)
    return render(request, "requests/inbox.html", context)


@role_required("is_student", "is_official", "is_admin_role")
def download_document(request, pk):
    document = get_object_or_404(RequestDocument.objects.select_related("request"), pk=pk)
    if not services.visible_requests(request.user).filter(pk=document.request_id).exists():
        raise Http404
    return FileResponse(
        document.file.open("rb"), as_attachment=True, filename=document.original_name
    )
