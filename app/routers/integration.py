#!/usr/bin/env python3
"""
Integration API Routes for AI Ticket Creator Backend
Handles CRUD operations, testing, and synchronization of third-party integrations
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db_session
from ..models.user import User
from ..models.integration import IntegrationCategory, IntegrationStatus
from ..schemas.integration import (
    IntegrationCreateRequest,
    IntegrationUpdateRequest,
    IntegrationDetailResponse,
    IntegrationListResponse,
    IntegrationTestRequest,
    IntegrationTestResponse,
    IntegrationSyncRequest,
    IntegrationSyncResponse,
    IntegrationStatusUpdateRequest,
    IntegrationSearchParams,
    IntegrationSortParams
)
from ..middleware.auth_middleware import get_current_user
from ..services.integration_service import IntegrationService
from ..services.jira_integration import JiraIntegration

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Integrations"])
integration_service = IntegrationService()


@router.post("/", response_model=IntegrationDetailResponse)
async def create_integration(
    integration_data: IntegrationCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new integration"""
    try:
        # Create integration using service
        db_integration = await integration_service.create_integration(
            db=db,
            integration_request=integration_data,
            user_id=current_user.id
        )
        
        logger.info(f"✅ Integration created: {db_integration.name} ({db_integration.platform_name})")
        
        # Convert to dict and create proper response
        integration_dict = db_integration.to_dict(include_credentials=False, include_stats=True)
        
        # Create health info - defaulting for new integrations
        from ..schemas.integration import IntegrationHealthInfo, IntegrationUsageStats
        health_info = IntegrationHealthInfo(
            status="unknown",
            last_check=None,
            response_time_ms=None,
            error_message=None
        )
        
        usage_stats = IntegrationUsageStats(
            total_requests=db_integration.total_requests or 0,
            successful_requests=db_integration.successful_requests or 0,
            failed_requests=db_integration.failed_requests or 0,
            success_rate=db_integration.success_rate,
            avg_response_time_ms=None,
            last_request_at=db_integration.last_request_at,
            last_success_at=db_integration.last_success_at,
            last_error_at=db_integration.last_error_at
        )
        
        return IntegrationDetailResponse(
            id=db_integration.id,
            name=db_integration.name,
            integration_category=db_integration.integration_category,
            platform_name=db_integration.platform_name,
            status=db_integration.status,
            enabled=db_integration.enabled,
            description=db_integration.description,
            environment=db_integration.environment or "production",
            is_healthy=db_integration.is_healthy,
            base_url=db_integration.base_url,
            api_version=db_integration.api_version,
            auth_type=db_integration.auth_type,
            oauth_scopes=db_integration.oauth_scopes,
            health_info=health_info,
            usage_stats=usage_stats,
            default_priority=db_integration.default_priority or 100,
            supports_categories=db_integration.supports_categories,
            supports_priorities=db_integration.supports_priorities,
            department_mapping=db_integration.department_mapping,
            custom_fields_mapping=db_integration.custom_fields_mapping,
            routing_rules=db_integration.routing_rules,
            sync_enabled=db_integration.sync_enabled or False,
            sync_frequency_minutes=db_integration.sync_frequency_minutes or 60,
            last_sync_at=db_integration.last_sync_at,
            webhook_url=db_integration.webhook_url,
            rate_limit_per_hour=db_integration.rate_limit_per_hour,
            current_hour_requests=db_integration.current_hour_requests or 0,
            rate_limit_reset_at=db_integration.rate_limit_reset_at,
            notification_events=db_integration.notification_events,
            notification_channels=db_integration.notification_channels,
            maintenance_window_start=db_integration.maintenance_window_start,
            maintenance_window_end=db_integration.maintenance_window_end,
            auto_disable_on_error=db_integration.auto_disable_on_error or False,
            failure_threshold=db_integration.failure_threshold or 5,
            consecutive_failures=db_integration.consecutive_failures or 0,
            expires_at=db_integration.expires_at,
            region=db_integration.region,
            is_rate_limited=db_integration.is_rate_limited,
            is_expired=db_integration.is_expired,
            in_maintenance_window=db_integration.in_maintenance_window,
            created_at=db_integration.created_at,
            updated_at=db_integration.updated_at
        )
        
    except ValueError as e:
        logger.error(f"❌ Integration creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"❌ Integration creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create integration"
        )


