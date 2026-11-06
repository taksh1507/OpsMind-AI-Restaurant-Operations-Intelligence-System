# Step 5: input limits, imports and safe errors

Implemented after verifying Step 4 on an isolated PostgreSQL 18.6 cluster.
No existing application database was changed.

- Checkout validates quantities 1–1,000, 1–100 items, payment enum and tax
  fraction 0–1. Subtotals beyond the database's monetary range return 422.
- Sales, menu, categories, team and recommendations lists enforce limits
  1–200 and nonnegative offsets. Existing top-item limits are validated.
  Sales use `selectinload`, eliminating per-row refresh queries.
- Imports enforce byte/row limits, BOM support, structural validation,
  whole-order rejection, order IDs, preserved payment/tax and persistent
  idempotency. See [CSV format](docs/sales-import.md).
- API exception details no longer interpolate raw exception text. Handled
  failures log tracebacks with a reference; unhandled exceptions return a
  generic 500 with a correlation ID. Debug traceback responses are disabled.
- Executable `print()` calls use module logging. UTC clocks are timezone-aware;
  SQLite timestamps are normalized for shift/customer comparisons.

Tests cover oversized sale payloads returning 422, pagination, file/row/item
limits, distinct equal-total orders, payment/tax persistence, retries and
conflicts, foreign/oversized customer IDs, rollback, concurrent PostgreSQL
workers, debug-mode safe errors and a two-query sales-list assertion.

## Verification on 23 October 2026

| Check | Result |
| --- | --- |
| PostgreSQL 18.6 full regression | 197 passed in 281.69s |
| Final PostgreSQL input/error/import tests | 39 passed in 79.99s, including the final forwarded-service-error assertion |
| SQLite full artifact-isolation replays | 195 passed / 2 skipped, then 196 passed / 2 skipped after adding the forwarded-error regression; artifact hashes and Git status unchanged after both |
| Final SQLite full regression | 196 passed / 2 PostgreSQL-only checks skipped in 216.15s |
| Flake8 F checks on new import/error/time modules and verification tests | Pass |
| `git diff --check` and application compilation | Pass |

The PostgreSQL URL targeted only the separate test cluster on localhost port
55432. Shared database fixtures used per-test PostgreSQL schemas; tests that
explicitly create SQLite engines retained SQLite. Full-project lint cleanup
and warning gates remain in their later audit steps. No frontend code or
runtime dependency versions changed in Step 5.
