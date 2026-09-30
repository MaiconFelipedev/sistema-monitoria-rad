# Sistema de Apoio à Monitoria

Atividade de ponto extra da disciplina de Rapid Application Development (RAD), desenvolvida com Django.

## Integrante

- Maicon Felipe de Souza

## Funcionalidades

- autenticação nativa do Django com login e logout;
- cadastro público que adiciona a nova conta somente ao grupo `Alunos`;
- abertura de dúvidas em disciplinas ativas;
- três visões da mesma lista, conforme o papel do usuário;
- fluxo protegido de assumir, responder e encerrar uma dúvida;
- base de conhecimento com busca por título ou descrição;
- Admin com filtros, busca e edição dos monitores das disciplinas;
- desafio opcional de horários de atendimento, incluindo validação de sobreposição.

## Contas de teste

Todas usam a senha `Monitoria@2026`.

| Usuário | Papel | Uso principal |
|---|---|---|
| `admin_monitoria` | Superusuário e Professor | Administrar pelo `/admin/` |
| `aluno2` | Aluno | Abrir dúvidas e confirmar resolução |
| `aluno3` | Aluno | Confirmar isolamento entre alunos |
| `monitor4` | Monitor | Atender somente dúvidas de RAD |
| `professor5` | Professor | Visualizar todas as dúvidas |

## Disciplinas

| Código | Disciplina | Estado | Monitores |
|---|---|---|---|
| `RAD101` | Rapid Application Development | Ativa | `monitor4` |
| `BD102` | Banco de Dados | Ativa | Nenhum |
| `ALG000` | Algoritmos | Inativa | Nenhum |

## Como executar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py configurar_monitoria
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/`.

O comando `configurar_monitoria` é idempotente: ele pode ser executado novamente para restaurar grupos, contas e dados demonstrativos.

## Como executar os testes

```powershell
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

São 31 testes automatizados cobrindo os 22 critérios de aceitação e as regras técnicas e opcionais.

## Decisões técnicas

- `Disciplina.monitores` é `ManyToManyField`, pois uma disciplina pode ter vários monitores e um monitor pode atuar em várias disciplinas.
- `Duvida.autor` e `Duvida.monitor_responsavel` possuem `related_name` diferentes para evitar conflito no acesso reverso.
- a lista do monitor usa `disciplina__monitores=usuario`, atravessando o relacionamento em uma única consulta de dúvidas;
- as transições de estado ficam em `monitoria/services.py`, utilizam transação e `select_for_update()`;
- assumir, responder e encerrar aceitam somente `POST`;
- autor, monitor, resposta e situação não aparecem no formulário de abertura;
- autorização utiliza grupos e relacionamentos, nunca `is_superuser`;
- dúvidas respondidas e encerradas podem ser consultadas por qualquer usuário autenticado na base de conhecimento;
- a validação de horário consulta o banco e impede intervalos sobrepostos no mesmo dia.

## Rotas principais

| Rota | Finalidade |
|---|---|
| `/` | Lista de dúvidas de acordo com o papel |
| `/cadastro/` | Cadastro público de aluno |
| `/contas/login/` | Login nativo do Django |
| `/duvidas/nova/` | Abrir dúvida |
| `/duvidas/<id>/` | Detalhar e executar ações permitidas |
| `/base-conhecimento/` | Consultar dúvidas respondidas ou encerradas |
| `/horarios/` | Monitor cadastrar horários de atendimento |
| `/admin/` | Administração |

## Requisitos pendentes

Nenhum requisito obrigatório ficou pendente. O desafio opcional de horários de atendimento também foi implementado.

## Dados entregues

O arquivo `db.sqlite3` está versionado intencionalmente nesta atividade, conforme o enunciado, para que as contas, disciplinas, vínculos e dúvidas de teste possam ser avaliados imediatamente. A pasta `.venv` permanece fora do repositório.
