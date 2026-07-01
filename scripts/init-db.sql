-- ============================================================
-- IncidentGuard — init-db.sql
-- Executado automaticamente na primeira subida do container.
-- As tabelas reais são criadas pelo Alembic (migrations).
-- Este script apenas cria extensões necessárias.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
