"""Regras de coordenação executadas dentro de uma transação já aberta."""

from datetime import datetime
from uuid import UUID

from gestao_filas.domain.model import Fila
from gestao_senhas.domain import EstadoSenha, Senha

from .application import Transacao
from .domain import (
    ErroDeRegraDeNegocio, FUSO_OPERACIONAL, QueueNotFoundError,
    TransicaoSenha, validar_instante,
)


def obter_fila(tx: Transacao, fila_id: UUID) -> Fila:
    fila = tx.filas.buscar(fila_id)
    if fila is None:
        raise QueueNotFoundError(f"Fila '{fila_id}' não encontrada.")
    return fila


def registrar(tx: Transacao, senha: Senha, anterior: EstadoSenha | None, quando: datetime) -> None:
    tx.senhas.salvar(senha)
    tx.registrar_transicao(TransicaoSenha(
        senha_id=senha.id,
        fila_id=UUID(senha.fila_id),
        estado_anterior=anterior,
        estado=senha.estado,
        quando=quando,
        atendente_id=senha.atendente_id,
        guiche_id=senha.guiche_id,
        motivo=senha.motivo_cancelamento,
    ))


def cancelar_pendentes(
    tx: Transacao, fila: Fila, quando: datetime, motivo: str, *, apenas_anteriores: bool = False,
) -> None:
    for senha in tx.senhas.listar(fila.id):
        if apenas_anteriores and senha.dia_operacional >= fila.dia_operacional:
            continue
        if senha.estado in (EstadoSenha.AGUARDANDO, EstadoSenha.CHAMADA):
            anterior = senha.estado
            senha.cancelar(motivo)
            registrar(tx, senha, anterior, quando)


def garantir_dia(tx: Transacao, fila: Fila, quando: datetime) -> None:
    dia = validar_instante(quando).astimezone(FUSO_OPERACIONAL).date()
    if dia < fila.dia_operacional:
        raise ErroDeRegraDeNegocio("A operação não pode retroceder o dia operacional da fila.")
    if dia > fila.dia_operacional:
        fila.dia_operacional = dia
        fila.chamadas_prioritarias_consecutivas = 0
        cancelar_pendentes(tx, fila, quando, "encerramento_diario", apenas_anteriores=True)
        tx.filas.salvar(fila)
