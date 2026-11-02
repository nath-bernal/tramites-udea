from django.db import migrations


def update_templates(apps, schema_editor):
    from apps.certificates.defaults import TEMPLATES

    CertificateTemplate = apps.get_model("certificates", "CertificateTemplate")
    title, body = TEMPLATES[("grades", "es")]
    CertificateTemplate.objects.filter(kind="grades", language="es").update(body_html=body)


class Migration(migrations.Migration):
    dependencies = [("certificates", "0002_course_record_templates")]

    operations = [migrations.RunPython(update_templates, migrations.RunPython.noop)]
