#!/usr/bin/env python3
"""
User Avatar API endpoints
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas.user import AvatarResponse, AvatarDeleteResponse
from app.models.user import User
from app.services.avatar_service import AvatarService
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users")
avatar_service = AvatarService()


@router.post("/{user_id}/avatar", response_model=AvatarResponse)
async def upload_avatar(
    user_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Upload a new avatar for a user.
    
    - **user_id**: ID of the user to upload avatar for
    - **file**: Image file to upload (JPG, PNG, GIF, HEIC, WebP)
    - Requires authentication
    - Users can only upload their own avatars unless they are admin
    """
    try:
        # Check permissions - users can only modify their own avatar unless admin
        if str(user_id) != str(current_user.id) and not getattr(current_user, 'is_admin', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only upload your own avatar"
            )
        
        # Check if user exists
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Upload avatar using the avatar service
        avatar_url = await avatar_service.upload_avatar(db, user_id, file)
        
        # Refresh user to get updated timestamp
        await db.refresh(user)
        
        # Return avatar response
        return AvatarResponse(
            id=user.id,  # Using user.id as the response ID
            user_id=user_id,
            avatar_url=avatar_url,
            filename=file.filename,
            file_size=file.size if hasattr(file, 'size') else None,
            upload_date=user.updated_at,  # This will be updated after avatar upload
            thumbnail_sizes=None,  # Will be generated in the service
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (403, 404, etc.)
        raise
    except ValueError as e:
        # Handle validation errors from avatar service
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error uploading avatar for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar"
        )


@router.get("/{user_id}/avatar")
async def get_avatar(
    user_id: UUID,
    size: Optional[str] = "medium",
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get a user's avatar image.
    
    - **user_id**: ID of the user
    - **size**: Avatar size (small, medium, large) - defaults to medium
    - Returns the actual image file
    - No authentication required for viewing avatars
    """
    try:
        # Check if user exists
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get avatar path (handle optional size parameter)
        avatar_size = size if size is not None else "medium"
        avatar_path = await avatar_service.get_avatar_path(user_id, avatar_size)
        
        if not avatar_path or not avatar_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Avatar not found"
            )
        
        # Determine content type based on file extension
        content_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.heic': 'image/heic',
            '.webp': 'image/webp'
        }
        
        file_extension = avatar_path.suffix.lower()
        content_type = content_type_map.get(file_extension, 'image/jpeg')
        
        return FileResponse(
            path=avatar_path,
            media_type=content_type,
            filename=f"avatar_{user_id}_{size}{file_extension}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving avatar for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve avatar"
        )


@router.delete("/{user_id}/avatar", response_model=AvatarDeleteResponse)
async def delete_avatar(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Delete a user's avatar.
    
    - **user_id**: ID of the user to delete avatar for
    - Requires authentication
    - Users can only delete their own avatars unless they are admin
    """
    try:
        # Check permissions - users can only modify their own avatar unless admin
        if str(user_id) != str(current_user.id) and not getattr(current_user, 'is_admin', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own avatar"
            )
        
        # Check if user exists
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Delete avatar using the avatar service
        deleted = await avatar_service.delete_avatar(db, user_id)
        
        if deleted:
            return AvatarDeleteResponse(
                user_id=user_id,
                deleted=True,
                message="Avatar successfully deleted"
            )
        else:
            return AvatarDeleteResponse(
                user_id=user_id,
                deleted=False,
                message="No avatar found to delete"
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions (403, 404, etc.)
        raise
    except Exception as e:
        logger.error(f"Error deleting avatar for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete avatar"
        )


@router.get("/{user_id}/avatar/info", response_model=AvatarResponse)
async def get_avatar_info(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get avatar information (metadata only, not the image file).
    
    - **user_id**: ID of the user
    - Returns avatar metadata including URLs for different sizes
    - Requires authentication
    """
    try:
        # Check if user exists
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user has an avatar
        if not user.avatar_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User has no avatar"
            )
        
        # Get file path to check if it exists and get file info
        avatar_path = await avatar_service.get_avatar_path(user_id, "medium")
        
        if not avatar_path or not avatar_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Avatar file not found"
            )
        
        # Generate thumbnail URLs
        thumbnail_sizes = {
            size: f"/api/v1/users/{user_id}/avatar?size={size}"
            for size in avatar_service.thumbnail_sizes.keys()
        }
        
        return AvatarResponse(
            id=user.id,
            user_id=user_id,
            avatar_url=user.avatar_url,
            filename=avatar_path.name,
            file_size=avatar_path.stat().st_size if avatar_path.exists() else None,
            upload_date=user.updated_at,
            thumbnail_sizes=thumbnail_sizes,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting avatar info for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get avatar information"
        )