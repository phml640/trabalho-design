"""Entidades e regras de negócio das filas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4


class EstadoFila(StrEnum):
    ABERTA = "aberta"
    ENCERRADA = "encerrada"


class RegraDeFilaError(ValueError):
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

    def encerrar(self, quando: datetime | None = None) -> None:
        if self.estado is EstadoFila.ENCERRADA:
            return
        self.estado = EstadoFila.ENCERRADA
        self.encerrada_em = quando or datetime.now(timezone.utc)

    def reabrir(self) -> None:
        self.estado = EstadoFila.ABERTA
        self.encerrada_em = None
        self.chamadas_prioritarias_consecutivas = 0

    def registrar_chamada_prioritaria(self) -> None:
        self.chamadas_prioritarias_consecutivas += 1

    def registrar_chamada_normal(self) -> None:
        self.chamadas_prioritarias_consecutivas = 0
