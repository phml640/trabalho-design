"""Rotas HTTP do componente de gestão de filas."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from gestao_filas.application import GestaoDeFilas, QueueNotFoundError
from gestao_filas.domain.model import EstadoFila, Fila
from gestao_filas.infrastructure import RepositorioDeFilasEmMemoria

router = APIRouter(prefix="/filas", tags=["Filas"])
gestao_de_filas = GestaoDeFilas(RepositorioDeFilasEmMemoria())


class CriacaoDeFila(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    descricao: str | None = Field(default=None, max_length=500)


def _representar(fila: Fila) -> dict[str, object]:
    return {
        "id": str(fila.id),
        "nome": fila.nome,
        "descricao": fila.descricao,
        "estado": fila.estado,
        "criada_em": fila.criada_em,
        "encerrada_em": fila.encerrada_em,
        "chamadas_prioritarias_consecutivas": fila.chamadas_prioritarias_consecutivas,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def criar_fila(entrada: CriacaoDeFila) -> dict[str, object]:
    try:
        return _representar(gestao_de_filas.criar_fila(**entrada.model_dump()))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.get("")
def listar_filas(abertas: bool = False) -> list[dict[str, object]]:
    return [_representar(fila) for fila in gestao_de_filas.listar_filas(apenas_abertas=abertas)]


@router.get("/{fila_id}")
def obter_fila(fila_id: UUID) -> dict[str, object]:
    try:
        return _representar(gestao_de_filas.obter_fila(fila_id))
    except QueueNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.post("/{fila_id}/encerramento")
def encerrar_fila(fila_id: UUID) -> dict[str, object]:
    try:
        return _representar(gestao_de_filas.encerrar_fila(fila_id))
    except QueueNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.post("/{fila_id}/reabertura")
def reabrir_fila(fila_id: UUID) -> dict[str, object]:
    try:
        return _representar(gestao_de_filas.reabrir_fila(fila_id))
    except QueueNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
