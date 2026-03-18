"""Category Management API Router

Handles CRUD operations for menu categories.
Uses get_current_user dependency to ensure tenant isolation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.api.deps import get_current_user
from app.models import User, Category
from app.models.schemas import CategoryCreate, CategoryResponse, CategoryUpdate


router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    request: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new menu category for the authenticated user's restaurant.
    
    The tenant_id is automatically extracted from the JWT token via get_current_user.
    This ensures the category belongs to the authenticated user's restaurant.
    
    Args:
        request: Category creation request
        current_user: Authenticated user with tenant context (injected)
        db: Database session (injected)
        
    Returns:
        Created category with all details
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 500: If database error occurs
    """
    try:
        # Create new category scoped to user's tenant
        new_category = Category(
            tenant_id=current_user.tenant_id,  # Auto-scoped to user's restaurant
            name=request.name,
            description=request.description,
            is_active=request.is_active
        )
        
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)
        
        return new_category
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create category"
        )


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all menu categories for the authenticated user's restaurant.
    
    Uses tenant_id from get_current_user to ensure data isolation.
    Restaurant A can only see their own categories, not Restaurant B's.
    
    Args:
        current_user: Authenticated user with tenant context (injected)
        db: Database session (injected)
        
    Returns:
        List of categories belonging to the user's restaurant
        
    Raises:
        HTTPException 401: If user is not authenticated
    """
    try:
        # Query only categories for this user's tenant
        result = await db.execute(
            select(Category)
            .where(Category.tenant_id == current_user.tenant_id)
            .where(Category.is_active == True)
            .order_by(Category.created_at)
        )
        
        categories = result.scalars().all()
        return categories
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve categories"
        )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific category by ID.
    
    Verifies the category belongs to the authenticated user's restaurant.
    Prevents cross-tenant access (Restaurant A cannot see Restaurant B's categories).
    
    Args:
        category_id: ID of the category to retrieve
        current_user: Authenticated user with tenant context (injected)
        db: Database session (injected)
        
    Returns:
        Category details
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If category belongs to different tenant
        HTTPException 404: If category not found
    """
    try:
        # Query category with both ID and tenant_id (security check)
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
                detail="Category not found or access denied"
            )
        
        return category
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category"
        )


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    request: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a menu category.
    
    Only allows updating categories that belong to the authenticated user's restaurant.
    
    Args:
        category_id: ID of the category to update
        request: Updated category data
        current_user: Authenticated user with tenant context (injected)
        db: Database session (injected)
        
    Returns:
        Updated category
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If category belongs to different tenant
        HTTPException 404: If category not found
    """
    try:
        # Verify category belongs to user's tenant
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
                detail="Category not found or access denied"
            )
        
        # Update allowed fields
        if request.name is not None:
            category.name = request.name
        if request.description is not None:
            category.description = request.description
        if request.is_active is not None:
            category.is_active = request.is_active
        
        await db.commit()
        await db.refresh(category)
        
        return category
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category"
        )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a menu category.
    
    Only allows deleting categories that belong to the authenticated user's restaurant.
    Cascading delete removes all associated menu items.
    
    Args:
        category_id: ID of the category to delete
        current_user: Authenticated user with tenant context (injected)
        db: Database session (injected)
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If category belongs to different tenant
        HTTPException 404: If category not found
    """
    try:
        # Verify category belongs to user's tenant
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
                detail="Category not found or access denied"
            )
        
        await db.delete(category)
        await db.commit()
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete category"
        )
