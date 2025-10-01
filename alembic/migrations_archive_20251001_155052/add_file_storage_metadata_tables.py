"""Add file_storage_metadata and avatar_variants tables for generic file tracking

Revision ID: add_file_storage_metadata_tables
Revises: unified_storage_agent_avatar
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_file_storage_metadata_tables'
down_revision = 'unified_storage_agent_avatar'
branch_labels = None
depends_on = None


def upgrade():
    # Create file_storage_metadata table
    op.create_table('file_storage_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('storage_key', sa.String(length=500), nullable=False, comment='Unique storage key/path for the file across all backends'),
        sa.Column('original_filename', sa.String(length=255), nullable=False, comment='Original filename when uploaded'),
        sa.Column('content_type', sa.String(length=100), nullable=False, comment='MIME type of the file'),
        sa.Column('storage_backend', sa.String(length=20), nullable=False, comment='Storage backend used (local, s3, etc.)'),
        sa.Column('file_size', sa.BigInteger(), nullable=False, comment='File size in bytes'),
        sa.Column('file_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Additional file metadata and custom fields'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('notes', sa.Text(), nullable=True),
        
        # Indexes
        sa.Index('ix_file_storage_metadata_storage_key', 'storage_key'),
        sa.Index('ix_file_storage_metadata_content_type', 'content_type'),
        sa.Index('ix_file_storage_metadata_storage_backend', 'storage_backend'),
        sa.Index('ix_file_storage_metadata_created_at', 'created_at'),
        sa.Index('ix_file_storage_metadata_updated_at', 'updated_at'),
        sa.Index('ix_file_storage_metadata_deleted_at', 'deleted_at'),
        sa.Index('ix_file_storage_metadata_is_deleted', 'is_deleted'),
        
        # Unique constraint on storage_key
        sa.UniqueConstraint('storage_key', name='uq_file_storage_metadata_storage_key'),
        
        comment='Generic file storage metadata for all file types across storage backends'
    )
    
    # Create avatar_variants table
    op.create_table('avatar_variants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('base_file_id', postgresql.UUID(as_uuid=True), nullable=False, comment='References file_storage_metadata for the original file'),
        sa.Column('entity_type', sa.String(length=20), nullable=False, comment='Type of entity (user, agent)'),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False, comment='ID of the entity (user_id or agent_id)'),
        sa.Column('size_variant', sa.String(length=20), nullable=False, comment='Size variant (original, small, medium, large)'),
        sa.Column('storage_key', sa.String(length=500), nullable=False, comment='Storage key for this specific size variant'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('notes', sa.Text(), nullable=True),
        
        # Foreign key constraint
        sa.ForeignKeyConstraint(['base_file_id'], ['file_storage_metadata.id'], ondelete='CASCADE'),
        
        # Indexes
        sa.Index('ix_avatar_variants_entity', 'entity_type', 'entity_id'),
        sa.Index('ix_avatar_variants_entity_size', 'entity_id', 'size_variant'),
        sa.Index('ix_avatar_variants_storage_key', 'storage_key'),
        sa.Index('ix_avatar_variants_created_at', 'created_at'),
        sa.Index('ix_avatar_variants_updated_at', 'updated_at'),
        sa.Index('ix_avatar_variants_deleted_at', 'deleted_at'),
        sa.Index('ix_avatar_variants_is_deleted', 'is_deleted'),
        
        # Unique constraint on storage_key
        sa.UniqueConstraint('storage_key', name='uq_avatar_variants_storage_key'),
        
        comment='Avatar size variants for different entity types'
    )


def downgrade():
    # Drop avatar_variants table (has foreign key, so drop first)
    op.drop_table('avatar_variants')
    
    # Drop file_storage_metadata table
    op.drop_table('file_storage_metadata')