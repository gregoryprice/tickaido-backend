#!/usr/bin/env python3
"""
Files API Router - Core endpoints for file upload, download, delete, and metadata
Implements the file attachment system according to PRP specifications
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.auth_middleware import get_current_user
from app.database import get_db_session
from app.models.user import User
from app.models.file import File as FileModel, FileStatus, FileType
from app.schemas.file import (
    FileUploadResponse, 
    FileResponse, 
    FileListResponse,
    FileProcessingStatusResponse
)
from app.services.file_service import FileService, DuplicateFileError
from app.services.file_processing_service import FileProcessingService
from app.tasks.file_tasks import process_file_upload

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a single file with basic validation and processing
    
    Files are uploaded independently and can be associated with tickets/threads later
    """
    try:
        # Read file content
        file_content = await file.read()
        logger.info(f"File upload started: {file.filename}, size: {len(file_content)} bytes")
        
        # Basic validation
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="File cannot be empty")
        
        # Initialize services
        file_service = FileService()
        
        # Create file record
        logger.info(f"Creating file record for {file.filename}")
        file_obj = await file_service.create_file_record(
            db=db,
            filename=file.filename,
            mime_type=file.content_type or "application/octet-stream",
            file_size=len(file_content),
            file_content=file_content,
            uploaded_by_id=current_user.id,
            organization_id=current_user.organization_id,
            description=description
        )
        logger.info(f"File record created successfully: {file_obj.id}")
        
        # Schedule Celery processing task
        try:
            task_result = process_file_upload.delay(str(file_obj.id))
            logger.info(f"Enqueued file processing task for file {file_obj.id}, task_id: {task_result.id}")
        except ConnectionError as conn_error:
            logger.error(f"Celery connection error for file {file_obj.id}: {conn_error}")
            # Don't fail the upload, just log the error
            # The file will be picked up by the periodic task later
        except Exception as celery_error:
            logger.error(f"Failed to enqueue Celery task for file {file_obj.id}: {celery_error}")
            # Don't fail the upload, just log the error
            # The file will be picked up by the periodic task later
        
        # Determine if processing is required
        processing_required = file_obj.is_text_file or file_obj.is_image_file or file_obj.is_media_file
        
        return FileUploadResponse(
            id=file_obj.id,
            filename=file_obj.filename,
            file_size=file_obj.file_size,
            mime_type=file_obj.mime_type,
            file_type=file_obj.file_type,
            status=file_obj.status,
            url=f"/api/v1/files/{file_obj.id}/content",
            processing_required=processing_required
        )
        
    except HTTPException:
        raise
    except DuplicateFileError as e:
        # Handle duplicate active file case
        logger.info(f"Duplicate active file upload attempt: {e}")
        raise HTTPException(
            status_code=409,
            detail={
                "message": "File with this content already exists",
                "existing_file_id": str(e.existing_file_id),
                "existing_file_url": f"/api/v1/files/{e.existing_file_id}/content"
            }
        )
    except ValueError as e:
        logger.error(f"File upload failed with ValueError: {e}")
        raise HTTPException(status_code=400, detail="File upload failed")
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        
        # Check for duplicate file hash (unique constraint violation) - fallback for edge cases
        if "duplicate key value violates unique constraint" in str(e) and "file_hash" in str(e):
            raise HTTPException(
                status_code=409, 
                detail="File already exists"
            )
        
        # Generic server error for other issues
        raise HTTPException(status_code=500, detail="File upload failed")


@router.get("/{file_id}", response_model=FileResponse)
async def get_file_metadata(
    file_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get file metadata and processing status"""
    
    file_service = FileService()
    file_obj = await file_service.get_file(db, file_id)
    
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check organization access
    if file_obj.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return FileResponse(
        id=file_obj.id,
        filename=file_obj.filename,
        file_size=file_obj.file_size,
        mime_type=file_obj.mime_type,
        file_type=file_obj.file_type,
        status=file_obj.status,
        url=f"/api/v1/files/{file_obj.id}/content",
        extraction_method=file_obj.extraction_method,
        content_summary=file_obj.content_summary,
        extracted_context=file_obj.extracted_context,
        language_detection=file_obj.language_detection,
        processing_started_at=file_obj.processing_started_at,
        processing_completed_at=file_obj.processing_completed_at,
        processing_error=file_obj.processing_error,
        created_at=file_obj.created_at,
        updated_at=file_obj.updated_at
    )


@router.get("/{file_id}/content")
async def download_file_content(
    file_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Download file content with access control"""
    
    file_service = FileService()
    file_obj = await file_service.get_file(db, file_id)
    
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check organization access
    if file_obj.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Get file content from storage
        file_content = await file_service.get_file_content(db, file_id)
        
        # Record download
        file_obj.record_download()
        await db.commit()
        
        # Return streaming response
        def generate_content():
            yield file_content
        
        return StreamingResponse(
            generate_content(),
            media_type=file_obj.mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{file_obj.filename}"',
                "Content-Length": str(file_obj.file_size)
            }
        )
        
    except Exception as e:
        logger.error(f"File download failed for {file_id}: {e}")
        raise HTTPException(status_code=500, detail="File download failed")


