#!/usr/bin/env python3
"""
Agent Action Service for tracking operations and performance analytics
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload

from app.models.agent_action import AgentAction
from app.models.ai_agent import Agent
from app.database import get_async_db_session

logger = logging.getLogger(__name__)


class AgentActionService:
    """
    Service for tracking and analyzing agent actions and performance metrics.
    
    Provides comprehensive monitoring of agent operations, performance analytics,
    and quality tracking for continuous improvement.
    """
    
    async def record_action(
        self,
        agent_id: UUID,
        action_type: str,
        action_data: Dict[str, Any],
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        source_channel: Optional[str] = None,
        action_subtype: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[AgentAction]:
        """
        Record the start of an agent action.
        
        Args:
            agent_id: Agent performing the action
            action_type: Type of action (chat_response, ticket_creation, etc.)
            action_data: Action input data
            user_id: User who triggered the action
            session_id: Session ID
            conversation_id: Conversation ID
            source_channel: Channel (api, slack, email, etc.)
            action_subtype: Action subtype
            db: Database session (optional)
            
        Returns:
            AgentAction: Created action record or None if failed
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                action = AgentAction(
                    agent_id=agent_id,
                    action_type=action_type,
                    action_subtype=action_subtype,
                    action_data=action_data,
                    user_id=user_id,
                    session_id=session_id,
                    conversation_id=conversation_id,
                    source_channel=source_channel,
                    started_at=datetime.now(timezone.utc)
                )
                
                session.add(action)
                await session.commit()
                await session.refresh(action)
                
                logger.debug(f"✅ Recorded {action_type} action for agent {agent_id}")
                return action
                
            except Exception as e:
                logger.error(f"Error recording agent action: {e}")
                await session.rollback()
                return None
    
    async def complete_action(
        self,
        action_id: UUID,
        result_data: Dict[str, Any],
        success: bool = True,
        error_message: Optional[str] = None,
        performance_metrics: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Mark an action as completed with results and metrics.
        
        Args:
            action_id: Action ID
            result_data: Action results
            success: Whether action was successful
            error_message: Error message if failed
            performance_metrics: Performance metrics (tokens, cost, etc.)
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                stmt = select(AgentAction).where(AgentAction.id == action_id)
                result = await session.execute(stmt)
                action = result.scalar_one_or_none()
                
                if not action:
                    logger.error(f"Action {action_id} not found")
                    return False
                
                # Mark completed
                action.mark_completed(result_data, success, error_message)
                
                # Set performance metrics if provided
                if performance_metrics:
                    action.set_performance_metrics(
                        tokens_used=performance_metrics.get("tokens_used"),
                        cost_cents=performance_metrics.get("cost_cents"),
                        confidence_score=performance_metrics.get("confidence_score")
                    )
                
                await session.commit()
                
                logger.debug(f"✅ Completed action {action_id} with success={success}")
                return True
                
            except Exception as e:
                logger.error(f"Error completing action: {e}")
                await session.rollback()
                return False
    
    async def get_agent_actions(
        self,
        agent_id: UUID,
        action_type: Optional[str] = None,
        success_only: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
        db: Optional[AsyncSession] = None
    ) -> List[AgentAction]:
        """
        Get actions for an agent with filtering options.
        
        Args:
            agent_id: Agent ID
            action_type: Filter by action type
            success_only: Filter by success status
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of actions
            offset: Number of actions to skip
            db: Database session (optional)
            
        Returns:
            List[AgentAction]: Agent actions
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                conditions = [AgentAction.agent_id == agent_id]
                
                if action_type:
                    conditions.append(AgentAction.action_type == action_type)
                
                if success_only is not None:
                    conditions.append(AgentAction.success == success_only)
                
                if start_date:
                    conditions.append(AgentAction.started_at >= start_date)
                
                if end_date:
                    conditions.append(AgentAction.started_at <= end_date)
                
                stmt = (
                    select(AgentAction)
                    .where(and_(*conditions))
                    .options(selectinload(AgentAction.user))
                    .order_by(desc(AgentAction.started_at))
                    .offset(offset)
                    .limit(limit)
                )
                
                result = await session.execute(stmt)
                actions = result.scalars().all()
                
                logger.debug(f"Found {len(actions)} actions for agent {agent_id}")
                return list(actions)
                
            except Exception as e:
                logger.error(f"Error getting agent actions: {e}")
                return []
    
    async def get_performance_metrics(
        self,
        agent_id: UUID,
        period_days: int = 7,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get performance metrics for an agent over a time period.
        
        Args:
            agent_id: Agent ID
            period_days: Number of days to analyze
            db: Database session (optional)
            
        Returns:
            Dict: Performance metrics
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                start_date = datetime.now(timezone.utc) - timedelta(days=period_days)
                
                conditions = [
                    AgentAction.agent_id == agent_id,
                    AgentAction.started_at >= start_date
                ]
                
                # Get basic metrics
                basic_stmt = (
                    select(
                        func.count(AgentAction.id).label('total_actions'),
                        func.count(func.nullif(AgentAction.success, False)).label('successful_actions'),
                        func.avg(AgentAction.execution_time_ms).label('avg_execution_time'),
                        func.sum(AgentAction.tokens_used).label('total_tokens'),
                        func.sum(AgentAction.cost_cents).label('total_cost_cents')
                    )
                    .where(and_(*conditions))
                )
                
                basic_result = await session.execute(basic_stmt)
                basic_metrics = basic_result.first()
                
                # Get action type distribution
                type_stmt = (
                    select(AgentAction.action_type, func.count(AgentAction.id))
                    .where(and_(*conditions))
                    .group_by(AgentAction.action_type)
                )
                
                type_result = await session.execute(type_stmt)
                action_types = dict(type_result.all())
                
                # Get performance categories
                perf_stmt = (
                    select(AgentAction.execution_time_ms)
                    .where(and_(*conditions))
                )
                
                perf_result = await session.execute(perf_stmt)
                execution_times = [row[0] for row in perf_result.all() if row[0]]
                
                # Categorize performance
                performance_categories = {
                    "fast": len([t for t in execution_times if t < 1000]),
                    "normal": len([t for t in execution_times if 1000 <= t < 5000]),
                    "slow": len([t for t in execution_times if 5000 <= t < 15000]),
                    "very_slow": len([t for t in execution_times if t >= 15000])
                }
                
                # Calculate success rate
                total_actions = basic_metrics.total_actions or 0
                successful_actions = basic_metrics.successful_actions or 0
                success_rate = (successful_actions / total_actions * 100) if total_actions > 0 else 0
                
                metrics = {
                    "agent_id": str(agent_id),
                    "period_days": period_days,
                    "total_actions": total_actions,
                    "successful_actions": successful_actions,
                    "success_rate": round(success_rate, 2),
                    "avg_execution_time_ms": float(basic_metrics.avg_execution_time) if basic_metrics.avg_execution_time else 0,
                    "total_tokens_used": basic_metrics.total_tokens or 0,
                    "total_cost_dollars": float(basic_metrics.total_cost_cents or 0) / 100,
                    "action_type_distribution": action_types,
                    "performance_categories": performance_categories,
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                return metrics
                
            except Exception as e:
                logger.error(f"Error getting performance metrics: {e}")
                return {"error": str(e)}
    
    async def get_quality_metrics(
        self,
        agent_id: UUID,
        period_days: int = 30,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get quality metrics for an agent.
        
        Args:
            agent_id: Agent ID
            period_days: Number of days to analyze
            db: Database session (optional)
            
        Returns:
            Dict: Quality metrics
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                start_date = datetime.now(timezone.utc) - timedelta(days=period_days)
                
                conditions = [
                    AgentAction.agent_id == agent_id,
                    AgentAction.started_at >= start_date
                ]
                
                # Get quality metrics
                quality_stmt = (
                    select(
                        func.avg(AgentAction.confidence_score).label('avg_confidence'),
                        func.avg(AgentAction.quality_score).label('avg_quality'),
                        func.avg(AgentAction.user_feedback_score).label('avg_user_feedback'),
                        func.count(func.nullif(AgentAction.user_feedback_score, None)).label('feedback_count')
                    )
                    .where(and_(*conditions))
                )
                
                quality_result = await session.execute(quality_stmt)
                quality_metrics = quality_result.first()
                
                # Get feedback distribution
                feedback_stmt = (
                    select(AgentAction.user_feedback_score, func.count(AgentAction.id))
                    .where(and_(*conditions + [AgentAction.user_feedback_score.isnot(None)]))
                    .group_by(AgentAction.user_feedback_score)
                )
                
                feedback_result = await session.execute(feedback_stmt)
                feedback_distribution = dict(feedback_result.all())
                
                metrics = {
                    "agent_id": str(agent_id),
                    "period_days": period_days,
                    "avg_confidence_score": float(quality_metrics.avg_confidence or 0),
                    "avg_quality_score": float(quality_metrics.avg_quality or 0),
                    "avg_user_feedback": float(quality_metrics.avg_user_feedback or 0),
                    "feedback_responses": quality_metrics.feedback_count or 0,
                    "feedback_distribution": feedback_distribution,
                    "quality_rating": self._calculate_quality_rating(quality_metrics),
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                return metrics
                
            except Exception as e:
                logger.error(f"Error getting quality metrics: {e}")
                return {"error": str(e)}
    
    async def get_conversation_analytics(
        self,
        agent_id: UUID,
        period_days: int = 7,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get conversation-based analytics for an agent.
        
        Args:
            agent_id: Agent ID
            period_days: Number of days to analyze
            db: Database session (optional)
            
        Returns:
            Dict: Conversation analytics
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                start_date = datetime.now(timezone.utc) - timedelta(days=period_days)
                
                conditions = [
                    AgentAction.agent_id == agent_id,
                    AgentAction.started_at >= start_date,
                    AgentAction.conversation_id.isnot(None)
                ]
                
                # Get conversation metrics
                conv_stmt = (
                    select(
                        func.count(func.distinct(AgentAction.conversation_id)).label('unique_conversations'),
                        func.avg(
                            func.count(AgentAction.id)
                        ).label('avg_actions_per_conversation')
                    )
                    .where(and_(*conditions))
                    .group_by(AgentAction.conversation_id)
                )
                
                conv_result = await session.execute(conv_stmt)
                conv_metrics = conv_result.first()
                
                # Get channel distribution
                channel_stmt = (
                    select(AgentAction.source_channel, func.count(AgentAction.id))
                    .where(and_(*conditions))
                    .group_by(AgentAction.source_channel)
                )
                
                channel_result = await session.execute(channel_stmt)
                channel_distribution = dict(channel_result.all())
                
                # Get session analytics
                session_stmt = (
                    select(
                        func.count(func.distinct(AgentAction.session_id)).label('unique_sessions'),
                        func.avg(AgentAction.execution_time_ms).label('avg_response_time')
                    )
                    .where(and_(*conditions))
                )
                
                session_result = await session.execute(session_stmt)
                session_metrics = session_result.first()
                
                analytics = {
                    "agent_id": str(agent_id),
                    "period_days": period_days,
                    "unique_conversations": conv_metrics.unique_conversations if conv_metrics else 0,
                    "avg_actions_per_conversation": float(conv_metrics.avg_actions_per_conversation or 0),
                    "unique_sessions": session_metrics.unique_sessions if session_metrics else 0,
                    "avg_response_time_ms": float(session_metrics.avg_response_time or 0),
                    "channel_distribution": channel_distribution,
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                return analytics
                
            except Exception as e:
                logger.error(f"Error getting conversation analytics: {e}")
                return {"error": str(e)}
    
    async def add_user_feedback(
        self,
        action_id: UUID,
        feedback_score: int,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Add user feedback to an action.
        
        Args:
            action_id: Action ID
            feedback_score: Feedback score (1-5)
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                stmt = select(AgentAction).where(AgentAction.id == action_id)
                result = await session.execute(stmt)
                action = result.scalar_one_or_none()
                
                if not action:
                    logger.error(f"Action {action_id} not found")
                    return False
                
                action.set_quality_metrics(user_feedback_score=feedback_score)
                await session.commit()
                
                logger.info(f"✅ Added feedback score {feedback_score} to action {action_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error adding user feedback: {e}")
                await session.rollback()
                return False
    
    async def get_top_performing_agents(
        self,
        organization_id: UUID,
        period_days: int = 30,
        limit: int = 10,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top performing agents for an organization.
        
        Args:
            organization_id: Organization ID
            period_days: Number of days to analyze
            limit: Maximum number of agents
            db: Database session (optional)
            
        Returns:
            List[Dict]: Top performing agents with metrics
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                start_date = datetime.now(timezone.utc) - timedelta(days=period_days)
                
                # Get agents with performance metrics
                stmt = (
                    select(
                        Agent.id,
                        Agent.name,
                        Agent.agent_type,
                        func.count(AgentAction.id).label('total_actions'),
                        func.avg(
                            func.case(
                                (AgentAction.success == True, 1.0),
                                else_=0.0
                            )
                        ).label('success_rate'),
                        func.avg(AgentAction.execution_time_ms).label('avg_response_time'),
                        func.avg(AgentAction.user_feedback_score).label('avg_feedback')
                    )
                    .select_from(Agent)
                    .join(AgentAction, Agent.id == AgentAction.agent_id)
                    .where(
                        and_(
                            Agent.organization_id == organization_id,
                            Agent.is_active == True,
                            AgentAction.started_at >= start_date
                        )
                    )
                    .group_by(Agent.id, Agent.name, Agent.agent_type)
                    .having(func.count(AgentAction.id) > 0)
                    .order_by(desc('success_rate'), desc('total_actions'))
                    .limit(limit)
                )
                
                result = await session.execute(stmt)
                agent_metrics = result.all()
                
                top_agents = []
                for metrics in agent_metrics:
                    agent_data = {
                        "agent_id": str(metrics.id),
                        "agent_name": metrics.name,
                        "agent_type": metrics.agent_type,
                        "total_actions": metrics.total_actions,
                        "success_rate": round(float(metrics.success_rate or 0) * 100, 2),
                        "avg_response_time_ms": float(metrics.avg_response_time or 0),
                        "avg_user_feedback": float(metrics.avg_feedback or 0),
                        "performance_score": self._calculate_performance_score(metrics)
                    }
                    top_agents.append(agent_data)
                
                return top_agents
                
            except Exception as e:
                logger.error(f"Error getting top performing agents: {e}")
                return []
    
    def _calculate_quality_rating(self, metrics) -> str:
        """Calculate overall quality rating from metrics"""
        confidence = float(metrics.avg_confidence or 0)
        quality = float(metrics.avg_quality or 0)
        feedback = float(metrics.avg_user_feedback or 0)
        
        # Weighted average (confidence: 30%, quality: 40%, feedback: 30%)
        if feedback > 0:
            overall = (confidence * 0.3 + quality * 0.4 + feedback * 0.3)
        else:
            overall = (confidence * 0.5 + quality * 0.5)
        
        if overall >= 0.8:
            return "excellent"
        elif overall >= 0.6:
            return "good"
        elif overall >= 0.4:
            return "fair"
        else:
            return "needs_improvement"
    
    def _calculate_performance_score(self, metrics) -> float:
        """Calculate performance score from multiple metrics"""
        success_rate = float(metrics.success_rate or 0)
        response_time = float(metrics.avg_response_time or 5000)
        feedback = float(metrics.avg_feedback or 3.0)
        
        # Normalize response time (lower is better, max 10 seconds)
        time_score = max(0, (10000 - min(response_time, 10000)) / 10000)
        
        # Normalize feedback (scale 1-5 to 0-1)
        feedback_score = (feedback - 1) / 4 if feedback > 0 else 0.5
        
        # Weighted score
        score = (success_rate * 0.5 + time_score * 0.3 + feedback_score * 0.2)
        return round(score, 3)


# Global agent action service instance
agent_action_service = AgentActionService()