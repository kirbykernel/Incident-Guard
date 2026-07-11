# ============================================================
# IncidentGuard — entry point da aplicação FastAPI
# ============================================================

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.database import engine
from app.core.settings import get_settings
from app.routes import auth, incidents, webhooks

settings = get_settings()

logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("incidentguard")


# ----------------------------------------------------------
# Lifecycle
# O schema do banco é responsabilidade das migrations Alembic
# (rodadas antes da app subir — ver entrypoint.sh), não da app.
# ----------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Iniciando IncidentGuard — ambiente: {settings.API_ENV}")
    yield
    logger.info("Encerrando IncidentGuard")
    await engine.dispose()


# ----------------------------------------------------------
# Aplicação
# ----------------------------------------------------------

app = FastAPI(
    title="IncidentGuard API",
    description="Plataforma cloud-native de monitoramento de incidentes",
    version="1.0.0",
    lifespan=lifespan,
    # Em produção, desativa docs públicas
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)


# ----------------------------------------------------------
# Middlewares
# ----------------------------------------------------------


# ----------------------------------------------------------
# Métricas Prometheus
# Expõe /metrics para coleta pelo Prometheus
# ----------------------------------------------------------

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


# ----------------------------------------------------------
# Handler global de erros não tratados
# ----------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erro não tratado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno do servidor"},
    )


# ----------------------------------------------------------
# Rotas base
# ----------------------------------------------------------

@app.get("/health", tags=["health"])
async def health():
    """
    Health check para Kubernetes liveness e readiness probes.
    Retorna 200 se a aplicação está saudável.
    """
    return {
        "status": "healthy",
        "environment": settings.API_ENV,
        "version": "1.0.0",
    }


# ----------------------------------------------------------
# Registro de rotas
# ----------------------------------------------------------

app.include_router(auth.router,      prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(webhooks.router,  prefix="/api/v1")

logger.info("Rotas registradas: /api/v1/auth | /api/v1/incidents | /api/v1/webhooks")
