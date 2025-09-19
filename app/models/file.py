#!/usr/bin/env python3
"""
File model for attachment management and AI processing
"""

import enum
from datetime import datetime, timezone
from typing import Optional
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


class File(BaseModel):
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
    
    # Relationships - removed ticket_id, files now referenced by ticket.file_ids array
    uploaded_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="User who uploaded the file"
    )
    
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
        comment="Organization that owns this file"
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
    
    # AI Analysis Results - Simplified Structure
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
    
    # Unified Content Extraction (NEW APPROACH) - as specified in PRP
    extracted_context = Column(
        JSON,
        nullable=True,
        comment="Unified JSON structure for all content types (document, image, audio)"
    )
    
    extraction_method = Column(
        String(50),
        nullable=True,
        comment="Method used for extraction (document_parser, vision_ocr, speech_transcription)"
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
    uploader = relationship(
        "User",
        back_populates="uploaded_files"
    )
    
    organization = relationship(
        "Organization",
        back_populates="files"
    )
    
    def __repr__(self):
        return f"<File(id={self.id}, filename={self.filename}, status={self.status})>"
    
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
            self.extracted_context or
            self.content_summary
        )
    
    def start_processing(self):
        """Mark file as processing started"""
        self.status = FileStatus.PROCESSING
        self.processing_started_at = datetime.now(timezone.utc)
        # Handle None value for processing_attempts (in tests)
        if self.processing_attempts is None:
            self.processing_attempts = 1
        else:
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
        """Get combined content from extracted_context JSON structure"""
        content_parts = []
        
        if self.extracted_context:
            context = self.extracted_context
            
            # Document content
            if "document" in context:
                doc = context["document"]
                doc_text = ""
                for page in doc.get("pages", []):
                    doc_text += page.get("text", "")
                if doc_text:
                    content_parts.append(f"Document Content:\n{doc_text}")
            
            # Image content
            if "image" in context:
                img = context["image"]
                if img.get("description"):
                    content_parts.append(f"Image Description:\n{img['description']}")
                
                # Text found in image
                text_regions = img.get("text_regions", [])
                if text_regions:
                    image_text = " ".join([region.get("text", "") for region in text_regions])
                    if image_text:
                        content_parts.append(f"Text in Image:\n{image_text}")
            
            # Audio content
            if "audio" in context:
                audio = context["audio"]
                transcription = audio.get("transcription", {}).get("text", "")
                if transcription:
                    content_parts.append(f"Audio Transcription:\n{transcription}")
        
        if self.content_summary:
            content_parts.append(f"AI Summary:\n{self.content_summary}")
        
        return "\n\n---\n\n".join(content_parts)
    
    def get_text_for_ai_model(self, max_length: Optional[int] = 2000) -> str:
        """
        Extract text content optimized for AI model consumption with token limits.
        
        Uses priority order:
        1. content_summary (always included - concise AI summary)
        2. extracted_context structured data (rich content)
        3. Formatted content based on file type
        
        Args:
            max_length: Maximum character length to return (approximate token limit)
            
        Returns:
            str: Formatted text content ready for AI processing
        """
        content_parts = []
        
        # Priority 1: Always include content summary (concise and most important)
        if self.content_summary:
            content_parts.append(f"Summary: {self.content_summary}")
        
        # Priority 2: Add structured content based on file type and extracted_context
        if self.extracted_context:
            context = self.extracted_context
            
            # Text-based files (documents, text, code, spreadsheets)
            if self.is_text_file and "document" in context:
                doc = context["document"]
                doc_text = ""
                for page in doc.get("pages", []):
                    page_text = page.get("text", "")
                    if page_text:
                        doc_text += page_text + "\n"
                
                if doc_text.strip():
                    # Format based on file type
                    if self.file_type == FileType.SPREADSHEET:
                        content_parts.append(f"Table Data:\n{self._format_spreadsheet_content(doc_text[:1000])}")
                    elif self.file_type == FileType.CODE:
                        content_parts.append(f"Code Content:\n```\n{doc_text[:800]}\n```")
                    else:
                        content_parts.append(f"Document Text:\n{doc_text[:1000]}")
            
            # Image files with OCR
            elif self.is_image_file and "image" in context:
                img = context["image"]
                
                # Include image description
                if img.get("description"):
                    content_parts.append(f"Visual Description: {img['description']}")
                
                # Include extracted text from OCR
                text_regions = img.get("text_regions", [])
                if text_regions:
                    ocr_text = " ".join([region.get("text", "") for region in text_regions])
                    if ocr_text.strip():
                        content_parts.append(f"Text in Image: {ocr_text[:600]}")
            
            # Audio/Video files with transcription
            elif self.is_media_file and "audio" in context:
                audio = context["audio"]
                transcription = audio.get("transcription", {}).get("text", "")
                if transcription:
                    content_parts.append(f"Transcription: {transcription[:800]}")
        
        # Combine all content
        full_content = "\n\n".join(content_parts)
        
        # Apply length limits with intelligent truncation
        if max_length and len(full_content) > max_length:
            # Always keep the summary, truncate other content
            if self.content_summary and len(content_parts) > 1:
                summary = content_parts[0]
                remaining_length = max_length - len(summary) - 20  # Buffer for separators
                
                if remaining_length > 100:  # Only include additional content if there's meaningful space
                    additional_content = "\n\n".join(content_parts[1:])
                    if len(additional_content) > remaining_length:
                        additional_content = additional_content[:remaining_length] + "... [truncated]"
                    full_content = f"{summary}\n\n{additional_content}"
                else:
                    full_content = summary
            else:
                # No summary, just truncate the content
                full_content = full_content[:max_length] + "... [truncated]"
        
        return full_content or f"File: {self.filename} ({self.file_type.value})"
    
    def _format_spreadsheet_content(self, content: str) -> str:
        """Format spreadsheet content for better AI consumption"""
        lines = content.strip().split('\n')
        if len(lines) <= 1:
            return content
        
        # Simple CSV-like formatting for AI
        formatted_lines = []
        for i, line in enumerate(lines[:10]):  # Limit to first 10 rows
            if i == 0:
                formatted_lines.append(f"Headers: {line}")
            else:
                formatted_lines.append(f"Row {i}: {line}")
        
        if len(lines) > 10:
            formatted_lines.append(f"... ({len(lines) - 10} more rows)")
        
        return "\n".join(formatted_lines)
    
    def can_be_deleted(self) -> bool:
        """Check if file can be safely deleted"""
        # Don't delete files that are still processing or recently uploaded
        if self.status == FileStatus.PROCESSING:
            return False
        
        # Files are now referenced by ticket.file_ids arrays
        # Additional validation can be added here if needed
        
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