#!/usr/bin/env python3
"""
Integration schemas for API validation and serialization
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.base import BaseCreate, BaseResponse, BaseSchema, BaseUpdate, URLStr


class IntegrationCategorySchema(str, Enum):
    """Integration category enum schema"""
    TICKETING = "ticketing"
    CRM = "crm"
    MESSAGING = "messaging"
    COMMUNICATION = "communication"
    PROJECT_MANAGEMENT = "project_management"
    CODE_REPOSITORY = "code_repository"
    WEBHOOK = "webhook"


class IntegrationStatusSchema(str, Enum):
    """Integration status enum schema"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ERROR = "error"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


# Request schemas
class IntegrationCreateRequest(BaseCreate):
    """Schema for creating a new integration"""
    name: str = Field(max_length=255, description="Display name for the integration")
    integration_category: IntegrationCategorySchema = Field(description="Functional category of integration")
    platform_name: str = Field(max_length=50, description="Platform name (jira, slack, etc.)")
    description: Optional[str] = Field(None, description="Integration description")
    enabled: bool = Field(default=True, description="Whether the integration is enabled")
    
    # Connection configuration
    base_url: Optional[URLStr] = Field(None, description="Base URL for API endpoints")
    api_version: Optional[str] = Field(None, max_length=20, description="API version")
    
    # Authentication
    auth_type: str = Field("api_key", description="Authentication type")
    credentials: Dict[str, Any] = Field(description="Authentication credentials")
    oauth_scopes: Optional[List[str]] = Field(None, description="OAuth scopes if applicable")
    
    # Configuration
    routing_rules: Optional[Dict[str, Any]] = Field(None, description="Routing rules")
    default_priority: int = Field(100, ge=1, le=1000, description="Routing priority")
    supports_categories: Optional[List[str]] = Field(None, description="Supported categories")
    supports_priorities: Optional[List[str]] = Field(None, description="Supported priorities")
    department_mapping: Optional[Dict[str, str]] = Field(None, description="Department mappings")
    custom_fields_mapping: Optional[Dict[str, str]] = Field(None, description="Custom field mappings")
    
    # Webhook configuration
    webhook_url: Optional[URLStr] = Field(None, description="Webhook URL")
    webhook_secret: Optional[str] = Field(None, description="Webhook secret")
    
    # Sync settings
    sync_enabled: bool = Field(False, description="Enable bidirectional sync")
    sync_frequency_minutes: int = Field(60, ge=1, le=1440, description="Sync frequency")
    
    # Rate limiting
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, description="Rate limit per hour")
    
    # Notification settings
    notification_events: Optional[List[str]] = Field(None, description="Events for notifications")
    notification_channels: Optional[Dict[str, Any]] = Field(None, description="Notification channels")
    
    # Environment
    environment: str = Field("production", description="Environment")
    region: Optional[str] = Field(None, description="Service region")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Integration name cannot be empty')
        return v.strip()
    
    @field_validator('auth_type')
    @classmethod
    def validate_auth_type(cls, v):
        valid_types = {"api_key", "oauth2", "basic", "bearer", "custom"}
        if v not in valid_types:
            raise ValueError(f'Auth type must be one of: {valid_types}')
        return v
    
    @model_validator(mode='after')
    def validate_credentials(self):
        auth_type = self.auth_type
        credentials = self.credentials
        platform_name = getattr(self, 'platform_name', None)
        
        if auth_type == "api_key":
            # Handle different integration types that use "api_key" auth differently
            if platform_name == "jira":
                # JIRA uses email + api_token for API key authentication
                if not all(k in credentials for k in ["email", "api_token"]):
                    raise ValueError('Email and API token required for JIRA api_key authentication')
            else:
                # Standard API key authentication
                if "api_key" not in credentials:
                    raise ValueError('API key required for api_key authentication')
        elif auth_type == "oauth2" and not all(k in credentials for k in ["client_id", "client_secret"]):
            raise ValueError('Client ID and secret required for OAuth2')
        elif auth_type == "basic" and not all(k in credentials for k in ["username", "password"]):
            raise ValueError('Username and password required for basic auth')
        elif auth_type == "bearer" and "token" not in credentials:
            raise ValueError('Token required for bearer authentication')
        
        return self


