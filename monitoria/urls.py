from django.urls import path

from . import views

app_name = "monitoria"

urlpatterns = [
    path("", views.ListaDuvidasView.as_view(), name="lista_duvidas"),
    path("cadastro/", views.CadastroView.as_view(), name="cadastro"),
    path("duvidas/nova/", views.AbrirDuvidaView.as_view(), name="abrir_duvida"),
    path(
        "duvidas/<int:pk>/",
        views.DetalheDuvidaView.as_view(),
        name="detalhe_duvida",
    ),
    path("duvidas/<int:pk>/assumir/", views.assumir, name="assumir"),
    path("duvidas/<int:pk>/responder/", views.responder, name="responder"),
    path("duvidas/<int:pk>/encerrar/", views.encerrar, name="encerrar"),
    path(
        "base-conhecimento/",
        views.BaseConhecimentoView.as_view(),
        name="base_conhecimento",
    ),
    path("horarios/", views.horarios, name="horarios"),
]
