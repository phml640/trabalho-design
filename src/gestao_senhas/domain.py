"""Entidades e regras de negócio do gerenciador de senhas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class TipoSenha(StrEnum):
    NORMAL = "normal"
    PRIORITARIA = "prioritaria"


class EstadoSenha(StrEnum):
    AGUARDANDO = "aguardando"
    CHAMADA = "chamada"
    EM_ATENDIMENTO = "em_atendimento"
    FINALIZADA = "finalizada"
    CANCELADA = "cancelada"


class ErroDeRegraDeNegocio(ValueError):
    """Indica uma operação incompatível com o estado atual da senha."""


@dataclass
class Senha:
    fila_id: str
    numero: str
    tipo: TipoSenha
    usuario_id: str
    emitida_em: datetime
    canal: str
    id: UUID | None = None
    estado: EstadoSenha = EstadoSenha.AGUARDANDO
    chamada_em: datetime | None = None
    atendimento_iniciado_em: datetime | None = None
    atendimento_finalizado_em: datetime | None = None
    atendente_id: str | None = None
    guiche_id: str | None = None
    motivo_cancelamento: str | None = None

    def __post_init__(self) -> None:
        if self.id is None:
            self.id = uuid4()

    def chamar(
        self,
        *,
        atendente_id: str,
        guiche_id: str,
        chamada_em: datetime,
    ) -> None:
        if self.estado is not EstadoSenha.AGUARDANDO:
            raise ErroDeRegraDeNegocio(
                "Apenas uma senha aguardando pode ser chamada."
            )
        self.estado = EstadoSenha.CHAMADA
        self.chamada_em = chamada_em
        self.atendente_id = atendente_id
        self.guiche_id = guiche_id

    def iniciar_atendimento(self, quando: datetime) -> None:
        if self.estado is not EstadoSenha.CHAMADA:
            raise ErroDeRegraDeNegocio(
                "O atendimento só pode iniciar para uma senha chamada."
            )
        self.estado = EstadoSenha.EM_ATENDIMENTO
        self.atendimento_iniciado_em = quando

    def finalizar_atendimento(self, quando: datetime) -> None:
        if self.estado is not EstadoSenha.EM_ATENDIMENTO:
            raise ErroDeRegraDeNegocio(
                "O atendimento só pode finalizar quando estiver em andamento."
            )
        self.estado = EstadoSenha.FINALIZADA
        self.atendimento_finalizado_em = quando

    def cancelar(self, motivo: str) -> None:
        if self.estado not in (EstadoSenha.AGUARDANDO, EstadoSenha.CHAMADA):
            raise ErroDeRegraDeNegocio(
                "Apenas senhas aguardando ou chamadas podem ser canceladas."
            )
        self.estado = EstadoSenha.CANCELADA
        self.motivo_cancelamento = motivo