class IntegrationUpdateRequest(BaseUpdate):
    """Schema for updating an integration"""
    name: Optional[str] = Field(None, max_length=255, description="Integration name")
    description: Optional[str] = Field(None, description="Description")
    enabled: Optional[bool] = Field(None, description="Whether the integration is enabled")
    base_url: Optional[URLStr] = Field(None, description="Base URL")
    api_version: Optional[str] = Field(None, max_length=20, description="API version")
    credentials: Optional[Dict[str, Any]] = Field(None, description="Authentication credentials")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Integration-specific configuration values")
    oauth_scopes: Optional[List[str]] = Field(None, description="OAuth scopes")
    routing_rules: Optional[Dict[str, Any]] = Field(None, description="Routing rules")
    default_priority: Optional[int] = Field(None, ge=1, le=1000, description="Default priority")
    supports_categories: Optional[List[str]] = Field(None, description="Supported categories")
    supports_priorities: Optional[List[str]] = Field(None, description="Supported priorities")
    department_mapping: Optional[Dict[str, str]] = Field(None, description="Department mappings")
    custom_fields_mapping: Optional[Dict[str, str]] = Field(None, description="Field mappings")
    webhook_url: Optional[URLStr] = Field(None, description="Webhook URL")
    webhook_secret: Optional[str] = Field(None, description="Webhook secret")
    sync_enabled: Optional[bool] = Field(None, description="Sync enabled")
    sync_frequency_minutes: Optional[int] = Field(None, ge=1, le=1440, description="Sync frequency")
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, description="Rate limit")
    notification_events: Optional[List[str]] = Field(None, description="Notification events")
    notification_channels: Optional[Dict[str, Any]] = Field(None, description="Notification channels")
    environment: Optional[str] = Field(None, description="Environment")
    region: Optional[str] = Field(None, description="Region")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Integration name cannot be empty')
        return v.strip() if v else None


class IntegrationStatusUpdateRequest(BaseSchema):
    """Schema for updating integration status"""
    enabled: Optional[bool] = Field(None, description="Whether integration is enabled")
    reason: Optional[str] = Field(None, description="Reason for status change")


class IntegrationTestRequest(BaseSchema):
    """Schema for testing integration connection"""
    test_types: List[str] = Field(
        default=["connection", "authentication"],
        description="Types of tests to perform"
    )
    test_data: Optional[Dict[str, Any]] = Field(None, description="Test data to use")
    auto_activate_on_success: bool = Field(
        True, 
        description="Automatically activate integration if all tests pass"
    )
    
    @field_validator('test_types')
    @classmethod
    def validate_test_types(cls, v):
        valid_types = {"connection", "authentication", "create_ticket", "search", "webhook", "project_access"}
        if not all(t in valid_types for t in v):
            raise ValueError(f'Invalid test types. Must be one of: {valid_types}')
        return v


class IntegrationSyncRequest(BaseSchema):
    """Schema for manual sync request"""
    sync_type: str = Field(description="Type of sync", pattern="^(full|incremental|test)$")
    direction: str = Field("bidirectional", description="Sync direction", pattern="^(inbound|outbound|bidirectional)$")
    dry_run: bool = Field(False, description="Perform dry run without changes")
    filters: Optional[Dict[str, Any]] = Field(None, description="Sync filters")


class IntegrationRoutingTestRequest(BaseSchema):
    """Schema for testing routing rules"""
    ticket_data: Dict[str, Any] = Field(description="Sample ticket data for routing test")
    routing_rules: Optional[Dict[str, Any]] = Field(None, description="Routing rules to test")


