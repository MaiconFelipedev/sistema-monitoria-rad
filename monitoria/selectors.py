from django.db.models import Q

from .models import Duvida
from .roles import GRUPO_MONITORES, GRUPO_PROFESSORES, pertence_ao_grupo


def duvidas_visiveis_para(usuario):
    consulta = Duvida.objects.select_related(
        "disciplina",
        "autor",
        "monitor_responsavel",
    )

    if pertence_ao_grupo(usuario, GRUPO_PROFESSORES):
        return consulta

    if pertence_ao_grupo(usuario, GRUPO_MONITORES):
        return consulta.filter(disciplina__monitores=usuario).distinct()

    return consulta.filter(autor=usuario)


def duvidas_acessiveis_para(usuario):
    publicadas_na_base = Q(
        situacao__in=(Duvida.Situacao.RESPONDIDA, Duvida.Situacao.ENCERRADA)
    )
    visiveis_por_papel = Q(pk__in=duvidas_visiveis_para(usuario).values("pk"))
    return Duvida.objects.select_related(
        "disciplina",
        "autor",
        "monitor_responsavel",
    ).filter(publicadas_na_base | visiveis_por_papel).distinct()
