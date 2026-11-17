"""Consultas operacionais e processamento manual para a demonstração local."""

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, computed_field

from gestao_senhas.domain import EstadoSenha

from .consultas import Consultas
from .http import PaginaResposta, RESPOSTAS_ERRO
from .notificacoes import ProcessadorOutbox

router = APIRouter(responses=RESPOSTAS_ERRO)
Limite = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


def obter_consultas(request: Request) -> Consultas:
    return Consultas(request.app.state.unidade_de_trabalho)


Consulta = Annotated[Consultas, Depends(obter_consultas)]


class TransicaoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    senha_id: UUID
    fila_id: UUID
    estado_anterior: EstadoSenha | None
    estado: EstadoSenha
    quando: datetime
    atendente_id: str | None
    guiche_id: str | None
    motivo: str | None


class EventoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    senha_id: UUID
    fila_id: UUID
    chamada_em: datetime


class NotificacaoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    evento: EventoResposta
    tentativas: int
    processado_em: datetime | None
    ultimo_erro: str | None
    reservado_ate: datetime | None

    @computed_field
    @property
    def status(self) -> Literal["pendente", "em_processamento", "falha", "processada"]:
        if self.processado_em is not None:
            return "processada"
        if self.reservado_ate is not None and self.reservado_ate > datetime.now(timezone.utc):
            return "em_processamento"
        return "falha" if self.ultimo_erro else "pendente"


class SimuladaResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    evento_id: UUID
    senha_id: UUID
    fila_id: UUID
    mensagem: str
    criada_em: datetime


class TentativaResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    evento_id: UUID
    numero: int
    iniciada_em: datetime
    finalizada_em: datetime | None
    erro: str | None


class ProcessamentoEntrada(BaseModel):
    limite: int = Field(default=20, ge=1, le=100)
    simular_falha: bool = False


class ProcessamentoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    processadas: int
    sucessos: int
    falhas: int


@router.get("/filas/{fila_id}/historico", tags=["Histórico"])
def consultar_historico(
    fila_id: UUID, consultas: Consulta, limite: Limite = 20, offset: Offset = 0,
    senha_id: UUID | None = None, estado: EstadoSenha | None = None,
) -> PaginaResposta[TransicaoResposta]:
    """Inclui dias anteriores, atendimentos finalizados e senhas canceladas."""
    return PaginaResposta[TransicaoResposta].model_validate(consultas.historico(
        fila_id, limite=limite, offset=offset, senha_id=senha_id, estado=estado,
    ))


@router.get("/notificacoes", tags=["Notificações"])
def consultar_notificacoes(
    consultas: Consulta, limite: Limite = 20, offset: Offset = 0,
    fila_id: UUID | None = None, senha_id: UUID | None = None,
) -> PaginaResposta[NotificacaoResposta]:
    """Inspeciona eventos pendentes, reservas, sucessos e falhas."""
    return PaginaResposta[NotificacaoResposta].model_validate(consultas.notificacoes(
        limite=limite, offset=offset, fila_id=fila_id, senha_id=senha_id,
    ))


@router.get("/notificacoes/simuladas", tags=["Notificações"])
def consultar_simuladas(
    consultas: Consulta, limite: Limite = 20, offset: Offset = 0,
    fila_id: UUID | None = None, senha_id: UUID | None = None,
) -> PaginaResposta[SimuladaResposta]:
    return PaginaResposta[SimuladaResposta].model_validate(consultas.notificacoes(
        limite=limite, offset=offset, fila_id=fila_id, senha_id=senha_id, simuladas=True,
    ))


@router.get("/notificacoes/{evento_id}/tentativas", tags=["Notificações"])
def consultar_tentativas(
    evento_id: UUID, consultas: Consulta, limite: Limite = 20, offset: Offset = 0,
) -> PaginaResposta[TentativaResposta]:
    return PaginaResposta[TentativaResposta].model_validate(consultas.tentativas(
        evento_id, limite=limite, offset=offset,
    ))


@router.post("/notificacoes/processamento", tags=["Notificações"])
def processar_notificacoes(
    request: Request, entrada: ProcessamentoEntrada = Body(default=ProcessamentoEntrada()),
) -> ProcessamentoResposta:
    """Executa um lote. Falhas ficam registradas e podem ser tentadas novamente.

    simular_falha usa um adaptador que falha sem enviar; não altera a chamada.
    """
    notificador = request.app.state.notificador_falho if entrada.simular_falha else request.app.state.notificador
    resultado = ProcessadorOutbox(request.app.state.unidade_de_trabalho, notificador).processar(entrada.limite)
    return ProcessamentoResposta.model_validate(resultado)
