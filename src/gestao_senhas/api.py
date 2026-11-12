"""Rotas HTTP do componente de gerenciamento de senhas."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from gestao_filas.api.dependencies import obter_gerenciador_de_senhas

from .application import GerenciadorDeSenhas
from .domain import Senha, TipoSenha

router = APIRouter(prefix="/filas", tags=["Senhas"])
Gerenciador = Annotated[GerenciadorDeSenhas, Depends(obter_gerenciador_de_senhas)]


class EmissaoDeSenha(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    usuario_id: str = Field(min_length=1)
    tipo: TipoSenha = TipoSenha.NORMAL
    canal: Literal["online", "totem"] = "online"


class ChamadaDeSenha(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    atendente_id: str = Field(min_length=1)
    guiche_id: str = Field(min_length=1)


def _representar(senha: Senha) -> dict[str, object]:
    return {
        "id": str(senha.id), "fila_id": senha.fila_id, "numero": senha.numero,
        "tipo": senha.tipo, "usuario_id": senha.usuario_id, "estado": senha.estado,
        "emitida_em": senha.emitida_em, "dia_operacional": senha.dia_operacional,
        "canal": senha.canal, "atendente_id": senha.atendente_id,
        "guiche_id": senha.guiche_id,
    }


@router.post("/{fila_id}/senhas", status_code=status.HTTP_201_CREATED)
def emitir_senha(fila_id: UUID, entrada: EmissaoDeSenha, gerenciador: Gerenciador) -> dict[str, object]:
    return _representar(gerenciador.emitir_senha(fila_id=str(fila_id), **entrada.model_dump()))


@router.get("/{fila_id}/senhas")
def consultar_senhas(fila_id: UUID, gerenciador: Gerenciador) -> list[dict[str, object]]:
    return [_representar(s) for s in gerenciador.consultar_fila(str(fila_id))]


@router.post("/{fila_id}/senhas/chamada")
def chamar_senha(fila_id: UUID, entrada: ChamadaDeSenha, gerenciador: Gerenciador) -> dict[str, object]:
    senha = gerenciador.chamar_proxima_senha(fila_id=str(fila_id), **entrada.model_dump())
    if senha is None:
        raise HTTPException(status_code=404, detail="Não há senhas aguardando nesta fila.")
    return _representar(senha)
