"""Indicadores calculados a partir del historial (RequestEvent)."""

from collections import Counter, defaultdict
from statistics import mean

from apps.catalog.models import ProcedureType
from apps.requests.models import ACTIVE_STATUSES, Request, RequestEvent, Status


def _days(delta):
    return delta.total_seconds() / 86400


def status_counts():
    counts = Counter(Request.objects.exclude(status=Status.DRAFT).values_list("status", flat=True))
    return [{"status": s, "count": counts.get(s.value, 0)} for s in Status if s != Status.DRAFT]


def procedure_times():
    """Tiempo promedio total (radicación → resolución) por tipo de trámite."""
    rows = []
    for procedure in ProcedureType.objects.all():
        resolved = Request.objects.filter(
            procedure=procedure, resolved_at__isnull=False, submitted_at__isnull=False
        )
        durations = [_days(r.resolved_at - r.submitted_at) for r in resolved]
        active = Request.objects.filter(procedure=procedure, status__in=ACTIVE_STATUSES).count()
        rows.append(
            {
                "procedure": procedure,
                "resolved": len(durations),
                "active": active,
                "avg_days": round(mean(durations), 1) if durations else None,
                "estimated_days": procedure.estimated_days,
            }
        )
    return rows


def stage_times():
    """Tiempo promedio que una solicitud pasa en cada etapa (solo tramos cerrados).

    Un tramo empieza en un evento que deja la solicitud activa (radicada o en revisión) en una
    etapa y termina en el evento siguiente. El tiempo en «requiere ajustes» no cuenta, porque
    depende del estudiante.
    """
    durations = defaultdict(list)
    events = RequestEvent.objects.select_related("stage__department", "stage__procedure").order_by(
        "request_id", "created_at", "id"
    )
    previous = None
    for event in events:
        if (
            previous is not None
            and previous.request_id == event.request_id
            and previous.to_status in ACTIVE_STATUSES
            and previous.stage is not None
        ):
            durations[previous.stage].append(_days(event.created_at - previous.created_at))
        previous = event
    rows = [
        {
            "stage": stage,
            "count": len(values),
            "avg_days": round(mean(values), 1),
            "deadline_days": stage.deadline_days,
        }
        for stage, values in durations.items()
    ]
    rows.sort(key=lambda r: r["avg_days"], reverse=True)
    return rows


def deadline_summary():
    active = Request.objects.filter(status__in=ACTIVE_STATUSES).select_related(
        "current_stage__department", "procedure", "student"
    )
    overdue, due_soon = [], []
    for req in active:
        if req.deadline_state == "overdue":
            overdue.append(req)
        elif req.deadline_state == "due_soon":
            due_soon.append(req)
    return {"overdue": overdue, "due_soon": due_soon}
