# ============================================================
# IncidentGuard — env.py do Alembic
#
# Script que o Alembic executa em todo comando (upgrade, revision,
# etc). Responsabilidades:
#   1. montar a URL do banco a partir do Settings da aplicação
#      (mesma fonte de verdade do runtime — nada de URL duplicada)
#   2. expor Base.metadata para o --autogenerate poder comparar
#      os models com o banco real e gerar o diff
#   3. adaptar o engine assíncrono (asyncpg) ao núcleo síncrono
#      do Alembic via run_sync — mesmo padrão do lifespan da app
# ============================================================

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.database import Base
from app.core.settings import get_settings

# Importa os models pelo efeito colateral: registrar as tabelas
# no Base.metadata. Sem isso o autogenerate veria um metadata vazio
# e geraria uma migration que DROPA tudo.
from app.models import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL vem do .env via Settings — convertida para o driver async,
# como em core/database.py
settings = get_settings()
config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
)

# O que o autogenerate usa como "estado desejado" do schema
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Modo offline: gera o SQL sem conectar no banco (alembic upgrade
    head --sql). Útil para ambientes onde o DDL precisa ser revisado
    ou aplicado por um DBA.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Cria engine async e delega ao núcleo síncrono do Alembic."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Modo online: conecta no banco e aplica as migrations."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
