#!/usr/bin/env python3
"""
File schemas for API validation and serialization
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import Field, field_validator
from enum import Enum

from app.schemas.base import BaseSchema, BaseCreate, BaseUpdate, BaseResponse


class FileStatusSchema(str, Enum):
    """File processing status enum schema"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    QUARANTINED = "quarantined"
    DELETED = "deleted"


class FileTypeSchema(str, Enum):
    """File type enum schema"""
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


# Request schemas
class FileUploadRequest(BaseCreate):
    """Schema for file upload request"""
    filename: str = Field(max_length=255, description="Original filename")
    mime_type: str = Field(description="MIME type of the file")
    file_size: int = Field(gt=0, description="File size in bytes")
    ticket_id: Optional[UUID] = Field(None, description="Associated ticket ID")
    file_type: Optional[FileTypeSchema] = Field(None, description="File type category")
    tags: Optional[List[str]] = Field(None, description="User-defined tags")
    description: Optional[str] = Field(None, description="File description")
    is_public: bool = Field(False, description="Whether file should be publicly accessible")
    retention_days: Optional[int] = Field(None, ge=1, le=3650, description="Days to retain file")
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        if not v.strip():
            raise ValueError('Filename cannot be empty')
        # Basic filename validation
        if any(char in v for char in '<>:"|?*'):
            raise ValueError('Filename contains invalid characters')
        return v.strip()
    
    @field_validator('file_size')
    @classmethod
    def validate_file_size(cls, v):
        # 100MB limit
        if v > 100 * 1024 * 1024:
            raise ValueError('File size cannot exceed 100MB')
        return v


class FileUpdateRequest(BaseUpdate):
    """Schema for updating file metadata"""
    filename: Optional[str] = Field(None, max_length=255, description="Filename")
    tags: Optional[List[str]] = Field(None, description="File tags")
    description: Optional[str] = Field(None, description="File description")
    is_public: Optional[bool] = Field(None, description="Public access")
    retention_days: Optional[int] = Field(None, ge=1, le=3650, description="Retention period")
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Filename cannot be empty')
        if v and any(char in v for char in '<>:"|?*'):
            raise ValueError('Filename contains invalid characters')
        return v.strip() if v else None


class FileProcessingRequest(BaseSchema):
    """Schema for requesting file processing"""
    processing_types: List[str] = Field(
        default=["auto"],
        description="Types of processing to perform"
    )
    force_reprocess: bool = Field(False, description="Force reprocessing if already processed")
    analysis_options: Optional[Dict[str, Any]] = Field(None, description="Processing options")
    
    @field_validator('processing_types')
    @classmethod
    def validate_processing_types(cls, v):
        valid_types = {"auto", "text_extraction", "transcription", "image_analysis", "virus_scan"}
        if not all(t in valid_types for t in v):
            raise ValueError(f'Invalid processing types. Must be one of: {valid_types}')
        return v


class FileAnalysisRequest(BaseSchema):
    """Schema for AI analysis of file content"""
    analysis_types: List[str] = Field(
        default=["summary", "classification"],
        description="Types of analysis to perform"
    )
    context: Optional[str] = Field(None, description="Additional context for analysis")
    extract_metadata: bool = Field(True, description="Whether to extract metadata")
    
    @field_validator('analysis_types')
    @classmethod
    def validate_analysis_types(cls, v):
        valid_types = {"summary", "classification", "sentiment", "topics", "language_detection"}
        if not all(t in valid_types for t in v):
            raise ValueError(f'Invalid analysis types. Must be one of: {valid_types}')
        return v


class FileBulkProcessRequest(BaseSchema):
    """Schema for bulk file processing"""
    file_ids: List[UUID] = Field(description="List of file IDs to process")
    processing_types: List[str] = Field(description="Processing types to apply")
    force_reprocess: bool = Field(False, description="Force reprocessing")
    
    @field_validator('file_ids')
    @classmethod
    def validate_file_ids(cls, v):
        if len(v) > 50:  # Limit bulk operations
            raise ValueError('Cannot process more than 50 files at once')
        return v


