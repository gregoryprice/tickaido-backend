#!/usr/bin/env python3
"""
Agent History Service for tracking configuration changes and lifecycle events
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_async_db_session
from app.models.agent_history import AgentHistory
from app.models.ai_agent import Agent

logger = logging.getLogger(__name__)


class AgentHistoryService:
    """
    Service for managing agent change history and audit trails.
    
    This service provides comprehensive tracking of agent modifications,
    enabling rollback capabilities, change analysis, and compliance reporting.
    """
    
    async def record_change(
        self,
        agent_id: UUID,
        user_id: UUID,
        change_type: str,
        field_changed: str,
        old_value: Any,
        new_value: Any,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        request_metadata: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[AgentHistory]:
        """
        Record a change to an agent configuration or status.
        
        Args:
            agent_id: Agent that was changed
            user_id: User who made the change
            change_type: Type of change (configuration_update, status_change, etc.)
            field_changed: Which field was changed
            old_value: Previous value
            new_value: New value
            reason: Optional reason for change
            ip_address: Optional IP address
            request_metadata: Optional request metadata
            db: Database session (optional)
            
        Returns:
            AgentHistory: Created history record or None if failed
        """
        if db is not None:
            # Use the provided session (don't create a new context or commit)
            try:
                # Create history entry using the model's record_change method
                history_entry = await AgentHistory.record_change(
                    agent_id=agent_id,
                    user_id=user_id,
                    change_type=change_type,
                    field_changed=field_changed,
                    old_value=old_value,
                    new_value=new_value,
                    reason=reason,
                    ip_address=ip_address
                )
                
                # Add additional metadata if provided
                if request_metadata:
                    history_entry.request_metadata = request_metadata
                
                db.add(history_entry)
                
                logger.info(f"✅ Recorded change for agent {agent_id}: {change_type} - {field_changed}")
                return history_entry
                
            except Exception as e:
                logger.error(f"Error recording agent change: {e}")
                return None
        else:
            # Create our own session context
            async with get_async_db_session() as session:
                try:
                    # Create history entry using the model's record_change method
                    history_entry = await AgentHistory.record_change(
                        agent_id=agent_id,
                        user_id=user_id,
                        change_type=change_type,
                        field_changed=field_changed,
                        old_value=old_value,
                        new_value=new_value,
                        reason=reason,
                        ip_address=ip_address
                    )
                    
                    # Add additional metadata if provided
                    if request_metadata:
                        history_entry.request_metadata = request_metadata
                    
                    session.add(history_entry)
                    await session.commit()
                    await session.refresh(history_entry)
                    
                    logger.info(f"✅ Recorded change for agent {agent_id}: {change_type} - {field_changed}")
                    return history_entry
                    
                except Exception as e:
                    logger.error(f"Error recording agent change: {e}")
                    await session.rollback()
                    return None
    
    async def record_agent_update(
        self,
        agent: Agent,
        updates: Dict[str, Any],
        user_id: UUID,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> List[AgentHistory]:
        """
        Record multiple field changes from an agent update operation.
        
        Args:
            agent: Agent being updated
            updates: Dictionary of field updates
            user_id: User making the changes
            reason: Optional reason for changes
            ip_address: Optional IP address
            db: Database session (optional)
            
        Returns:
            List[AgentHistory]: List of created history records
        """
        if db is not None:
            # Use the provided session
            history_records = []
            
            try:
                for field_name, new_value in updates.items():
                    # Get current value
                    old_value = getattr(agent, field_name, None)
                    
                    # Only record if value actually changed
                    if old_value != new_value:
                        history_record = await self.record_change(
                            agent_id=agent.id,
                            user_id=user_id,
                            change_type="configuration_update",
                            field_changed=field_name,
                            old_value=old_value,
                            new_value=new_value,
                            reason=reason,
                            ip_address=ip_address,
                            db=db
                        )
                        
                        if history_record:
                            history_records.append(history_record)
                
                logger.info(f"✅ Recorded {len(history_records)} changes for agent {agent.id}")
                return history_records
                
            except Exception as e:
                logger.error(f"Error recording agent update: {e}")
                return []
        else:
            # Create our own session
            async with get_async_db_session() as session:
                history_records = []
                
                try:
                    for field_name, new_value in updates.items():
                        # Get current value
                        old_value = getattr(agent, field_name, None)
                        
                        # Only record if value actually changed
                        if old_value != new_value:
                            history_record = await self.record_change(
                                agent_id=agent.id,
                                user_id=user_id,
                                change_type="configuration_update",
                                field_changed=field_name,
                                old_value=old_value,
                                new_value=new_value,
                                reason=reason,
                                ip_address=ip_address,
                                db=session
                            )
                            
                            if history_record:
                                history_records.append(history_record)
                    
                    await session.commit()
                    logger.info(f"✅ Recorded {len(history_records)} changes for agent {agent.id}")
                    return history_records
                    
                except Exception as e:
                    logger.error(f"Error recording agent update: {e}")
                    await session.rollback()
                    return []
    
    async def get_agent_history(
        self,
        agent_id: UUID,
        limit: int = 50,
        offset: int = 0,
        change_type: Optional[str] = None,
        field_filter: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_filter: Optional[UUID] = None,
        db: Optional[AsyncSession] = None
    ) -> List[AgentHistory]:
        """
        Get history records for an agent with filtering options.
        
        Args:
            agent_id: Agent to get history for
            limit: Maximum number of records
            offset: Number of records to skip
            change_type: Filter by change type
            field_filter: Filter by field name
            start_date: Filter by start date
            end_date: Filter by end date
            user_filter: Filter by user who made changes
            db: Database session (optional)
            
        Returns:
            List[AgentHistory]: History records
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Build query with filters
                conditions = [AgentHistory.agent_id == agent_id]
                
                if change_type:
                    conditions.append(AgentHistory.change_type == change_type)
                
                if field_filter:
                    conditions.append(AgentHistory.field_changed == field_filter)
                
                if start_date:
                    conditions.append(AgentHistory.change_timestamp >= start_date)
                
                if end_date:
                    conditions.append(AgentHistory.change_timestamp <= end_date)
                
                if user_filter:
                    conditions.append(AgentHistory.changed_by_user_id == user_filter)
                
                stmt = (
                    select(AgentHistory)
                    .where(and_(*conditions))
                    .options(selectinload(AgentHistory.changed_by))
                    .order_by(desc(AgentHistory.change_timestamp))
                    .offset(offset)
                    .limit(limit)
                )
                
                result = await session.execute(stmt)
                history_records = result.scalars().all()
                
                logger.debug(f"Retrieved {len(history_records)} history records for agent {agent_id}")
                return list(history_records)
                
            except Exception as e:
                logger.error(f"Error getting agent history: {e}")
                return []
    
    async def get_field_history(
        self,
        agent_id: UUID,
        field: str,
        limit: int = 10,
        db: Optional[AsyncSession] = None
    ) -> List[AgentHistory]:
        """
        Get history for a specific field of an agent.
        
        Args:
            agent_id: Agent ID
            field: Field name to get history for
            limit: Maximum number of records
            db: Database session (optional)
            
        Returns:
            List[AgentHistory]: Field history records
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                stmt = (
                    select(AgentHistory)
                    .where(
                        and_(
                            AgentHistory.agent_id == agent_id,
                            AgentHistory.field_changed == field
                        )
                    )
                    .options(selectinload(AgentHistory.changed_by))
                    .order_by(desc(AgentHistory.change_timestamp))
                    .limit(limit)
                )
                
                result = await session.execute(stmt)
                field_history = result.scalars().all()
                
                logger.debug(f"Retrieved {len(field_history)} history records for field '{field}' on agent {agent_id}")
                return list(field_history)
                
            except Exception as e:
                logger.error(f"Error getting field history: {e}")
                return []
    
    async def get_change_summary(
        self,
        agent_id: UUID,
        days: int = 30,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get a summary of changes for an agent over a time period.
        
        Args:
            agent_id: Agent ID
            days: Number of days to look back
            db: Database session (optional)
            
        Returns:
            Dict: Change summary with statistics
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                start_date = datetime.now(timezone.utc) - timedelta(days=days)
                
                # Get all changes in the period
                stmt = (
                    select(AgentHistory)
                    .where(
                        and_(
                            AgentHistory.agent_id == agent_id,
                            AgentHistory.change_timestamp >= start_date
                        )
                    )
                    .options(selectinload(AgentHistory.changed_by))
                )
                
                result = await session.execute(stmt)
                changes = result.scalars().all()
                
                # Compile statistics
                summary = {
                    "agent_id": str(agent_id),
                    "period_days": days,
                    "total_changes": len(changes),
                    "change_types": {},
                    "fields_changed": {},
                    "users_who_changed": {},
                    "recent_changes": [],
                    "most_active_day": None,
                    "change_frequency": 0.0
                }
                
                if changes:
                    # Group by change type
                    for change in changes:
                        change_type = change.change_type
                        summary["change_types"][change_type] = summary["change_types"].get(change_type, 0) + 1
                        
                        # Group by field
                        field = change.field_changed
                        summary["fields_changed"][field] = summary["fields_changed"].get(field, 0) + 1
                        
                        # Group by user
                        user_name = change.changed_by.full_name if change.changed_by else "Unknown"
                        summary["users_who_changed"][user_name] = summary["users_who_changed"].get(user_name, 0) + 1
                    
                    # Recent changes (last 5)
                    summary["recent_changes"] = [
                        {
                            "change_type": change.change_type,
                            "field_changed": change.field_changed,
                            "change_timestamp": change.change_timestamp.isoformat(),
                            "changed_by": change.changed_by.full_name if change.changed_by else "Unknown",
                            "change_summary": change.change_summary
                        }
                        for change in sorted(changes, key=lambda x: x.change_timestamp, reverse=True)[:5]
                    ]
                    
                    # Calculate change frequency (changes per day)
                    summary["change_frequency"] = len(changes) / days
                
                return summary
                
            except Exception as e:
                logger.error(f"Error getting change summary: {e}")
                return {"error": str(e)}
    
    async def cleanup_old_history(
        self,
        agent_id: Optional[UUID] = None,
        keep_days: int = 90,
        db: Optional[AsyncSession] = None
    ) -> int:
        """
        Clean up old history entries to manage storage.
        
        Args:
            agent_id: Specific agent to clean up (None for all agents)
            keep_days: Number of days of history to keep
            db: Database session (optional)
            
        Returns:
            int: Number of records deleted
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=keep_days)
                
                # Build delete conditions
                conditions = [AgentHistory.change_timestamp < cutoff_date]
                if agent_id:
                    conditions.append(AgentHistory.agent_id == agent_id)
                
                # Get count before deletion
                count_stmt = select(func.count(AgentHistory.id)).where(and_(*conditions))
                count_result = await session.execute(count_stmt)
                records_to_delete = count_result.scalar()
                
                if records_to_delete > 0:
                    # Delete old records
                    delete_stmt = select(AgentHistory).where(and_(*conditions))
                    result = await session.execute(delete_stmt)
                    old_records = result.scalars().all()
                    
                    for record in old_records:
                        await session.delete(record)
                    
                    await session.commit()
                    
                    target = f"agent {agent_id}" if agent_id else "all agents"
                    logger.info(f"✅ Cleaned up {records_to_delete} old history records for {target}")
                
                return records_to_delete
                
            except Exception as e:
                logger.error(f"Error cleaning up old history: {e}")
                await session.rollback()
                return 0
    
    async def get_agents_with_recent_changes(
        self,
        hours: int = 24,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Get agents that have had recent changes.
        
        Args:
            hours: Number of hours to look back
            db: Database session (optional)
            
        Returns:
            List[Dict]: Agents with recent changes
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
                
                # Query for agents with recent changes
                stmt = (
                    select(AgentHistory.agent_id, func.count(AgentHistory.id).label('change_count'))
                    .where(AgentHistory.change_timestamp >= cutoff_time)
                    .group_by(AgentHistory.agent_id)
                    .order_by(desc('change_count'))
                )
                
                result = await session.execute(stmt)
                agent_changes = result.all()
                
                # Get agent details
                agents_with_changes = []
                for agent_id, change_count in agent_changes:
                    agent_stmt = select(Agent).where(Agent.id == agent_id)
                    agent_result = await session.execute(agent_stmt)
                    agent = agent_result.scalar_one_or_none()
                    
                    if agent:
                        agents_with_changes.append({
                            "agent_id": str(agent.id),
                            "agent_name": agent.name,
                            "agent_type": agent.agent_type,
                            "change_count": change_count,
                            "organization_id": str(agent.organization_id)
                        })
                
                return agents_with_changes
                
            except Exception as e:
                logger.error(f"Error getting agents with recent changes: {e}")
                return []


# Global agent history service instance
agent_history_service = AgentHistoryService()