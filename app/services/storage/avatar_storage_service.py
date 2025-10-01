#!/usr/bin/env python3
"""
Avatar Storage Service - Handles avatar-specific storage operations with thumbnail generation
"""

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional
from uuid import UUID

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps

from app.config.settings import get_settings

from .backend import StorageBackend


class AvatarStorageService:
    """Service for avatar-specific storage operations including thumbnail generation"""
    
    def __init__(self, backend: StorageBackend):
        """
        Initialize avatar storage service
        
        Args:
            backend: Storage backend implementation
        """
        self.backend = backend
        self.settings = get_settings()
        
        # Avatar configuration
        self.max_avatar_size = 5 * 1024 * 1024  # 5MB limit
        self.allowed_avatar_formats = [
            'image/jpeg', 
            'image/jpg', 
            'image/png', 
            'image/gif', 
            'image/heic',
            'image/webp'
        ]
        self.allowed_avatar_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.heic', '.webp'}
        self.thumbnail_sizes = {
            'small': (32, 32),    # Chat avatars
            'medium': (150, 150), # Profile cards
            'large': (300, 300)   # Full profile view
        }
    
    async def upload_user_avatar(
        self,
        user_id: UUID,
        file: UploadFile
    ) -> Dict[str, str]:
        """
        Upload and process user avatar with thumbnails
        
        Args:
            user_id: ID of the user
            file: Upload file object
            
        Returns:
            Dictionary with avatar URLs for different sizes
            
        Raises:
            HTTPException: On validation or processing errors
        """
        return await self._upload_avatar(user_id, file, "users")
    
    async def upload_agent_avatar(
        self,
        agent_id: UUID,
        file: UploadFile
    ) -> Dict[str, str]:
        """
        Upload and process agent avatar with thumbnails
        
        Args:
            agent_id: ID of the agent
            file: Upload file object
            
        Returns:
            Dictionary with avatar URLs for different sizes
            
        Raises:
            HTTPException: On validation or processing errors
        """
        return await self._upload_avatar(agent_id, file, "agents")
    
    async def _upload_avatar(
        self,
        entity_id: UUID,
        file: UploadFile,
        entity_type: str
    ) -> Dict[str, str]:
        """
        Upload and process avatar with thumbnails
        
        Args:
            entity_id: ID of the entity (user or agent)
            file: Upload file object
            entity_type: Type of entity ("users" or "agents")
            
        Returns:
            Dictionary with avatar URLs for different sizes
        """
        # Read file content
        content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        # Validate file
        await self._validate_avatar_file(file, content)
        
        # Validate image security
        filename = file.filename or "unknown"
        self._validate_image_security(content, filename)
        
        # Generate file extension
        file_extension = Path(filename).suffix.lower()
        if not file_extension:
            content_type = file.content_type or "image/jpeg"
            file_extension = self._detect_extension_from_mime(content_type)
        
        # Generate storage keys and upload all sizes
        avatar_urls = {}
        timestamp = int(datetime.now().timestamp())
        
        # Upload original
        original_key = f"avatars/{entity_type}/{entity_id}/original{file_extension}"
        original_url = await self.backend.upload_file(
            content=content,
            key=original_key,
            content_type=file.content_type,
            metadata={
                "entity_id": str(entity_id),
                "entity_type": entity_type,
                "original_filename": filename,
                "timestamp": str(timestamp)
            }
        )
        avatar_urls["original"] = original_url
        
        # Generate and upload thumbnails
        thumbnail_urls = await self._generate_and_upload_thumbnails(
            content, entity_id, entity_type, file_extension, timestamp
        )
        avatar_urls.update(thumbnail_urls)
        
        return avatar_urls
    
    async def _generate_and_upload_thumbnails(
        self,
        content: bytes,
        entity_id: UUID,
        entity_type: str,
        file_extension: str,
        timestamp: int
    ) -> Dict[str, str]:
        """Generate and upload avatar thumbnails"""
        thumbnail_urls = {}
        
        try:
            with Image.open(BytesIO(content)) as original_img:
                # Handle EXIF orientation
                img = ImageOps.exif_transpose(original_img)
                if img is None:
                    img = original_img
                
                # Convert to RGB if necessary
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                
                # Generate each thumbnail size
                for size_name, dimensions in self.thumbnail_sizes.items():
                    thumbnail_key = f"avatars/{entity_type}/{entity_id}/{size_name}{file_extension}"
                    
                    # Create thumbnail with proper aspect ratio
                    thumbnail = img.copy()
                    thumbnail.thumbnail(dimensions, Image.Resampling.LANCZOS)
                    
                    # Create a square thumbnail with padding if needed
                    square_img = Image.new('RGB', dimensions, (255, 255, 255))
                    
                    # Center the thumbnail
                    x = (dimensions[0] - thumbnail.size[0]) // 2
                    y = (dimensions[1] - thumbnail.size[1]) // 2
                    square_img.paste(thumbnail, (x, y))
                    
                    # Convert to bytes
                    thumbnail_buffer = BytesIO()
                    square_img.save(thumbnail_buffer, format='JPEG', optimize=True, quality=85)
                    thumbnail_content = thumbnail_buffer.getvalue()
                    
                    # Upload thumbnail
                    thumbnail_url = await self.backend.upload_file(
                        content=thumbnail_content,
                        key=thumbnail_key,
                        content_type="image/jpeg",
                        metadata={
                            "entity_id": str(entity_id),
                            "entity_type": entity_type,
                            "size": size_name,
                            "timestamp": str(timestamp)
                        }
                    )
                    thumbnail_urls[size_name] = thumbnail_url
                
            return thumbnail_urls
            
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Failed to generate thumbnails: {str(e)}")
    
    async def get_avatar_url(
        self,
        entity_id: UUID,
        entity_type: str,
        size: str = "medium",
        expires_in: Optional[int] = None
    ) -> Optional[str]:
        """
        Get avatar URL for entity
        
        Args:
            entity_id: ID of entity (user or agent)
            entity_type: Type of entity ("users" or "agents")
            size: Avatar size (small, medium, large, original)
            expires_in: URL expiration time in seconds (for signed URLs)
            
        Returns:
            Avatar URL or None if not found
        """
        if size not in list(self.thumbnail_sizes.keys()) + ["original"]:
            size = "medium"
        
        avatar_key = f"avatars/{entity_type}/{entity_id}/{size}.jpg"
        
        # Check if file exists
        if not await self.backend.file_exists(avatar_key):
            # Try with original extension detection
            for ext in ['.png', '.jpeg', '.gif', '.webp']:
                test_key = f"avatars/{entity_type}/{entity_id}/{size}{ext}"
                if await self.backend.file_exists(test_key):
                    avatar_key = test_key
                    break
            else:
                return None
        
        # Get URL (public or signed)
        return await self.backend.get_file_url(
            avatar_key, 
            expires_in=expires_in,
            public=(expires_in is None)
        )
    
    async def delete_avatar(
        self,
        entity_id: UUID,
        entity_type: str
    ) -> bool:
        """
        Delete all avatar files for entity
        
        Args:
            entity_id: ID of entity (user or agent)
            entity_type: Type of entity ("users" or "agents")
            
        Returns:
            True if deletion was successful
        """
        success = True
        
        # Delete all sizes
        sizes_to_delete = list(self.thumbnail_sizes.keys()) + ["original"]
        
        for size in sizes_to_delete:
            # Try different extensions
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                avatar_key = f"avatars/{entity_type}/{entity_id}/{size}{ext}"
                try:
                    if await self.backend.file_exists(avatar_key):
                        delete_success = await self.backend.delete_file(avatar_key)
                        if not delete_success:
                            success = False
                except Exception:
                    success = False
        
        return success
    
    async def _validate_avatar_file(self, file: UploadFile, content: bytes):
        """Validate avatar file meets requirements"""
        # Check file size
        if len(content) > self.max_avatar_size:
            raise ValueError(f"File size {len(content)} exceeds maximum allowed size {self.max_avatar_size}")
        
        # Check MIME type
        if file.content_type not in self.allowed_avatar_formats:
            raise ValueError(f"File type {file.content_type} not allowed. Allowed types: {self.allowed_avatar_formats}")
        
        # Check file extension and validate filename characters
        filename = file.filename or "unknown"
        
        # Validate filename for security
        dangerous_chars = '<>"|?*'
        if any(char in filename for char in dangerous_chars):
            raise ValueError(f"Filename contains invalid characters: {filename}")
        
        file_extension = Path(filename).suffix.lower()
        if file_extension and file_extension not in self.allowed_avatar_extensions:
            raise ValueError(f"File extension {file_extension} not allowed")
        
        # Check minimum size
        if len(content) < 100:
            raise ValueError("File too small to be a valid image")
    
    def _validate_image_security(self, content: bytes, filename: str):
        """Validate image security using PIL"""
        try:
            with Image.open(BytesIO(content)) as img:
                img_format = img.format
                if img_format is None:
                    raise ValueError("File is not a valid image format")
        except Exception:
            raise ValueError("File is not a valid image format")
        
        # Verify image with PIL
        try:
            with Image.open(BytesIO(content)) as img:
                img.verify()
                
                # Check for reasonable dimensions
                if hasattr(img, 'size'):
                    width, height = img.size
                    max_dimension = 10000
                    if width > max_dimension or height > max_dimension:
                        raise ValueError(f"Image dimensions too large: {width}x{height}")
                    
                    if width < 16 or height < 16:
                        raise ValueError(f"Image dimensions too small: {width}x{height}")
        
        except Exception as e:
            if "cannot identify image file" in str(e).lower():
                raise ValueError("Invalid or corrupted image file")
            elif "Image dimensions too" in str(e):
                raise e
            else:
                raise ValueError(f"Image validation failed: {str(e)}")
        
        # Check for suspicious content patterns
        suspicious_patterns = [b'<script', b'javascript:', b'vbscript:', b'<?php']
        content_lower = content[:1024].lower()
        for pattern in suspicious_patterns:
            if pattern in content_lower:
                raise ValueError("File contains suspicious content")
    
    def _detect_extension_from_mime(self, mime_type: str) -> str:
        """Detect file extension from MIME type"""
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/heic': '.heic',
            'image/webp': '.webp'
        }
        return mime_to_ext.get(mime_type, '.jpg')
    
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