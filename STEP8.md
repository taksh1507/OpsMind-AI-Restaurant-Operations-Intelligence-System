# Step 8: staffing and database portability

Staffing calculations now query tenant-scoped shifts and sales using portable
SQL and bucket them in Python. Removed unused SQLite-only queries and the
invalid `func.cast(..., Decimal)` expression. Labor uses Decimal arithmetic
and exact overlap seconds, clipped to each UTC hour. Overnight shifts,
partial hours, shifts spanning a whole day and microsecond sales boundaries
are handled without lazy-loading staff. Each hour rounds to cents; daily labor
is the sum of those rounded hourly costs. Invalid reversed shifts are excluded.

Days use an inclusive midnight start and exclusive next-midnight end. Missing
shifts return a helpful 404 even when sales exist; invalid dates retain 400.
Forecast-day bounds return 422 instead of silently clamping. Optional forecast
history is ordered chronologically and exceptions are logged.

The new `utc_date` SQL expression uses PostgreSQL `date(timezone('UTC', ...))`
and SQLite `date(...)`, returning Python `date` values on both. Applied it to
daily analytics, forecast features, briefing/forecast history and sustainability
month/year extraction. Public daily analytics normalize date keys to ISO text;
training features retain their documented Python date values. Fixed the unused
daily-revenue helper's scalar-versus-row iteration while verifying its dates.

The analytics module also reset its router after registering sustainability,
silently removing that endpoint. Removed the second reset so sustainability is
registered and keeps the same manager/owner protection as other analytics.

CI now runs the suite in SQLite and PostgreSQL matrix jobs using a health-checked
PostgreSQL 18 service and the isolated-schema `TEST_DATABASE_URL` fixture. No
live AI secret is passed to tests. Explicit SQLite-only tests keep that dialect
in both jobs; shared database fixtures and the new portability tests use the
selected database. Hosted GitHub Actions execution has not been triggered here.

## Verification

- Step 8 focused tests: 11 passed on SQLite (27.81s), 11 on PostgreSQL 18.6
  (29.58s). Covers exact fractional/overnight costs, tenant isolation, boundaries,
  200 staffing responses with real seeded database records and mocked AI,
  missing-shift 404, invalid input, staff 403, chronological forecast history,
  UTC date/month grouping under `Pacific/Honolulu`, daily services and ML dates.
- CI YAML parses and its matrix, health check and database URL checks pass.
- Scoped Flake8 F checks and `git diff --check` pass. No frontend code changed.
- Live Anthropic calls remain untested. Application databases were not migrated;
  PostgreSQL checks use only temporary schemas in the isolated test cluster.

Full regression results:

| Check | Result |
| --- | --- |
| PostgreSQL 18.6 full suite | 240 passed in 310.77s |
| SQLite artifact-isolation replay 1 | 238 passed, two PostgreSQL-only checks skipped in 298.01s |
| SQLite artifact-isolation replay 2 | 238 passed, two PostgreSQL-only checks skipped in 151.57s |

Artifact hashes and Git status were unchanged after each SQLite replay. Scoped
lint, compilation and CI YAML checks passed. Temporary PostgreSQL schemas were
removed (zero remained) and the isolated server was stopped. Hosted CI and
live Anthropic execution remain unverified; database-backed endpoint tests
mock only the AI responses.
