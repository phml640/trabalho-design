"""Casos de uso das filas, coordenados com as senhas pela mesma transação."""

from datetime import datetime, timezone
from uuid import UUID

from gestao_compartilhada.application import UnidadeDeTrabalho
from gestao_compartilhada.domain import texto_obrigatorio, validar_instante
from gestao_compartilhada.operacoes import cancelar_pendentes, garantir_dia, obter_fila
from gestao_filas.domain.model import EstadoFila, Fila, RegraDeFilaError


class GestaoDeFilas:
    def __init__(self, unidade_de_trabalho: UnidadeDeTrabalho) -> None:
        self._uow = unidade_de_trabalho

    def criar_fila(
        self, nome: str, descricao: str | None = None, *, quando: datetime | None = None,
    ) -> Fila:
        nome = texto_obrigatorio(nome, "Nome da fila")
        agora = validar_instante(quando or datetime.now(timezone.utc))
        with self._uow.transacao() as tx:
            if any(f.nome.casefold() == nome.casefold() for f in tx.filas.listar()):
                raise RegraDeFilaError("Já existe uma fila com esse nome.")
            return tx.filas.salvar(Fila(nome=nome, descricao=descricao, criada_em=agora))

    def listar_filas(self, apenas_abertas: bool = False) -> list[Fila]:
        with self._uow.transacao() as tx:
            filas = tx.filas.listar()
            return [f for f in filas if f.estado is EstadoFila.ABERTA] if apenas_abertas else filas

    def obter_fila(self, fila_id: UUID) -> Fila:
        with self._uow.transacao(UUID(str(fila_id))) as tx:
            return obter_fila(tx, UUID(str(fila_id)))

    def encerrar_fila(self, fila_id: UUID, quando: datetime | None = None) -> Fila:
        fila_id = UUID(str(fila_id))
        agora = validar_instante(quando or datetime.now(timezone.utc))
        with self._uow.transacao(fila_id) as tx:
            fila = obter_fila(tx, fila_id)
            garantir_dia(tx, fila, agora)
            cancelar_pendentes(tx, fila, agora, "encerramento_administrativo")
            fila.encerrar(agora)
            return tx.filas.salvar(fila)

    def reabrir_fila(self, fila_id: UUID, quando: datetime | None = None) -> Fila:
        fila_id = UUID(str(fila_id))
        agora = validar_instante(quando or datetime.now(timezone.utc))
        with self._uow.transacao(fila_id) as tx:
            fila = obter_fila(tx, fila_id)
            garantir_dia(tx, fila, agora)
            fila.reabrir()
            return tx.filas.salvar(fila)
