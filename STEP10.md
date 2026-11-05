# Step 10: operational data entry

Implemented on `hardening`, 23 October 2026. No application database was
modified during verification; changes remain uncommitted.

Added bounded, tenant-scoped CRUD endpoints for customers, ingredients,
recipes, staff, shifts and waste logs, plus review creation and listing.
Writes require owner or manager permissions. Payroll and operational records
also require those roles for reads; customer reads retain authenticated staff
access. Recipes validate both menu and ingredient ownership; shifts and waste
logs validate their parent ownership on creation and replacement.

Sales accept an optional customer ID and update tax-inclusive spending and
visit counts with atomic SQL increments in the sale transaction. CSV imports
update the same counters within their savepoint; retries do not count twice.
Customer history already queried real tenant-scoped sale items following
Step 4, and is now usable with customer creation and linked checkout.

Reviews are processed with local sentiment inference or a local heuristic,
without a paid AI call on creation. Ingredient units cannot change while
recipes or waste logs reference them. Ingredient/staff deletion requires
explicit removal of dependent records. Customer deletion preserves sales and
removes their customer link.

Waste analytics now normalizes grams and kilograms instead of treating every
unit as kilograms. Other units are disclosed and excluded from weight and
illustrative CO2 calculations, while their actual recorded costs remain in
the cost totals. The CO2 factor is labelled as an assumption.

The [data-entry guide](docs/operational-data-entry.md) documents request shapes,
permissions, units and analytics prerequisites. A tested maintenance command
can rebuild old customer totals for one tenant from its linked sales. It has
not been run against the application database. No new database columns are
needed; the Step 4 customer ownership migration remains a prerequisite for
older installations.

## Verification

| Check | Result |
| --- | --- |
| Final full backend suite, SQLite | 284 passed, 2 PostgreSQL-only checks skipped; 214.50 seconds |
| PostgreSQL 18.6 related regression set | 102 passed; 152.90 seconds |
| New operational tests | All 34 included in both final runs |
| Pyflakes for new API, schemas, totals service, maintenance command and tests | Passed |
| Black check for those files | Passed |
| Compilation of new application modules and command | Passed |
| Concrete request schemas in generated OpenAPI | Passed |
| Maintenance command `--help` | Passed |
| `git diff --check` | Passed |

The PostgreSQL run includes operational API tests, staffing portability,
customer tenant isolation, CSV imports and input limits. It used isolated
temporary schemas; zero remained afterward, and the test server was stopped.
No application data or live database service was modified.

The workflow tests enter business data through HTTP APIs. They cover a real
registration and authenticated checkout, CRUD, permissions, two-tenant reads
and writes, foreign and missing parent IDs, parent reassignment, bounded lists,
invalid inputs, real customer history, duplicate email conflicts, four
concurrent sales, CSV retry totals, repeatable tenant-scoped historical totals
rebuilding, local-only sentiment, and mixed-unit waste calculations.

The API-to-analytics workflow verifies recorded revenue of INR 300, recipe
cost INR 20 per item, labor cost INR 2,880 for a 24-hour shift at INR 120/hour,
actual review counts/ratings, and waste records. AI narrative calls in margin
and staffing tests are mocked; underlying database calculations are real.

Live Anthropic calls, hosted CI and browser interactions are not claimed.
AI narrative/forecast endpoints retain their credential and trained-model
prerequisites; entering records does not replace those services. No frontend
code changed in this step. Step 11 has not been started.
