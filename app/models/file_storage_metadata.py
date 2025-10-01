#!/usr/bin/env python3
"""
File Storage Metadata model for tracking files across storage backends
"""

from sqlalchemy import BigInteger, Column, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class FileStorageMetadata(BaseModel):
    """
    Generic file storage metadata for tracking files across different storage backends.
    This model stores information about any file (avatars, attachments, etc.) in the system.
    """
    
    __tablename__ = "file_storage_metadata"
    
    # Storage information
    storage_key = Column(
        String(500),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique storage key/path for the file across all backends"
    )
    
    # File information
    original_filename = Column(
        String(255),
        nullable=False,
        comment="Original filename when uploaded"
    )
    
    content_type = Column(
        String(100),
        nullable=False,
        index=True,
        comment="MIME type of the file"
    )
    
    file_size = Column(
        BigInteger,
        nullable=False,
        comment="File size in bytes"
    )
    
    # Storage backend information
    storage_backend = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Storage backend used (local, s3, etc.)"
    )
    
    # Additional metadata
    file_metadata = Column(
        JSONB,
        nullable=True,
        comment="Additional file metadata and custom fields"
    )
    
    # Table configuration
    __table_args__ = (
        Index('ix_file_storage_metadata_content_type', 'content_type'),
        Index('ix_file_storage_metadata_created_at', 'created_at'),
        {'comment': 'Generic file storage metadata for all file types across storage backends'}
    )
    
    # Relationships
    avatar_variants = relationship(
        "AvatarVariant",
        back_populates="base_file",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<FileStorageMetadata(id={self.id}, storage_key={self.storage_key}, content_type={self.content_type})>"
    
    @property
    def is_image(self) -> bool:
        """Check if file is an image"""
        return self.content_type.startswith('image/')
    
    @property
    def is_avatar(self) -> bool:
        """Check if this file is used as an avatar (has avatar variants)"""
        return len(self.avatar_variants) > 0 if self.avatar_variants else False
    
    @property
    def display_size(self) -> str:
        """Get human-readable file size"""
        size = self.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        data = super().to_dict()
        data['is_image'] = self.is_image
        data['is_avatar'] = self.is_avatar
        data['display_size'] = self.display_size
        return data


class AvatarVariant(BaseModel):
    """
    Avatar size variants tracking different sizes of avatar images.
    Links to FileStorageMetadata for the base file information.
    """
    
    __tablename__ = "avatar_variants"
    
    # Reference to base file
    base_file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("file_storage_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="References file_storage_metadata for the original file"
    )
    
    # Entity information
    entity_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Type of entity (user, agent)"
    )
    
    entity_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="ID of the entity (user_id or agent_id)"
    )
    
    # Size variant information
    size_variant = Column(
        String(20),
        nullable=False,
        comment="Size variant (original, small, medium, large)"
    )
    
    storage_key = Column(
        String(500),
        nullable=False,
        unique=True,
        index=True,
        comment="Storage key for this specific size variant"
    )
    
    # Table configuration
    __table_args__ = (
        Index('ix_avatar_variants_entity', 'entity_type', 'entity_id'),
        Index('ix_avatar_variants_entity_size', 'entity_id', 'size_variant'),
        {'comment': 'Avatar size variants for different entity types'}
    )
    
    # Relationships
    base_file = relationship(
        "FileStorageMetadata",
        back_populates="avatar_variants"
    )
    
    def __repr__(self):
        return f"<AvatarVariant(id={self.id}, entity_type={self.entity_type}, entity_id={self.entity_id}, size={self.size_variant})>"
    
    @property
    def is_thumbnail(self) -> bool:
        """Check if this is a thumbnail (not original)"""
        return self.size_variant != "original"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        data = super().to_dict()
        data['is_thumbnail'] = self.is_thumbnail
        return data