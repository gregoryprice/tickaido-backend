#!/usr/bin/env python3
"""
Agent File Processing Tasks for asynchronous file content extraction
"""

import logging
import asyncio
from typing import Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.services.agent_file_service import agent_file_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, queue="agent_file_processing")
def process_agent_file(self, agent_file_id: str) -> Dict[str, Any]:
    """
    Process file content and extract text for agent context.
    
    Args:
        agent_file_id: Agent file relationship ID
        
    Returns:
        Dict: Processing result with status and metadata
    """
    try:
        # Convert string ID to UUID
        file_uuid = UUID(agent_file_id)
        
        logger.info(f"Starting file processing for agent file {agent_file_id}")
        start_time = datetime.now(timezone.utc)
        
        # Run async processing
        success = asyncio.run(agent_file_service.process_file_content(file_uuid))
        
        end_time = datetime.now(timezone.utc)
        duration_seconds = (end_time - start_time).total_seconds()
        
        if success:
            logger.info(f"✅ Completed file processing for agent file {agent_file_id} in {duration_seconds:.2f}s")
            return {
                "status": "completed",
                "agent_file_id": agent_file_id,
                "processing_time_seconds": duration_seconds,
                "completed_at": end_time.isoformat()
            }
        else:
            logger.error(f"❌ Failed to process agent file {agent_file_id}")
            return {
                "status": "failed",
                "agent_file_id": agent_file_id,
                "processing_time_seconds": duration_seconds,
                "error": "File processing failed"
            }
        
    except Exception as e:
        logger.error(f"Error in process_agent_file task: {e}")
        self.retry(countdown=60, max_retries=3, exc=e)


@celery_app.task(bind=True, queue="agent_file_processing")
def batch_process_agent_files(self, agent_id: str, file_ids: list) -> Dict[str, Any]:
    """
    Process multiple files for an agent in batch.
    
    Args:
        agent_id: Agent ID
        file_ids: List of agent file IDs to process
        
    Returns:
        Dict: Batch processing results
    """
    try:
        agent_uuid = UUID(agent_id)
        results = {
            "agent_id": agent_id,
            "total_files": len(file_ids),
            "successful": 0,
            "failed": 0,
            "file_results": []
        }
        
        logger.info(f"Starting batch processing of {len(file_ids)} files for agent {agent_id}")
        
        for file_id in file_ids:
            try:
                file_uuid = UUID(file_id)
                success = asyncio.run(agent_file_service.process_file_content(file_uuid))
                
                if success:
                    results["successful"] += 1
                    results["file_results"].append({"file_id": file_id, "status": "completed"})
                else:
                    results["failed"] += 1
                    results["file_results"].append({"file_id": file_id, "status": "failed"})
                    
            except Exception as file_error:
                logger.error(f"Error processing file {file_id}: {file_error}")
                results["failed"] += 1
                results["file_results"].append({
                    "file_id": file_id, 
                    "status": "error", 
                    "error": str(file_error)
                })
        
        logger.info(f"✅ Completed batch processing for agent {agent_id}: {results['successful']} successful, {results['failed']} failed")
        return results
        
    except Exception as e:
        logger.error(f"Error in batch_process_agent_files task: {e}")
        self.retry(countdown=120, max_retries=2, exc=e)


@celery_app.task(bind=True, queue="agent_file_processing")
def reprocess_failed_files(self, agent_id: str = None) -> Dict[str, Any]:
    """
    Reprocess files that failed previous processing attempts.
    
    Args:
        agent_id: Optional agent ID to limit reprocessing scope
        
    Returns:
        Dict: Reprocessing results
    """
    try:
        logger.info(f"Starting reprocessing of failed files for agent: {agent_id or 'all agents'}")
        
        # This would query for failed agent files and retry processing
        # Placeholder implementation
        results = {
            "reprocessed_files": 0,
            "successful": 0,
            "still_failed": 0,
            "agent_id": agent_id
        }
        
        # In real implementation, would:
        # 1. Query AgentFile table for files with processing_status="failed"
        # 2. Filter by agent_id if provided
        # 3. Retry processing for each failed file
        # 4. Update results accordingly
        
        logger.info(f"✅ Completed reprocessing: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Error in reprocess_failed_files task: {e}")
        self.retry(countdown=300, max_retries=1, exc=e)


