"""cleanup_old_attachment_columns_and_finalize_schema

Revision ID: e0e4af067228
Revises: 8a89d9de47f3
Create Date: 2025-09-16 16:03:42.620244

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e0e4af067228'
down_revision = '8a89d9de47f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove old file_ids column from tickets after data migration verification
    op.drop_column('tickets', 'file_ids')
    
    # For messages: drop old attachments column and rename attachments_v2 to attachments
    op.drop_column('messages', 'attachments')  # Drop the old generic attachments column
    op.alter_column('messages', 'attachments_v2', new_column_name='attachments')
    
    # Update index name to match the new column name  
    op.execute("DROP INDEX IF EXISTS idx_messages_attachments_v2")
    op.execute("CREATE INDEX idx_messages_attachments ON messages USING gin ((attachments::jsonb) jsonb_path_ops)")


def downgrade() -> None:
    # Reverse the cleanup - restore old structure
    
    # Restore indexes and column structure for messages
    op.execute("DROP INDEX IF EXISTS idx_messages_attachments")
    op.alter_column('messages', 'attachments', new_column_name='attachments_v2')
    op.execute("CREATE INDEX idx_messages_attachments_v2 ON messages USING gin ((attachments_v2::jsonb) jsonb_path_ops)")
    
    # Restore the old generic attachments column (nullable JSON)
    op.add_column('messages', sa.Column('attachments', sa.JSON(), nullable=True))
    
    # Restore file_ids column to tickets
    op.add_column('tickets', sa.Column('file_ids', sa.JSON(), nullable=True, 
                  comment="Array of file IDs associated with this ticket"))