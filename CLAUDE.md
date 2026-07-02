# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

IncidentGuard is a cloud-native incident monitoring platform: it ingests alerts from Prometheus/Alertmanager,
security scanners (Trivy, Gitleaks, OPA/Gatekeeper), and Falco (runtime security), normalizes them into
`Incident` records, and exposes them through an API and (planned) React dashboard.

**Project state**: the backend API is implemented; the frontend is scaffolded only (Dockerfile + nginx config
+ empty `src/{components,hooks,pages,services}` dirs, no `package.json` yet); `k8s/backend`, `k8s/frontend`,
`k8s/postgres`, `k8s/security/{falco,opa}`, `infra/terraform`, `docs/uml`, and `.github/workflows` exist as
empty directories reserved for future work. There are no tests beyond an empty `backend/tests/__init__.py`,
no lint/format config, and no Alembic migrations set up yet (despite `alembic` being in requirements.txt and
referenced in comments — the app currently creates tables via `Base.metadata.create_all` on startup, see
`backend/app/main.py`'s `lifespan`).

Code comments and docstrings throughout the backend are written in Portuguese; match that convention when
editing existing files.

## Commands

### Local dev environment (full stack via Docker)

```bash
cp .env.example .env        # fill in real secrets first — see Settings validation below
docker compose up -d        # starts postgres, backend, frontend, prometheus, alertmanager, grafana, loki
docker compose logs -f
docker compose down -v      # tear down containers + volumes
```

Service ports: backend `8000`, frontend `3000`, postgres `5432`, prometheus `9090`, alertmanager `9093`,
grafana `3001`, loki `3100`. The backend container mounts `./backend/app` read-only for hot reload in dev.

### Backend (FastAPI), run outside Docker

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

There is no pytest/ruff/black config in the repo yet — if adding tests or lint tooling, add the corresponding
dev dependency and config file rather than assuming one exists.

### Frontend

Not yet scaffolded beyond `Dockerfile`/`nginx.conf`. The Dockerfile expects a Vite React app (`npm ci`,
`npm run build` → `dist/`) and `VITE_API_BASE_URL` env var pointing at the backend — set these up before
adding frontend code.

## Architecture

### Backend layout (`backend/app/`)

- `main.py` — FastAPI app factory: CORS, Prometheus instrumentation exposed at `/metrics`
  (`prometheus-fastapi-instrumentator`), a global exception handler that never leaks internals, `/health`,
  and router registration under `/api/v1`.
- `core/settings.py` — single `Settings` (pydantic-settings) object read from `.env`, cached via
  `get_settings()` (`@lru_cache`). Fails fast at startup if `JWT_SECRET_KEY` is short/default or `API_ENV`
  is invalid — required env vars have no defaults, so a missing one crashes on import.
- `core/database.py` — async SQLAlchemy engine/session. `DATABASE_URL` from settings is a sync-style
  `postgresql://` URL rewritten to `postgresql+asyncpg://` here. `get_db()` is the FastAPI dependency:
  commits on success, rolls back on exception.
- `core/security.py` — bcrypt password hashing, JWT create/decode (`pyjwt`), and two auth mechanisms that
  must not be conflated:
  - **Human users**: `Authorization: Bearer <JWT>` via `get_current_user_id`/`get_current_user_role`.
  - **Machine webhook senders**: `X-API-Key` header checked per-source (`alertmanager`, `security_scanner`,
    `falco`) against settings-configured keys — see `verify_api_key` and each webhook route's
    `_validate_api_key` check.
- `models/models.py` — SQLAlchemy ORM models mirroring a UML class diagram (intended to live under
  `docs/uml/`, currently empty): `User`, `Incident`, `APIKey`, `WebhookEvent`, plus `Role`/`Severity`/
  `Status`/`Source` enums. `Incident.source` records provenance; `WebhookEvent` stores the raw payload and
  links back to the `Incident` it produced (nullable — not every webhook creates one).
- `schemas/schemas.py` — Pydantic v2 request/response contracts, intentionally decoupled from the ORM models
  (never return a SQLAlchemy model directly from a route).
- `routes/auth.py`, `routes/incidents.py`, `routes/webhooks.py` — one router per domain, each mounted under
  `/api/v1` in `main.py`.

### Webhook ingestion pattern (`routes/webhooks.py`)

Each of the three webhook endpoints (`/webhooks/alertmanager`, `/webhooks/security`, `/webhooks/falco`)
follows the same shape: validate `X-API-Key` for that source → map the source's own severity/priority
vocabulary onto the shared `Severity` enum → conditionally create an `Incident` (Alertmanager only for
`firing` alerts; security scanner only for `CRITICAL`/`HIGH`; Falco always) → always persist a `WebhookEvent`
with the raw payload, linked to the incident if one was created. When adding a new alert source, follow this
same validate → map-severity → conditionally-create-incident → always-record-event structure.

### Infra / monitoring stack

`docker-compose.yml` wires Prometheus → Alertmanager → backend webhook, plus Grafana reading from Prometheus
and Loki. Config for these lives under `k8s/monitoring/{prometheus,grafana,loki}/` and is mounted read-only
into the containers even in the Docker Compose (non-k8s) dev flow. Docker images are pinned by digest
(`image@sha256:...`) — when bumping a version, update the digest too, not just the tag (Dependabot,
configured in `.github/dependabot.yml`, tracks these).

Both `Dockerfile`s are multi-stage (builder → runtime), run as non-root users, and expose a `/health`
endpoint used by the compose healthchecks — keep new services consistent with that pattern.
