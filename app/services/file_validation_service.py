#!/usr/bin/env python3
"""
File Validation Service for attachment validation
"""

from typing import List, Dict, Any
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import logging

from app.models.file import File, FileStatus

logger = logging.getLogger(__name__)


class FileValidationService:
    """Service for validating file attachments"""
    
    async def validate_file_attachments(
        self,
        db: AsyncSession,
        attachments: List[Dict[str, Any]],
        organization_id: UUID
    ) -> List[UUID]:
        """
        Validate file attachments and return valid file IDs
        
        Args:
            db: Database session
            attachments: List of attachment objects with file_id
            organization_id: Organization ID for access control
            
        Returns:
            List of validated file UUIDs
            
        Raises:
            HTTPException: If any file is invalid or inaccessible
        """
        if not attachments:
            return []
        
        # Extract file_ids from attachment objects
        try:
            file_ids = []
            for att in attachments:
                file_id_value = att["file_id"]
                # Handle both UUID objects and string values
                if isinstance(file_id_value, UUID):
                    file_ids.append(file_id_value)
                else:
                    file_ids.append(UUID(file_id_value))
        except (KeyError, ValueError, TypeError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid attachment format. Expected [{{\"file_id\":\"uuid\"}}]: {e}"
            )
        
        # Batch query for file validation
        files = await self.get_valid_files(db, file_ids, organization_id)
        
        # Check that all requested files were found and are valid
        if len(files) != len(file_ids):
            found_ids = {f.id for f in files}
            invalid_ids = set(file_ids) - found_ids
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid or inaccessible files: {[str(id) for id in invalid_ids]}"
            )
        
        logger.info(f"Validated {len(file_ids)} file attachments for organization {organization_id}")
        return file_ids
    
    async def get_valid_files(self, db: AsyncSession, file_ids: List[UUID], org_id: UUID):
        """
        Get files that exist, are accessible, and not deleted/quarantined
        
        Args:
            db: Database session
            file_ids: List of file UUIDs to validate
            org_id: Organization ID for access control
            
        Returns:
            List of valid File objects
        """
        query = select(File).where(
            and_(
                File.id.in_(file_ids),
                File.organization_id == org_id,
                File.status != FileStatus.DELETED,
                File.status != FileStatus.QUARANTINED
            )
        )
        result = await db.execute(query)
        return result.scalars().all()
    
    async def validate_single_file_attachment(
        self,
        db: AsyncSession,
        file_id: UUID,
        organization_id: UUID
    ) -> File:
        """
        Validate a single file attachment
        
        Args:
            db: Database session
            file_id: File UUID to validate
            organization_id: Organization ID for access control
            
        Returns:
            File object if valid
            
        Raises:
            HTTPException: If file is invalid or inaccessible
        """
        files = await self.get_valid_files(db, [file_id], organization_id)
        
        if not files:
            raise HTTPException(
                status_code=404,
                detail=f"File {file_id} not found or not accessible"
            )
        
        return files[0]
    
    async def format_attachments_for_storage(
        self, 
        attachments: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Format attachment objects for storage in database
        
        Args:
            attachments: List of attachment objects (can contain UUID objects or strings)
            
        Returns:
            List of formatted attachment objects with string file_ids
        """
        if not attachments:
            return []
            
        formatted = []
        for att in attachments:
            if "file_id" not in att:
                raise HTTPException(
                    status_code=400,
                    detail="Each attachment must have 'file_id' field"
                )
            
            file_id_value = att["file_id"]
            
            # Handle both UUID objects and string values
            if isinstance(file_id_value, UUID):
                file_id_str = str(file_id_value)
            else:
                file_id_str = str(file_id_value)
                # Validate string is a valid UUID
                try:
                    UUID(file_id_str)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid file_id format: {file_id_str}"
                    )
            
            formatted.append({"file_id": file_id_str})
        
        return formatted
    
    async def get_attachment_files_info(
        self,
        db: AsyncSession,
        attachments: List[Dict[str, str]],
        organization_id: UUID
    ) -> List[File]:
        """
        Get file information for attachment display
        
        Args:
            db: Database session
            attachments: List of attachment objects with file_id
            organization_id: Organization ID for access control
            
        Returns:
            List of File objects with information
        """
        if not attachments:
            return []
        
        try:
            file_ids = [UUID(att["file_id"]) for att in attachments]
        except (KeyError, ValueError) as e:
            logger.warning(f"Invalid attachment format in stored data: {e}")
            return []
        
        return await self.get_valid_files(db, file_ids, organization_id)