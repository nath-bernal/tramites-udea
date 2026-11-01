from django.conf import settings
from django.middleware.locale import LocaleMiddleware
from django.utils import translation


class SpanishByDefaultLocaleMiddleware(LocaleMiddleware):
    """La interfaz es en español; el inglés solo se activa si el usuario lo elige.

    A diferencia de ``LocaleMiddleware``, ignora el idioma del navegador
    (cabecera Accept-Language). Orden: cookie del selector → preferencia guardada
    del usuario → español.
    """

    def process_request(self, request):
        available = {code for code, _ in settings.LANGUAGES}
        language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        if language not in available:
            user = getattr(request, "user", None)
            language = getattr(user, "language", None) if user and user.is_authenticated else None
        if language not in available:
            language = settings.LANGUAGE_CODE
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()
