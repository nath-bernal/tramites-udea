from django.core.management.base import BaseCommand

from apps.metrics.services import deadline_summary
from apps.notifications.services import notify_overdue


class Command(BaseCommand):
    help = "Notifica a las dependencias las solicitudes que superaron el plazo de su etapa."

    def handle(self, *args, **options):
        overdue = deadline_summary()["overdue"]
        for req in overdue:
            notify_overdue(req)
            self.stdout.write(f"Vencida: {req.number} ({req.current_stage.department})")
        self.stdout.write(self.style.SUCCESS(f"{len(overdue)} solicitudes vencidas notificadas."))
