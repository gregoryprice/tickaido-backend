#!/usr/bin/env python3
"""
Celery tasks for file processing, analysis, and management
"""

from typing import Any, Dict

from celery.utils.log import get_task_logger

from app.celery_app import celery_app

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
        # Use sync DB session with async services
        result = _process_file_upload_sync(file_id, processing_options)
        logger.info(f"File processing completed for file_id: {file_id}")
        return result
        
    except Exception as exc:
        # Check if it's a cancellation (from actual revoke calls)
        from celery.exceptions import WorkerLostError
        if isinstance(exc, WorkerLostError) or "revoked" in str(exc).lower():
            logger.info(f"File processing cancelled for file_id: {file_id}")
            return {"status": "cancelled", "file_id": file_id}
            
        logger.error(f"File processing failed for file_id: {file_id}, error: {str(exc)}")
        # Retry with exponential backoff
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True, retry_backoff=True, max_retries=3)
def reprocess_file(self, file_id: str):
    """
    Reprocess a file - same as process_file_upload but with force reprocessing
    
    Args:
        file_id: UUID of the file to reprocess
    """
    logger.info(f"Starting file reprocessing for file_id: {file_id}")
    
    try:
        # Force reprocessing by passing force_reprocess option
        processing_options = {"force_reprocess": True}
        
        # Use sync DB session with async services
        result = _process_file_upload_sync(file_id, processing_options)
            
        logger.info(f"File reprocessing completed for file_id: {file_id}")
        return result
        
    except Exception as exc:
        logger.error(f"File reprocessing failed for file_id: {file_id}, error: {str(exc)}")
        # Retry with exponential backoff
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True)
def process_pending_files(self):
    """
    Process all files with UPLOADED status
    """
    logger.info("Starting processing of pending files")
    
    try:
        processed_count = _process_pending_files_sync()
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
        cleaned_count = _cleanup_failed_uploads_sync(older_than_hours)
        logger.info(f"Cleaned up {cleaned_count} failed uploads")
        return {"cleaned": cleaned_count}
        
    except Exception as exc:
        logger.error(f"Error cleaning up failed uploads: {str(exc)}")
        return {"error": str(exc)}


# Helper functions for Celery tasks using sync DB with async services  
def _process_file_upload_sync(file_id: str, processing_options: Dict[str, Any] = None) -> Dict[str, Any]:
    """Process file upload using sync DB session but async FileProcessingService"""
    logger.info(f"_process_file_upload_sync starting for {file_id}")
    
    from uuid import UUID

    from sqlalchemy import and_, select

    from app.database import SessionLocal
    from app.models.file import File, FileStatus
    from app.services.file_processing_service import FileProcessingService
    
    # Use synchronous database session for Celery
    db = SessionLocal()
    
    try:
        # Get file record using sync query
        db_file = db.execute(
            select(File).where(
                and_(File.id == UUID(file_id), File.deleted_at.is_(None))
            )
        ).scalar_one_or_none()
        
        if not db_file:
            raise ValueError(f"File not found: {file_id}")
        
        # Skip processing if file is soft-deleted
        if db_file.is_deleted:
            logger.warning(f"Skipping processing for soft-deleted file: {file_id}")
            raise ValueError(f"File is soft-deleted: {file_id}")
        
        # Handle idempotency - check current status
        if db_file.status == FileStatus.PROCESSING:
            logger.info(f"File {file_id} is already being processed, skipping")
            return {"status": "already_processing", "file_id": file_id}
        
        if db_file.status == FileStatus.PROCESSED:
            force_reprocess = processing_options.get("force_reprocess", False) if processing_options else False
            if not force_reprocess:
                logger.info(f"File {file_id} is already processed, skipping")
                return {"status": "already_processed", "file_id": file_id}
        
        # Start processing
        db_file.start_processing()
        db.commit()
        
        try:
            # Use FileProcessingService methods directly but handle transaction management here
            file_processing_service = FileProcessingService()
            
            # Use asyncio with explicit event loop policy for better cleanup
            import asyncio
            
            # Create async wrapper that calls service methods
            async def async_process_with_service():
                await _process_file_using_service_methods(file_processing_service, db_file)
            
            # Run async processing with proper cleanup handling
            try:
                # Use asyncio.run with debug=False to prevent cleanup warnings
                if hasattr(asyncio, '_get_running_loop') and asyncio._get_running_loop() is not None:
                    # If there's already a running loop, create a new one in a thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, async_process_with_service())
                        future.result()
                else:
                    # Normal case - no existing loop
                    asyncio.run(async_process_with_service())
                    
            except RuntimeError as e:
                if "Event loop is closed" not in str(e):
                    raise
                # Ignore event loop closure errors during cleanup
                logger.debug(f"Ignored event loop cleanup error: {e}")
                
            except Exception as e:
                logger.error(f"Async processing failed: {e}")
                raise
            
            # Mark as completed (transaction managed in Celery task)
            db_file.complete_processing()
            db.commit()
            
            logger.info(f"Successfully processed file {file_id}")
            return {"status": "completed", "file_id": file_id}
            
        except Exception as e:
            logger.error(f"File processing failed for {file_id}: {e}")
            db_file.fail_processing(str(e)[:500])
            db.commit()
            raise
            
    except Exception as e:
        logger.error(f"Database error for file {file_id}: {e}")
        db.rollback()
        raise e
    
    finally:
        db.close()


