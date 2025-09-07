#!/usr/bin/env python3
"""
Base Pydantic schemas for common validation patterns
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )


class TimestampMixin(BaseSchema):
    """Mixin for timestamp fields"""
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class UUIDMixin(BaseSchema):
    """Mixin for UUID primary key"""
    id: UUID = Field(description="Unique identifier")


class SoftDeleteMixin(BaseSchema):
    """Mixin for soft delete fields"""
    deleted_at: Optional[datetime] = Field(None, description="Deletion timestamp")
    is_deleted: bool = Field(False, description="Whether record is deleted")


class BaseResponse(UUIDMixin, TimestampMixin):
    """Base response schema with ID and timestamps"""
    pass


class BaseCreate(BaseSchema):
    """Base create schema without generated fields"""
    pass


class BaseUpdate(BaseSchema):
    """Base update schema with optional fields"""
    pass


class PaginationParams(BaseSchema):
    """Standard pagination parameters"""
    page: int = Field(1, ge=1, description="Page number (1-based)")
    size: int = Field(20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.size


class SortParams(BaseSchema):
    """Standard sorting parameters"""
    sort_by: str = Field("created_at", description="Field to sort by")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


class FilterParams(BaseSchema):
    """Standard filtering parameters"""
    search: Optional[str] = Field(None, description="Search query")
    status: Optional[str] = Field(None, description="Filter by status")
    category: Optional[str] = Field(None, description="Filter by category")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date (after)")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date (before)")


class PaginatedResponse(BaseSchema):
    """Standard paginated response wrapper"""
    items: List[Any] = Field(description="List of items")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    size: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there are more pages")
    has_prev: bool = Field(description="Whether there are previous pages")
    
    @classmethod
    def create(
        cls,
        items: List[Any],
        total: int,
        page: int,
        size: int
    ) -> "PaginatedResponse":
        """Create paginated response from items and counts"""
        pages = (total + size - 1) // size  # Ceiling division
        
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )


class ErrorDetail(BaseSchema):
    """Error detail schema"""
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseSchema):
    """Standard error response schema"""
    error: str = Field(description="Error type or category")
    message: str = Field(description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")


class SuccessResponse(BaseSchema):
    """Standard success response schema"""
    success: bool = Field(True, description="Operation success status")
    message: str = Field(description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional response data")


class BulkOperationRequest(BaseSchema):
    """Schema for bulk operations"""
    ids: List[UUID] = Field(description="List of IDs to operate on")
    action: str = Field(description="Action to perform")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Action parameters")


class BulkOperationResponse(BaseSchema):
    """Schema for bulk operation responses"""
    total: int = Field(description="Total number of items processed")
    successful: int = Field(description="Number of successful operations")
    failed: int = Field(description="Number of failed operations")
    errors: List[ErrorDetail] = Field(default_factory=list, description="List of errors")
    results: Optional[List[Dict[str, Any]]] = Field(None, description="Operation results")


class HealthCheckResponse(BaseSchema):
    """Health check response schema"""
    status: str = Field(description="Overall health status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Check timestamp")
    services: Dict[str, Dict[str, Any]] = Field(description="Individual service statuses")
    version: Optional[str] = Field(None, description="Application version")
    uptime_seconds: Optional[int] = Field(None, description="Application uptime in seconds")


class ValidationErrorResponse(BaseSchema):
    """Validation error response schema"""
    error: str = Field("validation_error", description="Error type")
    message: str = Field(description="Validation error message")
    errors: List[Dict[str, Any]] = Field(description="Field-specific validation errors")


# Common field validators and types
class EmailStr(str):
    """String that validates as email"""
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type, handler
    ):
        from pydantic_core import core_schema
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )
    
    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError('string required')
        
        # Simple email validation
        if '@' not in v or '.' not in v.split('@')[-1]:
            raise ValueError('invalid email format')
        
        return cls(v)


class PhoneStr(str):
    """String that validates as phone number"""
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type, handler
    ):
        from pydantic_core import core_schema
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )
    
    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError('string required')
        
        # Remove common phone number formatting
        cleaned = ''.join(filter(str.isdigit, v))
        
        # Basic phone number validation (10-15 digits)
        if not 10 <= len(cleaned) <= 15:
            raise ValueError('invalid phone number format')
        
        return cls(v)


class URLStr(str):
    """String that validates as URL"""
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type, handler
    ):
        from pydantic_core import core_schema
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )
    
    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError('string required')
        
        # Simple URL validation
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        
        return cls(v)


# Utility functions for schema conversion
def exclude_none(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values from dictionary"""
    return {k: v for k, v in data.items() if v is not None}


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase"""
    components = snake_str.split('_')
    return components[0] + ''.join(word.capitalize() for word in components[1:])


def to_snake_case(camel_str: str) -> str:
    """Convert camelCase to snake_case"""
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()