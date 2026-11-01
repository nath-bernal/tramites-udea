from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext as _

# Firma de los primeros bytes de cada formato soportado.
MAGIC_BYTES = {
    "pdf": [b"%PDF"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
}


def validate_upload(uploaded_file, allowed_extensions):
    """Valida extensión, tamaño y contenido real del archivo subido."""
    ext = Path(uploaded_file.name).suffix.lower().lstrip(".")
    allowed = set(allowed_extensions)
    if "jpg" in allowed:
        allowed.add("jpeg")
    if ext not in allowed or ext not in MAGIC_BYTES:
        raise ValidationError(
            _("Formato no permitido. Formatos aceptados: %(formats)s.")
            % {"formats": ", ".join(sorted(allowed_extensions)).upper()}
        )
    if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(
            _("El archivo pesa %(size)s; el máximo es %(max)s.")
            % {
                "size": filesizeformat(uploaded_file.size),
                "max": filesizeformat(settings.MAX_UPLOAD_SIZE),
            }
        )
    uploaded_file.seek(0)
    head = uploaded_file.read(16)
    uploaded_file.seek(0)
    if not any(head.startswith(sig) for sig in MAGIC_BYTES[ext]):
        raise ValidationError(_("El contenido del archivo no corresponde a su extensión."))
