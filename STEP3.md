# Step 3 — authentication hardening

## Behavior

- Login reserves attempts atomically against both the direct client IP and a
  normalized account key: five failed/in-flight attempts per five minutes.
  The sixth attempt gets 429 and a `Retry-After` header. Successful logins release
  only their own reservation; they cannot clear other failed attempts.
- Registration is limited to five requests per hour per IP/account; refresh to
  30 per minute per IP; password changes and logout-all to five per five minutes
  per IP/user. Unauthenticated, invalid credentials receive the same login error.
- Unknown emails still run a real Argon2 verification against a process-local
  dummy hash. Generic registration text is shared by success and duplicate
  responses and never includes the supplied email. Registration retains its
  existing immediate token-issuance contract: success status/payload still differ
  from rejection, so it is **not a fully opaque registration flow**. Completely
  hiding account existence requires an out-of-band verification flow.
- Access tokens default to 15 minutes. A user's integer `token_version` is
  embedded in issued access and refresh JWTs. Missing, malformed or stale versions
  are rejected; tenant claims are checked as well.
- Password changes, role/status changes and `POST /api/v1/auth/logout-all`
  increment the version and revoke refresh tokens in the same transaction.
  Password changes issue a replacement pair; logout-all invalidates the caller
  too. Unchanged team-member updates do not revoke sessions.
- Refresh validates signed JWT claims and stored-token state. Conditional
  revocation makes each token single-use; a PostgreSQL user-row lock coordinates
  refresh with account revocation. This path does not commit between consuming
  the old token and issuing the replacement.
- Temporary-password users receive 403 `password change required` on protected
  HTTP routes except `/auth/change-password`, `/auth/logout` and `/auth/me`.
  Public login/refresh can issue tokens, but those tokens remain subject to this
  restriction. Changing the password clears the restriction; old tokens fail.
- WebSocket connection authentication now checks the tenant, token version,
  active status and temporary-password flag. Existing open sockets are not
  disconnected by session revocation in this step; their lifecycle, route and
  token transport changes remain in Step 6.

## Deployment and migration

- Set `ACCESS_TOKEN_EXPIRE_MINUTES=15` in existing environments too; an explicit
  older `.env` setting overrides the new application and Compose defaults.
- Set `REDIS_URL` for shared counters. Redis Lua checks/increments all relevant
  keys atomically and gives them TTLs. Redis outages return 503; the application
  does not silently fall back to independent memory counters. Keys contain HMAC
  digests rather than email addresses or raw IPs.
- Without Redis, use one process. The memory store expires old windows on
  periodic request-time cleanup, has a hard `RATE_LIMIT_MAX_KEYS` capacity
  (default 10000), and refuses new keys at capacity instead of evicting lockouts.
- Docker/Gunicorn now defaults to `WEB_CONCURRENCY=1`; settings reject a larger
  configured value without Redis. An explicit CLI worker count must match this
  environment setting. Redis WebSocket fanout and scheduler process isolation
  remain deployment work in Steps 6 and 11.
- Start Uvicorn with `--no-proxy-headers`. Docker's Gunicorn command disables
  its forwarded-peer processing, and `python -m app.main` disables Uvicorn's
  proxy processing. This preserves the actual network peer for the application
  limiter. Set `TRUSTED_PROXIES` to the actual trusted proxy IPs/CIDRs, e.g.
  `["10.0.0.10/32"]`; the application walks X-Forwarded-For right to left and
  stops at the first untrusted hop. Unknown/malformed chains are ignored.
- Application startup adds `users.token_version INTEGER NOT NULL DEFAULT 0`
  only when missing. It preserves existing users and is idempotent. PostgreSQL
  startup runs it under the existing advisory DDL lock. Existing JWTs without
  a version require signing in again. Formal migrations are planned in Step 4.
- Ordinary logout continues to revoke its refresh token; use logout-all to
  invalidate every access/refresh session immediately for subsequent requests.

## Verification

The three initial regression tests failed before implementation (spoofed login
headers evaded 429, the pre-change token still returned 200, and the temporary
user reached the sales handler). They now pass. The sales case additionally
seeds a valid menu item and proves 403 before the password change and 201 after.

Focused tests cover proxy chains, per-account lockouts across IPs, every new
limit, temporary-password restrictions, old access/refresh tokens, reactivation,
logout-all, malformed versions, dummy verification and existing-schema migration.
Redis concurrency tests execute the real Lua scripts using fakeredis with Lua
support and two independent store instances; no live Redis server is required.
The existing SQLite schema migration is exercised twice against real SQL.

Final checks on Windows/Python 3.14 in `.venv-step2`:

| Check | Result |
| --- | --- |
| Focused new auth/rate-limit/migration cases | 30 passed |
| `python scripts/verify_test_isolation.py` | 135 passed twice (58.29s, 69.07s); artifact hashes and Git status unchanged after each run |
| `python -m pip_audit -r requirements.txt --progress-spinner off` | No known vulnerabilities found |
| `python -m pip check` | No broken requirements |
| Flake8 F checks on changed auth/config/database modules and new tests | Pass |
| `docker compose config --quiet` | Pass |
| `git diff --check` | Pass |

PostgreSQL and a live Redis deployment were not exercised locally. No frontend
code changed in Step 3; the frontend lint findings recorded in Step 2 remain.

Reference: [Redis atomic rate-limiter guidance](https://redis.io/docs/latest/commands/incr/).
