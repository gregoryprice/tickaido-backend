#!/usr/bin/env python3
"""
Agent Avatar API endpoints
"""

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas.agent import AgentAvatarResponse, AgentAvatarDeleteResponse, AgentAvatarInfoResponse
from app.models.user import User
from app.models.ai_agent import Agent
from app.services.avatar_service import AvatarService
from app.dependencies import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents")
avatar_service = AvatarService()


@router.post("/{agent_id}/avatar", response_model=AgentAvatarResponse)
async def upload_agent_avatar(
    agent_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Upload a new avatar for an agent.
    
    - **agent_id**: ID of the agent to upload avatar for
    - **file**: Image file to upload (JPG, PNG, GIF, HEIC, WebP)
    - Requires authentication and agent must belong to user's organization
    """
    try:
        # Check if agent exists and belongs to user's organization
        agent = await db.get(Agent, agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        if agent.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only modify agents in your organization"
            )
        
        # Check for empty file upload (used for avatar deletion)
        if file.size == 0 or not file.filename or file.filename.strip() == "":
            logger.info(f"Empty file uploaded for agent {agent_id} - treating as avatar deletion")
            success = await avatar_service.delete_agent_avatar(db, agent_id)
            
            if success:
                logger.info(f"✅ Avatar deleted successfully for agent {agent_id}")
                return AgentAvatarResponse(
                    agent_id=agent_id,
                    avatar_url=None,
                    message="Agent avatar removed successfully"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to remove avatar"
                )
        
        # Upload avatar (non-empty file)
        logger.info(f"Uploading avatar for agent {agent_id} by user {current_user.id}")
        avatar_url = await avatar_service.upload_agent_avatar(db, agent_id, file)
        
        logger.info(f"✅ Avatar uploaded successfully for agent {agent_id}")
        return AgentAvatarResponse(
            agent_id=agent_id,
            avatar_url=avatar_url,
            message="Agent avatar uploaded successfully",
            filename=file.filename,
            file_size=file.size,
            upload_date=datetime.now(),
            has_custom_avatar=True
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Avatar upload validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error uploading agent avatar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar"
        )


@router.get("/{agent_id}/avatar")
async def get_agent_avatar(
    agent_id: UUID,
    size: str = "medium",
    t: Optional[str] = None,  # Cache-busting timestamp parameter (ignored)
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get agent avatar image.
    
    - **agent_id**: ID of the agent
    - **size**: Avatar size (small, medium, large, original)
    - Returns the avatar image file or 404 if not found
    - Requires authentication and agent must belong to user's organization
    """
    try:
        logger.debug(f"GET avatar request for agent {agent_id} by user {current_user.id}")
        
        # Check if agent exists and belongs to user's organization
        agent = await db.get(Agent, agent_id)
        if not agent:
            logger.warning(f"Agent {agent_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        logger.debug(f"Agent found: organization_id={agent.organization_id}, user_org={current_user.organization_id}")
        
        if agent.organization_id != current_user.organization_id:
            logger.warning(f"403 - Agent {agent_id} org {agent.organization_id} != user {current_user.id} org {current_user.organization_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access agents in your organization"
            )
        
        # Get avatar URL
        avatar_url = await avatar_service.get_agent_avatar_url(agent_id, size)
        
        if not avatar_url:
            logger.warning(f"No avatar URL found for agent {agent_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent avatar not found"
            )
        
        logger.debug(f"Retrieved avatar URL: {avatar_url}")
        
        # For unified storage, we redirect to the actual file URL
        # This allows the storage backend (local/S3) to serve the file
        if avatar_service.backend_type == "s3":
            # For S3, return redirect to the actual URL
            return Response(
                status_code=status.HTTP_302_FOUND,
                headers={"Location": avatar_url}
            )
        else:
            # For local storage, we need to serve the file directly
            # Get file content and serve it
            storage_key = avatar_url.split("/api/v1/storage/")[-1] if "/api/v1/storage/" in avatar_url else None
            if storage_key:
                file_content = await avatar_service.avatar_storage_service.backend.download_file(storage_key)
                if file_content:
                    # Determine content type based on file extension
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
        logger.error(f"Error getting agent avatar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get avatar"
        )


@router.delete("/{agent_id}/avatar", response_model=AgentAvatarDeleteResponse)
async def delete_agent_avatar(
    agent_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Delete agent avatar.
    
    - **agent_id**: ID of the agent to delete avatar for
    - Requires authentication and agent must belong to user's organization
    """
    try:
        # Check if agent exists and belongs to user's organization
        agent = await db.get(Agent, agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        if agent.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only modify agents in your organization"
            )
        
        # Delete avatar
        logger.info(f"Deleting avatar for agent {agent_id} by user {current_user.id}")
        success = await avatar_service.delete_agent_avatar(db, agent_id)
        
        if success:
            logger.info(f"✅ Avatar deleted successfully for agent {agent_id}")
            return AgentAvatarDeleteResponse(
                agent_id=agent_id,
                deleted=True,
                message="Agent avatar deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete avatar"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent avatar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete avatar"
        )


@router.get("/{agent_id}/avatar/info", response_model=AgentAvatarInfoResponse)
async def get_agent_avatar_info(
    agent_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get agent avatar metadata/info.
    
    - **agent_id**: ID of the agent
    - Returns avatar metadata and thumbnail sizes (aligned with user avatar info)
    """
    try:
        # Check if agent exists and belongs to user's organization
        agent = await db.get(Agent, agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        if agent.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access agents in your organization"
            )
        
        # Generate thumbnail URLs using avatar service (aligned with user avatar info)
        thumbnail_sizes = {}
        for size in ["small", "medium", "large", "original"]:
            size_url = await avatar_service.get_agent_avatar_url(agent_id, size)
            if size_url:
                thumbnail_sizes[size] = size_url
        
        if not thumbnail_sizes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent avatar not found"
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
        
        return AgentAvatarInfoResponse(
            id=agent.id,
            agent_id=agent_id,
            avatar_url=agent.avatar_url,
            filename=None,  # Not available without storage metadata
            file_size=file_size,  # Size of original image from storage backend
            upload_date=agent.updated_at,
            thumbnail_sizes=thumbnail_sizes,
            created_at=agent.created_at,
            updated_at=agent.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent avatar info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get avatar info"
        )