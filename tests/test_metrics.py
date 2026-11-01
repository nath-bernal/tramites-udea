from datetime import date, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.metrics import services as metrics
from apps.requests import services
from apps.requests.deadlines import add_business_days, business_days_between

pytestmark = pytest.mark.django_db


def test_add_business_days_skips_weekends():
    friday = date(2026, 10, 30)
    assert add_business_days(friday, 1) == date(2026, 11, 2)
    assert add_business_days(friday, 5) == date(2026, 11, 6)
    assert business_days_between(friday, date(2026, 11, 2)) == 1


def test_deadline_state(submitted_request):
    assert submitted_request.deadline_state == "on_time"
    submitted_request.stage_entered_at = timezone.now() - timedelta(days=20)
    assert submitted_request.deadline_state == "overdue"


def test_stage_times_from_events(submitted_request, staff):
    event = submitted_request.events.get()
    event.created_at = timezone.now() - timedelta(days=4)
    event.save()
    services.approve(submitted_request, staff["coord"])
    rows = metrics.stage_times()
    assert len(rows) == 1
    assert rows[0]["stage"].department.name == "Coordinación de programa"
    assert rows[0]["avg_days"] == pytest.approx(4.0, abs=0.1)


def test_procedure_times_and_counts(submitted_request, staff):
    services.reject(submitted_request, staff["coord"], "No")
    rows = {r["procedure"].code: r for r in metrics.procedure_times()}
    assert rows["homologacion"]["resolved"] == 1
    counts = {r["status"]: r["count"] for r in metrics.status_counts()}
    assert counts["FINALIZED"] == 1


def test_dashboard_and_csv(client, submitted_request, admin_user):
    client.force_login(admin_user)
    assert client.get(reverse("metrics:dashboard")).status_code == 200
    response = client.get(reverse("metrics:export_csv"))
    assert response["Content-Type"].startswith("text/csv")
    content = response.content.decode("utf-8-sig")
    assert "Homologación" in content
    assert "Radicada" in content
