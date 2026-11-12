"""Casos de uso do componente de filas."""

from gestao_compartilhada.domain import QueueNotFoundError
from .service import GestaoDeFilas

__all__ = ["GestaoDeFilas", "QueueNotFoundError"]
