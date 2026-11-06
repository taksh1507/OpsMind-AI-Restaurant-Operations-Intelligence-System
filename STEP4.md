# Step 4 — tenant isolation

Customers now have a required, indexed tenant FK and email uniqueness per
restaurant. Briefings, real order history, CSV customer references, personas,
segmentation inputs and recipe cost calculations enforce tenant ownership.
Foreign and nonexistent customer IDs produce equivalent rejection behavior.
Existing test fixtures now assign customer ownership explicitly.

The briefing's invented order history was replaced with real tenant-scoped
sale/line-item queries as part of securing those queries. Customer CRUD and
sales-driven profile updates remain Step 10 work.

## Migration

Use the [maintenance migration instructions](docs/customer-tenant-migration.md)
for existing databases. Shared customer IDs are split, sale links rewritten,
and tenant totals rebuilt. Original profiles are archived for review; orphan
ownership is never guessed. Startup rejects the old global schema until the
migration has been run. No configured application database was migrated during
this work.

## ML data policy

- `build_raw_dataset()` without a tenant reads only public/synthetic data and
  never opens the restaurant database. This is the shared-model path; tenants
  have not opted into shared private-review training.
- Reading restaurant reviews requires an explicit tenant ID; a provided session
  without one is rejected. Both supplied-session and configured-database paths
  apply the tenant filter.
- Tenant review frames carry owner metadata. Exports must go under
  `data/<tenant_id>/`, and training such a CSV requires the matching tenant ID.
  A tenant sentiment model is saved beneath `models/<tenant_id>/` instead of
  overwriting the shared artifact. The shared serving path is unchanged and does
  not load these tenant artifacts. This step does not introduce a new tenant
  training API. Regenerate shared training CSVs with the public-only builder
  before retraining; do not reuse private CSVs from older unscoped pipelines.
- Segmentation checks the customer, sale, line item, menu item and category
  tenant, including malformed historical links. Training endpoints receive only
  their own customer feature rows. Recipe costs require both menu and ingredient
  ownership.

## Verification

New tests cover two tenants in both directions, briefing/import existence
oracles, owned customers without sales, real history and recency, malformed
cross-tenant links, training endpoint inputs, review datasets, private exports,
model artifact isolation, scoped uniqueness and migration rollback/idempotence.

Final checks on Windows/Python 3.14 using `.venv-step2`:

| Check | Result |
| --- | --- |
| `python scripts/verify_test_isolation.py` | 158 passed twice (98.94s, 93.28s); artifact hashes and Git status unchanged after each run |
| Focused customer/migration/sentiment tests | 24 passed before the final positive export assertion was expanded; that assertion passed in both full runs |
| Flake8 F checks on changed customer/ML/migration modules and new tests | Pass |
| `git diff --check` | Pass |

PostgreSQL 18.6 was verified on 23 October 2026 using an isolated local cluster
on port 55432, separate from the installed PostgreSQL service. The full suite
passed (158 tests, 148.72s) with `TEST_DATABASE_URL` set; shared database fixtures
used PostgreSQL while tests explicitly creating SQLite engines retained SQLite.
All seven customer migration tests passed on PostgreSQL, including sequence
advancement, split ownership, rollback, orphan mapping and repeat execution.
The five auth schema/config tests also passed with the PostgreSQL fixture.
No existing application database was migrated.
