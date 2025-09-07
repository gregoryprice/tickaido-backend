#!/usr/bin/env python3
"""
Avatar Service - Business logic for user avatar management and processing
"""

# imghdr is deprecated in Python 3.13, using PIL instead
from typing import Optional, Dict
from uuid import UUID
from datetime import datetime
from pathlib import Path
from io import BytesIO

from sqlalchemy.ext.asyncio import AsyncSession

from PIL import Image, ImageOps
from fastapi import UploadFile, HTTPException

from app.models.user import User
from app.config.settings import get_settings


class AvatarService:
    """Service class for avatar operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.upload_directory = Path(self.settings.upload_directory)
        self.avatar_directory = self.upload_directory / "avatars"
        self.max_avatar_size = 5 * 1024 * 1024  # 5MB limit
        self.allowed_formats = [
            'image/jpeg', 
            'image/jpg', 
            'image/png', 
            'image/gif', 
            'image/heic',
            'image/webp'
        ]
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.heic', '.webp'}
        self.thumbnail_sizes = {
            'small': (32, 32),    # Chat avatars
            'medium': (150, 150), # Profile cards
            'large': (300, 300)   # Full profile view
        }
        
        # Ensure upload directories exist
        self.avatar_directory.mkdir(parents=True, exist_ok=True)
        for size in self.thumbnail_sizes.keys():
            (self.avatar_directory / size).mkdir(parents=True, exist_ok=True)
    
    async def upload_avatar(
        self,
        db: AsyncSession,
        user_id: UUID,
        file: UploadFile
    ) -> str:
        """
        Upload and process a new avatar for a user
        
        Args:
            db: Database session
            user_id: ID of the user
            file: Upload file object
            
        Returns:
            Avatar URL string
        """
        # Read file content
        content = await file.read()
        await file.seek(0)  # Reset file pointer for potential reuse
        
        # Validate file
        await self._validate_avatar_file(file, content)
        
        # Validate image security
        filename = file.filename or "unknown"
        self._validate_image_security(content, filename)
        
        # Generate unique filename
        file_extension = Path(filename).suffix.lower()
        if not file_extension:
            content_type = file.content_type or "image/jpeg"
            file_extension = self._detect_extension_from_mime(content_type)
        
        storage_filename = f"{user_id}_avatar_{int(datetime.now().timestamp())}{file_extension}"
        storage_path = self.avatar_directory / storage_filename
        
        # Process and save images
        await self._save_original_image(content, storage_path)
        await self._generate_thumbnails(content, storage_filename, user_id)
        
        # Update user avatar URL in database
        avatar_url = await self._update_user_avatar_url(db, user_id, storage_filename)
        
        return avatar_url
    
    async def get_avatar_path(self, user_id: UUID, size: str = "medium") -> Optional[Path]:
        """
        Get the file path for a user's avatar
        
        Args:
            user_id: User ID
            size: Avatar size (small, medium, large)
            
        Returns:
            Path to avatar file or None if not found
        """
        if size not in self.thumbnail_sizes:
            size = "medium"
        
        # Look for avatar files with the user_id pattern
        size_directory = self.avatar_directory / size
        pattern = f"{user_id}_avatar_*"
        
        for file_path in size_directory.glob(pattern):
            if file_path.is_file():
                return file_path
        
        return None
    
    async def delete_avatar(self, db: AsyncSession, user_id: UUID) -> bool:
        """
        Delete all avatar files and update user record
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find and delete all avatar files for this user
            pattern = f"{user_id}_avatar_*"
            deleted_files = []
            
            # Delete original and all thumbnails
            for file_path in self.avatar_directory.glob(pattern):
                if file_path.is_file():
                    file_path.unlink()
                    deleted_files.append(str(file_path))
            
            for size in self.thumbnail_sizes.keys():
                size_dir = self.avatar_directory / size
                for file_path in size_dir.glob(pattern):
                    if file_path.is_file():
                        file_path.unlink()
                        deleted_files.append(str(file_path))
            
            # Update user record to remove avatar URL
            user = await db.get(User, user_id)
            if user:
                user.avatar_url = None  # type: ignore
                await db.commit()
            
            return len(deleted_files) > 0
            
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete avatar: {str(e)}")
    
    async def _validate_avatar_file(self, file: UploadFile, content: bytes):
        """
        Validate avatar file meets requirements
        
        Args:
            file: Upload file object
            content: File content bytes
        """
        # Check file size
        if len(content) > self.max_avatar_size:
            raise ValueError(f"File size {len(content)} exceeds maximum allowed size {self.max_avatar_size}")
        
        # Check MIME type
        if file.content_type not in self.allowed_formats:
            raise ValueError(f"File type {file.content_type} not allowed. Allowed types: {self.allowed_formats}")
        
        # Check file extension and validate filename characters
        filename = file.filename or "unknown"
        
        # Validate filename for security - reject dangerous characters
        dangerous_chars = '<>"|?*'
        if any(char in filename for char in dangerous_chars):
            raise ValueError(f"Filename contains invalid characters: {filename}")
        
        file_extension = Path(filename).suffix.lower()
        if file_extension and file_extension not in self.allowed_extensions:
            raise ValueError(f"File extension {file_extension} not allowed")
        
        # Check minimum size (avoid tiny images)
        if len(content) < 100:  # 100 bytes minimum
            raise ValueError("File too small to be a valid image")
    
    def _validate_image_security(self, content: bytes, filename: str):
        """
        Validate image security using multiple validation layers
        
        Args:
            content: File content bytes
            filename: Original filename
        """
        # 1. Magic number validation using PIL (replaced deprecated imghdr)
        try:
            with Image.open(BytesIO(content)) as img:
                # If PIL can open it, it's a valid image format
                img_format = img.format
                if img_format is None:
                    raise ValueError("File is not a valid image format")
        except Exception:
            raise ValueError("File is not a valid image format")
        
        # 2. PIL format validation with Image.verify()
        try:
            with Image.open(BytesIO(content)) as img:
                img.verify()
                
                # Check for reasonable dimensions (prevent image bombs)
                if hasattr(img, 'size'):
                    width, height = img.size
                    max_dimension = 10000  # 10k pixels max per dimension
                    if width > max_dimension or height > max_dimension:
                        raise ValueError(f"Image dimensions too large: {width}x{height}")
                    
                    # Minimum dimensions
                    if width < 16 or height < 16:
                        raise ValueError(f"Image dimensions too small: {width}x{height}")
        
        except Exception as e:
            if "cannot identify image file" in str(e).lower():
                raise ValueError("Invalid or corrupted image file")
            elif "Image dimensions too" in str(e):
                raise e
            else:
                raise ValueError(f"Image validation failed: {str(e)}")
        
        # 3. Check for suspicious file patterns
        suspicious_patterns = [b'<script', b'javascript:', b'vbscript:', b'<?php']
        content_lower = content[:1024].lower()  # Check first 1KB
        for pattern in suspicious_patterns:
            if pattern in content_lower:
                raise ValueError("File contains suspicious content")
    
    async def _save_original_image(self, content: bytes, storage_path: Path) -> Path:
        """
        Save the original image with EXIF rotation correction
        
        Args:
            content: Image content bytes
            storage_path: Path to save the image
            
        Returns:
            Path where image was saved
        """
        try:
            # Open and process the image
            with Image.open(BytesIO(content)) as original_img:
                # Handle EXIF orientation
                img = ImageOps.exif_transpose(original_img)
                if img is None:
                    img = original_img
                
                # Convert to RGB if necessary (handles RGBA, P mode, etc.)
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                
                # Save with optimization
                img.save(storage_path, optimize=True, quality=90)
            
            return storage_path
            
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Failed to process image: {str(e)}")
    
    async def _generate_thumbnails(self, content: bytes, filename: str, user_id: UUID) -> Dict[str, Path]:
        """
        Generate thumbnails in multiple sizes
        
        Args:
            content: Original image content
            filename: Base filename
            user_id: User ID
            
        Returns:
            Dictionary mapping size names to file paths
        """
        thumbnail_paths = {}
        base_name = Path(filename).stem
        extension = Path(filename).suffix
        
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
                    size_dir = self.avatar_directory / size_name
                    thumbnail_filename = f"{base_name}{extension}"
                    thumbnail_path = size_dir / thumbnail_filename
                    
                    # Create thumbnail with proper aspect ratio
                    thumbnail = img.copy()
                    thumbnail.thumbnail(dimensions, Image.Resampling.LANCZOS)
                    
                    # Create a square thumbnail with padding if needed
                    square_img = Image.new('RGB', dimensions, (255, 255, 255))
                    
                    # Center the thumbnail
                    x = (dimensions[0] - thumbnail.size[0]) // 2
                    y = (dimensions[1] - thumbnail.size[1]) // 2
                    square_img.paste(thumbnail, (x, y))
                    
                    # Save thumbnail
                    square_img.save(thumbnail_path, optimize=True, quality=85)
                    thumbnail_paths[size_name] = thumbnail_path
                
            return thumbnail_paths
            
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Failed to generate thumbnails: {str(e)}")
    
    async def _update_user_avatar_url(self, db: AsyncSession, user_id: UUID, filename: str) -> str:
        """
        Update user record with new avatar URL
        
        Args:
            db: Database session
            user_id: User ID
            filename: Avatar filename
            
        Returns:
            Avatar URL string
        """
        try:
            # Generate avatar URL
            avatar_url = f"/api/v1/users/{user_id}/avatar"
            
            # Update user record
            user = await db.get(User, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            user.avatar_url = avatar_url  # type: ignore
            await db.commit()
            await db.refresh(user)
            
            return avatar_url
            
        except HTTPException:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update user avatar: {str(e)}")
    
    def _detect_extension_from_mime(self, mime_type: str) -> str:
        """
        Detect file extension from MIME type
        
        Args:
            mime_type: MIME type string
            
        Returns:
            File extension with dot prefix
        """
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/heic': '.heic',
            'image/webp': '.webp'
        }
        return mime_to_ext.get(mime_type, '.jpg')
    
    def _generate_avatar_url(self, user_id: UUID) -> str:
        """
        Generate avatar URL for API responses
        
        Args:
            user_id: User ID
            
        Returns:
            Avatar URL string
        """
        return f"/api/v1/users/{user_id}/avatar"