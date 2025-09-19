#!/usr/bin/env python3
"""
Task Management API - Cancel and monitor file processing tasks
"""

import logging
from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.auth_middleware import get_current_user
from app.database import get_db_session
from app.models.user import User
from app.services.task_cancellation_service import TaskCancellationService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/files/{file_id}/cancel-processing")
async def cancel_file_processing(
    file_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel active processing tasks for a specific file
    """
    try:
        task_canceller = TaskCancellationService()
        result = task_canceller.cancel_file_processing_tasks(str(file_id))
        
        if result["success"]:
            message = f"Cancelled {len(result['cancelled_tasks'])} tasks for file {file_id}"
            if result["active_tasks_found"] == 0:
                message = f"No active processing tasks found for file {file_id}"
        else:
            message = f"Failed to cancel tasks for file {file_id}"
        
        return {
            "message": message,
            "file_id": str(file_id),
            "results": result
        }
        
    except Exception as e:
        logger.error(f"Failed to cancel processing for file {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Task cancellation failed")


@router.get("/active-file-tasks")
async def get_active_file_processing_tasks(
    current_user: User = Depends(get_current_user)
):
    """
    Get all currently active file processing tasks
    """
    try:
        task_canceller = TaskCancellationService()
        active_tasks = task_canceller.get_active_file_processing_tasks()
        
        return {
            "active_files": len(active_tasks),
            "tasks": active_tasks
        }
        
    except Exception as e:
        logger.error(f"Failed to get active tasks: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve active tasks")


@router.post("/cancel-multiple-files")
async def cancel_multiple_file_processing(
    file_ids: List[str],
    current_user: User = Depends(get_current_user)
):
    """
    Cancel processing tasks for multiple files
    """
    if len(file_ids) > 50:
        raise HTTPException(status_code=400, detail="Cannot cancel more than 50 files at once")
    
    try:
        task_canceller = TaskCancellationService()
        results = task_canceller.cancel_all_file_tasks_by_pattern(file_ids)
        
        return {
            "message": f"Processed {results['files_processed']} files, cancelled {results['total_cancelled']} tasks",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Failed to cancel multiple file processing: {str(e)}")
        raise HTTPException(status_code=500, detail="Batch task cancellation failed")