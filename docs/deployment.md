# Deployment

How to run OpsMind on your own server or machine. This is for the person
hosting the system, not day-to-day restaurant users.

## What runs

`docker-compose.yml` orchestrates two services:

- **db** — PostgreSQL 15 (data persists in a named volume `postgres_data`).
- **api** — the FastAPI backend (serves the REST API on port 8000).

The **frontend** (Next.js) runs separately — see [`frontend/README.md`](../frontend/README.md).

## 1. Prerequisites

- Docker and Docker Compose installed.
- API keys ready: an **Anthropic** key (or gateway auth token) for AI, and an
  **OpenWeather** key for weather-aware tips.

## 2. Configure environment

```bash
cp .env.example .env
```

Then edit `.env` and set **real** values:

- `DB_PASSWORD` — a strong password (12+ chars). Also update it inside
  `DATABASE_URL`.
- `SECRET_KEY` — generate one:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- `ANTHROPIC_API_KEY` — from https://console.anthropic.com/ (or set
  `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL` for an Anthropic-compatible
  gateway).
- `OPENWEATHER_API_KEY` — from https://openweathermap.org/.
- `CORS_ORIGINS` — the URL(s) your frontend is served from.

> **Never commit `.env`.** It is gitignored. See the security checklist at the
> bottom of `.env.example`.
>
> **Data privacy note:** if you point `ANTHROPIC_BASE_URL` at a third-party
> proxy, every prompt (including your sales/cost/customer data) and your auth
> token go to that endpoint. Only use an endpoint you trust and control.

## 3. Start

```bash
docker compose up -d --build
```

The database schema is created automatically on first startup (no manual
migration step for a fresh database).

## 4. Verify

```bash
curl http://localhost:8000/health      # should return 200 / {"status":"healthy"}
```

Interactive API docs: open **http://localhost:8000/docs**.

> **Known cosmetic issue:** `docker ps` may show the api container as
> "unhealthy" because the container's healthcheck calls `curl`, which isn't
> installed inside the image. The app still serves fine — confirm with the
> `curl http://localhost:8000/health` command above from your host.

## 5. Frontend

```bash
cd frontend
npm install
npm run dev        # development
# or: npm run build && npm start   # production
```

Point the frontend at the API base URL and make sure that origin is listed in
`CORS_ORIGINS`. See [`frontend/README.md`](../frontend/README.md) for details.

## 6. (Optional) Demo data

To explore with a pre-filled restaurant, run the seed script
(`scripts/seed_data.py`) against the database. Do **not** run it against a
production database with real restaurants.

## Common operations

```bash
docker compose logs -f api     # tail API logs
docker compose down            # stop (data is preserved in the volume)
docker compose up -d --build api   # rebuild just the API after code changes
```

## Production checklist

- Serve everything over **HTTPS** (tokens and cookies must be encrypted in
  transit).
- Strong `DB_PASSWORD` and `SECRET_KEY`; rotate periodically.
- `DEBUG=false`.
- Restrict `CORS_ORIGINS` to your real frontend domain(s).
- Back up the `postgres_data` volume.
- See [security.md](security.md) for the full model.
