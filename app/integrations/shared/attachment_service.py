#!/usr/bin/env python3
"""
Shared Attachment Service
Common utilities for handling attachments across different integrations
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File
from app.services.file_service import FileService

logger = logging.getLogger(__name__)


class BaseAttachmentService:
    """
    Shared utilities for attachment handling across integrations.
    Provides common validation, access control, and file operations.
    """
    
    def __init__(self):
        self.file_service = FileService()
    
    async def validate_file_access(
        self, 
        db: AsyncSession,
        file_id: UUID, 
        user_id: UUID, 
        organization_id: UUID
    ) -> Dict[str, Any]:
        """
        Common file access validation logic.
        
        Args:
            db: Database session
            file_id: ID of file to validate
            user_id: ID of user requesting access
            organization_id: Organization ID for boundary checking
            
        Returns:
            Dict containing:
            - success: bool
            - file: File object if successful
            - error_message: str if failed
        """
        try:
            # Get file object
            file_obj = await self.file_service.get_file(db, file_id)
            
            if not file_obj:
                return {
                    "success": False,
                    "file": None,
                    "error_message": "File not found"
                }
            
            # Validate organization boundary
            if file_obj.organization_id != organization_id:
                logger.warning(
                    f"Access denied for file {file_id} - organization mismatch. "
                    f"File org: {file_obj.organization_id}, User org: {organization_id}"
                )
                return {
                    "success": False,
                    "file": file_obj,
                    "error_message": "Access denied - file belongs to different organization"
                }
            
            # Check file status
            if file_obj.status.value == "deleted":
                return {
                    "success": False,
                    "file": file_obj,
                    "error_message": "File has been deleted"
                }
            
            if file_obj.status.value == "processing":
                return {
                    "success": False,
                    "file": file_obj,
                    "error_message": "File is still processing"
                }
            
            return {
                "success": True,
                "file": file_obj,
                "error_message": None
            }
            
        except Exception as e:
            logger.error(f"Error validating file access for {file_id}: {e}")
            return {
                "success": False,
                "file": None,
                "error_message": f"File access validation failed: {str(e)}"
            }
    
    async def get_attachment_content(
        self, 
        db: AsyncSession,
        file_id: UUID
    ) -> Optional[bytes]:
        """
        Common file content retrieval.
        
        Args:
            db: Database session
            file_id: ID of file to retrieve
            
        Returns:
            File content as bytes or None if not available
        """
        try:
            content = await self.file_service.get_file_content(db, file_id)
            if not content:
                logger.error(f"File content not available for {file_id}")
                return None
            
            return content
            
        except Exception as e:
            logger.error(f"Error retrieving file content for {file_id}: {e}")
            return None
    
    async def validate_attachment_constraints(
        self,
        file_obj: File,
        max_file_size: Optional[int] = None,
        allowed_mime_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate attachment against external service constraints.
        
        Args:
            file_obj: File object to validate
            max_file_size: Maximum file size in bytes (e.g., JIRA default 10MB)
            allowed_mime_types: List of allowed MIME types
            
        Returns:
            Dict containing validation result:
            - success: bool
            - error_message: str if failed
        """
        try:
            # Check file size if constraint provided
            if max_file_size and file_obj.file_size > max_file_size:
                size_mb = file_obj.file_size / (1024 * 1024)
                limit_mb = max_file_size / (1024 * 1024)
                return {
                    "success": False,
                    "error_message": f"File size ({size_mb:.1f}MB) exceeds limit ({limit_mb:.1f}MB)"
                }
            
            # Check MIME type if constraint provided
            if allowed_mime_types and file_obj.mime_type not in allowed_mime_types:
                return {
                    "success": False,
                    "error_message": f"File type '{file_obj.mime_type}' is not supported"
                }
            
            # Check for required metadata
            if not file_obj.filename or not file_obj.mime_type:
                return {
                    "success": False,
                    "error_message": "File metadata is incomplete"
                }
            
            return {
                "success": True,
                "error_message": None
            }
            
        except Exception as e:
            logger.error(f"Error validating attachment constraints: {e}")
            return {
                "success": False,
                "error_message": f"Validation error: {str(e)}"
            }
    
    def get_safe_filename(self, filename: str) -> str:
        """
        Ensure filename is safe for external systems.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for upload
        """
        import re
        
        # Remove or replace potentially problematic characters
        # Keep alphanumeric, dots, hyphens, underscores
        safe_name = re.sub(r'[^\w\-_\.]', '_', filename)
        
        # Ensure it doesn't start with a dot (hidden file)
        if safe_name.startswith('.'):
            safe_name = 'file_' + safe_name
        
        # Limit length
        if len(safe_name) > 255:
            name_parts = safe_name.rsplit('.', 1)
            if len(name_parts) == 2:
                # Has extension
                name, ext = name_parts
                max_name_len = 255 - len(ext) - 1
                safe_name = name[:max_name_len] + '.' + ext
            else:
                safe_name = safe_name[:255]
        
        return safe_name