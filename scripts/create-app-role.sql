-- ============================================================
-- IncidentGuard — role de aplicação com privilégio mínimo.
-- A app NÃO conecta como owner: ela lê/escreve LINHAS, nunca altera SCHEMA.
-- Migrations seguem usando o owner (incidentguard).
-- Uso: psql ... -v app_password="$APP_DB_PASSWORD" -f create-app-role.sql
-- ============================================================

-- Login role da aplicação (senha vem de variável psql, nunca do arquivo)
CREATE ROLE incidentguard_app LOGIN PASSWORD :'app_password';

-- Pode conectar e enxergar o schema, mas não criar objetos nele
GRANT CONNECT ON DATABASE incidentguard TO incidentguard_app;
GRANT USAGE   ON SCHEMA   public        TO incidentguard_app;

-- CRUD de linhas nas tabelas que JÁ existem
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO incidentguard_app;

-- CRUCIAL: mesmas permissões para tabelas FUTURAS criadas pelo owner.
-- Sem isto, toda tabela de uma migration futura nasceria inacessível à app.
ALTER DEFAULT PRIVILEGES FOR ROLE incidentguard IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO incidentguard_app;
