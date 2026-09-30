from django.contrib import admin

from .models import Disciplina, Duvida, HorarioAtendimento


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "ativa")
    list_filter = ("ativa",)
    search_fields = ("codigo", "nome")
    filter_horizontal = ("monitores",)


@admin.register(Duvida)
class DuvidaAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "disciplina",
        "autor",
        "monitor_responsavel",
        "situacao",
        "atualizada_em",
    )
    list_filter = ("situacao", "disciplina")
    search_fields = (
        "titulo",
        "descricao",
        "resposta",
        "autor__username",
        "monitor_responsavel__username",
    )
    readonly_fields = ("aberta_em", "atualizada_em")


@admin.register(HorarioAtendimento)
class HorarioAtendimentoAdmin(admin.ModelAdmin):
    list_display = (
        "monitor",
        "disciplina",
        "dia_semana",
        "hora_inicio",
        "hora_fim",
    )
    list_filter = ("disciplina", "dia_semana")
    search_fields = ("monitor__username", "disciplina__codigo", "disciplina__nome")


admin.site.site_header = "Sistema de Monitoria - Administração"
admin.site.site_title = "Monitoria"
admin.site.index_title = "Cadastros e atendimentos"
