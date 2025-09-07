#!/usr/bin/env python3
"""
AI Configuration schemas for API validation and serialization
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import Field, field_validator, model_validator
from enum import Enum

from app.schemas.base import BaseSchema, BaseCreate, BaseUpdate, BaseResponse


class AIAgentTypeSchema(str, Enum):
    """AI agent type enum schema"""
    CUSTOMER_SUPPORT = "customer_support_agent"
    CATEGORIZATION = "categorization_agent"
    FILE_ANALYSIS = "file_analysis_agent"
    TITLE_GENERATION = "title_generation"
    SENTIMENT_ANALYSIS = "sentiment_analysis_agent"
    ROUTING = "routing_agent"
    ESCALATION = "escalation_agent"
    SUMMARY = "summary_agent"
    TRANSLATION = "translation_agent"


# Request schemas
class AIAgentConfigCreateRequest(BaseCreate):
    """Schema for creating AI agent configuration"""
    agent_type: AIAgentTypeSchema = Field(description="Type of AI agent")
    name: str = Field(max_length=255, description="Configuration name")
    version: str = Field(default="1.0.0", max_length=20, description="Configuration version")
    description: Optional[str] = Field(None, description="Configuration description")
    
    # Environment and activation
    environment: str = Field("production", description="Target environment")
    is_default: bool = Field(False, description="Whether this is the default configuration")
    
    # AI Model configuration
    model_provider: str = Field("openai", description="AI provider")
    model_name: str = Field("gpt-4o-mini", description="Model name")
    model_parameters: Optional[Dict[str, Any]] = Field(None, description="Model parameters")
    
    # Prompt configuration
    system_prompt: Optional[str] = Field(None, description="System prompt template")
    prompt_template: Optional[str] = Field(None, description="User prompt template")
    prompt_variables: Optional[Dict[str, Any]] = Field(None, description="Prompt variables")
    few_shot_examples: Optional[List[Dict[str, Any]]] = Field(None, description="Few-shot examples")
    
    # Output configuration
    output_schema: Optional[Dict[str, Any]] = Field(None, description="Output schema")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Validation rules")
    post_processing_rules: Optional[Dict[str, Any]] = Field(None, description="Post-processing rules")
    
    # Performance settings
    temperature: str = Field("0.7", description="Model temperature")
    max_tokens: Optional[int] = Field(None, ge=1, le=32000, description="Maximum tokens")
    timeout_seconds: int = Field(30, ge=5, le=300, description="Request timeout")
    retry_attempts: int = Field(3, ge=1, le=10, description="Retry attempts")
    
    # Quality settings
    confidence_threshold: str = Field("0.8", description="Confidence threshold")
    content_filters: Optional[Dict[str, Any]] = Field(None, description="Content filters")
    safety_settings: Optional[Dict[str, Any]] = Field(None, description="Safety settings")
    
    # Cost management
    cost_per_request_usd: Optional[str] = Field(None, description="Cost per request")
    daily_budget_usd: Optional[str] = Field(None, description="Daily budget")
    monthly_budget_usd: Optional[str] = Field(None, description="Monthly budget")
    
    # A/B Testing
    ab_test_group: Optional[str] = Field(None, description="A/B test group")
    ab_test_percentage: Optional[int] = Field(None, ge=1, le=100, description="A/B test percentage")
    ab_test_start_date: Optional[datetime] = Field(None, description="A/B test start")
    ab_test_end_date: Optional[datetime] = Field(None, description="A/B test end")
    
    # Configuration inheritance
    parent_config_id: Optional[UUID] = Field(None, description="Parent configuration")
    inheritance_rules: Optional[Dict[str, str]] = Field(None, description="Inheritance rules")
    
    # Monitoring
    monitoring_enabled: bool = Field(True, description="Enable monitoring")
    alert_thresholds: Optional[Dict[str, Any]] = Field(None, description="Alert thresholds")
    
    # Metadata
    tags: Optional[List[str]] = Field(None, description="Configuration tags")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Configuration name cannot be empty')
        return v.strip()
    
    @field_validator('model_provider')
    @classmethod
    def validate_model_provider(cls, v):
        valid_providers = {"openai", "anthropic", "google", "azure", "local"}
        if v not in valid_providers:
            raise ValueError(f'Model provider must be one of: {valid_providers}')
        return v
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        try:
            temp = float(v)
            if not 0.0 <= temp <= 2.0:
                raise ValueError('Temperature must be between 0.0 and 2.0')
        except ValueError:
            raise ValueError('Temperature must be a valid number')
        return v
    
    @field_validator('confidence_threshold')
    @classmethod
    def validate_confidence_threshold(cls, v):
        try:
            threshold = float(v)
            if not 0.0 <= threshold <= 1.0:
                raise ValueError('Confidence threshold must be between 0.0 and 1.0')
        except ValueError:
            raise ValueError('Confidence threshold must be a valid number')
        return v
    
    @model_validator(mode='after')
    def validate_ab_test_dates(self):
        if self.ab_test_start_date and self.ab_test_end_date:
            if self.ab_test_start_date >= self.ab_test_end_date:
                raise ValueError('A/B test start date must be before end date')
        return self


class AIAgentConfigUpdateRequest(BaseUpdate):
    """Schema for updating AI agent configuration"""
    name: Optional[str] = Field(None, max_length=255, description="Configuration name")
    version: Optional[str] = Field(None, max_length=20, description="Configuration version")
    description: Optional[str] = Field(None, description="Description")
    
    # Model configuration
    model_provider: Optional[str] = Field(None, description="AI provider")
    model_name: Optional[str] = Field(None, description="Model name")
    model_parameters: Optional[Dict[str, Any]] = Field(None, description="Model parameters")
    
    # Prompts
    system_prompt: Optional[str] = Field(None, description="System prompt")
    prompt_template: Optional[str] = Field(None, description="Prompt template")
    prompt_variables: Optional[Dict[str, Any]] = Field(None, description="Prompt variables")
    few_shot_examples: Optional[List[Dict[str, Any]]] = Field(None, description="Few-shot examples")
    
    # Output configuration
    output_schema: Optional[Dict[str, Any]] = Field(None, description="Output schema")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Validation rules")
    post_processing_rules: Optional[Dict[str, Any]] = Field(None, description="Post-processing rules")
    
    # Performance
    temperature: Optional[str] = Field(None, description="Model temperature")
    max_tokens: Optional[int] = Field(None, ge=1, le=32000, description="Maximum tokens")
    timeout_seconds: Optional[int] = Field(None, ge=5, le=300, description="Timeout")
    retry_attempts: Optional[int] = Field(None, ge=1, le=10, description="Retry attempts")
    
    # Quality
    confidence_threshold: Optional[str] = Field(None, description="Confidence threshold")
    content_filters: Optional[Dict[str, Any]] = Field(None, description="Content filters")
    safety_settings: Optional[Dict[str, Any]] = Field(None, description="Safety settings")
    
    # Cost management
    cost_per_request_usd: Optional[str] = Field(None, description="Cost per request")
    daily_budget_usd: Optional[str] = Field(None, description="Daily budget")
    monthly_budget_usd: Optional[str] = Field(None, description="Monthly budget")
    
    # A/B Testing
    ab_test_group: Optional[str] = Field(None, description="A/B test group")
    ab_test_percentage: Optional[int] = Field(None, ge=1, le=100, description="A/B test percentage")
    ab_test_start_date: Optional[datetime] = Field(None, description="A/B test start")
    ab_test_end_date: Optional[datetime] = Field(None, description="A/B test end")
    
    # Inheritance
    parent_config_id: Optional[UUID] = Field(None, description="Parent configuration")
    inheritance_rules: Optional[Dict[str, str]] = Field(None, description="Inheritance rules")
    
    # Monitoring
    monitoring_enabled: Optional[bool] = Field(None, description="Enable monitoring")
    alert_thresholds: Optional[Dict[str, Any]] = Field(None, description="Alert thresholds")
    
    # Metadata
    tags: Optional[List[str]] = Field(None, description="Tags")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Configuration name cannot be empty')
        return v.strip() if v else None
    
    @field_validator('model_provider')
    @classmethod
    def validate_model_provider(cls, v):
        if v is not None:
            valid_providers = {"openai", "anthropic", "google", "azure", "local"}
            if v not in valid_providers:
                raise ValueError(f'Model provider must be one of: {valid_providers}')
        return v
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if v is not None:
            try:
                temp = float(v)
                if not 0.0 <= temp <= 2.0:
                    raise ValueError('Temperature must be between 0.0 and 2.0')
            except ValueError:
                raise ValueError('Temperature must be a valid number')
        return v
    
    @field_validator('confidence_threshold')
    @classmethod
    def validate_confidence_threshold(cls, v):
        if v is not None:
            try:
                threshold = float(v)
                if not 0.0 <= threshold <= 1.0:
                    raise ValueError('Confidence threshold must be between 0.0 and 1.0')
            except ValueError:
                raise ValueError('Confidence threshold must be a valid number')
        return v


class AIAgentConfigActivationRequest(BaseSchema):
    """Schema for activating/deactivating configuration"""
    is_active: bool = Field(description="Whether to activate the configuration")
    reason: Optional[str] = Field(None, description="Reason for activation/deactivation")


class AIAgentConfigApprovalRequest(BaseSchema):
    """Schema for approving configuration"""
    approved: bool = Field(description="Whether to approve the configuration")
    comments: Optional[str] = Field(None, description="Approval comments")


class AIAgentConfigDeprecationRequest(BaseSchema):
    """Schema for deprecating configuration"""
    reason: str = Field(description="Reason for deprecation")
    replacement_config_id: Optional[UUID] = Field(None, description="Replacement configuration")
    deprecation_date: Optional[datetime] = Field(None, description="Deprecation date")


class AIAgentConfigCloneRequest(BaseSchema):
    """Schema for cloning configuration"""
    name: str = Field(description="Name for cloned configuration")
    version: str = Field(description="Version for cloned configuration")
    modifications: Optional[Dict[str, Any]] = Field(None, description="Modifications to apply")
    environment: Optional[str] = Field(None, description="Target environment")


class AIAgentConfigTestRequest(BaseSchema):
    """Schema for testing configuration"""
    test_data: Dict[str, Any] = Field(description="Test input data")
    expected_output: Optional[Dict[str, Any]] = Field(None, description="Expected output")
    test_options: Optional[Dict[str, Any]] = Field(None, description="Test options")


# Response schemas
class AIAgentConfigUserInfo(BaseSchema):
    """User information for config responses"""
    id: UUID = Field(description="User ID")
    email: str = Field(description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    display_name: str = Field(description="User display name")


class AIAgentConfigUsageStats(BaseSchema):
    """Configuration usage statistics"""
    total_requests: int = Field(description="Total requests")
    successful_requests: int = Field(description="Successful requests")
    failed_requests: int = Field(description="Failed requests")
    success_rate: float = Field(description="Success rate percentage")
    average_response_time_ms: Optional[int] = Field(None, description="Average response time")
    last_used_at: Optional[datetime] = Field(None, description="Last used timestamp")
    cost_per_day_usd: Optional[float] = Field(None, description="Estimated daily cost")


class AIAgentConfigBaseResponse(BaseResponse):
    """Base AI agent configuration response"""
    agent_type: AIAgentTypeSchema = Field(description="Agent type")
    name: str = Field(description="Configuration name")
    version: str = Field(description="Configuration version")
    description: Optional[str] = Field(None, description="Description")
    is_active: bool = Field(description="Whether configuration is active")
    is_default: bool = Field(description="Whether this is the default")
    environment: str = Field(description="Environment")


class AIAgentConfigListResponse(AIAgentConfigBaseResponse):
    """AI configuration information for list views"""
    model_provider: str = Field(description="AI provider")
    model_name: str = Field(description="Model name")
    temperature: str = Field(description="Model temperature")
    confidence_threshold: str = Field(description="Confidence threshold")
    is_deprecated: bool = Field(description="Whether configuration is deprecated")
    success_rate: float = Field(description="Success rate")
    total_requests: int = Field(description="Total requests")
    last_used_at: Optional[datetime] = Field(None, description="Last used")
    created_by: Optional[AIAgentConfigUserInfo] = Field(None, description="Creator")
    approved_by: Optional[AIAgentConfigUserInfo] = Field(None, description="Approver")
    approved_at: Optional[datetime] = Field(None, description="Approval date")
    is_ab_test_active: bool = Field(description="Whether A/B test is active")


class AIAgentConfigDetailResponse(AIAgentConfigBaseResponse):
    """Detailed AI configuration information"""
    # Model configuration
    model_provider: str = Field(description="AI provider")
    model_name: str = Field(description="Model name")
    model_parameters: Optional[Dict[str, Any]] = Field(None, description="Model parameters")
    
    # Prompt configuration
    system_prompt: Optional[str] = Field(None, description="System prompt")
    prompt_template: Optional[str] = Field(None, description="Prompt template")
    prompt_variables: Optional[Dict[str, Any]] = Field(None, description="Prompt variables")
    few_shot_examples: Optional[List[Dict[str, Any]]] = Field(None, description="Few-shot examples")
    
    # Output configuration
    output_schema: Optional[Dict[str, Any]] = Field(None, description="Output schema")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Validation rules")
    post_processing_rules: Optional[Dict[str, Any]] = Field(None, description="Post-processing rules")
    
    # Performance settings
    temperature: str = Field(description="Model temperature")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens")
    timeout_seconds: int = Field(description="Request timeout")
    retry_attempts: int = Field(description="Retry attempts")
    
    # Quality settings
    confidence_threshold: str = Field(description="Confidence threshold")
    content_filters: Optional[Dict[str, Any]] = Field(None, description="Content filters")
    safety_settings: Optional[Dict[str, Any]] = Field(None, description="Safety settings")
    
    # Cost management
    cost_per_request_usd: Optional[str] = Field(None, description="Cost per request")
    daily_budget_usd: Optional[str] = Field(None, description="Daily budget")
    monthly_budget_usd: Optional[str] = Field(None, description="Monthly budget")
    
    # Usage statistics
    usage_stats: AIAgentConfigUsageStats = Field(description="Usage statistics")
    
    # A/B Testing
    ab_test_group: Optional[str] = Field(None, description="A/B test group")
    ab_test_percentage: Optional[int] = Field(None, description="A/B test percentage")
    ab_test_start_date: Optional[datetime] = Field(None, description="A/B test start")
    ab_test_end_date: Optional[datetime] = Field(None, description="A/B test end")
    is_ab_test_active: bool = Field(description="Whether A/B test is active")
    
    # Configuration inheritance
    parent_config_id: Optional[UUID] = Field(None, description="Parent configuration")
    inheritance_rules: Optional[Dict[str, str]] = Field(None, description="Inheritance rules")
    parent_config: Optional['AIAgentConfigBaseResponse'] = Field(None, description="Parent config info")
    child_configs: Optional[List['AIAgentConfigBaseResponse']] = Field(None, description="Child configs")
    
    # Monitoring
    monitoring_enabled: bool = Field(description="Monitoring enabled")
    alert_thresholds: Optional[Dict[str, Any]] = Field(None, description="Alert thresholds")
    performance_metrics: Optional[Dict[str, Any]] = Field(None, description="Performance metrics")
    
    # Lifecycle
    created_by: Optional[AIAgentConfigUserInfo] = Field(None, description="Creator")
    approved_by: Optional[AIAgentConfigUserInfo] = Field(None, description="Approver")
    approved_at: Optional[datetime] = Field(None, description="Approval date")
    deprecated_at: Optional[datetime] = Field(None, description="Deprecation date")
    deprecation_reason: Optional[str] = Field(None, description="Deprecation reason")
    
    # Change tracking
    change_log: Optional[List[Dict[str, Any]]] = Field(None, description="Change log")
    tags: Optional[List[str]] = Field(None, description="Tags")
    
    # Computed properties
    is_deprecated: bool = Field(description="Whether configuration is deprecated")


class AIAgentConfigEffectiveResponse(BaseSchema):
    """Effective configuration response (with inheritance applied)"""
    config_id: UUID = Field(description="Configuration ID")
    effective_config: Dict[str, Any] = Field(description="Effective configuration")
    inheritance_chain: List[UUID] = Field(description="Inheritance chain")
    overrides_applied: Dict[str, Any] = Field(description="Overrides applied")


class AIAgentConfigTestResponse(BaseSchema):
    """Configuration test response"""
    test_id: str = Field(description="Test ID")
    config_id: UUID = Field(description="Configuration ID")
    success: bool = Field(description="Test success")
    response_time_ms: int = Field(description="Response time")
    output: Optional[Dict[str, Any]] = Field(None, description="Test output")
    validation_results: Optional[Dict[str, Any]] = Field(None, description="Validation results")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    confidence_score: Optional[float] = Field(None, description="Output confidence")
    suggestions: Optional[List[str]] = Field(None, description="Improvement suggestions")


class AIAgentConfigStatsResponse(BaseSchema):
    """AI configuration statistics response"""
    total_configs: int = Field(description="Total configurations")
    active_configs: int = Field(description="Active configurations")
    deprecated_configs: int = Field(description="Deprecated configurations")
    agent_type_distribution: Dict[str, int] = Field(description="Configs by agent type")
    provider_distribution: Dict[str, int] = Field(description="Configs by provider")
    environment_distribution: Dict[str, int] = Field(description="Configs by environment")
    total_requests_today: int = Field(description="Total requests today")
    success_rate_today: float = Field(description="Success rate today")
    avg_response_time_ms: Optional[float] = Field(None, description="Average response time")
    total_cost_today_usd: Optional[float] = Field(None, description="Total cost today")
    ab_tests_active: int = Field(description="Active A/B tests")


class AIAgentConfigVersionResponse(BaseSchema):
    """Configuration version information"""
    config_id: UUID = Field(description="Configuration ID")
    version: str = Field(description="Version")
    created_at: datetime = Field(description="Creation date")
    created_by: Optional[AIAgentConfigUserInfo] = Field(None, description="Creator")
    changes_summary: str = Field(description="Summary of changes")
    is_current: bool = Field(description="Whether this is the current version")
    usage_stats: Optional[AIAgentConfigUsageStats] = Field(None, description="Usage statistics")


# Search and filter schemas
class AIAgentConfigSearchParams(BaseSchema):
    """AI configuration search parameters"""
    q: Optional[str] = Field(None, description="Search query (name, description)")
    agent_type: Optional[List[AIAgentTypeSchema]] = Field(None, description="Filter by agent type")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_default: Optional[bool] = Field(None, description="Filter by default status")
    is_deprecated: Optional[bool] = Field(None, description="Filter by deprecation")
    environment: Optional[str] = Field(None, description="Filter by environment")
    model_provider: Optional[str] = Field(None, description="Filter by provider")
    model_name: Optional[str] = Field(None, description="Filter by model")
    created_by_id: Optional[UUID] = Field(None, description="Filter by creator")
    approved_by_id: Optional[UUID] = Field(None, description="Filter by approver")
    has_ab_test: Optional[bool] = Field(None, description="Filter by A/B test presence")
    is_ab_test_active: Optional[bool] = Field(None, description="Filter by active A/B test")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    created_after: Optional[datetime] = Field(None, description="Created after date")
    created_before: Optional[datetime] = Field(None, description="Created before date")
    last_used_after: Optional[datetime] = Field(None, description="Last used after date")
    success_rate_min: Optional[float] = Field(None, ge=0, le=100, description="Minimum success rate")


class AIAgentConfigSortParams(BaseSchema):
    """AI configuration sorting parameters"""
    sort_by: str = Field(
        "created_at",
        description="Sort field",
        pattern="^(created_at|updated_at|name|version|success_rate|total_requests|last_used_at)$"
    )
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


# Bulk operation schemas
class AIAgentConfigBulkActivateRequest(BaseSchema):
    """Schema for bulk activation"""
    config_ids: List[UUID] = Field(description="Configuration IDs to activate")
    reason: Optional[str] = Field(None, description="Reason for activation")


class AIAgentConfigBulkDeprecateRequest(BaseSchema):
    """Schema for bulk deprecation"""
    config_ids: List[UUID] = Field(description="Configuration IDs to deprecate")
    reason: str = Field(description="Reason for deprecation")
    replacement_config_id: Optional[UUID] = Field(None, description="Replacement configuration")


class AIAgentConfigBulkTestRequest(BaseSchema):
    """Schema for bulk testing"""
    config_ids: List[UUID] = Field(description="Configuration IDs to test")
    test_data: Dict[str, Any] = Field(description="Test data to use")
    test_options: Optional[Dict[str, Any]] = Field(None, description="Test options")


# Import/Export schemas
class AIAgentConfigExportRequest(BaseSchema):
    """Schema for exporting configurations"""
    config_ids: Optional[List[UUID]] = Field(None, description="Specific configs to export")
    agent_types: Optional[List[AIAgentTypeSchema]] = Field(None, description="Agent types to export")
    environment: Optional[str] = Field(None, description="Environment to export")
    include_sensitive: bool = Field(False, description="Include sensitive data")
    format: str = Field("json", description="Export format", pattern="^(json|yaml)$")


class AIAgentConfigExportResponse(BaseSchema):
    """Configuration export response"""
    export_id: str = Field(description="Export ID")
    download_url: str = Field(description="Download URL")
    expires_at: datetime = Field(description="Download expiration")
    config_count: int = Field(description="Number of configurations exported")
    file_size_bytes: int = Field(description="File size")


class AIAgentConfigImportRequest(BaseSchema):
    """Schema for importing configurations"""
    file_url: Optional[str] = Field(None, description="URL of file to import")
    file_data: Optional[str] = Field(None, description="Base64 encoded file data")
    format: str = Field("json", description="File format", pattern="^(json|yaml)$")
    overwrite_existing: bool = Field(False, description="Overwrite existing configs")
    environment: Optional[str] = Field(None, description="Target environment")
    dry_run: bool = Field(False, description="Perform validation only")


class AIAgentConfigImportResponse(BaseSchema):
    """Configuration import response"""
    import_id: str = Field(description="Import ID")
    configs_imported: int = Field(description="Configurations imported")
    configs_updated: int = Field(description="Configurations updated")
    configs_skipped: int = Field(description="Configurations skipped")
    errors: List[str] = Field(default=[], description="Import errors")
    warnings: List[str] = Field(default=[], description="Import warnings")