#!/usr/bin/env python3
"""
User Avatar API endpoints
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.user import AvatarDeleteResponse, AvatarResponse
from app.services.avatar_service import AvatarService

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
        
        # Generate thumbnail URLs using avatar service
        thumbnail_sizes = {}
        for size in ["small", "medium", "large", "original"]:
            size_url = await avatar_service.get_user_avatar_url(user_id, size)
            if size_url:
                thumbnail_sizes[size] = size_url
        
        # Return avatar response
        return AvatarResponse(
            id=user.id,  # Using user.id as the response ID
            user_id=user_id,
            avatar_url=avatar_url,
            filename=file.filename,
            file_size=file.size if hasattr(file, 'size') else None,
            upload_date=user.updated_at,  # This will be updated after avatar upload
            thumbnail_sizes=thumbnail_sizes,  # Generated via avatar service
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
    t: Optional[str] = None,  # Cache-busting timestamp parameter (ignored)
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
        
        # Get avatar URL (handle optional size parameter)
        avatar_size = size if size is not None else "medium"
        avatar_url = await avatar_service.get_user_avatar_url(user_id, avatar_size)
        
        if not avatar_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Avatar not found"
            )
        
        # For unified storage, we need to handle differently based on backend type
        if avatar_service.backend_type == "s3":
            # For S3, redirect to the actual URL
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=avatar_url, status_code=302)
        else:
            # For local storage, get the file content and serve it
            # Extract storage key from URL
            storage_key = avatar_url.split("/api/v1/storage/")[-1] if "/api/v1/storage/" in avatar_url else None
            if storage_key:
                file_content = await avatar_service.avatar_storage_service.backend.download_file(storage_key)
                if file_content:
                    # Determine content type based on storage key extension
                    content_type = "image/jpeg"  # default
                    if storage_key.lower().endswith('.png'):
                        content_type = "image/png"
                    elif storage_key.lower().endswith('.gif'):
                        content_type = "image/gif"
                    elif storage_key.lower().endswith('.webp'):
                        content_type = "image/webp"
                    
                    # Generate ETag with timestamp for proper cache-busting
                    base_etag = hash(file_content)
                    etag_value = f'"{base_etag}-{t}"' if t else f'"{base_etag}"'
                    
                    from fastapi.responses import Response
                    return Response(
                        content=file_content,
                        media_type=content_type,
                        headers={
                            "Cache-Control": "public, max-age=3600",
                            "ETag": etag_value
                        }
                    )
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Avatar file not found"
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
        
        # Generate thumbnail URLs using avatar service
        thumbnail_sizes = {}
        for size in ["small", "medium", "large", "original"]:
            size_url = await avatar_service.get_user_avatar_url(user_id, size)
            if size_url:
                thumbnail_sizes[size] = size_url
        
        if not thumbnail_sizes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Avatar not found"
            )
        
        # Get file info for original image to get file size
        original_url = thumbnail_sizes.get("original")
        file_size = None
        if original_url:
            # Extract storage key from original URL
            storage_key = original_url.split("/api/v1/storage/")[-1] if "/api/v1/storage/" in original_url else None
            if storage_key:
                file_info = await avatar_service.avatar_storage_service.backend.get_file_info(storage_key)
                if file_info:
                    file_size = file_info.get("size")
        
        return AvatarResponse(
            id=user.id,
            user_id=user_id,
            avatar_url=user.avatar_url,
            filename=None,  # Not available without storage metadata
            file_size=file_size,  # Size of original image from storage backend
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