@router.get("/", response_model=List[IntegrationListResponse])
async def list_integrations(
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    integration_category: Optional[IntegrationCategory] = Query(None, description="Filter by integration category"),
    integration_status: Optional[IntegrationStatus] = Query(None, description="Filter by status"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    name: Optional[str] = Query(None, description="Filter by name (partial match)"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """List integrations for current user's organization"""
    try:
        # Build search and sort parameters
        search_params = None
        if any([integration_category, integration_status, enabled is not None, name]):
            search_params = IntegrationSearchParams(
                integration_category=[integration_category] if integration_category else None,
                status=[integration_status] if integration_status else None,
                enabled=enabled,
                q=name  # 'name' should be 'q' according to schema
            )
        
        sort_params = IntegrationSortParams(
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Get integrations using service
        integrations, total_count = await integration_service.list_integrations(
            db=db,
            user_id=current_user.id,
            offset=offset,
            limit=limit,
            search_params=search_params,
            sort_params=sort_params
        )
        
        logger.info(f"📋 Listed {len(integrations)}/{total_count} integrations for org {current_user.organization_id}")
        
        # Convert to response format (without sensitive data)
        return [
            IntegrationListResponse(
                id=integration.id,
                name=integration.name,
                integration_category=integration.integration_category,
                platform_name=integration.platform_name,
                status=integration.status,
                enabled=integration.enabled,
                description=integration.description,
                environment=integration.environment or "production",
                is_healthy=integration.is_healthy,
                base_url=integration.base_url,
                auth_type=integration.auth_type,
                default_priority=integration.default_priority or 100,
                sync_enabled=integration.sync_enabled or False,
                last_health_check_at=integration.last_health_check_at,
                health_check_status=integration.health_check_status,
                total_requests=integration.total_requests or 0,
                success_rate=integration.success_rate,
                is_rate_limited=integration.is_rate_limited,
                in_maintenance_window=integration.in_maintenance_window,
                created_at=integration.created_at,
                updated_at=integration.updated_at
            )
            for integration in integrations
        ]
        
    except Exception as e:
        logger.error(f"❌ Integration listing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list integrations"
        )


@router.get("/{integration_id}", response_model=IntegrationDetailResponse)
async def get_integration(
    integration_id: UUID,
    include_stats: bool = Query(False, description="Include usage statistics"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get integration details by ID"""
    try:
        # Get integration using service (with organization filtering)
        db_integration = await integration_service.get_integration(
            db=db,
            integration_id=integration_id,
            user_id=current_user.id,
            include_stats=include_stats
        )
        
        if not db_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        logger.info(f"📄 Retrieved integration: {db_integration.name}")
        
        # Note: Configuration contains sensitive data, so we don't include actual credentials in GET responses
        
        # Create health info and usage stats for response
        from ..schemas.integration import IntegrationHealthInfo, IntegrationUsageStats
        health_info = IntegrationHealthInfo(
            status=db_integration.health_check_status or "unknown",
            last_check=db_integration.last_health_check_at,
            response_time_ms=None,
            error_message=db_integration.health_check_error
        )
        
        usage_stats = IntegrationUsageStats(
            total_requests=db_integration.total_requests or 0,
            successful_requests=db_integration.successful_requests or 0,
            failed_requests=db_integration.failed_requests or 0,
            success_rate=db_integration.success_rate,
            avg_response_time_ms=None,
            last_request_at=db_integration.last_request_at,
            last_success_at=db_integration.last_success_at,
            last_error_at=db_integration.last_error_at
        )
        
        return IntegrationDetailResponse(
            id=db_integration.id,
            name=db_integration.name,
            integration_category=db_integration.integration_category,
            platform_name=db_integration.platform_name,
            status=db_integration.status,
            enabled=db_integration.enabled,
            description=db_integration.description,
            environment=db_integration.environment or "production",
            is_healthy=db_integration.is_healthy,
            base_url=db_integration.base_url,
            api_version=db_integration.api_version,
            auth_type=db_integration.auth_type,
            oauth_scopes=db_integration.oauth_scopes,
            health_info=health_info,
            usage_stats=usage_stats,
            default_priority=db_integration.default_priority or 100,
            supports_categories=db_integration.supports_categories,
            supports_priorities=db_integration.supports_priorities,
            department_mapping=db_integration.department_mapping,
            custom_fields_mapping=db_integration.custom_fields_mapping,
            routing_rules=db_integration.routing_rules,
            sync_enabled=db_integration.sync_enabled or False,
            sync_frequency_minutes=db_integration.sync_frequency_minutes or 60,
            last_sync_at=db_integration.last_sync_at,
            webhook_url=db_integration.webhook_url,
            rate_limit_per_hour=db_integration.rate_limit_per_hour,
            current_hour_requests=db_integration.current_hour_requests or 0,
            rate_limit_reset_at=db_integration.rate_limit_reset_at,
            notification_events=db_integration.notification_events,
            notification_channels=db_integration.notification_channels,
            maintenance_window_start=db_integration.maintenance_window_start,
            maintenance_window_end=db_integration.maintenance_window_end,
            auto_disable_on_error=db_integration.auto_disable_on_error or False,
            failure_threshold=db_integration.failure_threshold or 5,
            consecutive_failures=db_integration.consecutive_failures or 0,
            expires_at=db_integration.expires_at,
            region=db_integration.region,
            is_rate_limited=db_integration.is_rate_limited,
            is_expired=db_integration.is_expired,
            in_maintenance_window=db_integration.in_maintenance_window,
            created_at=db_integration.created_at,
            updated_at=db_integration.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Integration retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve integration"
        )


@router.put("/{integration_id}", response_model=IntegrationDetailResponse)
async def update_integration(
    integration_id: UUID,
    update_data: IntegrationUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Update an existing integration"""
    try:
        # Get integration using service (with organization filtering)
        db_integration = await integration_service.get_integration(
            db=db,
            integration_id=integration_id,
            user_id=current_user.id
        )
        
        if not db_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        # Update integration using service
        updated_integration = await integration_service.update_integration(
            db=db,
            integration_id=integration_id,
            update_request=update_data,
            user_id=current_user.id
        )
        
        logger.info(f"✏️ Integration updated: {updated_integration.name}")
        
        return IntegrationDetailResponse(
            id=updated_integration.id,
            name=updated_integration.name,
            integration_category=updated_integration.integration_category,
            platform_name=updated_integration.platform_name,
            status=updated_integration.status,
            enabled=updated_integration.enabled,
            description=updated_integration.description,
            configuration={},  # Security: Don't return credentials
            webhook_url=updated_integration.webhook_url,
            sync_frequency_minutes=updated_integration.sync_frequency_minutes,
            last_sync_at=updated_integration.last_sync_at,
            routing_rules=updated_integration.routing_rules,
            field_mappings=updated_integration.custom_fields_mapping,
            metadata=updated_integration.metadata,
            created_at=updated_integration.created_at,
            updated_at=updated_integration.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Integration update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update integration"
        )


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Soft delete an integration"""
    try:
        # Get integration using service (with organization filtering)
        db_integration = await integration_service.get_integration(
            db=db,
            integration_id=integration_id,
            user_id=current_user.id
        )
        
        if not db_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        # Delete integration using service
        await integration_service.delete_integration(
            db=db,
            integration_id=integration_id,
            user_id=current_user.id
        )
        
        logger.info(f"🗑️ Integration deleted: {db_integration.name}")
        
        return {"message": "Integration deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Integration deletion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete integration"
        )


@router.post("/{integration_id}/test", response_model=IntegrationTestResponse)
async def test_integration(
    integration_id: UUID,
    test_request: IntegrationTestRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Test integration connection and functionality"""
    try:
        # Get integration using service (with organization filtering)
        db_integration = await integration_service.get_integration(
            db=db,
            integration_id=integration_id,
            user_id=current_user.id
        )
        
        if not db_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        # Test integration using generic interface
        test_result = await integration_service.test_integration(
            db=db,
            integration_id=integration_id,
            test_request=test_request,
            user_id=current_user.id,
            auto_activate_on_success=test_request.auto_activate_on_success
        )
        
        if not test_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to test integration"
            )
        
        logger.info(f"🧪 Integration test: {'✅ Success' if test_result.success else '❌ Failed'}")
        
        return test_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Integration test error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test integration"
        )


@router.post("/{integration_id}/sync", response_model=IntegrationSyncResponse) 
async def sync_integration(
    integration_id: UUID,
    sync_request: IntegrationSyncRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger integration synchronization"""
    try:
        # Get integration using service (with organization filtering)
        db_integration = await integration_service.get_integration(
            db=db,
            integration_id=integration_id,
            user_id=current_user.id
        )
        
        if not db_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        # Trigger sync using service
        sync_result = await integration_service.sync_integration(
            db=db,
            integration_id=integration_id,
            sync_request=sync_request,
            user_id=current_user.id
        )
        
        logger.info(f"🔄 Integration sync triggered: {db_integration.name}")
        
        return sync_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Integration sync error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync integration"
        )


@router.patch("/{integration_id}/status", response_model=IntegrationDetailResponse)
async def update_integration_status(
    integration_id: UUID,
    status_update: IntegrationStatusUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Update integration status (enable/disable)"""
    try:
        # Get integration using service (with organization filtering)
        db_integration = await integration_service.get_integration(
            db=db,
            integration_id=integration_id,
            user_id=current_user.id
        )
        
        if not db_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        # Update status using service
        updated_integration = await integration_service.update_integration_status(
            db=db,
            integration_id=integration_id,
            status_update=status_update,
            user_id=current_user.id
        )
        
        logger.info(f"📊 Integration status updated: {updated_integration.name} -> enabled={status_update.enabled if hasattr(status_update, 'enabled') else 'unchanged'}")
        
        # Create health info and usage stats for response
        from ..schemas.integration import IntegrationHealthInfo, IntegrationUsageStats
        health_info = IntegrationHealthInfo(
            status=updated_integration.health_check_status or "unknown",
            last_check=updated_integration.last_health_check_at,
            response_time_ms=None,
            error_message=updated_integration.health_check_error
        )
        
        usage_stats = IntegrationUsageStats(
            total_requests=updated_integration.total_requests or 0,
            successful_requests=updated_integration.successful_requests or 0,
            failed_requests=updated_integration.failed_requests or 0,
            success_rate=updated_integration.success_rate,
            avg_response_time_ms=None,
            last_request_at=updated_integration.last_request_at,
            last_success_at=updated_integration.last_success_at,
            last_error_at=updated_integration.last_error_at
        )
        
        return IntegrationDetailResponse(
            id=updated_integration.id,
            name=updated_integration.name,
            integration_category=updated_integration.integration_category,
            platform_name=updated_integration.platform_name,
            status=updated_integration.status,
            enabled=updated_integration.enabled,
            description=updated_integration.description,
            environment=updated_integration.environment or "production",
            is_healthy=updated_integration.is_healthy,
            base_url=updated_integration.base_url,
            api_version=updated_integration.api_version,
            auth_type=updated_integration.auth_type,
            oauth_scopes=updated_integration.oauth_scopes,
            health_info=health_info,
            usage_stats=usage_stats,
            default_priority=updated_integration.default_priority or 100,
            supports_categories=updated_integration.supports_categories,
            supports_priorities=updated_integration.supports_priorities,
            department_mapping=updated_integration.department_mapping,
            custom_fields_mapping=updated_integration.custom_fields_mapping,
            routing_rules=updated_integration.routing_rules,
            sync_enabled=updated_integration.sync_enabled or False,
            sync_frequency_minutes=updated_integration.sync_frequency_minutes or 60,
            last_sync_at=updated_integration.last_sync_at,
            webhook_url=updated_integration.webhook_url,
            rate_limit_per_hour=updated_integration.rate_limit_per_hour,
            current_hour_requests=updated_integration.current_hour_requests or 0,
            rate_limit_reset_at=updated_integration.rate_limit_reset_at,
            notification_events=updated_integration.notification_events,
            notification_channels=updated_integration.notification_channels,
            maintenance_window_start=updated_integration.maintenance_window_start,
            maintenance_window_end=updated_integration.maintenance_window_end,
            auto_disable_on_error=updated_integration.auto_disable_on_error or False,
            failure_threshold=updated_integration.failure_threshold or 5,
            consecutive_failures=updated_integration.consecutive_failures or 0,
            expires_at=updated_integration.expires_at,
            region=updated_integration.region,
            is_rate_limited=updated_integration.is_rate_limited,
            is_expired=updated_integration.is_expired,
            in_maintenance_window=updated_integration.in_maintenance_window,
            created_at=updated_integration.created_at,
            updated_at=updated_integration.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Integration status update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update integration status"
        )


@router.get("/active", response_model=List[Dict[str, Any]])
async def get_active_integrations(
    supports_category: Optional[str] = Query(None, description="Filter by category support"),
    integration_category: Optional[IntegrationCategory] = Query(None, description="Filter by integration category"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get list of active integrations available for ticket creation"""
    try:
        # Get active integrations for the user's organization
        from sqlalchemy import and_
        from ..models.integration import Integration, IntegrationStatus
        
        # Build query for active integrations
        filters = [
            Integration.status == IntegrationStatus.ACTIVE,
            Integration.is_deleted == False,
            Integration.organization_id == current_user.organization_id
        ]
        
        if integration_category:
            filters.append(Integration.integration_category == integration_category)
        
        if supports_category:
            # Filter by supported categories
            filters.append(Integration.supports_categories.contains([supports_category]))
        
        query = select(Integration).where(and_(*filters)).order_by(Integration.name)
        
        result = await db.execute(query)
        integrations = result.scalars().all()
        
        logger.info(f"📋 Found {len(integrations)} active integrations for org {current_user.organization_id}")
        
        # Format response
        active_integrations = []
        for integration in integrations:
            active_integrations.append({
                "id": str(integration.id),
                "name": integration.name,
                "integration_category": integration.integration_category.value,
                "platform_name": integration.platform_name,
                "status": "active",
                "description": integration.description,
                "supports_categories": integration.supports_categories or [],
                "supports_priorities": integration.supports_priorities or [],
                "default_priority": integration.default_priority or 100,
                "health_status": "healthy" if integration.is_healthy else "error",
                "success_rate": round(integration.success_rate, 2),
                "last_successful_creation": integration.last_success_at
            })
        
        return active_integrations
        
    except Exception as e:
        logger.error(f"❌ Active integrations retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active integrations"
        )


@router.post("/{integration_id}/activate")
async def activate_integration(
    integration_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Manually activate an integration that has passed tests"""
    try:
        # Get integration using service (with organization filtering)
        db_integration = await integration_service.get_integration(
            db=db,
            integration_id=integration_id,
            user_id=current_user.id
        )
        
        if not db_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        # Only allow activation if integration is in PENDING status and healthy
        if db_integration.status != IntegrationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Integration status is {db_integration.status.value}, can only activate PENDING integrations"
            )
        
        # Activate the integration
        db_integration.activate(method="manual")
        await db.commit()
        
        logger.info(f"🟢 Integration manually activated: {db_integration.name}")
        
        return {
            "message": "Integration activated successfully",
            "integration_id": str(integration_id),
            "integration_name": db_integration.name,
            "previous_status": "pending",
            "new_status": "active",
            "activation_method": "manual"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Integration activation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate integration"
        )


@router.get("/{integration_id}/fields")
async def get_integration_fields(
    integration_id: UUID,
    field_type: Optional[str] = Query(None, description="Filter by field type (custom, system)"),
    search: Optional[str] = Query(None, description="Search field names"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get available fields for an integration (useful for discovering custom field IDs)"""
    try:
        # Get integration using service (with organization filtering)
        db_integration = await integration_service.get_integration(
            db=db,
            integration_id=integration_id,
            user_id=current_user.id
        )
        
        if not db_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        # Currently only supports JIRA
        if db_integration.platform_name != "jira":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Field discovery not supported for {db_integration.platform_name} integrations"
            )
        
        # Get JIRA credentials and initialize service
        credentials = db_integration.get_credentials()
        async with JiraIntegration(
            base_url=db_integration.base_url,
            email=credentials.get("email"),
            api_token=credentials.get("api_token")
        ) as jira_service:
            
            if field_type == "custom":
                fields = await jira_service.get_custom_fields()
            else:
                fields = await jira_service.get_all_fields()
            
            # Apply search filter if provided
            if search:
                fields = [f for f in fields if search.lower() in f["name"].lower()]
            
            # Apply field type filter
            if field_type == "custom":
                fields = [f for f in fields if f.get("custom", False)]
            elif field_type == "system":
                fields = [f for f in fields if not f.get("custom", False)]
            
            logger.info(f"📋 Retrieved {len(fields)} fields for {db_integration.name}")
            
            return {
                "integration_name": db_integration.name,
                "integration_category": db_integration.integration_category.value,
                "platform_name": db_integration.platform_name,
                "total_fields": len(fields),
                "fields": fields
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Field discovery error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to discover integration fields"
        )