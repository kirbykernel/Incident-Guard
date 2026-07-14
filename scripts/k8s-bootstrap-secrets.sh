#!/bin/sh
# Cria os Secrets imperativos do IncidentGuard — valores gerados, nunca versionados.
set -e
kubectl create secret generic postgres-credentials --namespace incidentguard \
 --from-literal=POSTGRES_USER=incidentguard \
 --from-literal=POSTGRES_DB=incidentguard \
 --from-literal=POSTGRES_PASSWORD="$(openssl rand -base64 24)"
kubectl create secret generic backend-secrets --namespace incidentguard \
 --from-literal=JWT_SECRET_KEY="$(openssl rand -hex 32)" \
 --from-literal=ALERTMANAGER_API_KEY="$(openssl rand -hex 24)" \
 --from-literal=SECURITY_SCANNER_API_KEY="$(openssl rand -hex 24)" \
 --from-literal=FALCO_API_KEY="$(openssl rand -hex 24)"
