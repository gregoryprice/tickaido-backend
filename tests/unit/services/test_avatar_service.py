#!/usr/bin/env python3
"""
Unit tests for Avatar Service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from pathlib import Path
from io import BytesIO

from fastapi import UploadFile
from PIL import Image

from app.services.avatar_service import AvatarService


class TestAvatarService:
    """Test cases for AvatarService"""
    
    def test_avatar_service_initialization(self):
        """Test avatar service initializes correctly"""
        service = AvatarService()
        
        # Check basic properties are set
        assert service.max_avatar_size == 5 * 1024 * 1024  # 5MB
        assert 'image/jpeg' in service.allowed_formats
        assert 'image/png' in service.allowed_formats
        assert 'image/gif' in service.allowed_formats
        assert '.jpg' in service.allowed_extensions
        assert '.png' in service.allowed_extensions
        
        # Check thumbnail sizes are defined
        assert 'small' in service.thumbnail_sizes
        assert 'medium' in service.thumbnail_sizes  
        assert 'large' in service.thumbnail_sizes
        assert service.thumbnail_sizes['small'] == (32, 32)
        assert service.thumbnail_sizes['medium'] == (150, 150)
        assert service.thumbnail_sizes['large'] == (300, 300)
        
        # Check directories are configured
        assert service.avatar_directory.exists()
        
        print("✅ Avatar service initialization working")
    
    @pytest.mark.asyncio
    async def test_validate_avatar_file_valid_formats(self):
        """Test validation passes for valid image formats"""
        service = AvatarService()
        
        # Create mock UploadFile objects for different formats
        test_cases = [
            ("image/jpeg", "test.jpg", b"fake_jpeg_content" * 100),
            ("image/png", "test.png", b"fake_png_content" * 100),
            ("image/gif", "test.gif", b"fake_gif_content" * 100)
        ]
        
        for mime_type, filename, content in test_cases:
            mock_file = MagicMock(spec=UploadFile)
            mock_file.content_type = mime_type
            mock_file.filename = filename
            
            # Should not raise an exception
            try:
                await service._validate_avatar_file(mock_file, content)
            except ValueError as e:
                pytest.fail(f"Valid format {mime_type} should not raise ValueError: {e}")
        
        print("✅ Avatar file validation for valid formats working")
    
    @pytest.mark.asyncio
    async def test_validate_avatar_file_invalid_formats(self):
        """Test validation rejects invalid formats and sizes"""
        service = AvatarService()
        
        # Test oversized file
        mock_file_large = MagicMock(spec=UploadFile)
        mock_file_large.content_type = "image/jpeg"
        mock_file_large.filename = "large.jpg"
        large_content = b"x" * (6 * 1024 * 1024)  # 6MB - over limit
        
        with pytest.raises(ValueError, match="exceeds maximum allowed size"):
            await service._validate_avatar_file(mock_file_large, large_content)
        
        # Test invalid MIME type
        mock_file_invalid = MagicMock(spec=UploadFile)
        mock_file_invalid.content_type = "application/pdf"
        mock_file_invalid.filename = "document.pdf"
        invalid_content = b"fake_pdf_content" * 100
        
        with pytest.raises(ValueError, match="not allowed"):
            await service._validate_avatar_file(mock_file_invalid, invalid_content)
        
        # Test invalid file extension
        mock_file_bad_ext = MagicMock(spec=UploadFile)
        mock_file_bad_ext.content_type = "image/jpeg"
        mock_file_bad_ext.filename = "test.exe"
        valid_content = b"fake_image_content" * 100
        
        with pytest.raises(ValueError, match="not allowed"):
            await service._validate_avatar_file(mock_file_bad_ext, valid_content)
        
        # Test tiny file
        mock_file_tiny = MagicMock(spec=UploadFile)
        mock_file_tiny.content_type = "image/jpeg"
        mock_file_tiny.filename = "tiny.jpg"
        tiny_content = b"x"  # Too small
        
        with pytest.raises(ValueError, match="too small"):
            await service._validate_avatar_file(mock_file_tiny, tiny_content)
        
        print("✅ Avatar file validation for invalid formats working")
    
    def test_validate_image_security_magic_numbers(self):
        """Test image security validation using magic numbers"""
        service = AvatarService()
        
        # Create a simple 20x20 pixel PNG for testing (above minimum size)
        img = Image.new('RGB', (20, 20), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        valid_png_content = img_bytes.getvalue()
        
        # Should not raise an exception for valid PNG
        try:
            service._validate_image_security(valid_png_content, "test.png")
        except ValueError as e:
            pytest.fail(f"Valid PNG should not raise ValueError: {e}")
        
        # Create a simple 20x20 pixel JPEG for testing (above minimum size)
        img_jpeg = Image.new('RGB', (20, 20), color='blue')
        jpeg_bytes = BytesIO()
        img_jpeg.save(jpeg_bytes, format='JPEG')
        valid_jpeg_content = jpeg_bytes.getvalue()
        
        # Should not raise an exception for valid JPEG
        try:
            service._validate_image_security(valid_jpeg_content, "test.jpg")
        except ValueError as e:
            pytest.fail(f"Valid JPEG should not raise ValueError: {e}")
        
        # Test invalid content (not an image)
        invalid_content = b"This is not an image file"
        with pytest.raises(ValueError, match="not a valid image format"):
            service._validate_image_security(invalid_content, "fake.jpg")
        
        # Test suspicious content (embed in the middle of valid PNG to pass magic number check)
        # Create content that starts with PNG header but has suspicious content in first 1KB
        png_header = valid_png_content[:100]  # PNG header and some data
        suspicious_middle = b"<script>alert('xss')</script>"
        png_remainder = valid_png_content[100:]
        suspicious_content = png_header + suspicious_middle + png_remainder
        
        with pytest.raises(ValueError, match="suspicious content"):
            service._validate_image_security(suspicious_content, "malicious.png")
        
        print("✅ Image security validation with magic numbers working")
    
    @pytest.mark.asyncio
    async def test_upload_avatar_success_path(self):
        """Test successful avatar upload flow"""
        service = AvatarService()
        
        # Create a mock database session
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.avatar_url = None
        mock_db.get.return_value = mock_user
        
        # Create a test image
        img = Image.new('RGB', (100, 100), color='green')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        test_content = img_bytes.getvalue()
        
        # Create mock UploadFile
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "avatar.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read.return_value = test_content
        mock_file.seek = AsyncMock()
        
        # Mock file system operations
        with patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=True), \
             patch.object(service, '_save_original_image', return_value=Path("/fake/path.jpg")), \
             patch.object(service, '_generate_thumbnails', return_value={}):
            
            test_user_id = uuid4()
            result_url = await service.upload_avatar(mock_db, test_user_id, mock_file)
            
            # Verify the result
            assert result_url == f"/api/v1/users/{test_user_id}/avatar"
            
            # Verify database operations
            mock_db.get.assert_called_once()
            mock_db.commit.assert_called_once()
        
        print("✅ Avatar upload success path working")
    
    def test_detect_extension_from_mime(self):
        """Test MIME type to extension detection"""
        service = AvatarService()
        
        # Test various MIME types
        assert service._detect_extension_from_mime('image/jpeg') == '.jpg'
        assert service._detect_extension_from_mime('image/jpg') == '.jpg'
        assert service._detect_extension_from_mime('image/png') == '.png'
        assert service._detect_extension_from_mime('image/gif') == '.gif'
        assert service._detect_extension_from_mime('image/heic') == '.heic'
        assert service._detect_extension_from_mime('image/webp') == '.webp'
        
        # Test unknown MIME type defaults to .jpg
        assert service._detect_extension_from_mime('unknown/type') == '.jpg'
        
        print("✅ MIME type to extension detection working")
    
    def test_generate_avatar_url(self):
        """Test avatar URL generation"""
        service = AvatarService()
        
        test_user_id = uuid4()
        expected_url = f"/api/v1/users/{test_user_id}/avatar"
        
        result = service._generate_avatar_url(test_user_id)
        assert result == expected_url
        
        print("✅ Avatar URL generation working")
    
    @pytest.mark.asyncio
    async def test_get_avatar_path(self):
        """Test getting avatar file path"""
        service = AvatarService()
        
        test_user_id = uuid4()
        
        # Mock file system to simulate no avatar found
        with patch('pathlib.Path.glob', return_value=[]), \
             patch('pathlib.Path.is_file', return_value=False):
            
            result = await service.get_avatar_path(test_user_id)
            assert result is None
        
        # Mock file system to simulate avatar found
        mock_path = Path(f"/fake/avatars/medium/{test_user_id}_avatar_123.jpg")
        with patch('pathlib.Path.glob', return_value=[mock_path]), \
             patch('pathlib.Path.is_file', return_value=True):
            
            result = await service.get_avatar_path(test_user_id, "medium")
            assert result == mock_path
        
        print("✅ Avatar path retrieval working")
    
    @pytest.mark.asyncio
    async def test_delete_avatar(self):
        """Test avatar deletion"""
        service = AvatarService()
        
        # Create mock database session and user
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.avatar_url = "/api/v1/users/123/avatar"
        mock_db.get.return_value = mock_user
        
        test_user_id = uuid4()
        
        # Mock file system operations
        mock_file_paths = [
            Path(f"/fake/{test_user_id}_avatar_123.jpg"),
            Path(f"/fake/small/{test_user_id}_avatar_123.jpg"),
            Path(f"/fake/medium/{test_user_id}_avatar_123.jpg")
        ]
        
        with patch('pathlib.Path.glob', return_value=mock_file_paths), \
             patch('pathlib.Path.is_file', return_value=True), \
             patch('pathlib.Path.unlink') as mock_unlink:
            
            result = await service.delete_avatar(mock_db, test_user_id)
            
            # Verify files were "deleted"
            assert result is True
            assert mock_unlink.call_count >= len(mock_file_paths)
            
            # Verify database operations
            mock_db.get.assert_called_once()
            mock_db.commit.assert_called_once()
            assert mock_user.avatar_url is None
        
        print("✅ Avatar deletion working")


# Run tests if this file is executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])