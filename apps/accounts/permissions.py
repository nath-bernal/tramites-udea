from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*checks):
    """Exige sesión y que el usuario cumpla alguna de las propiedades de rol dadas.

    Ejemplo: ``@role_required("is_official", "is_admin_role")``.
    """

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not any(getattr(request.user, check) for check in checks):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
