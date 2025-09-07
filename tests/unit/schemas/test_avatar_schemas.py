#!/usr/bin/env python3
"""
Unit tests for Avatar Schemas
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError

from app.schemas.user import AvatarUploadRequest, AvatarResponse, AvatarDeleteResponse


class TestAvatarSchemas:
    """Test cases for Avatar Schemas"""
    
    def test_avatar_upload_request_validation(self):
        """Test valid avatar upload request validation"""
        
        # Test with valid filename
        valid_request = AvatarUploadRequest(filename="profile.jpg")
        assert valid_request.filename == "profile.jpg"
        
        # Test with different valid extensions
        valid_extensions = ["image.png", "avatar.jpeg", "pic.gif", "photo.heic", "img.webp"]
        for filename in valid_extensions:
            request = AvatarUploadRequest(filename=filename)
            assert request.filename == filename
        
        # Test with no filename (should be allowed)
        request_no_filename = AvatarUploadRequest()
        assert request_no_filename.filename is None
        
        # Test with empty filename (should become None)
        request_empty = AvatarUploadRequest(filename="")
        assert request_empty.filename is None
        
        # Test with whitespace filename (should become None)
        request_whitespace = AvatarUploadRequest(filename="   ")
        assert request_whitespace.filename is None
        
        print("✅ Avatar upload request validation working")
    
    def test_avatar_upload_request_invalid_data(self):
        """Test avatar upload request with invalid data"""
        
        # Test with invalid filename characters
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in invalid_chars:
            with pytest.raises(ValidationError, match="invalid characters"):
                AvatarUploadRequest(filename=f"file{char}.jpg")
        
        # Test with invalid file extensions
        invalid_extensions = ["file.txt", "document.pdf", "script.js", "data.csv", "video.mp4"]
        for filename in invalid_extensions:
            with pytest.raises(ValidationError, match="Invalid file extension"):
                AvatarUploadRequest(filename=filename)
        
        # Test filename too long (over 255 characters) 
        long_filename = "a" * 252 + ".jpg"  # 256 characters total
        with pytest.raises(ValidationError):
            AvatarUploadRequest(filename=long_filename)
        
        print("✅ Avatar upload request invalid data validation working")
    
    def test_avatar_response_serialization(self):
        """Test avatar response serialization"""
        
        user_id = uuid4()
        upload_time = datetime.now(timezone.utc)
        
        # Test basic avatar response
        response_data = {
            "id": uuid4(),
            "user_id": user_id,
            "avatar_url": f"/api/v1/users/{user_id}/avatar",
            "filename": "avatar.jpg",
            "file_size": 102400,  # 100KB
            "upload_date": upload_time,
            "created_at": upload_time,
            "updated_at": upload_time,
            "thumbnail_sizes": {
                "small": f"/api/v1/users/{user_id}/avatar?size=small",
                "medium": f"/api/v1/users/{user_id}/avatar?size=medium",
                "large": f"/api/v1/users/{user_id}/avatar?size=large"
            }
        }
        
        response = AvatarResponse(**response_data)
        
        assert response.user_id == user_id
        assert response.avatar_url == f"/api/v1/users/{user_id}/avatar"
        assert response.filename == "avatar.jpg"
        assert response.file_size == 102400
        assert response.upload_date == upload_time
        assert "small" in response.thumbnail_sizes
        assert "medium" in response.thumbnail_sizes
        assert "large" in response.thumbnail_sizes
        
        print("✅ Avatar response serialization working")
    
    def test_avatar_response_fields_present(self):
        """Test that all required avatar response fields are present"""
        
        user_id = uuid4()
        upload_time = datetime.now(timezone.utc)
        
        # Test with minimal required fields
        minimal_data = {
            "id": uuid4(),
            "user_id": user_id,
            "avatar_url": f"/api/v1/users/{user_id}/avatar",
            "upload_date": upload_time,
            "created_at": upload_time,
            "updated_at": upload_time
        }
        
        response = AvatarResponse(**minimal_data)
        
        # Required fields should be present
        assert response.user_id == user_id
        assert response.avatar_url.startswith("/api/v1/users/")
        assert response.upload_date == upload_time
        
        # Optional fields should be None
        assert response.filename is None
        assert response.file_size is None
        assert response.thumbnail_sizes is None
        
        print("✅ Avatar response fields validation working")
    
    def test_avatar_response_missing_required_fields(self):
        """Test avatar response with missing required fields"""
        
        # Test missing user_id
        with pytest.raises(ValidationError, match="Field required"):
            AvatarResponse(
                id=uuid4(),
                avatar_url="/api/v1/users/123/avatar",
                upload_date=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        
        # Test missing avatar_url
        with pytest.raises(ValidationError, match="Field required"):
            AvatarResponse(
                id=uuid4(),
                user_id=uuid4(),
                upload_date=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        
        # Test missing upload_date
        with pytest.raises(ValidationError, match="Field required"):
            AvatarResponse(
                id=uuid4(),
                user_id=uuid4(),
                avatar_url="/api/v1/users/123/avatar",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        
        print("✅ Avatar response required fields validation working")
    
    def test_avatar_delete_response(self):
        """Test avatar delete response schema"""
        
        user_id = uuid4()
        
        # Test successful deletion response
        success_response = AvatarDeleteResponse(
            user_id=user_id,
            deleted=True,
            message="Avatar successfully deleted"
        )
        
        assert success_response.user_id == user_id
        assert success_response.deleted is True
        assert success_response.message == "Avatar successfully deleted"
        
        # Test failed deletion response
        failed_response = AvatarDeleteResponse(
            user_id=user_id,
            deleted=False,
            message="No avatar found to delete"
        )
        
        assert failed_response.user_id == user_id
        assert failed_response.deleted is False
        assert failed_response.message == "No avatar found to delete"
        
        print("✅ Avatar delete response validation working")
    
    def test_avatar_schema_json_serialization(self):
        """Test avatar schemas can be serialized to/from JSON"""
        
        user_id = uuid4()
        
        # Test AvatarUploadRequest JSON serialization
        upload_request = AvatarUploadRequest(filename="test.jpg")
        json_data = upload_request.model_dump()
        assert json_data["filename"] == "test.jpg"
        
        # Test AvatarResponse JSON serialization
        response = AvatarResponse(
            id=uuid4(),
            user_id=user_id,
            avatar_url=f"/api/v1/users/{user_id}/avatar",
            filename="test.jpg",
            file_size=1024,
            upload_date=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        json_data = response.model_dump()
        # UUIDs might not be serialized as strings by default in model_dump()
        assert json_data["user_id"] == user_id or json_data["user_id"] == str(user_id)
        assert json_data["avatar_url"] == f"/api/v1/users/{user_id}/avatar"
        assert json_data["filename"] == "test.jpg"
        assert json_data["file_size"] == 1024
        
        # Test AvatarDeleteResponse JSON serialization
        delete_response = AvatarDeleteResponse(
            user_id=user_id,
            deleted=True,
            message="Success"
        )
        
        json_data = delete_response.model_dump()
        assert json_data["user_id"] == user_id or json_data["user_id"] == str(user_id)
        assert json_data["deleted"] is True
        assert json_data["message"] == "Success"
        
        print("✅ Avatar schema JSON serialization working")


# Run tests if this file is executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])