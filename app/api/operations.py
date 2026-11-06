"""Operational data entry. Indirect ownership is checked through both parents."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_manager, get_current_user
from app.core.time_utils import utc_now
from app.database import get_db
from app.models import Customer, Ingredient, MenuItem, Recipe, Review, Sale, User
from app.models.menu import WasteLog
from app.models.staff import Staff, Shift
from app.models.operations_schemas import (
    CustomerInput,
    CustomerOutput,
    IngredientInput,
    IngredientOutput,
    RecipeInput,
    RecipeOutput,
    StaffInput,
    StaffOutput,
    ShiftInput,
    ShiftOutput,
    WasteInput,
    WasteOutput,
    ReviewInput,
    ReviewOutput,
)
from app.services import sentiment_service

router = APIRouter(tags=["Operational data"])


def owned_query(model, tenant_id):
    if model is Recipe:
        return (
            select(Recipe)
            .join(MenuItem)
            .join(Ingredient)
            .where(MenuItem.tenant_id == tenant_id, Ingredient.tenant_id == tenant_id)
        )
    if model is Shift:
        return select(Shift).join(Staff).where(Staff.tenant_id == tenant_id)
    if model is WasteLog:
        return (
            select(WasteLog).join(Ingredient).where(Ingredient.tenant_id == tenant_id)
        )
    return select(model).where(model.tenant_id == tenant_id)


async def owned(db, model, record_id, tenant_id):
    row = await db.scalar(owned_query(model, tenant_id).where(model.id == record_id))
    if row is None:
        raise HTTPException(404, "Record not found")
    return row


async def validate_parents(db, model, values, tenant_id):
    if model is Recipe:
        await owned(db, MenuItem, values["menu_item_id"], tenant_id)
        await owned(db, Ingredient, values["ingredient_id"], tenant_id)
    elif model is Shift:
        await owned(db, Staff, values["staff_id"], tenant_id)
    elif model is WasteLog:
        await owned(db, Ingredient, values["ingredient_id"], tenant_id)


async def commit(db):
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Record conflicts with existing data") from None


def register_crud(path, model, input_schema, output_schema, *, public_read=False):
    """Register the same bounded CRUD contract with explicit resource schemas."""
    read_dependency = get_current_user if public_read else get_current_manager

    async def listing(
        user: User = Depends(read_dependency),
        db: AsyncSession = Depends(get_db),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ):
        return (
            await db.scalars(
                owned_query(model, user.tenant_id)
                .order_by(model.id)
                .limit(limit)
                .offset(offset)
            )
        ).all()

    async def reading(
        record_id: int,
        user: User = Depends(read_dependency),
        db: AsyncSession = Depends(get_db),
    ):
        return await owned(db, model, record_id, user.tenant_id)

    async def creating(
        payload,
        user: User = Depends(get_current_manager),
        db: AsyncSession = Depends(get_db),
    ):
        values = payload.model_dump()
        await validate_parents(db, model, values, user.tenant_id)
        if hasattr(model, "tenant_id"):
            values["tenant_id"] = user.tenant_id
        row = model(**values)
        db.add(row)
        await commit(db)
        await db.refresh(row)
        return row

    async def replacing(
        record_id: int,
        payload,
        user: User = Depends(get_current_manager),
        db: AsyncSession = Depends(get_db),
    ):
        row = await owned(db, model, record_id, user.tenant_id)
        values = payload.model_dump()
        await validate_parents(db, model, values, user.tenant_id)
        if model is Ingredient and row.unit != values["unit"]:
            if await db.scalar(
                select(Recipe.id).where(Recipe.ingredient_id == record_id).limit(1)
            ) or await db.scalar(
                select(WasteLog.id).where(WasteLog.ingredient_id == record_id).limit(1)
            ):
                raise HTTPException(
                    409,
                    "Cannot change units while recipes or waste logs reference this ingredient",
                )
        for key, value in values.items():
            setattr(row, key, value)
        await commit(db)
        await db.refresh(row)
        return row

    async def deleting(
        record_id: int,
        user: User = Depends(get_current_manager),
        db: AsyncSession = Depends(get_db),
    ):
        row = await owned(db, model, record_id, user.tenant_id)
        if model is Ingredient:
            if await db.scalar(
                select(Recipe.id).where(Recipe.ingredient_id == record_id).limit(1)
            ) or await db.scalar(
                select(WasteLog.id).where(WasteLog.ingredient_id == record_id).limit(1)
            ):
                raise HTTPException(
                    409,
                    "Remove related recipes and waste logs before deleting this ingredient",
                )
        if model is Staff and await db.scalar(
            select(Shift.id).where(Shift.staff_id == record_id).limit(1)
        ):
            raise HTTPException(
                409, "Remove shifts before deleting this staff record, or deactivate it"
            )
        if model is Customer:
            await db.execute(
                update(Sale)
                .where(Sale.tenant_id == user.tenant_id, Sale.customer_id == record_id)
                .values(customer_id=None)
            )
        await db.delete(row)
        await commit(db)
        return Response(status_code=204)

    creating.__annotations__["payload"] = input_schema
    replacing.__annotations__["payload"] = input_schema
    for method, suffix, handler, response_model, status_code in (
        ("GET", "", listing, list[output_schema], 200),
        ("GET", "/{record_id}", reading, output_schema, 200),
        ("POST", "", creating, output_schema, 201),
        ("PUT", "/{record_id}", replacing, output_schema, 200),
        ("DELETE", "/{record_id}", deleting, None, 204),
    ):
        router.add_api_route(
            path + suffix,
            handler,
            methods=[method],
            response_model=response_model,
            status_code=status_code,
            name=f"{method.lower()}_{model.__name__.lower()}",
        )


register_crud("/customers", Customer, CustomerInput, CustomerOutput, public_read=True)
register_crud("/ingredients", Ingredient, IngredientInput, IngredientOutput)
register_crud("/recipes", Recipe, RecipeInput, RecipeOutput)
register_crud("/staff", Staff, StaffInput, StaffOutput)
register_crud("/shifts", Shift, ShiftInput, ShiftOutput)
register_crud("/waste-logs", WasteLog, WasteInput, WasteOutput)


@router.post("/reviews", response_model=ReviewOutput, status_code=201)
async def create_review(
    payload: ReviewInput,
    user: User = Depends(get_current_manager),
    db: AsyncSession = Depends(get_db),
):
    result = await sentiment_service.predict_sentiment(
        payload.comment, allow_external=False
    )
    score = Decimal(str(result["score"]))
    if not score.is_finite() or not -1 <= score <= 1:
        raise HTTPException(503, "Sentiment analysis is temporarily unavailable")
    row = Review(
        **payload.model_dump(),
        tenant_id=user.tenant_id,
        sentiment_score=score.quantize(Decimal("0.01")),
        is_processed=True,
        processed_at=utc_now(),
    )
    db.add(row)
    await commit(db)
    await db.refresh(row)
    return row


@router.get("/reviews", response_model=list[ReviewOutput])
async def list_reviews(
    user: User = Depends(get_current_manager),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return (
        await db.scalars(
            owned_query(Review, user.tenant_id)
            .order_by(Review.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