@celery_app.task(bind=True, queue="agent_maintenance")
def cleanup_processed_files(self) -> Dict[str, Any]:
    """
    Clean up old processed file content to manage storage.
    
    Returns:
        Dict: Cleanup results
    """
    try:
        logger.info("Starting cleanup of old processed files")
        
        # This would implement cleanup logic:
        # 1. Find agent files with extracted_content older than retention period
        # 2. Clear extracted_content but keep metadata
        # 3. Update processing status to indicate cleanup
        
        results = {
            "cleaned_files": 0,
            "storage_freed_bytes": 0,
            "cleanup_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"✅ Completed file cleanup: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Error in cleanup_processed_files task: {e}")
        return {"error": str(e)}


@celery_app.task(bind=True, queue="agent_file_processing")
def validate_agent_file_integrity(self, agent_id: str) -> Dict[str, Any]:
    """
    Validate integrity of agent files and their processed content.
    
    Args:
        agent_id: Agent ID to validate
        
    Returns:
        Dict: Validation results
    """
    try:
        agent_uuid = UUID(agent_id)
        logger.info(f"Starting file integrity validation for agent {agent_id}")
        
        # Run validation check
        files_accessible = asyncio.run(agent_file_service.check_file_access(agent_uuid))
        
        # This would implement comprehensive validation:
        # 1. Check if all agent files are accessible
        # 2. Verify content hashes match extracted content
        # 3. Validate processing status consistency
        # 4. Check for orphaned or corrupted files
        
        results = {
            "agent_id": agent_id,
            "files_accessible": files_accessible,
            "validation_passed": files_accessible,  # Simplified for now
            "issues_found": [],
            "validation_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if not files_accessible:
            results["issues_found"].append("File access check failed")
        
        logger.info(f"✅ Completed file integrity validation for agent {agent_id}: {results['validation_passed']}")
        return results
        
    except Exception as e:
        logger.error(f"Error in validate_agent_file_integrity task: {e}")
        self.retry(countdown=180, max_retries=2, exc=e)


@celery_app.task(bind=True, queue="agent_file_processing")
def generate_context_preview(self, agent_id: str, max_length: int = 1000) -> Dict[str, Any]:
    """
    Generate a preview of the context that would be assembled for an agent.
    
    Args:
        agent_id: Agent ID
        max_length: Maximum preview length
        
    Returns:
        Dict: Context preview information
    """
    try:
        agent_uuid = UUID(agent_id)
        logger.info(f"Generating context preview for agent {agent_id}")
        
        # Assemble context window
        context = asyncio.run(
            agent_file_service.assemble_context_window(
                agent_uuid, 
                max_context_length=max_length
            )
        )
        
        # Get file information
        agent_files = asyncio.run(agent_file_service.get_agent_files(agent_uuid))
        
        results = {
            "agent_id": agent_id,
            "context_length": len(context),
            "context_preview": context[:500] + "..." if len(context) > 500 else context,
            "total_files": len(agent_files),
            "processed_files": len([f for f in agent_files if f.is_processed]),
            "failed_files": len([f for f in agent_files if f.is_failed]),
            "files_info": [
                {
                    "filename": f.file.filename if f.file else "unknown",
                    "status": f.processing_status,
                    "priority": f.priority,
                    "order_index": f.order_index,
                    "content_length": f.content_length or 0
                }
                for f in agent_files
            ]
        }
        
        logger.info(f"✅ Generated context preview for agent {agent_id}: {len(context)} characters from {results['processed_files']} files")
        return results
        
    except Exception as e:
        logger.error(f"Error in generate_context_preview task: {e}")
        self.retry(countdown=60, max_retries=2, exc=e)


@celery_app.task(bind=True, queue="agent_maintenance")
def optimize_agent_file_storage(self) -> Dict[str, Any]:
    """
    Optimize storage for agent files by removing duplicates and compressing content.
    
    Returns:
        Dict: Optimization results
    """
    try:
        logger.info("Starting agent file storage optimization")
        
        # This would implement optimization logic:
        # 1. Find duplicate content using content_hash
        # 2. Deduplicate by keeping one copy and updating references
        # 3. Compress large text content
        # 4. Archive old, unused content
        
        results = {
            "duplicates_removed": 0,
            "content_compressed": 0,
            "storage_saved_bytes": 0,
            "optimization_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"✅ Completed storage optimization: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Error in optimize_agent_file_storage task: {e}")
        return {"error": str(e)}


# Periodic task registration (would be configured in Celery beat)
@celery_app.task(bind=True)
def schedule_file_maintenance(self):
    """
    Schedule periodic maintenance tasks for agent files.
    """
    try:
        logger.info("Scheduling file maintenance tasks")
        
        # Schedule cleanup
        cleanup_processed_files.delay()
        
        # Schedule optimization
        optimize_agent_file_storage.delay()
        
        return {
            "scheduled_tasks": ["cleanup_processed_files", "optimize_agent_file_storage"],
            "scheduled_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error scheduling file maintenance: {e}")
        return {"error": str(e)}