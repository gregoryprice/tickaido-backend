#!/usr/bin/env python3
"""
File Cleanup API endpoints for administrative tasks
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.services.file_cleanup_service import file_cleanup_service

router = APIRouter(prefix="/admin/file-cleanup", tags=["File Cleanup"])


@router.post("/orphaned-files/scan")
async def scan_orphaned_files(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Scan for orphaned files that are no longer referenced by any thread or ticket.
    This is a dry-run operation that only counts orphaned files without deleting them.
    """
    try:
        orphaned_count = await file_cleanup_service.cleanup_orphaned_files(
            db=db,
            organization_id=current_user.organization_id,
            dry_run=True
        )
        
        return {
            "message": "Orphaned file scan completed",
            "organization_id": str(current_user.organization_id),
            "orphaned_files_found": orphaned_count,
            "action": "scan_only"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan orphaned files: {str(e)}")


@router.delete("/orphaned-files/cleanup")
async def cleanup_orphaned_files(
    confirm: bool = Query(False, description="Must be True to actually delete files"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Delete orphaned files that are no longer referenced by any thread or ticket.
    Requires confirmation parameter to prevent accidental deletion.
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Must set confirm=True to delete orphaned files"
        )
    
    try:
        deleted_count = await file_cleanup_service.cleanup_orphaned_files(
            db=db,
            organization_id=current_user.organization_id,
            dry_run=False
        )
        
        return {
            "message": "Orphaned file cleanup completed",
            "organization_id": str(current_user.organization_id),
            "files_deleted": deleted_count,
            "action": "cleanup_performed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup orphaned files: {str(e)}")