"""Entidades, eventos e política de seleção de senhas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from gestao_compartilhada.domain import (
    ErroDeRegraDeNegocio, FUSO_OPERACIONAL, texto_obrigatorio, validar_instante,
)


class TipoSenha(StrEnum):
    NORMAL = "normal"
    PRIORITARIA = "prioritaria"


class EstadoSenha(StrEnum):
    AGUARDANDO = "aguardando"
    CHAMADA = "chamada"
    EM_ATENDIMENTO = "em_atendimento"
    FINALIZADA = "finalizada"
    CANCELADA = "cancelada"


@dataclass(frozen=True)
class SenhaChamada:
    senha_id: UUID
    fila_id: UUID
    chamada_em: datetime
    id: UUID = field(default_factory=uuid4)


@dataclass
class Senha:
    fila_id: str
    numero: str
    tipo: TipoSenha
    usuario_id: str
    emitida_em: datetime
    canal: str
    id: UUID = field(default_factory=uuid4)
    estado: EstadoSenha = EstadoSenha.AGUARDANDO
    chamada_em: datetime | None = None
    atendimento_iniciado_em: datetime | None = None
    atendimento_finalizado_em: datetime | None = None
    atendente_id: str | None = None
    guiche_id: str | None = None
    motivo_cancelamento: str | None = None
    dia_operacional: date = field(init=False)

    def __post_init__(self) -> None:
        self.fila_id = str(UUID(str(self.fila_id)))
        self.tipo = TipoSenha(self.tipo)
        self.usuario_id = texto_obrigatorio(self.usuario_id, "Usuário")
        self.canal = texto_obrigatorio(self.canal, "Canal")
        if self.canal not in ("online", "totem"):
            raise ValueError("Canal deve ser online ou totem.")
        self.dia_operacional = validar_instante(self.emitida_em).astimezone(FUSO_OPERACIONAL).date()

    def _validar_ordem(self, quando: datetime, anterior: datetime | None) -> None:
        if anterior is None:
            raise ErroDeRegraDeNegocio("O horário da etapa anterior deve estar registrado.")
        if validar_instante(quando) < anterior:
            raise ErroDeRegraDeNegocio("A transição não pode preceder a etapa anterior.")

    def chamar(self, *, atendente_id: str, guiche_id: str, chamada_em: datetime) -> None:
        if self.estado is not EstadoSenha.AGUARDANDO:
            raise ErroDeRegraDeNegocio("Apenas uma senha aguardando pode ser chamada.")
        atendente = texto_obrigatorio(atendente_id, "Atendente")
        guiche = texto_obrigatorio(guiche_id, "Guichê")
        self._validar_ordem(chamada_em, self.emitida_em)
        self.estado = EstadoSenha.CHAMADA
        self.chamada_em = chamada_em
        self.atendente_id = atendente
        self.guiche_id = guiche

    def iniciar_atendimento(self, quando: datetime) -> None:
        if self.estado is not EstadoSenha.CHAMADA:
            raise ErroDeRegraDeNegocio("O atendimento só pode iniciar para uma senha chamada.")
        self._validar_ordem(quando, self.chamada_em)
        self.estado = EstadoSenha.EM_ATENDIMENTO
        self.atendimento_iniciado_em = quando

    def finalizar_atendimento(self, quando: datetime) -> None:
        if self.estado is not EstadoSenha.EM_ATENDIMENTO:
            raise ErroDeRegraDeNegocio("O atendimento só pode finalizar quando estiver em andamento.")
        self._validar_ordem(quando, self.atendimento_iniciado_em)
        self.estado = EstadoSenha.FINALIZADA
        self.atendimento_finalizado_em = quando

    def cancelar(self, motivo: str) -> None:
        if self.estado not in (EstadoSenha.AGUARDANDO, EstadoSenha.CHAMADA):
            raise ErroDeRegraDeNegocio("Apenas senhas aguardando ou chamadas podem ser canceladas.")
        self.estado = EstadoSenha.CANCELADA
        self.motivo_cancelamento = motivo


def selecionar_proxima(senhas: list[Senha], consecutivas: int) -> Senha | None:
    """Seleção pura: o contador só muda após a chamada bem-sucedida."""
    aguardando = sorted(
        (s for s in senhas if s.estado is EstadoSenha.AGUARDANDO),
        key=lambda s: (s.emitida_em, str(s.id)),
    )
    prioritarias = [s for s in aguardando if s.tipo is TipoSenha.PRIORITARIA]
    normais = [s for s in aguardando if s.tipo is TipoSenha.NORMAL]
    if prioritarias and (not normais or consecutivas < 2):
        return prioritarias[0]
    return normais[0] if normais else None