# Response schemas
class IntegrationHealthInfo(BaseSchema):
    """Integration health information"""
    status: str = Field(description="Health status")
    last_check: Optional[datetime] = Field(None, description="Last health check")
    response_time_ms: Optional[int] = Field(None, description="Response time")
    error_message: Optional[str] = Field(None, description="Error if unhealthy")


class IntegrationUsageStats(BaseSchema):
    """Integration usage statistics"""
    total_requests: int = Field(description="Total requests made")
    successful_requests: int = Field(description="Successful requests")
    failed_requests: int = Field(description="Failed requests")
    success_rate: float = Field(description="Success rate percentage")
    avg_response_time_ms: Optional[int] = Field(None, description="Average response time")
    last_request_at: Optional[datetime] = Field(None, description="Last request timestamp")
    last_success_at: Optional[datetime] = Field(None, description="Last success timestamp")
    last_error_at: Optional[datetime] = Field(None, description="Last error timestamp")


class IntegrationBaseResponse(BaseResponse):
    """Base integration response with common fields"""
    name: str = Field(description="Integration name")
    integration_category: IntegrationCategorySchema = Field(description="Integration category")
    platform_name: str = Field(description="Platform name")
    status: IntegrationStatusSchema = Field(description="Current status")
    enabled: bool = Field(description="Whether integration is enabled")
    description: Optional[str] = Field(None, description="Description")
    environment: str = Field(description="Environment")
    is_healthy: bool = Field(description="Health status")


class IntegrationListResponse(IntegrationBaseResponse):
    """Integration information for list views"""
    base_url: Optional[str] = Field(None, description="Base URL")
    auth_type: str = Field(description="Authentication type")
    default_priority: int = Field(description="Default routing priority")
    sync_enabled: bool = Field(description="Sync enabled")
    last_health_check_at: Optional[datetime] = Field(None, description="Last health check")
    health_check_status: Optional[str] = Field(None, description="Health check result")
    total_requests: int = Field(description="Total requests")
    success_rate: float = Field(description="Success rate")
    is_rate_limited: bool = Field(description="Whether currently rate limited")
    in_maintenance_window: bool = Field(description="Whether in maintenance window")


class IntegrationDetailResponse(IntegrationBaseResponse):
    """Detailed integration information"""
    base_url: Optional[str] = Field(None, description="Base URL")
    api_version: Optional[str] = Field(None, description="API version")
    auth_type: str = Field(description="Authentication type")
    oauth_scopes: Optional[List[str]] = Field(None, description="OAuth scopes")
    
    # Health and monitoring
    health_info: IntegrationHealthInfo = Field(description="Health information")
    usage_stats: IntegrationUsageStats = Field(description="Usage statistics")
    
    # Configuration
    default_priority: int = Field(description="Default priority")
    supports_categories: Optional[List[str]] = Field(None, description="Supported categories")
    supports_priorities: Optional[List[str]] = Field(None, description="Supported priorities")
    department_mapping: Optional[Dict[str, str]] = Field(None, description="Department mapping")
    custom_fields_mapping: Optional[Dict[str, str]] = Field(None, description="Field mapping")
    routing_rules: Optional[Dict[str, Any]] = Field(None, description="Routing rules")
    
    # Sync settings
    sync_enabled: bool = Field(description="Sync enabled")
    sync_frequency_minutes: int = Field(description="Sync frequency")
    last_sync_at: Optional[datetime] = Field(None, description="Last sync timestamp")
    
    # Webhook settings
    webhook_url: Optional[str] = Field(None, description="Webhook URL")
    
    # Rate limiting
    rate_limit_per_hour: Optional[int] = Field(None, description="Rate limit")
    current_hour_requests: int = Field(description="Current hour requests")
    rate_limit_reset_at: Optional[datetime] = Field(None, description="Rate limit reset time")
    
    # Notifications
    notification_events: Optional[List[str]] = Field(None, description="Notification events")
    notification_channels: Optional[Dict[str, Any]] = Field(None, description="Notification channels")
    
    # Maintenance
    maintenance_window_start: Optional[str] = Field(None, description="Maintenance start time")
    maintenance_window_end: Optional[str] = Field(None, description="Maintenance end time")
    auto_disable_on_error: bool = Field(description="Auto-disable on error")
    failure_threshold: int = Field(description="Failure threshold")
    consecutive_failures: int = Field(description="Consecutive failures")
    
    # Lifecycle
    expires_at: Optional[datetime] = Field(None, description="Credential expiration")
    region: Optional[str] = Field(None, description="Service region")
    
    # Computed properties
    is_rate_limited: bool = Field(description="Currently rate limited")
    is_expired: bool = Field(description="Credentials expired")
    in_maintenance_window: bool = Field(description="In maintenance window")