@router.delete("/{file_id}")
async def delete_file(
    file_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Delete file with access control"""
    
    file_service = FileService()
    file_obj = await file_service.get_file(db, file_id)
    
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check organization access
    if file_obj.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if file can be deleted
    if not file_obj.can_be_deleted():
        raise HTTPException(status_code=400, detail="File cannot be deleted")
    
    try:
        # Cancel any active processing tasks for this file
        from app.services.task_cancellation_service import TaskCancellationService
        task_canceller = TaskCancellationService()
        
        # Cancel processing if file is being processed
        if file_obj.status == FileStatus.PROCESSING:
            cancellation_result = task_canceller.cancel_file_processing_tasks(str(file_id))
            logger.info(f"Task cancellation for file {file_id}: {cancellation_result}")
        
        # Delete file from storage and database
        await file_service.delete_file(db, file_id, current_user.id)
        
        return {"message": "File deleted successfully"}
        
    except Exception as e:
        logger.error(f"File deletion failed for {file_id}: {e}")
        raise HTTPException(status_code=500, detail="File deletion failed")


@router.get("", response_model=FileListResponse)
async def list_user_files(
    skip: int = 0,
    limit: int = 50,
    file_type: Optional[FileType] = None,
    status: Optional[FileStatus] = None,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    List user's files with organization scoping
    
    Note: Deleted files are automatically excluded from results.
    Valid status filters: uploaded, processing, processed, failed, quarantined
    """
    
    file_service = FileService()
    
    # Build filters
    filters = {}
    if file_type:
        filters["file_type"] = file_type
    if status:
        # Prevent querying for deleted files since they're filtered out anyway
        if status == FileStatus.DELETED:
            raise HTTPException(
                status_code=400, 
                detail="Cannot filter by deleted status. Deleted files are not included in results."
            )
        filters["status"] = status
    
    try:
        files = await file_service.get_files_for_organization(
            db=db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            filters=filters,
            skip=skip,
            limit=limit
        )
        
        file_responses = []
        for file_obj in files:
            file_responses.append(FileResponse(
                id=file_obj.id,
                filename=file_obj.filename,
                file_size=file_obj.file_size,
                mime_type=file_obj.mime_type,
                file_type=file_obj.file_type,
                status=file_obj.status,
                url=f"/api/v1/files/{file_obj.id}/content",
                extraction_method=file_obj.extraction_method,
                content_summary=file_obj.content_summary,
                language_detection=file_obj.language_detection,
                processing_started_at=file_obj.processing_started_at,
                processing_completed_at=file_obj.processing_completed_at,
                processing_error=file_obj.processing_error,
                created_at=file_obj.created_at,
                updated_at=file_obj.updated_at
            ))
        
        return FileListResponse(
            files=file_responses,
            total=len(file_responses),
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"File listing failed: {e}")
        raise HTTPException(status_code=500, detail="File listing failed")


@router.get("/{file_id}/processing-status", response_model=FileProcessingStatusResponse)
async def get_file_processing_status(
    file_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get detailed processing status for a file"""
    
    processing_service = FileProcessingService()
    
    try:
        status = await processing_service.get_file_processing_status(db, str(file_id))
        
        if status is None:
            raise HTTPException(status_code=404, detail="File not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processing status check failed for {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Status check failed")


@router.post("/{file_id}/reprocess")
async def reprocess_file(
    file_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Reprocess a file that failed or needs updated extraction"""
    
    file_service = FileService()
    file_obj = await file_service.get_file(db, file_id)
    
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check organization access
    if file_obj.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Reset file status to UPLOADED before reprocessing
        file_obj.status = FileStatus.UPLOADED
        file_obj.processing_error = None
        file_obj.processing_started_at = None
        file_obj.processing_completed_at = None
        await db.commit()
        
        # Schedule Celery reprocessing task
        from app.tasks.file_tasks import reprocess_file as reprocess_file_task
        reprocess_file_task.delay(str(file_id))
        
        return {"message": "File reprocessing started"}
        
    except Exception as e:
        logger.error(f"File reprocessing failed for {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Reprocessing failed")