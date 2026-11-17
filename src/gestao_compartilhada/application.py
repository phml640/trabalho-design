"""Porta transacional comum: todas as escritas confirmam ou revertem juntas."""

from contextlib import AbstractContextManager
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from gestao_filas.domain.model import Fila
from gestao_senhas.domain import EstadoSenha, Senha, SenhaChamada, TipoSenha

from .domain import TransicaoSenha
from .notificacoes import MensagemOutbox, NotificacaoSimulada, TentativaNotificacao


class RepositorioDeFilas(Protocol):
    def salvar(self, fila: Fila) -> Fila: ...
    def buscar(self, fila_id: UUID) -> Fila | None: ...
    def listar(self) -> list[Fila]: ...


class RepositorioDeSenhas(Protocol):
    def salvar(self, senha: Senha) -> Senha: ...
    def buscar(self, senha_id: UUID) -> Senha | None: ...
    def listar(self, fila_id: UUID) -> list[Senha]: ...
    def proximo_numero(self, fila_id: UUID, dia: date, tipo: TipoSenha) -> str: ...


class RepositorioDeHistorico(Protocol):
    def listar(self, fila_id: UUID, limite: int, offset: int, senha_id: UUID | None = None,
               estado: EstadoSenha | None = None) -> list[TransicaoSenha]: ...


class RepositorioDeOutbox(Protocol):
    def buscar(self, evento_id: UUID) -> MensagemOutbox | None: ...
    def salvar(self, mensagem: MensagemOutbox) -> None: ...
    def listar(self, limite: int, offset: int, fila_id: UUID | None = None,
               senha_id: UUID | None = None) -> list[MensagemOutbox]: ...
    def listar_pendentes(self, quando: datetime, limite: int) -> list[MensagemOutbox]: ...
    def salvar_tentativa(self, tentativa: TentativaNotificacao) -> None: ...
    def buscar_tentativa(self, evento_id: UUID, numero: int) -> TentativaNotificacao | None: ...
    def listar_tentativas(self, evento_id: UUID, limite: int, offset: int) -> list[TentativaNotificacao]: ...


class RepositorioDeNotificacoes(Protocol):
    def registrar(self, notificacao: NotificacaoSimulada) -> None: ...
    def listar(self, limite: int, offset: int, fila_id: UUID | None = None,
               senha_id: UUID | None = None) -> list[NotificacaoSimulada]: ...


class Transacao(Protocol):
    filas: RepositorioDeFilas
    senhas: RepositorioDeSenhas
    historico: RepositorioDeHistorico
    outbox: RepositorioDeOutbox
    notificacoes: RepositorioDeNotificacoes

    def registrar_transicao(self, transicao: TransicaoSenha) -> None: ...
    def registrar_evento(self, evento: SenhaChamada) -> None: ...


class UnidadeDeTrabalho(Protocol):
    def transacao(self, fila_id: UUID | None = None) -> AbstractContextManager[Transacao]:
        """Bloqueia a fila até confirmar; qualquer exceção reverte todas as escritas.

        Sem fila_id, protege operações globais, como unicidade do nome da fila.
        Os objetos retornados não podem permitir mutações fora da transação.
        """
        ...
