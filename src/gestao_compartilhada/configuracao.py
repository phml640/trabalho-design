"""Seleção do adaptador na borda da aplicação, sem conexão durante o import."""

import os

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine, make_url

from .application import UnidadeDeTrabalho
from .infrastructure import UnidadeDeTrabalhoEmMemoria


def url_postgres() -> URL:
    """DATABASE_URL tem precedência; variáveis separadas dispensam escape da senha."""
    valor = os.getenv("DATABASE_URL")
    url = make_url(valor) if valor else URL.create(
        "postgresql+psycopg",
        username=os.getenv("POSTGRES_USER", "gestao"),
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "gestao_filas"),
    )
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    if url.drivername != "postgresql+psycopg":
        raise ValueError("Use uma conexão PostgreSQL com o driver psycopg.")
    return url


def criar_engine_postgres(url: str | URL | None = None) -> Engine:
    conexao = make_url(url) if url is not None else url_postgres()
    opcoes = conexao.query.get("options", "")
    return create_engine(
        conexao,
        pool_pre_ping=True,
        isolation_level="READ COMMITTED",
        connect_args={"connect_timeout": 10, "options": f"{opcoes} -c timezone=UTC"},
    )


def criar_unidade_de_trabalho() -> UnidadeDeTrabalho:
    adaptador = os.getenv("PERSISTENCIA", "memoria").strip().lower()
    if adaptador == "memoria":
        return UnidadeDeTrabalhoEmMemoria()
    if adaptador == "postgres":
        from .postgres import UnidadeDeTrabalhoPostgres

        return UnidadeDeTrabalhoPostgres(criar_engine_postgres())
    raise ValueError("PERSISTENCIA deve ser memoria ou postgres.")
