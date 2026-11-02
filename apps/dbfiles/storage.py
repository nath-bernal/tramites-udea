from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

from .models import StoredFile


@deconstructible
class DatabaseStorage(Storage):
    """Almacenamiento de archivos en la tabla ``StoredFile``.

    Los archivos nunca tienen URL pública: se descargan a través de vistas que
    validan permisos.
    """

    def _open(self, name, mode="rb"):
        try:
            stored = StoredFile.objects.get(name=name)
        except StoredFile.DoesNotExist as exc:
            raise FileNotFoundError(name) from exc
        return ContentFile(bytes(stored.content), name=name)

    def _save(self, name, content):
        if hasattr(content, "seek"):
            content.seek(0)
        data = content.read()
        StoredFile.objects.create(name=name, content=data, size=len(data))
        return name

    def exists(self, name):
        return StoredFile.objects.filter(name=name).exists()

    def delete(self, name):
        StoredFile.objects.filter(name=name).delete()

    def size(self, name):
        return StoredFile.objects.values_list("size", flat=True).get(name=name)

    def url(self, name):
        raise NotImplementedError("Los archivos se descargan solo a través de vistas con permisos.")
