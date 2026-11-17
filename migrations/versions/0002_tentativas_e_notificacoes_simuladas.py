"""Tentativas e notificações simuladas.

Revision ID: 0002
Revises: 0001
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('notificacoes_simuladas',
    sa.Column('evento_id', sa.Uuid(), nullable=False),
    sa.Column('mensagem', sa.String(), nullable=False),
    sa.Column('criada_em', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['evento_id'], ['outbox.id'], ),
    sa.PrimaryKeyConstraint('evento_id')
    )
    op.create_table('tentativas_notificacao',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('evento_id', sa.Uuid(), nullable=False),
    sa.Column('numero', sa.Integer(), nullable=False),
    sa.Column('iniciada_em', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finalizada_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('erro', sa.String(), nullable=True),
    sa.CheckConstraint('numero > 0', name='ck_tentativas_numero'),
    sa.ForeignKeyConstraint(['evento_id'], ['outbox.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('evento_id', 'numero', name='uq_tentativas_evento_numero')
    )
    op.create_index('ix_historico_fila_ordem', 'historico_transicoes', ['fila_id', 'ordem'], unique=False)
    op.add_column('outbox', sa.Column('reservado_ate', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('outbox', 'reservado_ate')
    op.drop_index('ix_historico_fila_ordem', table_name='historico_transicoes')
    op.drop_table('tentativas_notificacao')
    op.drop_table('notificacoes_simuladas')
