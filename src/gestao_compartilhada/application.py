"""Porta transacional comum: todas as escritas confirmam ou revertem juntas."""

from contextlib import AbstractContextManager
from datetime import date
from typing import Protocol
from uuid import UUID

from gestao_filas.domain.model import Fila
from gestao_senhas.domain import Senha, SenhaChamada, TipoSenha

from .domain import TransicaoSenha


class RepositorioDeFilas(Protocol):
    def salvar(self, fila: Fila) -> Fila: ...
    def buscar(self, fila_id: UUID) -> Fila | None: ...
    def listar(self) -> list[Fila]: ...


class RepositorioDeSenhas(Protocol):
    def salvar(self, senha: Senha) -> Senha: ...
    def buscar(self, senha_id: UUID) -> Senha | None: ...
    def listar(self, fila_id: UUID) -> list[Senha]: ...
    def proximo_numero(self, fila_id: UUID, dia: date, tipo: TipoSenha) -> str: ...


class Transacao(Protocol):
    filas: RepositorioDeFilas
    senhas: RepositorioDeSenhas

    def registrar_transicao(self, transicao: TransicaoSenha) -> None: ...
    def registrar_evento(self, evento: SenhaChamada) -> None: ...


class UnidadeDeTrabalho(Protocol):
    def transacao(self, fila_id: UUID | None = None) -> AbstractContextManager[Transacao]:
        """Bloqueia a fila até confirmar; qualquer exceção reverte todas as escritas.

        Sem fila_id, protege operações globais, como unicidade do nome da fila.
        Os objetos retornados não podem permitir mutações fora da transação.
        """
        ...
