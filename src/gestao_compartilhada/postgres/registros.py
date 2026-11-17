"""Persistência das consultas e do processamento posterior da Outbox."""

from dataclasses import asdict, fields

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert

from gestao_compartilhada.domain import TransicaoSenha
from gestao_compartilhada.notificacoes import MensagemOutbox, NotificacaoSimulada, TentativaNotificacao
from gestao_senhas.domain import SenhaChamada

from .models import EventoOutboxModelo, NotificacaoSimuladaModelo, TentativaNotificacaoModelo, TransicaoModelo


def _dominio(tipo, modelo):
    return tipo(**{f.name: getattr(modelo, f.name) for f in fields(tipo)})


def _mensagem(modelo):
    return MensagemOutbox(
        evento=_dominio(SenhaChamada, modelo), tentativas=modelo.tentativas,
        processado_em=modelo.processado_em, ultimo_erro=modelo.ultimo_erro,
        reservado_ate=modelo.reservado_ate,
    )


def _filtros(comando, modelo, fila_id, senha_id):
    if fila_id is not None:
        comando = comando.where(modelo.fila_id == fila_id)
    if senha_id is not None:
        comando = comando.where(modelo.senha_id == senha_id)
    return comando


class HistoricoPostgres:
    def __init__(self, session):
        self._session = session

    def listar(self, fila_id, limite, offset, senha_id=None, estado=None):
        comando = _filtros(select(TransicaoModelo), TransicaoModelo, fila_id, senha_id)
        if estado is not None:
            comando = comando.where(TransicaoModelo.estado == estado)
        modelos = self._session.scalars(comando.order_by(TransicaoModelo.ordem).limit(limite).offset(offset))
        return [_dominio(TransicaoSenha, m) for m in modelos]


class OutboxPostgres:
    def __init__(self, session):
        self._session = session

    def buscar(self, evento_id):
        modelo = self._session.scalar(select(EventoOutboxModelo).where(EventoOutboxModelo.id == evento_id))
        return _mensagem(modelo) if modelo is not None else None

    def salvar(self, mensagem):
        modelo = self._session.scalar(select(EventoOutboxModelo).where(EventoOutboxModelo.id == mensagem.evento.id))
        for campo in ("tentativas", "processado_em", "ultimo_erro", "reservado_ate"):
            setattr(modelo, campo, getattr(mensagem, campo))
        self._session.flush()

    def listar(self, limite, offset, fila_id=None, senha_id=None):
        comando = _filtros(select(EventoOutboxModelo), EventoOutboxModelo, fila_id, senha_id)
        modelos = self._session.scalars(comando.order_by(EventoOutboxModelo.ordem).limit(limite).offset(offset))
        return [_mensagem(m) for m in modelos]

    def listar_pendentes(self, quando, limite):
        modelos = self._session.scalars(select(EventoOutboxModelo).where(
            EventoOutboxModelo.processado_em.is_(None),
            or_(EventoOutboxModelo.reservado_ate.is_(None), EventoOutboxModelo.reservado_ate <= quando),
        ).order_by(EventoOutboxModelo.ordem).limit(limite))
        return [_mensagem(m) for m in modelos]

    def salvar_tentativa(self, tentativa):
        self._session.merge(TentativaNotificacaoModelo(**asdict(tentativa)))
        self._session.flush()

    def buscar_tentativa(self, evento_id, numero):
        modelo = self._session.scalar(select(TentativaNotificacaoModelo).where(
            TentativaNotificacaoModelo.evento_id == evento_id,
            TentativaNotificacaoModelo.numero == numero,
        ))
        return _dominio(TentativaNotificacao, modelo) if modelo is not None else None

    def listar_tentativas(self, evento_id, limite, offset):
        modelos = self._session.scalars(select(TentativaNotificacaoModelo).where(
            TentativaNotificacaoModelo.evento_id == evento_id,
        ).order_by(TentativaNotificacaoModelo.numero).limit(limite).offset(offset))
        return [_dominio(TentativaNotificacao, m) for m in modelos]


class NotificacoesPostgres:
    def __init__(self, session):
        self._session = session

    def registrar(self, notificacao):
        self._session.execute(insert(NotificacaoSimuladaModelo).values(
            evento_id=notificacao.evento_id, mensagem=notificacao.mensagem,
            criada_em=notificacao.criada_em,
        ).on_conflict_do_nothing(index_elements=["evento_id"]))

    def listar(self, limite, offset, fila_id=None, senha_id=None):
        comando = select(NotificacaoSimuladaModelo, EventoOutboxModelo).join(
            EventoOutboxModelo, NotificacaoSimuladaModelo.evento_id == EventoOutboxModelo.id,
        )
        comando = _filtros(comando, EventoOutboxModelo, fila_id, senha_id).order_by(
            NotificacaoSimuladaModelo.criada_em, NotificacaoSimuladaModelo.evento_id,
        ).limit(limite).offset(offset)
        return [NotificacaoSimulada(
            evento_id=n.evento_id, senha_id=e.senha_id, fila_id=e.fila_id,
            mensagem=n.mensagem, criada_em=n.criada_em,
        ) for n, e in self._session.execute(comando)]
