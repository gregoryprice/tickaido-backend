#!/usr/bin/env python3
"""
Avatar Service - Business logic for user and agent avatar management using unified storage
"""

from typing import Optional
from uuid import UUID
import re
import io

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException
from PIL import Image

from app.models.user import User
from app.models.ai_agent import Agent
from app.services.storage.factory import get_avatar_storage_service


class AvatarService:
    """Service class for avatar operations using avatar storage backend"""
    
    def __init__(self):
        self.avatar_storage_service = get_avatar_storage_service()
    
    async def upload_user_avatar(
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
            Avatar URL string for medium size (default)
            
        Raises:
            HTTPException: On validation or processing errors
        """
        try:
            # Upload avatar with thumbnails using avatar storage service
            avatar_urls = await self.avatar_storage_service.upload_user_avatar(user_id, file)
            
            # Update user avatar URL in database
            avatar_url = await self._update_user_avatar_url(db, user_id, avatar_urls["medium"])
            
            return avatar_url
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload avatar: {str(e)}")
    
    async def upload_agent_avatar(
        self,
        db: AsyncSession,
        agent_id: UUID,
        file: UploadFile
    ) -> str:
        """
        Upload and process a new avatar for an agent
        
        Args:
            db: Database session
            agent_id: ID of the agent
            file: Upload file object
            
        Returns:
            Avatar URL string for medium size (default)
            
        Raises:
            HTTPException: On validation or processing errors
        """
        try:
            # Upload avatar with thumbnails using avatar storage service
            avatar_urls = await self.avatar_storage_service.upload_agent_avatar(agent_id, file)
            
            # Update agent avatar URL in database
            avatar_url = await self._update_agent_avatar_url(db, agent_id, avatar_urls["medium"])
            
            return avatar_url
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload agent avatar: {str(e)}")
    
    # Legacy method for backward compatibility
    async def upload_avatar(
        self,
        db: AsyncSession,
        user_id: UUID,
        file: UploadFile
    ) -> str:
        """
        Legacy method for user avatar upload (backward compatibility)
        
        Args:
            db: Database session
            user_id: ID of the user
            file: Upload file object
            
        Returns:
            Avatar URL string
        """
        return await self.upload_user_avatar(db, user_id, file)
    
    async def get_user_avatar_url(
        self,
        user_id: UUID,
        size: str = "medium",
        expires_in: Optional[int] = None
    ) -> Optional[str]:
        """
        Get avatar URL for a user
        
        Args:
            user_id: User ID
            size: Avatar size (small, medium, large, original)
            expires_in: URL expiration time in seconds (for signed URLs)
            
        Returns:
            Avatar URL or None if not found
        """
        return await self.avatar_storage_service.get_avatar_url(
            user_id, "users", size, expires_in
        )
    
    async def get_agent_avatar_url(
        self,
        agent_id: UUID,
        size: str = "medium", 
        expires_in: Optional[int] = None
    ) -> Optional[str]:
        """
        Get avatar URL for an agent
        
        Args:
            agent_id: Agent ID
            size: Avatar size (small, medium, large, original)
            expires_in: URL expiration time in seconds (for signed URLs)
            
        Returns:
            Avatar URL or None if not found
        """
        return await self.avatar_storage_service.get_avatar_url(
            agent_id, "agents", size, expires_in
        )
    
    # Legacy method for backward compatibility
    async def get_avatar_path(self, user_id: UUID, size: str = "medium") -> Optional[str]:
        """
        Legacy method - now returns URL instead of path for backward compatibility
        
        Args:
            user_id: User ID
            size: Avatar size
            
        Returns:
            Avatar URL or None if not found
        """
        return await self.get_user_avatar_url(user_id, size)
    
    async def delete_user_avatar(self, db: AsyncSession, user_id: UUID) -> bool:
        """
        Delete user avatar files and update database record
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete avatar files from storage
            storage_success = await self.avatar_storage_service.delete_avatar(user_id, "users")
            
            # Update user record to remove avatar URL
            user = await db.get(User, user_id)
            if user:
                user.avatar_url = None  # type: ignore
                await db.commit()
            
            return storage_success
            
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete avatar: {str(e)}")
    
    async def delete_agent_avatar(self, db: AsyncSession, agent_id: UUID) -> bool:
        """
        Delete agent avatar files and update database record
        
        Args:
            db: Database session
            agent_id: Agent ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete avatar files from storage
            storage_success = await self.avatar_storage_service.delete_avatar(agent_id, "agents")
            
            # Update agent record to remove avatar URL
            agent = await db.get(Agent, agent_id)
            if agent:
                agent.avatar_url = None  # type: ignore
                agent.has_custom_avatar = False  # type: ignore
                await db.commit()
            
            return storage_success
            
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete agent avatar: {str(e)}")
    
    # Legacy method for backward compatibility
    async def delete_avatar(self, db: AsyncSession, user_id: UUID) -> bool:
        """
        Legacy method for user avatar deletion (backward compatibility)
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        return await self.delete_user_avatar(db, user_id)
    
    async def _update_user_avatar_url(self, db: AsyncSession, user_id: UUID, avatar_url: str) -> str:
        """
        Update user record with new avatar URL
        
        Args:
            db: Database session
            user_id: User ID
            avatar_url: Avatar URL
            
        Returns:
            Avatar URL string
        """
        try:
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
    
    async def _update_agent_avatar_url(self, db: AsyncSession, agent_id: UUID, avatar_url: str) -> str:
        """
        Update agent record with new avatar URL
        
        Args:
            db: Database session
            agent_id: Agent ID
            avatar_url: Avatar URL
            
        Returns:
            Avatar URL string
        """
        try:
            # Update agent record
            agent = await db.get(Agent, agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            agent.avatar_url = avatar_url  # type: ignore
            agent.has_custom_avatar = True  # type: ignore
            await db.commit()
            await db.refresh(agent)
            
            return avatar_url
            
        except HTTPException:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update agent avatar: {str(e)}")
    
    @property
    def backend_type(self) -> str:
        """Get storage backend type"""
        return self.avatar_storage_service.backend_type
    
    @property
    def supports_signed_urls(self) -> bool:
        """Check if backend supports signed URLs"""
        return self.avatar_storage_service.supports_signed_urls
    
    async def _validate_avatar_file(self, file: UploadFile, content: bytes) -> None:
        """
        Validate avatar file for security and size constraints
        
        Args:
            file: Upload file object
            content: File content bytes
            
        Raises:
            ValueError: If validation fails
        """
        # Maximum file size: 5MB (to match test expectations)
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        
        if len(content) > MAX_FILE_SIZE:
            raise ValueError(f"File exceeds maximum allowed size of {MAX_FILE_SIZE} bytes")
        
        # Validate filename for dangerous characters
        if file.filename:
            dangerous_chars = re.compile(r'[<>:"|?*]')
            if dangerous_chars.search(file.filename):
                raise ValueError("Filename contains invalid characters")
        
        # Validate image content only if file size is acceptable
        self._validate_image_security(content, file.filename or "unknown")
    
    def _validate_image_security(self, content: bytes, filename: str) -> None:
        """
        Validate image content for security issues
        
        Args:
            content: Image content bytes
            filename: Original filename
            
        Raises:
            ValueError: If validation fails
        """
        # Check for suspicious content patterns at the beginning
        suspicious_patterns = [
            b"<script>",
            b"javascript:",
            b"vbscript:",
            b"<?php",
            b"%PDF-",  # PDF magic number
            b"MZ\x90\x00",  # PE executable magic number
        ]
        
        content_start = content[:100].lower()  # Check first 100 bytes
        for pattern in suspicious_patterns:
            if pattern.lower() in content_start:
                if pattern == b"%PDF-" or pattern == b"MZ\x90\x00":
                    raise ValueError("File is not a valid image format")
                else:
                    raise ValueError("File contains suspicious content")
        
        # Validate as proper image using PIL
        try:
            with Image.open(io.BytesIO(content)) as img:
                # Verify image integrity
                img.verify()
                
                # Check dimensions to prevent decompression bombs
                MAX_DIMENSION = 10000  # 10k pixels max per dimension
                width, height = img.size
                if width > MAX_DIMENSION or height > MAX_DIMENSION:
                    raise ValueError(f"Image dimensions too large: {width}x{height}")
                
                # Check for valid image formats
                if img.format not in ['JPEG', 'PNG', 'GIF', 'WEBP']:
                    raise ValueError(f"Unsupported image format: {img.format}")
                    
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError("File is not a valid image format")