"""redesign_ticket_comments_for_generic_platform_support_with_markdown

Revision ID: 5f24b7aa71a4
Revises: 41a9b6e2c5f2
Create Date: 2025-10-01 00:05:37.654106

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f24b7aa71a4'
down_revision = '41a9b6e2c5f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Redesign ticket_comments table for generic platform support with markdown
    
    # Drop the existing table to recreate with new schema
    op.drop_table('ticket_comments')
    
    # Recreate with new generic schema
    op.create_table('ticket_comments',
        sa.Column('id', sa.UUID(), 
                 server_default=sa.text('gen_random_uuid()'), 
                 nullable=False,
                 comment='Primary key for comment'),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                 server_default=sa.text('NOW()'), 
                 nullable=False,
                 comment='Timestamp when comment was created'),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                 server_default=sa.text('NOW()'), 
                 nullable=False,
                 comment='Timestamp when comment was last updated'),
        sa.Column('ticket_id', sa.UUID(), 
                 nullable=False,
                 comment='Reference to parent ticket'),
        sa.Column('external_comment_id', sa.Text(), 
                 nullable=True,
                 comment='External platform comment ID for synchronization (JIRA, ServiceNow, etc.)'),
        sa.Column('integration_id', sa.UUID(),
                 nullable=True,
                 comment='Integration platform this comment was synchronized with'),
        sa.Column('author_email', sa.Text(), 
                 nullable=False,
                 comment='Email address of comment author'),
        sa.Column('author_display_name', sa.Text(), 
                 nullable=True,
                 comment='Display name of comment author'),
        sa.Column('body', sa.Text(), 
                 nullable=False,
                 comment='Comment content (supports text and markdown)'),
        sa.Column('body_html', sa.Text(),
                 nullable=True,
                 comment='Rendered HTML version of content'),
        sa.Column('external_format_data', sa.JSON(),
                 nullable=True,
                 comment='Platform-specific formatted content (e.g., ADF for JIRA, rich text for ServiceNow)'),
        sa.Column('is_internal', sa.Boolean(), 
                 server_default=sa.text('false'), 
                 nullable=False,
                 comment='Whether comment is internal-only or visible to customers'),
        # BaseModel inherited fields (excluding redundant is_deleted)
        sa.Column('notes', sa.Text(),
                 nullable=True,
                 comment='Internal notes'),
        sa.Column('extra_metadata', sa.Text(),
                 nullable=True,
                 comment='JSON metadata storage'),
        sa.Column('deleted_at', sa.DateTime(timezone=True),
                 nullable=True,
                 comment='Soft delete timestamp - NULL means not deleted'),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], 
                               ondelete='CASCADE',
                               name='fk_ticket_comments_ticket_id'),
        sa.ForeignKeyConstraint(['integration_id'], ['integrations.id'],
                               name='fk_ticket_comments_integration_id'),
        sa.PrimaryKeyConstraint('id', name='pk_ticket_comments'),
        comment='Comments on support tickets with generic integration platform support'
    )
    
    # Create indexes for efficient queries
    op.create_index('idx_ticket_comments_ticket_id', 'ticket_comments', ['ticket_id'], unique=False)
    op.create_index('idx_ticket_comments_external_id', 'ticket_comments', ['external_comment_id'], unique=False)
    op.create_index('idx_ticket_comments_integration_id', 'ticket_comments', ['integration_id'], unique=False)
    op.create_index('idx_ticket_comments_author_email', 'ticket_comments', ['author_email'], unique=False)
    op.create_index('idx_ticket_comments_created_at', 'ticket_comments', ['created_at'], unique=False)


def downgrade() -> None:
    # Restore original ADF-based ticket_comments table
    op.drop_table('ticket_comments')
    
    # Recreate original schema (if rollback needed)
    op.create_table('ticket_comments',
        sa.Column('id', sa.UUID(), 
                 server_default=sa.text('gen_random_uuid()'), 
                 nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                 server_default=sa.text('NOW()'), 
                 nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                 server_default=sa.text('NOW()'), 
                 nullable=False),
        sa.Column('ticket_id', sa.UUID(), nullable=False),
        sa.Column('jira_comment_id', sa.Text(), nullable=True),
        sa.Column('author_email', sa.Text(), nullable=False),
        sa.Column('author_display_name', sa.Text(), nullable=True),
        sa.Column('body', sa.JSON(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), 
                 server_default=sa.text('false'), 
                 nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('extra_metadata', sa.Text(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )