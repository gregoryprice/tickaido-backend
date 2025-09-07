"""Create system title generation agent

This migration creates the single system-wide title generation agent
that serves all organizations for title generation functionality.

Revision ID: c740f9fb4b4b
Revises: 5c5af32e4312
Create Date: 2025-09-05 22:08:00.883311

"""
from alembic import op
import sqlalchemy as sa
import logging
from uuid import uuid4
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision = 'c740f9fb4b4b'
down_revision = 'efdfb7615061'
branch_labels = None
depends_on = None

logger = logging.getLogger(__name__)


def upgrade() -> None:
    """Create the system title generation agent"""
    # This migration creates a system-wide title generation agent
    # that can be used by all organizations for title generation
    
    # Get database connection
    connection = op.get_bind()
    
    # Check if system title generation agent already exists
    result = connection.execute(
        sa.text("""
            SELECT id FROM agents 
            WHERE agent_type = 'title_generation' 
            AND organization_id IS NULL 
            AND is_deleted = false
            LIMIT 1
        """)
    )
    
    existing_agent = result.fetchone()
    if existing_agent:
        logger.info(f"System title generation agent already exists: {existing_agent[0]}")
        return
    
    # System title generation agent configuration
    agent_id = uuid4()
    now = datetime.now(timezone.utc)
    
    # Insert system title generation agent
    connection.execute(
        sa.text("""
            INSERT INTO agents (
                id, organization_id, agent_type, name, avatar_url,
                is_active, status, role, prompt, initial_context, initial_ai_msg,
                tone, communication_style, use_streaming, response_length,
                memory_retention, show_suggestions_after_each_message,
                suggestions_prompt, max_context_size, use_memory_context,
                max_iterations, timeout_seconds, tools, last_used_at,
                extra_metadata, created_at, updated_at, is_deleted,
                deleted_at, notes
            ) VALUES (
                :agent_id, NULL, 'title_generation', 'System Title Generator', NULL,
                true, 'active', 'Title Generation Utility', 
                :prompt, NULL, NULL, NULL, 'professional', 
                false, 'brief', 1, false, NULL, 10000, false, 1, 15, 
                '[]'::json, NULL, NULL, :created_at, :updated_at, false,
                NULL, 'System-wide title generation agent'
            )
        """),
        {
            'agent_id': agent_id,
            'prompt': """You are an expert at creating concise, descriptive titles for customer support conversations.

Analyze the conversation and generate a clear, specific title that captures the essence of the discussion.

TITLE GENERATION RULES:
1. Maximum 8 words, ideally 4-6 words
2. Use specific, descriptive terms
3. Avoid generic words: "Help", "Support", "Question", "Issue"
4. Include technical terms when relevant
5. Capture the primary topic/problem
6. Use title case formatting

Focus on the main issue or request being discussed.""",
            'created_at': now,
            'updated_at': now
        }
    )
    
    logger.info(f"✅ Created system title generation agent: {agent_id}")


def downgrade() -> None:
    """Remove the system title generation agent"""
    connection = op.get_bind()
    
    # Soft delete system title generation agent
    result = connection.execute(
        sa.text("""
            UPDATE agents 
            SET is_deleted = true, deleted_at = :deleted_at, is_active = false
            WHERE agent_type = 'title_generation' 
            AND organization_id IS NULL
            RETURNING id
        """),
        {'deleted_at': datetime.now(timezone.utc)}
    )
    
    deleted_agents = result.fetchall()
    if deleted_agents:
        for agent in deleted_agents:
            logger.info(f"Soft deleted system title generation agent: {agent[0]}")
    else:
        logger.info("No system title generation agents found to delete")