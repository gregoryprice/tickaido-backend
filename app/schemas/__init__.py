#!/usr/bin/env python3
"""
Pydantic Schemas for AI Ticket Creator Backend API

This module exports all Pydantic schemas used for request/response validation,
serialization, and automatic OpenAPI documentation generation.
"""

# Base schemas and utilities
# AI Configuration schemas
from app.schemas.ai_config import (
    AIAgentConfigActivationRequest,
    AIAgentConfigApprovalRequest,
    AIAgentConfigBaseResponse,
    AIAgentConfigBulkActivateRequest,
    AIAgentConfigBulkDeprecateRequest,
    AIAgentConfigBulkTestRequest,
    AIAgentConfigCloneRequest,
    # Request schemas
    AIAgentConfigCreateRequest,
    AIAgentConfigDeprecationRequest,
    AIAgentConfigDetailResponse,
    AIAgentConfigEffectiveResponse,
    AIAgentConfigExportRequest,
    AIAgentConfigExportResponse,
    AIAgentConfigImportRequest,
    AIAgentConfigImportResponse,
    AIAgentConfigListResponse,
    # Search and filter schemas
    AIAgentConfigSearchParams,
    AIAgentConfigSortParams,
    AIAgentConfigStatsResponse,
    AIAgentConfigTestRequest,
    AIAgentConfigTestResponse,
    AIAgentConfigUpdateRequest,
    AIAgentConfigUsageStats,
    # Response schemas
    AIAgentConfigUserInfo,
    AIAgentConfigVersionResponse,
    # Enums
    AIAgentTypeSchema,
)
from app.schemas.base import (
    BaseCreate,
    BaseResponse,
    BaseSchema,
    BaseUpdate,
    BulkOperationRequest,
    BulkOperationResponse,
    EmailStr,
    ErrorDetail,
    ErrorResponse,
    FilterParams,
    HealthCheckResponse,
    PaginatedResponse,
    PaginationParams,
    PhoneStr,
    SoftDeleteMixin,
    SortParams,
    SuccessResponse,
    TimestampMixin,
    URLStr,
    UUIDMixin,
    ValidationErrorResponse,
    exclude_none,
    to_camel_case,
    to_snake_case,
)

# File schemas
from app.schemas.file import (
    FileAnalysisRequest,
    FileAnalysisResponse,
    FileBaseResponse,
    FileBulkDeleteRequest,
    FileBulkProcessRequest,
    FileBulkTagRequest,
    FileBulkUpdateRequest,
    FileContentResponse,
    FileDetailResponse,
    FileDownloadResponse,
    FileErrorResponse,
    FileListResponse,
    FileProcessingRequest,
    FileProcessingResponse,
    FileProcessingResults,
    # Search and filter schemas
    FileSearchParams,
    FileSortParams,
    FileStatsResponse,
    # Enums
    FileStatusSchema,
    FileTicketInfo,
    FileTypeSchema,
    FileUpdateRequest,
    # Request schemas
    FileUploadRequest,
    FileUploadResponse,
    FileUploadUrlRequest,
    FileUploadUrlResponse,
    # Response schemas
    FileUserInfo,
)

# Integration schemas
from app.schemas.integration import (
    IntegrationBaseResponse,
    IntegrationBulkStatusUpdateRequest,
    IntegrationBulkSyncRequest,
    IntegrationBulkTestRequest,
    # Enums
    IntegrationCategorySchema,
    IntegrationConfigResponse,
    # Request schemas
    IntegrationCreateRequest,
    IntegrationDetailResponse,
    IntegrationErrorResponse,
    # Response schemas
    IntegrationHealthInfo,
    IntegrationListResponse,
    IntegrationRoutingTestRequest,
    IntegrationRoutingTestResponse,
    # Search and filter schemas
    IntegrationSearchParams,
    IntegrationSortParams,
    IntegrationStatsResponse,
    IntegrationStatusSchema,
    IntegrationStatusUpdateRequest,
    IntegrationSyncRequest,
    IntegrationSyncResponse,
    IntegrationTestRequest,
    IntegrationTestResponse,
    IntegrationUpdateRequest,
    IntegrationUsageStats,
    IntegrationWebhookEvent,
    IntegrationWebhookResponse,
)

