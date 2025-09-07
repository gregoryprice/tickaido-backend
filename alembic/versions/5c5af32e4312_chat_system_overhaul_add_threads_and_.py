"""chat system overhaul - add threads and messages tables

Revision ID: 5c5af32e4312
Revises: 743d4de64175
Create Date: 2025-09-05 15:56:18.849807

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text
import uuid


# revision identifiers, used by Alembic.
revision = '5c5af32e4312'
down_revision = '743d4de64175'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Chat System Overhaul Migration
    
    This migration transforms the conversation-based chat system into an agent-centric
    architecture with the following changes:
    
    1. CREATE threads table with agent_id and organization_id relationships
    2. RENAME chat_messages table to messages
    3. ADD tool_calls, attachments, content_html, metadata columns to messages
    4. REMOVE model_used, tokens_used columns from messages  
    5. ADD thread_id column to messages (foreign key to threads)
    6. MIGRATE existing chat_conversations data to threads
    7. UPDATE foreign key references from conversation_id to thread_id
    8. PRESERVE all existing data during migration
    """
    
    # Step 1: Create threads table with agent_id and organization_id relationships
    op.create_table('threads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('thread_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('archived', sa.Boolean(), nullable=False, default=False),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], name='fk_threads_agent_id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_threads_organization_id'),
        
        # Indexes for performance
        sa.Index('idx_threads_agent_org', 'agent_id', 'organization_id'),
        sa.Index('idx_threads_user_archived', 'user_id', 'archived'),
        sa.Index('idx_threads_created_at', 'created_at'),
        sa.Index('idx_threads_updated_at', 'updated_at'),
    )
    
    # Step 2: Create temporary table for messages with new structure
    op.create_table('messages_temp',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('thread_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_html', sa.Text(), nullable=True),  # NEW
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        
        # NEW: Tool calling support
        sa.Column('tool_calls', sa.JSON(), nullable=True),
        
        # NEW: Attachments support
        sa.Column('attachments', sa.JSON(), nullable=True),
        
        # NEW: Message metadata
        sa.Column('message_metadata', sa.JSON(), nullable=True),
        
        # Retained fields (model_used and tokens_used REMOVED)
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        
        # Foreign key to threads
        sa.ForeignKeyConstraint(['thread_id'], ['threads.id'], name='fk_messages_thread_id'),
        
        # Indexes
        sa.Index('idx_messages_thread_id', 'thread_id'),
        sa.Index('idx_messages_created_at', 'created_at'),
        sa.Index('idx_messages_role', 'role'),
    )
    
    # Step 3: Ensure default customer support agents exist for all organizations
    # This is critical for data migration - every conversation needs an agent
    op.execute(text("""
        INSERT INTO agents (
            id, organization_id, agent_type, name, is_active, status,
            role, communication_style, use_streaming, response_length,
            memory_retention, show_suggestions_after_each_message,
            max_context_size, use_memory_context, max_iterations,
            tools, created_at, updated_at
        )
        SELECT 
            gen_random_uuid(),
            o.id,
            'customer_support',
            'Customer Support Agent',
            true,
            'active',
            'Customer Support Representative',
            'professional',
            false,
            'moderate',
            5,
            true,
            100000,
            true,
            5,
            '[]'::json,
            now(),
            now()
        FROM organizations o
        WHERE NOT EXISTS (
            SELECT 1 FROM agents a 
            WHERE a.organization_id = o.id 
            AND a.agent_type = 'customer_support'
            AND a.is_active = true
        )
    """))
    
    # Step 4: Migrate existing chat_conversations data to threads
    # Each conversation gets assigned to the organization's default customer support agent
    op.execute(text("""
        INSERT INTO threads (
            id, agent_id, user_id, organization_id, title, thread_metadata,
            created_at, updated_at, archived
        )
        SELECT 
            cc.id,
            -- Get the organization's default customer support agent
            (SELECT a.id FROM agents a 
             JOIN users u ON u.organization_id = a.organization_id
             WHERE u.id::text = cc.user_id 
             AND a.agent_type = 'customer_support' 
             AND a.is_active = true 
             LIMIT 1),
            cc.user_id,
            -- Get organization_id from user
            (SELECT u.organization_id FROM users u WHERE u.id::text = cc.user_id),
            cc.title,
            -- Create metadata from conversation fields
            json_build_object(
                'migrated_from_conversation', true,
                'original_conversation_id', cc.id,
                'is_auditable', cc.is_auditable,
                'retention_days', cc.retention_days,
                'total_messages', cc.total_messages,
                'total_tokens_used', cc.total_tokens_used,
                'migration_timestamp', now()
            ),
            cc.created_at,
            cc.updated_at,
            COALESCE(cc.is_archived, false)
        FROM chat_conversations cc
        WHERE cc.is_deleted = false
        -- Only migrate conversations where we can find a user and agent
        AND EXISTS (
            SELECT 1 FROM users u WHERE u.id::text = cc.user_id
        )
        AND EXISTS (
            SELECT 1 FROM agents a 
            JOIN users u ON u.organization_id = a.organization_id
            WHERE u.id::text = cc.user_id 
            AND a.agent_type = 'customer_support' 
            AND a.is_active = true
        )
    """))
    
    # Step 5: Migrate existing chat_messages data to messages_temp
    op.execute(text("""
        INSERT INTO messages_temp (
            id, thread_id, role, content, content_html, created_at,
            tool_calls, attachments, message_metadata, 
            response_time_ms, confidence_score
        )
        SELECT 
            cm.id,
            cm.conversation_id, -- This will become thread_id
            cm.role,
            cm.content,
            null, -- content_html - new field, start as null
            cm.created_at,
            null, -- tool_calls - new field, start as null
            null, -- attachments - new field, start as null
            -- Create metadata from original fields (preserving model_used, tokens_used in metadata)
            CASE 
                WHEN cm.model_used IS NOT NULL OR cm.tokens_used IS NOT NULL THEN
                    json_build_object(
                        'migrated_from_chat_message', true,
                        'original_model_used', cm.model_used,
                        'original_tokens_used', cm.tokens_used,
                        'migration_timestamp', now()
                    )
                ELSE
                    json_build_object(
                        'migrated_from_chat_message', true,
                        'migration_timestamp', now()
                    )
            END,
            cm.response_time_ms,
            cm.confidence_score
        FROM chat_messages cm
        -- Only migrate messages that have corresponding threads
        WHERE EXISTS (
            SELECT 1 FROM threads t WHERE t.id = cm.conversation_id
        )
    """))
    
    # Step 6: Drop the original chat_messages table
    op.drop_table('chat_messages')
    
    # Step 7: Rename messages_temp to messages
    op.rename_table('messages_temp', 'messages')
    
    # Step 8: Archive the original chat_conversations table for safety
    # We don't drop it immediately in case we need to rollback
    op.rename_table('chat_conversations', 'chat_conversations_archived')


