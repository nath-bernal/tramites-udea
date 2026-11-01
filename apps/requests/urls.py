from django.urls import path

from . import views

app_name = "requests"

urlpatterns = [
    path("", views.my_requests, name="my_requests"),
    path("bandeja/", views.inbox, name="inbox"),
    path("nueva/<slug:code>/", views.new_request, name="new"),
    path("<int:pk>/", views.request_detail, name="detail"),
    path("<int:pk>/editar/", views.edit_request, name="edit"),
    path("<int:pk>/eliminar/", views.delete_request, name="delete"),
    path("<int:pk>/revisar/", views.review, name="review"),
    path("documentos/<int:pk>/", views.download_document, name="document"),
]
