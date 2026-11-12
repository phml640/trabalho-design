"""Adaptadores de persistência do gerenciador de senhas."""

from __future__ import annotations

from collections import defaultdict
from threading import RLock

from .domain import EstadoSenha, Senha, TipoSenha


class RepositorioDeSenhasEmMemoria:
    """Persistência temporária para o protótipo e testes do componente."""

    def __init__(self) -> None:
        self._senhas: dict[str, Senha] = {}
        self._contadores: defaultdict[tuple[str, TipoSenha], int] = defaultdict(int)
        self._prioritarias_consecutivas: defaultdict[str, int] = defaultdict(int)
        self._lock = RLock()

    def proximo_numero(self, fila_id: str, tipo: TipoSenha) -> str:
        with self._lock:
            chave = (fila_id, tipo)
            self._contadores[chave] += 1
            prefixo = "P" if tipo is TipoSenha.PRIORITARIA else "N"
            return f"{prefixo}{self._contadores[chave]:03d}"

    def emitir(self, senha: Senha) -> Senha:
        with self._lock:
            self._senhas[str(senha.id)] = senha
            return senha

    def listar(self, fila_id: str) -> list[Senha]:
        with self._lock:
            return sorted(
                (
                    senha
                    for senha in self._senhas.values()
                    if senha.fila_id == fila_id
                    and senha.estado is not EstadoSenha.FINALIZADA
                    and senha.estado is not EstadoSenha.CANCELADA
                ),
                key=lambda senha: (senha.emitida_em, str(senha.id)),
            )

    def listar_todas(self) -> list[Senha]:
        with self._lock:
            return list(self._senhas.values())

    def proxima_senha(self, fila_id: str, limite_prioritarias: int) -> Senha | None:
        with self._lock:
            aguardando = [
                senha
                for senha in self._senhas.values()
                if senha.fila_id == fila_id
                and senha.estado is EstadoSenha.AGUARDANDO
            ]
            prioritarias = sorted(
                (s for s in aguardando if s.tipo is TipoSenha.PRIORITARIA),
                key=lambda senha: (senha.emitida_em, str(senha.id)),
            )
            normais = sorted(
                (s for s in aguardando if s.tipo is TipoSenha.NORMAL),
                key=lambda senha: (senha.emitida_em, str(senha.id)),
            )
            if prioritarias and normais:
                if self._prioritarias_consecutivas[fila_id] < limite_prioritarias:
                    escolhida = prioritarias[0]
                else:
                    escolhida = normais[0]
            else:
                escolhida = (prioritarias or normais or [None])[0]

            if escolhida is not None:
                if escolhida.tipo is TipoSenha.PRIORITARIA:
                    self._prioritarias_consecutivas[fila_id] += 1
                else:
                    self._prioritarias_consecutivas[fila_id] = 0
            return escolhida

    def salvar(self, senha: Senha) -> Senha:
        with self._lock:
            self._senhas[str(senha.id)] = senha
            return senha
