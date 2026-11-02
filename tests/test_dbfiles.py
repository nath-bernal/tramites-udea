import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.urls import reverse

from apps.dbfiles.models import StoredFile
from apps.dbfiles.storage import DatabaseStorage
from apps.requests import services

pytestmark = pytest.mark.django_db


@pytest.fixture
def db_storage(settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "apps.dbfiles.storage.DatabaseStorage"},
    }
    storages._storages.pop("default", None)
    yield
    storages._storages.pop("default", None)


def test_save_open_delete():
    storage = DatabaseStorage()
    name = storage.save("requests/a.pdf", ContentFile(b"%PDF-hola"))
    assert storage.exists(name)
    assert storage.size(name) == 9
    assert storage.open(name).read() == b"%PDF-hola"
    storage.delete(name)
    assert not storage.exists(name)
    with pytest.raises(FileNotFoundError):
        storage.open(name)


def test_full_flow_with_database_storage(db_storage, client, student, certificate_procedure, staff):
    req = services.create_request(student, certificate_procedure)
    services.update_form_data(
        req, student, {"certificate_kind": "studies", "certificate_language": "es"}
    )
    services.submit(req, student)
    services.approve(req, staff["registro"])
    certificate = req.certificates.get()
    assert StoredFile.objects.filter(name=certificate.pdf.name).exists()
    client.force_login(student)
    response = client.get(reverse("certificates:download", args=[certificate.pk]))
    assert b"".join(response.streaming_content).startswith(b"%PDF")


def test_uploaded_document_in_database(db_storage, submitted_request, client):
    doc = submitted_request.documents.get()
    assert StoredFile.objects.filter(name=doc.file.name).exists()
    client.force_login(submitted_request.student)
    response = client.get(reverse("requests:document", args=[doc.pk]))
    assert b"".join(response.streaming_content).startswith(b"%PDF")
