"""allow_null_organization_id_for_system_agents

Revision ID: 003_system_agents
Revises: 002_complete
Create Date: 2025-10-01 21:04:13.984270

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_system_agents'
down_revision = '002_complete'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Allow NULL organization_id for system-wide agents
    # System agents like title generation don't belong to specific organizations
    op.alter_column('agents', 'organization_id',
               existing_type=sa.UUID(),
               nullable=True,
               existing_nullable=False,
               comment='Organization this agent belongs to (NULL for system agents)')


def downgrade() -> None:
    # Note: This downgrade might fail if system agents with NULL organization_id exist
    # You would need to assign them to organizations or delete them first
    op.alter_column('agents', 'organization_id',
               existing_type=sa.UUID(),
               nullable=False,
               existing_nullable=True,
               comment='Organization this agent belongs to')