#!/usr/bin/env python3
"""
Local filesystem storage backend implementation
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

import aiofiles

from app.config.settings import get_settings

from .backend import StorageBackend


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage implementation"""
    
    def __init__(self, base_path: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize local storage backend
        
        Args:
            base_path: Base directory for file storage (defaults to settings.upload_directory)
            base_url: Base URL for serving files (defaults to /api/v1/storage/)
        """
        self.settings = get_settings()
        self.base_path = Path(base_path or self.settings.upload_directory)
        self.base_url = base_url or "/api/v1/storage"
        
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def upload_file(
        self, 
        content: bytes, 
        key: str, 
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Upload file to local filesystem"""
        file_path = self.base_path / key
        
        # Ensure parent directories exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file content
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Store metadata if provided
        if metadata or content_type:
            metadata_dict = metadata or {}
            if content_type:
                metadata_dict['content_type'] = content_type
            metadata_dict['uploaded_at'] = datetime.now().isoformat()
            metadata_dict['file_size'] = len(content)
            
            metadata_path = file_path.with_suffix(file_path.suffix + '.meta')
            async with aiofiles.open(metadata_path, 'w') as f:
                await f.write(json.dumps(metadata_dict, indent=2))
        
        # Return access URL
        return f"{self.base_url}/{quote(key)}"
    
    async def download_file(self, key: str) -> Optional[bytes]:
        """Download file from local filesystem"""
        file_path = self.base_path / key
        
        if not file_path.exists() or not file_path.is_file():
            return None
        
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                return await f.read()
        except Exception:
            return None
    
    async def delete_file(self, key: str) -> bool:
        """Delete file from local filesystem"""
        file_path = self.base_path / key
        metadata_path = file_path.with_suffix(file_path.suffix + '.meta')
        
        success = True
        
        # Delete main file
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            success = False
        
        # Delete metadata file if exists
        try:
            if metadata_path.exists():
                metadata_path.unlink()
        except Exception:
            pass  # Metadata deletion failure is not critical
        
        return success
    
    async def file_exists(self, key: str) -> bool:
        """Check if file exists in local filesystem"""
        file_path = self.base_path / key
        return file_path.exists() and file_path.is_file()
    
    async def get_file_url(
        self, 
        key: str, 
        expires_in: Optional[int] = None,
        public: bool = False
    ) -> str:
        """Get URL for local file (ignores expires_in as local URLs don't expire)"""
        return f"{self.base_url}/{quote(key)}"
    
    async def get_file_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get file info from local filesystem"""
        file_path = self.base_path / key
        
        if not file_path.exists() or not file_path.is_file():
            return None
        
        # Get basic file stats
        stat_result = file_path.stat()
        info = {
            'size': stat_result.st_size,
            'modified_time': datetime.fromtimestamp(stat_result.st_mtime).isoformat(),
            'created_time': datetime.fromtimestamp(stat_result.st_ctime).isoformat(),
        }
        
        # Load metadata if available
        metadata_path = file_path.with_suffix(file_path.suffix + '.meta')
        if metadata_path.exists():
            try:
                async with aiofiles.open(metadata_path, 'r') as f:
                    metadata_content = await f.read()
                    metadata = json.loads(metadata_content)
                    info.update(metadata)
            except Exception:
                pass  # Metadata reading failure is not critical
        
        return info
    
    async def list_files(
        self, 
        prefix: str = "", 
        limit: Optional[int] = None
    ) -> list[str]:
        """List files in local filesystem with prefix filter"""
        prefix_path = self.base_path / prefix if prefix else self.base_path
        
        files = []
        try:
            if prefix_path.is_dir():
                # List all files recursively under prefix directory
                for file_path in prefix_path.rglob('*'):
                    if file_path.is_file() and not file_path.name.endswith('.meta'):
                        # Get relative path from base_path
                        relative_path = file_path.relative_to(self.base_path)
                        files.append(str(relative_path))
                        
                        if limit and len(files) >= limit:
                            break
            elif prefix_path.is_file():
                # Single file match
                relative_path = prefix_path.relative_to(self.base_path)
                files.append(str(relative_path))
                
        except Exception:
            pass  # Return empty list on error
        
        return sorted(files)
    
    @property
    def backend_type(self) -> str:
        """Get backend type identifier"""
        return "local"
    
    @property
    def supports_public_urls(self) -> bool:
        """Local backend serves URLs through the application"""
        return True
    
    @property
    def supports_signed_urls(self) -> bool:
        """Local backend doesn't support URL expiration"""
        return False