"""Migrações usam a mesma configuração por ambiente da API."""

from logging.config import fileConfig

from alembic import context

from gestao_compartilhada.configuracao import criar_engine_postgres, url_postgres
from gestao_compartilhada.postgres.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=url_postgres(), target_metadata=target_metadata,
        literal_binds=True, dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        executar_migracoes(connection)
        return
    engine = criar_engine_postgres()
    try:
        with engine.connect() as connection:
            executar_migracoes(connection)
    finally:
        engine.dispose()


def executar_migracoes(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
