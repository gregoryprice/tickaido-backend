#!/usr/bin/env python3
"""
File Service - Business logic for file management, processing, and analysis using unified storage
"""

import os
import uuid
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.models.file import File, FileStatus, FileType
from app.schemas.file import (
    FileUploadRequest,
    FileUpdateRequest,
    FileProcessingRequest,
    FileAnalysisRequest,
    FileProcessingResponse,
    FileAnalysisResponse,
    FileSearchParams,
    FileSortParams
)
from app.config.settings import get_settings
from app.services.storage.factory import get_storage_service


class DuplicateFileError(Exception):
    """Exception raised when attempting to upload a duplicate file"""
    def __init__(self, message: str, existing_file_id: UUID):
        super().__init__(message)
        self.existing_file_id = existing_file_id


class FileService:
    """Service class for file operations using unified storage"""
    
    def __init__(self):
        self.settings = get_settings()
        self.storage_service = get_storage_service()
        self.max_file_size = self.settings.max_file_size
        self.allowed_file_types = self.settings.allowed_file_types
        self.upload_directory = getattr(self.settings, 'upload_directory', '/tmp/uploads')
    
    async def upload_file(
        self,
        db: AsyncSession,
        file_request: FileUploadRequest,
        file_content: bytes,
        user_id: UUID
    ) -> File:
        """
        Upload a new file using unified storage
        
        Args:
            db: Database session
            file_request: File upload request data
            file_content: Raw file content
            user_id: ID of uploading user
            
        Returns:
            Created file record
        """
        # Validate file size
        if len(file_content) > self.max_file_size:
            raise ValueError(f"File size {len(file_content)} exceeds maximum allowed size {self.max_file_size}")
        
        # Validate file type
        if file_request.mime_type not in self.allowed_file_types:
            raise ValueError(f"File type {file_request.mime_type} not allowed")
        
        # Generate unique file ID and storage key
        file_id = uuid.uuid4()
        file_extension = Path(file_request.filename).suffix
        
        # Create storage key with date organization for better structure
        now = datetime.now()
        storage_key = f"attachments/{now.year}/{now.month:02d}/{file_id}{file_extension}"
        
        # Upload file using storage service
        file_url = await self.storage_service.upload_content(
            content=file_content,
            storage_key=storage_key,
            content_type=file_request.mime_type,
            metadata={
                "file_id": str(file_id),
                "user_id": str(user_id),
                "ticket_id": str(file_request.ticket_id) if file_request.ticket_id else None,
                "original_filename": file_request.filename,
                "file_size": str(len(file_content))
            }
        )
        
        # Calculate file hash
        import hashlib
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Create database record
        db_file = File(
            id=file_id,
            filename=file_request.filename,
            file_path=storage_key,  # Store storage key as file path
            mime_type=file_request.mime_type,
            file_size=len(file_content),
            file_hash=file_hash,
            file_type=file_request.file_type or self._detect_file_type(file_request.mime_type),
            status=FileStatus.UPLOADED,
            uploaded_by_id=user_id,
            ticket_id=file_request.ticket_id,
            processing_attempts=0,  # Initialize to 0
            is_public=file_request.is_public,
            download_count=0,  # Initialize to 0
            tags=file_request.tags or [],
            # Note: description and retention_days might not be in the File model
        )
        
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        
        return db_file
    
    async def get_file(
        self,
        db: AsyncSession,
        file_id: UUID,
        include_content: bool = False
    ) -> Optional[File]:
        """
        Get file by ID
        
        Args:
            db: Database session
            file_id: File ID
            include_content: Whether to load file content
            
        Returns:
            File record if found
        """
        query = select(File).where(
            and_(File.id == file_id, File.is_deleted == False)
        )
        
        if include_content:
            query = query.options(
                selectinload(File.uploader),
                selectinload(File.ticket)
            )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_files(
        self,
        db: AsyncSession,
        offset: int = 0,
        limit: int = 20,
        search_params: Optional[FileSearchParams] = None,
        sort_params: Optional[FileSortParams] = None,
        user_id: Optional[UUID] = None,
        ticket_id: Optional[UUID] = None
    ) -> Tuple[List[File], int]:
        """
        List files with filtering and pagination
        
        Args:
            db: Database session
            offset: Number of records to skip
            limit: Maximum number of records to return
            search_params: Search parameters
            sort_params: Sort parameters
            user_id: Filter by user ID
            ticket_id: Filter by ticket ID
            
        Returns:
            Tuple of (files list, total count)
        """
        # Base query
        query = select(File).where(File.is_deleted == False)
        count_query = select(func.count(File.id)).where(File.is_deleted == False)
        
        # Apply filters
        filters = []
        
        if user_id:
            filters.append(File.uploaded_by_id == user_id)
        
        if ticket_id:
            filters.append(File.ticket_id == ticket_id)
        
        if search_params:
            if search_params.filename:
                filters.append(File.filename.ilike(f"%{search_params.filename}%"))
            
            if search_params.mime_type:
                filters.append(File.mime_type == search_params.mime_type)
            
            if search_params.file_type:
                filters.append(File.file_type == search_params.file_type)
            
            if search_params.status:
                filters.append(File.status == search_params.status)
            
            if search_params.tags:
                # Filter by tags (PostgreSQL array contains)
                for tag in search_params.tags:
                    filters.append(File.tags.contains([tag]))
            
            if search_params.uploaded_after:
                filters.append(File.created_at >= search_params.uploaded_after)
            
            if search_params.uploaded_before:
                filters.append(File.created_at <= search_params.uploaded_before)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Apply sorting
        if sort_params:
            sort_field = getattr(File, sort_params.sort_by, File.created_at)
            if sort_params.sort_order == "desc":
                query = query.order_by(sort_field.desc())
            else:
                query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(File.created_at.desc())
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute queries
        files_result = await db.execute(query)
        count_result = await db.execute(count_query)
        
        files = files_result.scalars().all()
        total = count_result.scalar()
        
        return list(files), total
    
    async def update_file(
        self,
        db: AsyncSession,
        file_id: UUID,
        update_request: FileUpdateRequest,
        user_id: UUID
    ) -> Optional[File]:
        """
        Update file metadata
        
        Args:
            db: Database session
            file_id: File ID
            update_request: Update request data
            user_id: ID of updating user
            
        Returns:
            Updated file record if found
        """
        db_file = await self.get_file(db, file_id)
        if not db_file:
            return None
        
        # Check permissions (owner or admin)
        if db_file.uploaded_by_id != user_id:
            # TODO: Check if user is admin
            pass
        
        # Update fields
        update_data = update_request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(db_file, field):
                setattr(db_file, field, value)
        
        db_file.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(db_file)
        
        return db_file
    
    async def delete_file(
        self,
        db: AsyncSession,
        file_id: UUID,
        user_id: UUID,
        hard_delete: Optional[bool] = None
    ) -> bool:
        """
        Delete file with configurable hard/soft delete behavior
        
        Args:
            db: Database session
            file_id: File ID
            user_id: ID of deleting user
            hard_delete: Optional override for delete behavior. If None, uses settings.hard_delete_files
            
        Returns:
            True if deleted successfully
        """
        db_file = await self.get_file(db, file_id)
        if not db_file:
            return False
        
        # Check permissions
        if db_file.uploaded_by_id != user_id:
            # TODO: Check if user is admin
            pass
        
        # Determine delete strategy
        should_hard_delete = hard_delete if hard_delete is not None else self.settings.hard_delete_files
        
        if should_hard_delete:
            # Hard delete: remove from storage and database
            try:
                await self.storage_service.delete_file(db_file.file_path)
            except Exception:
                # Log error but continue
                pass
            
            # Delete from database
            await db.delete(db_file)
        else:
            # Soft delete: mark as deleted
            db_file.soft_delete()
            db_file.status = FileStatus.DELETED
        
        await db.commit()
        return True
    
    async def get_file_content(
        self,
        db: AsyncSession,
        file_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[bytes]:
        """
        Get file content from unified storage
        
        Args:
            db: Database session
            file_id: File ID
            user_id: Optional user ID for permission check
            
        Returns:
            File content if accessible
        """
        db_file = await self.get_file(db, file_id)
        if not db_file:
            return None
        
        # Check permissions
        if not db_file.is_public and user_id:
            if db_file.uploaded_by_id != user_id:
                # TODO: Check if user has access via ticket or is admin
                pass
        
        # Read file from storage service using file_path as key
        try:
            return await self.storage_service.download_file(db_file.file_path)
        except Exception:
            return None
    
    async def get_file_url(
        self,
        db: AsyncSession,
        file_id: UUID,
        user_id: Optional[UUID] = None,
        expires_in: Optional[int] = None
    ) -> Optional[str]:
        """
        Get file URL from unified storage
        
        Args:
            db: Database session
            file_id: File ID
            user_id: Optional user ID for permission check
            expires_in: URL expiration time in seconds (for signed URLs)
            
        Returns:
            File URL if accessible
        """
        db_file = await self.get_file(db, file_id)
        if not db_file:
            return None
        
        # Check permissions
        if not db_file.is_public and user_id:
            if db_file.uploaded_by_id != user_id:
                # TODO: Check if user has access via ticket or is admin
                pass
        
        # Get URL from storage service
        try:
            public = db_file.is_public and expires_in is None
            return await self.storage_service.get_file_url(
                db_file.file_path,
                expires_in=expires_in,
                public=public
            )
        except Exception:
            return None
    
    async def process_file(
        self,
        db: AsyncSession,
        file_id: UUID,
        processing_request: FileProcessingRequest,
        user_id: UUID
    ) -> Optional[FileProcessingResponse]:
        """
        Process file (extract text, analyze, etc.)
        
        Args:
            db: Database session
            file_id: File ID
            processing_request: Processing request data
            user_id: ID of requesting user
            
        Returns:
            Processing results if successful
        """
        db_file = await self.get_file(db, file_id)
        if not db_file:
            return None
        
        # Update status to processing
        db_file.status = FileStatus.PROCESSING
        await db.commit()
        
        try:
            # Get file content
            content = await self.get_file_content(db, file_id, user_id)
            if not content:
                raise Exception("Cannot read file content")
            
            processing_results = {}
            
            # Text extraction
            if processing_request.extract_text:
                extracted_text = await self._extract_text(content, db_file.mime_type)
                processing_results["extracted_text"] = extracted_text
            
            # Metadata extraction
            if processing_request.extract_metadata:
                metadata = await self._extract_metadata(content, db_file.mime_type)
                processing_results["metadata"] = metadata
            
            # Content analysis
            if processing_request.analyze_content:
                analysis = await self._analyze_content(
                    content,
                    db_file.mime_type,
                    processing_results.get("extracted_text")
                )
                processing_results["analysis"] = analysis
            
            # Update file with processing results
            db_file.processing_results = processing_results
            db_file.status = FileStatus.PROCESSED
            await db.commit()
            
            return FileProcessingResponse(
                file_id=file_id,
                status="completed",
                results=processing_results,
                processed_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            # Update status to error
            db_file.status = FileStatus.ERROR
            db_file.processing_error = str(e)
            await db.commit()
            
            return FileProcessingResponse(
                file_id=file_id,
                status="error",
                error=str(e),
                processed_at=datetime.now(timezone.utc)
            )
    
    async def analyze_file(
        self,
        db: AsyncSession,
        file_id: UUID,
        analysis_request: FileAnalysisRequest,
        user_id: UUID
    ) -> Optional[FileAnalysisResponse]:
        """
        Perform AI analysis on file
        
        Args:
            db: Database session
            file_id: File ID
            analysis_request: Analysis request data
            user_id: ID of requesting user
            
        Returns:
            Analysis results if successful
        """
        db_file = await self.get_file(db, file_id)
        if not db_file:
            return None
        
        # Get processed content or process if needed
        if not db_file.processing_results:
            processing_request = FileProcessingRequest(
                extract_text=True,
                extract_metadata=True,
                analyze_content=False
            )
            await self.process_file(db, file_id, processing_request, user_id)
            await db.refresh(db_file)
        
        try:
            analysis_results = {}
            
            extracted_text = db_file.processing_results.get("extracted_text", "")
            
            # Content categorization
            if analysis_request.categorize_content:
                category = await self._categorize_content(extracted_text, db_file.filename)
                analysis_results["category"] = category
            
            # Sentiment analysis
            if analysis_request.analyze_sentiment:
                sentiment = await self._analyze_sentiment(extracted_text)
                analysis_results["sentiment"] = sentiment
            
            # Entity extraction
            if analysis_request.extract_entities:
                entities = await self._extract_entities(extracted_text)
                analysis_results["entities"] = entities
            
            # Summary generation
            if analysis_request.generate_summary:
                summary = await self._generate_summary(extracted_text)
                analysis_results["summary"] = summary
            
            # Update file with analysis results
            db_file.analysis_results = analysis_results
            await db.commit()
            
            return FileAnalysisResponse(
                file_id=file_id,
                results=analysis_results,
                analyzed_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            return FileAnalysisResponse(
                file_id=file_id,
                error=str(e),
                analyzed_at=datetime.now(timezone.utc)
            )
    
    def _detect_file_type(self, mime_type: str) -> FileType:
        """Detect file type from MIME type"""
        if mime_type.startswith('image/'):
            return FileType.IMAGE
        elif mime_type.startswith('audio/'):
            return FileType.AUDIO
        elif mime_type.startswith('video/'):
            return FileType.VIDEO
        elif mime_type == 'application/pdf':
            return FileType.DOCUMENT
        elif mime_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            return FileType.DOCUMENT
        elif mime_type == 'text/plain':
            return FileType.TEXT
        else:
            return FileType.OTHER
    
    async def _extract_text(self, content: bytes, mime_type: str) -> str:
        """Extract text from file content"""
        # TODO: Implement text extraction based on file type
        if mime_type == 'text/plain':
            return content.decode('utf-8', errors='ignore')
        elif mime_type == 'application/pdf':
            # TODO: Use PDF processing library
            return "PDF text extraction not implemented"
        else:
            return f"Text extraction not supported for {mime_type}"
    
    async def _extract_metadata(self, content: bytes, mime_type: str) -> Dict[str, Any]:
        """Extract metadata from file content"""
        # TODO: Implement metadata extraction
        return {
            "mime_type": mime_type,
            "size": len(content),
            "extraction_method": "basic"
        }
    
    async def _analyze_content(self, content: bytes, mime_type: str, text: Optional[str] = None) -> Dict[str, Any]:
        """Analyze file content"""
        # TODO: Implement content analysis
        return {
            "content_type": mime_type,
            "has_text": bool(text),
            "text_length": len(text) if text else 0
        }
    
    async def _categorize_content(self, text: str, filename: str) -> str:
        """Categorize content using AI"""
        # TODO: Use AI service for categorization
        return "uncategorized"
    
    async def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        # TODO: Use AI service for sentiment analysis
        return {"sentiment": "neutral", "confidence": 0.5}
    
    async def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from text"""
        # TODO: Use AI service for entity extraction
        return []
    
    async def _generate_summary(self, text: str) -> str:
        """Generate summary of text"""
        # TODO: Use AI service for summarization
        if len(text) > 100:
            return text[:100] + "..."
        return text
    
    async def create_file_record(
        self,
        db: AsyncSession,
        filename: str,
        mime_type: str,
        file_size: int,
        file_content: bytes,
        uploaded_by_id: UUID,
        organization_id: UUID,
        description: Optional[str] = None
    ) -> File:
        """
        Create a new file record with simplified parameters for PRP implementation.
        Handles soft-deleted files with same hash by reusing or updating them.
        """
        import hashlib
        
        # Calculate file hash first
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Check for existing file with same hash (including soft-deleted ones)
        existing_query = select(File).where(
            and_(
                File.file_hash == file_hash,
                File.organization_id == organization_id,
                File.uploaded_by_id == uploaded_by_id
            )
        )
        result = await db.execute(existing_query)
        existing_file = result.scalar_one_or_none()
        
        # If we find an existing file (active or soft-deleted)
        if existing_file:
            if existing_file.is_deleted:
                # Restore the soft-deleted file
                existing_file.filename = filename
                existing_file.mime_type = mime_type
                existing_file.file_size = file_size
                existing_file.file_type = self._detect_file_type(mime_type)
                existing_file.status = FileStatus.UPLOADED
                existing_file.is_deleted = False
                existing_file.deleted_at = None
                existing_file.updated_at = datetime.now(timezone.utc)
                
                await db.commit()
                await db.refresh(existing_file)
                
                return existing_file
            else:
                # File already exists and is active - this is a true duplicate
                raise DuplicateFileError(f"File with hash {file_hash} already exists and is active", existing_file.id)
        
        # Generate unique file ID and storage key for new file
        file_id = uuid.uuid4()
        file_extension = Path(filename).suffix
        
        # Create storage key with date organization
        now = datetime.now()
        storage_key = f"attachments/{now.year}/{now.month:02d}/{file_id}{file_extension}"
        
        # Upload file using storage service
        file_url = await self.storage_service.upload_content(
            content=file_content,
            storage_key=storage_key,
            content_type=mime_type,
            metadata={
                "file_id": str(file_id),
                "user_id": str(uploaded_by_id),
                "organization_id": str(organization_id),
                "original_filename": filename,
                "file_size": str(file_size)
            }
        )
        
        # Create database record with new model structure
        db_file = File(
            id=file_id,
            filename=filename,
            file_path=storage_key,
            mime_type=mime_type,
            file_size=file_size,
            file_hash=file_hash,
            file_type=self._detect_file_type(mime_type),
            uploaded_by_id=uploaded_by_id,
            organization_id=organization_id,
            status=FileStatus.UPLOADED
        )
        
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        
        return db_file
    
    async def get_files_for_organization(
        self,
        db: AsyncSession,
        organization_id: UUID,
        user_id: UUID,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[File]:
        """
        Get files scoped to organization with filters for PRP implementation
        """
        query = select(File).where(
            and_(
                File.organization_id == organization_id,
                File.is_deleted == False,
                File.uploaded_by_id == user_id  # Phase 1: Only user's own files
            )
        )
        
        # Apply filters
        if filters:
            if filters.get("file_type"):
                query = query.where(File.file_type == filters["file_type"])
            if filters.get("status"):
                query = query.where(File.status == filters["status"])
        
        # Add pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()