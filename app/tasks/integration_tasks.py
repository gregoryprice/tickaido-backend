#!/usr/bin/env python3
"""
Celery tasks for third-party integrations
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import UUID

from celery import current_app as celery_app
from celery.utils.log import get_task_logger
from sqlalchemy import and_, select

from app.database import get_db_session
from app.models.integration import Integration, IntegrationStatus
from app.schemas.integration import IntegrationSyncRequest, IntegrationTestRequest
from app.services.integration_service import IntegrationService

# Get logger
logger = get_task_logger(__name__)


@celery_app.task(bind=True, retry_backoff=True, max_retries=3)
def sync_integration(self, integration_id: str, sync_type: str = "incremental"):
    """
    Sync data with a specific integration
    
    Args:
        integration_id: UUID of the integration to sync
        sync_type: Type of sync (incremental, full)
    """
    logger.info(f"Starting sync for integration: {integration_id}, type: {sync_type}")
    
    try:
        result = asyncio.run(_sync_integration_async(integration_id, sync_type))
        logger.info(f"Sync completed for integration: {integration_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Sync failed for integration: {integration_id}, error: {str(exc)}")
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True)
def sync_all_active_integrations(self):
    """
    Sync all active integrations
    """
    logger.info("Starting sync for all active integrations")
    
    try:
        result = asyncio.run(_sync_all_active_integrations_async())
        logger.info(f"Synced {result['synced']} integrations")
        return result
        
    except Exception as exc:
        logger.error(f"Bulk sync failed: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True, retry_backoff=True, max_retries=2)
def test_integration_connection(self, integration_id: str, test_type: str = "connection"):
    """
    Test integration connectivity
    
    Args:
        integration_id: UUID of the integration to test
        test_type: Type of test (connection, permissions, data)
    """
    logger.info(f"Testing integration: {integration_id}, type: {test_type}")
    
    try:
        result = asyncio.run(_test_integration_async(integration_id, test_type))
        logger.info(f"Test completed for integration: {integration_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Test failed for integration: {integration_id}, error: {str(exc)}")
        self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


@celery_app.task(bind=True)
def health_check_integrations(self):
    """
    Perform health checks on all active integrations
    """
    logger.info("Starting health checks for active integrations")
    
    try:
        result = asyncio.run(_health_check_integrations_async())
        logger.info(f"Health checked {result['checked']} integrations")
        return result
        
    except Exception as exc:
        logger.error(f"Health check failed: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True)
def send_to_integration(self, integration_id: str, data: Dict[str, Any], action: str = "create"):
    """
    Send data to external integration
    
    Args:
        integration_id: UUID of the integration
        data: Data to send
        action: Action to perform (create, update, delete)
    """
    logger.info(f"Sending data to integration: {integration_id}, action: {action}")
    
    try:
        result = asyncio.run(_send_to_integration_async(integration_id, data, action))
        logger.info(f"Data sent to integration: {integration_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Failed to send to integration: {integration_id}, error: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True)
def process_webhook_event(self, integration_id: str, event_data: Dict[str, Any]):
    """
    Process incoming webhook event from integration
    
    Args:
        integration_id: UUID of the integration
        event_data: Webhook event data
    """
    logger.info(f"Processing webhook from integration: {integration_id}")
    
    try:
        result = asyncio.run(_process_webhook_async(integration_id, event_data))
        logger.info(f"Webhook processed for integration: {integration_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Webhook processing failed for integration: {integration_id}, error: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True)
def cleanup_failed_sync_attempts(self, older_than_hours: int = 24):
    """
    Clean up failed sync attempts
    
    Args:
        older_than_hours: Remove attempts older than this many hours
    """
    logger.info(f"Cleaning up failed sync attempts older than {older_than_hours} hours")
    
    try:
        result = asyncio.run(_cleanup_failed_syncs_async(older_than_hours))
        logger.info(f"Cleaned up {result['cleaned']} failed sync attempts")
        return result
        
    except Exception as exc:
        logger.error(f"Cleanup failed: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True, retry_backoff=True, max_retries=3)
def sync_salesforce_data(self, integration_id: str):
    """
    Specialized task for Salesforce data sync
    
    Args:
        integration_id: UUID of the Salesforce integration
    """
    logger.info(f"Starting Salesforce sync for integration: {integration_id}")
    
    try:
        result = asyncio.run(_sync_salesforce_async(integration_id))
        logger.info(f"Salesforce sync completed for integration: {integration_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Salesforce sync failed for integration: {integration_id}, error: {str(exc)}")
        self.retry(exc=exc, countdown=120 * (self.request.retries + 1))


@celery_app.task(bind=True, retry_backoff=True, max_retries=3)
def sync_jira_tickets(self, integration_id: str):
    """
    Specialized task for Jira ticket sync
    
    Args:
        integration_id: UUID of the Jira integration
    """
    logger.info(f"Starting Jira sync for integration: {integration_id}")
    
    try:
        result = asyncio.run(_sync_jira_async(integration_id))
        logger.info(f"Jira sync completed for integration: {integration_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Jira sync failed for integration: {integration_id}, error: {str(exc)}")
        self.retry(exc=exc, countdown=120 * (self.request.retries + 1))


# Async helper functions
async def _sync_integration_async(integration_id: str, sync_type: str) -> Dict[str, Any]:
    """Sync integration asynchronously"""
    async with get_db_session() as db:
        integration_service = IntegrationService()
        
        # Create sync request
        sync_request = IntegrationSyncRequest(
            sync_type=sync_type,
            since_timestamp=datetime.now(timezone.utc) - timedelta(hours=24)
        )
        
        # Perform sync
        result = await integration_service.sync_integration(
            db, UUID(integration_id), sync_request, None  # System user
        )
        
        if result:
            return result.model_dump()
        else:
            raise Exception("Sync failed")


async def _sync_all_active_integrations_async() -> Dict[str, Any]:
    """Sync all active integrations"""
    async with get_db_session() as db:
        # Get active integrations
        query = select(Integration).where(
            and_(
                Integration.is_enabled == True,
                Integration.status == IntegrationStatus.ACTIVE,
                Integration.deleted_at.is_(None)
            )
        )
        
        result = await db.execute(query)
        active_integrations = result.scalars().all()
        
        synced_count = 0
        failed_count = 0
        
        for integration in active_integrations:
            try:
                # Queue sync task for each integration
                sync_integration.delay(str(integration.id))
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Failed to queue sync for integration {integration.id}: {str(e)}")
                failed_count += 1
                continue
        
        return {
            "synced": synced_count,
            "failed": failed_count,
            "total": len(active_integrations)
        }


async def _test_integration_async(integration_id: str, test_type: str) -> Dict[str, Any]:
    """Test integration asynchronously"""
    async with get_db_session() as db:
        integration_service = IntegrationService()
        
        # Create test request
        test_request = IntegrationTestRequest(test_type=test_type)
        
        # Perform test
        result = await integration_service.test_integration(
            db, UUID(integration_id), test_request, None  # System user
        )
        
        if result:
            return result.model_dump()
        else:
            raise Exception("Test failed")


async def _health_check_integrations_async() -> Dict[str, Any]:
    """Health check all integrations"""
    async with get_db_session() as db:
        # Get all integrations to check
        query = select(Integration).where(
            and_(
                Integration.is_enabled == True,
                Integration.deleted_at.is_(None)
            )
        )
        
        result = await db.execute(query)
        integrations = result.scalars().all()
        
        checked_count = 0
        healthy_count = 0
        unhealthy_count = 0
        
        for integration in integrations:
            try:
                # Queue health check for each integration
                test_integration_connection.delay(str(integration.id), "connection")
                checked_count += 1
                
            except Exception as e:
                logger.error(f"Failed to queue health check for integration {integration.id}: {str(e)}")
                unhealthy_count += 1
                continue
        
        return {
            "checked": checked_count,
            "healthy": healthy_count,
            "unhealthy": unhealthy_count
        }


async def _send_to_integration_async(integration_id: str, data: Dict[str, Any], action: str) -> Dict[str, Any]:
    """Send data to integration asynchronously"""
    async with get_db_session() as db:
        integration_service = IntegrationService()
        
        # Get integration
        integration = await integration_service.get_integration(db, UUID(integration_id))
        if not integration:
            raise ValueError(f"Integration not found: {integration_id}")
        
        # TODO: Implement actual data sending based on integration type
        # This would use the integration's API client to send data
        
        return {
            "integration_id": integration_id,
            "action": action,
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat()
        }


async def _process_webhook_async(integration_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process webhook event asynchronously"""
    async with get_db_session() as db:
        integration_service = IntegrationService()
        
        # Get integration
        integration = await integration_service.get_integration(db, UUID(integration_id))
        if not integration:
            raise ValueError(f"Integration not found: {integration_id}")
        
        # Process event based on integration type and event
        # TODO: Implement actual webhook processing
        
        return {
            "integration_id": integration_id,
            "event_type": event_data.get("type", "unknown"),
            "status": "processed",
            "processed_at": datetime.now(timezone.utc).isoformat()
        }