# Ticket schemas
from app.schemas.ticket import (
    TicketActivityResponse,
    TicketAIAnalysis,
    TicketAIAnalysisRequest,
    TicketAIAnalysisResponse,
    TicketAICreateRequest,
    TicketAICreateResponse,
    TicketAssignmentRequest,
    TicketBaseResponse,
    TicketBulkAssignRequest,
    TicketBulkCategoryRequest,
    TicketBulkStatusUpdateRequest,
    TicketBulkUpdateRequest,
    TicketCategorySchema,
    # Request schemas
    TicketCreateRequest,
    TicketDetailResponse,
    TicketEscalationRequest,
    TicketPrioritySchema,
    TicketPublicResponse,
    TicketSatisfactionRequest,
    # Search and filter schemas
    TicketSearchParams,
    TicketSortParams,
    TicketStatsResponse,
    # Enums
    TicketStatusSchema,
    TicketStatusUpdateRequest,
    TicketUpdateRequest,
    # Response schemas
    TicketUserInfo,
)

# User schemas
from app.schemas.user import (
    UserActivityResponse,
    UserAdminResponse,
    UserAPIKeyRequest,
    UserAPIKeyResponse,
    UserAuditLogResponse,
    UserBulkCreateRequest,
    UserBulkDeactivateRequest,
    UserBulkUpdateRequest,
    # Request schemas
    UserCreateRequest,
    UserEmailVerificationRequest,
    UserListResponse,
    UserLoginRequest,
    UserLoginResponse,
    UserPasswordChangeRequest,
    UserPasswordResetConfirmRequest,
    UserPasswordResetRequest,
    UserPermissionsResponse,
    UserPermissionsUpdateRequest,
    UserPrivateResponse,
    UserProfileResponse,
    # Response schemas
    UserPublicResponse,
    UserRegistrationRequest,
    # Enums
    UserRoleSchema,
    # Search and filter schemas
    UserSearchParams,
    UserSortParams,
    UserStatsResponse,
    UserUpdateRequest,
)

