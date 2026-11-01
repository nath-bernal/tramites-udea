from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import ProcedureField

from .validators import validate_upload


class RequestForm(forms.Form):
    """Formulario dinámico: campos y documentos según la configuración del trámite."""

    def __init__(self, *args, procedure, request_obj=None, **kwargs):
        initial = dict(request_obj.form_data) if request_obj else {}
        super().__init__(*args, initial=initial, **kwargs)
        self.procedure = procedure
        self.request_obj = request_obj
        self.config_fields = list(procedure.fields.all())
        self.config_documents = list(procedure.documents.all())
        self.existing = (
            {d.required_document_id: d for d in request_obj.documents.all()} if request_obj else {}
        )

        for field in self.config_fields:
            self.fields[field.key] = self._build_field(field)
        for doc in self.config_documents:
            formats = ", ".join(ext.upper() for ext in doc.extensions)
            self.fields[f"doc_{doc.pk}"] = forms.FileField(
                label=doc.display_name,
                required=False,
                help_text=_("Formatos: %(formats)s. Máximo 5 MB.") % {"formats": formats},
                widget=forms.ClearableFileInput(
                    attrs={"accept": ",".join(f".{ext}" for ext in doc.extensions)}
                ),
            )

    def _build_field(self, field):
        common = {"label": field.display_label, "required": field.is_required}
        if field.field_type == ProcedureField.FieldType.SELECT:
            return forms.ChoiceField(choices=[("", "—"), *field.parsed_choices()], **common)
        if field.field_type == ProcedureField.FieldType.TEXTAREA:
            return forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), **common)
        return forms.CharField(max_length=300, **common)

    def clean(self):
        cleaned = super().clean()
        for doc in self.config_documents:
            name = f"doc_{doc.pk}"
            uploaded = cleaned.get(name)
            if uploaded:
                try:
                    validate_upload(uploaded, doc.extensions)
                except ValidationError as exc:
                    self.add_error(name, exc)
        return cleaned

    def data_fields(self):
        return [self[field.key] for field in self.config_fields]

    def document_rows(self):
        return [
            {"doc": doc, "field": self[f"doc_{doc.pk}"], "existing": self.existing.get(doc.pk)}
            for doc in self.config_documents
        ]

    def form_data(self):
        return {field.key: self.cleaned_data.get(field.key, "") for field in self.config_fields}

    def uploaded_documents(self):
        return [
            (doc, self.cleaned_data[f"doc_{doc.pk}"])
            for doc in self.config_documents
            if self.cleaned_data.get(f"doc_{doc.pk}")
        ]


class ReviewForm(forms.Form):
    ACTIONS = [
        ("approve", _("Aprobar")),
        ("changes", _("Pedir ajustes")),
        ("reject", _("Rechazar")),
    ]
    action = forms.ChoiceField(choices=ACTIONS, widget=forms.HiddenInput)
    comment = forms.CharField(
        label=_("Comentario"),
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": _("Obligatorio para rechazar o pedir ajustes.")}
        ),
    )
