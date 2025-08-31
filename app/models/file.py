#!/usr/bin/env python3
"""
File model for attachment management and AI processing
"""

import enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum as SQLEnum, JSON, ForeignKey, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class FileStatus(enum.Enum):
    """File processing status"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    QUARANTINED = "quarantined"
    DELETED = "deleted"


class FileType(enum.Enum):
    """Supported file types for processing"""
    DOCUMENT = "document"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    ARCHIVE = "archive"
    TEXT = "text"
    CODE = "code"
    OTHER = "other"


class DBFile(BaseModel):
    """
    File attachment model with AI processing capabilities.
    Supports transcription, OCR, and content analysis.
    """
    
    __tablename__ = "files"
    
    # Basic file information
    filename = Column(
        String(255),
        nullable=False,
        comment="Original filename"
    )
    
    file_path = Column(
        String(500),
        nullable=False,
        unique=True,
        index=True,
        comment="Server file path"
    )
    
    mime_type = Column(
        String(100),
        nullable=False,
        comment="MIME type of the file"
    )
    
    file_size = Column(
        BigInteger,
        nullable=False,
        comment="File size in bytes"
    )
    
    file_hash = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="SHA-256 hash of file content"
    )
    
    # File classification
    file_type = Column(
        SQLEnum(FileType),
        default=FileType.OTHER,
        nullable=False,
        index=True,
        comment="Detected file type category"
    )
    
    status = Column(
        SQLEnum(FileStatus),
        default=FileStatus.UPLOADED,
        nullable=False,
        index=True,
        comment="Current processing status"
    )
    
    # Relationships
    ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id"),
        nullable=True,
        index=True,
        comment="Associated ticket ID"
    )
    
    uploaded_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="User who uploaded the file"
    )
    
    # Processing metadata
    processing_started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When processing started"
    )
    
    processing_completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When processing completed"
    )
    
    processing_error = Column(
        Text,
        nullable=True,
        comment="Error message if processing failed"
    )
    
    processing_attempts = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of processing attempts"
    )
    
    # AI Analysis Results
    ai_analysis_version = Column(
        String(20),
        nullable=True,
        comment="Version of AI analysis used"
    )
    
    ai_confidence_score = Column(
        String(10),
        nullable=True,
        comment="AI confidence in analysis (0-1)"
    )
    
    # Text extraction (OCR/document parsing)
    extracted_text = Column(
        Text,
        nullable=True,
        comment="Text extracted from file"
    )
    
    text_extraction_method = Column(
        String(50),
        nullable=True,
        comment="Method used for text extraction (ocr, parsing, etc.)"
    )
    
    text_extraction_confidence = Column(
        String(10),
        nullable=True,
        comment="Confidence score for text extraction"
    )
    
    # Audio transcription
    transcription_text = Column(
        Text,
        nullable=True,
        comment="Transcribed audio content"
    )
    
    transcription_language = Column(
        String(10),
        nullable=True,
        comment="Detected language of transcription"
    )
    
    transcription_confidence = Column(
        String(10),
        nullable=True,
        comment="Transcription confidence score"
    )
    
    transcription_duration_seconds = Column(
        Integer,
        nullable=True,
        comment="Duration of audio file in seconds"
    )
    
    # Image analysis
    image_description = Column(
        Text,
        nullable=True,
        comment="AI-generated description of image content"
    )
    
    detected_objects = Column(
        JSON,
        nullable=True,
        comment="List of objects detected in image"
    )
    
    image_text_regions = Column(
        JSON,
        nullable=True,
        comment="Text regions found in image with coordinates"
    )
    
    image_metadata = Column(
        JSON,
        nullable=True,
        comment="EXIF and other image metadata"
    )
    
    # Content analysis
    content_summary = Column(
        Text,
        nullable=True,
        comment="AI-generated summary of file content"
    )
    
    key_topics = Column(
        JSON,
        nullable=True,
        comment="Key topics identified in content"
    )
    
    sentiment_analysis = Column(
        JSON,
        nullable=True,
        comment="Sentiment analysis results"
    )
    
    language_detection = Column(
        String(10),
        nullable=True,
        comment="Detected primary language"
    )
    
    # Security scanning
    virus_scan_result = Column(
        String(20),
        nullable=True,
        comment="Virus scan result (clean, infected, unknown)"
    )
    
    virus_scan_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When virus scan was performed"
    )
    
    virus_details = Column(
        Text,
        nullable=True,
        comment="Details if virus/malware detected"
    )
    
    # Access control
    is_public = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether file is publicly accessible"
    )
    
    access_permissions = Column(
        JSON,
        nullable=True,
        comment="Specific access permissions for users/roles"
    )
    
    download_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of times file has been downloaded"
    )
    
    last_accessed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last access timestamp"
    )
    
    # Retention and lifecycle
    retention_policy = Column(
        String(50),
        nullable=True,
        comment="Retention policy name"
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When file should be automatically deleted"
    )
    
    archived_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When file was archived"
    )
    
    # Integration metadata
    external_references = Column(
        JSON,
        nullable=True,
        comment="References to file in external systems"
    )
    
    tags = Column(
        JSON,
        nullable=True,
        comment="User and AI-generated tags"
    )
    
    # Performance metrics
    processing_time_seconds = Column(
        Integer,
        nullable=True,
        comment="Total processing time in seconds"
    )
    
    file_quality_score = Column(
        String(10),
        nullable=True,
        comment="Quality assessment score (0-1)"
    )
    
    # Relationships
    ticket = relationship(
        "DBTicket",
        back_populates="files"
    )
    
    uploader = relationship(
        "DBUser",
        back_populates="uploaded_files"
    )
    
    def __repr__(self):
        return f"<DBFile(id={self.id}, filename={self.filename}, status={self.status})>"
    
    @property
    def display_size(self) -> str:
        """Get human-readable file size"""
        if not self.file_size:
            return "Unknown"
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    @property
    def file_extension(self) -> str:
        """Get file extension from filename"""
        if '.' in self.filename:
            return self.filename.rsplit('.', 1)[-1].lower()
        return ""
    
    @property
    def is_processed(self) -> bool:
        """Check if file processing is complete"""
        return self.status == FileStatus.PROCESSED
    
    @property
    def is_text_file(self) -> bool:
        """Check if file contains extractable text"""
        return self.file_type in [
            FileType.DOCUMENT, FileType.TEXT, FileType.CODE,
            FileType.SPREADSHEET, FileType.PRESENTATION
        ]
    
    @property
    def is_media_file(self) -> bool:
        """Check if file is audio/video media"""
        return self.file_type in [FileType.AUDIO, FileType.VIDEO]
    
    @property
    def is_image_file(self) -> bool:
        """Check if file is an image"""
        return self.file_type == FileType.IMAGE
    
    @property
    def processing_time_minutes(self) -> Optional[float]:
        """Get processing time in minutes"""
        if self.processing_time_seconds:
            return self.processing_time_seconds / 60.0
        return None
    
    @property
    def is_expired(self) -> bool:
        """Check if file has expired"""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)
    
    @property
    def has_content(self) -> bool:
        """Check if file has extracted content"""
        return bool(
            self.extracted_text or 
            self.transcription_text or 
            self.image_description or
            self.content_summary
        )
    
    def start_processing(self):
        """Mark file as processing started"""
        self.status = FileStatus.PROCESSING
        self.processing_started_at = datetime.now(timezone.utc)
        self.processing_attempts += 1
    
    def complete_processing(self):
        """Mark file processing as completed"""
        self.status = FileStatus.PROCESSED
        self.processing_completed_at = datetime.now(timezone.utc)
        
        if self.processing_started_at:
            delta = self.processing_completed_at - self.processing_started_at.replace(tzinfo=timezone.utc)
            self.processing_time_seconds = int(delta.total_seconds())
    
    def fail_processing(self, error_message: str):
        """Mark file processing as failed"""
        self.status = FileStatus.FAILED
        self.processing_error = error_message
        self.processing_completed_at = datetime.now(timezone.utc)
    
    def quarantine(self, reason: str):
        """Quarantine file for security reasons"""
        self.status = FileStatus.QUARANTINED
        self.virus_details = reason
        self.virus_scan_at = datetime.now(timezone.utc)
    
    def record_download(self):
        """Record file download"""
        self.download_count += 1
        self.last_accessed_at = datetime.now(timezone.utc)
    
    def set_expiration(self, days: int):
        """Set file expiration date"""
        from datetime import timedelta
        self.expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    
    def get_all_content(self) -> str:
        """Get combined content from all extraction methods"""
        content_parts = []
        
        if self.extracted_text:
            content_parts.append(f"Extracted Text:\n{self.extracted_text}")
        
        if self.transcription_text:
            content_parts.append(f"Transcription:\n{self.transcription_text}")
        
        if self.image_description:
            content_parts.append(f"Image Description:\n{self.image_description}")
        
        if self.content_summary:
            content_parts.append(f"Content Summary:\n{self.content_summary}")
        
        return "\n\n---\n\n".join(content_parts)
    
    def can_be_deleted(self) -> bool:
        """Check if file can be safely deleted"""
        # Don't delete files that are still processing or recently uploaded
        if self.status == FileStatus.PROCESSING:
            return False
        
        # Check if file is referenced by active tickets
        if self.ticket and not self.ticket.is_deleted:
            return False
        
        return True
    
    def to_dict(self, include_content: bool = False, include_analysis: bool = True) -> dict:
        """
        Convert file to dictionary with optional content inclusion.
        
        Args:
            include_content: Include extracted content (can be large)
            include_analysis: Include AI analysis results
            
        Returns:
            dict: File data
        """
        data = super().to_dict()
        
        # Remove large content fields if not requested
        if not include_content:
            content_fields = [
                'extracted_text', 'transcription_text', 'image_description',
                'content_summary', 'processing_error'
            ]
            for field in content_fields:
                data.pop(field, None)
        
        # Remove analysis fields if not requested
        if not include_analysis:
            analysis_fields = [
                'ai_confidence_score', 'detected_objects', 'key_topics',
                'sentiment_analysis', 'image_text_regions'
            ]
            for field in analysis_fields:
                data.pop(field, None)
        
        # Add computed properties
        data['display_size'] = self.display_size
        data['file_extension'] = self.file_extension
        data['is_processed'] = self.is_processed
        data['is_expired'] = self.is_expired
        data['has_content'] = self.has_content
        data['processing_time_minutes'] = self.processing_time_minutes
        data['can_be_deleted'] = self.can_be_deleted()
        
        return data