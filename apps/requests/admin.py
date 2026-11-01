from django.contrib import admin

from .models import Request, RequestDocument, RequestEvent


class DocumentInline(admin.TabularInline):
    model = RequestDocument
    extra = 0
    readonly_fields = ["required_document", "original_name", "uploaded_at"]
    exclude = ["file"]


class EventInline(admin.TabularInline):
    model = RequestEvent
    extra = 0
    readonly_fields = ["from_status", "to_status", "stage", "actor", "comment", "created_at"]
    can_delete = False


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    """Solo lectura: los cambios de estado pasan por apps/requests/services.py."""

    list_display = ["number", "student", "procedure", "status", "current_stage", "submitted_at"]
    list_filter = ["status", "procedure"]
    search_fields = ["number", "student__username", "student__last_name"]
    readonly_fields = [
        "number",
        "student",
        "procedure",
        "status",
        "outcome",
        "current_stage",
        "form_data",
        "submitted_at",
        "stage_entered_at",
        "resolved_at",
    ]
    inlines = [DocumentInline, EventInline]

    def has_add_permission(self, request):
        return False
