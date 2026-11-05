from decimal import Decimal
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event

from app.api.deps import get_current_user
from app.database import get_db
from app.main import create_app
from app.models import Tenant, User, UserRole, Category, MenuItem
from app.models.staff import Staff, StaffRole


@pytest.fixture
async def search_api(db_session):
    owners = []
    for tenant in (1, 2):
        db_session.add(
            Tenant(id=tenant, tenant_id=f"search-{tenant}", name="Search tenant")
        )
        await db_session.flush()
        owner = User(
            tenant_id=tenant,
            email=f"search{tenant}@example.com",
            hashed_password="unused",
            role=UserRole.OWNER,
        )
        owners.append(owner)
        db_session.add(owner)
        for index in range(60):
            category = Category(tenant_id=tenant, name=f"Shared category {index:03}")
            db_session.add(category)
            await db_session.flush()
            db_session.add(
                MenuItem(
                    tenant_id=tenant,
                    category_id=category.id,
                    name=f"Shared dish {index:03}",
                    price=Decimal("1234.50"),
                    cost_price=Decimal("20"),
                )
            )
            db_session.add(
                Staff(
                    tenant_id=tenant,
                    name=f"Shared person {index:03}",
                    role=StaffRole.SOUS_CHEF,
                    hourly_rate=Decimal("999.00"),
                    email="private@example.com",
                    notes="Private payroll note",
                )
            )
    await db_session.commit()
    active = [owners[0]]
    app = create_app()

    async def database():
        yield db_session

    async def user():
        return active[0]

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = user
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client, active, owners, app


@pytest.mark.parametrize("tenant", [0, 1])
async def test_search_reaches_sixtieth_record_of_every_type(search_api, tenant):
    client, active, owners, _ = search_api
    active[0] = owners[tenant]
    response = await client.get("/api/v1/search", params={"q": "059"})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    assert {row["category"] for row in data["results"]} == {"menu", "category", "staff"}
    assert all("059" in row["name"] for row in data["results"])
    price = next(
        row["description"] for row in data["results"] if row["category"] == "menu"
    )
    assert price == "₹1,234.50"
    # IDs are disjoint between the tenants; a same-name record must not leak.
    assert all((int(row["id"]) <= 60) == (tenant == 0) for row in data["results"])


async def test_query_filters_in_sql_and_caps_each_type(search_api, db_session):
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    engine = db_session.bind.sync_engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        data = (
            await search_api[0].get("/api/v1/search", params={"q": "Shared"})
        ).json()
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert data["count"] == len(data["results"]) == 60
    assert all(
        sum(row["category"] == kind for row in data["results"]) == 20
        for kind in ("menu", "category", "staff")
    )
    assert len(statements) == 3
    assert all(
        "LIKE" in statement.upper() and "LIMIT" in statement.upper()
        for statement in statements
    )


@pytest.mark.parametrize(
    "role,expected",
    [
        (UserRole.STAFF, {"menu", "category"}),
        (UserRole.MANAGER, {"menu", "category", "staff"}),
    ],
)
async def test_role_permissions_and_minimal_staff_fields(search_api, role, expected):
    client, active, _, _ = search_api
    active[0].role = role
    response = await client.get("/api/v1/search", params={"q": "Shared"})
    assert {row["category"] for row in response.json()["results"]} == expected
    assert (
        "private@example.com" not in response.text
        and "Private payroll note" not in response.text
    )
    assert "999.00" not in response.text


async def test_staff_cannot_search_archived_menu_records(search_api, db_session):
    from sqlalchemy import select

    category = await db_session.scalar(
        select(Category).where(Category.tenant_id == 1, Category.name.endswith("059"))
    )
    category.is_active = False
    item = await db_session.scalar(
        select(MenuItem).where(MenuItem.tenant_id == 1, MenuItem.name.endswith("058"))
    )
    item.is_available = False
    await db_session.commit()
    client, active, _, _ = search_api
    active[0].role = UserRole.STAFF
    assert (await client.get("/api/v1/search", params={"q": "059"})).json()[
        "results"
    ] == []
    data = (await client.get("/api/v1/search", params={"q": "058"})).json()
    assert all(row["category"] == "category" for row in data["results"])


async def test_role_search_uses_actual_staff_role_and_does_not_duplicate(search_api):
    data = (await search_api[0].get("/api/v1/search", params={"q": "SOUS_CHEF"})).json()
    assert data["count"] == 20
    assert all(
        row["category"] == "staff" and row["description"] == "Sous Chef"
        for row in data["results"]
    )
    assert len({(row["category"], row["id"]) for row in data["results"]}) == 20


@pytest.mark.parametrize("query", ["%", "_", "\\", "missing-name", "   "])
async def test_wildcards_and_no_matches_do_not_dump_records(search_api, query):
    search_api[1][0].role = UserRole.STAFF
    data = (await search_api[0].get("/api/v1/search", params={"q": query})).json()
    assert data["count"] == 0 and data["results"] == []


async def test_literal_wildcard_names_are_searchable(search_api, db_session):
    from sqlalchemy import select

    item = await db_session.scalar(
        select(MenuItem).where(MenuItem.tenant_id == 1).limit(1)
    )
    item.name = "100%_special\\dish"
    await db_session.commit()
    for query in ("%_", "\\dish"):
        data = (await search_api[0].get("/api/v1/search", params={"q": query})).json()
        assert data["count"] == 1
        assert data["results"][0]["name"] == item.name


async def test_search_requires_authentication_and_validates_length(search_api):
    client, _, _, app = search_api
    assert (await client.get("/api/v1/search", params={"q": ""})).status_code == 422
    assert (
        await client.get("/api/v1/search", params={"q": "x" * 101})
    ).status_code == 422
    del app.dependency_overrides[get_current_user]
    assert (
        await client.get("/api/v1/search", params={"q": "Shared"})
    ).status_code == 401


async def test_search_errors_are_not_disguised_as_empty_results(
    search_api, db_session, caplog
):
    with patch.object(
        db_session, "execute", side_effect=RuntimeError("private database hostname")
    ):
        response = await search_api[0].get("/api/v1/search", params={"q": "Shared"})
    assert response.status_code == 500
    assert "private database hostname" not in response.text
    assert response.json()["correlation_id"] in caplog.text
