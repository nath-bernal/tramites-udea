from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("contador/", views.badge, name="badge"),
    path("<int:pk>/", views.open_notification, name="open"),
    path("marcar-leidas/", views.mark_all_read, name="mark_all_read"),
]
