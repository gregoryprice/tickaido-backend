#!/usr/bin/env python3
"""
AI Agent Service for managing organization-scoped AI agents
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.ai_agent import Agent
from app.services.ai_config_service import ai_config_service
from app.database import get_async_db_session

logger = logging.getLogger(__name__)


class AgentService:
    """
    Service for managing organization-scoped AI agents with automatic provisioning.
    
    This service implements the agent lifecycle management including:
    - Automatic agent creation for organizations
    - Configuration management with ai_config.yaml defaults
    - CRUD operations for agents
    - Usage statistics tracking
    """
    
    async def get_organization_agent(
        self, 
        organization_id: UUID, 
        agent_type: str = "customer_support",
        db: Optional[AsyncSession] = None
    ) -> Optional[Agent]:
        """
        Get organization's AI agent by type.
        
        Args:
            organization_id: Organization UUID
            agent_type: Type of agent (default: "customer_support")
            db: Database session (optional)
            
        Returns:
            Agent: The organization's agent or None if not found
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Query for the organization's agent
                stmt = select(Agent).where(
                    and_(
                        Agent.organization_id == organization_id,
                        Agent.agent_type == agent_type,
                        Agent.is_deleted == False
                    )
                ).options(selectinload(Agent.organization))
                
                result = await session.execute(stmt)
                agent = result.scalar_one_or_none()
                
                if agent:
                    logger.debug(f"Found {agent_type} agent for organization {organization_id}")
                else:
                    logger.debug(f"No {agent_type} agent found for organization {organization_id}")
                
                return agent
                
            except Exception as e:
                logger.error(f"Error getting organization agent: {e}")
                return None
    
    async def create_organization_agent(
        self,
        organization_id: UUID,
        agent_type: str = "customer_support",
        name: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[Agent]:
        """
        Create a new AI agent for an organization.
        
        Args:
            organization_id: Organization UUID
            agent_type: Type of agent to create
            name: Custom name for the agent
            configuration: Custom configuration (uses defaults if not provided)
            db: Database session (optional)
            
        Returns:
            Agent: Created agent or None if failed
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Check if agent already exists
                existing_agent = await self.get_organization_agent(
                    organization_id, agent_type, session
                )
                if existing_agent:
                    logger.warning(f"Agent {agent_type} already exists for organization {organization_id}")
                    return existing_agent
                
                # Load default configuration if not provided
                if configuration is None:
                    logger.info("Loading default agent configuration from ai_config.yaml")
                    configuration = await ai_config_service.load_default_agent_configuration()
                
                # Set default name if not provided
                if name is None:
                    if agent_type == "customer_support":
                        name = "Customer Support Agent"
                    else:
                        name = f"{agent_type.replace('_', ' ').title()} Agent"
                
                # Create the agent with individual configuration fields
                agent = Agent(
                    organization_id=organization_id,
                    agent_type=agent_type,
                    name=name,
                    is_active=True,
                    status="active",
                    # Configuration fields from ai_config.yaml
                    role=configuration.get("role", "AI assistant"),
                    prompt=configuration.get("prompt", "You are a helpful AI assistant."),
                    initial_context=configuration.get("initial_context"),
                    initial_ai_msg=configuration.get("initial_ai_msg"),
                    tone=configuration.get("tone", "professional"),
                    communication_style=configuration.get("communication_style", "formal"),
                    use_streaming=configuration.get("use_streaming", False),
                    response_length=configuration.get("response_length", "moderate"),
                    memory_retention=configuration.get("memory_retention", 10),
                    show_suggestions_after_each_message=configuration.get("show_suggestions_after_each_message", False),
                    max_context_size=configuration.get("max_context_size", 150000),
                    use_memory_context=configuration.get("use_memory_context", True),
                    max_iterations=configuration.get("max_iterations", 8),
                    timeout_seconds=configuration.get("timeout_seconds", 120),
                    tools=configuration.get("tools_enabled", [])
                )
                
                session.add(agent)
                await session.commit()
                await session.refresh(agent)
                
                logger.info(f"✅ Created {agent_type} agent {agent.id} for organization {organization_id}")
                return agent
                
            except Exception as e:
                logger.error(f"Error creating organization agent: {e}")
                await session.rollback()
                return None
    
    async def ensure_organization_agent(
        self,
        organization_id: UUID,
        agent_type: str = "customer_support",
        db: Optional[AsyncSession] = None
    ) -> Optional[Agent]:
        """
        Ensure organization has an agent (create if missing).
        
        This implements the "Agent Availability Guarantee" from the PRP.
        
        Args:
            organization_id: Organization UUID
            agent_type: Type of agent to ensure exists
            db: Database session (optional)
            
        Returns:
            Agent: Organization's agent (existing or newly created)
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Try to get existing agent
                agent = await self.get_organization_agent(organization_id, agent_type, session)
                
                if agent:
                    # Agent exists - check if it's active
                    if not agent.is_ready:
                        logger.info(f"Reactivating inactive {agent_type} agent for organization {organization_id}")
                        await self.activate_agent(agent.id, session)
                        await session.refresh(agent)
                    return agent
                
                # Agent doesn't exist - create with defaults from ai_config.yaml
                logger.info(f"🔄 Creating missing {agent_type} agent for organization {organization_id}")
                agent = await self.create_organization_agent(
                    organization_id=organization_id,
                    agent_type=agent_type,
                    db=session
                )
                
                if agent:
                    logger.info(f"✅ Auto-created {agent_type} agent for organization {organization_id}")
                
                return agent
                
            except Exception as e:
                logger.error(f"Error ensuring organization agent: {e}")
                return None
    
    async def update_agent_configuration(
        self,
        agent_id: UUID,
        configuration_updates: Dict[str, Any],
        db: Optional[AsyncSession] = None
    ) -> Optional[Agent]:
        """
        Update agent configuration.
        
        Args:
            agent_id: Agent UUID
            configuration_updates: Configuration updates to apply
            db: Database session (optional)
            
        Returns:
            Agent: Updated agent or None if failed
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Get the agent
                stmt = select(Agent).where(
                    and_(Agent.id == agent_id, Agent.is_deleted == False)
                )
                result = await session.execute(stmt)
                agent = result.scalar_one_or_none()
                
                if not agent:
                    logger.error(f"Agent {agent_id} not found")
                    return None
                
                # Update configuration
                agent.update_configuration(configuration_updates)
                await session.commit()
                await session.refresh(agent)
                
                logger.info(f"✅ Updated configuration for agent {agent_id}")
                return agent
                
            except Exception as e:
                logger.error(f"Error updating agent configuration: {e}")
                await session.rollback()
                return None
    
    async def activate_agent(
        self,
        agent_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Activate an agent.
        
        Args:
            agent_id: Agent UUID
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                stmt = select(Agent).where(
                    and_(Agent.id == agent_id, Agent.is_deleted == False)
                )
                result = await session.execute(stmt)
                agent = result.scalar_one_or_none()
                
                if not agent:
                    logger.error(f"Agent {agent_id} not found")
                    return False
                
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
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Deactivate an agent.
        
        Args:
            agent_id: Agent UUID
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                stmt = select(Agent).where(
                    and_(Agent.id == agent_id, Agent.is_deleted == False)
                )
                result = await session.execute(stmt)
                agent = result.scalar_one_or_none()
                
                if not agent:
                    logger.error(f"Agent {agent_id} not found")
                    return False
                
                agent.deactivate()
                await session.commit()
                
                logger.info(f"✅ Deactivated agent {agent_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error deactivating agent: {e}")
                await session.rollback()
                return False
    
    async def delete_agent(
        self,
        agent_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Delete an agent (soft delete).
        
        Args:
            agent_id: Agent UUID
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                stmt = select(Agent).where(
                    and_(Agent.id == agent_id, Agent.is_deleted == False)
                )
                result = await session.execute(stmt)
                agent = result.scalar_one_or_none()
                
                if not agent:
                    logger.error(f"Agent {agent_id} not found")
                    return False
                
                # Soft delete
                agent.delete()  # Inherited from BaseModel
                await session.commit()
                
                logger.info(f"✅ Deleted agent {agent_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error deleting agent: {e}")
                await session.rollback()
                return False
    
    async def reset_agent_to_defaults(
        self,
        agent_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> Optional[Agent]:
        """
        Reset agent configuration to defaults from ai_config.yaml.
        
        Args:
            agent_id: Agent UUID
            db: Database session (optional)
            
        Returns:
            Agent: Reset agent or None if failed
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                stmt = select(Agent).where(
                    and_(Agent.id == agent_id, Agent.is_deleted == False)
                )
                result = await session.execute(stmt)
                agent = result.scalar_one_or_none()
                
                if not agent:
                    logger.error(f"Agent {agent_id} not found")
                    return None
                
                # Load defaults from ai_config.yaml
                default_config = await ai_config_service.load_default_agent_configuration()
                
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
                stmt = select(Agent).where(
                    and_(Agent.id == agent_id, Agent.is_deleted == False)
                )
                result = await session.execute(stmt)
                agent = result.scalar_one_or_none()
                
                if not agent:
                    logger.error(f"Agent {agent_id} not found")
                    return False
                
                # Update agent usage timestamp
                agent.record_usage()
                
                # TODO: Implement detailed usage statistics
                # This would create/update AgentUsageStats records
                # For now, just update the agent's last_used_at
                
                await session.commit()
                return True
                
            except Exception as e:
                logger.error(f"Error recording agent usage: {e}")
                await session.rollback()
                return False
    
    async def get_agent_stats(
        self,
        agent_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get usage statistics for an agent.
        
        Args:
            agent_id: Agent UUID
            db: Database session (optional)
            
        Returns:
            Dict[str, Any]: Agent statistics
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Get agent with usage stats
                stmt = select(Agent).where(
                    and_(Agent.id == agent_id, Agent.is_deleted == False)
                ).options(selectinload(Agent.usage_stats))
                
                result = await session.execute(stmt)
                agent = result.scalar_one_or_none()
                
                if not agent:
                    return {"error": "Agent not found"}
                
                # Compile basic stats
                stats = {
                    "agent_id": str(agent.id),
                    "agent_name": agent.name,
                    "agent_type": agent.agent_type,
                    "is_active": agent.is_active,
                    "status": agent.status,
                    "last_used_at": agent.last_used_at.isoformat() if agent.last_used_at else None,
                    "created_at": agent.created_at.isoformat(),
                    "tools_count": agent.tools_count,
                    "mcp_enabled": agent.mcp_enabled,
                    "auto_created": agent.auto_created
                }
                
                # Add usage stats if available
                if agent.usage_stats:
                    latest_stats = agent.usage_stats[0]  # Ordered by period_start desc
                    stats["latest_period"] = {
                        "total_messages": latest_stats.total_messages,
                        "success_rate": latest_stats.success_rate,
                        "avg_response_time_ms": float(latest_stats.avg_response_time_ms) if latest_stats.avg_response_time_ms else None,
                        "period_start": latest_stats.period_start.isoformat(),
                        "period_end": latest_stats.period_end.isoformat()
                    }
                
                return stats
                
            except Exception as e:
                logger.error(f"Error getting agent stats: {e}")
                return {"error": str(e)}
    
    async def list_organization_agents(
        self,
        organization_id: UUID,
        include_inactive: bool = False,
        db: Optional[AsyncSession] = None
    ) -> List[Agent]:
        """
        List all agents for an organization.
        
        Args:
            organization_id: Organization UUID
            include_inactive: Include inactive agents
            db: Database session (optional)
            
        Returns:
            List[Agent]: List of organization's agents
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                conditions = [
                    Agent.organization_id == organization_id,
                    Agent.is_deleted == False
                ]
                
                if not include_inactive:
                    conditions.append(Agent.is_active == True)
                
                stmt = select(Agent).where(and_(*conditions)).order_by(Agent.created_at.desc())
                
                result = await session.execute(stmt)
                agents = result.scalars().all()
                
                logger.debug(f"Found {len(agents)} agents for organization {organization_id}")
                return list(agents)
                
            except Exception as e:
                logger.error(f"Error listing organization agents: {e}")
                return []


# Global AI Agent service instance
ai_agent_service = AgentService()