"""Repositório de senhas usado exclusivamente dentro da unidade de trabalho."""

from copy import deepcopy
from datetime import date
from uuid import UUID

from .domain import Senha, TipoSenha


class RepositorioDeSenhasEmMemoria:
    def __init__(
        self,
        senhas: dict[UUID, Senha],
        contadores: dict[tuple[UUID, date, TipoSenha], int],
    ) -> None:
        self._senhas = senhas
        self._contadores = contadores

    def proximo_numero(self, fila_id: UUID, dia: date, tipo: TipoSenha) -> str:
        chave = (fila_id, dia, tipo)
        self._contadores[chave] = self._contadores.get(chave, 0) + 1
        prefixo = "P" if tipo is TipoSenha.PRIORITARIA else "N"
        return f"{prefixo}{self._contadores[chave]:03d}"

    def buscar(self, senha_id: UUID) -> Senha | None:
        return deepcopy(self._senhas.get(senha_id))

    def listar(self, fila_id: UUID) -> list[Senha]:
        return sorted(
            (deepcopy(s) for s in self._senhas.values() if s.fila_id == str(fila_id)),
            key=lambda s: (s.emitida_em, str(s.id)),
        )

    def salvar(self, senha: Senha) -> Senha:
        self._senhas[senha.id] = deepcopy(senha)
        return senha
