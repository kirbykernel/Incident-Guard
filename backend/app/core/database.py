# ============================================================
# IncidentGuard — configuração do banco de dados
# SQLAlchemy com sessão assíncrona (async/await).
# Cada requisição HTTP recebe sua própria sessão,
# garantindo isolamento de transações.
# ============================================================

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.settings import get_settings

settings = get_settings()

# Converte URL síncrona para assíncrona
# postgresql://... → postgresql+asyncpg://...
DATABASE_URL_ASYNC = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

engine = create_async_engine(
    DATABASE_URL_ASYNC,
    echo=not settings.is_production,   # loga SQL em dev, silencia em produção
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,                # valida conexão antes de usar
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Classe base para todos os models SQLAlchemy."""
    pass


async def get_db() -> AsyncSession:
    """
    Dependência FastAPI — injeta sessão de banco na rota.
    Garante commit em sucesso e rollback em exceção.

    Uso:
        @router.get("/")
        async def list(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise