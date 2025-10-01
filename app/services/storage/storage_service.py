#!/usr/bin/env python3
"""
Storage service for generic file management operations
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import UploadFile

from app.config.settings import get_settings

from .backend import StorageBackend


class StorageService:
    """Generic storage service for file operations through pluggable backends"""
    
    def __init__(self, backend: StorageBackend):
        """
        Initialize storage service
        
        Args:
            backend: Storage backend implementation
        """
        self.backend = backend
        self.settings = get_settings()
    
    async def upload_file(
        self,
        file: UploadFile,
        storage_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Upload a file to storage
        
        Args:
            file: Upload file object
            storage_key: Storage key/path for the file
            metadata: Optional metadata to store with file
            
        Returns:
            File URL for access
            
        Raises:
            HTTPException: On validation or upload errors
        """
        # Read file content
        content = await file.read()
        await file.seek(0)
        
        # Validate file
        await self._validate_file(file, content)
        
        # Upload file
        file_url = await self.backend.upload_file(
            content=content,
            key=storage_key,
            content_type=file.content_type,
            metadata=metadata
        )
        
        return file_url
    
    async def upload_content(
        self,
        content: bytes,
        storage_key: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Upload raw content to storage
        
        Args:
            content: Raw file content
            storage_key: Storage key/path for the file
            content_type: MIME type of content
            metadata: Optional metadata to store with file
            
        Returns:
            File URL for access
        """
        return await self.backend.upload_file(
            content=content,
            key=storage_key,
            content_type=content_type,
            metadata=metadata
        )
    
    async def download_file(self, storage_key: str) -> Optional[bytes]:
        """
        Download file content from storage
        
        Args:
            storage_key: Storage key/path for the file
            
        Returns:
            File content or None if not found
        """
        return await self.backend.download_file(storage_key)
    
    async def get_file_url(
        self,
        storage_key: str,
        expires_in: Optional[int] = None,
        public: bool = False
    ) -> Optional[str]:
        """
        Get file URL
        
        Args:
            storage_key: Storage key/path for the file
            expires_in: URL expiration in seconds
            public: Whether to return public URL
            
        Returns:
            File URL or None if not found
        """
        if not await self.backend.file_exists(storage_key):
            return None
        
        return await self.backend.get_file_url(
            storage_key,
            expires_in=expires_in,
            public=public
        )
    
    async def delete_file(self, storage_key: str) -> bool:
        """
        Delete file from storage
        
        Args:
            storage_key: Storage key/path for the file
            
        Returns:
            True if deletion was successful
        """
        return await self.backend.delete_file(storage_key)
    
    async def file_exists(self, storage_key: str) -> bool:
        """
        Check if file exists in storage
        
        Args:
            storage_key: Storage key/path for the file
            
        Returns:
            True if file exists
        """
        return await self.backend.file_exists(storage_key)
    
    async def get_file_info(self, storage_key: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata/info
        
        Args:
            storage_key: Storage key/path for the file
            
        Returns:
            Dictionary with file info or None if not found
        """
        return await self.backend.get_file_info(storage_key)
    
    async def list_files(
        self, 
        prefix: str = "", 
        limit: Optional[int] = None
    ) -> list[str]:
        """
        List files with optional prefix filter
        
        Args:
            prefix: Key prefix to filter by
            limit: Maximum number of files to return
            
        Returns:
            List of file keys matching the criteria
        """
        return await self.backend.list_files(prefix, limit)
    
    async def generate_storage_key(
        self,
        file_type: str,
        filename: str,
        entity_id: Optional[UUID] = None
    ) -> str:
        """
        Generate a storage key for a file
        
        Args:
            file_type: Type of file (attachments, documents, etc.)
            filename: Original filename
            entity_id: Optional entity ID for organization
            
        Returns:
            Generated storage key
        """
        file_id = uuid.uuid4()
        file_extension = Path(filename).suffix
        
        if file_type == "attachments":
            # Organize by date for better structure
            now = datetime.now()
            return f"attachments/{now.year}/{now.month:02d}/{file_id}{file_extension}"
        elif file_type == "documents":
            return f"documents/{file_id}{file_extension}"
        elif file_type == "temp":
            return f"temp/{file_id}{file_extension}"
        else:
            return f"{file_type}/{file_id}{file_extension}"
    
    async def _validate_file(self, file: UploadFile, content: bytes):
        """Validate file meets basic requirements"""
        # Check file size
        if len(content) > self.settings.max_file_size:
            raise ValueError(f"File size {len(content)} exceeds maximum allowed size {self.settings.max_file_size}")
        
        # Check MIME type
        if file.content_type not in self.settings.allowed_file_types:
            raise ValueError(f"File type {file.content_type} not allowed")
        
        # Basic security validation
        filename = file.filename or "unknown"
        dangerous_chars = '<>"|?*'
        if any(char in filename for char in dangerous_chars):
            raise ValueError(f"Filename contains invalid characters: {filename}")
        
        if len(content) < 1:
            raise ValueError("File is empty")
    
    @property
    def backend_type(self) -> str:
        """Get underlying backend type"""
        return self.backend.backend_type
    
    @property
    def supports_signed_urls(self) -> bool:
        """Check if backend supports signed URLs"""
        return self.backend.supports_signed_urls
    
    @property
    def supports_public_urls(self) -> bool:
        """Check if backend supports public URLs"""
        return self.backend.supports_public_urls