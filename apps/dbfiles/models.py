from django.db import models


class StoredFile(models.Model):
    """Contenido de un archivo subido o generado, guardado en la base de datos.

    Se usa en el despliegue gratuito de Render, cuyo disco se borra en cada reinicio.
    """

    name = models.CharField(max_length=255, unique=True)
    content = models.BinaryField()
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