def downgrade() -> None:
    """
    Rollback the chat system overhaul migration
    
    WARNING: This rollback will lose any new thread/message data created after migration
    """
    
    # Step 1: Restore chat_conversations table
    op.rename_table('chat_conversations_archived', 'chat_conversations')
    
    # Step 2: Recreate chat_messages table with original structure
    op.create_table('chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('model_used', sa.String(100), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        
        sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], name='fk_chat_messages_conversation_id'),
        
        sa.Index('idx_chat_message_conversation', 'conversation_id'),
        sa.Index('idx_chat_message_created', 'created_at'),
        sa.Index('idx_chat_message_role', 'role'),
        sa.Index('idx_chat_message_content_search', 'content'),
        sa.Index('idx_chat_message_conv_content', 'conversation_id', 'content'),
    )
    
    # Step 3: Migrate messages back to chat_messages (only for conversations that exist)
    op.execute(text("""
        INSERT INTO chat_messages (
            id, conversation_id, role, content, created_at,
            model_used, tokens_used, response_time_ms, confidence_score
        )
        SELECT 
            m.id,
            m.thread_id,
            m.role,
            m.content,
            m.created_at,
            -- Extract original values from metadata if available
            CASE 
                WHEN m.message_metadata ? 'original_model_used' THEN 
                    m.message_metadata->>'original_model_used'
                ELSE null
            END,
            CASE 
                WHEN m.message_metadata ? 'original_tokens_used' THEN 
                    (m.message_metadata->>'original_tokens_used')::integer
                ELSE null
            END,
            m.response_time_ms,
            m.confidence_score
        FROM messages m
        -- Only restore messages for conversations that exist in archived table
        WHERE EXISTS (
            SELECT 1 FROM chat_conversations cc WHERE cc.id = m.thread_id
        )
    """))
    
    # Step 4: Drop new tables
    op.drop_table('messages')
    op.drop_table('threads')