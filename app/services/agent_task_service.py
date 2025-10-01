#!/usr/bin/env python3
"""
Agent Task Service for autonomous task processing and queue management
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_async_db_session
from app.models.agent_task import AgentTask
from app.models.ai_agent import Agent

logger = logging.getLogger(__name__)


class AgentTaskService:
    """
    Service for managing autonomous agent task processing and queue operations.
    
    Handles task creation, scheduling, status tracking, and queue management
    for multi-channel autonomous agent operations.
    """
    
    async def create_task(
        self,
        agent_id: UUID,
        task_type: str,
        task_data: Dict[str, Any],
        priority: int = 5,
        task_subtype: Optional[str] = None,
        task_metadata: Optional[Dict[str, Any]] = None,
        scheduled_at: Optional[datetime] = None,
        max_retries: int = 3,
        created_by_user_id: Optional[UUID] = None,
        source_channel: Optional[str] = None,
        source_reference: Optional[str] = None,
        correlation_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[AgentTask]:
        """
        Create a new task for autonomous agent processing.
        
        Args:
            agent_id: Agent to process the task
            task_type: Type of task (slack_message, email, api_request, etc.)
            task_data: Task input data and parameters
            priority: Task priority (1=highest, 10=lowest)
            task_subtype: Optional task subtype
            task_metadata: Additional metadata
            scheduled_at: When task should be processed (default: now)
            max_retries: Maximum retry attempts
            created_by_user_id: User who created the task
            source_channel: Channel that generated the task
            source_reference: External reference ID
            correlation_id: Correlation ID for grouping
            db: Database session (optional)
            
        Returns:
            AgentTask: Created task or None if failed
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Verify agent exists
                agent_stmt = select(Agent).where(Agent.id == agent_id)
                agent_result = await session.execute(agent_stmt)
                agent = agent_result.scalar_one_or_none()
                
                if not agent:
                    logger.error(f"Agent {agent_id} not found")
                    return None
                
                # Create task
                task = AgentTask(
                    agent_id=agent_id,
                    task_type=task_type,
                    task_subtype=task_subtype,
                    task_data=task_data,
                    task_metadata=task_metadata or {},
                    status="pending",
                    priority=priority,
                    scheduled_at=scheduled_at or datetime.now(timezone.utc),
                    max_retries=max_retries,
                    created_by_user_id=created_by_user_id,
                    source_channel=source_channel,
                    source_reference=source_reference,
                    correlation_id=correlation_id
                )
                
                session.add(task)
                await session.commit()
                await session.refresh(task)
                
                logger.info(f"✅ Created {task_type} task {task.id} for agent {agent_id} with priority {priority}")
                
                # Queue task for processing
                from app.tasks.agent_tasks import process_agent_task
                celery_task = process_agent_task.delay(str(task.id))
                
                # Update task with Celery task ID
                task.celery_task_id = celery_task.id
                await session.commit()
                
                return task
                
            except Exception as e:
                logger.error(f"Error creating agent task: {e}")
                await session.rollback()
                return None
    
    async def get_task(
        self,
        task_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> Optional[AgentTask]:
        """
        Get task by ID.
        
        Args:
            task_id: Task ID
            db: Database session (optional)
            
        Returns:
            AgentTask: Task or None if not found
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                stmt = (
                    select(AgentTask)
                    .where(AgentTask.id == task_id)
                    .options(selectinload(AgentTask.agent))
                )
                
                result = await session.execute(stmt)
                task = result.scalar_one_or_none()
                
                return task
                
            except Exception as e:
                logger.error(f"Error getting task: {e}")
                return None
    
    async def get_agent_tasks(
        self,
        agent_id: UUID,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        include_completed: bool = True,
        db: Optional[AsyncSession] = None
    ) -> List[AgentTask]:
        """
        Get tasks for an agent with filtering options.
        
        Args:
            agent_id: Agent ID
            status: Filter by status
            task_type: Filter by task type
            limit: Maximum number of tasks
            offset: Number of tasks to skip
            include_completed: Include completed tasks
            db: Database session (optional)
            
        Returns:
            List[AgentTask]: Agent tasks
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                conditions = [AgentTask.agent_id == agent_id]
                
                if status:
                    conditions.append(AgentTask.status == status)
                
                if task_type:
                    conditions.append(AgentTask.task_type == task_type)
                
                if not include_completed:
                    conditions.append(AgentTask.status != "completed")
                
                stmt = (
                    select(AgentTask)
                    .where(and_(*conditions))
                    .order_by(desc(AgentTask.scheduled_at))
                    .offset(offset)
                    .limit(limit)
                )
                
                result = await session.execute(stmt)
                tasks = result.scalars().all()
                
                logger.debug(f"Found {len(tasks)} tasks for agent {agent_id}")
                return list(tasks)
                
            except Exception as e:
                logger.error(f"Error getting agent tasks: {e}")
                return []
    
    async def get_pending_tasks(
        self,
        priority_threshold: int = 10,
        limit: int = 100,
        agent_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None
    ) -> List[AgentTask]:
        """
        Get pending tasks ready for processing.
        
        Args:
            priority_threshold: Only include tasks with priority <= threshold
            limit: Maximum number of tasks
            agent_id: Filter by specific agent
            db: Database session (optional)
            
        Returns:
            List[AgentTask]: Pending tasks ordered by priority and schedule time
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                conditions = [
                    AgentTask.status == "pending",
                    AgentTask.scheduled_at <= datetime.now(timezone.utc),
                    AgentTask.priority <= priority_threshold
                ]
                
                if agent_id:
                    conditions.append(AgentTask.agent_id == agent_id)
                
                stmt = (
                    select(AgentTask)
                    .where(and_(*conditions))
                    .options(selectinload(AgentTask.agent))
                    .order_by(AgentTask.priority, AgentTask.scheduled_at)
                    .limit(limit)
                )
                
                result = await session.execute(stmt)
                tasks = result.scalars().all()
                
                logger.debug(f"Found {len(tasks)} pending tasks ready for processing")
                return list(tasks)
                
            except Exception as e:
                logger.error(f"Error getting pending tasks: {e}")
                return []
    
    async def update_task_status(
        self,
        task_id: UUID,
        status: str,
        result_data: Optional[Dict[str, Any]] = None,
        result_metadata: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Update task status and results.
        
        Args:
            task_id: Task ID
            status: New status
            result_data: Task results
            result_metadata: Result metadata
            error_message: Error message if failed
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                task = await self.get_task(task_id, db=session)
                if not task:
                    logger.error(f"Task {task_id} not found")
                    return False
                
                if status == "completed":
                    task.mark_completed(result_data or {}, result_metadata)
                elif status == "failed":
                    task.mark_failed(error_message or "Unknown error")
                else:
                    task.status = status
                
                await session.commit()
                
                logger.info(f"✅ Updated task {task_id} status to {status}")
                return True
                
            except Exception as e:
                logger.error(f"Error updating task status: {e}")
                await session.rollback()
                return False
    
    async def assign_task_to_agent(
        self,
        task_id: UUID,
        agent_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Assign task to a specific agent.
        
        Args:
            task_id: Task ID
            agent_id: Agent to assign task to
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                task = await self.get_task(task_id, db=session)
                if not task:
                    logger.error(f"Task {task_id} not found")
                    return False
                
                task.assign_to_agent(agent_id)
                await session.commit()
                
                logger.info(f"✅ Assigned task {task_id} to agent {agent_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error assigning task to agent: {e}")
                await session.rollback()
                return False
    
    async def cancel_task(
        self,
        task_id: UUID,
        reason: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: Task ID
            reason: Cancellation reason
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                task = await self.get_task(task_id, db=session)
                if not task:
                    logger.error(f"Task {task_id} not found")
                    return False
                
                task.cancel(reason)
                await session.commit()
                
                logger.info(f"✅ Cancelled task {task_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error cancelling task: {e}")
                await session.rollback()
                return False
    
    async def reschedule_task(
        self,
        task_id: UUID,
        new_time: datetime,
        reason: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Reschedule a task for a different time.
        
        Args:
            task_id: Task ID
            new_time: New scheduled time
            reason: Reschedule reason
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                task = await self.get_task(task_id, db=session)
                if not task:
                    logger.error(f"Task {task_id} not found")
                    return False
                
                task.reschedule(new_time, reason)
                await session.commit()
                
                logger.info(f"✅ Rescheduled task {task_id} to {new_time}")
                return True
                
            except Exception as e:
                logger.error(f"Error rescheduling task: {e}")
                await session.rollback()
                return False
    
    async def get_task_queue_stats(
        self,
        agent_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get task queue statistics.
        
        Args:
            agent_id: Filter by specific agent
            db: Database session (optional)
            
        Returns:
            Dict: Queue statistics
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                conditions = []
                if agent_id:
                    conditions.append(AgentTask.agent_id == agent_id)
                
                # Get status counts
                status_stmt = (
                    select(AgentTask.status, func.count(AgentTask.id))
                    .where(and_(*conditions) if conditions else True)
                    .group_by(AgentTask.status)
                )
                status_result = await session.execute(status_stmt)
                status_counts = dict(status_result.all())
                
                # Get priority distribution for pending tasks
                pending_conditions = conditions + [AgentTask.status == "pending"]
                priority_stmt = (
                    select(AgentTask.priority, func.count(AgentTask.id))
                    .where(and_(*pending_conditions))
                    .group_by(AgentTask.priority)
                    .order_by(AgentTask.priority)
                )
                priority_result = await session.execute(priority_stmt)
                priority_counts = dict(priority_result.all())
                
                # Get overdue tasks count
                overdue_conditions = pending_conditions + [
                    AgentTask.scheduled_at < datetime.now(timezone.utc)
                ]
                overdue_stmt = select(func.count(AgentTask.id)).where(and_(*overdue_conditions))
                overdue_result = await session.execute(overdue_stmt)
                overdue_count = overdue_result.scalar()
                
                # Get average processing time for completed tasks
                completed_conditions = conditions + [AgentTask.status == "completed"]
                avg_time_stmt = (
                    select(func.avg(AgentTask.actual_duration_seconds))
                    .where(and_(*completed_conditions))
                )
                avg_time_result = await session.execute(avg_time_stmt)
                avg_processing_time = avg_time_result.scalar()
                
                stats = {
                    "agent_id": str(agent_id) if agent_id else None,
                    "status_counts": status_counts,
                    "priority_distribution": priority_counts,
                    "overdue_tasks": overdue_count or 0,
                    "avg_processing_time_seconds": float(avg_processing_time) if avg_processing_time else None,
                    "total_tasks": sum(status_counts.values()),
                    "queue_health": "healthy" if (overdue_count or 0) < 10 else "degraded"
                }
                
                return stats
                
            except Exception as e:
                logger.error(f"Error getting task queue stats: {e}")
                return {"error": str(e)}
    
    async def clear_failed_tasks(
        self,
        agent_id: UUID,
        older_than_hours: int = 24,
        db: Optional[AsyncSession] = None
    ) -> int:
        """
        Clear old failed tasks for an agent.
        
        Args:
            agent_id: Agent ID
            older_than_hours: Clear tasks older than this many hours
            db: Database session (optional)
            
        Returns:
            int: Number of tasks cleared
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
                
                # Get failed tasks older than cutoff
                stmt = select(AgentTask).where(
                    and_(
                        AgentTask.agent_id == agent_id,
                        AgentTask.status == "failed",
                        AgentTask.completed_at < cutoff_time
                    )
                )
                
                result = await session.execute(stmt)
                failed_tasks = result.scalars().all()
                
                # Delete the tasks
                for task in failed_tasks:
                    await session.delete(task)
                
                await session.commit()
                
                count = len(failed_tasks)
                logger.info(f"✅ Cleared {count} failed tasks for agent {agent_id}")
                return count
                
            except Exception as e:
                logger.error(f"Error clearing failed tasks: {e}")
                await session.rollback()
                return 0
    
    async def create_health_check_task(
        self,
        agent_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> Optional[AgentTask]:
        """
        Create a health check task for an agent.
        
        Args:
            agent_id: Agent ID
            db: Database session (optional)
            
        Returns:
            AgentTask: Created health check task
        """
        return await self.create_task(
            agent_id=agent_id,
            task_type="health_check",
            task_data={
                "check_type": "routine",
                "checks": ["configuration", "database", "file_access", "tool_availability"]
            },
            priority=8,  # Lower priority
            max_retries=1,  # Limited retries for health checks
            source_channel="system",
            db=db
        )
    
    async def create_slack_message_task(
        self,
        agent_id: UUID,
        slack_data: Dict[str, Any],
        priority: int = 5,
        db: Optional[AsyncSession] = None
    ) -> Optional[AgentTask]:
        """
        Create a task for processing Slack message.
        
        Args:
            agent_id: Agent ID
            slack_data: Slack message data
            priority: Task priority
            db: Database session (optional)
            
        Returns:
            AgentTask: Created task
        """
        return await self.create_task(
            agent_id=agent_id,
            task_type="slack_message",
            task_data=slack_data,
            priority=priority,
            source_channel="slack",
            source_reference=slack_data.get("message_id"),
            correlation_id=slack_data.get("thread_ts"),
            db=db
        )
    
    async def create_email_task(
        self,
        agent_id: UUID,
        email_data: Dict[str, Any],
        priority: int = 4,
        db: Optional[AsyncSession] = None
    ) -> Optional[AgentTask]:
        """
        Create a task for processing email.
        
        Args:
            agent_id: Agent ID
            email_data: Email data
            priority: Task priority
            db: Database session (optional)
            
        Returns:
            AgentTask: Created task
        """
        return await self.create_task(
            agent_id=agent_id,
            task_type="email",
            task_data=email_data,
            priority=priority,
            source_channel="email",
            source_reference=email_data.get("message_id"),
            correlation_id=email_data.get("thread_id"),
            db=db
        )
    
    async def create_api_request_task(
        self,
        agent_id: UUID,
        request_data: Dict[str, Any],
        priority: int = 3,
        created_by_user_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[AgentTask]:
        """
        Create a task for processing API request.
        
        Args:
            agent_id: Agent ID
            request_data: API request data
            priority: Task priority
            created_by_user_id: User making the request
            db: Database session (optional)
            
        Returns:
            AgentTask: Created task
        """
        return await self.create_task(
            agent_id=agent_id,
            task_type="api_request",
            task_data=request_data,
            priority=priority,
            created_by_user_id=created_by_user_id,
            source_channel="api",
            source_reference=request_data.get("request_id"),
            db=db
        )
    


# Global agent task service instance
agent_task_service = AgentTaskService()