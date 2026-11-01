from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    notifications = request.user.notifications.select_related("request")[:100]
    return render(request, "notifications/list.html", {"notifications": notifications})


@login_required
def badge(request):
    """Fragmento HTMX con el contador de no leídas (se refresca periódicamente)."""
    count = request.user.notifications.filter(is_read=False).count()
    return render(request, "notifications/_badge.html", {"unread_notifications": count})


@login_required
def open_notification(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    if notification.request_id:
        return redirect("requests:detail", pk=notification.request_id)
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications:list")
