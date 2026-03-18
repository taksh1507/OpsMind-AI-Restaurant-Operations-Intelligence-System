"""Menu Item Management API Router

Handles CRUD operations for menu items with cross-tenant security validation.
Uses get_current_user dependency to ensure tenant isolation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal

from app.database import get_db
from app.api.deps import get_current_user
from app.models import User, MenuItem, Category
from app.models.schemas import MenuItemCreate, MenuItemResponse, MenuItemUpdate


router = APIRouter(prefix="/menu-items", tags=["menu-items"])


async def verify_category_ownership(
    category_id: int,
    current_user: User,
    db: AsyncSession
) -> Category:
    """Verify that a category belongs to the authenticated user's tenant.
    
    This is CRITICAL for preventing cross-tenant category hijacking.
    Restaurant A cannot create menu items in Restaurant B's categories.
    
    Args:
        category_id: ID of the category to verify
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Category object if it belongs to user's tenant
        
    Raises:
        HTTPException 404: If category not found or belongs to different tenant
    """
    result = await db.execute(
        select(Category).where(
            (Category.id == category_id) &
            (Category.tenant_id == current_user.tenant_id)
        )
    )
    
    category = result.scalar_one_or_none()
    
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or does not belong to your restaurant"
        )
    
    return category


@router.post("", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    request: MenuItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new menu item.
    
    Security Checks:
    1. Verify the category_id belongs to the authenticated user's tenant
    2. Validate that price > cost_price for profit calculation
    3. Auto-scope the menu item to the user's tenant
    
    Args:
        request: Menu item creation request
        current_user: Authenticated user with tenant context (injected)
        db: Database session (injected)
        
    Returns:
        Created menu item with all details
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 400: If price <= cost_price
        HTTPException 404: If category doesn't belong to user's tenant
        HTTPException 500: If database error occurs
    """
    
    # Validate price > cost_price
    if request.price <= request.cost_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="price must be greater than cost_price"
        )
    
    # CRITICAL: Verify category belongs to user's tenant
    # This prevents Restaurant A from adding items to Restaurant B's categories
    category = await verify_category_ownership(
        request.category_id,
        current_user,
        db
    )
    
    try:
        # Create new menu item scoped to user's tenant
        new_item = MenuItem(
            tenant_id=current_user.tenant_id,  # Auto-scoped to user's restaurant
            category_id=request.category_id,
            name=request.name,
            description=request.description,
            price=request.price,
            cost_price=request.cost_price,
            is_available=request.is_available
        )
        
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        
        return new_item
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create menu item"
        )


@router.get("", response_model=list[MenuItemResponse])
async def list_menu_items(
    category_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all menu items for the authenticated user's restaurant.
    
    Uses tenant_id from get_current_user to ensure data isolation.
    Restaurant A can only see their own items, not Restaurant B's.
    
    Optional category_id filter to get items from a specific category.
    
    Args:
        category_id: Optional category ID to filter items
        current_user: Authenticated user with tenant context (injected)
        db: Database session (injected)
        
    Returns:
        List of menu items belonging to the user's restaurant
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 404: If category doesn't belong to user (if filtered)
    """
    
    try:
        # Build base query: only items for this user's tenant
        query = select(MenuItem).where(
            (MenuItem.tenant_id == current_user.tenant_id) &
            (MenuItem.is_available == True)
        )
        
        # Optional: filter by category_id with ownership verification
        if category_id is not None:
            # Verify category belongs to user before showing items
            await verify_category_ownership(category_id, current_user, db)
            
            query = query.where(MenuItem.category_id == category_id)
        
        query = query.order_by(MenuItem.created_at)
        
        result = await db.execute(query)
        items = result.scalars().all()
        
        return items
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve menu items"
        )


@router.get("/{item_id}", response_model=MenuItemResponse)
async def get_menu_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific menu item by ID.
    
    Verifies the item belongs to the authenticated user's restaurant.
    Prevents cross-tenant access.
    
    Args:
        item_id: ID of the menu item to retrieve
        current_user: Authenticated user with tenant context (injected)
        db: Database session (injected)
        
    Returns:
        Menu item details
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If item belongs to different tenant
        HTTPException 404: If item not found
    """
    
    try:
        result = await db.execute(
            select(MenuItem).where(
                (MenuItem.id == item_id) &
                (MenuItem.tenant_id == current_user.tenant_id)
            )
        )
        
        item = result.scalar_one_or_none()
        
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found or access denied"
            )
        
        return item
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve menu item"
        )


@router.put("/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    item_id: int,
    request: MenuItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a menu item.
    
    Security Checks:
    1. Verify item belongs to authenticated user's tenant
    2. Validate price > cost_price if both are being updated
    
    Args:
        item_id: ID of the menu item to update
        request: Updated menu item data
        current_user: Authenticated user with tenant context (injected)
        db: Database session (injected)
        
    Returns:
        Updated menu item
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 400: If price <= cost_price
        HTTPException 403: If item belongs to different tenant
        HTTPException 404: If item not found
    """
    
    try:
        # Verify item belongs to user's tenant
        result = await db.execute(
            select(MenuItem).where(
                (MenuItem.id == item_id) &
                (MenuItem.tenant_id == current_user.tenant_id)
            )
        )
        
        item = result.scalar_one_or_none()
        
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found or access denied"
            )
        
        # Validate price > cost_price if updating price fields
        new_price = request.price if request.price is not None else item.price
        new_cost_price = request.cost_price if request.cost_price is not None else item.cost_price
        
        if new_price <= new_cost_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="price must be greater than cost_price"
            )
        
        # Update allowed fields
        if request.name is not None:
            item.name = request.name
        if request.description is not None:
            item.description = request.description
        if request.price is not None:
            item.price = request.price
        if request.cost_price is not None:
            item.cost_price = request.cost_price
        if request.is_available is not None:
            item.is_available = request.is_available
        
        await db.commit()
        await db.refresh(item)
        
        return item
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update menu item"
        )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a menu item.
    
    Only allows deleting items that belong to the authenticated user's restaurant.
    
    Args:
        item_id: ID of the menu item to delete
        current_user: Authenticated user with tenant context (injected)
        db: Database session (injected)
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If item belongs to different tenant
        HTTPException 404: If item not found
    """
    
    try:
        # Verify item belongs to user's tenant
        result = await db.execute(
            select(MenuItem).where(
                (MenuItem.id == item_id) &
                (MenuItem.tenant_id == current_user.tenant_id)
            )
        )
        
        item = result.scalar_one_or_none()
        
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found or access denied"
            )
        
        await db.delete(item)
        await db.commit()
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete menu item"
        )
