from datetime import time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from monitoria.models import Disciplina, Duvida, HorarioAtendimento
from monitoria.roles import GRUPO_ALUNOS, GRUPO_MONITORES, GRUPO_PROFESSORES


SENHA_DEMONSTRACAO = "Monitoria@2026"


class Command(BaseCommand):
    help = "Cria grupos, cinco contas e dados exigidos pela atividade extra."

    def handle(self, *args, **options):
        Usuario = get_user_model()
        grupos = {
            nome: Group.objects.get_or_create(name=nome)[0]
            for nome in (GRUPO_ALUNOS, GRUPO_MONITORES, GRUPO_PROFESSORES)
        }

        usuarios = {}
        definicoes = {
            "admin_monitoria": {
                "grupo": GRUPO_PROFESSORES,
                "is_staff": True,
                "is_superuser": True,
            },
            "aluno2": {"grupo": GRUPO_ALUNOS},
            "aluno3": {"grupo": GRUPO_ALUNOS},
            "monitor4": {"grupo": GRUPO_MONITORES},
            "professor5": {"grupo": GRUPO_PROFESSORES},
        }

        for username, dados in definicoes.items():
            usuario, _ = Usuario.objects.get_or_create(username=username)
            usuario.is_active = True
            usuario.is_staff = dados.get("is_staff", False)
            usuario.is_superuser = dados.get("is_superuser", False)
            usuario.set_password(SENHA_DEMONSTRACAO)
            usuario.save()
            usuario.groups.clear()
            usuario.groups.add(grupos[dados["grupo"]])
            usuario.user_permissions.clear()
            usuarios[username] = usuario

        rad, _ = Disciplina.objects.update_or_create(
            codigo="RAD101",
            defaults={"nome": "Rapid Application Development", "ativa": True},
        )
        banco, _ = Disciplina.objects.update_or_create(
            codigo="BD102",
            defaults={"nome": "Banco de Dados", "ativa": True},
        )
        Disciplina.objects.update_or_create(
            codigo="ALG000",
            defaults={"nome": "Algoritmos - Inativa", "ativa": False},
        )
        rad.monitores.set((usuarios["monitor4"],))
        banco.monitores.clear()

        exemplos = (
            {
                "titulo": "Como organizar as URLs do projeto?",
                "descricao": "Tenho dúvidas sobre include, namespaces e nomes de rotas.",
                "disciplina": rad,
                "autor": usuarios["aluno2"],
                "situacao": Duvida.Situacao.ABERTA,
                "monitor_responsavel": None,
                "resposta": "",
            },
            {
                "titulo": "Quando devo criar um índice no banco?",
                "descricao": "Quero entender o impacto dos índices nas consultas SQL.",
                "disciplina": banco,
                "autor": usuarios["aluno2"],
                "situacao": Duvida.Situacao.ABERTA,
                "monitor_responsavel": None,
                "resposta": "",
            },
            {
                "titulo": "Como funciona o LoginRequiredMixin?",
                "descricao": "Não entendi como uma generic view redireciona usuários anônimos.",
                "disciplina": rad,
                "autor": usuarios["aluno2"],
                "situacao": Duvida.Situacao.EM_ATENDIMENTO,
                "monitor_responsavel": usuarios["monitor4"],
                "resposta": "",
            },
            {
                "titulo": "Por que preciso executar migrations?",
                "descricao": "Qual é a diferença entre makemigrations e migrate?",
                "disciplina": rad,
                "autor": usuarios["aluno2"],
                "situacao": Duvida.Situacao.RESPONDIDA,
                "monitor_responsavel": usuarios["monitor4"],
                "resposta": (
                    "makemigrations cria os arquivos que descrevem as mudanças; "
                    "migrate aplica essas mudanças ao banco de dados."
                ),
            },
            {
                "titulo": "Como validar um ModelForm?",
                "descricao": "Onde devo colocar uma validação que consulta o banco?",
                "disciplina": rad,
                "autor": usuarios["aluno2"],
                "situacao": Duvida.Situacao.ENCERRADA,
                "monitor_responsavel": usuarios["monitor4"],
                "resposta": (
                    "Use os métodos clean do formulário ou do modelo conforme o escopo "
                    "da regra e mantenha a proteção também no servidor."
                ),
            },
            {
                "titulo": "Qual a diferença entre chave primária e estrangeira?",
                "descricao": "Preciso revisar relacionamentos no modelo relacional.",
                "disciplina": banco,
                "autor": usuarios["aluno3"],
                "situacao": Duvida.Situacao.ABERTA,
                "monitor_responsavel": None,
                "resposta": "",
            },
        )

        for dados in exemplos:
            titulo = dados.pop("titulo")
            Duvida.objects.update_or_create(titulo=titulo, defaults=dados)

        HorarioAtendimento.objects.update_or_create(
            monitor=usuarios["monitor4"],
            disciplina=rad,
            dia_semana=HorarioAtendimento.DiaSemana.QUARTA,
            hora_inicio=time(14, 0),
            defaults={"hora_fim": time(16, 0)},
        )
        HorarioAtendimento.objects.update_or_create(
            monitor=usuarios["monitor4"],
            disciplina=rad,
            dia_semana=HorarioAtendimento.DiaSemana.SEXTA,
            hora_inicio=time(10, 0),
            defaults={"hora_fim": time(12, 0)},
        )

        self.stdout.write(self.style.SUCCESS("Ambiente de demonstração configurado."))
        self.stdout.write("Usuários: admin_monitoria, aluno2, aluno3, monitor4, professor5")
        self.stdout.write(f"Senha comum: {SENHA_DEMONSTRACAO}")
