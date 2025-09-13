#!/usr/bin/env python3
"""
Unit tests for Avatar Service with storage
"""

import pytest
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from pathlib import Path
from io import BytesIO

from fastapi import UploadFile
from PIL import Image

from app.services.avatar_service import AvatarService
from app.services.storage.local_backend import LocalStorageBackend
from app.services.storage.storage_service import StorageService
from app.services.storage.avatar_storage_service import AvatarStorageService
from app.models.user import User
from app.models.ai_agent import Agent


class MockUploadFile:
    """Mock UploadFile for testing"""
    def __init__(self, filename, content, content_type):
        self.filename = filename
        self.content = content
        self.content_type = content_type
        
    async def read(self):
        return self.content
        
    async def seek(self, position):
        pass


class TestAvatarService:
    """Test cases for AvatarService with storage"""
    
    def test_avatar_service_initialization(self):
        """Test avatar service initializes correctly with storage"""
        service = AvatarService()
        
        # Check service has avatar_storage_service
        assert service.avatar_storage_service is not None
        assert hasattr(service, 'backend_type')
        assert hasattr(service, 'supports_signed_urls')
        
        print("✅ Avatar service initialization with storage working")
    
    @pytest.mark.asyncio
    async def test_validate_via_storage_service(self):
        """Test validation works through storage service"""
        # Setup temporary directory and service
        temp_dir = tempfile.mkdtemp()
        try:
            backend = LocalStorageBackend(base_path=temp_dir)
            avatar_storage_service = AvatarStorageService(backend)
            
            # Create test image
            img = Image.new('RGB', (100, 100), color='red')
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG')
            img_content = img_buffer.getvalue()
            
            # Test valid file
            valid_file = MockUploadFile("test.png", img_content, "image/png")
            user_id = uuid4()
            
            # Should not raise exception
            avatar_urls = await avatar_storage_service.upload_user_avatar(user_id, valid_file)
            assert len(avatar_urls) == 4  # original + 3 thumbnails
            
            # Test invalid file type
            invalid_file = MockUploadFile("test.txt", b"not an image", "text/plain")
            
            with pytest.raises(Exception):
                await avatar_storage_service.upload_user_avatar(user_id, invalid_file)
            
            # Test oversized file
            large_content = b"x" * (6 * 1024 * 1024)  # 6MB
            large_file = MockUploadFile("large.png", large_content, "image/png")
            
            with pytest.raises(Exception):
                await avatar_storage_service.upload_user_avatar(user_id, large_file)
            
            print("✅ Avatar validation through storage working")
        finally:
            shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_upload_user_avatar_success_path(self):
        """Test successful user avatar upload through AvatarService"""
        # Setup
        temp_dir = tempfile.mkdtemp()
        try:
            backend = LocalStorageBackend(base_path=temp_dir)
            storage_service = StorageService(backend)
            
            avatar_service = AvatarService()
            avatar_service.storage_service = storage_service
            
            # Create mock database session and user
            mock_db = AsyncMock()
            mock_user = MagicMock()
            mock_user.id = uuid4()
            mock_user.avatar_url = None
            mock_db.get.return_value = mock_user
            
            # Create test image
            img = Image.new('RGB', (150, 150), color='blue')
            img_buffer = BytesIO()
            img.save(img_buffer, format='JPEG')
            img_content = img_buffer.getvalue()
            
            # Upload avatar
            upload_file = MockUploadFile("test.jpg", img_content, "image/jpeg")
            result_url = await avatar_service.upload_user_avatar(mock_db, mock_user.id, upload_file)
            
            # Verify result
            assert result_url is not None
            assert "avatars/users" in result_url
            
            # Verify database was updated
            mock_db.get.assert_called_with(User, mock_user.id)
            mock_db.commit.assert_called()
            assert mock_user.avatar_url is not None
            
            print("✅ User avatar upload through AvatarService working")
        finally:
            shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_upload_agent_avatar_success_path(self):
        """Test successful agent avatar upload through AvatarService"""
        # Setup
        temp_dir = tempfile.mkdtemp()
        try:
            backend = LocalStorageBackend(base_path=temp_dir)
            storage_service = StorageService(backend)
            
            avatar_service = AvatarService()
            avatar_service.storage_service = storage_service
            
            # Create mock database session and agent
            mock_db = AsyncMock()
            mock_agent = MagicMock()
            mock_agent.id = uuid4()
            mock_agent.avatar_url = None
            mock_agent.has_custom_avatar = False
            mock_db.get.return_value = mock_agent
            
            # Create test image
            img = Image.new('RGB', (150, 150), color='green')
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG')
            img_content = img_buffer.getvalue()
            
            # Upload avatar
            upload_file = MockUploadFile("agent.png", img_content, "image/png")
            result_url = await avatar_service.upload_agent_avatar(mock_db, mock_agent.id, upload_file)
            
            # Verify result
            assert result_url is not None
            assert "avatars/agents" in result_url
            
            # Verify database was updated
            mock_db.get.assert_called_with(Agent, mock_agent.id)
            mock_db.commit.assert_called()
            assert mock_agent.avatar_url is not None
            assert mock_agent.has_custom_avatar == True
            
            print("✅ Agent avatar upload through AvatarService working")
        finally:
            shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_get_avatar_path_legacy_compatibility(self):
        """Test legacy get_avatar_path method compatibility"""
        # Setup
        temp_dir = tempfile.mkdtemp()
        try:
            backend = LocalStorageBackend(base_path=temp_dir)
            storage_service = StorageService(backend)
            
            avatar_service = AvatarService()
            avatar_service.storage_service = storage_service
            
            user_id = uuid4()
            
            # Test with no avatar (should return None)
            result = await avatar_service.get_avatar_path(user_id)
            assert result is None
            
            # Test with avatar (first upload one)
            mock_db = AsyncMock()
            mock_user = MagicMock()
            mock_user.id = user_id
            mock_user.avatar_url = None
            mock_db.get.return_value = mock_user
            
            # Create test image and upload
            img = Image.new('RGB', (100, 100), color='yellow')
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG')
            img_content = img_buffer.getvalue()
            
            upload_file = MockUploadFile("test.png", img_content, "image/png")
            await avatar_service.upload_user_avatar(mock_db, user_id, upload_file)
            
            # Now test getting the path (should return URL)
            result = await avatar_service.get_avatar_path(user_id, "medium")
            assert result is not None
            assert "avatars/users" in result
            
            print("✅ Legacy get_avatar_path compatibility working")
        finally:
            shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_delete_avatar_legacy_compatibility(self):
        """Test legacy delete_avatar method compatibility"""
        # Setup
        temp_dir = tempfile.mkdtemp()
        try:
            backend = LocalStorageBackend(base_path=temp_dir)
            storage_service = StorageService(backend)
            
            avatar_service = AvatarService()
            avatar_service.storage_service = storage_service
            
            # Create mock database session and user
            mock_db = AsyncMock()
            user_id = uuid4()
            mock_user = MagicMock()
            mock_user.id = user_id
            mock_user.avatar_url = None
            mock_db.get.return_value = mock_user
            
            # First upload an avatar
            img = Image.new('RGB', (100, 100), color='purple')
            img_buffer = BytesIO()
            img.save(img_buffer, format='JPEG')
            img_content = img_buffer.getvalue()
            
            upload_file = MockUploadFile("test.jpg", img_content, "image/jpeg")
            await avatar_service.upload_user_avatar(mock_db, user_id, upload_file)
            
            # Reset mock calls
            mock_db.reset_mock()
            mock_user.avatar_url = "/some/avatar/url"  # Simulate existing avatar
            
            # Test delete_avatar (legacy method)
            result = await avatar_service.delete_avatar(mock_db, user_id)
            
            # Verify result
            assert result == True
            
            # Verify database operations
            mock_db.get.assert_called_with(User, user_id)
            mock_db.commit.assert_called()
            assert mock_user.avatar_url is None
            
            print("✅ Legacy delete_avatar compatibility working")
        finally:
            shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_service_properties(self):
        """Test service properties work correctly"""
        # Setup with local backend
        temp_dir = tempfile.mkdtemp()
        try:
            backend = LocalStorageBackend(base_path=temp_dir)
            storage_service = StorageService(backend)
            
            avatar_service = AvatarService()
            avatar_service.storage_service = storage_service
            
            # Test properties
            assert avatar_service.backend_type == "local"
            assert avatar_service.supports_signed_urls == False
            
            print("✅ Service properties working")
        finally:
            shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in avatar service"""
        # Setup
        temp_dir = tempfile.mkdtemp()
        try:
            backend = LocalStorageBackend(base_path=temp_dir)
            storage_service = StorageService(backend)
            
            avatar_service = AvatarService()
            avatar_service.storage_service = storage_service
            
            # Test user not found
            mock_db = AsyncMock()
            mock_db.get.return_value = None  # User not found
            
            user_id = uuid4()
            
            # Create valid image
            img = Image.new('RGB', (100, 100), color='red')
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG')
            img_content = img_buffer.getvalue()
            
            upload_file = MockUploadFile("test.png", img_content, "image/png")
            
            # Should raise HTTPException
            with pytest.raises(Exception):
                await avatar_service.upload_user_avatar(mock_db, user_id, upload_file)
            
            # Verify rollback was called
            mock_db.rollback.assert_called()
            
            print("✅ Error handling working")
        finally:
            shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio  
    async def test_backward_compatibility_methods(self):
        """Test that legacy methods still work"""
        # Setup
        temp_dir = tempfile.mkdtemp()
        try:
            backend = LocalStorageBackend(base_path=temp_dir)
            storage_service = StorageService(backend)
            
            avatar_service = AvatarService()
            avatar_service.storage_service = storage_service
            
            # Create mock database and user
            mock_db = AsyncMock()
            user_id = uuid4()
            mock_user = MagicMock()
            mock_user.id = user_id
            mock_user.avatar_url = None
            mock_db.get.return_value = mock_user
            
            # Create test image
            img = Image.new('RGB', (100, 100), color='orange')
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG')
            img_content = img_buffer.getvalue()
            
            # Test legacy upload_avatar method
            upload_file = MockUploadFile("legacy.png", img_content, "image/png")
            result = await avatar_service.upload_avatar(mock_db, user_id, upload_file)
            assert result is not None
            
            # Test get_avatar_path (legacy)
            path_result = await avatar_service.get_avatar_path(user_id, "small")
            assert path_result is not None
            
            # Test delete_avatar (legacy)
            delete_result = await avatar_service.delete_avatar(mock_db, user_id)
            assert delete_result == True
            
            print("✅ Backward compatibility methods working")
        finally:
            shutil.rmtree(temp_dir)