# Response schemas
class FileUserInfo(BaseSchema):
    """User information for file responses"""
    id: UUID = Field(description="User ID")
    email: str = Field(description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    display_name: str = Field(description="User display name")


class FileTicketInfo(BaseSchema):
    """Ticket information for file responses"""
    id: UUID = Field(description="Ticket ID")
    title: str = Field(description="Ticket title")
    status: str = Field(description="Ticket status")


class FileProcessingResults(BaseSchema):
    """File processing results"""
    text_extraction: Optional[Dict[str, Any]] = Field(None, description="Text extraction results")
    transcription: Optional[Dict[str, Any]] = Field(None, description="Audio transcription results")
    image_analysis: Optional[Dict[str, Any]] = Field(None, description="Image analysis results")
    virus_scan: Optional[Dict[str, Any]] = Field(None, description="Virus scan results")
    ai_analysis: Optional[Dict[str, Any]] = Field(None, description="AI analysis results")


class FileBaseResponse(BaseResponse):
    """Base file response with common fields"""
    filename: str = Field(description="Original filename")
    file_extension: str = Field(description="File extension")
    mime_type: str = Field(description="MIME type")
    file_size: int = Field(description="File size in bytes")
    display_size: str = Field(description="Human-readable file size")
    file_type: FileTypeSchema = Field(description="File type category")
    status: FileStatusSchema = Field(description="Processing status")
    file_hash: str = Field(description="File content hash")
    uploader: FileUserInfo = Field(description="User who uploaded the file")


class FileListResponse(FileBaseResponse):
    """File information for list views"""
    ticket: Optional[FileTicketInfo] = Field(None, description="Associated ticket")
    is_processed: bool = Field(description="Whether processing is complete")
    has_content: bool = Field(description="Whether file has extracted content")
    download_count: int = Field(description="Number of downloads")
    last_accessed_at: Optional[datetime] = Field(None, description="Last access time")
    tags: Optional[List[str]] = Field(None, description="File tags")
    is_expired: bool = Field(description="Whether file has expired")


class FileDetailResponse(FileBaseResponse):
    """Detailed file information"""
    file_path: str = Field(description="Server file path")
    ticket: Optional[FileTicketInfo] = Field(None, description="Associated ticket")
    description: Optional[str] = Field(None, description="File description")
    tags: Optional[List[str]] = Field(None, description="File tags")
    
    # Processing metadata
    processing_started_at: Optional[datetime] = Field(None, description="Processing start time")
    processing_completed_at: Optional[datetime] = Field(None, description="Processing completion time")
    processing_time_seconds: Optional[int] = Field(None, description="Processing time in seconds")
    processing_time_minutes: Optional[float] = Field(None, description="Processing time in minutes")
    processing_attempts: int = Field(description="Number of processing attempts")
    processing_error: Optional[str] = Field(None, description="Processing error message")
    
    # AI Analysis metadata
    ai_analysis_version: Optional[str] = Field(None, description="AI analysis version")
    ai_confidence_score: Optional[float] = Field(None, description="AI confidence score")
    
    # Content extraction
    extracted_text: Optional[str] = Field(None, description="Extracted text content")
    text_extraction_method: Optional[str] = Field(None, description="Text extraction method")
    text_extraction_confidence: Optional[float] = Field(None, description="Text extraction confidence")
    
    # Audio transcription
    transcription_text: Optional[str] = Field(None, description="Transcribed audio content")
    transcription_language: Optional[str] = Field(None, description="Detected language")
    transcription_confidence: Optional[float] = Field(None, description="Transcription confidence")
    transcription_duration_seconds: Optional[int] = Field(None, description="Audio duration")
    
    # Image analysis
    image_description: Optional[str] = Field(None, description="AI image description")
    detected_objects: Optional[List[Dict[str, Any]]] = Field(None, description="Detected objects")
    image_text_regions: Optional[List[Dict[str, Any]]] = Field(None, description="Text regions in image")
    image_metadata: Optional[Dict[str, Any]] = Field(None, description="Image metadata")
    
    # Content analysis
    content_summary: Optional[str] = Field(None, description="AI content summary")
    key_topics: Optional[List[str]] = Field(None, description="Key topics identified")
    sentiment_analysis: Optional[Dict[str, Any]] = Field(None, description="Sentiment analysis")
    language_detection: Optional[str] = Field(None, description="Detected language")
    
    # Security
    virus_scan_result: Optional[str] = Field(None, description="Virus scan result")
    virus_scan_at: Optional[datetime] = Field(None, description="Virus scan timestamp")
    virus_details: Optional[str] = Field(None, description="Virus scan details")
    
    # Access and lifecycle
    is_public: bool = Field(description="Whether file is public")
    access_permissions: Optional[Dict[str, Any]] = Field(None, description="Access permissions")
    download_count: int = Field(description="Download count")
    last_accessed_at: Optional[datetime] = Field(None, description="Last access time")
    retention_policy: Optional[str] = Field(None, description="Retention policy")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    archived_at: Optional[datetime] = Field(None, description="Archive date")
    
    # External references
    external_references: Optional[Dict[str, Any]] = Field(None, description="External references")
    file_quality_score: Optional[float] = Field(None, description="Quality assessment score")
    
    # Computed properties
    is_processed: bool = Field(description="Whether processing is complete")
    is_text_file: bool = Field(description="Whether file contains text")
    is_media_file: bool = Field(description="Whether file is media")
    is_image_file: bool = Field(description="Whether file is an image")
    is_expired: bool = Field(description="Whether file has expired")
    has_content: bool = Field(description="Whether file has extracted content")
    can_be_deleted: bool = Field(description="Whether file can be deleted")


class FileContentResponse(BaseSchema):
    """File content response (for content extraction)"""
    file_id: UUID = Field(description="File ID")
    content_type: str = Field(description="Type of content extracted")
    content: str = Field(description="Extracted content")
    confidence_score: Optional[float] = Field(None, description="Extraction confidence")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Content metadata")


class FileProcessingResponse(BaseSchema):
    """File processing status response"""
    file_id: UUID = Field(description="File ID")
    status: FileStatusSchema = Field(description="Processing status")
    progress_percentage: Optional[int] = Field(None, description="Processing progress")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    processing_results: Optional[FileProcessingResults] = Field(None, description="Processing results")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class FileAnalysisResponse(BaseSchema):
    """File AI analysis response"""
    file_id: UUID = Field(description="File ID")
    analysis_type: str = Field(description="Type of analysis performed")
    results: Dict[str, Any] = Field(description="Analysis results")
    confidence_score: float = Field(description="Analysis confidence")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Analysis metadata")
    suggestions: Optional[List[str]] = Field(None, description="AI suggestions")


class FileStatsResponse(BaseSchema):
    """File statistics response"""
    total_files: int = Field(description="Total number of files")
    processed_files: int = Field(description="Number of processed files")
    pending_files: int = Field(description="Number of pending files")
    failed_files: int = Field(description="Number of failed files")
    total_size_bytes: int = Field(description="Total file size in bytes")
    total_size_display: str = Field(description="Human-readable total size")
    file_type_distribution: Dict[str, int] = Field(description="Files by type")
    status_distribution: Dict[str, int] = Field(description="Files by status")
    avg_processing_time_seconds: Optional[float] = Field(None, description="Average processing time")
    virus_scan_stats: Optional[Dict[str, int]] = Field(None, description="Virus scan statistics")


class FileDownloadResponse(BaseSchema):
    """File download response"""
    file_id: UUID = Field(description="File ID")
    filename: str = Field(description="File name")
    mime_type: str = Field(description="MIME type")
    file_size: int = Field(description="File size")
    download_url: str = Field(description="Download URL")
    expires_at: datetime = Field(description="URL expiration time")


# Search and filter schemas
class FileSearchParams(BaseSchema):
    """File search parameters"""
    q: Optional[str] = Field(None, description="Search query (filename, content)")
    file_type: Optional[List[FileTypeSchema]] = Field(None, description="Filter by file type")
    status: Optional[List[FileStatusSchema]] = Field(None, description="Filter by status")
    mime_type: Optional[str] = Field(None, description="Filter by MIME type")
    uploaded_by_id: Optional[UUID] = Field(None, description="Filter by uploader")
    ticket_id: Optional[UUID] = Field(None, description="Filter by ticket")
    has_content: Optional[bool] = Field(None, description="Filter by content extraction")
    is_processed: Optional[bool] = Field(None, description="Filter by processing status")
    is_public: Optional[bool] = Field(None, description="Filter by public access")
    is_expired: Optional[bool] = Field(None, description="Filter by expiration")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    file_size_min: Optional[int] = Field(None, ge=0, description="Minimum file size")
    file_size_max: Optional[int] = Field(None, ge=0, description="Maximum file size")
    created_after: Optional[datetime] = Field(None, description="Uploaded after date")
    created_before: Optional[datetime] = Field(None, description="Uploaded before date")
    processed_after: Optional[datetime] = Field(None, description="Processed after date")
    processed_before: Optional[datetime] = Field(None, description="Processed before date")
    virus_scan_result: Optional[str] = Field(None, description="Filter by virus scan result")
    language: Optional[str] = Field(None, description="Filter by detected language")


class FileSortParams(BaseSchema):
    """File sorting parameters"""
    sort_by: str = Field(
        "created_at",
        description="Sort field",
        pattern="^(created_at|updated_at|filename|file_size|download_count|processing_completed_at)$"
    )
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


# Bulk operation schemas
class FileBulkDeleteRequest(BaseSchema):
    """Schema for bulk file deletion"""
    file_ids: List[UUID] = Field(description="List of file IDs to delete")
    reason: Optional[str] = Field(None, description="Reason for deletion")
    force_delete: bool = Field(False, description="Force delete even if referenced")


class FileBulkUpdateRequest(BaseSchema):
    """Schema for bulk file updates"""
    file_ids: List[UUID] = Field(description="List of file IDs to update")
    updates: FileUpdateRequest = Field(description="Updates to apply")
    reason: Optional[str] = Field(None, description="Reason for bulk update")


class FileBulkTagRequest(BaseSchema):
    """Schema for bulk file tagging"""
    file_ids: List[UUID] = Field(description="List of file IDs")
    action: str = Field(description="Action: add, remove, or replace", pattern="^(add|remove|replace)$")
    tags: List[str] = Field(description="Tags to add/remove/replace")


# Upload and processing schemas
class FileUploadResponse(BaseSchema):
    """File upload response"""
    file_id: UUID = Field(description="Uploaded file ID")
    filename: str = Field(description="File name")
    file_size: int = Field(description="File size")
    status: FileStatusSchema = Field(description="Initial status")
    upload_url: Optional[str] = Field(None, description="Upload URL if using presigned uploads")
    processing_started: bool = Field(description="Whether processing has started")


class FileUploadUrlRequest(BaseSchema):
    """Request for presigned upload URL"""
    filename: str = Field(description="File name")
    mime_type: str = Field(description="MIME type")
    file_size: int = Field(description="File size")
    ticket_id: Optional[UUID] = Field(None, description="Associated ticket")


class FileUploadUrlResponse(BaseSchema):
    """Presigned upload URL response"""
    upload_url: str = Field(description="Presigned upload URL")
    file_id: UUID = Field(description="File ID for tracking")
    expires_at: datetime = Field(description="URL expiration time")
    required_headers: Optional[Dict[str, str]] = Field(None, description="Required HTTP headers")


# Error schemas
class FileErrorResponse(BaseSchema):
    """File-specific error response"""
    file_id: Optional[UUID] = Field(None, description="File ID if applicable")
    error_code: str = Field(description="Error code")
    error_message: str = Field(description="Error message")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


# New schemas for PRP implementation with extracted_context JSON structure
class FileUploadResponse(BaseSchema):
    """Response for file upload according to PRP specs"""
    id: UUID = Field(description="Unique file identifier")
    filename: str = Field(description="Original filename")
    file_size: int = Field(description="File size in bytes")
    mime_type: str = Field(description="MIME type of the file")
    file_type: FileTypeSchema = Field(description="Detected file type")
    status: FileStatusSchema = Field(description="Current processing status")
    url: str = Field(description="Fully qualified URL with filename for file content")
    processing_required: bool = Field(description="Whether file needs AI processing")


class FileResponse(BaseSchema):
    """Unified file response with extracted_context support"""
    id: UUID = Field(description="Unique file identifier")
    filename: str = Field(description="Original filename")
    file_size: int = Field(description="File size in bytes")
    mime_type: str = Field(description="MIME type")
    file_type: FileTypeSchema = Field(description="File type category")
    status: FileStatusSchema = Field(description="Processing status")
    url: str = Field(description="Fully qualified URL with filename for file content")
    extraction_method: Optional[str] = Field(None, description="Method used for content extraction")
    content_summary: Optional[str] = Field(None, description="AI-generated content summary")
    extracted_context: Optional[Dict[str, Any]] = Field(None, description="Unified extracted content JSON")
    language_detection: Optional[str] = Field(None, description="Detected language")
    processing_started_at: Optional[datetime] = Field(None, description="Processing start time")
    processing_completed_at: Optional[datetime] = Field(None, description="Processing completion time")
    processing_error: Optional[str] = Field(None, description="Processing error message")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class FileListResponse(BaseSchema):
    """Response for file list endpoint"""
    files: List[FileResponse] = Field(description="List of files")
    total: int = Field(description="Total number of files")
    skip: int = Field(description="Number of files skipped")
    limit: int = Field(description="Maximum number of files returned")


class FileProcessingStatusResponse(BaseSchema):
    """Detailed processing status response"""
    id: UUID = Field(description="File identifier") 
    filename: str = Field(description="Filename")
    status: str = Field(description="Processing status")
    extraction_method: Optional[str] = Field(None, description="Extraction method used")
    processing_started_at: Optional[datetime] = Field(None, description="Processing start time")
    processing_completed_at: Optional[datetime] = Field(None, description="Processing completion time")
    processing_error: Optional[str] = Field(None, description="Processing error message")
    has_content: bool = Field(description="Whether file has extracted content")
    content_summary: Optional[str] = Field(None, description="Content summary")
    language_detection: Optional[str] = Field(None, description="Detected language")