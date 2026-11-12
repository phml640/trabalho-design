"""Rotas HTTP do componente de gerenciamento de senhas."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from .application import GerenciadorDeSenhas
from .domain import Senha, TipoSenha
from .infrastructure import RepositorioDeSenhasEmMemoria

router = APIRouter(prefix="/filas", tags=["Senhas"])
gerenciador = GerenciadorDeSenhas(RepositorioDeSenhasEmMemoria())


class EmissaoDeSenha(BaseModel):
    usuario_id: str = Field(min_length=1)
    tipo: TipoSenha = TipoSenha.NORMAL
    canal: str = Field(default="online", min_length=1)


class ChamadaDeSenha(BaseModel):
    atendente_id: str = Field(min_length=1)
    guiche_id: str = Field(min_length=1)


def _representar(senha: Senha) -> dict[str, object]:
    return {
        "id": str(senha.id),
        "fila_id": senha.fila_id,
        "numero": senha.numero,
        "tipo": senha.tipo,
        "usuario_id": senha.usuario_id,
        "estado": senha.estado,
        "emitida_em": senha.emitida_em,
        "canal": senha.canal,
        "atendente_id": senha.atendente_id,
        "guiche_id": senha.guiche_id,
    }


@router.post("/{fila_id}/senhas", status_code=status.HTTP_201_CREATED)
def emitir_senha(fila_id: str, entrada: EmissaoDeSenha) -> dict[str, object]:
    senha = gerenciador.emitir_senha(fila_id=fila_id, **entrada.model_dump())
    return _representar(senha)


@router.get("/{fila_id}/senhas")
def consultar_senhas(fila_id: str) -> list[dict[str, object]]:
    return [_representar(senha) for senha in gerenciador.consultar_fila(fila_id)]


@router.post("/{fila_id}/senhas/chamada")
def chamar_senha(
    fila_id: str, entrada: ChamadaDeSenha
) -> dict[str, object]:
    senha = gerenciador.chamar_proxima_senha(fila_id=fila_id, **entrada.model_dump())
    if senha is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não há senhas aguardando nesta fila.",
        )
    return _representar(senha)
