import base64
import io

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.template import Context, Template
from django.template.defaultfilters import date as date_filter
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from .models import CertificateKind, CertificateTemplate, IssuedCertificate, Language
from .pdf import render_pdf


class CertificateError(Exception):
    pass


LANGUAGE_CHOICES = {"es": ["es"], "en": ["en"], "both": ["es", "en"]}


def verification_url(code):
    return f"{settings.SITE_URL}{reverse('certificates:verify_code', args=[code])}"


def qr_data_uri(text):
    image = qrcode.make(text, box_size=6, border=1)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def _certificate_options(req):
    kind = req.form_data.get("certificate_kind")
    languages = LANGUAGE_CHOICES.get(req.form_data.get("certificate_language"))
    if kind not in CertificateKind.values or not languages:
        raise CertificateError(_("La solicitud no indica un tipo e idioma de certificado válidos."))
    return kind, languages


def build_certificate_html(req, template, code):
    student = req.student
    with translation.override(template.language):
        context = {
            "student_name": student.get_full_name() or student.username,
            "document": student.document_number,
            "program": student.program,
            "number": req.number,
            "issued_date": date_filter(timezone.localdate(), "j \\d\\e F \\d\\e Y")
            if template.language == "es"
            else date_filter(timezone.localdate(), "F j, Y"),
            "code": code,
        }
        body = Template(template.body_html).render(Context(context))
        url = verification_url(code)
        return render_to_string(
            "certificates/pdf.html",
            {
                "title": template.title,
                "body": body,
                "code": code,
                "verify_url": url,
                "qr": qr_data_uri(url),
                "lang": template.language,
                **context,
            },
        )


def issue_certificates(req):
    """Genera un PDF por idioma pedido. Se llama desde el servicio de solicitudes."""
    kind, languages = _certificate_options(req)
    issued = []
    for language in languages:
        template = CertificateTemplate.objects.filter(
            kind=kind, language=language, is_active=True
        ).first()
        if template is None:
            raise CertificateError(
                _("No hay plantilla activa para %(kind)s en %(lang)s.")
                % {"kind": CertificateKind(kind).label, "lang": Language(language).label}
            )
        certificate = IssuedCertificate(request=req, kind=kind, language=language)
        html = build_certificate_html(req, template, certificate.code)
        pdf_bytes = render_pdf(html, base_url=str(settings.BASE_DIR))
        certificate.pdf.save(f"{certificate.code}.pdf", ContentFile(pdf_bytes), save=False)
        certificate.save()
        issued.append(certificate)
    return issued
