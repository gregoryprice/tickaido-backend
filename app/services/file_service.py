#!/usr/bin/env python3
"""
File Service - Business logic for file management, processing, and analysis
"""

import os
import uuid
import aiofiles
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


class FileService:
    """Service class for file operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.upload_directory = Path(self.settings.upload_directory)
        self.max_file_size = self.settings.max_file_size
        self.allowed_file_types = self.settings.allowed_file_types
        
        # Ensure upload directory exists
        self.upload_directory.mkdir(parents=True, exist_ok=True)
    
    async def upload_file(
        self,
        db: AsyncSession,
        file_request: FileUploadRequest,
        file_content: bytes,
        user_id: UUID
    ) -> File:
        """
        Upload a new file
        
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
        
        # Generate unique file ID and storage path
        file_id = uuid.uuid4()
        file_extension = Path(file_request.filename).suffix
        storage_filename = f"{file_id}{file_extension}"
        storage_path = self.upload_directory / storage_filename
        
        # Save file to disk
        async with aiofiles.open(storage_path, 'wb') as f:
            await f.write(file_content)
        
        # Create database record
        db_file = File(
            id=file_id,
            filename=file_request.filename,
            original_filename=file_request.filename,
            storage_path=str(storage_path),
            mime_type=file_request.mime_type,
            file_size=len(file_content),
            file_type=file_request.file_type or self._detect_file_type(file_request.mime_type),
            status=FileStatus.UPLOADED,
            uploaded_by=user_id,
            ticket_id=file_request.ticket_id,
            tags=file_request.tags or [],
            description=file_request.description,
            is_public=file_request.is_public,
            retention_days=file_request.retention_days
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
                selectinload(File.uploaded_by_user),
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
            filters.append(File.uploaded_by == user_id)
        
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
        if db_file.uploaded_by != user_id:
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
        hard_delete: bool = False
    ) -> bool:
        """
        Delete file (soft delete by default)
        
        Args:
            db: Database session
            file_id: File ID
            user_id: ID of deleting user
            hard_delete: Whether to permanently delete
            
        Returns:
            True if deleted successfully
        """
        db_file = await self.get_file(db, file_id)
        if not db_file:
            return False
        
        # Check permissions
        if db_file.uploaded_by != user_id:
            # TODO: Check if user is admin
            pass
        
        if hard_delete:
            # Delete from filesystem
            try:
                if os.path.exists(db_file.storage_path):
                    os.unlink(db_file.storage_path)
            except Exception:
                # Log error but continue
                pass
            
            # Delete from database
            await db.delete(db_file)
        else:
            # Soft delete
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
        Get file content from storage
        
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
            if db_file.uploaded_by != user_id:
                # TODO: Check if user has access via ticket or is admin
                pass
        
        # Read file from storage
        try:
            async with aiofiles.open(db_file.storage_path, 'rb') as f:
                return await f.read()
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