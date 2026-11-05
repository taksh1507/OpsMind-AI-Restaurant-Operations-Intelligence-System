# Hardening baseline — 20 October 2026

Branch: `hardening`. Initial tracked working tree was clean; existing untracked
`.claude/`, `.claude-flow/` and `.swarm/` directories were left untouched.

## Checks before changes

- `python -m pytest -q`: exit 2, eight collection errors. The available Python is
  3.14. `anthropic` is missing, and importing SciPy's `_ppoly` fails because
  Windows Application Control blocks its DLL. No tests executed.
- `npm run lint` in `frontend/`: exit 1, 12 errors and 6 warnings.
- `npx --no-install tsc --noEmit` in `frontend/`: exit 0.

## Step 0 implementation

An automatic function-scoped fixture changes into a fresh temporary directory
for each test, copying only input datasets. All legacy relative `models/`,
`reports/` and `data/` writes therefore go outside the checkout. The forecast
training fixture now has function scope; the sentiment service test trains its
own model instead of depending on a production pickle.

Tenant artifact directories are ignored. Already tracked baseline artifacts
remain tracked; `.gitignore` does not remove them from Git.

## Completed Step 0 verification

The project `.venv` uses Python 3.14 with system packages plus local installs of
Anthropic 1.15.0, SciPy 1.18.1, NumPy 2.5.4, pytest 9.1.1 and pytest-asyncio
1.4.0. Installing the SciPy wheel locally resolved its import failure without
changing Windows policy. The repository's dependency pins remain unchanged;
this verification uses the installed environment, not the pinned requirements.
Test fixtures disable Anthropic credentials from the environment and settings,
so local `.env` credentials cannot trigger paid requests.

- `.venv\Scripts\python.exe -m pytest -q`: 54 passed in 35.21 seconds.
- `.venv\Scripts\python.exe scripts/verify_test_isolation.py`: passed.
  Full run 1: 54 passed in 35.30 seconds; full run 2: 54 passed in
  36.45 seconds. SHA-256 hashes of all files in `models/`, `reports/` and
  `data/`, plus complete Git porcelain status, were identical before and after
  each run. Existing working changes and user-owned untracked folders remain;
  tests introduce no additional changes.
- The focused isolation test also passed twice.
- Frontend checks were repeated: TypeScript passes; ESLint still reports the
  baseline 12 errors and 6 warnings (later audit steps address these).
- `git diff --check`: passed.

Step 0 is verified. Run the verification script again after future changes to
repeat both full-suite runs and the artifact/status comparisons.

## Step 1 — production defaults verified

- Non-development environments reject empty, whitespace-only, development-default
  and shorter-than-32-character JWT secrets. Environment names are normalized
  and limited to development, staging and production.
- Production requires Secure refresh cookies and explicitly supplied, non-empty
  CORS origins without wildcards. Checks run at settings loading, application
  creation and lifespan startup. Existing production AI credential validation is
  preserved, including when debug is enabled.
- Production disables `/docs`, `/redoc` and `/openapi.json`; the welcome response
  no longer advertises disabled docs.
- Health reports the configured environment, returns 503 for database query or
  connection failures, closes the probe session and keeps error details in logs.
- Compose defaults to production and Secure cookies, and no longer publishes
  PostgreSQL to the host. `.env.example` documents these settings.

Final checks:

- `.venv\Scripts\python.exe scripts/verify_test_isolation.py`: **passed**.
  Full run 1: **95 passed in 38.30 seconds**; full run 2: **95 passed in
  40.42 seconds**. Artifact hashes and Git status remained unchanged after
  each run. The suite includes 41 production configuration/health regression
  cases, including subprocess startup failures for empty and short secrets.
- `docker compose config --quiet`: passed. Resolved JSON using `.env.example`
  also confirms production, Secure cookies and no published database port.
  Containers were not started; deployment runtime testing belongs to Step 11.
- Flake8 F checks for changed application modules, new tests, conftest and the
  verification script: passed. `git diff --check`: passed.
- Frontend code was not changed in Step 1; the recorded lint failures remain.

Step 2 is now implemented and verified; see [STEP2.md](STEP2.md) for dependency
versions, audit results, migration checks and remaining development-only issues.

Step 3 is implemented and verified; see [STEP3.md](STEP3.md) for auth behavior,
deployment settings, migration notes and verification results (135 tests passed
twice with unchanged artifact hashes and Git status).

Step 4 is implemented and verified on SQLite; see [STEP4.md](STEP4.md) and the
[customer migration instructions](docs/customer-tenant-migration.md). All 158
tests passed twice with unchanged artifact hashes and Git status. Existing
application databases still need the maintenance migration; PostgreSQL runtime
verification was unavailable locally.
