from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from decimal import Decimal

class CustomerSchema(BaseModel):
    id: int
    name: str
    email: EmailStr
    total_spent_inr: Decimal
    visit_count: int
    preferences: Dict[str, Any]

    class Config:
        from_attributes = True
