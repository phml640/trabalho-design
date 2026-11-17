"""Repositórios válidos apenas durante a transação que os criou."""

from copy import deepcopy
from dataclasses import fields
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from gestao_filas.domain.model import EstadoFila, Fila
from gestao_senhas.domain import EstadoSenha, Senha, TipoSenha

from .models import ContadorSenhaModelo, FilaModelo, SenhaModelo


def _valores(entidade) -> dict:
    valores = {campo.name: getattr(entidade, campo.name) for campo in fields(entidade)}
    return {
        chave: valor.astimezone(timezone.utc) if isinstance(valor, datetime) else valor
        for chave, valor in valores.items()
    }


def _fila(modelo: FilaModelo) -> Fila:
    valores = {campo.name: getattr(modelo, campo.name) for campo in fields(Fila)}
    valores["estado"] = EstadoFila(valores["estado"])
    return Fila(**valores)


def _senha(modelo: SenhaModelo) -> Senha:
    valores = {campo.name: getattr(modelo, campo.name) for campo in fields(Senha) if campo.init}
    valores["estado"] = EstadoSenha(valores["estado"])
    return Senha(**valores)


class RepositorioDeFilasPostgres:
    def __init__(self, session: Session) -> None:
        self._session = session

    def salvar(self, fila: Fila) -> Fila:
        self._session.merge(FilaModelo(**_valores(fila), nome_normalizado=fila.nome.casefold()))
        self._session.flush()
        return deepcopy(fila)

    def buscar(self, fila_id: UUID) -> Fila | None:
        modelo = self._session.get(FilaModelo, fila_id)
        return _fila(modelo) if modelo is not None else None

    def listar(self) -> list[Fila]:
        modelos = self._session.scalars(select(FilaModelo).order_by(FilaModelo.criada_em, FilaModelo.id))
        return [_fila(m) for m in modelos]


class RepositorioDeSenhasPostgres:
    def __init__(self, session: Session) -> None:
        self._session = session

    def salvar(self, senha: Senha) -> Senha:
        valores = _valores(senha)
        valores["fila_id"] = UUID(senha.fila_id)
        self._session.merge(SenhaModelo(**valores))
        self._session.flush()
        return deepcopy(senha)

    def buscar(self, senha_id: UUID) -> Senha | None:
        modelo = self._session.get(SenhaModelo, senha_id)
        return _senha(modelo) if modelo is not None else None

    def listar(self, fila_id: UUID) -> list[Senha]:
        modelos = self._session.scalars(
            select(SenhaModelo).where(SenhaModelo.fila_id == fila_id)
            .order_by(SenhaModelo.emitida_em, SenhaModelo.id)
        )
        return [_senha(m) for m in modelos]

    def proximo_numero(self, fila_id: UUID, dia: date, tipo: TipoSenha) -> str:
        # Contador transacional, sem sequences: rollback não consome o número.
        comando = insert(ContadorSenhaModelo).values(
            fila_id=fila_id, dia_operacional=dia, tipo=tipo, ultimo_numero=1,
        ).on_conflict_do_update(
            index_elements=["fila_id", "dia_operacional", "tipo"],
            set_={"ultimo_numero": ContadorSenhaModelo.ultimo_numero + 1},
        ).returning(ContadorSenhaModelo.ultimo_numero)
        numero = self._session.scalar(comando)
        prefixo = "P" if tipo is TipoSenha.PRIORITARIA else "N"
        return f"{prefixo}{numero:03d}"
