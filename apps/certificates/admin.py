from django.contrib import admin

from .models import CertificateTemplate, IssuedCertificate


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ["kind", "language", "title", "is_active"]
    list_filter = ["kind", "language", "is_active"]


@admin.register(IssuedCertificate)
class IssuedCertificateAdmin(admin.ModelAdmin):
    list_display = ["code", "request", "kind", "language", "issued_at"]
    search_fields = ["code", "request__number"]
    readonly_fields = ["code", "request", "kind", "language", "pdf", "issued_at"]
