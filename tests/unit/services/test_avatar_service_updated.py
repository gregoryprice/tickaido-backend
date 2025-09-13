#!/usr/bin/env python3
"""
Tests for updated AvatarService using unified storage
"""

import pytest
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from PIL import Image
from io import BytesIO

from app.services.avatar_service import AvatarService
from app.services.storage.local_backend import LocalStorageBackend
from app.services.storage.storage_service import StorageService
from app.models.user import User
from app.models.ai_agent import Agent


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_storage_service(temp_dir):
    """Create mock storage service"""
    backend = LocalStorageBackend(base_path=temp_dir, base_url="/test-storage")
    return StorageService(backend)


@pytest.fixture
def avatar_service(mock_storage_service):
    """Create AvatarService instance with mock storage service"""
    service = AvatarService()
    service.storage_service = mock_storage_service
    return service


@pytest.fixture
def mock_upload_file():
    """Create mock UploadFile"""
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


@pytest.fixture
def test_image_content():
    """Create test image content"""
    img = Image.new('RGB', (100, 100), color='red')
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    return img_buffer.getvalue()


class TestAvatarService:
    """Tests for AvatarService"""
    
    @pytest.mark.asyncio
    async def test_upload_user_avatar_success(self, avatar_service, mock_upload_file, test_image_content):
        """Test successful user avatar upload"""
        # Create mock database session
        db_mock = AsyncMock()
        
        # Create mock user
        user_id = uuid4()
        user_mock = MagicMock()
        user_mock.avatar_url = None
        db_mock.get.return_value = user_mock
        
        # Create upload file
        upload_file = mock_upload_file("test.png", test_image_content, "image/png")
        
        # Upload avatar
        result_url = await avatar_service.upload_user_avatar(db_mock, user_id, upload_file)
        
        # Verify result
        assert result_url is not None
        assert "avatars/users" in result_url
        
        # Verify database operations
        db_mock.get.assert_called_once_with(User, user_id)
        db_mock.commit.assert_called()
        db_mock.refresh.assert_called_once_with(user_mock)
        
        # Verify user avatar_url was updated
        assert user_mock.avatar_url is not None
    
    @pytest.mark.asyncio
    async def test_upload_agent_avatar_success(self, avatar_service, mock_upload_file, test_image_content):
        """Test successful agent avatar upload"""
        # Create mock database session
        db_mock = AsyncMock()
        
        # Create mock agent
        agent_id = uuid4()
        agent_mock = MagicMock()
        agent_mock.avatar_url = None
        agent_mock.has_custom_avatar = False
        db_mock.get.return_value = agent_mock
        
        # Create upload file
        upload_file = mock_upload_file("agent.png", test_image_content, "image/png")
        
        # Upload avatar
        result_url = await avatar_service.upload_agent_avatar(db_mock, agent_id, upload_file)
        
        # Verify result
        assert result_url is not None
        assert "avatars/agents" in result_url
        
        # Verify database operations
        db_mock.get.assert_called_once_with(Agent, agent_id)
        db_mock.commit.assert_called()
        db_mock.refresh.assert_called_once_with(agent_mock)
        
        # Verify agent fields were updated
        assert agent_mock.avatar_url is not None
        assert agent_mock.has_custom_avatar == True
    
    @pytest.mark.asyncio
    async def test_upload_avatar_legacy_method(self, avatar_service, mock_upload_file, test_image_content):
        """Test legacy upload_avatar method"""
        db_mock = AsyncMock()
        user_id = uuid4()
        user_mock = MagicMock()
        db_mock.get.return_value = user_mock
        
        upload_file = mock_upload_file("legacy.png", test_image_content, "image/png")
        
        # This should call upload_user_avatar internally
        result_url = await avatar_service.upload_avatar(db_mock, user_id, upload_file)
        
        assert result_url is not None
        db_mock.get.assert_called_once_with(User, user_id)
    
    @pytest.mark.asyncio
    async def test_upload_user_avatar_user_not_found(self, avatar_service, mock_upload_file, test_image_content):
        """Test user avatar upload when user not found"""
        db_mock = AsyncMock()
        db_mock.get.return_value = None  # User not found
        
        user_id = uuid4()
        upload_file = mock_upload_file("test.png", test_image_content, "image/png")
        
        # Should raise HTTPException
        with pytest.raises(Exception):  # HTTPException
            await avatar_service.upload_user_avatar(db_mock, user_id, upload_file)
        
        db_mock.rollback.assert_called()
    
    @pytest.mark.asyncio
    async def test_upload_agent_avatar_agent_not_found(self, avatar_service, mock_upload_file, test_image_content):
        """Test agent avatar upload when agent not found"""
        db_mock = AsyncMock()
        db_mock.get.return_value = None  # Agent not found
        
        agent_id = uuid4()
        upload_file = mock_upload_file("test.png", test_image_content, "image/png")
        
        # Should raise HTTPException
        with pytest.raises(Exception):  # HTTPException
            await avatar_service.upload_agent_avatar(db_mock, agent_id, upload_file)
        
        db_mock.rollback.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_user_avatar_url(self, avatar_service, mock_upload_file, test_image_content):
        """Test getting user avatar URL"""
        # First upload an avatar
        db_mock = AsyncMock()
        user_id = uuid4()
        user_mock = MagicMock()
        db_mock.get.return_value = user_mock
        
        upload_file = mock_upload_file("test.png", test_image_content, "image/png")
        await avatar_service.upload_user_avatar(db_mock, user_id, upload_file)
        
        # Get avatar URL
        avatar_url = await avatar_service.get_user_avatar_url(user_id, "medium")
        assert avatar_url is not None
        assert f"avatars/users/{user_id}/medium" in avatar_url
        
        # Test non-existent user
        non_existent_url = await avatar_service.get_user_avatar_url(uuid4(), "medium")
        assert non_existent_url is None
    
    @pytest.mark.asyncio
    async def test_get_agent_avatar_url(self, avatar_service, mock_upload_file, test_image_content):
        """Test getting agent avatar URL"""
        # First upload an avatar
        db_mock = AsyncMock()
        agent_id = uuid4()
        agent_mock = MagicMock()
        db_mock.get.return_value = agent_mock
        
        upload_file = mock_upload_file("test.png", test_image_content, "image/png")
        await avatar_service.upload_agent_avatar(db_mock, agent_id, upload_file)
        
        # Get avatar URL
        avatar_url = await avatar_service.get_agent_avatar_url(agent_id, "large")
        assert avatar_url is not None
        assert f"avatars/agents/{agent_id}/large" in avatar_url
    
    @pytest.mark.asyncio
    async def test_get_avatar_path_legacy(self, avatar_service):
        """Test legacy get_avatar_path method"""
        user_id = uuid4()
        
        # Mock get_user_avatar_url to return a URL
        with patch.object(avatar_service, 'get_user_avatar_url', return_value="/test/avatar.jpg"):
            result = await avatar_service.get_avatar_path(user_id, "small")
            assert result == "/test/avatar.jpg"
    
    @pytest.mark.asyncio
    async def test_delete_user_avatar(self, avatar_service, mock_upload_file, test_image_content):
        """Test user avatar deletion"""
        # First upload an avatar
        db_mock = AsyncMock()
        user_id = uuid4()
        user_mock = MagicMock()
        db_mock.get.return_value = user_mock
        
        upload_file = mock_upload_file("test.png", test_image_content, "image/png")
        await avatar_service.upload_user_avatar(db_mock, user_id, upload_file)
        
        # Reset mock calls
        db_mock.reset_mock()
        
        # Delete avatar
        success = await avatar_service.delete_user_avatar(db_mock, user_id)
        
        # Verify deletion
        assert success == True
        db_mock.get.assert_called_once_with(User, user_id)
        assert user_mock.avatar_url is None
        db_mock.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_delete_agent_avatar(self, avatar_service, mock_upload_file, test_image_content):
        """Test agent avatar deletion"""
        # First upload an avatar
        db_mock = AsyncMock()
        agent_id = uuid4()
        agent_mock = MagicMock()
        agent_mock.has_custom_avatar = True
        db_mock.get.return_value = agent_mock
        
        upload_file = mock_upload_file("test.png", test_image_content, "image/png")
        await avatar_service.upload_agent_avatar(db_mock, agent_id, upload_file)
        
        # Reset mock calls
        db_mock.reset_mock()
        agent_mock.has_custom_avatar = True  # Reset after mock reset
        
        # Delete avatar
        success = await avatar_service.delete_agent_avatar(db_mock, agent_id)
        
        # Verify deletion
        assert success == True
        db_mock.get.assert_called_once_with(Agent, agent_id)
        assert agent_mock.avatar_url is None
        assert agent_mock.has_custom_avatar == False
        db_mock.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_delete_avatar_legacy(self, avatar_service):
        """Test legacy delete_avatar method"""
        db_mock = AsyncMock()
        user_id = uuid4()
        
        # Mock delete_user_avatar
        with patch.object(avatar_service, 'delete_user_avatar', return_value=True) as mock_delete:
            result = await avatar_service.delete_avatar(db_mock, user_id)
            assert result == True
            mock_delete.assert_called_once_with(db_mock, user_id)
    
    @pytest.mark.asyncio
    async def test_avatar_validation_errors(self, avatar_service, mock_upload_file):
        """Test avatar validation error handling"""
        db_mock = AsyncMock()
        user_id = uuid4()
        user_mock = MagicMock()
        db_mock.get.return_value = user_mock
        
        # Test invalid file type
        invalid_file = mock_upload_file("test.txt", b"not an image", "text/plain")
        
        with pytest.raises(Exception):  # HTTPException with 400 status
            await avatar_service.upload_user_avatar(db_mock, user_id, invalid_file)
        
        # Test oversized file
        large_content = b"x" * (6 * 1024 * 1024)  # 6MB
        large_file = mock_upload_file("large.png", large_content, "image/png")
        
        with pytest.raises(Exception):  # HTTPException with 400 status
            await avatar_service.upload_user_avatar(db_mock, user_id, large_file)
    
    def test_service_properties(self, avatar_service):
        """Test service properties"""
        assert avatar_service.backend_type == "local"
        assert avatar_service.supports_signed_urls == False


