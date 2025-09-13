"""Add has_custom_avatar field to agents table and storage backend settings

Revision ID: unified_storage_agent_avatar
Revises: f51e6981ada8
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'unified_storage_agent_avatar'
down_revision = 'd59a7b4f8ccd'
branch_labels = None
depends_on = None


def upgrade():
    # Add has_custom_avatar field to agents table
    op.add_column('agents', sa.Column(
        'has_custom_avatar',
        sa.Boolean(),
        nullable=False,
        server_default=sa.text('FALSE'),
        comment="Whether agent has a custom uploaded avatar"
    ))


def downgrade():
    # Remove has_custom_avatar field from agents table
    op.drop_column('agents', 'has_custom_avatar')