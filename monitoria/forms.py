from django import forms

from .models import Disciplina, Duvida, HorarioAtendimento


class DuvidaForm(forms.ModelForm):
    class Meta:
        model = Duvida
        fields = ("titulo", "descricao", "disciplina")
        widgets = {"descricao": forms.Textarea(attrs={"rows": 7})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["disciplina"].queryset = Disciplina.objects.filter(ativa=True)


class RespostaForm(forms.Form):
    resposta = forms.CharField(
        label="Resposta",
        strip=True,
        widget=forms.Textarea(attrs={"rows": 7}),
        error_messages={"required": "Escreva uma resposta antes de enviar."},
    )


class HorarioAtendimentoForm(forms.ModelForm):
    class Meta:
        model = HorarioAtendimento
        fields = ("disciplina", "dia_semana", "hora_inicio", "hora_fim")
        widgets = {
            "hora_inicio": forms.TimeInput(attrs={"type": "time"}),
            "hora_fim": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.monitor = usuario
        self.fields["disciplina"].queryset = usuario.disciplinas_monitoradas.filter(
            ativa=True
        )
