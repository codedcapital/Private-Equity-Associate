"""Add decision_output to intelligence_hubs

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-07-02 12:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add decision_output JSON column to intelligence_hubs."""
    op.add_column(
        "intelligence_hubs",
        sa.Column("decision_output", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Remove decision_output column from intelligence_hubs."""
    op.drop_column("intelligence_hubs", "decision_output")
