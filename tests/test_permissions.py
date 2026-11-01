import pytest
from django.urls import reverse

from apps.requests import services
from apps.requests.models import Status

pytestmark = pytest.mark.django_db


def test_visible_requests_by_role(submitted_request, other_student, staff, admin_user):
    assert list(services.visible_requests(submitted_request.student)) == [submitted_request]
    assert not services.visible_requests(other_student).exists()
    assert list(services.visible_requests(staff["coord"])) == [submitted_request]
    assert not services.visible_requests(staff["comite"]).exists()
    assert services.visible_requests(admin_user).count() == 1


def test_staff_loses_access_after_stage_moves(submitted_request, staff):
    services.approve(submitted_request, staff["coord"])
    assert not services.visible_requests(staff["coord"]).exists()
    assert list(services.visible_requests(staff["comite"])) == [submitted_request]


def test_staff_without_department_sees_nothing(submitted_request):
    from .conftest import make_user

    lonely = make_user("sin_dependencia", role="staff")
    assert not services.visible_requests(lonely).exists()


def test_other_student_gets_404_on_detail(client, submitted_request, other_student):
    client.force_login(other_student)
    response = client.get(reverse("requests:detail", args=[submitted_request.pk]))
    assert response.status_code == 404


def test_owner_sees_detail_with_timeline(client, submitted_request):
    client.force_login(submitted_request.student)
    response = client.get(reverse("requests:detail", args=[submitted_request.pk]))
    assert response.status_code == 200
    assert submitted_request.number in response.content.decode()
    assert "Línea de tiempo" in response.content.decode()


def test_wrong_department_cannot_see_or_review(client, submitted_request, staff):
    client.force_login(staff["registro"])
    url = reverse("requests:detail", args=[submitted_request.pk])
    assert client.get(url).status_code == 404
    response = client.post(
        reverse("requests:review", args=[submitted_request.pk]), {"action": "approve"}
    )
    assert response.status_code == 404
    submitted_request.refresh_from_db()
    assert submitted_request.status == Status.SUBMITTED


def test_review_view_approves(client, submitted_request, staff):
    client.force_login(staff["coord"])
    response = client.post(
        reverse("requests:review", args=[submitted_request.pk]),
        {"action": "approve", "comment": "Bien"},
    )
    assert response.status_code == 302
    submitted_request.refresh_from_db()
    assert submitted_request.current_stage.order == 2


def test_students_cannot_open_inbox_or_metrics(client, student):
    client.force_login(student)
    assert client.get(reverse("requests:inbox")).status_code == 403
    assert client.get(reverse("metrics:dashboard")).status_code == 403


def test_staff_cannot_open_metrics(client, staff):
    client.force_login(staff["coord"])
    assert client.get(reverse("metrics:dashboard")).status_code == 403


def test_inbox_lists_only_own_department(client, submitted_request, staff):
    client.force_login(staff["coord"])
    assert submitted_request.number in client.get(reverse("requests:inbox")).content.decode()
    client.force_login(staff["comite"])
    assert submitted_request.number not in client.get(reverse("requests:inbox")).content.decode()


def test_document_download_permissions(client, submitted_request, other_student, staff):
    doc = submitted_request.documents.get()
    url = reverse("requests:document", args=[doc.pk])
    client.force_login(other_student)
    assert client.get(url).status_code == 404
    client.force_login(staff["comite"])
    assert client.get(url).status_code == 404
    client.force_login(staff["coord"])
    assert client.get(url).status_code == 200
    client.force_login(submitted_request.student)
    assert client.get(url).status_code == 200


def test_anonymous_redirected_to_login(client, submitted_request):
    response = client.get(reverse("requests:detail", args=[submitted_request.pk]))
    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]


def test_staff_cannot_create_requests(client, staff, homologation):
    client.force_login(staff["coord"])
    assert client.get(reverse("requests:new", args=["homologacion"])).status_code == 403
