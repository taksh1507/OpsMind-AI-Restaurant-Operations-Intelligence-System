"""Transactional customer ownership migration for SQLite and PostgreSQL.

Run while application writers are stopped. No implicit tenant is assigned to an
orphan. Shared customers are split, metrics rebuilt and ambiguous preferences
archived rather than exposed to every restaurant.
"""

import json
from decimal import Decimal

from sqlalchemy import Column, Integer, MetaData, Table, Text, inspect, select, func
from sqlalchemy.schema import CreateTable, CreateIndex, DropTable

from app.models.customer import Customer
from app.models.tenant import Tenant


def _schema_state(connection):
    schema = inspect(connection)
    if not schema.has_table("customers"):
        return "absent"
    columns = {column["name"]: column for column in schema.get_columns("customers")}
    if "tenant_id" not in columns:
        return "legacy"
    uniques = schema.get_unique_constraints("customers") + [
        index for index in schema.get_indexes("customers") if index.get("unique")
    ]
    scoped = any(set(item["column_names"]) == {"tenant_id", "email"} for item in uniques)
    global_email = any(item["column_names"] == ["email"] for item in uniques)
    foreign_key = any(
        key["constrained_columns"] == ["tenant_id"] and key["referred_table"] == "tenants"
        for key in schema.get_foreign_keys("customers")
    )
    if columns["tenant_id"]["nullable"] or not scoped or global_email or not foreign_key:
        raise RuntimeError("Customer ownership schema is incomplete; review the migration before starting.")
    return "current"


async def require_customer_tenant_schema(connection):
    if await connection.run_sync(_schema_state) == "legacy":
        raise RuntimeError(
            "Legacy global customers require migration: stop writers and run "
            "python -m scripts.migrate_customer_tenants (see docs/customer-tenant-migration.md)."
        )


