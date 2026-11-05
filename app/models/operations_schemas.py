"""Validated inputs and explicit outputs for operational data entry."""

from datetime import datetime
from decimal import Decimal
import json
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    AwareDatetime,
    model_validator,
)

from app.models.staff import StaffRole
from app.models.menu import WasteReason

Money = Annotated[Decimal, Field(ge=0, le=999999, max_digits=10, decimal_places=2)]
Quantity = Annotated[float, Field(gt=0, le=1000000, allow_inf_nan=False)]
Identifier = Annotated[int, Field(gt=0)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CustomerInput(Input):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr = Field(max_length=255)
    preferences: dict[str, Any] = Field(default_factory=dict, max_length=30)

    @model_validator(mode="after")
    def bounded_preferences(self):
        if len(json.dumps(self.preferences, allow_nan=False)) > 8000:
            raise ValueError("Preferences must fit in 8000 characters of JSON")
        self.email = self.email.lower()
        return self


class CustomerOutput(CustomerInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    total_spent_inr: Decimal
    visit_count: int


class IngredientInput(Input):
    name: str = Field(min_length=1, max_length=100)
    unit: str = Field(min_length=1, max_length=20)
    unit_cost: Decimal = Field(ge=0, le=999999, max_digits=10, decimal_places=4)


class IngredientOutput(IngredientInput):
    model_config = ConfigDict(from_attributes=True)
    id: int


class RecipeInput(Input):
    menu_item_id: Identifier
    ingredient_id: Identifier
    quantity_used: Quantity


class RecipeOutput(RecipeInput):
    model_config = ConfigDict(from_attributes=True)
    id: int


class StaffInput(Input):
    name: str = Field(min_length=1, max_length=255)
    role: StaffRole = StaffRole.OTHER
    hourly_rate: Money
    is_active: bool = True
    phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


class StaffOutput(StaffInput):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ShiftInput(Input):
    staff_id: Identifier
    start_time: AwareDatetime
    end_time: AwareDatetime
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def valid_duration(self):
        hours = (self.end_time - self.start_time).total_seconds() / 3600
        if hours <= 0 or hours > 24:
            raise ValueError(
                "Shift duration must be greater than zero and at most 24 hours"
            )
        return self


class ShiftOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    staff_id: int
    start_time: datetime
    end_time: datetime
    notes: str | None


class WasteInput(Input):
    ingredient_id: Identifier
    quantity_wasted: Quantity
    reason: WasteReason
    cost_lost_inr: Money
    timestamp: AwareDatetime


class WasteOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ingredient_id: int
    quantity_wasted: float
    reason: WasteReason
    cost_lost_inr: Decimal
    timestamp: datetime


class ReviewInput(Input):
    customer_name: str = Field(default="Anonymous", min_length=1, max_length=255)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=1, max_length=10000)
    source: str = Field(default="internal", min_length=1, max_length=50)


class ReviewOutput(ReviewInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sentiment_score: Decimal | None
    is_processed: bool
    processed_at: datetime | None
    created_at: datetime
