#!/usr/bin/env python3
"""
Integration tests for unified storage system with existing avatar functionality
"""

import pytest
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from PIL import Image
from io import BytesIO

from app.services.avatar_service import AvatarService
from app.services.file_service import FileService
from app.services.storage.factory import create_storage_service, reset_storage_service
from app.services.storage.local_backend import LocalStorageBackend
from app.models.user import User
from app.models.ai_agent import Agent


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)
    reset_storage_service()  # Reset global service


@pytest.fixture
def mock_db():
    """Create mock database session"""
    return AsyncMock()


@pytest.fixture
def mock_user():
    """Create mock user"""
    user = MagicMock()
    user.id = uuid4()
    user.organization_id = uuid4()
    user.avatar_url = None
    return user


@pytest.fixture
def mock_agent():
    """Create mock agent"""
    agent = MagicMock()
    agent.id = uuid4()
    agent.organization_id = uuid4()
    agent.avatar_url = None
    agent.has_custom_avatar = False
    return agent


@pytest.fixture
def test_image_content():
    """Create test image content"""
    img = Image.new('RGB', (200, 200), color='blue')
    img_buffer = BytesIO()
    img.save(img_buffer, format='JPEG')
    return img_buffer.getvalue()


@pytest.fixture
def mock_upload_file():
    """Create mock UploadFile factory"""
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