async def _upgrade(connection, orphan_owners):
    state = await connection.run_sync(_schema_state)
    if state != "legacy":
        return {"status": state, "customers": 0, "splits": 0}
    if connection.dialect.name == "postgresql":
        await connection.exec_driver_sql("LOCK TABLE customers, sales IN ACCESS EXCLUSIVE MODE")

    def reflect(sync):
        metadata = MetaData()
        return (Table("customers", metadata, autoload_with=sync),
                Table("sales", metadata, autoload_with=sync),
                Table("tenants", metadata, autoload_with=sync, extend_existing=True))

    old, sales, tenants = await connection.run_sync(reflect)
    expected = set(Customer.__table__.columns.keys()) - {"tenant_id"}
    if set(old.columns.keys()) != expected:
        raise RuntimeError("Unexpected legacy customer columns; manual migration review is required.")
    originals = [dict(row) for row in (await connection.execute(select(old))).mappings()]
    original_ids = {row["id"] for row in originals}
    tenant_ids = set((await connection.execute(select(tenants.c.id))).scalars())
    if set(orphan_owners) - original_ids or any(value not in tenant_ids for value in orphan_owners.values()):
        raise ValueError("Orphan owner mapping references an unknown customer or tenant")
    groups = (await connection.execute(
        select(sales.c.customer_id, sales.c.tenant_id, func.count().label("visits"),
               func.sum(sales.c.total_amount).label("spent"))
        .where(sales.c.customer_id.is_not(None))
        .group_by(sales.c.customer_id, sales.c.tenant_id)
    )).mappings().all()
    aggregates = {}
    for group in groups:
        if group["customer_id"] not in original_ids or group["tenant_id"] not in tenant_ids:
            raise ValueError("Dangling customer/tenant sales references must be repaired before migration")
        aggregates.setdefault(group["customer_id"], {})[group["tenant_id"]] = group
    orphans = sorted(original_ids - set(aggregates) - set(orphan_owners))
    if orphans:
        raise ValueError(f"Explicit tenant assignments required for orphan customer IDs: {orphans}")
    if any(key in aggregates for key in orphan_owners):
        raise ValueError("Owner overrides are only permitted for customers without sales")

    archive = Table(
        "customer_tenant_migration_archive", MetaData(),
        Column("customer_id", Integer, primary_key=True),
        Column("original_record", Text, nullable=False),
        Column("tenant_ids", Text, nullable=False),
    )
    await connection.run_sync(lambda sync: archive.create(sync, checkfirst=True))
    rows, links = [], []
    next_id = max(original_ids, default=0) + 1
    for original in originals:
        owners = sorted(aggregates.get(original["id"], {})) or [orphan_owners[original["id"]]]
        await connection.execute(archive.insert().values(
            customer_id=original["id"], original_record=json.dumps(original, default=str),
            tenant_ids=json.dumps(owners),
        ))
        for position, owner in enumerate(owners):
            row = dict(original, tenant_id=owner)
            if position:
                row["id"], next_id = next_id, next_id + 1
                links.append((original["id"], row["id"], owner))
            group = aggregates.get(original["id"], {}).get(owner)
            row["visit_count"] = group["visits"] if group else 0
            row["total_spent_inr"] = group["spent"] if group else Decimal("0")
            if len(owners) > 1:
                row["preferences"] = {}
            rows.append(row)

    if connection.dialect.name == "sqlite":
        metadata = MetaData()
        Tenant.__table__.to_metadata(metadata)
        replacement = Customer.__table__.to_metadata(metadata, name="customers_tenant_rebuild")
        await connection.execute(CreateTable(replacement))
        if rows:
            await connection.execute(replacement.insert(), rows)
    else:
        schema = await connection.run_sync(lambda sync: (
            inspect(sync).get_unique_constraints("customers"), inspect(sync).get_indexes("customers")
        ))
        quote = connection.dialect.identifier_preparer.quote
        for constraint in schema[0]:
            if constraint["column_names"] == ["email"]:
                await connection.exec_driver_sql(f"ALTER TABLE customers DROP CONSTRAINT {quote(constraint['name'])}")
        for index in schema[1]:
            if index.get("unique") and index["column_names"] == ["email"] and not index.get("duplicates_constraint"):
                await connection.exec_driver_sql(f"DROP INDEX {quote(index['name'])}")
        await connection.exec_driver_sql("ALTER TABLE customers ADD COLUMN tenant_id INTEGER")
        for row in rows:
            if row["id"] in original_ids:
                await connection.execute(Customer.__table__.update().where(Customer.id == row["id"]).values(**row))
            else:
                await connection.execute(Customer.__table__.insert().values(**row))

    for old_id, new_id, owner in links:
        await connection.execute(sales.update().where(
            sales.c.customer_id == old_id, sales.c.tenant_id == owner
        ).values(customer_id=new_id))
    if connection.dialect.name == "sqlite":
        await connection.execute(DropTable(old))
        await connection.exec_driver_sql("ALTER TABLE customers_tenant_rebuild RENAME TO customers")
        for index in Customer.__table__.indexes:
            await connection.execute(CreateIndex(index))
        if (await connection.exec_driver_sql("PRAGMA foreign_key_check")).first():
            raise ValueError("Foreign-key check failed; migration rolled back")
    else:
        await connection.exec_driver_sql("ALTER TABLE customers ALTER COLUMN tenant_id SET NOT NULL")
        await connection.exec_driver_sql(
            "ALTER TABLE customers ADD CONSTRAINT fk_customers_tenant "
            "FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE"
        )
        await connection.exec_driver_sql(
            "ALTER TABLE customers ADD CONSTRAINT uq_customers_tenant_email UNIQUE (tenant_id, email)"
        )
        existing_indexes = await connection.run_sync(lambda sync: {
            index["name"] for index in inspect(sync).get_indexes("customers")
        })
        for index in Customer.__table__.indexes:
            if index.name not in existing_indexes:
                await connection.execute(CreateIndex(index))
        await connection.exec_driver_sql(
            "SELECT setval(pg_get_serial_sequence('customers', 'id'), "
            "COALESCE((SELECT MAX(id) FROM customers), 1), EXISTS(SELECT 1 FROM customers))"
        )
    await require_customer_tenant_schema(connection)
    return {"status": "migrated", "customers": len(rows), "splits": len(links)}


async def migrate_customer_tenants(engine, orphan_owners=None):
    """Own the transaction and restore SQLite foreign-key enforcement on errors."""
    if engine.dialect.name not in {"sqlite", "postgresql"}:
        raise ValueError("Customer migration supports SQLite and PostgreSQL only")
    orphan_owners = orphan_owners or {}
    if any(type(key) is not int or type(value) is not int for key, value in orphan_owners.items()):
        raise ValueError("Orphan assignments must contain integer customer and tenant IDs")
    async with engine.connect() as connection:
        if engine.dialect.name == "sqlite":
            enabled = (await connection.exec_driver_sql("PRAGMA foreign_keys")).scalar_one()
            await connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            await connection.commit()
            try:
                await connection.exec_driver_sql("BEGIN IMMEDIATE")
                result = await _upgrade(connection, orphan_owners)
                await connection.commit()
                return result
            except BaseException:
                await connection.rollback()
                raise
            finally:
                await connection.exec_driver_sql(f"PRAGMA foreign_keys={int(enabled)}")
                await connection.commit()
        else:
            async with connection.begin():
                await connection.exec_driver_sql("SELECT pg_advisory_xact_lock(9130524217)")
                return await _upgrade(connection, orphan_owners)
