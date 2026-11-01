import pytest
from django.core import mail
from django.urls import reverse

from apps.notifications.models import Notification
from apps.requests import services

pytestmark = pytest.mark.django_db


def test_submit_notifies_student_and_department(submitted_request, staff):
    assert Notification.objects.filter(user=submitted_request.student).count() == 1
    assert Notification.objects.filter(user=staff["coord"]).count() == 1
    assert not Notification.objects.filter(user=staff["comite"]).exists()
    recipients = {m.to[0] for m in mail.outbox}
    assert recipients == {submitted_request.student.email, staff["coord"].email}


def test_stage_change_notifies_next_department(submitted_request, staff):
    services.approve(submitted_request, staff["coord"])
    assert Notification.objects.filter(user=staff["comite"]).count() == 1


def test_needs_changes_message_includes_comment(submitted_request, staff):
    services.request_changes(submitted_request, staff["coord"], "Falta firma")
    note = Notification.objects.filter(user=submitted_request.student).first()
    assert "Falta firma" in note.message


def test_notification_in_user_language(submitted_request, staff):
    student = submitted_request.student
    student.language = "en"
    student.save()
    services.request_changes(submitted_request, staff["coord"], "x")
    assert "requires changes" in Notification.objects.filter(user=student).first().message


def test_open_marks_read_and_redirects(client, submitted_request):
    student = submitted_request.student
    note = student.notifications.get()
    client.force_login(student)
    response = client.get(reverse("notifications:open", args=[note.pk]))
    assert response["Location"] == reverse("requests:detail", args=[submitted_request.pk])
    note.refresh_from_db()
    assert note.is_read


def test_cannot_open_others_notifications(client, submitted_request, other_student):
    note = submitted_request.student.notifications.get()
    client.force_login(other_student)
    assert client.get(reverse("notifications:open", args=[note.pk])).status_code == 404


def test_check_deadlines_command(submitted_request, staff):
    from datetime import timedelta

    from django.core.management import call_command
    from django.utils import timezone

    submitted_request.stage_entered_at = timezone.now() - timedelta(days=30)
    submitted_request.save()
    call_command("check_deadlines")
    assert Notification.objects.filter(user=staff["coord"], message__contains="superó").exists()
