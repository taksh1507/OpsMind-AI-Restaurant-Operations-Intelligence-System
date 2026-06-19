"""Customer API - Table-Side Intelligence Endpoint for Hyper-Personalized Service

Day 24: VIP Insight Agent
Provides a quick-access briefing for staff when a customer checks in.
Returns a 3-bullet-point "cheat sheet" with:
1. Lifetime Value (LTV) in ₹
2. Most ordered item
3. AI-generated conversation starter
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import joinedload
from app.models import Customer, Sale
from app.database import get_db
from app.services.ai_agent import AIConsultant
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/customers", tags=["customers"])


async def get_customer_order_history(
    customer_id: int,
    db: AsyncSession,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Fetch order history for a customer.
    
    Currently returns mock historical data based on visit count and preferences.
    In production, this would join with Sales/SaleItem tables after adding customer_id foreign key.
    
    Args:
        customer_id: Customer ID
        db: Database session
        limit: Maximum number of orders to return
    
    Returns:
        List of order dicts with item, quantity, date, price, etc.
    """
    # Fetch customer to get preferences
    customer = await db.scalar(select(Customer).where(Customer.id == customer_id))
    if not customer:
        return []
    
    # TODO: In production, query from Sales/SaleItem tables
    # For now, return sample order history based on customer profile
    order_history = []
    
    if customer.preferences:
        # If customer has preferences, use them as favorite items
        fav_items = customer.preferences.get('favorite_items', [])
        
        if isinstance(fav_items, list) and fav_items:
            # Mock order history from favorite items
            visit_range = min(customer.visit_count, 10)  # Last 10 visits at most
            for i in range(visit_range):
                item = fav_items[i % len(fav_items)] if len(fav_items) > 0 else fav_items[0]
                order_history.append({
                    "date": f"2026-03-{(30 - i):02d}",  # Mock dates
                    "item": item,
                    "quantity": 1,
                    "price": 200.0 + (i * 10),
                    "category": "order"
                })
    
    # If no preferences or empty, create default mock orders
    if not order_history:
        default_items = [
            "Paneer Chilly",
            "Butter Chicken",
            "Malai Kofta",
            "Biryani",
            "Samosa"
        ]
        visit_range = min(customer.visit_count, 10)
        for i in range(visit_range):
            order_history.append({
                "date": f"2026-03-{(30 - i):02d}",
                "item": default_items[i % len(default_items)],
                "quantity": 1,
                "price": 250.0,
                "category": "order"
            })
    
    return order_history[:limit]


@router.get("/{id}/briefing", response_model=dict, summary="Get Customer Table-Side Briefing")
async def get_customer_briefing(
    id: int,
    db: AsyncSession = Depends(get_db)
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
        # Fetch customer
        customer = await db.scalar(select(Customer).where(Customer.id == id))
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        # Calculate LTV (Lifetime Value)
        ltv = float(customer.total_spent_inr) if customer.total_spent_inr else 0.0

        # Fetch customer's order history
        order_history = await get_customer_order_history(id, db, limit=20)

        # Calculate most ordered item
        most_ordered_item = None
        item_counts: Dict[str, int] = {}
        
        if order_history:
            for order in order_history:
                item = order.get("item", "")
                if item:
                    item_counts[item] = item_counts.get(item, 0) + 1
            
            if item_counts:
                most_ordered_item = max(item_counts, key=item_counts.get)

        # Look up customer's tenant_id from their sales, defaulting to 1
        tenant_id = await db.scalar(select(Sale.tenant_id).where(Sale.customer_id == id).limit(1))
        if not tenant_id:
            tenant_id = 1

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
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating customer briefing: {str(e)}"
        )

