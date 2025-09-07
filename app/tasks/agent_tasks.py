#!/usr/bin/env python3
"""
Agent Processing Tasks for autonomous multi-channel agent operations
"""

import logging
import asyncio
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.services.agent_task_service import agent_task_service
from app.services.agent_service import agent_service
from app.services.agent_file_service import agent_file_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, queue="agent_processing")
def process_agent_task(self, task_id: str) -> Dict[str, Any]:
    """
    Main task processor for autonomous agent operations.
    
    Args:
        task_id: Agent task ID to process
        
    Returns:
        Dict: Processing result with status and metadata
    """
    try:
        task_uuid = UUID(task_id)
        logger.info(f"Starting autonomous processing for task {task_id}")
        start_time = datetime.now(timezone.utc)
        
        # Get task details
        task = asyncio.run(agent_task_service.get_task(task_uuid))
        if not task:
            logger.error(f"Task {task_id} not found")
            return {"status": "error", "error": "Task not found"}
        
        # Mark task as processing
        asyncio.run(agent_task_service.update_task_status(
            task_uuid, "processing"
        ))
        
        # Process based on task type
        if task.task_type == "slack_message":
            result = asyncio.run(process_slack_message(task))
        elif task.task_type == "email":
            result = asyncio.run(process_email_message(task))
        elif task.task_type == "api_request":
            result = asyncio.run(process_api_request(task))
        elif task.task_type == "health_check":
            result = asyncio.run(perform_health_check(task))
        else:
            result = {
                "success": False,
                "error": f"Unknown task type: {task.task_type}"
            }
        
        end_time = datetime.now(timezone.utc)
        duration_seconds = (end_time - start_time).total_seconds()
        
        # Update task status based on result
        if result.get("success"):
            asyncio.run(agent_task_service.update_task_status(
                task_uuid, 
                "completed", 
                result_data=result,
                result_metadata={
                    "processing_time_seconds": duration_seconds,
                    "completed_at": end_time.isoformat()
                }
            ))
            logger.info(f"✅ Completed task {task_id} in {duration_seconds:.2f}s")
        else:
            asyncio.run(agent_task_service.update_task_status(
                task_uuid,
                "failed",
                error_message=result.get("error", "Unknown error")
            ))
            logger.error(f"❌ Failed task {task_id}: {result.get('error')}")
        
        return {
            "task_id": task_id,
            "status": "completed" if result.get("success") else "failed",
            "processing_time_seconds": duration_seconds,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error in process_agent_task: {e}")
        # Mark task as failed
        try:
            asyncio.run(agent_task_service.update_task_status(
                UUID(task_id), "failed", error_message=str(e)
            ))
        except:
            pass
        
        # Retry with exponential backoff
        self.retry(countdown=60 * (2 ** self.request.retries), max_retries=3, exc=e)


async def process_slack_message(task) -> Dict[str, Any]:
    """
    Process a Slack message with autonomous agent response.
    
    Args:
        task: AgentTask containing Slack message data
        
    Returns:
        Dict: Processing result
    """
    try:
        logger.info(f"Processing Slack message for agent {task.agent_id}")
        
        # Get agent and prepare context
        agent = await agent_service.get_agent(task.agent_id)
        if not agent:
            return {"success": False, "error": "Agent not found"}
        
        # Assemble file context
        context = await agent_file_service.assemble_context_window(
            agent.id, max_context_length=agent.max_context_size or 50000
        )
        
        # Extract message data
        slack_data = task.task_data
        message_text = slack_data.get("text", "")
        user_id = slack_data.get("user")
        channel_id = slack_data.get("channel")
        
        # Simulate agent processing (would integrate with Pydantic AI here)
        response = await simulate_agent_response(
            agent=agent,
            message=message_text,
            context=context,
            platform="slack"
        )
        
        # Record action
        await record_agent_action(
            agent_id=agent.id,
            action_type="slack_response",
            action_data={
                "message": message_text,
                "channel": channel_id,
                "user": user_id
            },
            result_data={
                "response": response,
                "response_length": len(response)
            },
            success=True
        )
        
        return {
            "success": True,
            "response": response,
            "channel": channel_id,
            "platform": "slack"
        }
        
    except Exception as e:
        logger.error(f"Error processing Slack message: {e}")
        return {"success": False, "error": str(e)}


async def process_email_message(task) -> Dict[str, Any]:
    """
    Process an email with autonomous agent response.
    
    Args:
        task: AgentTask containing email data
        
    Returns:
        Dict: Processing result
    """
    try:
        logger.info(f"Processing email for agent {task.agent_id}")
        
        # Get agent and prepare context
        agent = await agent_service.get_agent(task.agent_id)
        if not agent:
            return {"success": False, "error": "Agent not found"}
        
        # Assemble file context
        context = await agent_file_service.assemble_context_window(
            agent.id, max_context_length=agent.max_context_size or 50000
        )
        
        # Extract email data
        email_data = task.task_data
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")
        from_email = email_data.get("from")
        
        # Simulate agent processing
        response = await simulate_agent_response(
            agent=agent,
            message=f"Subject: {subject}\n\n{body}",
            context=context,
            platform="email"
        )
        
        # Record action
        await record_agent_action(
            agent_id=agent.id,
            action_type="email_response",
            action_data={
                "subject": subject,
                "body": body,
                "from": from_email
            },
            result_data={
                "response": response,
                "response_length": len(response)
            },
            success=True
        )
        
        return {
            "success": True,
            "response": response,
            "from": from_email,
            "platform": "email"
        }
        
    except Exception as e:
        logger.error(f"Error processing email: {e}")
        return {"success": False, "error": str(e)}



async def process_api_request(task) -> Dict[str, Any]:
    """
    Process an API request with autonomous agent response.
    
    Args:
        task: AgentTask containing API request data
        
    Returns:
        Dict: Processing result
    """
    try:
        logger.info(f"Processing API request for agent {task.agent_id}")
        
        # Get agent and prepare context
        agent = await agent_service.get_agent(task.agent_id)
        if not agent:
            return {"success": False, "error": "Agent not found"}
        
        # Assemble file context
        context = await agent_file_service.assemble_context_window(
            agent.id, max_context_length=agent.max_context_size or 50000
        )
        
        # Extract request data
        request_data = task.task_data
        message = request_data.get("message", "")
        conversation_id = request_data.get("conversation_id")
        
        # Simulate agent processing
        response = await simulate_agent_response(
            agent=agent,
            message=message,
            context=context,
            platform="api"
        )
        
        # Record action
        await record_agent_action(
            agent_id=agent.id,
            action_type="api_response",
            action_data={
                "message": message,
                "conversation_id": conversation_id
            },
            result_data={
                "response": response,
                "response_length": len(response)
            },
            success=True
        )
        
        return {
            "success": True,
            "response": response,
            "conversation_id": conversation_id,
            "platform": "api"
        }
        
    except Exception as e:
        logger.error(f"Error processing API request: {e}")
        return {"success": False, "error": str(e)}


async def perform_health_check(task) -> Dict[str, Any]:
    """
    Perform comprehensive health check for an agent.
    
    Args:
        task: AgentTask containing health check data
        
    Returns:
        Dict: Health check results
    """
    try:
        logger.info(f"Performing health check for agent {task.agent_id}")
        
        health_results = {
            "agent_id": str(task.agent_id),
            "overall_status": "healthy",
            "checks": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Check 1: Agent configuration
        agent = await agent_service.get_agent(task.agent_id)
        health_results["checks"]["agent_exists"] = agent is not None
        health_results["checks"]["agent_active"] = agent.is_active if agent else False
        
        # Check 2: File access
        if agent:
            files_accessible = await agent_file_service.check_file_access(agent.id)
            health_results["checks"]["file_access"] = files_accessible
        
        # Check 3: Configuration validity
        if agent:
            config = agent.get_configuration()
            health_results["checks"]["configuration_valid"] = bool(config)
        
        # Determine overall status
        failed_checks = [k for k, v in health_results["checks"].items() if not v]
        if failed_checks:
            health_results["overall_status"] = "degraded"
            health_results["failed_checks"] = failed_checks
        
        # Record health check action
        await record_agent_action(
            agent_id=task.agent_id,
            action_type="health_check",
            action_data={
                "check_type": "routine",
                "checks_performed": list(health_results["checks"].keys())
            },
            result_data=health_results,
            success=health_results["overall_status"] != "error"
        )
        
        return {
            "success": True,
            "health_status": health_results["overall_status"],
            "details": health_results
        }
        
    except Exception as e:
        logger.error(f"Error performing health check: {e}")
        return {"success": False, "error": str(e)}


async def simulate_agent_response(agent, message: str, context: str, platform: str) -> str:
    """
    Simulate agent response processing (placeholder for Pydantic AI integration).
    
    Args:
        agent: Agent instance
        message: Input message
        context: File context
        platform: Platform (slack, email, api)
        
    Returns:
        str: Agent response
    """
    # This would integrate with Pydantic AI in real implementation
    logger.info(f"Simulating {agent.agent_type} agent response for {platform}")
    
    # Use agent configuration to personalize response
    tone = agent.tone or "professional"
    style = agent.communication_style or "formal"
    
    # Placeholder response based on agent settings
    if platform == "slack":
        if "hello" in message.lower():
            return f"Hello! I'm {agent.name}, ready to help with a {tone} {style} approach. How can I assist you today?"
        else:
            return f"I understand your message. As your {agent.agent_type} agent, I'll help you with a {tone} response."
    
    elif platform == "email":
        return f"""Thank you for your email.

As {agent.name}, I've processed your request with our {tone} {style} approach.

{f"Based on the context from {len(context.split()) if context else 0} words of documentation, " if context else ""}I'm here to provide comprehensive assistance.

Best regards,
{agent.name}"""
    
    else:  # API
        return f"I'm {agent.name}, your {agent.agent_type} agent. I've processed your request using our {tone} {style} approach."


async def record_agent_action(
    agent_id: UUID,
    action_type: str,
    action_data: Dict[str, Any],
    result_data: Dict[str, Any],
    success: bool = True,
    execution_time_ms: int = None
) -> None:
    """
    Record agent action for analytics and monitoring.
    
    Args:
        agent_id: Agent ID
        action_type: Type of action performed
        action_data: Action input data
        result_data: Action results
        success: Whether action was successful
        execution_time_ms: Execution time in milliseconds
    """
    try:
        # Import here to avoid circular imports
        from app.models.agent_action import AgentAction
        from app.database import get_async_db_session
        
        async with get_async_db_session() as session:
            action = AgentAction(
                agent_id=agent_id,
                action_type=action_type,
                action_data=action_data,
                result_data=result_data,
                success=success,
                execution_time_ms=execution_time_ms or 1000,  # Default 1 second
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc)
            )
            
            session.add(action)
            await session.commit()
            
        logger.debug(f"Recorded {action_type} action for agent {agent_id}")
        
    except Exception as e:
        logger.error(f"Error recording agent action: {e}")


@celery_app.task(bind=True, queue="agent_processing")
def batch_process_agent_tasks(self, agent_id: str, task_ids: List[str]) -> Dict[str, Any]:
    """
    Process multiple tasks for an agent in batch.
    
    Args:
        agent_id: Agent ID
        task_ids: List of task IDs to process
        
    Returns:
        Dict: Batch processing results
    """
    try:
        agent_uuid = UUID(agent_id)
        results = {
            "agent_id": agent_id,
            "total_tasks": len(task_ids),
            "successful": 0,
            "failed": 0,
            "task_results": []
        }
        
        logger.info(f"Starting batch processing of {len(task_ids)} tasks for agent {agent_id}")
        
        for task_id in task_ids:
            try:
                # Process each task
                result = process_agent_task.apply(args=[task_id])
                
                if result.result.get("status") == "completed":
                    results["successful"] += 1
                    results["task_results"].append({
                        "task_id": task_id, 
                        "status": "completed"
                    })
                else:
                    results["failed"] += 1
                    results["task_results"].append({
                        "task_id": task_id, 
                        "status": "failed"
                    })
                    
            except Exception as task_error:
                logger.error(f"Error processing task {task_id}: {task_error}")
                results["failed"] += 1
                results["task_results"].append({
                    "task_id": task_id, 
                    "status": "error", 
                    "error": str(task_error)
                })
        
        logger.info(f"✅ Completed batch processing for agent {agent_id}: {results['successful']} successful, {results['failed']} failed")
        return results
        
    except Exception as e:
        logger.error(f"Error in batch_process_agent_tasks: {e}")
        self.retry(countdown=120, max_retries=2, exc=e)


@celery_app.task(bind=True, queue="agent_maintenance")
def monitor_agent_health(self, agent_id: str) -> Dict[str, Any]:
    """
    Monitor agent health and performance.
    
    Args:
        agent_id: Agent ID to monitor
        
    Returns:
        Dict: Health monitoring results
    """
    try:
        agent_uuid = UUID(agent_id)
        logger.info(f"Monitoring health for agent {agent_id}")
        
        # Create and process health check task
        health_task = asyncio.run(
            agent_task_service.create_health_check_task(agent_uuid)
        )
        
        if health_task:
            # Process health check immediately
            health_result = process_agent_task.apply(args=[str(health_task.id)])
            return health_result.result
        else:
            return {"error": "Failed to create health check task"}
        
    except Exception as e:
        logger.error(f"Error monitoring agent health: {e}")
        self.retry(countdown=300, max_retries=3, exc=e)


@celery_app.task(bind=True, queue="agent_maintenance")
def cleanup_completed_tasks(self, older_than_days: int = 7) -> Dict[str, Any]:
    """
    Clean up old completed tasks to manage storage.
    
    Args:
        older_than_days: Clean up tasks older than this many days
        
    Returns:
        Dict: Cleanup results
    """
    try:
        logger.info(f"Cleaning up completed tasks older than {older_than_days} days")
        
        # This would implement cleanup logic
        results = {
            "cleaned_tasks": 0,
            "storage_freed": "0MB",
            "cleanup_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # In real implementation would:
        # 1. Query for completed tasks older than cutoff
        # 2. Archive or delete old tasks
        # 3. Update storage metrics
        
        logger.info(f"✅ Completed task cleanup: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Error cleaning up tasks: {e}")
        return {"error": str(e)}


# Periodic task to process pending tasks
@celery_app.task
def process_pending_tasks():
    """
    Process all pending tasks across agents.
    """
    try:
        logger.info("Processing pending tasks across all agents")
        
        # Get pending tasks
        pending_tasks = asyncio.run(
            agent_task_service.get_pending_tasks(limit=50)
        )
        
        processed = 0
        for task in pending_tasks:
            try:
                # Queue task for processing
                process_agent_task.delay(str(task.id))
                processed += 1
            except Exception as task_error:
                logger.error(f"Error queuing task {task.id}: {task_error}")
        
        logger.info(f"✅ Queued {processed} pending tasks for processing")
        return {"queued_tasks": processed}
        
    except Exception as e:
        logger.error(f"Error processing pending tasks: {e}")
        return {"error": str(e)}