"""Crea datos de demostración. Todos los datos son ficticios."""

import os
from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone

from apps.accounts.models import Department, User
from apps.catalog.models import ProcedureField, ProcedureStage, ProcedureType, RequiredDocument
from apps.certificates.defaults import TEMPLATES
from apps.certificates.models import CertificateTemplate
from apps.requests import services
from apps.requests.models import Request, RequestEvent

PASSWORD = "demo1234"

DEPARTMENTS = {
    "coord": ("Coordinación de programa", "Program Coordination"),
    "comite": ("Comité de carrera", "Curriculum Committee"),
    "registro": ("Admisiones y Registro", "Admissions and Registrar's Office"),
}

PROCEDURES = [
    {
        "code": "homologacion",
        "name": "Homologación de cursos",
        "name_en": "Course credit transfer",
        "description": "Reconocimiento de cursos aprobados en otro programa o institución como "
        "equivalentes a cursos de tu plan de estudios.",
        "description_en": "Recognition of courses passed in another program or institution as "
        "equivalent to courses in your study plan.",
        "requirements": "Estar matriculado en el semestre actual.\n"
        "Haber aprobado los cursos de origen con nota mínima de 3.5.\n"
        "Adjuntar los contenidos oficiales de cada curso.",
        "requirements_en": "Be enrolled in the current term.\n"
        "Have passed the original courses with a minimum grade of 3.5.\n"
        "Attach the official syllabus of each course.",
        "estimated_days": 18,
        "stages": [("coord", 5), ("comite", 10), ("registro", 3)],
        "documents": [
            (
                "Certificado de notas de la institución de origen",
                "Transcript from the original institution",
                True,
                "pdf",
            ),
            ("Contenidos de los cursos", "Course syllabi", True, "pdf"),
        ],
        "fields": [
            (
                "origin_institution",
                "Institución de origen",
                "Original institution",
                "text",
                "",
                True,
            ),
            (
                "courses",
                "Cursos a homologar y su equivalente",
                "Courses to transfer and their equivalent",
                "textarea",
                "",
                True,
            ),
        ],
    },
    {
        "code": "cancelacion",
        "name": "Cancelación de curso o semestre",
        "name_en": "Course or term withdrawal",
        "description": "Retiro de uno o varios cursos, o del semestre completo, después de las "
        "fechas de ajuste de matrícula.",
        "description_en": "Withdrawal from one or more courses, or the whole term, after the "
        "enrollment adjustment period.",
        "requirements": "Explicar el motivo de la cancelación.\n"
        "Adjuntar soporte si el motivo es de salud, laboral o de fuerza mayor.",
        "requirements_en": "Explain the reason for the withdrawal.\n"
        "Attach supporting documents for health, work or force majeure reasons.",
        "estimated_days": 5,
        "stages": [("coord", 3), ("registro", 2)],
        "documents": [
            ("Soporte del motivo", "Supporting document", False, "pdf,jpg,png"),
        ],
        "fields": [
            (
                "scope",
                "¿Qué deseas cancelar?",
                "What do you want to withdraw from?",
                "select",
                "course|Uno o varios cursos|One or more courses\n"
                "semester|Semestre completo|Whole term",
                True,
            ),
            ("courses", "Cursos (si aplica)", "Courses (if applicable)", "text", "", False),
            ("reason", "Justificación", "Justification", "textarea", "", True),
        ],
    },
    {
        "code": "certificado",
        "name": "Certificado académico",
        "name_en": "Academic certificate",
        "description": "Certificado de estudios, de notas o de contenidos, en español, en inglés "
        "o en ambos idiomas, con código de verificación.",
        "description_en": "Enrollment, grades or course content certificate, in Spanish, "
        "English or both, with a verification code.",
        "requirements": "Estar a paz y salvo con la universidad.",
        "requirements_en": "Have no outstanding debts with the university.",
        "estimated_days": 2,
        "issues_certificate": True,
        "stages": [("registro", 2)],
        "documents": [],
        "fields": [
            (
                "certificate_kind",
                "Tipo de certificado",
                "Certificate type",
                "select",
                "studies|Certificado de estudios|Enrollment certificate\n"
                "grades|Certificado de notas|Grades certificate\n"
                "contents|Certificado de contenidos|Course content certificate",
                True,
            ),
            (
                "certificate_language",
                "Idioma",
                "Language",
                "select",
                "es|Español|Spanish\nen|Inglés|English\nboth|Español e inglés|Spanish and English",
                True,
            ),
            ("purpose", "¿Para qué lo necesitas?", "What do you need it for?", "text", "", False),
        ],
    },
    {
        "code": "reingreso",
        "name": "Reingreso",
        "name_en": "Readmission",
        "description": "Solicitud para retomar el programa después de haber interrumpido los "
        "estudios uno o más semestres.",
        "description_en": "Request to resume the program after interrupting studies for one or "
        "more terms.",
        "requirements": "No haber perdido el derecho a continuar en el programa por bajo "
        "rendimiento.\nPresentar la solicitud en las fechas del calendario académico.",
        "requirements_en": "Not having lost the right to continue in the program due to low "
        "performance.\nSubmit the request within the academic calendar dates.",
        "estimated_days": 18,
        "stages": [("coord", 5), ("comite", 10), ("registro", 3)],
        "documents": [
            ("Carta de motivos", "Statement of reasons", True, "pdf"),
            ("Historia académica", "Academic record", True, "pdf"),
        ],
        "fields": [
            (
                "last_term",
                "Último semestre cursado (p. ej., 2025-1)",
                "Last term attended (e.g., 2025-1)",
                "text",
                "",
                True,
            ),
            ("reason", "Motivo del reingreso", "Reason for readmission", "textarea", "", True),
        ],
    },
]

