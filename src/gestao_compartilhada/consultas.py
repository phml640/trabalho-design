"""Consultas paginadas pelos contratos da unidade de trabalho."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar
from uuid import UUID

from gestao_senhas.domain import EstadoSenha

from .operacoes import obter_fila
from .domain import TransicaoSenha
from .notificacoes import MensagemOutbox, NotificacaoSimulada, TentativaNotificacao

if TYPE_CHECKING:
    from .application import UnidadeDeTrabalho

T = TypeVar("T")


@dataclass
class Pagina(Generic[T]):
    itens: list[T]
    limite: int
    offset: int
    tem_mais: bool


def validar_paginacao(limite: int, offset: int) -> None:
    if not 1 <= limite <= 100 or offset < 0:
        raise ValueError("Limite deve estar entre 1 e 100; offset deve ser não negativo.")


def paginar(itens: list[T], limite: int, offset: int) -> Pagina[T]:
    return Pagina(itens[:limite], limite, offset, len(itens) > limite)


class Consultas:
    def __init__(self, uow: UnidadeDeTrabalho) -> None:
        self._uow = uow

    def historico(self, fila_id: UUID, *, limite=20, offset=0, senha_id: UUID | None = None,
                  estado: EstadoSenha | None = None) -> Pagina[TransicaoSenha]:
        validar_paginacao(limite, offset)
        with self._uow.transacao(fila_id) as tx:
            obter_fila(tx, fila_id)
            itens = tx.historico.listar(fila_id, limite + 1, offset, senha_id, estado)
            return paginar(itens, limite, offset)

    def notificacoes(self, *, limite=20, offset=0, fila_id: UUID | None = None,
                     senha_id: UUID | None = None, simuladas=False) -> Pagina[MensagemOutbox] | Pagina[NotificacaoSimulada]:
        validar_paginacao(limite, offset)
        with self._uow.transacao() as tx:
            if fila_id is not None:
                obter_fila(tx, fila_id)
            repo = tx.notificacoes if simuladas else tx.outbox
            return paginar(repo.listar(limite + 1, offset, fila_id, senha_id), limite, offset)

    def tentativas(self, evento_id: UUID, *, limite=20, offset=0) -> Pagina[TentativaNotificacao]:
        validar_paginacao(limite, offset)
        with self._uow.transacao() as tx:
            if tx.outbox.buscar(evento_id) is None:
                raise LookupError("Evento de notificação não encontrado.")
            return paginar(tx.outbox.listar_tentativas(evento_id, limite + 1, offset), limite, offset)
