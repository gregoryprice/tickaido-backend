#!/usr/bin/env python3
"""
Tests for AvatarStorageService
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from uuid import uuid4

from app.services.storage.local_backend import LocalStorageBackend
from app.services.storage.avatar_storage_service import AvatarStorageService


class TestAvatarStorageService:
    """Tests for AvatarStorageService"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def service(self, temp_dir):
        """Create AvatarStorageService instance for testing"""
        backend = LocalStorageBackend(
            base_path=temp_dir,
            base_url="/test-storage"
        )
        return AvatarStorageService(backend)
    
    @pytest.fixture
    def mock_upload_file(self):
        """Mock UploadFile for testing"""
        class MockUploadFile:
            def __init__(self, filename, content, content_type):
                self.filename = filename
                self.content = content
                self.content_type = content_type
                
            async def read(self):
                return self.content
                
            async def seek(self, position):
                pass
        
        return MockUploadFile
    
    @pytest.mark.asyncio
    async def test_upload_user_avatar(self, service, mock_upload_file):
        """Test user avatar upload with thumbnails"""
        # Create a simple test image (PNG format)
        from PIL import Image
        from io import BytesIO
        
        # Create test image
        img = Image.new('RGB', (100, 100), color='red')
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_content = img_buffer.getvalue()
        
        # Create mock upload file
        upload_file = mock_upload_file("test-avatar.png", img_content, "image/png")
        user_id = uuid4()
        
        # Upload avatar
        avatar_urls = await service.upload_user_avatar(user_id, upload_file)
        
        # Check all sizes are generated
        assert "original" in avatar_urls
        assert "small" in avatar_urls
        assert "medium" in avatar_urls
        assert "large" in avatar_urls
        
        # Check URLs format
        for size, url in avatar_urls.items():
            assert f"avatars/users/{user_id}/{size}" in url
    
    @pytest.mark.asyncio
    async def test_upload_agent_avatar(self, service, mock_upload_file):
        """Test agent avatar upload with thumbnails"""
        from PIL import Image
        from io import BytesIO
        
        # Create test image
        img = Image.new('RGB', (150, 150), color='blue')
        img_buffer = BytesIO()
        img.save(img_buffer, format='JPEG')
        img_content = img_buffer.getvalue()
        
        # Create mock upload file
        upload_file = mock_upload_file("agent-avatar.jpg", img_content, "image/jpeg")
        agent_id = uuid4()
        
        # Upload avatar
        avatar_urls = await service.upload_agent_avatar(agent_id, upload_file)
        
        # Check all sizes are generated
        assert "original" in avatar_urls
        assert "small" in avatar_urls
        assert "medium" in avatar_urls
        assert "large" in avatar_urls
        
        # Check URLs format
        for size, url in avatar_urls.items():
            assert f"avatars/agents/{agent_id}/{size}" in url
    
    @pytest.mark.asyncio
    async def test_get_avatar_url(self, service, mock_upload_file):
        """Test getting avatar URL"""
        from PIL import Image
        from io import BytesIO
        
        # Create and upload test avatar
        img = Image.new('RGB', (100, 100), color='green')
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_content = img_buffer.getvalue()
        
        upload_file = mock_upload_file("test.png", img_content, "image/png")
        user_id = uuid4()
        
        await service.upload_user_avatar(user_id, upload_file)
        
        # Get avatar URL
        medium_url = await service.get_avatar_url(user_id, "users", "medium")
        assert medium_url is not None
        assert f"avatars/users/{user_id}/medium" in medium_url
        
        # Get non-existent avatar URL
        non_existent_url = await service.get_avatar_url(uuid4(), "users", "medium")
        assert non_existent_url is None
    
    @pytest.mark.asyncio
    async def test_delete_avatar(self, service, mock_upload_file):
        """Test avatar deletion"""
        from PIL import Image
        from io import BytesIO
        
        # Create and upload test avatar
        img = Image.new('RGB', (100, 100), color='yellow')
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_content = img_buffer.getvalue()
        
        upload_file = mock_upload_file("delete-test.png", img_content, "image/png")
        user_id = uuid4()
        
        # Upload avatar
        await service.upload_user_avatar(user_id, upload_file)
        
        # Verify avatar exists
        url = await service.get_avatar_url(user_id, "users", "medium")
        assert url is not None
        
        # Delete avatar
        success = await service.delete_avatar(user_id, "users")
        assert success
        
        # Verify avatar is deleted
        url_after = await service.get_avatar_url(user_id, "users", "medium")
        assert url_after is None
    
    @pytest.mark.asyncio
    async def test_avatar_validation(self, service, mock_upload_file):
        """Test avatar file validation"""
        # Test oversized file
        large_content = b"x" * (6 * 1024 * 1024)  # 6MB, over 5MB limit
        large_file = mock_upload_file("large.png", large_content, "image/png")
        
        with pytest.raises(Exception):
            await service.upload_user_avatar(uuid4(), large_file)
        
        # Test invalid file type
        invalid_file = mock_upload_file("test.txt", b"not an image", "text/plain")
        
        with pytest.raises(Exception):
            await service.upload_user_avatar(uuid4(), invalid_file)
    
    def test_service_properties(self, service):
        """Test service properties"""
        assert service.backend_type == "local"
        assert service.supports_public_urls == True
        assert service.supports_signed_urls == False