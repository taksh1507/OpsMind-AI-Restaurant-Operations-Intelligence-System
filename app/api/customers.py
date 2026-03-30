"""Customer API - Table-Side Intelligence Endpoint

Provides a quick-access briefing for staff when a customer checks in.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import Customer, CustomerSchema
from app.api.deps import get_async_db
from app.services.ai_agent import AIConsultant

router = APIRouter(prefix="/customers", tags=["customers"])

@router.get("/{id}/briefing", response_model=dict)
async def get_customer_briefing(id: int, db: AsyncSession = Depends(get_async_db)):
    # Fetch customer
    customer = await db.scalar(select(Customer).where(Customer.id == id))
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Calculate LTV (total_spent_inr)
    ltv = float(customer.total_spent_inr)

    # Fetch most ordered item
    order_history = []  # TODO: Replace with real order history query
    most_ordered_item = None
    if order_history:
        item_counts = {}
        for order in order_history:
            item = order.get("item")
            item_counts[item] = item_counts.get(item, 0) + 1
        most_ordered_item = max(item_counts, key=item_counts.get)
    else:
        most_ordered_item = None

    # AI-generated conversation starter
    ai = AIConsultant()
    persona_result = await ai.get_customer_persona(
        customer={
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "total_spent_inr": ltv,
            "visit_count": customer.visit_count,
            "preferences": customer.preferences,
        },
        order_history=order_history
    )
    conversation_starter = None
    if persona_result.get("status") == "success":
        persona = persona_result.get("persona")
        suggested_action = persona_result.get("suggested_action")
        if persona and suggested_action:
            conversation_starter = f"[{persona}] {suggested_action}"
        else:
            conversation_starter = persona_result.get("raw_response")
    else:
        conversation_starter = "Welcome back! Ready for your usual?"

    # Build cheat sheet
    return {
        "cheat_sheet": [
            f"Lifetime Value (LTV): ₹{ltv:,.2f}",
            f"Most ordered item: {most_ordered_item or 'N/A'}",
            f"AI: {conversation_starter}"
        ]
    }
