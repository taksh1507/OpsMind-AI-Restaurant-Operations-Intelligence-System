"""WebSocket Endpoints for Real-Time Event Notifications

Day 26: The Real-Time Event Engine

Provides WebSocket endpoints for real-time communication with restaurants.
Handles authentication, connection pooling, and message broadcasting.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import json

from app.database import get_db
from app.models import User
from app.api.ws_manager import connection_manager
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["🔌 WebSocket Real-Time"])


async def get_current_user_from_ws(websocket: WebSocket) -> User:
    """
    Extract and validate JWT token from WebSocket connection.
    
    WebSocket connections include query parameter: ?token=<jwt>
    
    Args:
        websocket: WebSocket connection
        
    Returns:
        User object if valid
        
    Raises:
        Exception: If token invalid or user not found
    """
    token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="No token provided")
        raise Exception("No token provided")
    
    # Decode JWT
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        raise Exception("Invalid token")
    
    user_email = payload.get("sub")
    if not user_email:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        raise Exception("Invalid token")
    
    return user_email


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db)
):
    """
    Main WebSocket endpoint for real-time event notifications.
    
    Connection Flow:
    1. Client connects with JWT token in query params: ws://localhost:8000/ws?token=<jwt>
    2. Server validates token and extracts user
    3. Server looks up user and gets tenant_id
    4. Server adds connection to tenant's connection pool
    5. Server sends confirmation message
    6. Client receives real-time events for its tenant
    7. On disconnect or error, connection is removed from pool
    
    Real-Time Events Broadcast:
    - NEW_ORDER: New order created
    - NEW_SALE: Payment processed
    - TABLE_STATUS: Table status changed
    - STAFF_ALERT: General staff notification
    - SYSTEM_EVENT: System-level events
    
    Multi-Tenant Isolation:
    - Each WebSocket is associated with a tenant_id
    - Only events for that tenant are sent
    - No cross-restaurant data leakage
    
    Usage (Frontend):
    ```typescript
    const ws = new WebSocket(`ws://localhost:8000/ws?token=${jwtToken}`);
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.event === 'NEW_ORDER') {
            showToastNotification(`New order: ₹${data.amount}`);
            playSound('ding.mp3');
        }
    };
    ```
    """
    
    user_email = None
    tenant_id = None
    
    try:
        # Step 1: Authenticate user from token
        user_email = await get_current_user_from_ws(websocket)
        logger.info(f"WebSocket auth user: {user_email}")
        
        # Step 2: Look up user in database to get tenant_id
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.email == user_email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="User not found"
            )
            return
        
        if not user.is_active:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="User account inactive"
            )
            return
        
        tenant_id = user.tenant_id
        
        # Step 3: Register connection with ConnectionManager
        await connection_manager.connect(websocket, tenant_id)
        
        # Step 4: Send welcome message
        await websocket.send_json({
            "event": "CONNECTED",
            "message": f"Connected to real-time notifications for tenant {tenant_id}",
            "tenant_id": tenant_id,
            "user": user_email
        })
        
        logger.info(f"✅ WebSocket connected: {user_email} (tenant {tenant_id})")
        
        # Step 5: Keep connection open and listen for messages
        # (Most real-time use cases are server → client only, but we can accept
        # client messages for ping/pong or client-side events if needed)
        while True:
            try:
                data = await websocket.receive_text()
                
                # Handle client-side pings or other events
                if data == "ping":
                    await websocket.send_json({"event": "pong"})
                    logger.debug(f"Ping from {user_email}")
                else:
                    # Could implement client-initiated events here
                    logger.debug(f"Received from {user_email}: {data}")
            
            except WebSocketDisconnect:
                break
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {user_email}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    
    finally:
        # Step 6: Clean up connection
        if tenant_id is not None:
            connection_manager.disconnect(websocket, tenant_id)
            logger.info(f"❌ WebSocket cleanup: {user_email} (tenant {tenant_id})")
            logger.debug(f"Connection stats: {connection_manager.get_connection_count()}")


@router.get("/ws/stats")
async def get_websocket_stats(
    user: User = Depends(__import__("app.api.deps", fromlist=["get_current_user"]).get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get WebSocket connection statistics (admin only).
    
    Returns connection counts per tenant for monitoring.
    Useful for debugging or showing live user counts.
    """
    stats = connection_manager.get_connection_count()
    
    # If not admin, only return stats for user's tenant
    if user.role != "owner":  # Assuming 'owner' is admin role
        tenant_stats = connection_manager.get_connection_count(user.tenant_id)
        return {
            "your_connections": tenant_stats["connections"],
            "total_system": f"Contact support for system stats"
        }
    
    return stats
