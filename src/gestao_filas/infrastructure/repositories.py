"""Repositório de filas usado exclusivamente dentro da unidade de trabalho."""

from copy import deepcopy
from uuid import UUID

from gestao_filas.domain.model import Fila


class RepositorioDeFilasEmMemoria:
    def __init__(self, filas: dict[UUID, Fila]) -> None:
        self._filas = filas

    def salvar(self, fila: Fila) -> Fila:
        self._filas[fila.id] = deepcopy(fila)
        return fila

    def buscar(self, fila_id: UUID) -> Fila | None:
        return deepcopy(self._filas.get(fila_id))

    def listar(self) -> list[Fila]:
        return sorted(deepcopy(list(self._filas.values())), key=lambda f: f.criada_em)
