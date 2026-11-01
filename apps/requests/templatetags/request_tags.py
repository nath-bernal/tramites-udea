from django import template

register = template.Library()

STATUS_CLASSES = {
    "DRAFT": "bg-slate-100 text-slate-700 ring-slate-300",
    "SUBMITTED": "bg-sky-50 text-sky-800 ring-sky-300",
    "IN_REVIEW": "bg-indigo-50 text-indigo-800 ring-indigo-300",
    "NEEDS_CHANGES": "bg-amber-50 text-amber-800 ring-amber-300",
    "APPROVED": "bg-emerald-50 text-emerald-800 ring-emerald-300",
    "REJECTED": "bg-rose-50 text-rose-800 ring-rose-300",
    "FINALIZED": "bg-emerald-50 text-emerald-800 ring-emerald-300",
}

DEADLINE_CLASSES = {
    "overdue": "bg-rose-600 text-white",
    "due_soon": "bg-amber-400 text-amber-950",
    "on_time": "bg-emerald-100 text-emerald-800",
}


@register.filter
def status_classes(status):
    return STATUS_CLASSES.get(str(status), STATUS_CLASSES["DRAFT"])


@register.filter
def deadline_classes(state):
    return DEADLINE_CLASSES.get(state, "")
