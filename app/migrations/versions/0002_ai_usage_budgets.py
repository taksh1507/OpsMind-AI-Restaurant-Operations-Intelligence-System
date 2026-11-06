"""Add atomic monthly AI token reservations and carry forward current usage."""
from datetime import datetime, timezone

from alembic import op
from sqlalchemy import func, insert, literal, select

from app.models.ai_usage import AIUsage
from app.models.ai_usage_budget import AIUsageBudget

revision = "0002_ai_usage_budgets"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade():
    AIUsageBudget.__table__.create(bind=op.get_bind(), checkfirst=True)
    period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    existing_usage = (
        select(
            AIUsage.tenant_id,
            literal(period_start, type_=AIUsageBudget.period_start.type),
            literal(0),
            func.sum(AIUsage.total_tokens),
        )
        .where(AIUsage.created_at >= period_start)
        .group_by(AIUsage.tenant_id)
    )
    op.get_bind().execute(
        insert(AIUsageBudget).from_select(
            ["tenant_id", "period_start", "tokens_reserved", "tokens_committed"],
            existing_usage,
        )
    )


def downgrade():
    AIUsageBudget.__table__.drop(bind=op.get_bind(), checkfirst=True)
