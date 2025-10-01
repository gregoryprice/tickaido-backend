#!/usr/bin/env python3
"""
Abstract storage backend interface
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class StorageBackend(ABC):
    """Abstract storage backend interface for unified file storage"""
    
    @abstractmethod
    async def upload_file(
        self, 
        content: bytes, 
        key: str, 
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Upload file and return access URL
        
        Args:
            content: File content as bytes
            key: Storage key/path for the file
            content_type: MIME type of the file
            metadata: Additional metadata to store with file
            
        Returns:
            Access URL for the uploaded file
        """
        pass
    
    @abstractmethod
    async def download_file(self, key: str) -> Optional[bytes]:
        """
        Download file by key
        
        Args:
            key: Storage key/path for the file
            
        Returns:
            File content as bytes, or None if not found
        """
        pass
    
    @abstractmethod
    async def delete_file(self, key: str) -> bool:
        """
        Delete file by key
        
        Args:
            key: Storage key/path for the file
            
        Returns:
            True if file was deleted or didn't exist, False on error
        """
        pass
    
    @abstractmethod
    async def file_exists(self, key: str) -> bool:
        """
        Check if file exists
        
        Args:
            key: Storage key/path for the file
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_file_url(
        self, 
        key: str, 
        expires_in: Optional[int] = None,
        public: bool = False
    ) -> str:
        """
        Get public or signed URL for file
        
        Args:
            key: Storage key/path for the file
            expires_in: URL expiration time in seconds (for signed URLs)
            public: Whether to return a public URL (if supported)
            
        Returns:
            URL for accessing the file
        """
        pass
    
    @abstractmethod
    async def get_file_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata/info
        
        Args:
            key: Storage key/path for the file
            
        Returns:
            Dictionary with file info (size, content_type, modified_time, etc.)
            or None if file not found
        """
        pass
    
    @abstractmethod
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
        pass
    
    @property
    @abstractmethod
    def backend_type(self) -> str:
        """
        Get backend type identifier
        
        Returns:
            Backend type string (e.g., 'local', 's3')
        """
        pass
    
    @property
    @abstractmethod
    def supports_public_urls(self) -> bool:
        """
        Check if backend supports public URLs
        
        Returns:
            True if backend can serve public URLs directly
        """
        pass
    
    @property
    @abstractmethod
    def supports_signed_urls(self) -> bool:
        """
        Check if backend supports signed URLs
        
        Returns:
            True if backend can generate signed URLs with expiration
        """
        pass