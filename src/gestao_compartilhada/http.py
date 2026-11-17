"""Contratos HTTP compartilhados; permanecem na borda da aplicação."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ErroResposta(BaseModel):
    detail: str | list[dict[str, Any]]


RESPOSTAS_ERRO = {
    404: {"model": ErroResposta, "description": "Recurso inexistente ou nenhuma senha aguardando."},
    409: {"model": ErroResposta, "description": "Estado incompatível com a operação."},
    422: {"model": ErroResposta, "description": "Entrada inválida."},
}


class PaginaResposta(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)
    itens: list[T]
    limite: int
    offset: int
    tem_mais: bool
