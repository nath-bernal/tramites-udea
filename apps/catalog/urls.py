from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.procedure_list, name="list"),
    path("<slug:code>/", views.procedure_detail, name="detail"),
]
