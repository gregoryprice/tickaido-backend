"""remove_redundant_is_deleted_columns_use_deleted_at_property

Revision ID: 41a9b6e2c5f2
Revises: 8ff51a371afb
Create Date: 2025-09-30 23:32:13.711600

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '41a9b6e2c5f2'
down_revision = '8ff51a371afb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove redundant is_deleted columns from all tables
    # is_deleted is now a computed property: deleted_at IS NOT NULL
    
    tables_to_update = [
        'agent_actions', 'agent_files', 'agent_history', 'agent_tasks', 
        'agent_usage_stats', 'agents', 'ai_agent_configs', 'api_tokens',
        'avatar_variants', 'file_storage_metadata', 'files', 'integrations',
        'messages', 'organization_invitations', 'organizations', 'threads',
        'tickets', 'users'
    ]
    
    for table_name in tables_to_update:
        op.drop_column(table_name, 'is_deleted')


def downgrade() -> None:
    # Restore is_deleted columns to all tables (if rollback is needed)
    
    tables_to_restore = [
        'agent_actions', 'agent_files', 'agent_history', 'agent_tasks', 
        'agent_usage_stats', 'agents', 'ai_agent_configs', 'api_tokens',
        'avatar_variants', 'file_storage_metadata', 'files', 'integrations',
        'messages', 'organization_invitations', 'organizations', 'threads',
        'tickets', 'users'
    ]
    
    for table_name in tables_to_restore:
        op.add_column(table_name, sa.Column('is_deleted', sa.Boolean(), 
                                           server_default=sa.text('false'), 
                                           nullable=False,
                                           comment='Soft delete flag (computed from deleted_at)'))
        
        # Populate is_deleted based on deleted_at values
        op.execute(f"""
            UPDATE {table_name} 
            SET is_deleted = CASE 
                WHEN deleted_at IS NOT NULL THEN true 
                ELSE false 
            END
        """)