# Customer ownership migration

This is the documented SQL migration alternative to introducing Alembic in
Step 4. Its implementation is `app/migrations/customer_tenants.py`, with a
maintenance CLI in `scripts/migrate_customer_tenants.py`. It supports the
audited legacy schema on SQLite and PostgreSQL. New databases get the tenant
schema directly from the application's model metadata.

## Run against an existing database

1. Stop API workers and the retraining scheduler, and take a database backup.
   Test the migration on a restored copy first. The CLI uses the configured
   `DATABASE_URL`; it does not choose or print a database URL for you.
2. From the repository root, using the environment with runtime dependencies:

   ```text
   python -m scripts.migrate_customer_tenants
   ```

3. If a customer has no sales, the command stops without changing data and lists
   the customer IDs requiring verified owner assignments. Create a local JSON
   mapping such as `{"42": 3, "57": 8}` (customer ID to tenant ID), then run:

   ```text
   python -m scripts.migrate_customer_tenants --orphan-owners customer-owners.json
   ```

   The CLI rejects unknown IDs and overrides for customers whose sales already
   establish ownership. Keep the mapping out of source control if it contains
   operational information.
4. Review the result counts and the migrated customers/sales in the restored
   database before applying the same procedure to the intended database. Restart
   the API only after migration succeeds. Startup detects legacy or partially
   migrated customer schemas and fails with a migration instruction instead of
   serving requests against global customers.

The migration was implemented and tested against temporary databases during
hardening. It has **not** been run against your configured application database.

## Data policy

- A customer referenced by sales from one tenant keeps its ID and profile and
  receives that tenant ID. Its totals are rebuilt from that tenant's sale
  `total_amount` values and sale count.
- A customer referenced by multiple tenants becomes one record per tenant. The
  lowest tenant ID retains the old customer ID; other tenants receive new IDs.
  Their sale references are rewritten accordingly. Profiles retain the known
  name/email, while ambiguous preferences are cleared for every split record.
  Counts and spending are rebuilt independently for each restaurant.
- Orphan records require explicit verified assignments; no default tenant is
  guessed. With no linked sales, their rebuilt counts and totals are zero.
- Every original record is preserved as JSON text in
  `customer_tenant_migration_archive`, along with its referencing/assigned tenant
  IDs. This maintenance-only archive contains personal data and old preferences;
  it has no application model or endpoint. Restrict its access with your backup
  and database maintenance access, and retain it under the same data policy.
- Imports and bookmarks using an old shared customer ID must use the new ID for
  the relevant restaurant. The migrated `customers` table provides the resulting
  IDs by tenant and email; the application no longer accepts another tenant's ID.

## SQL and transaction strategy

SQLite disables foreign-key enforcement on its maintenance connection **before**
starting `BEGIN IMMEDIATE`, builds a replacement customers table with non-null
tenant FK and `UNIQUE (tenant_id, email)`, copies the mapped data, rewrites sales,
drops/renames the customer tables, rebuilds indexes, and runs
`PRAGMA foreign_key_check`. Commit or rollback happens before restoring the
original foreign-key enforcement setting. Rollback is tested even after the
table replacement and sale-reference changes.

PostgreSQL takes the same advisory DDL lock used by application startup and
exclusive customers/sales table locks. In one transaction it drops global email
uniqueness, adds and backfills tenant ownership, inserts split profiles,
rewrites references, enforces the tenant FK and non-null constraint, adds scoped
uniqueness/indexes, and advances the customer ID sequence beyond inserted clones.

Repeated execution recognizes the complete schema and leaves data unchanged.
Unknown columns, dangling references and incomplete tenant schemas require
review instead of a guessed or destructive repair.

SQLite and PostgreSQL 18.6 execution are covered by automated tests. To repeat
PostgreSQL checks, set `TEST_DATABASE_URL` to a disposable database using the
`postgresql+asyncpg://` driver, then run `python -m pytest -q`. Tests create and
drop only their own randomly named `opsmind_test_...` schemas. Explicit SQLite
tests retain their original dialect. See STEP4.md for recorded verification.

References: [SQLite table rebuild procedure](https://www.sqlite.org/lang_altertable.html),
[SQLite foreign-key PRAGMA rules](https://www.sqlite.org/pragma.html).
