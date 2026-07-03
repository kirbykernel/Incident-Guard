#!/bin/sh
# ============================================================
# IncidentGuard — entrypoint do container backend
#
# Aplica as migrations pendentes antes de subir a API: a app
# assume que o schema existe (main.py não faz mais create_all).
#
# Nota para a fase Kubernetes: com múltiplas réplicas, rodar
# migration no entrypoint de cada pod vira uma corrida — lá isso
# migra para um Job/initContainer que roda uma única vez antes
# do Deployment. No compose (1 réplica) o entrypoint basta.
# ============================================================
set -e

echo "Aplicando migrations do banco (alembic upgrade head)..."
alembic upgrade head

echo "Iniciando a API..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
