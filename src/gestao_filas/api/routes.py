"""Rotas HTTP do componente de gestão de filas."""

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from gestao_filas.application import GestaoDeFilas
from gestao_filas.domain.model import EstadoFila, Fila
from gestao_compartilhada.http import RESPOSTAS_ERRO

from .dependencies import obter_gestao_de_filas

router = APIRouter(prefix="/filas", tags=["Filas"], responses=RESPOSTAS_ERRO)
Gestao = Annotated[GestaoDeFilas, Depends(obter_gestao_de_filas)]


class CriacaoDeFila(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    nome: str = Field(min_length=1, max_length=120)
    descricao: str | None = Field(default=None, max_length=500)


class FilaResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    nome: str
    descricao: str | None
    estado: EstadoFila
    criada_em: datetime
    encerrada_em: datetime | None
    dia_operacional: date
    chamadas_prioritarias_consecutivas: int


def _representar(fila: Fila) -> FilaResposta:
    return FilaResposta.model_validate(fila)


@router.post("", status_code=status.HTTP_201_CREATED)
def criar_fila(entrada: CriacaoDeFila, gestao: Gestao) -> FilaResposta:
    return _representar(gestao.criar_fila(**entrada.model_dump()))


@router.get("")
def listar_filas(gestao: Gestao, abertas: bool = False) -> list[FilaResposta]:
    return [_representar(f) for f in gestao.listar_filas(apenas_abertas=abertas)]


@router.get("/{fila_id}")
def obter_fila(fila_id: UUID, gestao: Gestao) -> FilaResposta:
    return _representar(gestao.obter_fila(fila_id))


@router.post("/{fila_id}/encerramento")
def encerrar_fila(fila_id: UUID, gestao: Gestao) -> FilaResposta:
    return _representar(gestao.encerrar_fila(fila_id))


@router.post("/{fila_id}/reabertura")
def reabrir_fila(fila_id: UUID, gestao: Gestao) -> FilaResposta:
    return _representar(gestao.reabrir_fila(fila_id))
