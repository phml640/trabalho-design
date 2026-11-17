"""Adaptador simulado da porta Notificador, com registro persistente e idempotente."""

from datetime import datetime, timezone

from gestao_senhas.domain import SenhaChamada

from .application import UnidadeDeTrabalho
from .notificacoes import NotificacaoSimulada


class FalhaSimulada(RuntimeError):
    pass


class FakeNotificador:
    def __init__(self, uow: UnidadeDeTrabalho, *, falhar: bool = False):
        self._uow = uow
        self._falhar = falhar

    def notificar(self, evento: SenhaChamada) -> None:
        if self._falhar:
            raise FalhaSimulada("Falha de notificação simulada.")
        with self._uow.transacao() as tx:
            senha = tx.senhas.buscar(evento.senha_id)
            if senha is None:
                raise LookupError("Senha do evento não encontrada.")
            tx.notificacoes.registrar(NotificacaoSimulada(
                evento_id=evento.id, senha_id=evento.senha_id, fila_id=evento.fila_id,
                mensagem=f"Senha {senha.numero} chamada no guichê {senha.guiche_id}.",
                criada_em=datetime.now(timezone.utc),
            ))
