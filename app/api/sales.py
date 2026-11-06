"""Sales API Router

Handles sale creation (checkout) with secure multi-tenant transaction logic.
Uses get_current_user dependency to ensure tenant isolation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from decimal import Decimal
from datetime import datetime, timezone

from app.database import get_db
from app.api.deps import get_current_user
from app.api.ws_manager import connection_manager
from app.models import User, Sale, SaleItem, MenuItem, PaymentMethod, Customer
from app.models.schemas import SaleCreateRequest, SaleResponse

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
async def create_sale(
    request: SaleCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new sale (checkout).

    This is the transactional core that records when a customer buys items.

    Security & Integrity Checks:
    1. Fetch all menu items to verify they exist and belong to user's tenant
    2. Verify all menu items are available
    3. Calculate subtotal from current prices at time of sale
    4. Apply optional tax rate
    5. Save sale and all items in a single transaction

    Args:
        request: Sale creation request with list of items and quantities
        current_user: Authenticated user with tenant context (injected)
        db: Database session (injected)

    Returns:
        Created sale with all line items and calculated totals

    Raises:
        HTTPException 400: If items list is empty or items don't belong to tenant
        HTTPException 404: If any menu item not found
        HTTPException 500: If database error occurs
    """

    try:
        # Validate payment method
        try:
            payment_method = PaymentMethod(request.payment_method)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payment method. Must be one of: {', '.join([pm.value for pm in PaymentMethod])}",
            )

        if request.customer_id is not None:
            customer = await db.scalar(
                select(Customer.id)
                .where(
                    Customer.id == request.customer_id,
                    Customer.tenant_id == current_user.tenant_id,
                )
                .with_for_update()
            )
            if customer is None:
                raise HTTPException(404, "Customer not found")

        # Extract menu item IDs from request
        requested_item_ids = [item.menu_item_id for item in request.items]

        # CRITICAL: Fetch menu items and verify they belong to user's tenant
        result = await db.execute(
            select(MenuItem).where(
                (MenuItem.id.in_(requested_item_ids))
                & (MenuItem.tenant_id == current_user.tenant_id)
                & (MenuItem.is_available == True)
            )
        )

        menu_items_map = {item.id: item for item in result.scalars().all()}

        # Verify all requested items exist and belong to tenant
        for item in request.items:
            if item.menu_item_id not in menu_items_map:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Menu item {item.menu_item_id} not found or not available for your tenant",
                )

        # Calculate total amount from current menu item prices
        total_amount = Decimal("0.00")
        sale_items_data = []

        for item_request in request.items:
            menu_item = menu_items_map[item_request.menu_item_id]
            line_total = menu_item.price * Decimal(item_request.quantity)
            total_amount += line_total

            # Preserve the price at time of sale (for historical accuracy)
            sale_items_data.append(
                {
                    "menu_item_id": menu_item.id,
                    "quantity": item_request.quantity,
                    "unit_price_at_sale": menu_item.price,
                }
            )

        if total_amount > Decimal("99999999.99"):
            raise HTTPException(422, "Sale subtotal exceeds the supported amount")

        # Calculate tax if tax_rate provided
        tax_amount = Decimal("0.00")
        if request.tax_rate is not None and request.tax_rate > 0:
            tax_amount = (total_amount * request.tax_rate).quantize(Decimal("0.01"))

        # Create the Sale in a single transaction
        new_sale = Sale(
            tenant_id=current_user.tenant_id,  # Auto-scoped to user's restaurant
            customer_id=request.customer_id,
            total_amount=total_amount,
            tax_amount=tax_amount,
            payment_method=payment_method,
            timestamp=datetime.now(timezone.utc),
        )

        db.add(new_sale)
        await db.flush()  # Flush to get the sale.id before creating items

        # Create all SaleItems with historical pricing
        for item_data in sale_items_data:
            sale_item = SaleItem(
                tenant_id=current_user.tenant_id,  # Auto-scoped to user's restaurant
                sale_id=new_sale.id,
                menu_item_id=item_data["menu_item_id"],
                quantity=item_data["quantity"],
                unit_price_at_sale=item_data["unit_price_at_sale"],
            )
            db.add(sale_item)

        if request.customer_id is not None:
            await db.execute(
                update(Customer)
                .where(
                    Customer.id == request.customer_id,
                    Customer.tenant_id == current_user.tenant_id,
                )
                .values(
                    visit_count=Customer.visit_count + 1,
                    total_spent_inr=Customer.total_spent_inr
                    + total_amount
                    + tax_amount,
                )
            )

        # Commit transaction
        await db.commit()
        await db.refresh(new_sale)

        # Refresh sale_items relationship
        await db.refresh(new_sale, ["sale_items"])

        # Broadcast real-time WebSocket event to all connected clients for this tenant
        await notify_sale(
            tenant_id=current_user.tenant_id,
            event_type="NEW_SALE",
            data={
                "sale_id": new_sale.id,
                "amount": float(new_sale.total_amount),
                "tax_amount": float(new_sale.tax_amount),
                "payment_method": payment_method.value,
                "item_count": sum(item["quantity"] for item in sale_items_data),
                "timestamp": new_sale.timestamp.isoformat(),
            },
        )

        return new_sale

    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=safe_error_detail(),
        )


async def notify_sale(**kwargs):
    """A notification outage must not turn a committed sale into a failed checkout."""
    import logging

    try:
        await connection_manager.broadcast_named_event(**kwargs)
    except Exception:
        logging.getLogger(__name__).exception(
            "Sale committed but realtime delivery failed"
        )


@router.get("", response_model=list[SaleResponse])
async def list_sales(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all sales for the authenticated user's restaurant.

    Uses tenant_id from get_current_user to ensure data isolation.
    Restaurant A can only see their own sales, not Restaurant B's.

    Results are ordered by timestamp (newest first) for recent transaction view.

    Args:
        current_user: Authenticated user with tenant context (injected)
        db: Database session (injected)
        limit: Maximum number of results (default 100)
        offset: Offset for pagination (default 0)

    Returns:
        List of sales belonging to the user's restaurant

    Raises:
        HTTPException 401: If user is not authenticated
    """

    try:
        # Query only sales for this user's tenant
        result = await db.execute(
            select(Sale)
            .options(selectinload(Sale.sale_items))
            .where(Sale.tenant_id == current_user.tenant_id)
            .order_by(Sale.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )

        sales = result.scalars().all()

        return sales

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=safe_error_detail(),
        )


@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(
    sale_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific sale by ID.

    Verifies the sale belongs to the authenticated user's restaurant.
    Prevents cross-tenant access.

    Args:
        sale_id: ID of the sale to retrieve
        current_user: Authenticated user with tenant context (injected)
        db: Database session (injected)

    Returns:
        Sale details with all line items

    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If sale belongs to different tenant
        HTTPException 404: If sale not found
    """

    try:
        # Query sale with tenant verification
        result = await db.execute(
            select(Sale).where(
                (Sale.id == sale_id) & (Sale.tenant_id == current_user.tenant_id)
            )
        )

        sale = result.scalar_one_or_none()

        if sale is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sale not found or access denied",
            )

        # Refresh relationships for response
        await db.refresh(sale, ["sale_items"])

        return sale

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=safe_error_detail(),
        )


from app.core.errors import safe_error_detail