async def _process_file_using_service_methods(file_processing_service, db_file):
    """Process file using FileProcessingService methods without transaction management"""
    
    # Get file content from storage using the service
    file_content = await file_processing_service.file_service.storage_service.download_file(db_file.file_path)
    if not file_content:
        raise Exception("Unable to retrieve file content from storage")
    
    extracted_context = {}
    
    # Process based on file type using service methods
    logger.info(f"File processing - MIME: {db_file.mime_type}, is_text_file: {db_file.is_text_file}")
    
    if db_file.is_text_file or db_file.mime_type == "application/pdf":
        logger.info("Using document processing path")
        document_data = await file_processing_service._extract_document_content(db_file, file_content)
        extracted_context["document"] = document_data
        db_file.extraction_method = "document_parser"
    
    elif db_file.is_image_file:
        logger.info("Using image processing path")
        image_data = await file_processing_service._extract_image_content(db_file, file_content)
        extracted_context["image"] = image_data
        db_file.extraction_method = "vision_ocr"
    
    elif db_file.is_media_file:
        logger.info("Using audio processing path")
        audio_data = await file_processing_service._extract_audio_content(db_file, file_content)
        extracted_context["audio"] = audio_data
        db_file.extraction_method = "speech_transcription"
    
    # Validate and clean extracted context
    cleaned_context = file_processing_service._validate_and_clean_context(extracted_context)
    db_file.extracted_context = cleaned_context
    
    # Generate AI summary using service method
    all_text_content = file_processing_service._extract_text_from_context(extracted_context)
    if all_text_content:
        db_file.content_summary = await file_processing_service.ai_service.generate_summary(
            all_text_content,
            max_length=500
        )
        db_file.language_detection = await file_processing_service.ai_service.detect_language(all_text_content)
    else:
        db_file.content_summary = f"Processed {db_file.file_type.value} file: {db_file.filename}"
        db_file.language_detection = "en"


def _process_pending_files_sync() -> int:
    """Process all pending files using sync database session"""
    from sqlalchemy import and_, select

    from app.database import SessionLocal
    from app.models.file import File, FileStatus
    
    db = SessionLocal()
    
    try:
        # Get files with UPLOADED status
        query = select(File).where(
            and_(
                File.status == FileStatus.UPLOADED,
                File.deleted_at.is_(None)
            )
        )
        
        result = db.execute(query)
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
    
    except Exception as e:
        logger.error(f"Error processing pending files: {e}")
        db.rollback()
        raise e
    
    finally:
        db.close()


def _cleanup_failed_uploads_sync(older_than_hours: int) -> int:
    """Clean up failed uploads using sync database session"""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import and_, select

    from app.database import SessionLocal
    from app.models.file import File, FileStatus
    
    db = SessionLocal()
    
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        
        # Get files with FAILED status older than cutoff
        query = select(File).where(
            and_(
                File.status == FileStatus.FAILED,
                File.created_at < cutoff_time,
                File.deleted_at.is_(None)
            )
        )
        
        result = db.execute(query)
        failed_files = result.scalars().all()
        
        cleaned_count = 0
        
        for db_file in failed_files:
            try:
                # Soft delete from database
                db_file.soft_delete()
                cleaned_count += 1
                
            except Exception as e:
                logger.error(f"Failed to cleanup file {db_file.id}: {str(e)}")
                continue
        
        db.commit()
        return cleaned_count
    
    except Exception as e:
        logger.error(f"Error cleaning up failed uploads: {e}")
        db.rollback()
        raise e
    
    finally:
        db.close()