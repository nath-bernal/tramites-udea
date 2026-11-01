from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import User


class StudentRegistrationForm(UserCreationForm):
    """Registro abierto solo para estudiantes; funcionarios los crea el administrador."""

    first_name = forms.CharField(label=_("Nombres"), max_length=150)
    last_name = forms.CharField(label=_("Apellidos"), max_length=150)
    email = forms.EmailField(label=_("Correo electrónico"))
    document_number = forms.CharField(label=_("Documento de identidad"), max_length=20)
    program = forms.CharField(label=_("Programa académico"), max_length=150)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "first_name", "last_name", "email", "document_number", "program"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        if commit:
            user.save()
        return user
