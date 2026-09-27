"""Team / User Management API Router

Owner-driven staff & manager account management, scoped to the owner's tenant.

- POST   /users        Create a staff/manager login (OWNER only)
- GET    /users        List the tenant's team (OWNER or MANAGER)
- PUT    /users/{id}   Update a teammate's role / active status (OWNER only)
- DELETE /users/{id}   Remove a teammate (OWNER only)

Mutations are OWNER-only to keep account creation and permission changes in the
owner's hands (the product's "owner creates staff and their access" model).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_owner, get_current_manager
from app.models import User
from app.models.schemas import (
    TeamMemberResponse,
    CreateTeamMemberRequest,
    CreateTeamMemberResponse,
    UpdateTeamMemberRequest,
)
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[TeamMemberResponse])
async def list_team(
    current_user: User = Depends(get_current_manager),
    db: AsyncSession = Depends(get_db),
):
    """List everyone on the current tenant's team (owner + managers can view)."""
    return await user_service.list_team_members(db, current_user.tenant_id)


@router.post(
    "",
    response_model=CreateTeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_team_member(
    request: CreateTeamMemberRequest,
    current_user: User = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Create a staff/manager login and return its one-time temporary password.

    The password is returned only in this response; it is never retrievable
    again. The teammate must change it on first login.
    """
    try:
        member, temp_password = await user_service.create_team_member(
            db,
            owner=current_user,
            email=request.email,
            role=request.role,
            temp_password=request.temp_password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return CreateTeamMemberResponse(
        member=TeamMemberResponse.model_validate(member),
        temp_password=temp_password,
    )


@router.put("/{user_id}", response_model=TeamMemberResponse)
async def update_team_member(
    user_id: int,
    request: UpdateTeamMemberRequest,
    current_user: User = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Update a teammate's preset role and/or active status (owner only)."""
    try:
        return await user_service.update_team_member(
            db,
            owner=current_user,
            user_id=user_id,
            role=request.role,
            is_active=request.is_active,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team_member(
    user_id: int,
    current_user: User = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Remove a teammate from the tenant (owner only)."""
    try:
        await user_service.delete_team_member(db, current_user, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
