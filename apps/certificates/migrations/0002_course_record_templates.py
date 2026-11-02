"""Actualiza las plantillas para listar materias, notas y contenidos.

Las plantillas anteriores de notas y contenidos no mostraban los cursos.
"""

from django.db import migrations


def update_templates(apps, schema_editor):
    from apps.certificates.defaults import TEMPLATES

    CertificateTemplate = apps.get_model("certificates", "CertificateTemplate")
    for (kind, language), (title, body) in TEMPLATES.items():
        CertificateTemplate.objects.update_or_create(
            kind=kind, language=language, defaults={"title": title, "body_html": body}
        )


class Migration(migrations.Migration):
    dependencies = [("certificates", "0001_initial")]

    operations = [migrations.RunPython(update_templates, migrations.RunPython.noop)]
