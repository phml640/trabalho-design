"""Adaptador transacional em memória, limitado a um processo."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from threading import RLock
from typing import Iterator
from uuid import UUID

from gestao_filas.domain.model import Fila
from gestao_filas.infrastructure.repositories import RepositorioDeFilasEmMemoria
from gestao_senhas.domain import Senha, SenhaChamada, TipoSenha
from gestao_senhas.infrastructure import RepositorioDeSenhasEmMemoria

from .domain import TransicaoSenha
from .notificacoes import MensagemOutbox, NotificacaoSimulada, TentativaNotificacao
from .registros_em_memoria import HistoricoEmMemoria, NotificacoesEmMemoria, OutboxEmMemoria


@dataclass
class _Estado:
    filas: dict[UUID, Fila] = field(default_factory=dict)
    senhas: dict[UUID, Senha] = field(default_factory=dict)
    contadores: dict[tuple[UUID, date, TipoSenha], int] = field(default_factory=dict)
    historico: list[TransicaoSenha] = field(default_factory=list)
    eventos: list[SenhaChamada] = field(default_factory=list)
    outbox: dict[UUID, MensagemOutbox] = field(default_factory=dict)
    tentativas: dict[tuple[UUID, int], TentativaNotificacao] = field(default_factory=dict)
    notificacoes: dict[UUID, NotificacaoSimulada] = field(default_factory=dict)


class TransacaoEmMemoria:
    def __init__(self, estado: _Estado) -> None:
        self.filas = RepositorioDeFilasEmMemoria(estado.filas)
        self.senhas = RepositorioDeSenhasEmMemoria(estado.senhas, estado.contadores)
        self.historico = HistoricoEmMemoria(estado)
        self.outbox = OutboxEmMemoria(estado)
        self.notificacoes = NotificacoesEmMemoria(estado)
        self._estado = estado

    def registrar_transicao(self, transicao: TransicaoSenha) -> None:
        self._estado.historico.append(transicao)

    def registrar_evento(self, evento: SenhaChamada) -> None:
        self._estado.eventos.append(evento)
        self.outbox.salvar(MensagemOutbox(evento))


class UnidadeDeTrabalhoEmMemoria:
    """Serializa operações e publica uma cópia do estado só ao confirmar.

    O bloqueio global é deliberadamente simples neste adaptador de teste.
    O adaptador PostgreSQL usa bloqueio da linha da fila (ADR-003).
    """

    def __init__(self) -> None:
        self._estado = _Estado()
        self._lock = RLock()

    @contextmanager
    def transacao(self, fila_id: UUID | None = None) -> Iterator[TransacaoEmMemoria]:
        with self._lock:
            estado = deepcopy(self._estado)
            yield TransacaoEmMemoria(estado)
            # Exceções no corpo descartam o snapshot, incluindo contadores e registros.
            # A segunda cópia impede alterações através de referências já retornadas.
            self._estado = deepcopy(estado)

    @property
    def historico(self) -> tuple[TransicaoSenha, ...]:
        with self._lock:
            return tuple(self._estado.historico)

    @property
    def eventos(self) -> tuple[SenhaChamada, ...]:
        with self._lock:
            return tuple(self._estado.eventos)
