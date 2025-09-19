#!/usr/bin/env python3
"""
JIRA Attachment Service
Handles uploading ticket attachments to JIRA issues
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.file_service import FileService
from .jira_integration import JiraIntegration

logger = logging.getLogger(__name__)


class AttachmentResult:
    """Result of a single attachment upload"""
    
    def __init__(
        self,
        file_id: UUID,
        filename: str,
        success: bool,
        jira_attachment_id: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        self.file_id = file_id
        self.filename = filename  
        self.success = success
        self.jira_attachment_id = jira_attachment_id
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "file_id": str(self.file_id),
            "filename": self.filename,
            "upload_status": "success" if self.success else "failed",
            "jira_attachment_id": self.jira_attachment_id,
            "error_message": self.error_message
        }


class AttachmentSummary:
    """Summary of all attachment upload operations"""
    
    def __init__(self, results: List[AttachmentResult]):
        self.results = results
        self.total_files = len(results)
        self.successful_uploads = sum(1 for r in results if r.success)
        self.failed_uploads = sum(1 for r in results if not r.success)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "total_files": self.total_files,
            "successful_uploads": self.successful_uploads,
            "failed_uploads": self.failed_uploads
        }


class JiraAttachmentService:
    """Service for uploading attachments to JIRA issues"""
    
    def __init__(self):
        self.file_service = FileService()
    
    async def upload_ticket_attachments(
        self,
        db: AsyncSession,
        jira: JiraIntegration,
        issue_key: str,
        file_ids: List[UUID],
        user_id: UUID,
        organization_id: UUID
    ) -> AttachmentSummary:
        """
        Upload multiple files as JIRA attachments.
        
        Args:
            db: Database session
            jira: JIRA integration instance
            issue_key: JIRA issue key (e.g., "TEST-123")
            file_ids: List of file IDs to upload
            user_id: User performing the upload
            organization_id: Organization ID for access control
            
        Returns:
            AttachmentSummary with results of all upload operations
        """
        if not file_ids:
            return AttachmentSummary([])
        
        results = []
        
        for file_id in file_ids:
            try:
                result = await self.upload_single_attachment(
                    db=db,
                    jira=jira,
                    issue_key=issue_key,
                    file_id=file_id,
                    user_id=user_id,
                    organization_id=organization_id
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to upload attachment {file_id} to {issue_key}: {e}")
                # Create a failure result for this file
                try:
                    file_obj = await self.file_service.get_file(db, file_id)
                    filename = file_obj.filename if file_obj else "unknown"
                except:
                    filename = "unknown"
                    
                results.append(AttachmentResult(
                    file_id=file_id,
                    filename=filename,
                    success=False,
                    error_message=str(e)
                ))
        
        summary = AttachmentSummary(results)
        logger.info(f"Attachment upload summary for {issue_key}: {summary.successful_uploads}/{summary.total_files} successful")
        
        return summary
    
    async def upload_single_attachment(
        self,
        db: AsyncSession,
        jira: JiraIntegration,
        issue_key: str,
        file_id: UUID,
        user_id: UUID,
        organization_id: UUID
    ) -> AttachmentResult:
        """
        Upload a single file as a JIRA attachment with full error handling.
        
        Args:
            db: Database session
            jira: JIRA integration instance
            issue_key: JIRA issue key (e.g., "TEST-123")
            file_id: File ID to upload
            user_id: User performing the upload
            organization_id: Organization ID for access control
            
        Returns:
            AttachmentResult with upload status
        """
        try:
            # 1. Get file metadata and validate access
            file_obj = await self.file_service.get_file(db, file_id)
            if not file_obj:
                return AttachmentResult(
                    file_id=file_id,
                    filename="unknown",
                    success=False,
                    error_message="File not found"
                )
            
            # 2. Validate organization access
            if file_obj.organization_id != organization_id:
                return AttachmentResult(
                    file_id=file_id,
                    filename=file_obj.filename,
                    success=False,
                    error_message="Access denied - file belongs to different organization"
                )
            
            # 3. Check file status  
            if file_obj.status.value == "deleted":
                return AttachmentResult(
                    file_id=file_id,
                    filename=file_obj.filename,
                    success=False,
                    error_message="File has been deleted"
                )
            
            # 4. Get file content using the enhanced method for external uploads
            try:
                file_content = await self.file_service.get_file_content_for_external_upload(
                    db=db,
                    file_id=file_id,
                    user_id=user_id,
                    organization_id=organization_id
                )
                if not file_content:
                    return AttachmentResult(
                        file_id=file_id,
                        filename=file_obj.filename,
                        success=False,
                        error_message="File content not available"
                    )
            except PermissionError as e:
                return AttachmentResult(
                    file_id=file_id,
                    filename=file_obj.filename,
                    success=False,
                    error_message=f"Access denied: {str(e)}"
                )
            except ValueError as e:
                return AttachmentResult(
                    file_id=file_id,
                    filename=file_obj.filename,
                    success=False,
                    error_message=f"File validation failed: {str(e)}"
                )
            
            # 5. Upload to JIRA
            jira_attachments = await jira.add_attachment(
                issue_key=issue_key,
                file_content=file_content,
                filename=file_obj.filename
            )
            
            # 6. Extract attachment ID from response
            jira_attachment_id = None
            if jira_attachments and len(jira_attachments) > 0:
                jira_attachment_id = jira_attachments[0].get("id")
            
            logger.info(f"✅ Successfully uploaded {file_obj.filename} to {issue_key}")
            
            return AttachmentResult(
                file_id=file_id,
                filename=file_obj.filename,
                success=True,
                jira_attachment_id=jira_attachment_id
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to upload attachment {file_id} to {issue_key}: {e}")
            
            # Try to get filename for error response
            filename = "unknown"
            try:
                file_obj = await self.file_service.get_file(db, file_id)
                if file_obj:
                    filename = file_obj.filename
            except:
                pass
            
            return AttachmentResult(
                file_id=file_id,
                filename=filename,
                success=False,
                error_message=str(e)
            )