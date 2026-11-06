# Step 9: truthful analytics and UI

Completed 23 October 2026 on the existing `hardening` branch.

Dashboard and Sales now use recorded INR sales, order counts and current menu
costs. Gross profit is labelled as an estimate, excluding operating expenses.
Changes compare the preceding equal-length period; growth is unavailable when
the previous amount is zero. Hourly sales use 24 UTC buckets with half-open
date boundaries. The dashboard no longer displays invented confidence or staff
efficiency scores. Sales no longer displays hardcoded USD totals.

Insights uses tenant-scoped recommendation counts and pending records, including
the configured tenant Claude model. Counts cover all records rather than the
first page. Unmeasured confidence and ROI cards were removed. Empty tenants
receive zero values or empty states, and do not trigger the AI briefing call.
The briefing component no longer substitutes a positive assessment when the
response contains no assessment. The top-items chart no longer invents margins.

Model performance reads only `reports/<tenant_id>/backtest.csv`. Shared sample
reports are never used, including for tenant 1. Missing, zero-byte and
header-only reports return 404; existing HTTP errors retain their status.
Top-item and daily-cost joins also constrain sales and menu items by tenant.

Removed the `/components` gallery route and updated README and environment
documentation from Gemini to Claude. Current model-ID validation and AI client
safety remain scheduled for Step 12.

## Verification

| Check | Result |
| --- | --- |
| Final full backend suite on SQLite | 250 passed, 2 PostgreSQL-only checks skipped; 160.98 seconds |
| New truthful-analytics regression tests, SQLite | 12 passed |
| Same new regression tests, PostgreSQL 18.6 | 12 passed |
| Earlier combined input-limit and analytics checks, PostgreSQL | 48 passed |
| Analytics and staffing portability checks, PostgreSQL | 22 passed |
| Production frontend build | Passed |
| TypeScript `--noEmit` | Passed |
| ESLint for changed pages, hook, API helper and chart/briefing components | Passed |
| Pyflakes for new reporting service and regression tests | Passed |
| `git diff --check` | Passed |
| Production HTTP smoke check | `/`, `/sales`, `/insights`: 200; `/components`: 404 |

Regression coverage includes empty tenants, INR amounts and costs, previous-period
changes, missing growth baselines, hourly date boundaries, cross-tenant exclusion,
report isolation and empty reports, actual report averages, counts exceeding 200
records, recorded recommendation statuses, tenant model settings, staff denial
and invalid dates. PostgreSQL tests used temporary schemas in the isolated local
cluster; zero test schemas remained afterward. Temporary frontend and database
servers were stopped.

Browser rendering and authenticated browser interactions remain unverified because
the browser-control surface is unavailable in this session. HTTP checks do not
verify client rendering. Live Anthropic calls and hosted CI were not exercised.
Full-repository ESLint cleanup remains Step 14; the changed files were checked.
Step 10 has not been started. Changes remain uncommitted.
