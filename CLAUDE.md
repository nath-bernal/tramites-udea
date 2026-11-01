# Trámite Claro — guía para agentes

Lee README.md: es la especificación (alcance, modelo de datos, convenciones y fases).

Reglas clave:
- Código en inglés; interfaz, comentarios de negocio, docs y commits en español.
- Todo cambio de estado de una solicitud pasa por `apps/requests/services.py`, nunca por las vistas ni por el admin.
- Todo texto visible usa `gettext` / `{% translate %}`. Después de agregar textos: `python manage.py makemessages -l en`, traducir en `locale/en/LC_MESSAGES/django.po` y `compilemessages`.
- Permisos: estudiante solo lo suyo; funcionario solo su dependencia en la etapa actual (`services.visible_requests`). Pruébalos siempre.
- Solo datos ficticios. Nada de logos ni marcas oficiales de la universidad.
- Antes de terminar: `pytest` y `ruff check . && ruff format .`.
