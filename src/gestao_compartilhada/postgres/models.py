"""Modelo relacional do adaptador; não instrumenta as entidades de domínio."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint,
    Index, Integer, String, UniqueConstraint, Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class FilaModelo(Base):
    __tablename__ = "filas"
    __table_args__ = (
        CheckConstraint("estado IN ('aberta', 'encerrada')", name="ck_filas_estado"),
        CheckConstraint("chamadas_prioritarias_consecutivas >= 0", name="ck_filas_contador"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    nome: Mapped[str] = mapped_column(String)
    nome_normalizado: Mapped[str] = mapped_column(String, unique=True)
    descricao: Mapped[str | None] = mapped_column(String)
    estado: Mapped[str] = mapped_column(String)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    encerrada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    chamadas_prioritarias_consecutivas: Mapped[int] = mapped_column(Integer)
    dia_operacional: Mapped[date]


class SenhaModelo(Base):
    __tablename__ = "senhas"
    __table_args__ = (
        UniqueConstraint("fila_id", "dia_operacional", "tipo", "numero", name="uq_senhas_numero"),
        UniqueConstraint("id", "fila_id", name="uq_senhas_id_fila"),
        CheckConstraint("tipo IN ('normal', 'prioritaria')", name="ck_senhas_tipo"),
        CheckConstraint("canal IN ('online', 'totem')", name="ck_senhas_canal"),
        CheckConstraint(
            "estado IN ('aguardando', 'chamada', 'em_atendimento', 'finalizada', 'cancelada')",
            name="ck_senhas_estado",
        ),
        Index("ix_senhas_selecao", "fila_id", "dia_operacional", "estado", "tipo", "emitida_em", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    fila_id: Mapped[UUID] = mapped_column(ForeignKey("filas.id"))
    numero: Mapped[str] = mapped_column(String)
    tipo: Mapped[str] = mapped_column(String)
    usuario_id: Mapped[str] = mapped_column(String)
    emitida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    canal: Mapped[str] = mapped_column(String)
    estado: Mapped[str] = mapped_column(String)
    dia_operacional: Mapped[date]
    chamada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    atendimento_iniciado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    atendimento_finalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    atendente_id: Mapped[str | None] = mapped_column(String)
    guiche_id: Mapped[str | None] = mapped_column(String)
    motivo_cancelamento: Mapped[str | None] = mapped_column(String)


class ContadorSenhaModelo(Base):
    __tablename__ = "contadores_senhas"
    __table_args__ = (
        CheckConstraint("ultimo_numero >= 0", name="ck_contadores_numero"),
        CheckConstraint("tipo IN ('normal', 'prioritaria')", name="ck_contadores_tipo"),
    )

    fila_id: Mapped[UUID] = mapped_column(ForeignKey("filas.id"), primary_key=True)
    dia_operacional: Mapped[date] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String, primary_key=True)
    ultimo_numero: Mapped[int] = mapped_column(Integer)


class TransicaoModelo(Base):
    __tablename__ = "historico_transicoes"
    __table_args__ = (
        ForeignKeyConstraint(["senha_id", "fila_id"], ["senhas.id", "senhas.fila_id"]),
        Index("ix_historico_senha_quando", "senha_id", "quando", "ordem"),
        Index("ix_historico_fila_ordem", "fila_id", "ordem"),
    )

    ordem: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id: Mapped[UUID] = mapped_column(Uuid, unique=True)
    senha_id: Mapped[UUID] = mapped_column(Uuid)
    fila_id: Mapped[UUID] = mapped_column(Uuid)
    estado_anterior: Mapped[str | None] = mapped_column(String)
    estado: Mapped[str] = mapped_column(String)
    quando: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atendente_id: Mapped[str | None] = mapped_column(String)
    guiche_id: Mapped[str | None] = mapped_column(String)
    motivo: Mapped[str | None] = mapped_column(String)


class EventoOutboxModelo(Base):
    __tablename__ = "outbox"
    __table_args__ = (
        ForeignKeyConstraint(["senha_id", "fila_id"], ["senhas.id", "senhas.fila_id"]),
        Index("ix_outbox_pendentes", "processado_em", "ordem"),
        CheckConstraint("tentativas >= 0", name="ck_outbox_tentativas"),
    )

    ordem: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id: Mapped[UUID] = mapped_column(Uuid, unique=True)
    tipo: Mapped[str] = mapped_column(String, default="SenhaChamada", server_default="SenhaChamada")
    senha_id: Mapped[UUID] = mapped_column(Uuid)
    fila_id: Mapped[UUID] = mapped_column(Uuid)
    chamada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tentativas: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    processado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ultimo_erro: Mapped[str | None] = mapped_column(String)
    reservado_ate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TentativaNotificacaoModelo(Base):
    __tablename__ = "tentativas_notificacao"
    __table_args__ = (
        UniqueConstraint("evento_id", "numero", name="uq_tentativas_evento_numero"),
        CheckConstraint("numero > 0", name="ck_tentativas_numero"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    evento_id: Mapped[UUID] = mapped_column(ForeignKey("outbox.id"))
    numero: Mapped[int] = mapped_column(Integer)
    iniciada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finalizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    erro: Mapped[str | None] = mapped_column(String)


class NotificacaoSimuladaModelo(Base):
    __tablename__ = "notificacoes_simuladas"

    evento_id: Mapped[UUID] = mapped_column(ForeignKey("outbox.id"), primary_key=True)
    mensagem: Mapped[str] = mapped_column(String)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
