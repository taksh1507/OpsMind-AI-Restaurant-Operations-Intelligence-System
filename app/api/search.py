"""Bounded SQL substring searches, scoped to tenant and role."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import safe_error_detail
from app.database import get_db
from app.models import User, UserRole
from app.models.menu import Category, MenuItem
from app.models.staff import Staff

router = APIRouter(prefix="/search", tags=["search"])


def contains(column, query):
    # User wildcards are literal characters, not an instruction to match all.
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return column.ilike(f"%{escaped}%", escape="\\")


@router.get("")
async def global_search(
    q: str = Query(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return at most 20 matches per type; prices use the app's INR currency.

    Staff accounts see available menu items and active categories only.
    Managers/owners can also search archived menu records and staff names/roles.
    Staff contact details, wages and notes are never returned.
    """
    query = q.strip()
    if not query:
        return {"query": query, "count": 0, "results": []}
    can_manage = current_user.role in (UserRole.OWNER, UserRole.MANAGER)
    results = []
    try:
        menu = select(MenuItem).where(
            MenuItem.tenant_id == current_user.tenant_id, contains(MenuItem.name, query)
        )
        if not can_manage:
            menu = menu.join(Category, Category.id == MenuItem.category_id).where(
                MenuItem.is_available.is_(True),
                Category.is_active.is_(True),
                Category.tenant_id == current_user.tenant_id,
            )
        items = (
            (
                await db.execute(
                    menu.order_by(func.lower(MenuItem.name), MenuItem.id).limit(20)
                )
            )
            .scalars()
            .all()
        )
        results.extend(
            {
                "id": str(item.id),
                "name": item.name,
                "category": "menu",
                "description": f"₹{item.price:,.2f}",
            }
            for item in items
        )
        categories = select(Category).where(
            Category.tenant_id == current_user.tenant_id, contains(Category.name, query)
        )
        if not can_manage:
            categories = categories.where(Category.is_active.is_(True))
        rows = (
            (
                await db.execute(
                    categories.order_by(func.lower(Category.name), Category.id).limit(
                        20
                    )
                )
            )
            .scalars()
            .all()
        )
        results.extend(
            {
                "id": str(category.id),
                "name": category.name,
                "category": "category",
                "description": "Menu category",
            }
            for category in rows
        )
        if can_manage:
            # Cast native PostgreSQL enums before ILIKE; SQLite also supports this.
            roles = cast(Staff.role, String)
            staff = (
                select(Staff)
                .where(
                    Staff.tenant_id == current_user.tenant_id,
                    or_(contains(Staff.name, query), contains(roles, query)),
                )
                .order_by(func.lower(Staff.name), Staff.id)
                .limit(20)
            )
            rows = (await db.execute(staff)).scalars().all()
            results.extend(
                {
                    "id": str(member.id),
                    "name": member.name,
                    "category": "staff",
                    "description": member.role.value.replace("_", " ").title(),
                }
                for member in rows
            )
        return {"query": query, "count": len(results), "results": results}
    except Exception:
        raise HTTPException(
            500, safe_error_detail("Search temporarily unavailable")
        ) from None
