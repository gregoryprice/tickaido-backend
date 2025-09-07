#!/usr/bin/env python3
"""
Base model class with common fields and functionality
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import declarative_mixin

# Create the declarative base
Base = declarative_base()

@declarative_mixin
class TimestampMixin:
    """Mixin to add timestamp fields to models"""
    
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

@declarative_mixin 
class SoftDeleteMixin:
    """Mixin to add soft delete functionality"""
    
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
    
    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )
    
    def soft_delete(self):
        """Mark record as deleted"""
        self.deleted_at = datetime.now(timezone.utc)
        self.is_deleted = True
    
    def restore(self):
        """Restore soft deleted record"""
        self.deleted_at = None
        self.is_deleted = False

class BaseModel(Base, TimestampMixin, SoftDeleteMixin):
    """
    Abstract base model with common fields and functionality.
    Includes UUID primary key, timestamps, and soft delete.
    """
    
    __abstract__ = True
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False
    )
    
    # Metadata fields
    notes = Column(Text, nullable=True, comment="Internal notes")
    extra_metadata = Column(Text, nullable=True, comment="JSON metadata storage")
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def to_dict(self, include_deleted: bool = False) -> dict:
        """
        Convert model instance to dictionary.
        
        Args:
            include_deleted: Include soft deleted records
            
        Returns:
            dict: Model data as dictionary
        """
        if not include_deleted and getattr(self, 'is_deleted', False):
            return {}
        
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Convert datetime to ISO format
            if isinstance(value, datetime):
                value = value.isoformat()
            # Convert UUID to string
            elif isinstance(value, uuid.UUID):
                value = str(value)
            
            result[column.name] = value
            
        return result
    
    @classmethod
    def from_dict(cls, data: dict):
        """
        Create model instance from dictionary.
        
        Args:
            data: Dictionary with model data
            
        Returns:
            Model instance
        """
        # Filter out fields that don't exist in the model
        valid_fields = {c.name for c in cls.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
    
    def update_from_dict(self, data: dict, exclude_fields: Optional[set] = None):
        """
        Update model instance from dictionary.
        
        Args:
            data: Dictionary with updated data
            exclude_fields: Set of field names to exclude from update
        """
        exclude_fields = exclude_fields or {'id', 'created_at'}
        
        for key, value in data.items():
            if hasattr(self, key) and key not in exclude_fields:
                setattr(self, key, value)
        
        # Update the updated_at timestamp
        self.updated_at = datetime.now(timezone.utc)
    
    @property
    def is_active(self) -> bool:
        """Check if record is active (not soft deleted)"""
        return not getattr(self, 'is_deleted', False)
    
    @property
    def age_in_days(self) -> int:
        """Get age of record in days"""
        if self.created_at:
            delta = datetime.now(timezone.utc) - self.created_at.replace(tzinfo=timezone.utc)
            return delta.days
        return 0