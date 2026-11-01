from django.contrib import admin

from .models import ProcedureField, ProcedureStage, ProcedureType, RequiredDocument


class StageInline(admin.TabularInline):
    model = ProcedureStage
    extra = 0
    ordering = ["order"]


class DocumentInline(admin.TabularInline):
    model = RequiredDocument
    extra = 0


class FieldInline(admin.StackedInline):
    model = ProcedureField
    extra = 0


@admin.register(ProcedureType)
class ProcedureTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "estimated_days", "issues_certificate", "is_active", "order"]
    list_editable = ["is_active", "order"]
    prepopulated_fields = {"code": ["name"]}
    inlines = [StageInline, DocumentInline, FieldInline]
