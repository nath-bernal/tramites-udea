import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.requests.models import Request, Status

from .conftest import pdf_file

pytestmark = pytest.mark.django_db


def _post(client, procedure, action, **files):
    data = {"origin": "Otra U", "action": action}
    notas = procedure.documents.get(name="Notas")
    if "notas" in files:
        data[f"doc_{notas.pk}"] = files["notas"]
    return client.post(reverse("requests:new", args=[procedure.code]), data)


def test_student_submits_online(client, student, homologation, staff):
    client.force_login(student)
    response = _post(client, homologation, "submit", notas=pdf_file())
    req = Request.objects.get()
    assert response.status_code == 302
    assert response["Location"] == reverse("requests:detail", args=[req.pk])
    assert req.status == Status.SUBMITTED
    assert req.form_data == {"origin": "Otra U"}


def test_submit_without_documents_keeps_draft(client, student, homologation):
    client.force_login(student)
    response = _post(client, homologation, "submit")
    req = Request.objects.get()
    assert req.status == Status.DRAFT
    assert response["Location"] == reverse("requests:edit", args=[req.pk])
    page = client.get(response["Location"]).content.decode()
    assert "Faltan documentos obligatorios" in page


def test_save_draft(client, student, homologation):
    client.force_login(student)
    _post(client, homologation, "draft")
    assert Request.objects.get().status == Status.DRAFT


@pytest.mark.parametrize(
    ("name", "content", "error"),
    [
        ("virus.exe", b"MZ...", "Formato no permitido"),
        ("falso.pdf", b"no soy un pdf", "no corresponde"),
        ("grande.pdf", b"%PDF" + b"0" * (5 * 1024 * 1024 + 1), "máximo"),
    ],
)
def test_invalid_uploads_are_rejected(client, student, homologation, name, content, error):
    client.force_login(student)
    upload = SimpleUploadedFile(name, content)
    response = _post(client, homologation, "submit", notas=upload)
    assert response.status_code == 200
    assert error in response.content.decode()
    assert not Request.objects.exists()


def test_jpg_accepted_where_allowed(student, homologation):
    from apps.requests.validators import validate_upload

    validate_upload(SimpleUploadedFile("foto.JPG", b"\xff\xd8\xff\xe0rest"), ["pdf", "jpg"])


def test_needs_changes_flow_via_views(client, submitted_request, staff, student):
    client.force_login(staff["coord"])
    client.post(
        reverse("requests:review", args=[submitted_request.pk]),
        {"action": "changes", "comment": "Sube el documento legible"},
    )
    submitted_request.refresh_from_db()
    assert submitted_request.status == Status.NEEDS_CHANGES

    client.force_login(student)
    edit_url = reverse("requests:edit", args=[submitted_request.pk])
    assert "Sube el documento legible" in client.get(edit_url).content.decode()
    client.post(edit_url, {"origin": "Otra U", "action": "submit", "response": "Listo"})
    submitted_request.refresh_from_db()
    assert submitted_request.status == Status.IN_REVIEW


def test_catalog_search_and_inactive_hidden(client, homologation, certificate_procedure):
    certificate_procedure.is_active = False
    certificate_procedure.save()
    page = client.get(reverse("catalog:list")).content.decode()
    assert "Homologación" in page
    assert "Certificado" not in page
    response = client.get(
        reverse("catalog:list"), {"q": "zzz"}, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="results"
    )
    assert "<html" not in response.content.decode()
    assert client.get(reverse("catalog:detail", args=["certificado"])).status_code == 404
