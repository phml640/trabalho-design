"""Adaptadores de persistência das filas."""

from __future__ import annotations

from threading import RLock
from uuid import UUID

from gestao_filas.domain.model import Fila


class RepositorioDeFilasEmMemoria:
    """Repositório thread-safe usado pelo protótipo até a integração com PostgreSQL."""

    def __init__(self) -> None:
        self._filas: dict[UUID, Fila] = {}
        self._lock = RLock()

    def salvar(self, fila: Fila) -> Fila:
        with self._lock:
            self._filas[fila.id] = fila
            return fila

    def buscar(self, fila_id: UUID) -> Fila | None:
        with self._lock:
            return self._filas.get(fila_id)

    def listar(self) -> list[Fila]:
        with self._lock:
            return sorted(self._filas.values(), key=lambda fila: fila.criada_em)
