from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.i18n import set_language as django_set_language

from .forms import StudentRegistrationForm


@login_required
def home(request):
    """Lleva a cada rol a su pantalla principal."""
    user = request.user
    if user.is_admin_role:
        return redirect("metrics:dashboard")
    if user.is_official:
        return redirect("requests:inbox")
    return redirect("requests:my_requests")


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = StudentRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, _("Cuenta creada. ¡Bienvenido a Trámite Claro!"))
        return redirect("home")
    return render(request, "accounts/register.html", {"form": form})


@require_POST
def set_language(request):
    """Cambia el idioma de la interfaz y lo guarda como preferencia del usuario."""
    response = django_set_language(request)
    lang = request.POST.get("language")
    if request.user.is_authenticated and lang in ("es", "en"):
        request.user.language = lang
        request.user.save(update_fields=["language"])
    next_url = request.POST.get("next", "/")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = "/"
    response["Location"] = next_url
    return response
