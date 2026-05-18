def roles_usuario(request):

    es_admin = False
    es_cocina = False

    if request.user.is_authenticated:

        es_admin = request.user.groups.filter(
            name='Administrador'
        ).exists()

        es_cocina = request.user.groups.filter(
            name='Cocina'
        ).exists()

    return {
        'es_admin': es_admin,
        'es_cocina': es_cocina,
    }