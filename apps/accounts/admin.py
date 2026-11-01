from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Department, User


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "name_en"]
    search_fields = ["name", "name_en"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "get_full_name", "role", "department", "program", "is_active"]
    list_filter = ["role", "department", "is_active"]
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            _("Trámite Claro"),
            {"fields": ("role", "document_number", "program", "department", "language")},
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_("Trámite Claro"), {"fields": ("role", "department", "email")}),
    )