class IntegrationConfigResponse(BaseSchema):
    """Integration configuration response (no credentials)"""
    integration_category: IntegrationCategorySchema = Field(description="Integration category")
    platform_name: str = Field(description="Platform name")
    auth_type: str = Field(description="Authentication type")
    required_credentials: List[str] = Field(description="Required credential fields")
    optional_credentials: List[str] = Field(description="Optional credential fields")
    supported_features: List[str] = Field(description="Supported features")
    webhook_support: bool = Field(description="Webhook support")
    sync_support: bool = Field(description="Sync support")
    rate_limits: Optional[Dict[str, int]] = Field(None, description="Rate limit information")
    documentation_url: Optional[str] = Field(None, description="Documentation URL")


class IntegrationTestResponse(BaseSchema):
    """Integration test response"""
    test_type: str = Field(description="Type of test performed")
    success: bool = Field(description="Test success")
    response_time_ms: int = Field(description="Response time")
    details: Dict[str, Any] = Field(description="Test details")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    suggestions: Optional[List[str]] = Field(None, description="Suggestions for fixing issues")
    activation_triggered: Optional[bool] = Field(None, description="Whether integration was auto-activated")
    previous_status: Optional[str] = Field(None, description="Status before test")
    new_status: Optional[str] = Field(None, description="Status after test")


class IntegrationSyncResponse(BaseSchema):
    """Integration sync response"""
    sync_id: str = Field(description="Sync operation ID")
    sync_type: str = Field(description="Sync type")
    direction: str = Field(description="Sync direction")
    started_at: datetime = Field(description="Sync start time")
    completed_at: Optional[datetime] = Field(None, description="Sync completion time")
    status: str = Field(description="Sync status")
    records_processed: int = Field(description="Records processed")
    records_created: int = Field(description="Records created")
    records_updated: int = Field(description="Records updated")
    records_failed: int = Field(description="Records failed")
    errors: List[Dict[str, Any]] = Field(default=[], description="Sync errors")
    dry_run: bool = Field(description="Whether this was a dry run")


class IntegrationRoutingTestResponse(BaseSchema):
    """Integration routing test response"""
    integration_id: UUID = Field(description="Integration ID")
    integration_name: str = Field(description="Integration name")
    can_handle: bool = Field(description="Whether integration can handle ticket")
    routing_priority: int = Field(description="Calculated routing priority")
    routing_reason: str = Field(description="Reason for routing decision")
    field_mappings: Dict[str, Any] = Field(description="Field mappings that would be applied")
    estimated_processing_time: Optional[int] = Field(None, description="Estimated processing time")


class IntegrationStatsResponse(BaseSchema):
    """Integration statistics response"""
    total_integrations: int = Field(description="Total number of integrations")
    active_integrations: int = Field(description="Active integrations")
    healthy_integrations: int = Field(description="Healthy integrations")
    failed_integrations: int = Field(description="Failed integrations")
    type_distribution: Dict[str, int] = Field(description="Integrations by type")
    status_distribution: Dict[str, int] = Field(description="Integrations by status")
    total_requests_today: int = Field(description="Total requests today")
    success_rate_today: float = Field(description="Overall success rate today")
    avg_response_time_ms: Optional[float] = Field(None, description="Average response time")


