"""Casos de uso do gerenciador de senhas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from .domain import EstadoSenha, ErroDeRegraDeNegocio, Senha, TipoSenha


class RepositorioDeSenhas(Protocol):
    def emitir(self, senha: Senha) -> Senha: ...

    def listar(self, fila_id: str) -> list[Senha]: ...

    def proxima_senha(self, fila_id: str, limite_prioritarias: int) -> Senha | None: ...

    def salvar(self, senha: Senha) -> Senha: ...

    def proximo_numero(self, fila_id: str, tipo: TipoSenha) -> str: ...

    def listar_todas(self) -> list[Senha]: ...


class GerenciadorDeSenhas:
    """Coordena emissão, consulta e transições do ciclo de uma senha."""

    def __init__(self, repositorio: RepositorioDeSenhas) -> None:
        self._repositorio = repositorio

    def emitir_senha(
        self,
        *,
        fila_id: str,
        usuario_id: str,
        tipo: TipoSenha,
        canal: str,
        emitida_em: datetime | None = None,
    ) -> Senha:
        agora = emitida_em or datetime.now(timezone.utc)
        numero = self._repositorio.proximo_numero(fila_id, tipo)
        senha = Senha(
            fila_id=fila_id,
            numero=numero,
            tipo=tipo,
            usuario_id=usuario_id,
            emitida_em=agora,
            canal=canal,
        )
        return self._repositorio.emitir(senha)

    def consultar_fila(self, fila_id: str) -> list[Senha]:
        return self._repositorio.listar(fila_id)

    def chamar_proxima_senha(
        self,
        *,
        fila_id: str,
        atendente_id: str,
        guiche_id: str,
        chamada_em: datetime | None = None,
    ) -> Senha | None:
        senha = self._repositorio.proxima_senha(fila_id, 2)
        if senha is None:
            return None
        senha.chamar(
            atendente_id=atendente_id,
            guiche_id=guiche_id,
            chamada_em=chamada_em or datetime.now(timezone.utc),
        )
        return self._repositorio.salvar(senha)

    def iniciar_atendimento(
        self, senha_id: str, quando: datetime | None = None
    ) -> Senha:
        senha = self._senha_por_id(senha_id)
        senha.iniciar_atendimento(quando or datetime.now(timezone.utc))
        return self._repositorio.salvar(senha)

    def finalizar_atendimento(
        self, senha_id: str, quando: datetime | None = None
    ) -> Senha:
        senha = self._senha_por_id(senha_id)
        senha.finalizar_atendimento(quando or datetime.now(timezone.utc))
        return self._repositorio.salvar(senha)

    def _senha_por_id(self, senha_id: str) -> Senha:
        for senha in self._repositorio.listar_todas():
            if str(senha.id) == senha_id:
                return senha
        raise LookupError(f"Senha '{senha_id}' não encontrada.")
