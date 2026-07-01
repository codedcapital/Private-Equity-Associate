"""add_deal_settings_table

Revision ID: 215b1f04d130
Revises: 46417ac6cab7
Create Date: 2026-07-02 00:34:45.023905

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '215b1f04d130'
down_revision: Union[str, Sequence[str], None] = '46417ac6cab7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('deal_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('deal_id', sa.Integer(), nullable=False),
    sa.Column('confidence_weights', sa.JSON(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['deal_id'], ['deal_pipeline.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('deal_id')
    )
    op.create_index('idx_deal_settings_deal_id', 'deal_settings', ['deal_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_deal_settings_deal_id', table_name='deal_settings')
    op.drop_table('deal_settings')
