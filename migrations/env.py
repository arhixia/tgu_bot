from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
import asyncio
from alembic import context
from src.db.models import User, Group, Theme, Task, Answer 
from src.db.config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER
from src.db.database import Base


config = context.config
section = config.config_ini_section
config.set_section_option(section,"DB_HOST",DB_HOST)
config.set_section_option(section,"DB_USER",DB_USER)    
config.set_section_option(section,"DB_PASS",DB_PASS)
config.set_section_option(section,"DB_NAME",DB_NAME)
config.set_section_option(section,"DB_PORT",DB_PORT)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata



def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
