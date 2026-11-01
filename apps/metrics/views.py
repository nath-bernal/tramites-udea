import csv

from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.permissions import role_required

from . import services


@role_required("is_admin_role")
def dashboard(request):
    stage_rows = services.stage_times()
    context = {
        "status_counts": services.status_counts(),
        "procedure_rows": services.procedure_times(),
        "stage_rows": stage_rows,
        # Cuello de botella: etapas cuyo promedio supera su plazo.
        "bottlenecks": [r for r in stage_rows if r["avg_days"] > r["deadline_days"]],
        "deadlines": services.deadline_summary(),
    }
    context["max_status"] = max((r["count"] for r in context["status_counts"]), default=0) or 1
    return render(request, "metrics/dashboard.html", context)


@role_required("is_admin_role")
def export_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    stamp = timezone.localdate().isoformat()
    response["Content-Disposition"] = f'attachment; filename="indicadores-{stamp}.csv"'
    response.write("﻿")  # BOM para que Excel lea bien las tildes
    writer = csv.writer(response)
    writer.writerow(
        [_("Sección"), _("Elemento"), _("Cantidad"), _("Promedio (días)"), _("Referencia (días)")]
    )
    for row in services.status_counts():
        writer.writerow([_("Estado"), row["status"].label, row["count"], "", ""])
    for row in services.procedure_times():
        writer.writerow(
            [
                _("Trámite"),
                row["procedure"].display_name,
                row["resolved"],
                row["avg_days"] if row["avg_days"] is not None else "",
                row["estimated_days"],
            ]
        )
    for row in services.stage_times():
        stage = row["stage"]
        writer.writerow(
            [
                _("Etapa"),
                f"{stage.procedure.display_name} · {stage.department.display_name}",
                row["count"],
                row["avg_days"],
                row["deadline_days"],
            ]
        )
    return response
