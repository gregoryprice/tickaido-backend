"""migrate_existing_ticket_file_ids_to_attachments_format

Revision ID: 8a89d9de47f3
Revises: a93034934cad
Create Date: 2025-09-16 16:03:21.039592

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8a89d9de47f3'
down_revision = 'a93034934cad'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Migrate existing ticket file_ids to new attachments format
    # Convert JSON array of UUIDs to array of objects with file_id property
    
    op.execute("""
        UPDATE tickets 
        SET attachments = (
            SELECT json_agg(json_build_object('file_id', file_id::text))
            FROM json_array_elements_text(file_ids::json) AS file_id
        ) 
        WHERE file_ids IS NOT NULL 
          AND file_ids::text != 'null' 
          AND file_ids::text != '[]'
          AND jsonb_array_length(file_ids::jsonb) > 0
    """)


def downgrade() -> None:
    # Reverse the migration - convert attachments back to file_ids format
    # Extract file_id values from objects back to simple UUID array
    
    op.execute("""
        UPDATE tickets 
        SET file_ids = (
            SELECT json_agg(attachment->>'file_id')
            FROM json_array_elements(attachments::json) AS attachment
            WHERE attachment->>'file_id' IS NOT NULL
        )
        WHERE attachments IS NOT NULL 
          AND attachments::text != 'null' 
          AND attachments::text != '[]'
          AND jsonb_array_length(attachments::jsonb) > 0
    """)