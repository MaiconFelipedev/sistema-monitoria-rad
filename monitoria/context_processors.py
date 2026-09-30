from .roles import GRUPO_MONITORES, papel_do_usuario, pertence_ao_grupo


def papeis(request):
    if not request.user.is_authenticated:
        return {"papel_usuario": "", "eh_monitor": False}
    return {
        "papel_usuario": papel_do_usuario(request.user),
        "eh_monitor": pertence_ao_grupo(request.user, GRUPO_MONITORES),
    }
