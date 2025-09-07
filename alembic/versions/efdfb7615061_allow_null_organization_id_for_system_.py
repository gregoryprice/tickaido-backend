"""Allow NULL organization_id for system agents

This migration modifies the agents table to allow NULL organization_id 
for system-wide agents that serve all organizations.

Revision ID: efdfb7615061
Revises: c740f9fb4b4b
Create Date: 2025-09-05 22:09:45.763969

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'efdfb7615061'
down_revision = '5c5af32e4312'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Allow NULL organization_id for system agents"""
    # Modify organization_id column to allow NULL values for system agents
    op.alter_column('agents', 'organization_id',
                    existing_type=sa.UUID(),
                    nullable=True,
                    existing_nullable=False)


def downgrade() -> None:
    """Revert organization_id to NOT NULL (may fail if system agents exist)"""
    # Note: This downgrade may fail if there are system agents with NULL organization_id
    op.alter_column('agents', 'organization_id',
                    existing_type=sa.UUID(),
                    nullable=False,
                    existing_nullable=True)