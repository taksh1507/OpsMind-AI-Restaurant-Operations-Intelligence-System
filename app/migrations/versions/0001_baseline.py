"""Create missing application tables and stamp pre-Alembic installations."""
from alembic import op
from sqlalchemy import Column, Integer, inspect

import app.models  # noqa: F401 - register all mapped tables
from app.models.base import Base
from app.migrations.customer_tenants import _schema_state

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # Existing installations are adopted in place; absent tables are created
    # from the current metadata so new installations start fully initialized.
    Base.metadata.create_all(bind=bind, checkfirst=True)
    schema = inspect(bind)
    if schema.has_table("users") and "token_version" not in {
        column["name"] for column in schema.get_columns("users")
    }:
        op.add_column("users", Column("token_version", Integer(), nullable=False, server_default="0"))
    if _schema_state(bind) == "legacy":
        raise RuntimeError(
            "Legacy global customers require migration: stop writers and run "
            "python -m scripts.migrate_customer_tenants before Alembic upgrade."
        )


def downgrade():
    # Baseline adoption is intentionally irreversible: pre-Alembic schemas have
    # no reliable prior revision to restore.
    pass
