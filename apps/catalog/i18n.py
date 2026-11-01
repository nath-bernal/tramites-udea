from django.utils.translation import get_language


def pick(es_value, en_value):
    """Devuelve el valor en inglés si la interfaz está en inglés y existe; si no, el español."""
    if (get_language() or "es").startswith("en") and en_value:
        return en_value
    return es_value
