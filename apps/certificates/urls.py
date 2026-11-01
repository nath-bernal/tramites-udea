from django.urls import path

from . import views

app_name = "certificates"

urlpatterns = [
    path("verificar/", views.verify, name="verify"),
    path("verificar/<str:code>/", views.verify_code, name="verify_code"),
    path("<int:pk>/descargar/", views.download, name="download"),
]
