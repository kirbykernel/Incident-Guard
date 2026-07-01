# ============================================================
# IncidentGuard — Backend Dockerfile
# Multi-stage build: imagem final mínima, usuário não-root.
# Stage 1 (builder): instala dependências com pip
# Stage 2 (runtime): copia apenas o necessário, sem ferramentas de build
# ============================================================

# ---- Stage 1: builder ----
FROM python:3.12-slim AS builder

WORKDIR /build

# Instala dependências de build (removidas no stage final)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python em um diretório isolado
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---- Stage 2: runtime ----
FROM python:3.12-slim AS runtime

# Metadados da imagem
LABEL org.opencontainers.image.title="IncidentGuard API"
LABEL org.opencontainers.image.description="API de monitoramento de incidentes — backend FastAPI"
LABEL org.opencontainers.image.source="https://github.com/seu-usuario/incidentguard"

WORKDIR /app

# Instala apenas dependências de runtime do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copia pacotes Python instalados no stage builder
COPY --from=builder /install /usr/local

# Cria usuário não-root (princípio do menor privilégio)
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home --shell /bin/false appuser

# Copia código da aplicação
COPY --chown=appuser:appgroup app/ ./app/

# Sem root a partir daqui
USER appuser

# Expõe apenas a porta necessária
EXPOSE 8000

# Health check para Kubernetes liveness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Inicia com uvicorn (sem reload em produção)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
