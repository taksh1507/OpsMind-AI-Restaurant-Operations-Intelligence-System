# Deployment

The Compose deployment runs PostgreSQL, Redis, an Alembic migration job, the
FastAPI API, one model-retraining scheduler process, and the Next.js frontend.
PostgreSQL and Redis are private to the Compose network; the API and frontend
ports are published to the host.

## Configure

Copy `.env.example` to `.env`, then set a strong `DB_PASSWORD`, update the
credentials in `DATABASE_URL` (URL-encode reserved characters), a random
`SECRET_KEY` of at least 32 characters, an Anthropic API key or gateway token,
and the real frontend origin in `CORS_ORIGINS`. Set `NEXT_PUBLIC_API_URL` to
the API address a user's browser can reach, including `/api/v1`. For example,
use `https://api.example.com/api/v1` behind a TLS reverse proxy. Do not use a
Compose-only hostname such as `http://api:8000` for this browser URL.

`ENVIRONMENT` defaults to production and `COOKIE_SECURE` defaults to true.
Local HTTP development can set `ENVIRONMENT=development` and
`COOKIE_SECURE=false`. Configure `WEB_CONCURRENCY` for API workers; values
above one require the Compose Redis service. `DB_POOL_SIZE` and
`DB_MAX_OVERFLOW` size the PostgreSQL pool per worker.

## Start and verify

```sh
docker compose up -d --build
docker compose ps
```

Compose waits for PostgreSQL and Redis health, applies Alembic migrations in a
one-shot job, then starts the API. The API and frontend have Python/Node based
health checks. The scheduler runs once in its own service and shares the
`models_data` and `reports_data` volumes with the API. PostgreSQL and Redis
data use named volumes as well.

```sh
curl http://localhost:8000/health
```

The production API disables `/docs`, `/redoc`, and `/openapi.json`. To stop the
services while retaining persistent data, run `docker compose down`.

## Existing databases

Alembic's initial revision adopts existing tables and creates missing ones.
Installations with the old global-customer schema must first complete the
tenant ownership data migration described in
[`customer-tenant-migration.md`](customer-tenant-migration.md), with writers
stopped. The Alembic revision refuses to start against that legacy schema.

## Operations

```sh
docker compose logs -f api
docker compose logs -f scheduler
docker compose up -d --build api frontend
docker compose down
```

Back up the `postgres_data`, `models_data`, and `reports_data` volumes. Serve
production traffic over HTTPS and restrict `CORS_ORIGINS` to the frontend's
actual origin.
