"""Staff & Shift Models - Labor Cost Tracking

Represents restaurant staff and their work shifts.
Enables labor cost analysis against sales volume.
"""

from typing import Optional
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy import String, ForeignKey, Numeric, DateTime, func, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import BaseModel


class StaffRole(str, enum.Enum):
    """Staff position types in the restaurant."""
    CHEF = "chef"
    SOUS_CHEF = "sous_chef"
    LINE_COOK = "line_cook"
    PREP_COOK = "prep_cook"
    WAITER = "waiter"
    BARTENDER = "bartender"
    HOST = "host"
    BUSSER = "busser"
    DISHWASHER = "dishwasher"
    MANAGER = "manager"
    ASSISTANT_MANAGER = "assistant_manager"
    OTHER = "other"


class Staff(BaseModel):
    """
    A restaurant staff member.
    
    Attributes:
        id: Unique auto-incremented identifier
        tenant_id: Foreign key to parent tenant (restaurant) - CRITICAL FOR ISOLATION
        name: Employee name
        role: Job position (Chef, Waiter, Manager, etc.)
        hourly_rate: Hourly wage in dollars
        is_active: Whether the employee is currently employed
        start_date: When employee was hired
        end_date: When employee left (if terminated)
        phone: Contact number
        email: Employee email
        notes: Additional information
        shifts: Relationship to work shifts
        created_at: Timestamp when created
        updated_at: Timestamp of last update
    """
    
    __tablename__ = "staff"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True  # Index for fast filtering by tenant
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    role: Mapped[StaffRole] = mapped_column(
        Enum(StaffRole),
        nullable=False,
        default=StaffRole.OTHER
    )
    
    hourly_rate: Mapped[Decimal] = mapped_column(
        Numeric(precision=8, scale=2),
        nullable=False,
        default=Decimal("15.00")
    )
    
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True  # Index for quick active staff filtering
    )
    
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow,
        nullable=False
    )
    
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None
    )
    
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    shifts = relationship("Shift", back_populates="staff", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Staff(id={self.id}, name={self.name}, role={self.role}, rate=${self.hourly_rate})>"
    
    @property
    def role_label(self) -> str:
        """Get human-readable role label."""
        return self.role.value.replace("_", " ").title()


class Shift(BaseModel):
    """
    A work shift for a staff member.
    
    Attributes:
        id: Unique auto-incremented identifier
        staff_id: Foreign key to staff member
        start_time: When the shift started
        end_time: When the shift ended
        duration_hours: Calculated hours worked (float)
        total_cost: Calculated labor cost (hours * hourly_rate)
        notes: Shift notes (e.g., "Covered for sick employee")
        created_at: When the shift was recorded
        updated_at: Last updated timestamp
    """
    
    __tablename__ = "shifts"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    staff_id: Mapped[int] = mapped_column(
        ForeignKey("staff.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True  # Index for time-based queries
    )
    
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Relationships
    staff = relationship("Staff", back_populates="shifts", foreign_keys=[staff_id])
    
    def __repr__(self) -> str:
        return f"<Shift(id={self.id}, staff_id={self.staff_id}, duration={self.duration_hours}h, cost=${self.total_cost})>"
    
    @property
    def duration_hours(self) -> float:
        """Calculate hours worked (as float for partial hours)."""
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600.0
    
    @property
    def total_cost(self) -> Decimal:
        """Calculate total labor cost for this shift."""
        if not self.staff:
            return Decimal("0.00")
        
        hours = Decimal(str(round(self.duration_hours, 2)))
        cost = hours * self.staff.hourly_rate
        return cost.quantize(Decimal("0.01"))
    
    @property
    def is_ongoing(self) -> bool:
        """Check if shift is currently in progress."""
        now = datetime.utcnow()
        return self.start_time <= now <= self.end_time
    
    @property
    def is_future(self) -> bool:
        """Check if shift is in the future."""
        now = datetime.utcnow()
        return self.start_time > now
    
    @property
    def is_past(self) -> bool:
        """Check if shift has ended."""
        now = datetime.utcnow()
        return self.end_time < now
