import re

import pytest
from django.urls import reverse

from apps.certificates.models import IssuedCertificate, generate_verification_code
from apps.certificates.services import build_certificate_html
from apps.requests import services

pytestmark = pytest.mark.django_db


@pytest.fixture
def certificate_request(student, certificate_procedure):
    def make(language="both", kind="studies"):
        req = services.create_request(student, certificate_procedure)
        services.update_form_data(
            req, student, {"certificate_kind": kind, "certificate_language": language}
        )
        services.submit(req, student)
        return req

    return make


def test_approval_issues_both_languages(certificate_request, staff):
    req = certificate_request("both")
    services.approve(req, staff["registro"])
    languages = sorted(req.certificates.values_list("language", flat=True))
    assert languages == ["en", "es"]
    assert req.events.last().comment.startswith("Certificados emitidos")


def test_single_language(certificate_request, staff):
    req = certificate_request("en")
    services.approve(req, staff["registro"])
    assert list(req.certificates.values_list("language", flat=True)) == ["en"]


def test_missing_template_rolls_back_approval(certificate_request, staff):
    from apps.certificates.models import CertificateTemplate
    from apps.certificates.services import CertificateError

    CertificateTemplate.objects.filter(kind="grades").delete()
    req = certificate_request("es", kind="grades")
    with pytest.raises(CertificateError):
        services.approve(req, staff["registro"])
    req.refresh_from_db()
    assert req.status == "SUBMITTED"
    assert not IssuedCertificate.objects.exists()


def test_code_format_and_uniqueness():
    codes = {generate_verification_code() for _ in range(500)}
    assert len(codes) == 500
    assert all(re.fullmatch(r"[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}", c) for c in codes)


def test_certificate_html_has_watermark_qr_and_data(certificate_request, certificate_procedure):
    from apps.certificates.models import CertificateTemplate

    req = certificate_request("es")
    template = CertificateTemplate.objects.get(kind="studies", language="en")
    html = build_certificate_html(req, template, "ABCD-EFGH-JKMN")
    assert "PROTOTIPO ACADÉMICO – SIN VALIDEZ OFICIAL" in html
    assert "data:image/png;base64," in html
    assert "Ingeniería de Sistemas" in html
    assert "/certificados/verificar/ABCD-EFGH-JKMN/" in html
    assert "Verification code" in html


def test_public_verification(client, certificate_request, staff):
    req = certificate_request("es")
    services.approve(req, staff["registro"])
    certificate = req.certificates.get()
    response = client.get(reverse("certificates:verify_code", args=[certificate.code]))
    assert response.status_code == 200
    assert "Certificado válido" in response.content.decode()
    # El formulario acepta el código en minúsculas.
    response = client.get(reverse("certificates:verify"), {"code": certificate.code.lower()})
    assert response["Location"].endswith(f"{certificate.code}/")
    response = client.get(reverse("certificates:verify_code", args=["XXXX-XXXX-XXXX"]))
    assert response.status_code == 404
    assert "no encontrado" in response.content.decode()


def test_certificate_download_permissions(client, certificate_request, staff, other_student):
    req = certificate_request("es")
    services.approve(req, staff["registro"])
    url = reverse("certificates:download", args=[req.certificates.get().pk])
    client.force_login(other_student)
    assert client.get(url).status_code == 404
    client.force_login(req.student)
    response = client.get(url)
    assert response.status_code == 200
    assert b"".join(response.streaming_content).startswith(b"%PDF")


def test_real_pdf_rendering_if_available(certificate_request, certificate_procedure):
    """Prueba de integración con WeasyPrint; se omite si faltan las librerías del sistema."""
    from apps.certificates.models import CertificateTemplate
    from apps.certificates.pdf import CertificateRenderError, render_pdf

    req = certificate_request("es")
    html = build_certificate_html(
        req, CertificateTemplate.objects.get(kind="studies", language="es"), "AAAA-BBBB-CCCC"
    )
    try:
        pdf = render_pdf(html)
    except CertificateRenderError:
        pytest.skip("WeasyPrint sin librerías del sistema")
    assert pdf.startswith(b"%PDF")


def test_academic_record_is_stable_and_consistent(student):
    from apps.certificates.academic import academic_record, weighted_average

    first = academic_record(student)
    assert first == academic_record(student)
    assert 7 <= len(first) <= 10
    assert all(3 <= r.grade <= 5 for r in first)
    average = weighted_average(first)
    assert min(r.grade for r in first) <= average <= max(r.grade for r in first)
    english = academic_record(student, "en")
    assert [r.code for r in english] == [r.code for r in first]
    assert english[0].name == "Differential Calculus"


@pytest.mark.parametrize(
    ("kind", "language", "expected"),
    [
        (
            "contents",
            "es",
            ["Certificado de contenidos", "Cálculo diferencial", "Funciones reales"],
        ),
        (
            "contents",
            "en",
            ["Course Content Certificate", "Differential Calculus", "Real functions"],
        ),
        ("grades", "es", ["Certificado de notas", "Cálculo diferencial", "Promedio crédito"]),
        ("grades", "en", ["Grades Certificate", "Differential Calculus", "Cumulative grade"]),
        ("studies", "es", ["Certificado de estudios", "créditos"]),
    ],
)
def test_each_certificate_kind_has_its_own_content(certificate_request, kind, language, expected):
    """Las plantillas reales (creadas por migración) muestran el contenido de cada tipo."""
    from apps.certificates.defaults import TEMPLATES
    from apps.certificates.models import CertificateTemplate

    title, body = TEMPLATES[(kind, language)]
    template, _ = CertificateTemplate.objects.update_or_create(
        kind=kind, language=language, defaults={"title": title, "body_html": body}
    )
    req = certificate_request(language)
    html = build_certificate_html(req, template, "ABCD-EFGH-JKMN")
    for text in expected:
        assert text in html
    if kind == "studies":
        assert "Cálculo diferencial" not in html