# Search and filter schemas
class IntegrationSearchParams(BaseSchema):
    """Integration search parameters"""
    q: Optional[str] = Field(None, description="Search query (name, description)")
    integration_category: Optional[List[IntegrationCategorySchema]] = Field(None, description="Filter by category")
    platform_name: Optional[str] = Field(None, description="Filter by platform name")
    status: Optional[List[IntegrationStatusSchema]] = Field(None, description="Filter by status")
    environment: Optional[str] = Field(None, description="Filter by environment")
    auth_type: Optional[str] = Field(None, description="Filter by auth type")
    enabled: Optional[bool] = Field(None, description="Filter by enabled status")
    sync_enabled: Optional[bool] = Field(None, description="Filter by sync enabled")
    created_after: Optional[datetime] = Field(None, description="Created after date")
    created_before: Optional[datetime] = Field(None, description="Created before date")
    last_success_after: Optional[datetime] = Field(None, description="Last success after date")
    last_error_after: Optional[datetime] = Field(None, description="Last error after date")
    supports_category: Optional[str] = Field(None, description="Supports specific category")
    region: Optional[str] = Field(None, description="Filter by region")


class IntegrationSortParams(BaseSchema):
    """Integration sorting parameters"""
    sort_by: str = Field(
        "created_at",
        description="Sort field",
        pattern="^(created_at|updated_at|name|status|success_rate|last_request_at|total_requests)$"
    )
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


# Bulk operation schemas
class IntegrationBulkStatusUpdateRequest(BaseSchema):
    """Schema for bulk status updates"""
    integration_ids: List[UUID] = Field(description="List of integration IDs")
    status: IntegrationStatusSchema = Field(description="New status")
    reason: Optional[str] = Field(None, description="Reason for status change")


class IntegrationBulkTestRequest(BaseSchema):
    """Schema for bulk testing"""
    integration_ids: List[UUID] = Field(description="List of integration IDs to test")
    test_types: List[str] = Field(description="Types of tests to perform")
    
    @field_validator('integration_ids')
    @classmethod
    def validate_integration_ids(cls, v):
        if len(v) > 20:  # Limit bulk operations
            raise ValueError('Cannot test more than 20 integrations at once')
        return v


class IntegrationBulkSyncRequest(BaseSchema):
    """Schema for bulk sync operations"""
    integration_ids: List[UUID] = Field(description="List of integration IDs")
    sync_type: str = Field(description="Sync type", pattern="^(full|incremental)$")
    direction: str = Field("bidirectional", description="Sync direction")
    dry_run: bool = Field(False, description="Perform dry run")


# Webhook schemas
class IntegrationWebhookEvent(BaseSchema):
    """Schema for webhook events"""
    event_type: str = Field(description="Type of event")
    integration_id: UUID = Field(description="Integration ID")
    timestamp: datetime = Field(description="Event timestamp")
    data: Dict[str, Any] = Field(description="Event data")
    signature: Optional[str] = Field(None, description="Webhook signature")


class IntegrationWebhookResponse(BaseSchema):
    """Schema for webhook responses"""
    success: bool = Field(description="Processing success")
    message: str = Field(description="Response message")
    processed_events: int = Field(description="Number of events processed")
    errors: List[str] = Field(default=[], description="Processing errors")


# Error schemas
class IntegrationErrorResponse(BaseSchema):
    """Integration-specific error response"""
    integration_id: Optional[UUID] = Field(None, description="Integration ID if applicable")
    error_code: str = Field(description="Error code")
    error_message: str = Field(description="Error message")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")
    health_impact: Optional[str] = Field(None, description="Impact on integration health")
    suggested_actions: Optional[List[str]] = Field(None, description="Suggested remediation actions")