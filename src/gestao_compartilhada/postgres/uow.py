"""Uma Session por transação; o banco sincroniza processos e instâncias da API."""

from contextlib import contextmanager
from dataclasses import asdict, fields
from typing import Iterator
from uuid import UUID

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from gestao_compartilhada.domain import TransicaoSenha
from gestao_senhas.domain import SenhaChamada

from .models import EventoOutboxModelo, FilaModelo, TransicaoModelo
from .repositories import RepositorioDeFilasPostgres, RepositorioDeSenhasPostgres
from .registros import HistoricoPostgres, NotificacoesPostgres, OutboxPostgres


class TransacaoPostgres:
    def __init__(self, session: Session) -> None:
        self._session = session
        self.filas = RepositorioDeFilasPostgres(session)
        self.senhas = RepositorioDeSenhasPostgres(session)
        self.historico = HistoricoPostgres(session)
        self.outbox = OutboxPostgres(session)
        self.notificacoes = NotificacoesPostgres(session)

    def registrar_transicao(self, transicao: TransicaoSenha) -> None:
        self._session.add(TransicaoModelo(**asdict(transicao)))
        self._session.flush()

    def registrar_evento(self, evento: SenhaChamada) -> None:
        self._session.add(EventoOutboxModelo(**asdict(evento)))
        self._session.flush()


class UnidadeDeTrabalhoPostgres:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._sessions = sessionmaker(engine, expire_on_commit=False, close_resets_only=False)

    @contextmanager
    def transacao(self, fila_id: UUID | None = None) -> Iterator[TransacaoPostgres]:
        with self._sessions() as session, session.begin():
            if fila_id is None:
                # Namespace fixo da aplicação. Serializa a verificação casefold +
                # criação de nomes também quando ainda não há linha para bloquear.
                session.execute(text("SELECT pg_advisory_xact_lock(640, 1)"))
            else:
                # Adquirir ANTES de carregar entidades/contador. Em READ COMMITTED,
                # quem esperou o bloqueio verá o commit da chamada anterior.
                session.execute(
                    select(FilaModelo.id).where(FilaModelo.id == fila_id).with_for_update()
                )
            yield TransacaoPostgres(session)
            # begin() confirma na saída e reverte também falhas de flush/commit.

    @property
    def historico(self) -> tuple[TransicaoSenha, ...]:
        with self._sessions() as session:
            modelos = session.scalars(select(TransicaoModelo).order_by(TransicaoModelo.ordem))
            return tuple(TransicaoSenha(**{
                campo.name: getattr(m, campo.name) for campo in fields(TransicaoSenha)
            }) for m in modelos)

    @property
    def eventos(self) -> tuple[SenhaChamada, ...]:
        with self._sessions() as session:
            modelos = session.scalars(select(EventoOutboxModelo).order_by(EventoOutboxModelo.ordem))
            return tuple(SenhaChamada(
                id=m.id, senha_id=m.senha_id, fila_id=m.fila_id, chamada_em=m.chamada_em,
            ) for m in modelos)
