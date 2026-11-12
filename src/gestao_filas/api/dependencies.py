"""Composição dos gerenciadores com a mesma unidade de trabalho por aplicação."""

from fastapi import Request

from gestao_filas.application import GestaoDeFilas
from gestao_senhas.application import GerenciadorDeSenhas


def obter_gestao_de_filas(request: Request) -> GestaoDeFilas:
    return GestaoDeFilas(request.app.state.unidade_de_trabalho)


def obter_gerenciador_de_senhas(request: Request) -> GerenciadorDeSenhas:
    return GerenciadorDeSenhas(request.app.state.unidade_de_trabalho)
