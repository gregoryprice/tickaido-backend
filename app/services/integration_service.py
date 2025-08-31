#!/usr/bin/env python3
"""
Integration Service - Business logic for third-party integrations
"""

import json
import httpx
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timezone
from urllib.parse import urljoin

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.integration import DBIntegration, IntegrationType, IntegrationStatus
from app.models.user import DBUser
from app.models.ticket import DBTicket
from app.schemas.integration import (
    IntegrationCreateRequest,
    IntegrationUpdateRequest,
    IntegrationStatusUpdateRequest,
    IntegrationTestRequest,
    IntegrationSyncRequest,
    IntegrationDetailResponse,
    IntegrationTestResponse,
    IntegrationSyncResponse,
    IntegrationSearchParams,
    IntegrationSortParams
)
from app.config.settings import get_settings


class IntegrationService:
    """Service class for third-party integration operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def create_integration(
        self,
        db: AsyncSession,
        integration_request: IntegrationCreateRequest,
        user_id: UUID
    ) -> DBIntegration:
        """
        Create a new integration
        
        Args:
            db: Database session
            integration_request: Integration creation request data
            user_id: ID of user creating integration
            
        Returns:
            Created integration record
        """
        # Validate configuration based on type
        self._validate_integration_config(
            integration_request.integration_type,
            integration_request.configuration
        )
        
        # Create integration record
        db_integration = DBIntegration(
            name=integration_request.name,
            integration_type=integration_request.integration_type,
            configuration=integration_request.configuration,
            status=IntegrationStatus.INACTIVE,
            is_enabled=False,
            created_by=user_id,
            description=integration_request.description,
            webhook_url=integration_request.webhook_url,
            sync_frequency_minutes=integration_request.sync_frequency_minutes,
            routing_rules=integration_request.routing_rules or [],
            field_mappings=integration_request.field_mappings or {},
            metadata=integration_request.metadata or {}
        )
        
        db.add(db_integration)
        await db.commit()
        await db.refresh(db_integration)
        
        return db_integration
    
    async def get_integration(
        self,
        db: AsyncSession,
        integration_id: UUID,
        include_stats: bool = False
    ) -> Optional[DBIntegration]:
        """
        Get integration by ID
        
        Args:
            db: Database session
            integration_id: Integration ID
            include_stats: Whether to include usage statistics
            
        Returns:
            Integration record if found
        """
        query = select(DBIntegration).where(
            and_(DBIntegration.id == integration_id, DBIntegration.is_deleted == False)
        )
        
        if include_stats:
            query = query.options(
                selectinload(DBIntegration.created_by_user),
                selectinload(DBIntegration.tickets)
            )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_integrations(
        self,
        db: AsyncSession,
        offset: int = 0,
        limit: int = 20,
        search_params: Optional[IntegrationSearchParams] = None,
        sort_params: Optional[IntegrationSortParams] = None,
        user_id: Optional[UUID] = None
    ) -> Tuple[List[DBIntegration], int]:
        """
        List integrations with filtering and pagination
        
        Args:
            db: Database session
            offset: Number of records to skip
            limit: Maximum number of records to return
            search_params: Search parameters
            sort_params: Sort parameters
            user_id: Filter by user ID (for user-specific integrations)
            
        Returns:
            Tuple of (integrations list, total count)
        """
        # Base query
        query = select(DBIntegration).where(DBIntegration.is_deleted == False)
        count_query = select(func.count(DBIntegration.id)).where(DBIntegration.is_deleted == False)
        
        # Apply filters
        filters = []
        
        if user_id:
            filters.append(DBIntegration.created_by == user_id)
        
        if search_params:
            if search_params.name:
                filters.append(DBIntegration.name.ilike(f"%{search_params.name}%"))
            
            if search_params.integration_type:
                filters.append(DBIntegration.integration_type == search_params.integration_type)
            
            if search_params.status:
                filters.append(DBIntegration.status == search_params.status)
            
            if search_params.is_enabled is not None:
                filters.append(DBIntegration.is_enabled == search_params.is_enabled)
            
            if search_params.created_after:
                filters.append(DBIntegration.created_at >= search_params.created_after)
            
            if search_params.created_before:
                filters.append(DBIntegration.created_at <= search_params.created_before)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Apply sorting
        if sort_params:
            sort_field = getattr(DBIntegration, sort_params.sort_by, DBIntegration.created_at)
            if sort_params.sort_order == "desc":
                query = query.order_by(sort_field.desc())
            else:
                query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(DBIntegration.created_at.desc())
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute queries
        integrations_result = await db.execute(query)
        count_result = await db.execute(count_query)
        
        integrations = integrations_result.scalars().all()
        total = count_result.scalar()
        
        return list(integrations), total
    
    async def update_integration(
        self,
        db: AsyncSession,
        integration_id: UUID,
        update_request: IntegrationUpdateRequest,
        user_id: UUID
    ) -> Optional[DBIntegration]:
        """
        Update integration settings
        
        Args:
            db: Database session
            integration_id: Integration ID
            update_request: Update request data
            user_id: ID of updating user
            
        Returns:
            Updated integration record if found
        """
        db_integration = await self.get_integration(db, integration_id)
        if not db_integration:
            return None
        
        # Check permissions (owner or admin)
        if db_integration.created_by != user_id:
            # TODO: Check if user is admin
            pass
        
        # Update fields
        update_data = update_request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "configuration" and value:
                # Validate configuration
                self._validate_integration_config(
                    db_integration.integration_type,
                    value
                )
            
            if hasattr(db_integration, field):
                setattr(db_integration, field, value)
        
        db_integration.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(db_integration)
        
        return db_integration
    
    async def test_integration(
        self,
        db: AsyncSession,
        integration_id: UUID,
        test_request: IntegrationTestRequest,
        user_id: UUID
    ) -> Optional[IntegrationTestResponse]:
        """
        Test integration connectivity and configuration
        
        Args:
            db: Database session
            integration_id: Integration ID
            test_request: Test request data
            user_id: ID of requesting user
            
        Returns:
            Test results if successful
        """
        db_integration = await self.get_integration(db, integration_id)
        if not db_integration:
            return None
        
        try:
            # Test based on integration type
            test_results = await self._test_integration_by_type(
                db_integration.integration_type,
                db_integration.configuration,
                test_request.test_type
            )
            
            # Update last tested time
            db_integration.last_tested_at = datetime.now(timezone.utc)
            await db.commit()
            
            return IntegrationTestResponse(
                integration_id=integration_id,
                test_type=test_request.test_type,
                status="success",
                results=test_results,
                tested_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            return IntegrationTestResponse(
                integration_id=integration_id,
                test_type=test_request.test_type,
                status="error",
                error=str(e),
                tested_at=datetime.now(timezone.utc)
            )
    
    async def sync_integration(
        self,
        db: AsyncSession,
        integration_id: UUID,
        sync_request: IntegrationSyncRequest,
        user_id: UUID
    ) -> Optional[IntegrationSyncResponse]:
        """
        Perform data synchronization with integration
        
        Args:
            db: Database session
            integration_id: Integration ID
            sync_request: Sync request data
            user_id: ID of requesting user
            
        Returns:
            Sync results if successful
        """
        db_integration = await self.get_integration(db, integration_id)
        if not db_integration:
            return None
        
        if not db_integration.is_enabled:
            raise ValueError("Integration is not enabled")
        
        try:
            # Update status to syncing
            db_integration.status = IntegrationStatus.SYNCING
            db_integration.last_sync_started_at = datetime.now(timezone.utc)
            await db.commit()
            
            # Perform sync based on integration type
            sync_results = await self._sync_integration_by_type(
                db_integration.integration_type,
                db_integration.configuration,
                sync_request.sync_type,
                sync_request.since_timestamp
            )
            
            # Update sync status
            db_integration.status = IntegrationStatus.ACTIVE
            db_integration.last_sync_completed_at = datetime.now(timezone.utc)
            db_integration.sync_count = (db_integration.sync_count or 0) + 1
            await db.commit()
            
            return IntegrationSyncResponse(
                integration_id=integration_id,
                sync_type=sync_request.sync_type,
                status="completed",
                results=sync_results,
                synced_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            # Update error status
            db_integration.status = IntegrationStatus.ERROR
            db_integration.last_error = str(e)
            db_integration.last_error_at = datetime.now(timezone.utc)
            await db.commit()
            
            return IntegrationSyncResponse(
                integration_id=integration_id,
                sync_type=sync_request.sync_type,
                status="error",
                error=str(e),
                synced_at=datetime.now(timezone.utc)
            )
    
    async def enable_integration(
        self,
        db: AsyncSession,
        integration_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Enable integration
        
        Args:
            db: Database session
            integration_id: Integration ID
            user_id: ID of requesting user
            
        Returns:
            True if enabled successfully
        """
        db_integration = await self.get_integration(db, integration_id)
        if not db_integration:
            return False
        
        # Test integration before enabling
        test_request = IntegrationTestRequest(test_type="connection")
        test_result = await self.test_integration(db, integration_id, test_request, user_id)
        
        if not test_result or test_result.status != "success":
            raise ValueError("Integration test failed - cannot enable")
        
        db_integration.is_enabled = True
        db_integration.status = IntegrationStatus.ACTIVE
        db_integration.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        return True
    
    async def disable_integration(
        self,
        db: AsyncSession,
        integration_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Disable integration
        
        Args:
            db: Database session
            integration_id: Integration ID
            user_id: ID of requesting user
            
        Returns:
            True if disabled successfully
        """
        db_integration = await self.get_integration(db, integration_id)
        if not db_integration:
            return False
        
        db_integration.is_enabled = False
        db_integration.status = IntegrationStatus.INACTIVE
        db_integration.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        return True
    
    async def delete_integration(
        self,
        db: AsyncSession,
        integration_id: UUID,
        user_id: UUID,
        hard_delete: bool = False
    ) -> bool:
        """
        Delete integration
        
        Args:
            db: Database session
            integration_id: Integration ID
            user_id: ID of requesting user
            hard_delete: Whether to permanently delete
            
        Returns:
            True if deleted successfully
        """
        db_integration = await self.get_integration(db, integration_id)
        if not db_integration:
            return False
        
        # Check permissions
        if db_integration.created_by != user_id:
            # TODO: Check if user is admin
            pass
        
        if hard_delete:
            await db.delete(db_integration)
        else:
            db_integration.soft_delete()
        
        await db.commit()
        return True
    
    def _validate_integration_config(
        self,
        integration_type: IntegrationType,
        configuration: Dict[str, Any]
    ) -> None:
        """Validate integration configuration based on type"""
        required_fields = self._get_required_config_fields(integration_type)
        
        for field in required_fields:
            if field not in configuration:
                raise ValueError(f"Missing required configuration field: {field}")
    
    def _get_required_config_fields(self, integration_type: IntegrationType) -> List[str]:
        """Get required configuration fields for integration type"""
        field_map = {
            IntegrationType.SALESFORCE: ["client_id", "client_secret", "instance_url"],
            IntegrationType.JIRA: ["url", "email", "api_token"],
            IntegrationType.SERVICENOW: ["instance_url", "username", "password"],
            IntegrationType.ZENDESK: ["subdomain", "email", "api_token"],
            IntegrationType.GITHUB: ["token", "organization"],
            IntegrationType.SLACK: ["bot_token", "channel"],
            IntegrationType.TEAMS: ["webhook_url"],
            IntegrationType.ZOOM: ["client_id", "client_secret"],
            IntegrationType.EMAIL: ["smtp_host", "smtp_port", "username", "password"],
            IntegrationType.WEBHOOK: ["url"]
        }
        
        return field_map.get(integration_type, [])
    
    async def _test_integration_by_type(
        self,
        integration_type: IntegrationType,
        configuration: Dict[str, Any],
        test_type: str
    ) -> Dict[str, Any]:
        """Test integration based on type"""
        if integration_type == IntegrationType.SALESFORCE:
            return await self._test_salesforce(configuration, test_type)
        elif integration_type == IntegrationType.JIRA:
            return await self._test_jira(configuration, test_type)
        elif integration_type == IntegrationType.SLACK:
            return await self._test_slack(configuration, test_type)
        elif integration_type == IntegrationType.WEBHOOK:
            return await self._test_webhook(configuration, test_type)
        else:
            return {"message": f"Test not implemented for {integration_type}"}
    
    async def _sync_integration_by_type(
        self,
        integration_type: IntegrationType,
        configuration: Dict[str, Any],
        sync_type: str,
        since_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Sync data based on integration type"""
        if integration_type == IntegrationType.SALESFORCE:
            return await self._sync_salesforce(configuration, sync_type, since_timestamp)
        elif integration_type == IntegrationType.JIRA:
            return await self._sync_jira(configuration, sync_type, since_timestamp)
        elif integration_type == IntegrationType.SLACK:
            return await self._sync_slack(configuration, sync_type, since_timestamp)
        else:
            return {"message": f"Sync not implemented for {integration_type}"}
    
    async def _test_salesforce(
        self,
        config: Dict[str, Any],
        test_type: str
    ) -> Dict[str, Any]:
        """Test Salesforce integration"""
        try:
            # OAuth 2.0 authentication test
            auth_url = f"{config['instance_url']}/services/oauth2/token"
            auth_data = {
                "grant_type": "client_credentials",
                "client_id": config["client_id"],
                "client_secret": config["client_secret"]
            }
            
            response = await self.http_client.post(auth_url, data=auth_data)
            response.raise_for_status()
            
            token_data = response.json()
            
            if test_type == "connection":
                return {"status": "connected", "instance": config["instance_url"]}
            elif test_type == "permissions":
                # Test API access
                api_url = f"{config['instance_url']}/services/data/v58.0/"
                headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                
                api_response = await self.http_client.get(api_url, headers=headers)
                api_response.raise_for_status()
                
                return {"status": "authorized", "permissions": ["read", "write"]}
        
        except Exception as e:
            raise Exception(f"Salesforce test failed: {str(e)}")
    
    async def _test_jira(
        self,
        config: Dict[str, Any],
        test_type: str
    ) -> Dict[str, Any]:
        """Test Jira integration"""
        try:
            auth = (config["email"], config["api_token"])
            url = f"{config['url']}/rest/api/3/myself"
            
            response = await self.http_client.get(url, auth=auth)
            response.raise_for_status()
            
            user_data = response.json()
            
            return {
                "status": "connected",
                "user": user_data.get("displayName"),
                "url": config["url"]
            }
        
        except Exception as e:
            raise Exception(f"Jira test failed: {str(e)}")
    
    async def _test_slack(
        self,
        config: Dict[str, Any],
        test_type: str
    ) -> Dict[str, Any]:
        """Test Slack integration"""
        try:
            headers = {"Authorization": f"Bearer {config['bot_token']}"}
            url = "https://slack.com/api/auth.test"
            
            response = await self.http_client.post(url, headers=headers)
            response.raise_for_status()
            
            auth_data = response.json()
            
            if not auth_data.get("ok"):
                raise Exception(auth_data.get("error", "Unknown error"))
            
            return {
                "status": "connected",
                "team": auth_data.get("team"),
                "user": auth_data.get("user")
            }
        
        except Exception as e:
            raise Exception(f"Slack test failed: {str(e)}")
    
    async def _test_webhook(
        self,
        config: Dict[str, Any],
        test_type: str
    ) -> Dict[str, Any]:
        """Test webhook integration"""
        try:
            test_payload = {"test": True, "timestamp": datetime.now(timezone.utc).isoformat()}
            
            response = await self.http_client.post(
                config["url"],
                json=test_payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            return {
                "status": "connected",
                "response_code": response.status_code,
                "url": config["url"]
            }
        
        except Exception as e:
            raise Exception(f"Webhook test failed: {str(e)}")
    
    async def _sync_salesforce(
        self,
        config: Dict[str, Any],
        sync_type: str,
        since_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Sync data with Salesforce"""
        # TODO: Implement Salesforce data sync
        return {"synced_records": 0, "sync_type": sync_type}
    
    async def _sync_jira(
        self,
        config: Dict[str, Any],
        sync_type: str,
        since_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Sync data with Jira"""
        # TODO: Implement Jira data sync
        return {"synced_records": 0, "sync_type": sync_type}
    
    async def _sync_slack(
        self,
        config: Dict[str, Any],
        sync_type: str,
        since_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Sync data with Slack"""
        # TODO: Implement Slack data sync
        return {"synced_records": 0, "sync_type": sync_type}
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.http_client.aclose()