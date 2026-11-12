"""Casos de uso do componente de gestão de filas."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from . import QueueNotFoundError
from gestao_filas.domain.model import EstadoFila, Fila


class RepositorioDeFilas(Protocol):
    def salvar(self, fila: Fila) -> Fila: ...

    def buscar(self, fila_id: UUID) -> Fila | None: ...

    def listar(self) -> list[Fila]: ...


class GestaoDeFilas:
    """Coordena criação, consulta e ciclo administrativo das filas."""

    def __init__(self, repositorio: RepositorioDeFilas) -> None:
        self._repositorio = repositorio

    def criar_fila(self, nome: str, descricao: str | None = None) -> Fila:
        nome = nome.strip()
        if not nome:
            raise ValueError("O nome da fila é obrigatório.")
        if any(f.nome.casefold() == nome.casefold() for f in self._repositorio.listar()):
            raise ValueError("Já existe uma fila com esse nome.")
        return self._repositorio.salvar(Fila(nome=nome, descricao=descricao))

    def listar_filas(self, apenas_abertas: bool = False) -> list[Fila]:
        filas = self._repositorio.listar()
        if apenas_abertas:
            return [fila for fila in filas if fila.estado is EstadoFila.ABERTA]
        return filas

    def obter_fila(self, fila_id: UUID) -> Fila:
        fila = self._repositorio.buscar(fila_id)
        if fila is None:
            raise QueueNotFoundError(f"Fila '{fila_id}' não encontrada.")
        return fila

    def encerrar_fila(self, fila_id: UUID, quando: datetime | None = None) -> Fila:
        fila = self.obter_fila(fila_id)
        fila.encerrar(quando)
        return self._repositorio.salvar(fila)

    def reabrir_fila(self, fila_id: UUID) -> Fila:
        fila = self.obter_fila(fila_id)
        fila.reabrir()
        return self._repositorio.salvar(fila)
