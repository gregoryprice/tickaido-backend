#!/usr/bin/env python3
"""
Integration Service - Business logic for third-party integrations
"""

import httpx
import time
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.models.integration import Integration, IntegrationStatus
from app.models.user import User
from app.schemas.integration import (
    IntegrationCreateRequest,
    IntegrationUpdateRequest,
    IntegrationTestRequest,
    IntegrationSyncRequest,
    IntegrationTestResponse,
    IntegrationSyncResponse,
    IntegrationStatusUpdateRequest,
    IntegrationSearchParams,
    IntegrationSortParams
)
from app.config.settings import get_settings
from app.utils.http_debug_logger import log_http_request_response_pair
from .integration_interface import IntegrationInterface
from .jira_integration import JiraIntegration


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
    ) -> Integration:
        """
        Create a new integration
        
        Args:
            db: Database session
            integration_request: Integration creation request data
            user_id: ID of user creating integration
            
        Returns:
            Created integration record
        """
        # Get user's organization
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found")
            
        # Validate credentials based on type
        self._validate_credentials(
            integration_request.platform_name,
            integration_request.credentials
        )
        
        # Create integration record with organization support
        db_integration = Integration(
            name=integration_request.name,
            integration_category=integration_request.integration_category,
            platform_name=integration_request.platform_name,
            status=IntegrationStatus.PENDING,
            organization_id=user.organization_id,  # Associate with user's organization
            description=integration_request.description,
            base_url=integration_request.base_url,
            api_version=integration_request.api_version,
            auth_type=integration_request.auth_type,
            oauth_scopes=integration_request.oauth_scopes,
            webhook_url=integration_request.webhook_url,
            sync_enabled=integration_request.sync_enabled,
            sync_frequency_minutes=integration_request.sync_frequency_minutes,
            routing_rules=integration_request.routing_rules,
            default_priority=integration_request.default_priority,
            supports_categories=integration_request.supports_categories,
            supports_priorities=integration_request.supports_priorities,
            department_mapping=integration_request.department_mapping,
            custom_fields_mapping=integration_request.custom_fields_mapping,
            rate_limit_per_hour=integration_request.rate_limit_per_hour,
            notification_events=integration_request.notification_events,
            notification_channels=integration_request.notification_channels,
            environment=integration_request.environment,
            region=integration_request.region
        )
        
        # Set credentials securely using the model's encryption method
        db_integration.set_credentials(integration_request.credentials)
        
        # Set webhook secret if provided
        if integration_request.webhook_secret:
            db_integration.set_webhook_secret(integration_request.webhook_secret)
        
        db.add(db_integration)
        await db.commit()
        await db.refresh(db_integration)
        
        return db_integration
    
    async def get_integration(
        self,
        db: AsyncSession,
        integration_id: UUID,
        user_id: UUID,
        include_stats: bool = False
    ) -> Optional[Integration]:
        """
        Get integration by ID (organization-filtered)
        
        Args:
            db: Database session
            integration_id: Integration ID
            user_id: User ID for organization filtering
            include_stats: Whether to include usage statistics
            
        Returns:
            Integration record if found and accessible by user's organization
        """
        # Get user's organization
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return None
            
        # Query integration filtered by organization
        query = select(Integration).where(
            and_(
                Integration.id == integration_id,
                Integration.is_deleted == False,
                Integration.organization_id == user.organization_id
            )
        )
        
        if include_stats:
            query = query.options(
                selectinload(Integration.organization)
            )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_integrations(
        self,
        db: AsyncSession,
        user_id: UUID,
        offset: int = 0,
        limit: int = 20,
        search_params: Optional[IntegrationSearchParams] = None,
        sort_params: Optional[IntegrationSortParams] = None,
        created_by_filter: Optional[UUID] = None
    ) -> Tuple[List[Integration], int]:
        """
        List integrations with organization filtering and pagination
        
        Args:
            db: Database session
            user_id: User ID for organization filtering
            offset: Number of records to skip
            limit: Maximum number of records to return
            search_params: Search parameters
            sort_params: Sort parameters
            created_by_filter: Filter by specific creator user ID
            
        Returns:
            Tuple of (integrations list, total count)
        """
        # Get user's organization
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return [], 0
        
        # Base query with organization filtering
        base_filter = and_(
            Integration.is_deleted == False,
            Integration.organization_id == user.organization_id
        )
        
        query = select(Integration).where(base_filter)
        count_query = select(func.count(Integration.id)).where(base_filter)
        
        # Apply additional filters
        filters = []
        
        # TODO: Add created_by filter once user relationship is implemented
        # if created_by_filter:
        #     filters.append(Integration.created_by == created_by_filter)
        
        if search_params:
            if search_params.q:
                filters.append(Integration.name.ilike(f"%{search_params.q}%"))
            
            if search_params.integration_category:
                if isinstance(search_params.integration_category, list):
                    filters.append(Integration.integration_category.in_(search_params.integration_category))
                else:
                    filters.append(Integration.integration_category == search_params.integration_category)
            
            if search_params.status:
                if isinstance(search_params.status, list):
                    filters.append(Integration.status.in_(search_params.status))
                else:
                    filters.append(Integration.status == search_params.status)
            
            if search_params.enabled is not None:
                filters.append(Integration.enabled == search_params.enabled)
            
            if search_params.created_after:
                filters.append(Integration.created_at >= search_params.created_after)
            
            if search_params.created_before:
                filters.append(Integration.created_at <= search_params.created_before)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Apply sorting
        if sort_params:
            sort_field = getattr(Integration, sort_params.sort_by, Integration.created_at)
            if sort_params.sort_order == "desc":
                query = query.order_by(sort_field.desc())
            else:
                query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(Integration.created_at.desc())
        
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
    ) -> Optional[Integration]:
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
        db_integration = await self.get_integration(db, integration_id, user_id)
        if not db_integration:
            return None
        
        # Check permissions (owner or admin)
        # TODO: Add proper permission checking once user relationship is implemented
        # if db_integration.created_by != user_id:
        #     # TODO: Check if user is admin
        #     pass
        
        # Update fields
        update_data = update_request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "configuration" and value:
                # Validate configuration
                self._validate_credentials(
                    db_integration.platform_name,
                    value
                )
            
            if hasattr(db_integration, field):
                setattr(db_integration, field, value)
        
        db_integration.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(db_integration)
        
        return db_integration
    
    async def update_integration_status(
        self,
        db: AsyncSession,
        integration_id: UUID,
        status_update: IntegrationStatusUpdateRequest,
        user_id: UUID
    ) -> Optional[Integration]:
        """
        Update integration status (enable/disable)
        
        Args:
            db: Database session
            integration_id: Integration ID
            status_update: Status update request data
            user_id: ID of updating user
            
        Returns:
            Updated integration record if found
        """
        db_integration = await self.get_integration(db, integration_id, user_id)
        if not db_integration:
            return None
        
        # Update enabled status and automatically manage integration status
        if hasattr(status_update, 'enabled') and status_update.enabled is not None:
            db_integration.set_enabled(status_update.enabled, status_update.reason)
        elif hasattr(status_update, 'reason') and status_update.reason:
            # Add the reason to metadata if it exists
            if not db_integration.metadata:
                db_integration.metadata = {}
            db_integration.metadata['status_update_reason'] = status_update.reason
        
        db_integration.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(db_integration)
        
        return db_integration
    
    async def test_integration(
        self,
        db: AsyncSession,
        integration_id: UUID,
        test_request: IntegrationTestRequest,
        user_id: UUID,
        auto_activate_on_success: bool = False
    ) -> Optional[IntegrationTestResponse]:
        """
        Test integration connectivity and configuration using generic interface.
        
        Args:
            db: Database session
            integration_id: Integration ID
            test_request: Test request data
            user_id: ID of requesting user
            auto_activate_on_success: Whether to auto-activate on successful test
            
        Returns:
            Test results if successful
        """
        db_integration = await self.get_integration(db, integration_id, user_id)
        if not db_integration:
            return None
        
        try:
            # Get integration implementation
            integration_impl = self._get_integration_implementation(db_integration)
            
            # Run requested tests generically
            test_results = {}
            overall_success = True
            previous_status = db_integration.status
            
            for test_type in test_request.test_types:
                try:
                    if test_type == "connection":
                        result = await integration_impl.test_connection()
                    elif test_type == "authentication":
                        result = await integration_impl.test_authentication()
                    elif test_type == "permissions" or test_type == "project_access":
                        # Use provided test data or fall back to credentials
                        test_data = test_request.test_data or db_integration.get_credentials()
                        result = await integration_impl.test_permissions(test_data)
                    elif test_type == "create_ticket":
                        # Use provided test data or default credentials
                        test_data = test_request.test_data or db_integration.get_credentials()
                        result = await integration_impl.create_ticket(test_data, is_test=True)
                    else:
                        result = {"success": False, "message": f"Unknown test type: {test_type}"}
                    
                    test_results[test_type] = result
                    if not result.get("success", False):
                        overall_success = False
                        
                except Exception as e:
                    test_results[test_type] = {"success": False, "message": str(e)}
                    overall_success = False
            
            # Auto-activate if requested and all tests passed
            activation_triggered = False
            if overall_success and auto_activate_on_success and db_integration.status == IntegrationStatus.PENDING:
                db_integration.activate(method="automatic")
                activation_triggered = True
                
            # Update last tested time
            if hasattr(db_integration, 'last_health_check_at'):
                db_integration.last_health_check_at = datetime.now(timezone.utc)
                db_integration.health_check_status = "healthy" if overall_success else "unhealthy"
                db_integration.connection_test_count = (db_integration.connection_test_count or 0) + 1
                
            await db.commit()
            await integration_impl.close()
            
            return IntegrationTestResponse(
                test_type=", ".join(test_request.test_types),
                success=overall_success,
                response_time_ms=0,  # TODO: Track actual response time
                details=test_results,
                error_message=None if overall_success else "Some tests failed",
                suggestions=None,
                # Add new fields for auto-activation
                activation_triggered=activation_triggered,
                previous_status=previous_status.value if previous_status else None,
                new_status=db_integration.status.value if db_integration.status else None
            )
            
        except Exception as e:
            return IntegrationTestResponse(
                test_type=", ".join(test_request.test_types) if hasattr(test_request, 'test_types') else test_request.test_type,
                success=False,
                response_time_ms=0,
                details={},
                error_message=str(e),
                suggestions=None
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
        db_integration = await self.get_integration(db, integration_id, user_id)
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
                db_integration.platform_name,
                db_integration.get_credentials(),
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
        db_integration = await self.get_integration(db, integration_id, user_id)
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
        db_integration = await self.get_integration(db, integration_id, user_id)
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
        db_integration = await self.get_integration(db, integration_id, user_id)
        if not db_integration:
            return False
        
        # Check permissions
        # TODO: Add proper permission checking once user relationship is implemented
        # if db_integration.created_by != user_id:
        #     # TODO: Check if user is admin
        #     pass
        
        if hard_delete:
            await db.delete(db_integration)
        else:
            db_integration.soft_delete()
        
        await db.commit()
        return True
    
    def _validate_credentials(
        self,
        platform_name: str,
        configuration: Dict[str, Any]
    ) -> None:
        """Validate integration configuration based on platform"""
        required_fields = self._get_required_config_fields(platform_name)
        
        for field in required_fields:
            if field not in configuration:
                raise ValueError(f"Missing required configuration field: {field}")
    
    def _get_required_config_fields(self, platform_name: str) -> List[str]:
        """Get required configuration fields for platform"""
        field_map = {
            "salesforce": ["client_id", "client_secret", "instance_url"],
            # JIRA relies on top-level base_url and credentials containing email/api_token
            "jira": ["email", "api_token"],
            "servicenow": ["instance_url", "username", "password"],
            "zendesk": ["subdomain", "email", "api_token"],
            "github": ["token", "organization"],
            "slack": ["bot_token", "channel"],
            "teams": ["webhook_url"],
            "zoom": ["client_id", "client_secret"],
            "email": ["smtp_host", "smtp_port", "username", "password"],
            "webhook": ["url"]
        }
        
        return field_map.get(platform_name.lower(), [])
    
    def _get_integration_implementation(self, integration: Integration) -> IntegrationInterface:
        """
        Factory method to get integration implementation.
        
        Args:
            integration: Integration model instance
            
        Returns:
            IntegrationInterface implementation for the specific type
            
        Raises:
            ValueError: If integration type is not supported
        """
        if integration.platform_name == "jira":
            credentials = integration.get_credentials()
            return JiraIntegration(
                base_url=integration.base_url,
                email=credentials.get("email"),
                api_token=credentials.get("api_token")
            )
        # elif integration.integration_type == IntegrationType.SALESFORCE:
        #     credentials = integration.get_credentials()
        #     return SalesforceIntegration(
        #         instance_url=integration.base_url,
        #         client_id=credentials.get("client_id"),
        #         client_secret=credentials.get("client_secret")
        #     )
        else:
            raise ValueError(f"Unsupported integration type: {integration.platform_name}")
    
    async def _test_integration_by_type(
        self,
        platform_name: str,
        configuration: Dict[str, Any],
        test_type: str
    ) -> Dict[str, Any]:
        """Test integration based on type (DEPRECATED - use generic interface instead)"""
        if platform_name == "salesforce":
            return await self._test_salesforce(configuration, test_type)
        elif platform_name == "jira":
            return await self._test_jira(configuration, test_type)
        elif platform_name == "slack":
            return await self._test_slack(configuration, test_type)
        elif platform_name == "webhook":
            return await self._test_webhook(configuration, test_type)
        else:
            return {"message": f"Test not implemented for {platform_name}"}
    
    async def _sync_integration_by_type(
        self,
        platform_name: str,
        configuration: Dict[str, Any],
        sync_type: str,
        since_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Sync data based on integration type"""
        if platform_name == "salesforce":
            return await self._sync_salesforce(configuration, sync_type, since_timestamp)
        elif platform_name == "jira":
            return await self._sync_jira(configuration, sync_type, since_timestamp)
        elif platform_name == "slack":
            return await self._sync_slack(configuration, sync_type, since_timestamp)
        else:
            return {"message": f"Sync not implemented for {platform_name}"}
    
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
            
            start_time = time.time()
            response = await self.http_client.post(auth_url, data=auth_data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Debug log the request/response
            duration_ms = (time.time() - start_time) * 1000
            log_http_request_response_pair(
                method="POST",
                url=auth_url,
                response=response,
                data=auth_data,
                duration_ms=duration_ms
            )
            
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
        """Test Jira integration (deprecated path) via JiraIntegration using base_url"""
        try:
            base_url = config.get("base_url") or config.get("url")
            email = config["email"]
            api_token = config["api_token"]

            jira = JiraIntegration(base_url=base_url, email=email, api_token=api_token)
            try:
                if test_type in ("connection", "authentication"):
                    result = await jira.test_connection()
                    if result.get("success"):
                        details = result.get("details", {})
                        return {
                            "status": "connected",
                            "user": details.get("user"),
                            "base_url": base_url
                        }
                    else:
                        raise Exception(result.get("message", "Unknown error"))
                else:
                    # Fallback simple check
                    result = await jira.test_connection()
                    return {"status": "connected" if result.get("success") else "error"}
            finally:
                await jira.close()
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
            
            start_time = time.time()
            response = await self.http_client.post(url, headers=headers)
            response.raise_for_status()
            
            auth_data = response.json()
            
            # Debug log the request/response
            duration_ms = (time.time() - start_time) * 1000
            log_http_request_response_pair(
                method="POST",
                url=url,
                response=response,
                headers=headers,
                duration_ms=duration_ms
            )
            
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