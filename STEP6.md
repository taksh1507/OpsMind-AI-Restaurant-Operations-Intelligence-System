# Step 6 and CSV import UI

The new `/import-sales` screen is manager/owner-only, links a downloadable
template and explains stable order IDs, INR subtotal/tax amounts, limits and
retry behavior. Uploads use the authenticated API client and display imported,
matched and skipped counts plus row errors. The browser supplies multipart
boundaries; oversized/non-CSV files are rejected before sending.

WebSockets now connect to the configured API at `/api/v1/ws`; stats are at
`/api/v1/ws/stats`. Authentication is in the first message, with origin,
tenant, active-user, temporary-password and token-version checks. Database
sessions close immediately after lookup. Messages have an event/data/timestamp
envelope; sale item counts represent quantities. A notification outage cannot
fail an already-committed checkout.

Connection/message/idle/send limits, concurrent sends, expiring Redis leases,
Redis pub/sub, token-expiry closure, heartbeat handling and bounded exponential
reconnect are implemented. Without Redis exactly one worker is supported.
Stats expose only the caller's tenant on the current worker. Authentication
pages do not connect. See [protocol and deployment settings](docs/realtime.md).

## Verification

- Focused tests: 16 passed, including sale POST → WebSocket event, initial DB
  release, actual application routing, invalid auth/origin/query credentials,
  inactive and temporary users, expired tokens, timeouts, frame limits,
  tenant/user caps, tenant isolation, slow peers, Redis pub/sub across separate
  managers, commit/notification separation and template consistency.
- Redis tests use fakeredis with Lua; a deployed Redis server and separate
  Gunicorn processes have not been exercised here.
- TypeScript and targeted ESLint on the import page, WebSocket hook and Layout
  passed. Production Next.js build passed, including `/import-sales`.
- The production server returned HTTP 200 for `/import-sales` and the CSV
  download; downloaded headers, payment/tax fields and order grouping checked.
- Scoped backend Flake8 F checks and `git diff --check` passed.
- Full frontend lint still reports 17 errors and six warnings in other files;
  those belong to the later quality/cleanup steps.
- Visual two-tab/browser upload verification is pending: browser inventory was
  empty and the browser tool returned `Browser is not available: iab`.
  Protocol tests do not substitute for that visual check.

Final `scripts/verify_test_isolation.py` results: **212 passed, two skipped**
on both full runs (167.43s and 145.73s). The skipped checks require PostgreSQL.
Artifact hashes and Git status were unchanged after each run. The temporary
production frontend server was stopped and port 3310 has no listener.
