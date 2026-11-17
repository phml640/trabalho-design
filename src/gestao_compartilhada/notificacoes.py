"""Tipos e casos de uso de notificação; sem dependências de HTTP ou ORM."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Callable, Protocol
from uuid import UUID, uuid4

from gestao_senhas.domain import SenhaChamada

if TYPE_CHECKING:
    from .application import UnidadeDeTrabalho


class Notificador(Protocol):
    def notificar(self, evento: SenhaChamada) -> None:
        """Usa evento.id como chave de idempotência; lança exceção se falhar."""
        ...


@dataclass
class MensagemOutbox:
    evento: SenhaChamada
    tentativas: int = 0
    processado_em: datetime | None = None
    ultimo_erro: str | None = None
    reservado_ate: datetime | None = None


@dataclass
class TentativaNotificacao:
    evento_id: UUID
    numero: int
    iniciada_em: datetime
    finalizada_em: datetime | None = None
    erro: str | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class NotificacaoSimulada:
    evento_id: UUID
    senha_id: UUID
    fila_id: UUID
    mensagem: str
    criada_em: datetime


@dataclass
class ResultadoProcessamento:
    processadas: int = 0
    sucessos: int = 0
    falhas: int = 0


class ProcessadorOutbox:
    """Reserva em transação curta, envia sem transação aberta e registra resultado.

    Uma reserva expira em 30 segundos se o processo morrer. A próxima execução
    retoma o evento usando a mesma chave de idempotência. Não há worker externo.
    """

    def __init__(self, uow: UnidadeDeTrabalho, notificador: Notificador, *,
                 relogio: Callable[[], datetime] | None = None) -> None:
        self._uow = uow
        self._notificador = notificador
        self._agora = relogio or (lambda: datetime.now(timezone.utc))

    def processar(self, limite: int = 20) -> ResultadoProcessamento:
        from .consultas import validar_paginacao

        validar_paginacao(limite, 0)
        with self._uow.transacao() as tx:
            pendentes = tx.outbox.listar_pendentes(self._agora(), limite)
        resultado = ResultadoProcessamento()
        for mensagem in pendentes:
            tentativa = self._reservar(mensagem.evento.id)
            if tentativa is None:
                continue
            erro = None
            try:
                # A chamada já está confirmada e a reserva já foi persistida.
                self._notificador.notificar(mensagem.evento)
            except Exception as exc:
                # Não persistir mensagens de provedores que possam conter contatos.
                erro = f"{type(exc).__name__}: falha no envio"
            self._concluir(tentativa, erro)
            resultado.processadas += 1
            resultado.falhas += int(erro is not None)
            resultado.sucessos += int(erro is None)
        return resultado

    def _reservar(self, evento_id: UUID) -> TentativaNotificacao | None:
        agora = self._agora()
        with self._uow.transacao() as tx:
            mensagem = tx.outbox.buscar(evento_id)
            if mensagem.processado_em is not None:
                return None
            if mensagem.reservado_ate is not None:
                if mensagem.reservado_ate > agora:
                    return None
                anterior = tx.outbox.buscar_tentativa(evento_id, mensagem.tentativas)
                anterior.finalizada_em = agora
                anterior.erro = "reserva_expirada"
                tx.outbox.salvar_tentativa(anterior)
            mensagem.tentativas += 1
            mensagem.reservado_ate = agora + timedelta(seconds=30)
            tentativa = TentativaNotificacao(evento_id, mensagem.tentativas, agora)
            tx.outbox.salvar(mensagem)
            tx.outbox.salvar_tentativa(tentativa)
            return tentativa

    def _concluir(self, tentativa: TentativaNotificacao, erro: str | None) -> None:
        agora = self._agora()
        with self._uow.transacao() as tx:
            mensagem = tx.outbox.buscar(tentativa.evento_id)
            # Um envio lento não pode sobrescrever uma tentativa posterior.
            if mensagem.tentativas != tentativa.numero or mensagem.processado_em is not None:
                return
            tentativa.finalizada_em = agora
            tentativa.erro = erro
            mensagem.ultimo_erro = erro
            mensagem.reservado_ate = None
            if erro is None:
                mensagem.processado_em = agora
            tx.outbox.salvar_tentativa(tentativa)
            tx.outbox.salvar(mensagem)
