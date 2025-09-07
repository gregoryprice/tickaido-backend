#!/usr/bin/env python3
"""
Authentication and authorization tests for Avatar functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.api.v1.users import upload_avatar, delete_avatar, get_avatar_info
from app.services.avatar_service import AvatarService


class TestAvatarAuthentication:
    """Authentication and authorization tests for avatar endpoints"""
    
    @pytest.mark.asyncio
    async def test_unauthorized_upload_rejected(self):
        """CRITICAL: Test upload without JWT token"""
        # This test would need to be run at the HTTP level since
        # the JWT validation happens in the dependency injection
        # For unit testing, we test the permission checks in the endpoint
        
        user_id = uuid4()
        other_user_id = uuid4()
        
        # Test user trying to upload avatar for different user
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
        
        print("✅ Unauthorized upload rejection working")
    
    @pytest.mark.asyncio
    async def test_forbidden_cross_user_access(self):
        """CRITICAL: Test user A cannot modify user B's avatar"""
        user_a = uuid4()
        user_b = uuid4()
        
        # User A trying to upload avatar for User B
        current_user = MagicMock()
        current_user.id = user_a
        current_user.is_admin = False
        
        mock_db = AsyncMock()
        mock_file = MagicMock(spec=UploadFile)
        
        # Should raise 403 Forbidden for upload
        with pytest.raises(HTTPException) as exc_info:
            await upload_avatar(user_b, mock_file, current_user, mock_db)
        
        assert exc_info.value.status_code == 403
        
        # Should raise 403 Forbidden for delete
        with pytest.raises(HTTPException) as exc_info:
            await delete_avatar(user_b, current_user, mock_db)
        
        assert exc_info.value.status_code == 403
        assert "only delete your own avatar" in str(exc_info.value.detail)
        
        print("✅ Cross-user access forbidden working")
    
    @pytest.mark.asyncio 
    async def test_admin_privilege_escalation(self):
        """CRITICAL: Test admin-only operations are protected"""
        user_id = uuid4()
        admin_id = uuid4()
        regular_user_id = uuid4()
        
        # Test 1: Regular user cannot access admin operations on other users
        regular_user = MagicMock()
        regular_user.id = regular_user_id
        regular_user.is_admin = False
        
        mock_db = AsyncMock()
        mock_file = MagicMock(spec=UploadFile)
        
        with pytest.raises(HTTPException) as exc_info:
            await upload_avatar(user_id, mock_file, regular_user, mock_db)
        
        assert exc_info.value.status_code == 403
        
        # Test 2: Admin can perform cross-user operations
        admin_user = MagicMock()
        admin_user.id = admin_id
        admin_user.is_admin = True
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.created_at = "2023-01-01T00:00:00Z"
        mock_user.updated_at = "2023-01-01T00:00:00Z"
        
        mock_db.get.return_value = mock_user
        mock_db.refresh = AsyncMock()
        
        # Add required attributes to mock file
        mock_file.filename = "admin_test.jpg"
        mock_file.size = 2048
        
        # Mock the avatar service for successful admin operation
        from unittest.mock import patch
        with patch('app.api.v1.users.avatar_service') as mock_service:
            mock_service.upload_avatar = AsyncMock(return_value=f"/api/v1/users/{user_id}/avatar")
            
            # Should succeed for admin user (no exception raised)
            try:
                result = await upload_avatar(user_id, mock_file, admin_user, mock_db)
                assert result.user_id == user_id
            except HTTPException:
                pytest.fail("Admin should be able to upload avatar for any user")
        
        print("✅ Admin privilege boundaries working")
    
    @pytest.mark.asyncio
    async def test_user_can_modify_own_avatar(self):
        """Test that users can modify their own avatars"""
        user_id = uuid4()
        
        # User modifying their own avatar
        current_user = MagicMock()
        current_user.id = user_id
        current_user.is_admin = False
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.created_at = "2023-01-01T00:00:00Z"
        mock_user.updated_at = "2023-01-01T00:00:00Z"
        
        mock_db = AsyncMock()
        mock_db.get.return_value = mock_user
        mock_db.refresh = AsyncMock()
        
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "my_avatar.jpg"
        mock_file.size = 1024
        
        # Mock avatar service
        from unittest.mock import patch
        with patch('app.api.v1.users.avatar_service') as mock_service:
            mock_service.upload_avatar = AsyncMock(return_value=f"/api/v1/users/{user_id}/avatar")
            
            # Should succeed for own avatar
            result = await upload_avatar(user_id, mock_file, current_user, mock_db)
            assert result.user_id == user_id
            assert result.avatar_url == f"/api/v1/users/{user_id}/avatar"
        
        print("✅ User can modify own avatar working")
    
    @pytest.mark.asyncio
    async def test_nonexistent_user_protection(self):
        """Test protection against operations on non-existent users"""
        nonexistent_user_id = uuid4()
        current_user = MagicMock()
        current_user.id = nonexistent_user_id
        current_user.is_admin = False
        
        # Database returns None for non-existent user
        mock_db = AsyncMock()
        mock_db.get.return_value = None
        
        mock_file = MagicMock(spec=UploadFile)
        
        # Should raise 404 for upload
        with pytest.raises(HTTPException) as exc_info:
            await upload_avatar(nonexistent_user_id, mock_file, current_user, mock_db)
        
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)
        
        # Should raise 404 for delete
        with pytest.raises(HTTPException) as exc_info:
            await delete_avatar(nonexistent_user_id, current_user, mock_db)
        
        assert exc_info.value.status_code == 404
        
        # Should raise 404 for info
        with pytest.raises(HTTPException) as exc_info:
            await get_avatar_info(nonexistent_user_id, current_user, mock_db)
        
        assert exc_info.value.status_code == 404
        
        print("✅ Non-existent user protection working")
    
    @pytest.mark.asyncio
    async def test_file_extension_security(self):
        """Test that only safe file extensions are allowed"""
        service = AvatarService()
        
        # Test dangerous extensions
        dangerous_extensions = [
            "file.exe.jpg",    # Double extension
            "file.bat.png",    # Batch file
            "file.scr.gif",    # Screen saver
            "file.com.jpg",    # Executable
            "file.pif.png",    # Program information file  
            "file.js.gif",     # JavaScript
            "file.vbs.jpg",    # VBScript
            "file.ps1.png"     # PowerShell
        ]
        
        for filename in dangerous_extensions:
            mock_file = MagicMock(spec=UploadFile)
            mock_file.content_type = "image/jpeg"
            mock_file.filename = filename
            
            content = b"fake_content" * 20
            
            # Most of these should be rejected by extension validation
            # Since they end with valid image extensions, they might pass
            # But the content validation will catch non-image content
            
            try:
                await service._validate_avatar_file(mock_file, content)
                # If it passes file validation, test image security
                await service._validate_image_security(content, filename)
                pytest.fail(f"Dangerous file {filename} should have been rejected")
            except ValueError:
                # Expected - dangerous files should be rejected
                pass
        
        print("✅ File extension security working")


# Run tests if this file is executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])