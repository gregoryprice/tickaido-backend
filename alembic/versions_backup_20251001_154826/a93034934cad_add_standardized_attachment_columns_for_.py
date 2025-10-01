"""add_standardized_attachment_columns_for_messages_and_tickets

Revision ID: a93034934cad
Revises: c4175ea2cf6a
Create Date: 2025-09-16 16:02:42.687075

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a93034934cad'
down_revision = 'c4175ea2cf6a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new standardized attachment columns per PRP requirements
    
    # Add attachments_v2 column to messages for new format
    op.add_column('messages', sa.Column('attachments_v2', sa.JSON(), nullable=True, 
                  comment='Array of file references: [{"file_id":"uuid"}]'))
    
    # Add attachments column to tickets for new format  
    op.add_column('tickets', sa.Column('attachments', sa.JSON(), nullable=True,
                  comment='Array of file references: [{"file_id":"uuid"}]'))
    
    # Add GIN indexes for JSON query performance (using jsonb_path_ops for better performance)
    op.execute("CREATE INDEX idx_messages_attachments_v2 ON messages USING gin ((attachments_v2::jsonb) jsonb_path_ops)")
    op.execute("CREATE INDEX idx_tickets_attachments ON tickets USING gin ((attachments::jsonb) jsonb_path_ops)")


def downgrade() -> None:
    # Reverse the attachment column additions
    
    # Drop custom indexes first
    op.execute("DROP INDEX IF EXISTS idx_tickets_attachments")
    op.execute("DROP INDEX IF EXISTS idx_messages_attachments_v2")
    
    # Drop the new attachment columns
    op.drop_column('tickets', 'attachments')
    op.drop_column('messages', 'attachments_v2')