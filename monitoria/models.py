from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class Disciplina(models.Model):
    nome = models.CharField(max_length=120)
    codigo = models.CharField(max_length=20, unique=True)
    ativa = models.BooleanField(default=True)
    monitores = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="disciplinas_monitoradas",
    )

    class Meta:
        ordering = ("codigo",)

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class Duvida(models.Model):
    class Situacao(models.TextChoices):
        ABERTA = "ABERTA", "Aberta"
        EM_ATENDIMENTO = "EM_ATENDIMENTO", "Em atendimento"
        RESPONDIDA = "RESPONDIDA", "Respondida"
        ENCERRADA = "ENCERRADA", "Encerrada"

    titulo = models.CharField(max_length=160)
    descricao = models.TextField()
    disciplina = models.ForeignKey(
        Disciplina,
        on_delete=models.PROTECT,
        related_name="duvidas",
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="duvidas_abertas",
    )
    monitor_responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="duvidas_assumidas",
    )
    resposta = models.TextField(blank=True)
    situacao = models.CharField(
        max_length=20,
        choices=Situacao.choices,
        default=Situacao.ABERTA,
    )
    aberta_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-atualizada_em", "-pk")
        verbose_name_plural = "Dúvidas"

    def __str__(self):
        return self.titulo


class HorarioAtendimento(models.Model):
    class DiaSemana(models.IntegerChoices):
        SEGUNDA = 1, "Segunda-feira"
        TERCA = 2, "Terça-feira"
        QUARTA = 3, "Quarta-feira"
        QUINTA = 4, "Quinta-feira"
        SEXTA = 5, "Sexta-feira"
        SABADO = 6, "Sábado"

    monitor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="horarios_monitoria",
    )
    disciplina = models.ForeignKey(
        Disciplina,
        on_delete=models.CASCADE,
        related_name="horarios_atendimento",
    )
    dia_semana = models.PositiveSmallIntegerField(choices=DiaSemana.choices)
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()

    class Meta:
        ordering = ("disciplina__codigo", "dia_semana", "hora_inicio")
        constraints = [
            models.CheckConstraint(
                condition=Q(hora_inicio__lt=F("hora_fim")),
                name="horario_inicio_antes_fim",
            )
        ]
        verbose_name = "Horário de atendimento"
        verbose_name_plural = "Horários de atendimento"

    def clean(self):
        super().clean()
        erros = {}

        if self.hora_inicio and self.hora_fim:
            if self.hora_inicio >= self.hora_fim:
                erros["hora_fim"] = "A hora final deve ser posterior à inicial."

        if self.monitor_id and self.disciplina_id:
            if not self.disciplina.monitores.filter(pk=self.monitor_id).exists():
                erros["disciplina"] = "O usuário não monitora esta disciplina."

        if (
            self.monitor_id
            and self.dia_semana
            and self.hora_inicio
            and self.hora_fim
        ):
            conflitantes = HorarioAtendimento.objects.filter(
                monitor_id=self.monitor_id,
                dia_semana=self.dia_semana,
                hora_inicio__lt=self.hora_fim,
                hora_fim__gt=self.hora_inicio,
            ).exclude(pk=self.pk)
            if conflitantes.exists():
                erros["hora_inicio"] = (
                    "Este horário se sobrepõe a outro atendimento do monitor."
                )

        if erros:
            raise ValidationError(erros)

    def __str__(self):
        return (
            f"{self.monitor} - {self.disciplina.codigo} - "
            f"{self.get_dia_semana_display()} {self.hora_inicio:%H:%M}"
        )
