"""Customer API - Table-Side Intelligence Endpoint for Hyper-Personalized Service

Day 24: VIP Insight Agent
Provides a quick-access briefing for staff when a customer checks in.
Returns a 3-bullet-point "cheat sheet" with:
1. Lifetime Value (LTV) in ₹
2. Most ordered item
3. AI-generated conversation starter
"""

from app.core.errors import safe_error_detail
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Customer, Sale, SaleItem, MenuItem, Category, User
from app.database import get_db
from app.api.deps import get_current_user
from typing import Dict, Any, List

router = APIRouter(prefix="/customers", tags=["customers"])


async def get_customer_order_history(
    customer_id: int,
    db: AsyncSession,
    tenant_id: int,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Read real line items, validating the owner of every joined resource."""
    result = await db.execute(
        select(Sale.timestamp, SaleItem.quantity, SaleItem.unit_price_at_sale,
               MenuItem.name, Category.name.label("category"))
        .select_from(Sale).join(Customer, Sale.customer_id == Customer.id)
        .join(SaleItem, SaleItem.sale_id == Sale.id)
        .outerjoin(MenuItem, (MenuItem.id == SaleItem.menu_item_id) & (MenuItem.tenant_id == tenant_id))
        .outerjoin(Category, (Category.id == MenuItem.category_id) & (Category.tenant_id == tenant_id))
        .where(Customer.id == customer_id, Customer.tenant_id == tenant_id,
               Sale.tenant_id == tenant_id, SaleItem.tenant_id == tenant_id)
        .order_by(Sale.timestamp.desc(), Sale.id.desc(), SaleItem.id.desc()).limit(limit)
    )
    return [{"date": row.timestamp.isoformat(), "item": row.name or "Deleted menu item",
             "quantity": row.quantity, "price": float(row.unit_price_at_sale),
             "category": row.category or "Unknown"} for row in result]


@router.get("/{id}/briefing", response_model=dict, summary="Get Customer Table-Side Briefing")
async def get_customer_briefing(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get a 3-bullet "cheat sheet" for staff when a VIP customer checks in.
    
    Day 24: VIP Insight Agent
    
    This endpoint returns:
    1. **Lifetime Value (LTV)**: Total amount customer has spent in ₹
    2. **Most Ordered Item**: Customer's favorite/most frequent order
    3. **AI Conversation Starter**: Personalized greeting/recommendation from AI analysis
    
    Response Format:
    ```json
    {
        "status": "success",
        "customer_id": 1,
        "cheat_sheet": [
            "Lifetime Value (LTV): ₹5,400.00",
            "Most ordered item: Paneer Chilly",
            "AI: [High-Value Regular] Welcome back! We have a new Malai Kofta - perfect for your spicy preference"
        ],
        "persona": "High-Value Regular",
        "total_visits": 5,
        "ai_reasoning": "Based on 5 visits with consistent preference for spicy items..."
    }
    ```
    """
    try:
        tenant_id = current_user.tenant_id

        customer = await db.scalar(select(Customer).where(
            Customer.id == id, Customer.tenant_id == tenant_id
        ))
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        # Calculate LTV (Lifetime Value)
        ltv = float(customer.total_spent_inr) if customer.total_spent_inr else 0.0

        # Fetch customer's order history
        order_history = await get_customer_order_history(id, db, tenant_id, limit=20)

        # Calculate most ordered item
        most_ordered_item = None
        item_counts: Dict[str, int] = {}
        
        if order_history:
            for order in order_history:
                item = order.get("item", "")
                if item:
                    item_counts[item] = item_counts.get(item, 0) + order.get("quantity", 0)
            
            if item_counts:
                most_ordered_item = max(item_counts, key=item_counts.get)

        # Generate K-Means or rule-based persona
        from app.services.persona_engine import get_customer_persona as get_segmented_persona
        persona_result = await get_segmented_persona(
            customer_id=id,
            session=db,
            tenant_id=tenant_id
        )

        # Build conversation starter
        conversation_starter = "Welcome back!"
        persona = "Regular Customer"
        ai_reasoning = ""
        
        if persona_result.get("status") == "success":
            persona = persona_result.get("persona", "Regular Customer")
            suggested_action = persona_result.get("suggested_action", "")
            ai_reasoning = persona_result.get("reasoning", "")
            
            if persona and suggested_action:
                conversation_starter = f"[{persona}] {suggested_action}"
            else:
                conversation_starter = suggested_action or "Welcome back!"

        # Build the 3-bullet cheat sheet for server
        return {
            "status": "success",
            "customer_id": id,
            "customer_name": customer.name,
            "total_visits": customer.visit_count,
            "cheat_sheet": [
                f"👤 LTV: ₹{ltv:,.2f}",
                f"🍽️ Favorite: {most_ordered_item or 'Varied'}",
                f"🤖 AI: {conversation_starter}"
            ],
            "persona": persona,
            "ltv": ltv,
            "favorite_item": most_ordered_item,
            "suggested_action": persona_result.get("suggested_action"),
            "ai_reasoning": ai_reasoning,
            "preferences": customer.preferences or {},
            "order_history_sample": order_history[:5] if order_history else []
        }
    
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=safe_error_detail()
        )