# Export all schemas for easy importing
__all__ = [
    # Base schemas
    "BaseSchema",
    "BaseResponse", 
    "BaseCreate",
    "BaseUpdate",
    "TimestampMixin",
    "UUIDMixin",
    "SoftDeleteMixin",
    "PaginationParams",
    "SortParams",
    "FilterParams",
    "PaginatedResponse",
    "ErrorDetail",
    "ErrorResponse",
    "SuccessResponse",
    "BulkOperationRequest",
    "BulkOperationResponse",
    "HealthCheckResponse",
    "ValidationErrorResponse",
    "EmailStr",
    "PhoneStr", 
    "URLStr",
    "exclude_none",
    "to_camel_case",
    "to_snake_case",
    
    # User schemas
    "UserRoleSchema",
    "UserCreateRequest",
    "UserUpdateRequest",
    "UserPasswordChangeRequest",
    "UserPermissionsUpdateRequest",
    "UserAPIKeyRequest",
    "UserBulkCreateRequest",
    "UserBulkUpdateRequest", 
    "UserBulkDeactivateRequest",
    "UserLoginRequest",
    "UserRegistrationRequest",
    "UserPasswordResetRequest",
    "UserPasswordResetConfirmRequest",
    "UserEmailVerificationRequest",
    "UserPublicResponse",
    "UserPrivateResponse",
    "UserAdminResponse",
    "UserListResponse",
    "UserProfileResponse",
    "UserAPIKeyResponse",
    "UserPermissionsResponse",
    "UserStatsResponse",
    "UserLoginResponse",
    "UserActivityResponse",
    "UserAuditLogResponse",
    "UserSearchParams",
    "UserSortParams",
    
    # Ticket schemas
    "TicketStatusSchema",
    "TicketPrioritySchema", 
    "TicketCategorySchema",
    "TicketCreateRequest",
    "TicketUpdateRequest",
    "TicketStatusUpdateRequest",
    "TicketAssignmentRequest",
    "TicketEscalationRequest",
    "TicketSatisfactionRequest",
    "TicketAIAnalysisRequest",
    "TicketBulkUpdateRequest",
    "TicketBulkStatusUpdateRequest",
    "TicketBulkAssignRequest",
    "TicketBulkCategoryRequest",
    "TicketAICreateRequest",
    "TicketUserInfo",
    "TicketAIAnalysis",
    "TicketBaseResponse",
    "TicketDetailResponse",
    "TicketPublicResponse",
    "TicketStatsResponse",
    "TicketActivityResponse",
    "TicketAICreateResponse",
    "TicketAIAnalysisResponse",
    "TicketSearchParams",
    "TicketSortParams",
    
    # File schemas
    "FileStatusSchema",
    "FileTypeSchema",
    "FileUploadRequest",
    "FileUpdateRequest",
    "FileProcessingRequest", 
    "FileAnalysisRequest",
    "FileBulkProcessRequest",
    "FileBulkDeleteRequest",
    "FileBulkUpdateRequest",
    "FileBulkTagRequest",
    "FileUploadUrlRequest",
    "FileUserInfo",
    "FileTicketInfo",
    "FileProcessingResults",
    "FileBaseResponse",
    "FileListResponse",
    "FileDetailResponse",
    "FileContentResponse",
    "FileProcessingResponse",
    "FileAnalysisResponse",
    "FileStatsResponse",
    "FileDownloadResponse",
    "FileUploadResponse",
    "FileUploadUrlResponse",
    "FileErrorResponse",
    "FileSearchParams",
    "FileSortParams",
    
    # Integration schemas
    "IntegrationCategorySchema",
    "IntegrationStatusSchema",
    "IntegrationCreateRequest",
    "IntegrationUpdateRequest",
    "IntegrationStatusUpdateRequest",
    "IntegrationTestRequest",
    "IntegrationSyncRequest",
    "IntegrationRoutingTestRequest",
    "IntegrationBulkStatusUpdateRequest",
    "IntegrationBulkTestRequest",
    "IntegrationBulkSyncRequest",
    "IntegrationHealthInfo",
    "IntegrationUsageStats",
    "IntegrationBaseResponse",
    "IntegrationListResponse",
    "IntegrationDetailResponse",
    "IntegrationConfigResponse",
    "IntegrationTestResponse",
    "IntegrationSyncResponse",
    "IntegrationRoutingTestResponse",
    "IntegrationStatsResponse",
    "IntegrationWebhookEvent",
    "IntegrationWebhookResponse",
    "IntegrationErrorResponse",
    "IntegrationSearchParams",
    "IntegrationSortParams",
    
    # AI Configuration schemas
    "AIAgentTypeSchema",
    "AIAgentConfigCreateRequest",
    "AIAgentConfigUpdateRequest",
    "AIAgentConfigActivationRequest",
    "AIAgentConfigApprovalRequest",
    "AIAgentConfigDeprecationRequest",
    "AIAgentConfigCloneRequest",
    "AIAgentConfigTestRequest",
    "AIAgentConfigBulkActivateRequest",
    "AIAgentConfigBulkDeprecateRequest",
    "AIAgentConfigBulkTestRequest",
    "AIAgentConfigExportRequest",
    "AIAgentConfigImportRequest",
    "AIAgentConfigUserInfo",
    "AIAgentConfigUsageStats",
    "AIAgentConfigBaseResponse",
    "AIAgentConfigListResponse",
    "AIAgentConfigDetailResponse",
    "AIAgentConfigEffectiveResponse",
    "AIAgentConfigTestResponse",
    "AIAgentConfigStatsResponse",
    "AIAgentConfigVersionResponse",
    "AIAgentConfigExportResponse",
    "AIAgentConfigImportResponse",
    "AIAgentConfigSearchParams",
    "AIAgentConfigSortParams",
]


