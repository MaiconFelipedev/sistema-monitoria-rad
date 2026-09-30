from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import Duvida


@transaction.atomic
def assumir_duvida(duvida_id, usuario):
    duvida = (
        Duvida.objects.select_for_update()
        .select_related("disciplina")
        .get(pk=duvida_id)
    )

    if not duvida.disciplina.monitores.filter(pk=usuario.pk).exists():
        raise PermissionDenied("Você não monitora esta disciplina.")
    if duvida.situacao != Duvida.Situacao.ABERTA:
        raise ValidationError("Somente dúvidas abertas podem ser assumidas.")

    duvida.monitor_responsavel = usuario
    duvida.situacao = Duvida.Situacao.EM_ATENDIMENTO
    duvida.save(update_fields=("monitor_responsavel", "situacao", "atualizada_em"))
    return duvida


@transaction.atomic
def responder_duvida(duvida_id, usuario, resposta):
    duvida = Duvida.objects.select_for_update().get(pk=duvida_id)

    if duvida.monitor_responsavel_id != usuario.pk:
        raise PermissionDenied("Apenas o monitor responsável pode responder.")
    if duvida.situacao != Duvida.Situacao.EM_ATENDIMENTO:
        raise ValidationError("Esta dúvida não está aguardando resposta.")

    resposta = resposta.strip()
    if not resposta:
        raise ValidationError("A resposta não pode ficar em branco.")

    duvida.resposta = resposta
    duvida.situacao = Duvida.Situacao.RESPONDIDA
    duvida.save(update_fields=("resposta", "situacao", "atualizada_em"))
    return duvida


@transaction.atomic
def encerrar_duvida(duvida_id, usuario):
    duvida = Duvida.objects.select_for_update().get(pk=duvida_id)

    if duvida.autor_id != usuario.pk:
        raise PermissionDenied("Apenas o autor pode encerrar a dúvida.")
    if duvida.situacao != Duvida.Situacao.RESPONDIDA or not duvida.resposta.strip():
        raise ValidationError("A dúvida precisa ter uma resposta antes de ser encerrada.")

    duvida.situacao = Duvida.Situacao.ENCERRADA
    duvida.save(update_fields=("situacao", "atualizada_em"))
    return duvida
