from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView

from .forms import DuvidaForm, HorarioAtendimentoForm, RespostaForm
from .models import Duvida, HorarioAtendimento
from .roles import GRUPO_ALUNOS, GRUPO_MONITORES, papel_do_usuario, pertence_ao_grupo
from .selectors import duvidas_acessiveis_para, duvidas_visiveis_para
from .services import assumir_duvida, encerrar_duvida, responder_duvida


class CadastroView(CreateView):
    form_class = UserCreationForm
    template_name = "registration/cadastro.html"
    success_url = reverse_lazy("monitoria:lista_duvidas")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("monitoria:lista_duvidas")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        resposta = super().form_valid(form)
        grupo_alunos, _ = Group.objects.get_or_create(name=GRUPO_ALUNOS)
        self.object.groups.add(grupo_alunos)
        login(self.request, self.object)
        messages.success(self.request, "Conta criada. Você entrou como aluno.")
        return resposta


class ListaDuvidasView(LoginRequiredMixin, ListView):
    template_name = "monitoria/lista_duvidas.html"
    context_object_name = "duvidas"

    def get_queryset(self):
        return duvidas_visiveis_para(self.request.user)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["papel"] = papel_do_usuario(self.request.user)
        return contexto


class AbrirDuvidaView(LoginRequiredMixin, CreateView):
    form_class = DuvidaForm
    template_name = "monitoria/form_duvida.html"

    def form_valid(self, form):
        form.instance.autor = self.request.user
        form.instance.situacao = Duvida.Situacao.ABERTA
        messages.success(self.request, "Dúvida registrada com sucesso.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("monitoria:detalhe_duvida", args=(self.object.pk,))

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["horarios"] = HorarioAtendimento.objects.select_related(
            "disciplina", "monitor"
        ).filter(disciplina__ativa=True)
        return contexto


class DetalheDuvidaView(LoginRequiredMixin, DetailView):
    template_name = "monitoria/detalhe_duvida.html"
    context_object_name = "duvida"

    def get_queryset(self):
        return duvidas_acessiveis_para(self.request.user)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        duvida = self.object
        usuario = self.request.user
        contexto["form_resposta"] = RespostaForm()
        contexto["pode_assumir"] = (
            duvida.situacao == Duvida.Situacao.ABERTA
            and duvida.disciplina.monitores.filter(pk=usuario.pk).exists()
        )
        contexto["pode_responder"] = (
            duvida.situacao == Duvida.Situacao.EM_ATENDIMENTO
            and duvida.monitor_responsavel_id == usuario.pk
        )
        contexto["pode_encerrar"] = (
            duvida.situacao == Duvida.Situacao.RESPONDIDA
            and duvida.autor_id == usuario.pk
            and bool(duvida.resposta.strip())
        )
        return contexto


@login_required
@require_POST
def assumir(request, pk):
    try:
        assumir_duvida(pk, request.user)
    except Duvida.DoesNotExist as erro:
        raise Http404 from erro
    except ValidationError as erro:
        messages.error(request, erro.messages[0])
    else:
        messages.success(request, "Você assumiu o atendimento.")
    return redirect("monitoria:detalhe_duvida", pk=pk)


@login_required
@require_POST
def responder(request, pk):
    duvida = get_object_or_404(Duvida, pk=pk)
    if duvida.monitor_responsavel_id != request.user.pk:
        raise PermissionDenied("Apenas o monitor responsável pode responder.")

    form = RespostaForm(request.POST)
    if form.is_valid():
        try:
            responder_duvida(pk, request.user, form.cleaned_data["resposta"])
        except Duvida.DoesNotExist as erro:
            raise Http404 from erro
        except ValidationError as erro:
            messages.error(request, erro.messages[0])
        else:
            messages.success(request, "Resposta registrada.")
    else:
        messages.error(request, "Escreva uma resposta antes de enviar.")
    return redirect("monitoria:detalhe_duvida", pk=pk)


@login_required
@require_POST
def encerrar(request, pk):
    try:
        encerrar_duvida(pk, request.user)
    except Duvida.DoesNotExist as erro:
        raise Http404 from erro
    except ValidationError as erro:
        messages.error(request, erro.messages[0])
    else:
        messages.success(request, "Dúvida encerrada. Obrigado pela confirmação.")
    return redirect("monitoria:detalhe_duvida", pk=pk)


class BaseConhecimentoView(LoginRequiredMixin, ListView):
    template_name = "monitoria/base_conhecimento.html"
    context_object_name = "duvidas"

    def get_queryset(self):
        consulta = Duvida.objects.select_related("disciplina", "autor").filter(
            situacao__in=(Duvida.Situacao.RESPONDIDA, Duvida.Situacao.ENCERRADA)
        )
        termo = self.request.GET.get("q", "").strip()
        if termo:
            consulta = consulta.filter(
                Q(titulo__icontains=termo) | Q(descricao__icontains=termo)
            )
        return consulta

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["termo"] = self.request.GET.get("q", "").strip()
        return contexto


@login_required
def horarios(request):
    if not pertence_ao_grupo(request.user, GRUPO_MONITORES):
        raise PermissionDenied("Somente monitores podem cadastrar horários.")

    form = HorarioAtendimentoForm(request.POST or None, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Horário cadastrado.")
        return redirect("monitoria:horarios")

    return render(
        request,
        "monitoria/horarios.html",
        {
            "form": form,
            "horarios": request.user.horarios_monitoria.select_related("disciplina"),
        },
    )
