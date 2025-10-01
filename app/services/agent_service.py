#!/usr/bin/env python3
"""
Agent Service for managing organization-scoped multi-agent system
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_async_db_session
from app.models.ai_agent import Agent
from app.services.agent_history_service import agent_history_service
from app.services.ai_config_service import ai_config_service

logger = logging.getLogger(__name__)


class AgentService:
    """
    Service for managing multi-agent system with automatic change tracking.
    
    This service handles the agent lifecycle including:
    - Multi-agent creation per organization (no singleton constraint)
    - Configuration management with embedded fields and history tracking
    - CRUD operations with comprehensive audit trail
    - Agent personalization and file context integration
    """
    
    async def get_agent(
        self, 
        agent_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> Optional[Agent]:
        """
        Get agent by ID.
        
        Args:
            agent_id: Agent UUID
            db: Database session (optional)
            
        Returns:
            Agent: The agent or None if not found
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                stmt = select(Agent).where(
                    and_(
                        Agent.id == agent_id,
                        Agent.deleted_at.is_(None)
                    )
                ).options(selectinload(Agent.organization))
                
                result = await session.execute(stmt)
                agent = result.scalar_one_or_none()
                
                if agent:
                    logger.debug(f"Found agent {agent_id}")
                else:
                    logger.debug(f"Agent {agent_id} not found")
                
                return agent
                
            except Exception as e:
                logger.error(f"Error getting agent: {e}")
                return None
    
    async def get_organization_agents(
        self, 
        organization_id: UUID,
        agent_type: Optional[str] = None,
        include_inactive: bool = False,
        db: Optional[AsyncSession] = None
    ) -> List[Agent]:
        """
        Get all agents for an organization (no singleton constraint).
        
        Args:
            organization_id: Organization UUID
            agent_type: Filter by agent type (optional)
            include_inactive: Include inactive agents
            db: Database session (optional)
            
        Returns:
            List[Agent]: List of organization's agents
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # If organization_id is None, return empty list (no system agents via API)
                if organization_id is None:
                    logger.debug("No organization_id provided - returning empty agent list")
                    return []
                
                conditions = [
                    Agent.organization_id == organization_id,
                    Agent.organization_id.is_not(None),  # Explicitly exclude system agents
                    Agent.deleted_at.is_(None)
                ]
                
                if agent_type:
                    conditions.append(Agent.agent_type == agent_type)
                
                if not include_inactive:
                    conditions.append(Agent.is_active == True)
                
                stmt = (
                    select(Agent)
                    .where(and_(*conditions))
                    .options(selectinload(Agent.organization))
                    .order_by(Agent.created_at.desc())
                )
                
                result = await session.execute(stmt)
                agents = result.scalars().all()
                
                logger.debug(f"Found {len(agents)} agents for organization {organization_id}")
                return list(agents)
                
            except Exception as e:
                logger.error(f"Error getting organization agents: {e}")
                return []
    
    async def create_agent(
        self,
        organization_id: UUID,
        name: str,
        agent_type: str = "customer_support",
        avatar_url: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        created_by_user_id: Optional[UUID] = None,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[Agent]:
        """
        Create a new agent for an organization.
        
        Args:
            organization_id: Organization UUID
            name: Agent name
            agent_type: Type of agent to create
            avatar_url: Optional avatar URL
            configuration: Custom configuration (uses defaults if not provided)
            created_by_user_id: User creating the agent
            reason: Reason for creation
            ip_address: IP address of request
            db: Database session (optional)
            
        Returns:
            Agent: Created agent or None if failed
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Load default configuration if not provided
                if configuration is None:
                    logger.info("Loading default agent configuration from ai_config.yaml")
                    configuration = await ai_config_service.load_default_agent_configuration()
                
                # Create the agent
                agent = Agent(
                    organization_id=organization_id,
                    agent_type=agent_type,
                    name=name,
                    avatar_url=avatar_url,
                    is_active=True,
                    status="active"
                )
                
                # Set configuration fields directly
                agent.update_configuration(configuration)
                
                session.add(agent)
                await session.commit()
                await session.refresh(agent)
                
                # Record creation in history
                if created_by_user_id:
                    await agent_history_service.record_change(
                        agent_id=agent.id,
                        user_id=created_by_user_id,
                        change_type="agent_created",
                        field_changed="agent",
                        old_value=None,
                        new_value=f"Created agent '{name}' of type '{agent_type}'",
                        reason=reason or "Agent creation",
                        ip_address=ip_address,
                        db=session
                    )
                
                logger.info(f"✅ Created {agent_type} agent {agent.id} '{name}' for organization {organization_id}")
                return agent
                
            except Exception as e:
                logger.error(f"Error creating agent: {e}")
                await session.rollback()
                return None
    
    async def update_agent(
        self,
        agent_id: UUID,
        updates: Dict[str, Any],
        updated_by_user_id: UUID,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[Agent]:
        """
        Update agent with automatic change tracking.
        
        Args:
            agent_id: Agent UUID
            updates: Dictionary of updates to apply
            updated_by_user_id: User making the update
            reason: Reason for update
            ip_address: IP address of request
            db: Database session (optional)
            
        Returns:
            Agent: Updated agent or None if failed
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Get the agent directly in this session to avoid detached instance
                stmt = select(Agent).where(Agent.id == agent_id)
                result = await session.execute(stmt)
                agent = result.scalar_one_or_none()
                
                if not agent:
                    logger.error(f"Agent {agent_id} not found")
                    return None
                
                # Record changes before applying updates
                await agent_history_service.record_agent_update(
                    agent=agent,
                    updates=updates,
                    user_id=updated_by_user_id,
                    reason=reason,
                    ip_address=ip_address,
                    db=session
                )
                
                # Apply updates
                for field, value in updates.items():
                    if hasattr(agent, field):
                        setattr(agent, field, value)
                
                # Handle configuration updates
                config_fields = {
                    "role", "prompt", "initial_context", "initial_ai_msg", "tone",
                    "communication_style", "use_streaming", "response_length",
                    "memory_retention", "show_suggestions_after_each_message",
                    "suggestions_prompt", "max_context_size", "use_memory_context",
                    "max_iterations", "timeout_seconds", "tools"
                }
                
                config_updates = {k: v for k, v in updates.items() if k in config_fields}
                if config_updates:
                    agent.update_configuration(config_updates)
                
                await session.commit()
                await session.refresh(agent)
                
                logger.info(f"✅ Updated agent {agent_id} with {len(updates)} changes")
                return agent
                
            except Exception as e:
                logger.error(f"Error updating agent: {e}")
                await session.rollback()
                return None
    
    async def delete_agent(
        self,
        agent_id: UUID,
        deleted_by_user_id: UUID,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Delete an agent (soft delete) with history tracking.
        
        Args:
            agent_id: Agent UUID
            deleted_by_user_id: User deleting the agent
            reason: Reason for deletion
            ip_address: IP address of request
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Get the agent directly in this session to avoid detached instance
                stmt = select(Agent).where(Agent.id == agent_id)
                result = await session.execute(stmt)
                agent = result.scalar_one_or_none()
                
                if not agent:
                    logger.error(f"Agent {agent_id} not found")
                    return False
                
                # Record deletion in history
                await agent_history_service.record_change(
                    agent_id=agent.id,
                    user_id=deleted_by_user_id,
                    change_type="agent_deleted",
                    field_changed="is_deleted",
                    old_value=False,
                    new_value=True,
                    reason=reason or "Agent deletion",
                    ip_address=ip_address,
                    db=session
                )
                
                # Soft delete using ORM method
                agent.soft_delete()
                await session.commit()
                
                logger.info(f"✅ Deleted agent {agent_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error deleting agent: {e}")
                await session.rollback()
                return False
    
    async def activate_agent(
        self,
        agent_id: UUID,
        activated_by_user_id: UUID,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Activate an agent with history tracking.
        
        Args:
            agent_id: Agent UUID
            activated_by_user_id: User activating the agent
            reason: Reason for activation
            ip_address: IP address of request
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                agent = await self.get_agent(agent_id, db=session)
                if not agent:
                    logger.error(f"Agent {agent_id} not found")
                    return False
                
                # Record status changes
                if not agent.is_active:
                    await agent_history_service.record_change(
                        agent_id=agent.id,
                        user_id=activated_by_user_id,
                        change_type="activation",
                        field_changed="is_active",
                        old_value=agent.is_active,
                        new_value=True,
                        reason=reason or "Agent activation",
                        ip_address=ip_address,
                        db=session
                    )
                
                if agent.status != "active":
                    await agent_history_service.record_change(
                        agent_id=agent.id,
                        user_id=activated_by_user_id,
                        change_type="status_change",
                        field_changed="status",
                        old_value=agent.status,
                        new_value="active",
                        reason=reason or "Agent activation",
                        ip_address=ip_address,
                        db=session
                    )
                
                agent.activate()
                await session.commit()
                
                logger.info(f"✅ Activated agent {agent_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error activating agent: {e}")
                await session.rollback()
                return False
    
    async def deactivate_agent(
        self,
        agent_id: UUID,
        deactivated_by_user_id: UUID,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Deactivate an agent with history tracking.
        
        Args:
            agent_id: Agent UUID
            deactivated_by_user_id: User deactivating the agent
            reason: Reason for deactivation
            ip_address: IP address of request
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                agent = await self.get_agent(agent_id, db=session)
                if not agent:
                    logger.error(f"Agent {agent_id} not found")
                    return False
                
                # Record status changes
                if agent.is_active:
                    await agent_history_service.record_change(
                        agent_id=agent.id,
                        user_id=deactivated_by_user_id,
                        change_type="deactivation",
                        field_changed="is_active",
                        old_value=agent.is_active,
                        new_value=False,
                        reason=reason or "Agent deactivation",
                        ip_address=ip_address,
                        db=session
                    )
                
                if agent.status != "inactive":
                    await agent_history_service.record_change(
                        agent_id=agent.id,
                        user_id=deactivated_by_user_id,
                        change_type="status_change",
                        field_changed="status",
                        old_value=agent.status,
                        new_value="inactive",
                        reason=reason or "Agent deactivation",
                        ip_address=ip_address,
                        db=session
                    )
                
                agent.deactivate()
                await session.commit()
                
                logger.info(f"✅ Deactivated agent {agent_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error deactivating agent: {e}")
                await session.rollback()
                return False
    
    async def reset_agent_to_defaults(
        self,
        agent_id: UUID,
        reset_by_user_id: UUID,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[Agent]:
        """
        Reset agent configuration to defaults with history tracking.
        
        Args:
            agent_id: Agent UUID
            reset_by_user_id: User performing the reset
            reason: Reason for reset
            ip_address: IP address of request
            db: Database session (optional)
            
        Returns:
            Agent: Reset agent or None if failed
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                agent = await self.get_agent(agent_id, db=session)
                if not agent:
                    logger.error(f"Agent {agent_id} not found")
                    return None
                
                # Load defaults from ai_config.yaml
                default_config = await ai_config_service.load_default_agent_configuration()
                
                # Record configuration reset
                await agent_history_service.record_change(
                    agent_id=agent.id,
                    user_id=reset_by_user_id,
                    change_type="configuration_reset",
                    field_changed="configuration",
                    old_value=agent.get_configuration(),
                    new_value=default_config,
                    reason=reason or "Reset to ai_config.yaml defaults",
                    ip_address=ip_address,
                    db=session
                )
                
                # Reset agent to defaults
                agent.reset_to_defaults(default_config)
                await session.commit()
                await session.refresh(agent)
                
                logger.info(f"✅ Reset agent {agent_id} to ai_config.yaml defaults")
                return agent
                
            except Exception as e:
                logger.error(f"Error resetting agent to defaults: {e}")
                await session.rollback()
                return None
    
    async def get_agent_with_history(
        self,
        agent_id: UUID,
        history_limit: int = 10,
        db: Optional[AsyncSession] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get agent with recent change history.
        
        Args:
            agent_id: Agent UUID
            history_limit: Number of history records to include
            db: Database session (optional)
            
        Returns:
            Dict: Agent data with history or None if not found
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                agent = await self.get_agent(agent_id, db=session)
                if not agent:
                    return None
                
                # Get recent history
                history = await agent_history_service.get_agent_history(
                    agent_id=agent_id,
                    limit=history_limit,
                    db=session
                )
                
                return {
                    "agent": agent.to_dict(),
                    "recent_history": [h.to_dict() for h in history],
                    "history_count": len(history)
                }
                
            except Exception as e:
                logger.error(f"Error getting agent with history: {e}")
                return None
    
    async def record_agent_usage(
        self,
        agent_id: UUID,
        success: bool = True,
        tools_called: int = 0,
        response_time_ms: Optional[float] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Record usage statistics for an agent.
        
        Args:
            agent_id: Agent UUID
            success: Whether the request was successful
            tools_called: Number of tools called
            response_time_ms: Response time in milliseconds
            db: Database session (optional)
            
        Returns:
            bool: True if recorded successfully
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                agent = await self.get_agent(agent_id, db=session)
                if not agent:
                    logger.error(f"Agent {agent_id} not found")
                    return False
                
                # Update agent usage timestamp
                agent.record_usage()
                await session.commit()
                
                # Note: Detailed usage statistics would be handled by AgentAction model
                # This maintains the interface compatibility
                
                return True
                
            except Exception as e:
                logger.error(f"Error recording agent usage: {e}")
                await session.rollback()
                return False
    
    async def get_system_title_agent(
        self,
        db: Optional[AsyncSession] = None
    ) -> Optional[Agent]:
        """
        Get the system title generation agent (single instance).
        
        System agents have organization_id = None and serve all organizations.
        
        Args:
            db: Database session (optional)
            
        Returns:
            Agent: System title generation agent or None if not found
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Query for system title generation agent
                stmt = select(Agent).where(
                    Agent.agent_type == "title_generation",
                    Agent.is_active.is_(True),
                    Agent.organization_id.is_(None),  # System agent has no organization
                    Agent.deleted_at.is_(None)
                )
                
                result = await session.execute(stmt)
                agent = result.scalar_one_or_none()
                return agent
                
            except Exception as e:
                logger.error(f"Error getting system title agent: {e}")
                return None
    
    async def create_system_title_agent(
        self,
        db: Optional[AsyncSession] = None
    ) -> Optional[Agent]:
        """
        Create the system title generation agent (called during migration).
        
        This creates a single system-wide agent that serves all organizations
        for title generation purposes.
        
        Args:
            db: Database session (optional)
            
        Returns:
            Agent: Created system title generation agent or None if failed
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Check if system title agent already exists
                existing_agent = await self.get_system_title_agent(db=session)
                if existing_agent:
                    logger.info(f"System title generation agent already exists: {existing_agent.id}")
                    return existing_agent
                
                # Load default configuration for title generation agent
                logger.info("Creating system title generation agent")
                default_config = await ai_config_service.load_default_agent_configuration()
                
                # System title generation agent configuration (from PRP specification)
                system_title_config = {
                    "role": "Title Generation Utility",
                    "prompt": """You are an expert at creating concise, descriptive titles for customer support conversations.
    
Analyze the conversation and generate a clear, specific title that captures the essence of the discussion.

TITLE GENERATION RULES:
1. Maximum 8 words, ideally 4-6 words
2. Use specific, descriptive terms
3. Avoid generic words: "Help", "Support", "Question", "Issue"
4. Include technical terms when relevant
5. Capture the primary topic/problem
6. Use title case formatting

Focus on the main issue or request being discussed.""",
                    "communication_style": "professional",
                    "response_length": "brief",
                    "use_streaming": False,
                    "timeout_seconds": 15,
                    "tools": [],
                    "memory_retention": 1,  # Minimal memory for title generation
                    "max_context_size": 10000,  # Smaller context for efficiency
                    "use_memory_context": False,  # Don't need conversation memory
                    "max_iterations": 1  # Single iteration for title generation
                }
                
                # Create the system title generation agent with NULL organization_id
                # System agents serve all organizations universally
                agent = Agent(
                    organization_id=None,  # System agent - no organization
                    agent_type="title_generation",
                    name="System Title Generator",
                    is_active=True,
                    status="active"
                )
                
                # Set configuration fields
                agent.update_configuration(system_title_config)
                
                session.add(agent)
                await session.commit()
                await session.refresh(agent)
                
                logger.info(f"✅ Created system title generation agent: {agent.id}")
                return agent
                
            except Exception as e:
                logger.error(f"Error creating system title agent: {e}")
                await session.rollback()
                return None
    
    async def ensure_system_title_agent(
        self,
        db: Optional[AsyncSession] = None
    ) -> Optional[Agent]:
        """
        Ensure system title generation agent exists, creating it if necessary.
        
        This is a convenience method that combines get and create operations.
        
        Args:
            db: Database session (optional)
            
        Returns:
            Agent: System title generation agent
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Try to get existing system title agent
                agent = await self.get_system_title_agent(db=session)
                
                if not agent:
                    logger.info("System title agent not found, creating it")
                    agent = await self.create_system_title_agent(db=session)
                
                return agent
                
            except Exception as e:
                logger.error(f"Error ensuring system title agent: {e}")
                return None
    
    async def initialize_system_agents(
        self,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Initialize all required system agents on application startup.
        
        This method ensures all system-wide agents are created and available
        for use by all organizations. System agents have organization_id = NULL.
        
        Args:
            db: Database session (optional)
            
        Returns:
            bool: True if all system agents are ready, False if initialization failed
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                logger.info("🔧 Initializing system agents...")
                
                # Initialize system title generation agent
                title_agent = await self.ensure_system_title_agent(db=session)
                if not title_agent:
                    logger.error("❌ Failed to initialize system title generation agent")
                    return False
                
                logger.info(f"✅ System title generation agent ready: {title_agent.id}")
                
                # Future system agents can be added here
                # Example: categorization_agent = await self.ensure_system_categorization_agent(db=session)
                
                logger.info("✅ All system agents initialized successfully")
                return True
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize system agents: {e}")
                return False


# Global agent service instance
agent_service = AgentService()