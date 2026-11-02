import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import Department, User
from apps.catalog.models import ProcedureField, ProcedureStage, ProcedureType, RequiredDocument
from apps.certificates.models import CertificateTemplate

PDF_BYTES = b"%PDF-1.4\n% prueba\n%%EOF\n"


@pytest.fixture(autouse=True)
def _media_and_mail(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.LANGUAGE_CODE = "es"


@pytest.fixture(autouse=True)
def _fake_pdf(monkeypatch):
    """Evita depender de las librerías de WeasyPrint en las pruebas."""
    monkeypatch.setattr(
        "apps.certificates.services.render_pdf", lambda html, base_url=None: PDF_BYTES
    )


def pdf_file(name="soporte.pdf", content=PDF_BYTES):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


@pytest.fixture
def departments(db):
    return {
        "coord": Department.objects.create(name="Coordinación de programa", name_en="Coordination"),
        "comite": Department.objects.create(name="Comité de carrera", name_en="Committee"),
        "registro": Department.objects.create(name="Admisiones y Registro", name_en="Registrar"),
    }


def make_user(username, role=User.Role.STUDENT, department=None, **extra):
    user = User.objects.create_user(
        username=username,
        password="demo1234",
        email=f"{username}@demo.local",
        role=role,
        department=department,
        first_name=username.capitalize(),
        last_name="Prueba",
        **extra,
    )
    return user


@pytest.fixture
def student(db):
    return make_user("estudiante1", document_number="123", program="Ingeniería de Sistemas")


@pytest.fixture
def other_student(db):
    return make_user("estudiante2")


@pytest.fixture
def staff(departments):
    return {
        key: make_user(f"func_{key}", role=User.Role.STAFF, department=dept)
        for key, dept in departments.items()
    }


@pytest.fixture
def admin_user(db):
    return make_user("admin", role=User.Role.ADMIN, is_staff=True, is_superuser=True)


@pytest.fixture
def homologation(departments):
    procedure = ProcedureType.objects.create(
        code="homologacion",
        name="Homologación",
        name_en="Credit transfer",
        description="Desc",
        requirements="Req 1\nReq 2",
    )
    for order, key in enumerate(["coord", "comite", "registro"], start=1):
        ProcedureStage.objects.create(
            procedure=procedure, order=order, department=departments[key], deadline_days=5
        )
    RequiredDocument.objects.create(procedure=procedure, name="Notas", allowed_formats="pdf")
    RequiredDocument.objects.create(
        procedure=procedure, name="Opcional", is_required=False, allowed_formats="pdf,jpg,png"
    )
    ProcedureField.objects.create(procedure=procedure, key="origin", label="Origen")
    return procedure


@pytest.fixture
def certificate_procedure(departments):
    procedure = ProcedureType.objects.create(
        code="certificado", name="Certificado", description="Desc", issues_certificate=True
    )
    ProcedureStage.objects.create(
        procedure=procedure, order=1, department=departments["registro"], deadline_days=2
    )
    ProcedureField.objects.create(
        procedure=procedure,
        key="certificate_kind",
        label="Tipo",
        field_type="select",
        choices="studies|Estudios|Studies\ngrades|Notas|Grades",
    )
    ProcedureField.objects.create(
        procedure=procedure,
        key="certificate_language",
        label="Idioma",
        field_type="select",
        choices="es|Español|Spanish\nen|Inglés|English\nboth|Ambos|Both",
    )
    for lang in ("es", "en"):
        CertificateTemplate.objects.update_or_create(
            kind="studies",
            language=lang,
            defaults={
                "title": f"Certificado {lang}",
                "body_html": "<p>{{ student_name }} · {{ program }} · {{ code }}</p>",
            },
        )
    return procedure


@pytest.fixture
def submitted_request(student, homologation, staff):
    from apps.requests import services

    req = services.create_request(student, homologation)
    services.update_form_data(req, student, {"origin": "Otra U"})
    services.attach_document(req, student, homologation.documents.get(name="Notas"), pdf_file())
    services.submit(req, student)
    return req
