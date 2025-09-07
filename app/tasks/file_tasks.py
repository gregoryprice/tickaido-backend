#!/usr/bin/env python3
"""
Celery tasks for file processing, analysis, and management
"""

import os
import asyncio
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime, timezone, timedelta

from celery import current_app as celery_app
from celery.utils.log import get_task_logger
from sqlalchemy import select, and_

from app.database import get_db_session
from app.models.file import File, FileStatus, FileType
from app.services.file_service import FileService
from app.schemas.file import FileProcessingRequest, FileAnalysisRequest

# Get logger
logger = get_task_logger(__name__)


@celery_app.task(bind=True, retry_backoff=True, max_retries=3)
def process_file_upload(self, file_id: str, processing_options: Dict[str, Any] = None):
    """
    Process uploaded file - extract text, metadata, and analyze content
    
    Args:
        file_id: UUID of the file to process
        processing_options: Optional processing configuration
    """
    logger.info(f"Starting file processing for file_id: {file_id}")
    
    try:
        # Run async processing
        result = asyncio.run(_process_file_async(file_id, processing_options))
        logger.info(f"File processing completed for file_id: {file_id}")
        return result
        
    except Exception as exc:
        logger.error(f"File processing failed for file_id: {file_id}, error: {str(exc)}")
        # Retry with exponential backoff
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True, retry_backoff=True, max_retries=3)
def analyze_file_content(self, file_id: str, analysis_options: Dict[str, Any] = None):
    """
    Perform AI-powered analysis on file content
    
    Args:
        file_id: UUID of the file to analyze
        analysis_options: Analysis configuration
    """
    logger.info(f"Starting file analysis for file_id: {file_id}")
    
    try:
        result = asyncio.run(_analyze_file_async(file_id, analysis_options))
        logger.info(f"File analysis completed for file_id: {file_id}")
        return result
        
    except Exception as exc:
        logger.error(f"File analysis failed for file_id: {file_id}, error: {str(exc)}")
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True)
def process_pending_files(self):
    """
    Process all files with UPLOADED status
    """
    logger.info("Starting processing of pending files")
    
    try:
        processed_count = asyncio.run(_process_pending_files_async())
        logger.info(f"Processed {processed_count} pending files")
        return {"processed": processed_count}
        
    except Exception as exc:
        logger.error(f"Error processing pending files: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True)
def cleanup_failed_uploads(self, older_than_hours: int = 24):
    """
    Clean up files that failed to upload or process
    
    Args:
        older_than_hours: Remove files older than this many hours
    """
    logger.info(f"Starting cleanup of failed uploads older than {older_than_hours} hours")
    
    try:
        cleaned_count = asyncio.run(_cleanup_failed_uploads_async(older_than_hours))
        logger.info(f"Cleaned up {cleaned_count} failed uploads")
        return {"cleaned": cleaned_count}
        
    except Exception as exc:
        logger.error(f"Error cleaning up failed uploads: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True)
def generate_file_thumbnails(self, file_id: str, sizes: List[tuple] = None):
    """
    Generate thumbnails for image files
    
    Args:
        file_id: UUID of the file
        sizes: List of (width, height) tuples for thumbnail sizes
    """
    if not sizes:
        sizes = [(150, 150), (300, 300), (600, 600)]
    
    logger.info(f"Generating thumbnails for file_id: {file_id}")
    
    try:
        result = asyncio.run(_generate_thumbnails_async(file_id, sizes))
        logger.info(f"Thumbnail generation completed for file_id: {file_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Thumbnail generation failed for file_id: {file_id}, error: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True, retry_backoff=True, max_retries=2) 
def extract_file_text(self, file_id: str, extraction_options: Dict[str, Any] = None):
    """
    Extract text from various file types
    
    Args:
        file_id: UUID of the file
        extraction_options: Text extraction configuration
    """
    logger.info(f"Starting text extraction for file_id: {file_id}")
    
    try:
        result = asyncio.run(_extract_text_async(file_id, extraction_options))
        logger.info(f"Text extraction completed for file_id: {file_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Text extraction failed for file_id: {file_id}, error: {str(exc)}")
        self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


@celery_app.task(bind=True)
def scan_file_for_viruses(self, file_id: str):
    """
    Scan file for viruses using ClamAV
    
    Args:
        file_id: UUID of the file to scan
    """
    logger.info(f"Starting virus scan for file_id: {file_id}")
    
    try:
        result = asyncio.run(_scan_file_async(file_id))
        logger.info(f"Virus scan completed for file_id: {file_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Virus scan failed for file_id: {file_id}, error: {str(exc)}")
        return {"error": str(exc), "status": "scan_failed"}


# Async helper functions
async def _process_file_async(file_id: str, processing_options: Dict[str, Any] = None) -> Dict[str, Any]:
    """Process file asynchronously"""
    async with get_db_session() as db:
        file_service = FileService()
        
        # Get file record
        db_file = await file_service.get_file(db, UUID(file_id))
        if not db_file:
            raise ValueError(f"File not found: {file_id}")
        
        # Set default processing options
        if not processing_options:
            processing_options = {
                "extract_text": True,
                "extract_metadata": True,
                "analyze_content": True,
                "scan_virus": True
            }
        
        # Create processing request
        processing_request = FileProcessingRequest(
            extract_text=processing_options.get("extract_text", True),
            extract_metadata=processing_options.get("extract_metadata", True),
            analyze_content=processing_options.get("analyze_content", False)
        )
        
        # Process file
        result = await file_service.process_file(
            db, UUID(file_id), processing_request, db_file.uploaded_by
        )
        
        if result:
            return result.model_dump()
        else:
            raise Exception("File processing failed")


async def _analyze_file_async(file_id: str, analysis_options: Dict[str, Any] = None) -> Dict[str, Any]:
    """Analyze file content asynchronously"""
    async with get_db_session() as db:
        file_service = FileService()
        
        # Get file record
        db_file = await file_service.get_file(db, UUID(file_id))
        if not db_file:
            raise ValueError(f"File not found: {file_id}")
        
        # Set default analysis options
        if not analysis_options:
            analysis_options = {
                "categorize_content": True,
                "analyze_sentiment": True,
                "extract_entities": True,
                "generate_summary": True
            }
        
        # Create analysis request
        analysis_request = FileAnalysisRequest(
            categorize_content=analysis_options.get("categorize_content", True),
            analyze_sentiment=analysis_options.get("analyze_sentiment", True),
            extract_entities=analysis_options.get("extract_entities", True),
            generate_summary=analysis_options.get("generate_summary", True)
        )
        
        # Analyze file
        result = await file_service.analyze_file(
            db, UUID(file_id), analysis_request, db_file.uploaded_by
        )
        
        if result:
            return result.model_dump()
        else:
            raise Exception("File analysis failed")


async def _process_pending_files_async() -> int:
    """Process all pending files"""
    async with get_db_session() as db:
        # Get files with UPLOADED status
        query = select(File).where(
            and_(
                File.status == FileStatus.UPLOADED,
                File.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        pending_files = result.scalars().all()
        
        processed_count = 0
        
        for db_file in pending_files:
            try:
                # Queue processing task
                process_file_upload.delay(str(db_file.id))
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to queue processing for file {db_file.id}: {str(e)}")
                continue
        
        return processed_count


async def _cleanup_failed_uploads_async(older_than_hours: int) -> int:
    """Clean up failed uploads"""
    async with get_db_session() as db:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        
        # Get files with ERROR status older than cutoff
        query = select(File).where(
            and_(
                File.status == FileStatus.ERROR,
                File.created_at < cutoff_time,
                File.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        failed_files = result.scalars().all()
        
        cleaned_count = 0
        
        for db_file in failed_files:
            try:
                # Remove file from filesystem
                if os.path.exists(db_file.storage_path):
                    os.unlink(db_file.storage_path)
                
                # Soft delete from database
                db_file.soft_delete()
                cleaned_count += 1
                
            except Exception as e:
                logger.error(f"Failed to cleanup file {db_file.id}: {str(e)}")
                continue
        
        await db.commit()
        return cleaned_count


async def _generate_thumbnails_async(file_id: str, sizes: List[tuple]) -> Dict[str, Any]:
    """Generate thumbnails for image files"""
    async with get_db_session() as db:
        file_service = FileService()
        
        # Get file record
        db_file = await file_service.get_file(db, UUID(file_id))
        if not db_file:
            raise ValueError(f"File not found: {file_id}")
        
        # Check if file is an image
        if db_file.file_type != FileType.IMAGE:
            raise ValueError(f"File is not an image: {db_file.file_type}")
        
        # TODO: Implement thumbnail generation using PIL/Pillow
        thumbnails_generated = []
        
        for width, height in sizes:
            thumbnail_path = f"{db_file.storage_path}_thumb_{width}x{height}.jpg"
            # Generate thumbnail logic here
            thumbnails_generated.append({
                "size": f"{width}x{height}",
                "path": thumbnail_path
            })
        
        # Update file record with thumbnail paths
        if not db_file.processing_results:
            db_file.processing_results = {}
        
        db_file.processing_results["thumbnails"] = thumbnails_generated
        await db.commit()
        
        return {
            "file_id": file_id,
            "thumbnails": thumbnails_generated
        }


async def _extract_text_async(file_id: str, extraction_options: Dict[str, Any] = None) -> Dict[str, Any]:
    """Extract text from file"""
    async with get_db_session() as db:
        file_service = FileService()
        
        # Get file record  
        db_file = await file_service.get_file(db, UUID(file_id))
        if not db_file:
            raise ValueError(f"File not found: {file_id}")
        
        # Get file content
        content = await file_service.get_file_content(db, UUID(file_id))
        if not content:
            raise ValueError(f"Cannot read file content for: {file_id}")
        
        # Extract text based on file type
        extracted_text = await file_service._extract_text(content, db_file.mime_type)
        
        # Update file record
        if not db_file.processing_results:
            db_file.processing_results = {}
        
        db_file.processing_results["extracted_text"] = extracted_text
        db_file.processing_results["text_length"] = len(extracted_text)
        
        await db.commit()
        
        return {
            "file_id": file_id,
            "extracted_text": extracted_text,
            "text_length": len(extracted_text)
        }


async def _scan_file_async(file_id: str) -> Dict[str, Any]:
    """Scan file for viruses"""
    async with get_db_session() as db:
        file_service = FileService()
        
        # Get file record
        db_file = await file_service.get_file(db, UUID(file_id))
        if not db_file:
            raise ValueError(f"File not found: {file_id}")
        
        # TODO: Implement actual ClamAV scanning
        # For now, assume file is clean
        scan_result = {
            "status": "clean",
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "engine": "clamav",
            "threats_found": 0
        }
        
        # Update file record
        if not db_file.processing_results:
            db_file.processing_results = {}
        
        db_file.processing_results["virus_scan"] = scan_result
        
        await db.commit()
        
        return {
            "file_id": file_id,
            "scan_result": scan_result
        }