FAKE_PDF = b"%PDF-1.4\n% Documento ficticio de demostracion - Tramite Claro\n%%EOF\n"


class Command(BaseCommand):
    help = "Crea dependencias, trámites, etapas, plantillas, usuarios y solicitudes de demo."

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def handle(self, *args, **options):
        with transaction.atomic():
            departments = self._departments()
            users = self._users(departments)
            self._procedures(departments)
            self._templates()
            if Request.objects.exists():
                self.stdout.write("Ya hay solicitudes; no se crean solicitudes de demo.")
            else:
                self._demo_requests(users)
        self.stdout.write(self.style.SUCCESS(f"Datos de demo listos. Contraseña: {PASSWORD}"))

    def _departments(self):
        result = {}
        for key, (name, name_en) in DEPARTMENTS.items():
            result[key], _ = Department.objects.update_or_create(
                name=name, defaults={"name_en": name_en}
            )
        return result

    def _users(self, departments):
        specs = [
            (
                "estudiante1",
                "Valentina",
                "Ríos Demo",
                User.Role.STUDENT,
                None,
                "1000000001",
                "Ingeniería de Sistemas",
            ),
            (
                "estudiante2",
                "Santiago",
                "Mejía Demo",
                User.Role.STUDENT,
                None,
                "1000000002",
                "Ingeniería Industrial",
            ),
            (
                "estudiante3",
                "Camila",
                "Ochoa Demo",
                User.Role.STUDENT,
                None,
                "1000000003",
                "Bioingeniería",
            ),
            (
                "funcionario_coordinacion",
                "Andrés",
                "Coordinador Demo",
                User.Role.STAFF,
                departments["coord"],
                "",
                "",
            ),
            (
                "funcionario_comite",
                "Marta",
                "Comité Demo",
                User.Role.STAFF,
                departments["comite"],
                "",
                "",
            ),
            (
                "funcionario_registro",
                "Jorge",
                "Registro Demo",
                User.Role.STAFF,
                departments["registro"],
                "",
                "",
            ),
            ("admin", "Ana", "Administradora Demo", User.Role.ADMIN, None, "", ""),
        ]
        users = {}
        for username, first, last, role, department, document, program in specs:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": f"{username}@demo.local",
                    "role": role,
                    "department": department,
                    "document_number": document,
                    "program": program,
                    "is_staff": role == User.Role.ADMIN,
                    "is_superuser": role == User.Role.ADMIN,
                },
            )
            if created:
                user.set_password(PASSWORD)
                user.save()
            if role == User.Role.ADMIN and os.environ.get("DEMO_ADMIN_PASSWORD"):
                # En un despliegue público el administrador no usa la contraseña de demo.
                user.set_password(os.environ["DEMO_ADMIN_PASSWORD"])
                user.save()
            users[username] = user
        return users

    def _procedures(self, departments):
        for order, spec in enumerate(PROCEDURES):
            procedure, created = ProcedureType.objects.get_or_create(
                code=spec["code"],
                defaults={
                    "name": spec["name"],
                    "name_en": spec["name_en"],
                    "description": spec["description"],
                    "description_en": spec["description_en"],
                    "requirements": spec["requirements"],
                    "requirements_en": spec["requirements_en"],
                    "estimated_days": spec["estimated_days"],
                    "issues_certificate": spec.get("issues_certificate", False),
                    "order": order,
                },
            )
            if not created:
                continue  # respeta los cambios hechos desde /admin
            for stage_order, (dept, days) in enumerate(spec["stages"], start=1):
                ProcedureStage.objects.create(
                    procedure=procedure,
                    order=stage_order,
                    department=departments[dept],
                    deadline_days=days,
                )
            for doc_order, (name, name_en, required, formats) in enumerate(spec["documents"]):
                RequiredDocument.objects.create(
                    procedure=procedure,
                    name=name,
                    name_en=name_en,
                    is_required=required,
                    allowed_formats=formats,
                    order=doc_order,
                )
            for field_order, (key, label, label_en, ftype, choices, required) in enumerate(
                spec["fields"]
            ):
                ProcedureField.objects.create(
                    procedure=procedure,
                    key=key,
                    label=label,
                    label_en=label_en,
                    field_type=ftype,
                    choices=choices,
                    is_required=required,
                    order=field_order,
                )

    def _templates(self):
        for (kind, language), (title, body) in TEMPLATES.items():
            CertificateTemplate.objects.get_or_create(
                kind=kind, language=language, defaults={"title": title, "body_html": body}
            )

    # --- Solicitudes de ejemplo con fechas en el pasado para alimentar los indicadores ---

    def _backdate(self, req, since, days_ago):
        """Mueve al pasado los eventos y fechas que se crearon desde ``since``."""
        moment = timezone.now() - timedelta(days=days_ago)
        RequestEvent.objects.filter(request=req, created_at__gte=since).update(created_at=moment)
        req.refresh_from_db()
        updates = {
            field: moment
            for field in ("submitted_at", "stage_entered_at", "resolved_at")
            if getattr(req, field) and getattr(req, field) >= since
        }
        if "submitted_at" in updates:
            updates["created_at"] = moment
        if updates:
            Request.objects.filter(pk=req.pk).update(**updates)
        req.refresh_from_db()

    def _new(self, student, code, form_data):
        procedure = ProcedureType.objects.get(code=code)
        req = services.create_request(student, procedure)
        services.update_form_data(req, student, form_data)
        for doc in procedure.documents.all():
            services.attach_document(
                req, student, doc, ContentFile(FAKE_PDF, name="documento-ficticio.pdf")
            )
        return req

    def _run(self, req, steps):
        for action, actor, comment, days_ago in steps:
            since = timezone.now()
            if action == "submit":
                services.submit(req, actor)
            elif action == "resubmit":
                services.resubmit(req, actor, comment)
            else:
                getattr(services, action)(req, actor, comment)
            self._backdate(req, since, days_ago)

    def _demo_requests(self, users):
        s1, s2, s3 = users["estudiante1"], users["estudiante2"], users["estudiante3"]
        coord = users["funcionario_coordinacion"]
        comite = users["funcionario_comite"]
        registro = users["funcionario_registro"]

        # 1. Homologación aprobada y finalizada.
        req = self._new(
            s1,
            "homologacion",
            {
                "origin_institution": "Institución Universitaria Ficticia",
                "courses": "Cálculo I → Cálculo Diferencial\nProgramación I → Lógica y Algoritmos",
            },
        )
        self._run(
            req,
            [
                ("submit", s1, "", 30),
                ("approve", coord, "Contenidos equivalentes.", 27),
                ("approve", comite, "Aprobada en sesión del comité.", 16),
                ("approve", registro, "Homologación registrada en la historia académica.", 14),
            ],
        )

        # 2. Cancelación rechazada.
        req = self._new(
            s2,
            "cancelacion",
            {
                "scope": "semester",
                "courses": "",
                "reason": "Motivos personales.",
            },
        )
        self._run(
            req,
            [
                ("submit", s2, "", 20),
                ("reject", coord, "La solicitud está fuera del calendario académico.", 17),
            ],
        )

        # 3. Reingreso en el Comité, con plazo vencido.
        req = self._new(
            s3,
            "reingreso",
            {
                "last_term": "2025-1",
                "reason": "Retomo estudios tras un año de trabajo.",
            },
        )
        self._run(
            req,
            [
                ("submit", s3, "", 28),
                ("approve", coord, "Cumple requisitos.", 25),
            ],
        )

        # 4. Cancelación de estudiante1 a la que le pidieron ajustes.
        req = self._new(
            s1,
            "cancelacion",
            {
                "scope": "course",
                "courses": "Física II",
                "reason": "Incapacidad médica.",
            },
        )
        self._run(
            req,
            [
                ("submit", s1, "", 4),
                ("request_changes", coord, "Adjunta la incapacidad médica como soporte.", 3),
            ],
        )

        # 5. Homologación recién radicada (en la bandeja de Coordinación).
        req = self._new(
            s2,
            "homologacion",
            {
                "origin_institution": "Politécnico Ficticio",
                "courses": "Estadística → Probabilidad y Estadística",
            },
        )
        self._run(req, [("submit", s2, "", 4)])

        # 6. Certificado en Admisiones y Registro, listo para aprobar en vivo.
        req = self._new(
            s1,
            "certificado",
            {
                "certificate_kind": "studies",
                "certificate_language": "both",
                "purpose": "Intercambio académico",
            },
        )
        self._run(req, [("submit", s1, "", 1)])

        # 7. Borrador de reingreso sin enviar.
        self._new(s1, "reingreso", {"last_term": "2024-2", "reason": ""})
