import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.accounts.models import User
from apps.catalog.models import ProcedureType
from apps.requests.models import Request

pytestmark = pytest.mark.django_db


def test_seed_demo_is_idempotent():
    call_command("seed_demo")
    call_command("seed_demo")
    assert ProcedureType.objects.count() == 4
    for username in [
        "estudiante1",
        "funcionario_coordinacion",
        "funcionario_comite",
        "funcionario_registro",
        "admin",
    ]:
        assert User.objects.get(username=username).check_password("demo1234")
    assert Request.objects.filter(status="NEEDS_CHANGES").exists()
    assert Request.objects.filter(status="FINALIZED").count() == 2


def test_pages_render_for_each_demo_user(client):
    call_command("seed_demo")
    pages = {
        "estudiante1": ["requests:my_requests", "catalog:list", "notifications:list"],
        "funcionario_coordinacion": ["requests:inbox"],
        "admin": ["metrics:dashboard", "requests:inbox"],
    }
    for username, names in pages.items():
        client.force_login(User.objects.get(username=username))
        for name in names:
            assert client.get(reverse(name)).status_code == 200, (username, name)
        for req in Request.objects.all():
            response = client.get(reverse("requests:detail", args=[req.pk]))
            assert response.status_code in (200, 404)


def test_english_interface(client, homologation):
    client.post(reverse("set_language"), {"language": "en", "next": "/"})
    page = client.get(reverse("catalog:list")).content.decode()
    assert "Procedure catalog" in page
    assert "Credit transfer" in page


def test_language_preference_saved(client, student):
    client.force_login(student)
    client.post(reverse("set_language"), {"language": "en", "next": "/"})
    student.refresh_from_db()
    assert student.language == "en"


def test_register_creates_student(client):
    response = client.post(
        reverse("accounts:register"),
        {
            "username": "nuevo",
            "first_name": "N",
            "last_name": "U",
            "email": "n@demo.local",
            "document_number": "9",
            "program": "Ing",
            "password1": "clave-segura-123",
            "password2": "clave-segura-123",
        },
    )
    assert response.status_code == 302
    assert User.objects.get(username="nuevo").role == "student"


def test_spanish_even_if_browser_is_in_english(client, homologation):
    page = client.get(reverse("catalog:list"), HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9")
    html = page.content.decode()
    assert "Catálogo de trámites" in html
    assert "Procedure catalog" not in html
