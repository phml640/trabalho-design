"""Rotas HTTP do componente de gerenciamento de senhas."""

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from gestao_filas.api.dependencies import obter_gerenciador_de_senhas
from gestao_compartilhada.http import RESPOSTAS_ERRO

from .application import GerenciadorDeSenhas
from .domain import EstadoSenha, TipoSenha

router = APIRouter(tags=["Senhas"], responses=RESPOSTAS_ERRO)
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


class SenhaResposta(BaseModel):
    """Visão pública: omite identificação do usuário e do atendente."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    fila_id: UUID
    numero: str
    tipo: TipoSenha
    estado: EstadoSenha
    emitida_em: datetime
    dia_operacional: date
    canal: Literal["online", "totem"]
    guiche_id: str | None
    chamada_em: datetime | None
    atendimento_iniciado_em: datetime | None
    atendimento_finalizado_em: datetime | None
    motivo_cancelamento: str | None


class SenhaAtendimentoResposta(SenhaResposta):
    atendente_id: str | None


@router.post("/filas/{fila_id}/senhas", status_code=status.HTTP_201_CREATED)
def emitir_senha(fila_id: UUID, entrada: EmissaoDeSenha, gerenciador: Gerenciador) -> SenhaResposta:
    """Classificação prioritária demonstrativa; elegibilidade não verificada."""
    return SenhaResposta.model_validate(gerenciador.emitir_senha(fila_id=str(fila_id), **entrada.model_dump()))


@router.get("/filas/{fila_id}/senhas")
def consultar_senhas(fila_id: UUID, gerenciador: Gerenciador) -> list[SenhaResposta]:
    return [SenhaResposta.model_validate(s) for s in gerenciador.consultar_fila(str(fila_id))]


@router.post("/filas/{fila_id}/senhas/chamada")
def chamar_senha(fila_id: UUID, entrada: ChamadaDeSenha, gerenciador: Gerenciador) -> SenhaAtendimentoResposta:
    senha = gerenciador.chamar_proxima_senha(fila_id=str(fila_id), **entrada.model_dump())
    if senha is None:
        raise HTTPException(status_code=404, detail="Não há senhas aguardando nesta fila.")
    return SenhaAtendimentoResposta.model_validate(senha)


@router.get("/senhas/{senha_id}")
def consultar_senha(senha_id: UUID, gerenciador: Gerenciador) -> SenhaResposta:
    """Consulta individual, incluindo estados finais e cancelamentos."""
    return SenhaResposta.model_validate(gerenciador.consultar_senha(str(senha_id)))


@router.post("/senhas/{senha_id}/atendimento/inicio")
def iniciar_atendimento(senha_id: UUID, gerenciador: Gerenciador) -> SenhaAtendimentoResposta:
    return SenhaAtendimentoResposta.model_validate(gerenciador.iniciar_atendimento(str(senha_id)))


@router.post("/senhas/{senha_id}/atendimento/finalizacao")
def finalizar_atendimento(senha_id: UUID, gerenciador: Gerenciador) -> SenhaAtendimentoResposta:
    """Permite concluir atendimento já iniciado, inclusive após encerramento da fila."""
    return SenhaAtendimentoResposta.model_validate(gerenciador.finalizar_atendimento(str(senha_id)))
