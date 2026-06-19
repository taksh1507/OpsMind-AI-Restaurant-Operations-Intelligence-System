"""Persona Engine Service.

Predicts a customer's persona based on K-Means clustering when the model is trained,
and falls back to rule-based logic otherwise.
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime
import joblib
import pandas as pd
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.sales import Sale
from app.ml.segmentation_features import build_segmentation_features


def get_suggested_action_for_persona(persona: str) -> str:
    """Return an actionable suggestion based on customer persona."""
    actions = {
        "VIP Regular": "Offer a complimentary chef's special dessert and reserve their favorite table.",
        "Big Spender": "Recommend our premium wine pairing or high-margin signature dishes.",
        "At-Risk": "Offer a 15% discount coupon for their next visit to re-engage them.",
        "Occasional Visitor": "Suggest joining our loyalty program and highlight weekend specials.",
        "New Customer": "Welcome them warmly and offer a free appetizer on their next visit.",
        "Regular Customer": "Acknowledge their loyalty and offer a complimentary beverage."
    }
    return actions.get(persona, "Acknowledge their loyalty and offer a complimentary beverage.")


async def get_customer_persona(
    customer_id: int,
    session: AsyncSession,
    tenant_id: int
) -> Dict[str, Any]:
    """Get the customer's persona and recommended surprise & delight action.
    
    If the K-Means clustering model segments_v1.pkl is present for the tenant,
    assigns the persona using clustering inference. Otherwise, falls back
    to rule-based logic.
    
    Args:
        customer_id: ID of the customer
        session: Database session
        tenant_id: Tenant (restaurant) ID
        
    Returns:
        Dict matching response format:
            status: "success" or "error"
            persona: String persona name
            suggested_action: surprise & delight recommendation
            reasoning: Explanation details
    """
    # 1. Fetch Customer
    customer = await session.scalar(select(Customer).where(Customer.id == customer_id))
    if not customer:
        return {
            "status": "error",
            "persona": "Regular Customer",
            "reasoning": f"Customer ID {customer_id} not found in database",
            "suggested_action": "Welcome them warmly and ask about their preferences"
        }

    visit_count = int(customer.visit_count) if customer.visit_count else 0
    total_spent = float(customer.total_spent_inr) if customer.total_spent_inr else 0.0
    avg_spend = total_spent / visit_count if visit_count > 0 else 0.0

    # 2. Check for trained K-Means model
    from app.ml.manifest_helper import get_latest_model_path
    model_path = get_latest_model_path(tenant_id, "segmentation", "segments_v1.pkl")
    model_data = None
    if os.path.exists(model_path):
        try:
            model_data = joblib.load(model_path)
        except Exception as e:
            print(f"Error loading segmentation model: {e}")

    # 3. Load behavioral features for dynamic model inference
    df_features = await build_segmentation_features(session, tenant_id)
    cust_row = None
    if not df_features.empty and model_data is not None:
        cust_rows = df_features[df_features["customer_id"] == customer_id]
        if not cust_rows.empty:
            cust_row = cust_rows.iloc[0]

    # 4. Model Path Prediction
    if cust_row is not None and model_data is not None:
        try:
            preprocessor = model_data["preprocessor"]
            kmeans = model_data["model"]
            cluster_to_persona = model_data["cluster_to_persona"]
            features_cols = model_data["features_cols"]

            # Format input
            cust_df = pd.DataFrame([cust_row.to_dict()])
            X_cust = cust_df[features_cols]
            
            # Predict
            X_cust_preprocessed = preprocessor.transform(X_cust)
            cluster_id = int(kmeans.predict(X_cust_preprocessed)[0])
            
            persona = cluster_to_persona.get(cluster_id, "Regular Customer")
            suggested_action = get_suggested_action_for_persona(persona)
            reasoning = (
                f"Assigned K-Means cluster-based persona '{persona}' (cluster {cluster_id}) "
                f"based on spending patterns (avg spend: ₹{cust_row['avg_spend']:.2f}, "
                f"order frequency: {cust_row['order_frequency']} visits in last 90 days)."
            )

            return {
                "status": "success",
                "persona": persona,
                "suggested_action": suggested_action,
                "reasoning": reasoning
            }
        except Exception as e:
            print(f"Error predicting persona using model path: {e}")

    # 5. Fallback Path: Rule-Based Logic
    # Fetch last sale to calculate recency
    last_sale = await session.scalar(
        select(Sale)
        .where(Sale.customer_id == customer_id)
        .order_by(desc(Sale.timestamp))
        .limit(1)
    )
    if last_sale:
        last_ts = last_sale.timestamp
        if last_ts.tzinfo is not None:
            last_ts = last_ts.replace(tzinfo=None)
        recency_days = float((datetime.utcnow() - last_ts).days)
    else:
        recency_days = 999.0

    if visit_count >= 10 and total_spent >= 5000:
        persona = "VIP Regular"
    elif avg_spend >= 1500 or total_spent >= 8000:
        persona = "Big Spender"
    elif last_sale is not None and recency_days >= 30 and visit_count >= 2:
        persona = "At-Risk"
    elif visit_count <= 1:
        persona = "New Customer"
    else:
        persona = "Occasional Visitor"

    suggested_action = get_suggested_action_for_persona(persona)
    reasoning = (
        f"Assigned rule-based fallback persona '{persona}' (visit count: {visit_count}, "
        f"LTV: ₹{total_spent:.2f}, avg spend: ₹{avg_spend:.2f}, recency: {recency_days:.1f} days)."
    )

    return {
        "status": "success",
        "persona": persona,
        "suggested_action": suggested_action,
        "reasoning": reasoning
    }
