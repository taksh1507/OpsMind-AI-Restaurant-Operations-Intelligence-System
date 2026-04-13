"""WebSocket Connection Manager for Real-Time Event Notifications

Day 26: The Real-Time Event Engine

Manages WebSocket connections per tenant for broadcasting real-time events
(new orders, staff notifications, live updates) across the restaurant.

Key Features:
- Multi-tenant isolation: Each tenant only receives their own events
- Connection tracking: Dictionary of active connections per tenant
- Broadcast capability: Send JSON messages to all connected clients
- Connection lifecycle: Handle connect/disconnect gracefully
- State synchronization: Keep backend (database) ↔ WebSocket ↔ frontend in sync
"""

import json
from typing import Dict, List, Callable
from fastapi import WebSocket, WebSocketDisconnect, status
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections with multi-tenant broadcast capability.
    
    Each restaurant (tenant) has its own pool of connections.
    When an event happens (e.g., new order), broadcast to all connections
    for that tenant only - ensuring data isolation.
    
    Attributes:
        active_connections: Dict[tenant_id] -> List[WebSocket connections]
        
    Thread Safety:
        WebSocket connections are async, handled by FastAPI's event loop.
        For production, consider redis pub/sub for distributed setups.
    """
    
    def __init__(self):
        """Initialize the connection manager with empty connection pools."""
        # Structure: {tenant_id: [websocket1, websocket2, ...]}
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, tenant_id: int):
        """
        Accept a WebSocket connection and track it by tenant.
        
        Args:
            websocket: FastAPI WebSocket object
            tenant_id: Restaurant ID to isolate connections by tenant
            
        Raises:
            HTTPException: If connection cannot be accepted
        """
        await websocket.accept()
        
        # Initialize tenant connection pool if not exists
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = []
        
        # Add this connection to the tenant's pool
        self.active_connections[tenant_id].append(websocket)
        
        logger.info(
            f"✅ WebSocket connected: tenant_id={tenant_id}, "
            f"total_connections={len(self.active_connections[tenant_id])}"
        )
    
    def disconnect(self, websocket: WebSocket, tenant_id: int):
        """
        Remove a WebSocket connection from active tracking.
        
        Called when a client disconnects (page refresh, logout, network error).
        
        Args:
            websocket: FastAPI WebSocket object to remove
            tenant_id: Restaurant ID
        """
        if tenant_id in self.active_connections:
            try:
                self.active_connections[tenant_id].remove(websocket)
                logger.info(
                    f"❌ WebSocket disconnected: tenant_id={tenant_id}, "
                    f"remaining={len(self.active_connections[tenant_id])}"
                )
                
                # Clean up empty tenant pools
                if len(self.active_connections[tenant_id]) == 0:
                    del self.active_connections[tenant_id]
            except ValueError:
                logger.warning(f"WebSocket not found in tenant {tenant_id}")
    
    async def broadcast(
        self,
        tenant_id: int,
        message: dict,
        sender_id: int = None
    ):
        """
        Broadcast a JSON message to all connected clients for a specific tenant.
        
        This is the core of real-time functionality. When something happens
        in the database (new order, table status change), use this to notify
        all connected staff.
        
        Args:
            tenant_id: Restaurant ID - only connections for this tenant receive message
            message: Dict containing event data (will be JSON encoded)
                Example: {"event": "NEW_ORDER", "amount": 1200, "table": 5}
            sender_id: Optional user ID that triggered this event (for acks)
            
        Returns:
            int: Number of successful sends
            
        Multi-Tenant Isolation:
            - Only sends to connections for this specific tenant_id
            - Two restaurants never see each other's events
            - Restaurant A can have multiple connections (multiple staff logged in)
        
        Real-Time Event Examples:
            - NEW_ORDER: Staff gets instant notification with order details
            - TABLE_READY: Chef tells manager when table is ready
            - ORDER_COMPLETE: Order goes from kitchen to ready-to-serve
            - PAYMENT_PROCESSED: Cashier confirms payment
        """
        if tenant_id not in self.active_connections:
            logger.debug(f"No active connections for tenant {tenant_id}")
            return 0
        
        # Add timestamp and event metadata
        enriched_message = {
            **message,
            "timestamp": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "tenant_id": tenant_id
        }
        
        failed_connections = []
        successful_sends = 0
        
        # Send to all connected clients for this tenant
        for websocket in self.active_connections[tenant_id]:
            try:
                await websocket.send_json(enriched_message)
                successful_sends += 1
            except Exception as e:
                logger.error(
                    f"Failed to send to websocket: {str(e)}. "
                    f"Marking for remove."
                )
                failed_connections.append(websocket)
        
        # Clean up dead connections
        for websocket in failed_connections:
            self.disconnect(websocket, tenant_id)
        
        logger.debug(
            f"📢 Broadcast sent: tenant_id={tenant_id}, "
            f"event={message.get('event')}, "
            f"recipients={successful_sends}"
        )
        
        return successful_sends
    
    async def broadcast_named_event(
        self,
        tenant_id: int,
        event_type: str,
        data: dict = None,
        **kwargs
    ):
        """
        Convenience method for broadcasting named events.
        
        Usage:
            await connection_manager.broadcast_named_event(
                tenant_id=1,
                event_type="NEW_ORDER",
                data={"amount": 1200, "table": 5}
            )
        
        Args:
            tenant_id: Restaurant ID
            event_type: Event name (NEW_ORDER, TABLE_READY, etc.)
            data: Event-specific data payload
            **kwargs: Additional fields to include
        """
        message = {
            "event": event_type,
            **(data or {}),
            **kwargs
        }
        return await self.broadcast(tenant_id, message)
    
    def get_connection_count(self, tenant_id: int = None) -> dict:
        """
        Get connection statistics for monitoring/debugging.
        
        Args:
            tenant_id: If specified, return count for just this tenant
            
        Returns:
            Dict with connection counts
        """
        if tenant_id is not None:
            count = len(self.active_connections.get(tenant_id, []))
            return {"tenant_id": tenant_id, "connections": count}
        
        return {
            "total_tenants": len(self.active_connections),
            "total_connections": sum(
                len(conns) for conns in self.active_connections.values()
            ),
            "by_tenant": {
                tid: len(conns)
                for tid, conns in self.active_connections.items()
            }
        }


# Global instance - shared across all WebSocket endpoints
connection_manager = ConnectionManager()
