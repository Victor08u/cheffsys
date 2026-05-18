from django.http import HttpResponseForbidden


def rol_requerido(nombre_rol):

    def decorator(view_func):

        def wrapper(request, *args, **kwargs):

            if request.user.groups.filter(name=nombre_rol).exists():
                return view_func(request, *args, **kwargs)

            return HttpResponseForbidden("No tienes permisos")

        return wrapper

    return decorator