from datetime import time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .forms import DuvidaForm, HorarioAtendimentoForm
from .models import Disciplina, Duvida, HorarioAtendimento
from .roles import GRUPO_ALUNOS, GRUPO_MONITORES, GRUPO_PROFESSORES
from .selectors import duvidas_visiveis_para


class BaseMonitoriaTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.grupo_alunos = Group.objects.create(name=GRUPO_ALUNOS)
        cls.grupo_monitores = Group.objects.create(name=GRUPO_MONITORES)
        cls.grupo_professores = Group.objects.create(name=GRUPO_PROFESSORES)

        cls.aluno2 = Usuario.objects.create_user("aluno2", password="Teste@2026")
        cls.aluno3 = Usuario.objects.create_user("aluno3", password="Teste@2026")
        cls.monitor4 = Usuario.objects.create_user("monitor4", password="Teste@2026")
        cls.monitor_extra = Usuario.objects.create_user(
            "monitor_extra", password="Teste@2026"
        )
        cls.professor5 = Usuario.objects.create_user(
            "professor5", password="Teste@2026"
        )

        cls.aluno2.groups.add(cls.grupo_alunos)
        cls.aluno3.groups.add(cls.grupo_alunos)
        cls.monitor4.groups.add(cls.grupo_monitores)
        cls.monitor_extra.groups.add(cls.grupo_monitores)
        cls.professor5.groups.add(cls.grupo_professores)

        cls.rad = Disciplina.objects.create(
            nome="Rapid Application Development", codigo="RAD101"
        )
        cls.banco = Disciplina.objects.create(nome="Banco de Dados", codigo="BD102")
        cls.inativa = Disciplina.objects.create(
            nome="Algoritmos", codigo="ALG000", ativa=False
        )
        cls.rad.monitores.add(cls.monitor4, cls.monitor_extra)

        cls.duvida_rad_aberta = Duvida.objects.create(
            titulo="Dúvida aberta de RAD",
            descricao="Como organizar as URLs e seus namespaces?",
            disciplina=cls.rad,
            autor=cls.aluno2,
        )
        cls.duvida_banco_aberta = Duvida.objects.create(
            titulo="Dúvida aberta de Banco",
            descricao="Como criar um índice para uma consulta?",
            disciplina=cls.banco,
            autor=cls.aluno2,
        )
        cls.duvida_aluno3 = Duvida.objects.create(
            titulo="Dúvida exclusiva do aluno três",
            descricao="Como funciona uma chave estrangeira?",
            disciplina=cls.banco,
            autor=cls.aluno3,
        )
        cls.duvida_em_atendimento = Duvida.objects.create(
            titulo="Dúvida já assumida",
            descricao="Como usar o LoginRequiredMixin?",
            disciplina=cls.rad,
            autor=cls.aluno2,
            monitor_responsavel=cls.monitor4,
            situacao=Duvida.Situacao.EM_ATENDIMENTO,
        )
        cls.duvida_respondida = Duvida.objects.create(
            titulo="Migrations no Django",
            descricao="Qual a diferença entre makemigrations e migrate?",
            disciplina=cls.rad,
            autor=cls.aluno2,
            monitor_responsavel=cls.monitor4,
            situacao=Duvida.Situacao.RESPONDIDA,
            resposta="Um comando cria a migração e o outro aplica no banco.",
        )


class AutenticacaoCadastroTests(BaseMonitoriaTestCase):
    def test_01_anonimo_e_redirecionado_para_login_com_next(self):
        resposta = self.client.get(reverse("monitoria:lista_duvidas"))
        self.assertRedirects(resposta, "/contas/login/?next=/")

    def test_02_cadastro_com_senha_fraca_e_recusado(self):
        resposta = self.client.post(
            reverse("monitoria:cadastro"),
            {"username": "novo", "password1": "123", "password2": "123"},
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username="novo").exists())

    def test_03_nova_conta_entra_apenas_no_grupo_alunos(self):
        resposta = self.client.post(
            reverse("monitoria:cadastro"),
            {
                "username": "novo_aluno",
                "password1": "Senha-Monitoria@2026",
                "password2": "Senha-Monitoria@2026",
            },
        )
        self.assertRedirects(resposta, reverse("monitoria:lista_duvidas"))
        usuario = get_user_model().objects.get(username="novo_aluno")
        self.assertEqual(list(usuario.groups.values_list("name", flat=True)), [GRUPO_ALUNOS])
        self.assertFalse(usuario.user_permissions.exists())

    def test_logout_so_aceita_post(self):
        self.client.force_login(self.aluno2)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(
            self.client.post(reverse("logout")), reverse("login")
        )