class TestUnifiedStorageIntegration:
    """Integration tests for unified storage system"""
    
    @pytest.mark.asyncio
    async def test_avatar_service_with_local_backend(self, temp_dir, mock_db, mock_user, test_image_content, mock_upload_file):
        """Test AvatarService with local storage backend"""
        # Setup local storage backend
        with patch('app.services.storage.factory.get_settings') as mock_settings:
            mock_settings.return_value.storage_backend = "local"
            mock_settings.return_value.upload_directory = temp_dir
            
            # Create service with local backend
            reset_storage_service()
            service = create_storage_service(backend_type="local", base_path=temp_dir)
            
            # Create AvatarService instance
            avatar_service = AvatarService()
            avatar_service.storage_service = service
            
            # Mock database operations
            mock_db.get.return_value = mock_user
            
            # Create upload file
            upload_file = mock_upload_file("test.jpg", test_image_content, "image/jpeg")
            
            # Upload user avatar
            result_url = await avatar_service.upload_user_avatar(mock_db, mock_user.id, upload_file)
            
            # Verify result
            assert result_url is not None
            assert "avatars/users" in result_url
            
            # Verify database operations
            mock_db.get.assert_called_with(User, mock_user.id)
            mock_db.commit.assert_called()
            assert mock_user.avatar_url is not None
            
            # Test getting avatar URL
            avatar_url = await avatar_service.get_user_avatar_url(mock_user.id, "medium")
            assert avatar_url is not None
            
            # Test deletion
            success = await avatar_service.delete_user_avatar(mock_db, mock_user.id)
            assert success == True
    
    @pytest.mark.asyncio
    async def test_agent_avatar_workflow(self, temp_dir, mock_db, mock_agent, test_image_content, mock_upload_file):
        """Test complete agent avatar workflow"""
        # Setup local storage backend
        with patch('app.services.storage.factory.get_settings') as mock_settings:
            mock_settings.return_value.storage_backend = "local"
            mock_settings.return_value.upload_directory = temp_dir
            
            reset_storage_service()
            service = create_storage_service(backend_type="local", base_path=temp_dir)
            
            avatar_service = AvatarService()
            avatar_service.storage_service = service
            
            # Mock database operations
            mock_db.get.return_value = mock_agent
            
            # Create upload file
            upload_file = mock_upload_file("agent.png", test_image_content, "image/png")
            
            # Upload agent avatar
            result_url = await avatar_service.upload_agent_avatar(mock_db, mock_agent.id, upload_file)
            
            # Verify result
            assert result_url is not None
            assert "avatars/agents" in result_url
            
            # Verify database operations
            mock_db.get.assert_called_with(Agent, mock_agent.id)
            assert mock_agent.avatar_url is not None
            assert mock_agent.has_custom_avatar == True
            
            # Test getting avatar URL
            avatar_url = await avatar_service.get_agent_avatar_url(mock_agent.id, "large")
            assert avatar_url is not None
            
            # Test deletion
            success = await avatar_service.delete_agent_avatar(mock_db, mock_agent.id)
            assert success == True
            assert mock_agent.avatar_url is None
            assert mock_agent.has_custom_avatar == False
    
    @pytest.mark.asyncio
    async def test_file_service_integration(self, temp_dir, mock_db):
        """Test FileService integration with unified storage - simplified version focusing on storage"""
        # Test that FileService uses unified storage correctly
        
        # Setup local storage backend
        with patch('app.services.storage.factory.get_settings') as mock_settings:
            mock_settings.return_value.storage_backend = "local"
            mock_settings.return_value.upload_directory = temp_dir
            mock_settings.return_value.max_file_size = 10 * 1024 * 1024  # 10MB
            mock_settings.return_value.allowed_file_types = ["text/plain", "image/jpeg"]
            
            reset_storage_service()
            
            # Create FileService instance
            file_service = FileService()
            
            # Verify the service is using unified storage
            assert hasattr(file_service, 'storage_service')
            assert file_service.storage_service is not None
            assert file_service.storage_service.backend_type == "local"
            
            # Test direct storage backend functionality
            backend = file_service.storage_service.backend
            
            # Test file upload to storage
            test_content = b"Test file for unified storage"
            test_key = "test/unified_storage_test.txt"
            
            url = await backend.upload_file(test_content, test_key, "text/plain")
            assert url is not None
            assert test_key in url
            
            # Test file exists
            exists = await backend.file_exists(test_key)
            assert exists == True
            
            # Test file download
            downloaded = await backend.download_file(test_key)
            assert downloaded == test_content
            
            # Test file deletion
            success = await backend.delete_file(test_key)
            assert success == True
            
            # Verify deletion
            exists_after = await backend.file_exists(test_key)
            assert exists_after == False
    
    @pytest.mark.asyncio
    async def test_storage_backend_switching(self, temp_dir):
        """Test switching between storage backends"""
        # Test local backend
        with patch('app.services.storage.factory.get_settings') as mock_settings:
            mock_settings.return_value.storage_backend = "local"
            mock_settings.return_value.upload_directory = temp_dir
            
            reset_storage_service()
            local_service = create_storage_service()
            
            assert local_service.backend_type == "local"
            assert local_service.supports_public_urls == True
            assert local_service.supports_signed_urls == False
        
        # Test S3 backend (mocked)
        with patch('app.services.storage.factory.get_settings') as mock_settings:
            mock_settings.return_value.storage_backend = "s3"
            mock_settings.return_value.s3_bucket_name = "test-bucket"
            mock_settings.return_value.aws_region = "us-east-1"
            mock_settings.return_value.aws_access_key_id = "test-key"
            mock_settings.return_value.aws_secret_access_key = "test-secret"
            mock_settings.return_value.s3_bucket_path = ""
            mock_settings.return_value.cloudfront_domain = None
            
            # Mock boto3 session to avoid real AWS calls
            with patch('boto3.Session') as mock_session:
                mock_client = MagicMock()
                mock_client.head_bucket.return_value = {}
                mock_session.return_value.client.return_value = mock_client
                
                reset_storage_service()
                s3_service = create_storage_service()
                
                assert s3_service.backend_type == "s3"
                assert s3_service.supports_public_urls == True
                assert s3_service.supports_signed_urls == True
    
    @pytest.mark.asyncio
    async def test_backwards_compatibility(self, temp_dir, mock_db, mock_user, test_image_content, mock_upload_file):
        """Test that legacy avatar methods still work"""
        # Setup service
        with patch('app.services.storage.factory.get_settings') as mock_settings:
            mock_settings.return_value.storage_backend = "local"
            mock_settings.return_value.upload_directory = temp_dir
            
            reset_storage_service()
            service = create_storage_service(backend_type="local", base_path=temp_dir)
            
            avatar_service = AvatarService()
            avatar_service.storage_service = service
            
            mock_db.get.return_value = mock_user
            upload_file = mock_upload_file("legacy.jpg", test_image_content, "image/jpeg")
            
            # Test legacy upload_avatar method
            result_url = await avatar_service.upload_avatar(mock_db, mock_user.id, upload_file)
            assert result_url is not None
            
            # Test legacy get_avatar_path method (now returns URL)
            avatar_path = await avatar_service.get_avatar_path(mock_user.id, "medium")
            assert avatar_path is not None
            
            # Test legacy delete_avatar method
            success = await avatar_service.delete_avatar(mock_db, mock_user.id)
            assert success == True
    
    @pytest.mark.asyncio
    async def test_error_handling(self, temp_dir, mock_db, mock_user, mock_upload_file):
        """Test error handling in unified storage"""
        with patch('app.services.storage.factory.get_settings') as mock_settings:
            mock_settings.return_value.storage_backend = "local"
            mock_settings.return_value.upload_directory = temp_dir
            
            reset_storage_service()
            service = create_storage_service(backend_type="local", base_path=temp_dir)
            
            avatar_service = AvatarService()
            avatar_service.storage_service = service
            
            mock_db.get.return_value = mock_user
            
            # Test invalid file type
            invalid_file = mock_upload_file("test.txt", b"not an image", "text/plain")
            
            with pytest.raises(Exception):
                await avatar_service.upload_user_avatar(mock_db, mock_user.id, invalid_file)
            
            # Test oversized file
            large_content = b"x" * (6 * 1024 * 1024)  # 6MB, over 5MB limit
            large_file = mock_upload_file("large.jpg", large_content, "image/jpeg")
            
            with pytest.raises(Exception):
                await avatar_service.upload_user_avatar(mock_db, mock_user.id, large_file)
            
            # Test user not found
            mock_db.get.return_value = None
            valid_img = Image.new('RGB', (100, 100), color='red')
            img_buffer = BytesIO()
            valid_img.save(img_buffer, format='JPEG')
            valid_content = img_buffer.getvalue()
            
            valid_file = mock_upload_file("valid.jpg", valid_content, "image/jpeg")
            
            with pytest.raises(Exception):  # HTTPException
                await avatar_service.upload_user_avatar(mock_db, mock_user.id, valid_file)


@pytest.mark.asyncio
class TestRealFileOperations:
    """Test actual file operations with temporary directories"""
    
    async def test_complete_avatar_lifecycle(self, temp_dir):
        """Test complete avatar lifecycle with real file operations"""
        # Setup real local backend
        backend = LocalStorageBackend(base_path=temp_dir, base_url="/test")
        
        # Create test image
        img = Image.new('RGB', (300, 300), color='green')
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_content = img_buffer.getvalue()
        
        # Test direct backend operations
        key = "avatars/users/test-user/medium.png"
        
        # Upload
        url = await backend.upload_file(img_content, key, "image/png")
        assert url is not None
        assert key in url
        
        # Check exists
        exists = await backend.file_exists(key)
        assert exists == True
        
        # Download
        downloaded = await backend.download_file(key)
        assert downloaded == img_content
        
        # Get info
        info = await backend.get_file_info(key)
        assert info is not None
        assert info['size'] == len(img_content)
        assert info['content_type'] == "image/png"
        
        # List files
        files = await backend.list_files("avatars/")
        assert key in files
        
        # Delete
        success = await backend.delete_file(key)
        assert success == True
        
        # Verify deleted
        exists_after = await backend.file_exists(key)
        assert exists_after == False