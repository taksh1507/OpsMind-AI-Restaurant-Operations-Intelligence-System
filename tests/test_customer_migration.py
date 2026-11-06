import json

from sqlalchemy import text, inspect
import pytest

from app.migrations.customer_tenants import (
    migrate_customer_tenants,
    require_customer_tenant_schema,
)


def _json(value):
    return json.loads(value) if isinstance(value, str) else value


@pytest.fixture
async def legacy(test_database_engine):
    engine = test_database_engine
    postgres = engine.dialect.name == "postgresql"
    async with engine.begin() as conn:
        if not postgres:
            await conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        await conn.exec_driver_sql("CREATE TABLE tenants (id INTEGER PRIMARY KEY)")
        await conn.exec_driver_sql("INSERT INTO tenants VALUES (1), (2)")
        await conn.exec_driver_sql(
            f"CREATE TABLE customers (id {'SERIAL' if postgres else 'INTEGER'} PRIMARY KEY, name VARCHAR(255) NOT NULL, "
            "email VARCHAR(255) NOT NULL, total_spent_inr NUMERIC(12,2) NOT NULL, "
            "visit_count INTEGER NOT NULL, preferences JSON NOT NULL, "
            f"created_at {'TIMESTAMP' if postgres else 'DATETIME'} NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            f"updated_at {'TIMESTAMP' if postgres else 'DATETIME'} NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        await conn.exec_driver_sql(
            "CREATE UNIQUE INDEX ix_customers_email ON customers (email)"
        )
        await conn.exec_driver_sql(
            "CREATE TABLE sales (id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL REFERENCES tenants(id), "
            "customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL, total_amount NUMERIC(10,2))"
        )
        await conn.execute(
            text(
                "INSERT INTO customers (id,name,email,total_spent_inr,visit_count,preferences) "
                "VALUES (10,'Shared','shared@example.com',9999,100,:preferences)"
            ),
            {"preferences": json.dumps({"private_note": "unknown legacy owner"})},
        )
        await conn.exec_driver_sql(
            "INSERT INTO sales VALUES (1,1,10,20),(2,2,10,30),(3,2,10,40)"
        )
    try:
        yield engine
    finally:
        await engine.dispose()


async def test_shared_customer_migration_splits_links_and_preserves_archive(legacy):
    assert await migrate_customer_tenants(legacy) == {
        "status": "migrated",
        "customers": 2,
        "splits": 1,
    }
    async with legacy.connect() as conn:
        rows = (
            (
                await conn.execute(
                    text(
                        "SELECT id,tenant_id,email,total_spent_inr,visit_count,preferences FROM customers ORDER BY tenant_id"
                    )
                )
            )
            .mappings()
            .all()
        )
        assert [
            (row["tenant_id"], row["total_spent_inr"], row["visit_count"])
            for row in rows
        ] == [(1, 20, 1), (2, 70, 2)]
        assert rows[0]["id"] == 10 and rows[1]["id"] != 10
        assert all(_json(row["preferences"]) == {} for row in rows)
        references = (
            await conn.execute(
                text("SELECT tenant_id,customer_id FROM sales ORDER BY id")
            )
        ).all()
        assert references == [(1, 10), (2, rows[1]["id"]), (2, rows[1]["id"])]
        archive = json.loads(
            (
                await conn.execute(
                    text(
                        "SELECT original_record FROM customer_tenant_migration_archive WHERE customer_id=10"
                    )
                )
            ).scalar_one()
        )
        assert archive["preferences"] == {"private_note": "unknown legacy owner"}
        assert archive["visit_count"] == 100
        if legacy.dialect.name == "sqlite":
            assert (await conn.exec_driver_sql("PRAGMA foreign_keys")).scalar_one() == 1
            assert not (await conn.exec_driver_sql("PRAGMA foreign_key_check")).all()
        await require_customer_tenant_schema(conn)
    assert (await migrate_customer_tenants(legacy))["status"] == "current"


async def test_orphans_require_mapping_and_failure_leaves_legacy_schema_intact(legacy):
    async with legacy.begin() as conn:
        await conn.exec_driver_sql(
            "INSERT INTO customers (id,name,email,total_spent_inr,visit_count,preferences) "
            "VALUES (20,'Orphan','orphan@example.com',50,2,'{}')"
        )
    with pytest.raises(ValueError, match="orphan customer IDs"):
        await migrate_customer_tenants(legacy)
    async with legacy.connect() as conn:
        assert "tenant_id" not in await conn.run_sync(
            lambda sync: {col["name"] for col in inspect(sync).get_columns("customers")}
        )
        assert (
            await conn.execute(text("SELECT COUNT(*) FROM customers"))
        ).scalar_one() == 2
        if legacy.dialect.name == "sqlite":
            assert (await conn.exec_driver_sql("PRAGMA foreign_keys")).scalar_one() == 1
        with pytest.raises(RuntimeError, match="require migration"):
            await require_customer_tenant_schema(conn)
    await migrate_customer_tenants(legacy, {20: 2})
    async with legacy.connect() as conn:
        assert (
            await conn.execute(text("SELECT tenant_id FROM customers WHERE id=20"))
        ).scalar_one() == 2


async def test_invalid_assignment_cannot_modify_data(legacy):
    with pytest.raises(ValueError, match="unknown customer or tenant"):
        await migrate_customer_tenants(legacy, {999: 2})
    with pytest.raises(ValueError, match="only permitted"):
        await migrate_customer_tenants(legacy, {10: 2})
    async with legacy.connect() as conn:
        assert (
            await conn.execute(text("SELECT COUNT(*) FROM customers"))
        ).scalar_one() == 1
        assert (
            await conn.execute(text("SELECT customer_id FROM sales WHERE id=2"))
        ).scalar_one() == 10


async def test_late_failure_rolls_back_table_rebuild_archive_and_links(legacy):
    from unittest.mock import patch

    with patch(
        "app.migrations.customer_tenants.require_customer_tenant_schema",
        side_effect=RuntimeError("late failure"),
    ):
        with pytest.raises(RuntimeError, match="late failure"):
            await migrate_customer_tenants(legacy)
    async with legacy.connect() as conn:
        names = await conn.run_sync(lambda sync: inspect(sync).get_table_names())
        assert "customer_tenant_migration_archive" not in names
        assert "customers_tenant_rebuild" not in names
        assert (
            await conn.execute(text("SELECT customer_id FROM sales WHERE id=2"))
        ).scalar_one() == 10
        if legacy.dialect.name == "sqlite":
            assert (await conn.exec_driver_sql("PRAGMA foreign_keys")).scalar_one() == 1


async def test_single_owner_preserves_preferences_and_rebuilds_only_its_totals(legacy):
    async with legacy.begin() as conn:
        await conn.exec_driver_sql("DELETE FROM sales WHERE tenant_id=2")
    result = await migrate_customer_tenants(legacy)
    assert result["customers"] == 1 and result["splits"] == 0
    async with legacy.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT tenant_id,total_spent_inr,visit_count,preferences FROM customers"
                )
            )
        ).one()
        assert row[:3] == (1, 20, 1)
        assert _json(row[3]) == {"private_note": "unknown legacy owner"}


async def test_partial_schema_is_rejected_instead_of_guessing(legacy):
    async with legacy.begin() as conn:
        await conn.exec_driver_sql("ALTER TABLE customers ADD COLUMN tenant_id INTEGER")
    with pytest.raises(RuntimeError, match="incomplete"):
        await migrate_customer_tenants(legacy)


async def test_postgres_sequence_is_advanced_past_split_customers(legacy):
    if legacy.dialect.name != "postgresql":
        pytest.skip("PostgreSQL sequence check")
    await migrate_customer_tenants(legacy)
    async with legacy.begin() as conn:
        previous = (
            await conn.execute(text("SELECT MAX(id) FROM customers"))
        ).scalar_one()
        inserted = (
            await conn.execute(
                text(
                    "INSERT INTO customers (tenant_id,name,email,total_spent_inr,visit_count,preferences) "
                    "VALUES (1,'New','new@example.com',0,0,'{}') RETURNING id"
                )
            )
        ).scalar_one()
        assert inserted > previous
