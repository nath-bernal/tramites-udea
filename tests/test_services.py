import re

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.requests import services
from apps.requests.models import Outcome, Status

from .conftest import pdf_file


def test_submit_assigns_number_and_first_stage(submitted_request, departments):
    req = submitted_request
    assert re.fullmatch(r"TC-\d{4}-000001", req.number)
    assert req.status == Status.SUBMITTED
    assert req.current_stage.department == departments["coord"]
    event = req.events.get()
    assert (event.from_status, event.to_status) == (Status.DRAFT, Status.SUBMITTED)


def test_numbers_are_sequential(submitted_request, student, homologation):
    req = services.create_request(student, homologation)
    services.attach_document(req, student, homologation.documents.get(name="Notas"), pdf_file())
    services.submit(req, student)
    assert req.number.endswith("000002")


def test_submit_requires_mandatory_documents(student, homologation):
    req = services.create_request(student, homologation)
    with pytest.raises(ValidationError, match="Notas"):
        services.submit(req, student)
    req.refresh_from_db()
    assert req.status == Status.DRAFT
    assert req.events.count() == 0


def test_full_flow_through_all_stages(submitted_request, staff, departments):
    req = submitted_request
    services.approve(req, staff["coord"], "ok")
    assert req.status == Status.IN_REVIEW
    assert req.current_stage.department == departments["comite"]
    services.approve(req, staff["comite"])
    assert req.current_stage.department == departments["registro"]
    services.approve(req, staff["registro"])
    assert req.status == Status.FINALIZED
    assert req.outcome == Outcome.APPROVED
    assert req.resolved_at is not None
    statuses = list(req.events.values_list("to_status", flat=True))
    assert statuses == [
        Status.SUBMITTED,
        Status.IN_REVIEW,
        Status.IN_REVIEW,
        Status.APPROVED,
        Status.FINALIZED,
    ]


def test_staff_of_other_department_cannot_approve(submitted_request, staff):
    with pytest.raises(PermissionDenied):
        services.approve(submitted_request, staff["comite"])


def test_student_cannot_approve(submitted_request, student):
    with pytest.raises(PermissionDenied):
        services.approve(submitted_request, student)


def test_request_changes_and_resubmit_keeps_stage(submitted_request, staff, student):
    req = submitted_request
    services.approve(req, staff["coord"])
    stage = req.current_stage
    services.request_changes(req, staff["comite"], "Falta firma")
    assert req.status == Status.NEEDS_CHANGES
    # Mientras espera ajustes no está en ninguna bandeja.
    assert not services.can_review(staff["comite"], req)
    services.resubmit(req, student, "Corregido")
    assert req.status == Status.IN_REVIEW
    assert req.current_stage == stage
    assert req.events.last().comment == "Corregido"


def test_reject_and_changes_require_comment(submitted_request, staff):
    with pytest.raises(ValidationError):
        services.reject(submitted_request, staff["coord"], "  ")
    with pytest.raises(ValidationError):
        services.request_changes(submitted_request, staff["coord"], "")


def test_reject_finalizes(submitted_request, staff):
    services.reject(submitted_request, staff["coord"], "No cumple")
    assert submitted_request.status == Status.FINALIZED
    assert submitted_request.outcome == Outcome.REJECTED


def test_invalid_transition_raises(submitted_request, student):
    with pytest.raises(services.TransitionError):
        services.resubmit(submitted_request, student)


def test_finalized_request_cannot_be_acted_on(submitted_request, staff):
    services.reject(submitted_request, staff["coord"], "No")
    with pytest.raises(PermissionDenied):
        services.approve(submitted_request, staff["coord"])


def test_student_cannot_edit_after_submit(submitted_request, student):
    with pytest.raises(services.TransitionError):
        services.update_form_data(submitted_request, student, {})


def test_other_student_cannot_edit(student, other_student, homologation):
    req = services.create_request(student, homologation)
    with pytest.raises(PermissionDenied):
        services.update_form_data(req, other_student, {})


def test_attach_replaces_existing_document(student, homologation):
    req = services.create_request(student, homologation)
    doc = homologation.documents.get(name="Notas")
    services.attach_document(req, student, doc, pdf_file("a.pdf"))
    services.attach_document(req, student, doc, pdf_file("b.pdf"))
    assert list(req.documents.values_list("original_name", flat=True)) == ["b.pdf"]


def test_uploaded_file_name_is_random(submitted_request):
    stored = submitted_request.documents.get().file.name
    assert "soporte" not in stored
    assert re.fullmatch(r"requests/[0-9a-f]{32}\.pdf", stored)


def test_delete_only_drafts(submitted_request, student):
    with pytest.raises(services.TransitionError):
        services.delete_draft(submitted_request, student)
