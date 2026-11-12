"""Tipos compartilhados, sem dependências de persistência ou HTTP."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

FUSO_OPERACIONAL = ZoneInfo("America/Sao_Paulo")


class ErroDeRegraDeNegocio(ValueError):
    """Operação incompatível com as regras ou o estado atual."""


class QueueNotFoundError(LookupError):
    """Fila não encontrada."""


def validar_instante(quando: datetime) -> datetime:
    if quando.tzinfo is None or quando.utcoffset() is None:
        raise ValueError("O horário deve incluir o fuso horário.")
    return quando


def texto_obrigatorio(valor: str, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"{campo} é obrigatório.")
    return valor.strip()


@dataclass(frozen=True)
class TransicaoSenha:
    senha_id: UUID
    fila_id: UUID
    estado_anterior: str | None
    estado: str
    quando: datetime
    atendente_id: str | None = None
    guiche_id: str | None = None
    motivo: str | None = None
    id: UUID = field(default_factory=uuid4)
