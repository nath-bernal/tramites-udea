from django.urls import path

from . import views

app_name = "metrics"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("exportar.csv", views.export_csv, name="export_csv"),
]