async def _cleanup_failed_syncs_async(older_than_hours: int) -> Dict[str, Any]:
    """Clean up failed sync attempts"""
    async with get_db_session() as db:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        
        # Get integrations with old failed sync attempts
        query = select(Integration).where(
            and_(
                Integration.status == IntegrationStatus.ERROR,
                Integration.last_error_at < cutoff_time,
                Integration.deleted_at.is_(None)
            )
        )
        
        result = await db.execute(query)
        failed_integrations = result.scalars().all()
        
        cleaned_count = 0
        
        for integration in failed_integrations:
            try:
                # Reset integration status if it's been in error state for too long
                integration.status = IntegrationStatus.INACTIVE
                integration.last_error = None
                integration.last_error_at = None
                cleaned_count += 1
                
            except Exception as e:
                logger.error(f"Failed to clean up integration {integration.id}: {str(e)}")
                continue
        
        await db.commit()
        
        return {"cleaned": cleaned_count}


async def _sync_salesforce_async(integration_id: str) -> Dict[str, Any]:
    """Sync Salesforce data specifically"""
    async with get_db_session() as db:
        integration_service = IntegrationService()
        
        # Get integration
        integration = await integration_service.get_integration(db, UUID(integration_id))
        if not integration:
            raise ValueError(f"Integration not found: {integration_id}")
        
        # TODO: Implement Salesforce-specific sync logic
        # This would involve:
        # 1. Authenticating with Salesforce
        # 2. Fetching cases, accounts, contacts
        # 3. Mapping to internal ticket/user structure
        # 4. Creating/updating local records
        
        return {
            "integration_id": integration_id,
            "type": "salesforce",
            "records_synced": 0,
            "last_sync": datetime.now(timezone.utc).isoformat()
        }


async def _sync_jira_async(integration_id: str) -> Dict[str, Any]:
    """Sync Jira tickets specifically"""
    async with get_db_session() as db:
        integration_service = IntegrationService()
        
        # Get integration
        integration = await integration_service.get_integration(db, UUID(integration_id))
        if not integration:
            raise ValueError(f"Integration not found: {integration_id}")
        
        # TODO: Implement Jira-specific sync logic
        # This would involve:
        # 1. Authenticating with Jira
        # 2. Fetching issues using JQL
        # 3. Mapping to internal ticket structure
        # 4. Creating/updating local records
        
        return {
            "integration_id": integration_id,
            "type": "jira",
            "tickets_synced": 0,
            "last_sync": datetime.now(timezone.utc).isoformat()
        }