# Schema registry for dynamic access
SCHEMA_REGISTRY = {
    # User schemas
    "user": {
        "create": UserCreateRequest,
        "update": UserUpdateRequest,
        "list": UserListResponse,
        "detail": UserPrivateResponse,
        "admin": UserAdminResponse,
        "public": UserPublicResponse,
    },
    
    # Ticket schemas
    "ticket": {
        "create": TicketCreateRequest,
        "update": TicketUpdateRequest,
        "list": TicketDetailResponse,
        "detail": TicketDetailResponse,
        "public": TicketPublicResponse,
    },
    
    # File schemas
    "file": {
        "upload": FileUploadRequest,
        "update": FileUpdateRequest,
        "list": FileListResponse,
        "detail": FileDetailResponse,
    },
    
    # Integration schemas
    "integration": {
        "create": IntegrationCreateRequest,
        "update": IntegrationUpdateRequest,
        "list": IntegrationListResponse,
        "detail": IntegrationDetailResponse,
    },
    
    # AI Configuration schemas
    "ai_config": {
        "create": AIAgentConfigCreateRequest,
        "update": AIAgentConfigUpdateRequest,
        "list": AIAgentConfigListResponse,
        "detail": AIAgentConfigDetailResponse,
    },
}


def get_schema(resource: str, action: str):
    """
    Get schema class by resource and action.
    
    Args:
        resource: Resource name (user, ticket, file, integration, ai_config)
        action: Action name (create, update, list, detail, etc.)
        
    Returns:
        Pydantic schema class or None if not found
    """
    return SCHEMA_REGISTRY.get(resource, {}).get(action)


def get_response_schema(resource: str, detail: bool = False):
    """
    Get appropriate response schema for a resource.
    
    Args:
        resource: Resource name
        detail: Whether to get detail schema (True) or list schema (False)
        
    Returns:
        Pydantic schema class or None if not found
    """
    action = "detail" if detail else "list"
    return get_schema(resource, action)


def get_request_schema(resource: str, action: str):
    """
    Get appropriate request schema for a resource action.
    
    Args:
        resource: Resource name
        action: Action name (create, update)
        
    Returns:
        Pydantic schema class or None if not found
    """
    return get_schema(resource, action)


# Schema validation utilities
def validate_schema_compatibility(schema_class, data: dict) -> bool:
    """
    Check if data is compatible with schema without raising exceptions.
    
    Args:
        schema_class: Pydantic schema class
        data: Data to validate
        
    Returns:
        bool: True if data is compatible
    """
    try:
        schema_class.model_validate(data)
        return True
    except Exception:
        return False


def get_schema_fields(schema_class) -> list[str]:
    """
    Get list of field names from a Pydantic schema.
    
    Args:
        schema_class: Pydantic schema class
        
    Returns:
        List of field names
    """
    return list(schema_class.model_fields.keys())


def get_required_fields(schema_class) -> list[str]:
    """
    Get list of required field names from a Pydantic schema.
    
    Args:
        schema_class: Pydantic schema class
        
    Returns:
        List of required field names
    """
    return [
        field_name for field_name, field_info in schema_class.model_fields.items()
        if field_info.is_required()
    ]


def get_optional_fields(schema_class) -> list[str]:
    """
    Get list of optional field names from a Pydantic schema.
    
    Args:
        schema_class: Pydantic schema class
        
    Returns:
        List of optional field names
    """
    return [
        field_name for field_name, field_info in schema_class.model_fields.items()
        if not field_info.is_required()
    ]