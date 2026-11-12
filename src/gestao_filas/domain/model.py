"""Entidades e regras de negócio das filas."""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from gestao_compartilhada.domain import ErroDeRegraDeNegocio, FUSO_OPERACIONAL


class EstadoFila(StrEnum):
    ABERTA = "aberta"
    ENCERRADA = "encerrada"


class RegraDeFilaError(ErroDeRegraDeNegocio):
    """Indica uma operação inválida sobre uma fila."""


@dataclass
class Fila:
    nome: str
    descricao: str | None = None
    id: UUID = field(default_factory=uuid4)
    estado: EstadoFila = EstadoFila.ABERTA
    criada_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    encerrada_em: datetime | None = None
    chamadas_prioritarias_consecutivas: int = 0
    dia_operacional: date | None = None

    def __post_init__(self) -> None:
        if self.dia_operacional is None:
            self.dia_operacional = self.criada_em.astimezone(FUSO_OPERACIONAL).date()

    def exigir_aberta(self) -> None:
        if self.estado is not EstadoFila.ABERTA:
            raise RegraDeFilaError("A fila está encerrada.")

    def encerrar(self, quando: datetime) -> None:
        if self.estado is EstadoFila.ENCERRADA:
            return
        self.estado = EstadoFila.ENCERRADA
        self.encerrada_em = quando

    def reabrir(self) -> None:
        # Repetir a reabertura não reinicia a política da fila já aberta.
        if self.estado is EstadoFila.ENCERRADA:
            self.estado = EstadoFila.ABERTA
            self.encerrada_em = None

    def registrar_chamada_prioritaria(self) -> None:
        self.chamadas_prioritarias_consecutivas += 1

    def registrar_chamada_normal(self) -> None:
        self.chamadas_prioritarias_consecutivas = 0
