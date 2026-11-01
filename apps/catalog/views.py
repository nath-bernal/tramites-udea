from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import ProcedureType


def _search(query):
    procedures = ProcedureType.objects.filter(is_active=True)
    if query:
        procedures = procedures.filter(
            Q(name__icontains=query)
            | Q(name_en__icontains=query)
            | Q(description__icontains=query)
            | Q(description_en__icontains=query)
        )
    return procedures.prefetch_related("stages__department")


def procedure_list(request):
    query = request.GET.get("q", "").strip()
    context = {"procedures": _search(query), "query": query}
    if request.headers.get("HX-Request") and request.headers.get("HX-Target") == "results":
        return render(request, "catalog/_results.html", context)
    return render(request, "catalog/list.html", context)


def procedure_detail(request, code):
    procedure = get_object_or_404(ProcedureType, code=code, is_active=True)
    return render(
        request,
        "catalog/detail.html",
        {
            "procedure": procedure,
            "stages": procedure.ordered_stages(),
            "documents": procedure.documents.all(),
        },
    )
