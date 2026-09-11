from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def check_database_connection() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def initialize_database() -> None:
    from app.models import (
        AddressAnalysis,
        AnalysisCandidate,
        AuditLog,
        HumanCorrection,
        Locality,
        LocalityAlias,
        PostOffice,
        User,
        UserSession,
    )

    del (
        AddressAnalysis,
        AnalysisCandidate,
        AuditLog,
        HumanCorrection,
        Locality,
        LocalityAlias,
        PostOffice,
        User,
        UserSession,
    )
    # Refresh database collation version if container/host glibc version changed
    try:
        async with engine.connect() as autocommit_conn:
            await autocommit_conn.execution_options(isolation_level="AUTOCOMMIT")
            await autocommit_conn.execute(text("ALTER DATABASE postal_intelligence REFRESH COLLATION VERSION"))
    except Exception:
        pass

    async with engine.begin() as connection:
        try:
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pass
        await connection.run_sync(Base.metadata.create_all)

    # Seed authoritative master data if database is fresh
    try:
        from app.core.seed import seed_master_data
        async with AsyncSessionLocal() as session:
            await seed_master_data(session)
    except Exception:
        pass


async def dispose_database() -> None:
    await engine.dispose()
