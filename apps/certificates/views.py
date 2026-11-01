from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from .models import IssuedCertificate


def verify(request):
    code = request.GET.get("code", "").strip().upper()
    if code:
        return redirect("certificates:verify_code", code=code)
    return render(request, "certificates/verify.html")


def verify_code(request, code):
    certificate = (
        IssuedCertificate.objects.select_related("request__student", "request__procedure")
        .filter(code=code.strip().upper())
        .first()
    )
    return render(
        request,
        "certificates/verify_result.html",
        {"certificate": certificate, "code": code.upper()},
        status=200 if certificate else 404,
    )


@login_required
def download(request, pk):
    certificate = get_object_or_404(IssuedCertificate.objects.select_related("request"), pk=pk)
    user = request.user
    if not (user.is_admin_role or certificate.request.student_id == user.pk):
        raise Http404
    filename = f"{certificate.request.number}-{certificate.kind}-{certificate.language}.pdf"
    return FileResponse(certificate.pdf.open("rb"), as_attachment=True, filename=filename)
