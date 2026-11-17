"""Persistência de filas, senhas, histórico e outbox.

Revision ID: 0001
Revises: nenhuma (revisão inicial)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('filas',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('nome', sa.String(), nullable=False),
    sa.Column('nome_normalizado', sa.String(), nullable=False),
    sa.Column('descricao', sa.String(), nullable=True),
    sa.Column('estado', sa.String(), nullable=False),
    sa.Column('criada_em', sa.DateTime(timezone=True), nullable=False),
    sa.Column('encerrada_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('chamadas_prioritarias_consecutivas', sa.Integer(), nullable=False),
    sa.Column('dia_operacional', sa.Date(), nullable=False),
    sa.CheckConstraint("estado IN ('aberta', 'encerrada')", name='ck_filas_estado'),
    sa.CheckConstraint('chamadas_prioritarias_consecutivas >= 0', name='ck_filas_contador'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('nome_normalizado')
    )
    op.create_table('contadores_senhas',
    sa.Column('fila_id', sa.Uuid(), nullable=False),
    sa.Column('dia_operacional', sa.Date(), nullable=False),
    sa.Column('tipo', sa.String(), nullable=False),
    sa.Column('ultimo_numero', sa.Integer(), nullable=False),
    sa.CheckConstraint("tipo IN ('normal', 'prioritaria')", name='ck_contadores_tipo'),
    sa.CheckConstraint('ultimo_numero >= 0', name='ck_contadores_numero'),
    sa.ForeignKeyConstraint(['fila_id'], ['filas.id'], ),
    sa.PrimaryKeyConstraint('fila_id', 'dia_operacional', 'tipo')
    )
    op.create_table('senhas',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('fila_id', sa.Uuid(), nullable=False),
    sa.Column('numero', sa.String(), nullable=False),
    sa.Column('tipo', sa.String(), nullable=False),
    sa.Column('usuario_id', sa.String(), nullable=False),
    sa.Column('emitida_em', sa.DateTime(timezone=True), nullable=False),
    sa.Column('canal', sa.String(), nullable=False),
    sa.Column('estado', sa.String(), nullable=False),
    sa.Column('dia_operacional', sa.Date(), nullable=False),
    sa.Column('chamada_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('atendimento_iniciado_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('atendimento_finalizado_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('atendente_id', sa.String(), nullable=True),
    sa.Column('guiche_id', sa.String(), nullable=True),
    sa.Column('motivo_cancelamento', sa.String(), nullable=True),
    sa.CheckConstraint("canal IN ('online', 'totem')", name='ck_senhas_canal'),
    sa.CheckConstraint("estado IN ('aguardando', 'chamada', 'em_atendimento', 'finalizada', 'cancelada')", name='ck_senhas_estado'),
    sa.CheckConstraint("tipo IN ('normal', 'prioritaria')", name='ck_senhas_tipo'),
    sa.ForeignKeyConstraint(['fila_id'], ['filas.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('fila_id', 'dia_operacional', 'tipo', 'numero', name='uq_senhas_numero'),
    sa.UniqueConstraint('id', 'fila_id', name='uq_senhas_id_fila')
    )
    op.create_index('ix_senhas_selecao', 'senhas', ['fila_id', 'dia_operacional', 'estado', 'tipo', 'emitida_em', 'id'], unique=False)
    op.create_table('historico_transicoes',
    sa.Column('ordem', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('senha_id', sa.Uuid(), nullable=False),
    sa.Column('fila_id', sa.Uuid(), nullable=False),
    sa.Column('estado_anterior', sa.String(), nullable=True),
    sa.Column('estado', sa.String(), nullable=False),
    sa.Column('quando', sa.DateTime(timezone=True), nullable=False),
    sa.Column('atendente_id', sa.String(), nullable=True),
    sa.Column('guiche_id', sa.String(), nullable=True),
    sa.Column('motivo', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['senha_id', 'fila_id'], ['senhas.id', 'senhas.fila_id'], ),
    sa.PrimaryKeyConstraint('ordem'),
    sa.UniqueConstraint('id')
    )
    op.create_index('ix_historico_senha_quando', 'historico_transicoes', ['senha_id', 'quando', 'ordem'], unique=False)
    op.create_table('outbox',
    sa.Column('ordem', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tipo', sa.String(), server_default='SenhaChamada', nullable=False),
    sa.Column('senha_id', sa.Uuid(), nullable=False),
    sa.Column('fila_id', sa.Uuid(), nullable=False),
    sa.Column('chamada_em', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tentativas', sa.Integer(), server_default='0', nullable=False),
    sa.Column('processado_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ultimo_erro', sa.String(), nullable=True),
    sa.CheckConstraint('tentativas >= 0', name='ck_outbox_tentativas'),
    sa.ForeignKeyConstraint(['senha_id', 'fila_id'], ['senhas.id', 'senhas.fila_id'], ),
    sa.PrimaryKeyConstraint('ordem'),
    sa.UniqueConstraint('id')
    )
    op.create_index('ix_outbox_pendentes', 'outbox', ['processado_em', 'ordem'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_outbox_pendentes', table_name='outbox')
    op.drop_table('outbox')
    op.drop_index('ix_historico_senha_quando', table_name='historico_transicoes')
    op.drop_table('historico_transicoes')
    op.drop_index('ix_senhas_selecao', table_name='senhas')
    op.drop_table('senhas')
    op.drop_table('contadores_senhas')
    op.drop_table('filas')
