import asyncio
from sqlalchemy.ext.asyncio import async_engine_from_config
from logging.config import fileConfig

from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 你的原有模型元数据导入完全保留，不用任何修改
from app.db.database import Base
import app.db.models

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式生成纯SQL脚本，不需要连接数据库，完全兼容异步配置"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # 自动识别字段类型差异，避免漏生成字段变更
        compare_type=True
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """在同步上下文里实际执行迁移逻辑，被异步连接调用"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True  # 全局开启字段差异识别
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """异步创建引擎、连接数据库执行迁移，是核心异步逻辑"""
    configuration = config.get_section(config.config_ini_section, {})
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # 迁移场景禁用连接池，执行完直接销毁
    )

    async with connectable.connect() as connection:
        # 把异步连接包装成同步上下文执行迁移
        await connection.run_sync(do_run_migrations)

    # 迁移完成后安全销毁异步引擎，彻底释放所有连接
    await connectable.dispose()


def run_migrations_online() -> None:
    """把异步执行包装成同步入口，适配Alembic的启动流程"""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
