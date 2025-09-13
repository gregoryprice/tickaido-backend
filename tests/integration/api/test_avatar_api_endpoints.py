#!/usr/bin/env python3
"""
Unit tests for Avatar API Endpoints
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image

from app.api.v1.users import upload_avatar, get_avatar, delete_avatar, get_avatar_info
from app.schemas.user import AvatarResponse, AvatarDeleteResponse


class TestAvatarAPIEndpoints:
    """Test cases for Avatar API Endpoints"""

    @pytest.mark.asyncio
    async def test_upload_avatar_success(self):
        """Test successful avatar upload"""
        # Create test data
        user_id = uuid4()
        current_user = MagicMock()
        current_user.id = user_id
        current_user.is_admin = False
        
        # Mock database user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.avatar_url = None
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        
        # Mock database session
        mock_db = AsyncMock()
        mock_db.get.return_value = mock_user
        mock_db.refresh = AsyncMock()
        
        # Create test image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        # Mock UploadFile
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "avatar.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.size = len(img_bytes.getvalue())
        
        # Mock avatar service
        with patch('app.api.v1.users.avatar_service') as mock_service:
            mock_service.upload_avatar = AsyncMock(return_value=f"/api/v1/users/{user_id}/avatar")
            mock_service.get_user_avatar_url = AsyncMock(return_value=f"/api/v1/users/{user_id}/avatar/medium")
            
            # Call the endpoint
            result = await upload_avatar(user_id, mock_file, current_user, mock_db)
            
            # Verify the result
            assert isinstance(result, AvatarResponse)
            assert result.user_id == user_id
            assert result.avatar_url == f"/api/v1/users/{user_id}/avatar"
            assert result.filename == "avatar.jpg"
            
            # Verify service was called
            mock_service.upload_avatar.assert_called_once_with(mock_db, user_id, mock_file)
        
        print("✅ Avatar upload success test working")

    @pytest.mark.asyncio
    async def test_upload_avatar_unauthorized(self):
        """Test avatar upload with unauthorized user"""
        user_id = uuid4()
        other_user_id = uuid4()
        
        # Current user is different from target user
        current_user = MagicMock()
        current_user.id = other_user_id
        current_user.is_admin = False
        
        mock_db = AsyncMock()
        mock_file = MagicMock(spec=UploadFile)
        
        # Should raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            await upload_avatar(user_id, mock_file, current_user, mock_db)
        
        assert exc_info.value.status_code == 403
        assert "only upload your own avatar" in str(exc_info.value.detail)
        
        print("✅ Avatar upload unauthorized test working")

    @pytest.mark.asyncio
    async def test_upload_avatar_forbidden(self):
        """Test avatar upload for non-existent user"""
        user_id = uuid4()
        current_user = MagicMock()
        current_user.id = user_id
        current_user.is_admin = False
        
        # Database returns no user
        mock_db = AsyncMock()
        mock_db.get.return_value = None
        
        mock_file = MagicMock(spec=UploadFile)
        
        # Should raise 404 Not Found
        with pytest.raises(HTTPException) as exc_info:
            await upload_avatar(user_id, mock_file, current_user, mock_db)
        
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)
        
        print("✅ Avatar upload forbidden test working")

    @pytest.mark.asyncio
    async def test_upload_avatar_invalid_format(self):
        """Test avatar upload with invalid file format"""
        user_id = uuid4()
        current_user = MagicMock()
        current_user.id = user_id
        current_user.is_admin = False
        
        mock_user = MagicMock()
        mock_user.id = user_id
        
        mock_db = AsyncMock()
        mock_db.get.return_value = mock_user
        
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "document.pdf"
        
        # Mock avatar service to raise ValueError
        with patch('app.api.v1.users.avatar_service') as mock_service:
            mock_service.upload_avatar.side_effect = ValueError("Invalid file format")
            
            # Should raise 400 Bad Request
            with pytest.raises(HTTPException) as exc_info:
                await upload_avatar(user_id, mock_file, current_user, mock_db)
            
            assert exc_info.value.status_code == 400
            assert "Invalid file format" in str(exc_info.value.detail)
        
        print("✅ Avatar upload invalid format test working")

    @pytest.mark.asyncio
    async def test_upload_avatar_oversized(self):
        """Test avatar upload with oversized file"""
        user_id = uuid4()
        current_user = MagicMock()
        current_user.id = user_id
        current_user.is_admin = False
        
        mock_user = MagicMock()
        mock_user.id = user_id
        
        mock_db = AsyncMock()
        mock_db.get.return_value = mock_user
        
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "large_image.jpg"
        
        # Mock avatar service to raise ValueError for oversized file
        with patch('app.api.v1.users.avatar_service') as mock_service:
            mock_service.upload_avatar.side_effect = ValueError("File size exceeds maximum allowed size")
            
            # Should raise 400 Bad Request
            with pytest.raises(HTTPException) as exc_info:
                await upload_avatar(user_id, mock_file, current_user, mock_db)
            
            assert exc_info.value.status_code == 400
            assert "exceeds maximum allowed size" in str(exc_info.value.detail)
        
        print("✅ Avatar upload oversized test working")

    @pytest.mark.asyncio
    async def test_get_avatar_success(self):
        """Test successful avatar retrieval"""
        user_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.id = user_id
        
        mock_db = AsyncMock()
        mock_db.get.return_value = mock_user
        
        # Mock avatar service with complete setup
        with patch('app.api.v1.users.avatar_service') as mock_service:
            # Set up the avatar URL that includes the storage path
            avatar_url = "/api/v1/storage/avatars/users/test/medium.jpg"
            mock_service.get_user_avatar_url = AsyncMock(return_value=avatar_url)
            mock_service.backend_type = "local"  # This triggers the local storage path
            
            # Mock the avatar storage service backend
            mock_backend = AsyncMock()
            mock_backend.download_file = AsyncMock(return_value=b"fake_image_data")
            
            # Create the nested structure that the code expects
            mock_storage_service = MagicMock()
            mock_storage_service.backend = mock_backend
            mock_service.avatar_storage_service = mock_storage_service
            
            # Mock the Response class to avoid creating actual HTTP response
            with patch('fastapi.responses.Response') as mock_response_class:
                mock_response_instance = MagicMock()
                mock_response_class.return_value = mock_response_instance
                
                result = await get_avatar(user_id, "medium", None, mock_db)
                
                # Verify the Response was created with correct parameters
                assert result == mock_response_instance
                mock_service.get_user_avatar_url.assert_called_once_with(user_id, "medium")
                
                # Verify backend download was called with correct storage key
                expected_storage_key = "avatars/users/test/medium.jpg"
                mock_backend.download_file.assert_called_once_with(expected_storage_key)
                
                # Verify Response was created with image content
                mock_response_class.assert_called_once()
                call_kwargs = mock_response_class.call_args[1]
                assert call_kwargs['content'] == b"fake_image_data"
                assert call_kwargs['media_type'] == "image/jpeg"
                assert "Cache-Control" in call_kwargs['headers']
                assert "ETag" in call_kwargs['headers']
        
        print("✅ Avatar retrieval success test working")

    @pytest.mark.asyncio
    async def test_get_avatar_not_found(self):
        """Test avatar retrieval when avatar doesn't exist"""
        user_id = uuid4()
        
        mock_user = MagicMock()
        mock_user.id = user_id
        
        mock_db = AsyncMock()
        mock_db.get.return_value = mock_user
        
        # Mock avatar service to return None (no avatar found)
        with patch('app.api.v1.users.avatar_service') as mock_service:
            mock_service.get_user_avatar_url = AsyncMock(return_value=None)
            
            # Should raise 404 Not Found
            with pytest.raises(HTTPException) as exc_info:
                await get_avatar(user_id, "medium", None, mock_db)
            
            assert exc_info.value.status_code == 404
            assert "Avatar not found" in str(exc_info.value.detail)
            
            # Verify service was called
            mock_service.get_user_avatar_url.assert_called_once_with(user_id, "medium")
        
        print("✅ Avatar retrieval not found test working")

    @pytest.mark.asyncio
    async def test_delete_avatar_success(self):
        """Test successful avatar deletion"""
        user_id = uuid4()
        current_user = MagicMock()
        current_user.id = user_id
        current_user.is_admin = False
        
        mock_user = MagicMock()
        mock_user.id = user_id
        
        mock_db = AsyncMock()
        mock_db.get.return_value = mock_user
        
        # Mock avatar service
        with patch('app.api.v1.users.avatar_service') as mock_service:
            mock_service.delete_avatar = AsyncMock(return_value=True)
            
            result = await delete_avatar(user_id, current_user, mock_db)
            
            assert isinstance(result, AvatarDeleteResponse)
            assert result.user_id == user_id
            assert result.deleted is True
            assert "successfully deleted" in result.message
            
            mock_service.delete_avatar.assert_called_once_with(mock_db, user_id)
        
        print("✅ Avatar deletion success test working")

    @pytest.mark.asyncio
    async def test_delete_avatar_unauthorized(self):
        """Test avatar deletion with unauthorized user"""
        user_id = uuid4()
        other_user_id = uuid4()
        
        # Current user is different from target user
        current_user = MagicMock()
        current_user.id = other_user_id
        current_user.is_admin = False
        
        mock_db = AsyncMock()
        
        # Should raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            await delete_avatar(user_id, current_user, mock_db)
        
        assert exc_info.value.status_code == 403
        assert "only delete your own avatar" in str(exc_info.value.detail)
        
        print("✅ Avatar deletion unauthorized test working")

    @pytest.mark.asyncio
    async def test_get_avatar_info_success(self):
        """Test successful avatar info retrieval"""
        user_id = uuid4()
        current_user = MagicMock()
        current_user.id = user_id
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.avatar_url = f"/api/v1/users/{user_id}/avatar"
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        
        mock_db = AsyncMock()
        mock_db.get.return_value = mock_user
        
        # Mock avatar service
        with patch('app.api.v1.users.avatar_service') as mock_service:
            mock_service.get_user_avatar_url = AsyncMock(return_value=f"/api/v1/storage/avatars/users/{user_id}/medium.jpg")
            
            # Mock the avatar storage service backend
            mock_backend = MagicMock()
            mock_file_info = MagicMock()
            mock_file_info.get.return_value = 1024  # file size
            mock_backend.get_file_info = AsyncMock(return_value=mock_file_info)
            mock_service.avatar_storage_service.backend = mock_backend
            
            result = await get_avatar_info(user_id, current_user, mock_db)
            
            assert isinstance(result, AvatarResponse)
            assert result.user_id == user_id
            assert "thumbnail_sizes" in result.model_dump()
            # Verify multiple calls to get_user_avatar_url for different sizes
            assert mock_service.get_user_avatar_url.call_count >= 3
        
        print("✅ Avatar info retrieval test working")

    @pytest.mark.asyncio
    async def test_admin_can_modify_any_avatar(self):
        """Test that admin users can modify any user's avatar"""
        user_id = uuid4()
        admin_user_id = uuid4()
        
        # Admin user trying to modify another user's avatar
        current_user = MagicMock()
        current_user.id = admin_user_id
        current_user.is_admin = True
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        
        mock_db = AsyncMock()
        mock_db.get.return_value = mock_user
        mock_db.refresh = AsyncMock()
        
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "avatar.jpg"
        mock_file.size = 1024
        
        # Mock avatar service
        with patch('app.api.v1.users.avatar_service') as mock_service:
            mock_service.upload_avatar = AsyncMock(return_value=f"/api/v1/users/{user_id}/avatar")
            mock_service.get_user_avatar_url = AsyncMock(return_value=f"/api/v1/users/{user_id}/avatar/medium")
            
            # Should succeed for admin user
            result = await upload_avatar(user_id, mock_file, current_user, mock_db)
            
            assert isinstance(result, AvatarResponse)
            assert result.user_id == user_id
            mock_service.upload_avatar.assert_called_once()
        
        print("✅ Admin avatar modification test working")


# Run tests if this file is executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])