GRUPO_ALUNOS = "Alunos"
GRUPO_MONITORES = "Monitores"
GRUPO_PROFESSORES = "Professores"


def pertence_ao_grupo(usuario, nome_grupo):
    return usuario.is_authenticated and usuario.groups.filter(name=nome_grupo).exists()


def papel_do_usuario(usuario):
    if pertence_ao_grupo(usuario, GRUPO_PROFESSORES):
        return "Professor"
    if pertence_ao_grupo(usuario, GRUPO_MONITORES):
        return "Monitor"
    return "Aluno"