class AberturaEListagemTests(BaseMonitoriaTestCase):
    def test_04_aluno_abre_duvida_com_autor_automatico(self):
        self.client.force_login(self.aluno2)
        resposta = self.client.post(
            reverse("monitoria:abrir_duvida"),
            {
                "titulo": "Como configurar uma generic view?",
                "descricao": "Quero compreender os atributos necessários.",
                "disciplina": self.rad.pk,
            },
        )
        duvida = Duvida.objects.get(titulo="Como configurar uma generic view?")
        self.assertRedirects(
            resposta, reverse("monitoria:detalhe_duvida", args=(duvida.pk,))
        )
        self.assertEqual(duvida.autor, self.aluno2)
        self.assertEqual(duvida.situacao, Duvida.Situacao.ABERTA)

    def test_05_formulario_nao_expoe_campos_controlados_pelo_sistema(self):
        self.assertEqual(set(DuvidaForm().fields), {"titulo", "descricao", "disciplina"})

    def test_06_aluno_tres_nao_ve_duvida_do_aluno_dois(self):
        self.client.force_login(self.aluno3)
        resposta = self.client.get(reverse("monitoria:lista_duvidas"))
        self.assertNotContains(resposta, self.duvida_rad_aberta.titulo)
        self.assertContains(resposta, self.duvida_aluno3.titulo)

    def test_07_monitor_ve_apenas_duvidas_da_disciplina_monitorada(self):
        self.client.force_login(self.monitor4)
        resposta = self.client.get(reverse("monitoria:lista_duvidas"))
        self.assertContains(resposta, self.duvida_rad_aberta.titulo)
        self.assertContains(resposta, self.duvida_em_atendimento.titulo)

    def test_08_monitor_nao_ve_duvidas_de_outra_disciplina(self):
        self.client.force_login(self.monitor4)
        resposta = self.client.get(reverse("monitoria:lista_duvidas"))
        self.assertNotContains(resposta, self.duvida_banco_aberta.titulo)

    def test_09_professor_ve_todas_as_duvidas_sem_ser_superusuario(self):
        self.client.force_login(self.professor5)
        resposta = self.client.get(reverse("monitoria:lista_duvidas"))
        self.assertContains(resposta, self.duvida_rad_aberta.titulo)
        self.assertContains(resposta, self.duvida_banco_aberta.titulo)
        self.assertContains(resposta, self.duvida_aluno3.titulo)
        self.assertFalse(self.professor5.is_superuser)

    def test_consulta_do_monitor_atravessa_relacionamento(self):
        sql = str(duvidas_visiveis_para(self.monitor4).query)
        self.assertIn("monitoria_disciplina_monitores", sql)

    def test_22_disciplina_inativa_nao_pode_ser_escolhida(self):
        self.client.force_login(self.aluno2)
        resposta = self.client.post(
            reverse("monitoria:abrir_duvida"),
            {
                "titulo": "Tentativa em disciplina inativa",
                "descricao": "Esta dúvida não deve ser criada.",
                "disciplina": self.inativa.pk,
            },
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(
            Duvida.objects.filter(titulo="Tentativa em disciplina inativa").exists()
        )


class FluxoAtendimentoTests(BaseMonitoriaTestCase):
    def test_10_monitor_assume_duvida_da_sua_disciplina(self):
        self.client.force_login(self.monitor4)
        resposta = self.client.post(
            reverse("monitoria:assumir", args=(self.duvida_rad_aberta.pk,))
        )
        self.assertRedirects(
            resposta,
            reverse("monitoria:detalhe_duvida", args=(self.duvida_rad_aberta.pk,)),
        )
        self.duvida_rad_aberta.refresh_from_db()
        self.assertEqual(self.duvida_rad_aberta.monitor_responsavel, self.monitor4)
        self.assertEqual(
            self.duvida_rad_aberta.situacao, Duvida.Situacao.EM_ATENDIMENTO
        )

    def test_11_duvida_ja_assumida_nao_pode_ser_assumida_novamente(self):
        self.client.force_login(self.monitor_extra)
        self.client.post(
            reverse("monitoria:assumir", args=(self.duvida_em_atendimento.pk,))
        )
        self.duvida_em_atendimento.refresh_from_db()
        self.assertEqual(self.duvida_em_atendimento.monitor_responsavel, self.monitor4)

    def test_12_monitor_nao_assume_duvida_de_outra_disciplina(self):
        self.client.force_login(self.monitor4)
        resposta = self.client.post(
            reverse("monitoria:assumir", args=(self.duvida_banco_aberta.pk,))
        )
        self.assertEqual(resposta.status_code, 403)

    def test_13_aluno_nao_responde_a_propria_duvida_pela_url(self):
        self.client.force_login(self.aluno2)
        resposta = self.client.post(
            reverse("monitoria:responder", args=(self.duvida_em_atendimento.pk,)),
            {"resposta": "Tentativa indevida do aluno."},
        )
        self.assertEqual(resposta.status_code, 403)

    def test_14_monitor_responsavel_responde(self):
        self.client.force_login(self.monitor4)
        self.client.post(
            reverse("monitoria:responder", args=(self.duvida_em_atendimento.pk,)),
            {"resposta": "O mixin verifica o usuário antes da view."},
        )
        self.duvida_em_atendimento.refresh_from_db()
        self.assertEqual(self.duvida_em_atendimento.situacao, Duvida.Situacao.RESPONDIDA)
        self.assertIn("mixin", self.duvida_em_atendimento.resposta)

    def test_15_resposta_em_branco_e_recusada_com_mensagem(self):
        self.client.force_login(self.monitor4)
        resposta = self.client.post(
            reverse("monitoria:responder", args=(self.duvida_em_atendimento.pk,)),
            {"resposta": "   "},
            follow=True,
        )
        self.assertContains(resposta, "Escreva uma resposta antes de enviar")
        self.duvida_em_atendimento.refresh_from_db()
        self.assertEqual(
            self.duvida_em_atendimento.situacao, Duvida.Situacao.EM_ATENDIMENTO
        )

    def test_16_autor_encerra_duvida_respondida(self):
        self.client.force_login(self.aluno2)
        self.client.post(
            reverse("monitoria:encerrar", args=(self.duvida_respondida.pk,))
        )
        self.duvida_respondida.refresh_from_db()
        self.assertEqual(self.duvida_respondida.situacao, Duvida.Situacao.ENCERRADA)

    def test_17_duvida_sem_resposta_nao_pode_ser_encerrada(self):
        self.client.force_login(self.aluno2)
        self.client.post(
            reverse("monitoria:encerrar", args=(self.duvida_rad_aberta.pk,))
        )
        self.duvida_rad_aberta.refresh_from_db()
        self.assertEqual(self.duvida_rad_aberta.situacao, Duvida.Situacao.ABERTA)

    def test_18_outro_aluno_nao_encerra_duvida_do_autor(self):
        self.client.force_login(self.aluno3)
        resposta = self.client.post(
            reverse("monitoria:encerrar", args=(self.duvida_respondida.pk,))
        )
        self.assertEqual(resposta.status_code, 403)

    def test_acoes_de_estado_nao_aceitam_get(self):
        self.client.force_login(self.monitor4)
        for nome in ("assumir", "responder", "encerrar"):
            resposta = self.client.get(
                reverse(f"monitoria:{nome}", args=(self.duvida_rad_aberta.pk,))
            )
            self.assertEqual(resposta.status_code, 405)

    def test_interface_exibe_assumir_somente_quando_permitido(self):
        self.client.force_login(self.monitor4)
        resposta = self.client.get(
            reverse("monitoria:detalhe_duvida", args=(self.duvida_rad_aberta.pk,))
        )
        self.assertContains(resposta, "Assumir atendimento")

        resposta = self.client.get(
            reverse("monitoria:detalhe_duvida", args=(self.duvida_em_atendimento.pk,))
        )
        self.assertNotContains(resposta, "Assumir atendimento")
        self.assertContains(resposta, "Enviar resposta")


class BaseConhecimentoTests(BaseMonitoriaTestCase):
    def test_19_qualquer_usuario_autenticado_ve_respostas_de_todos(self):
        self.client.force_login(self.aluno3)
        resposta = self.client.get(reverse("monitoria:base_conhecimento"))
        self.assertContains(resposta, self.duvida_respondida.titulo)
        self.assertContains(resposta, self.duvida_respondida.resposta)

    def test_20_base_nao_exibe_abertas_nem_em_atendimento(self):
        self.client.force_login(self.aluno3)
        resposta = self.client.get(reverse("monitoria:base_conhecimento"))
        self.assertNotContains(resposta, self.duvida_rad_aberta.titulo)
        self.assertNotContains(resposta, self.duvida_em_atendimento.titulo)

    def test_21_busca_filtra_titulo_ou_descricao(self):
        self.client.force_login(self.aluno3)
        por_titulo = self.client.get(
            reverse("monitoria:base_conhecimento"), {"q": "Migrations"}
        )
        por_descricao = self.client.get(
            reverse("monitoria:base_conhecimento"), {"q": "makemigrations"}
        )
        self.assertContains(por_titulo, self.duvida_respondida.titulo)
        self.assertContains(por_descricao, self.duvida_respondida.titulo)


class HorariosOpcionaisTests(BaseMonitoriaTestCase):
    def test_apenas_monitor_acessa_cadastro_de_horarios(self):
        self.client.force_login(self.aluno2)
        self.assertEqual(self.client.get(reverse("monitoria:horarios")).status_code, 403)

    def test_formulario_lista_apenas_disciplinas_monitoradas(self):
        form = HorarioAtendimentoForm(usuario=self.monitor4)
        self.assertEqual(list(form.fields["disciplina"].queryset), [self.rad])

    def test_monitor_cadastra_horario_valido(self):
        self.client.force_login(self.monitor4)
        resposta = self.client.post(
            reverse("monitoria:horarios"),
            {
                "disciplina": self.rad.pk,
                "dia_semana": HorarioAtendimento.DiaSemana.QUARTA,
                "hora_inicio": "14:00",
                "hora_fim": "16:00",
            },
        )
        self.assertRedirects(resposta, reverse("monitoria:horarios"))
        self.assertTrue(
            HorarioAtendimento.objects.filter(monitor=self.monitor4).exists()
        )

    def test_horarios_sobrepostos_sao_recusados(self):
        HorarioAtendimento.objects.create(
            monitor=self.monitor4,
            disciplina=self.rad,
            dia_semana=HorarioAtendimento.DiaSemana.QUARTA,
            hora_inicio=time(14, 0),
            hora_fim=time(16, 0),
        )
        conflito = HorarioAtendimento(
            monitor=self.monitor4,
            disciplina=self.rad,
            dia_semana=HorarioAtendimento.DiaSemana.QUARTA,
            hora_inicio=time(15, 0),
            hora_fim=time(17, 0),
        )
        with self.assertRaises(ValidationError):
            conflito.full_clean()

    def test_horarios_aparecem_na_abertura_da_duvida(self):
        HorarioAtendimento.objects.create(
            monitor=self.monitor4,
            disciplina=self.rad,
            dia_semana=HorarioAtendimento.DiaSemana.SEXTA,
            hora_inicio=time(10, 0),
            hora_fim=time(12, 0),
        )
        self.client.force_login(self.aluno2)
        resposta = self.client.get(reverse("monitoria:abrir_duvida"))
        self.assertContains(resposta, "Sexta-feira")
        self.assertContains(resposta, "monitor4")