class TestAvatarServiceIntegration:
    """Integration tests for AvatarService with real storage"""
    
    @pytest.mark.asyncio
    async def test_complete_user_avatar_workflow(self, temp_dir):
        """Test complete user avatar workflow"""
        # Setup real storage backend
        backend = LocalStorageBackend(base_path=temp_dir, base_url="/test")
        storage_service = StorageService(backend)
        
        avatar_service = AvatarService()
        avatar_service.storage_service = storage_service
        
        # Create mock database session
        db_mock = AsyncMock()
        user_id = uuid4()
        user_mock = MagicMock()
        user_mock.avatar_url = None
        db_mock.get.return_value = user_mock
        
        # Create test image
        img = Image.new('RGB', (200, 200), color='blue')
        img_buffer = BytesIO()
        img.save(img_buffer, format='JPEG')
        img_content = img_buffer.getvalue()
        
        # Mock upload file
        class MockUploadFile:
            def __init__(self, filename, content, content_type):
                self.filename = filename
                self.content = content
                self.content_type = content_type
                
            async def read(self):
                return self.content
                
            async def seek(self, position):
                pass
        
        upload_file = MockUploadFile("test.jpg", img_content, "image/jpeg")
        
        # 1. Upload avatar
        result_url = await avatar_service.upload_user_avatar(db_mock, user_id, upload_file)
        assert result_url is not None
        
        # 2. Get avatar URL
        medium_url = await avatar_service.get_user_avatar_url(user_id, "medium")
        assert medium_url is not None
        assert f"avatars/users/{user_id}/medium" in medium_url
        
        # 3. Verify all thumbnail sizes exist
        for size in ["small", "medium", "large", "original"]:
            url = await avatar_service.get_user_avatar_url(user_id, size)
            assert url is not None
        
        # 4. Delete avatar
        success = await avatar_service.delete_user_avatar(db_mock, user_id)
        assert success == True
        
        # 5. Verify avatar is deleted
        deleted_url = await avatar_service.get_user_avatar_url(user_id, "medium")
        assert deleted_url is None