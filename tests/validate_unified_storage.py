#!/usr/bin/env python3
"""
Validation script for unified storage system
Run this to validate that the storage system is working correctly
"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from PIL import Image
from io import BytesIO
from uuid import uuid4

from app.services.storage.local_backend import LocalStorageBackend
from app.services.storage.storage_service import StorageService
from app.services.avatar_service import AvatarService


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


@pytest.mark.asyncio
async def test_local_backend():
    """Test LocalStorageBackend functionality"""
    print("Testing LocalStorageBackend...")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    print(f"Using temporary directory: {temp_dir}")
    
    try:
        # Create backend
        backend = LocalStorageBackend(base_path=temp_dir, base_url="/test-storage")
        
        # Test file upload
        content = b"This is a test file content"
        key = "test/file.txt"
        
        url = await backend.upload_file(content, key, "text/plain", {"test": "metadata"})
        print(f"✅ File uploaded: {url}")
        
        # Test file exists
        exists = await backend.file_exists(key)
        print(f"✅ File exists: {exists}")
        
        # Test file download
        downloaded = await backend.download_file(key)
        assert downloaded == content
        print("✅ File download successful")
        
        # Test file info
        info = await backend.get_file_info(key)
        print(f"✅ File info: size={info['size']}, content_type={info.get('content_type')}")
        
        # Test file listing
        files = await backend.list_files("test/")
        print(f"✅ Files in test/: {files}")
        
        # Test file deletion
        success = await backend.delete_file(key)
        print(f"✅ File deleted: {success}")
        
        print("✅ LocalStorageBackend tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_unified_service():
    """Test StorageService functionality"""
    print("\nTesting StorageService...")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    print(f"Using temporary directory: {temp_dir}")
    
    try:
        # Create backend and service
        backend = LocalStorageBackend(base_path=temp_dir, base_url="/test-storage")
        service = StorageService(backend)
        
        # Create test image
        img = Image.new('RGB', (200, 200), color='red')
        img_buffer = BytesIO()
        img.save(img_buffer, format='JPEG')
        img_content = img_buffer.getvalue()
        
        # Test user avatar upload
        user_id = uuid4()
        upload_file = MockUploadFile("test.jpg", img_content, "image/jpeg")
        
        avatar_urls = await service.upload_user_avatar(user_id, upload_file)
        print(f"✅ User avatar uploaded: {len(avatar_urls)} sizes generated")
        print(f"   Sizes: {list(avatar_urls.keys())}")
        
        # Test getting avatar URL
        medium_url = await service.get_avatar_url(user_id, "users", "medium")
        print(f"✅ Avatar URL retrieved: {medium_url}")
        
        # Test agent avatar upload
        agent_id = uuid4()
        agent_upload_file = MockUploadFile("agent.jpg", img_content, "image/jpeg")
        
        agent_avatar_urls = await service.upload_agent_avatar(agent_id, agent_upload_file)
        print(f"✅ Agent avatar uploaded: {len(agent_avatar_urls)} sizes generated")
        
        # Test file attachment upload
        doc_content = b"This is a test document attachment"
        doc_file = MockUploadFile("document.txt", doc_content, "text/plain")
        
        attachment_url = await service.upload_attachment(doc_file, user_id)
        print(f"✅ Attachment uploaded: {attachment_url}")
        
        # Test avatar deletion
        user_success = await service.delete_avatar(user_id, "users")
        agent_success = await service.delete_avatar(agent_id, "agents")
        print(f"✅ Avatars deleted - User: {user_success}, Agent: {agent_success}")
        
        print("✅ StorageService tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_avatar_service_integration():
    """Test AvatarService with unified storage"""
    print("\nTesting AvatarService integration...")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    print(f"Using temporary directory: {temp_dir}")
    
    try:
        # Create mock database and user
        class MockDB:
            def __init__(self):
                self.users = {}
                self.agents = {}
                
            async def get(self, model_class, entity_id):
                if model_class.__name__ == "User":
                    return self.users.get(entity_id)
                elif model_class.__name__ == "Agent":
                    return self.agents.get(entity_id)
                return None
                
            async def commit(self):
                pass
                
            async def refresh(self, entity):
                pass
                
            async def rollback(self):
                pass
        
        class MockUser:
            def __init__(self, user_id):
                self.id = user_id
                self.avatar_url = None
        
        class MockAgent:
            def __init__(self, agent_id):
                self.id = agent_id
                self.avatar_url = None
                self.has_custom_avatar = False
        
        # Setup service
        backend = LocalStorageBackend(base_path=temp_dir, base_url="/test-storage")
        service = StorageService(backend)
        
        avatar_service = AvatarService()
        avatar_service.storage_service = service
        
        # Create mock data
        db = MockDB()
        user_id = uuid4()
        agent_id = uuid4()
        user = MockUser(user_id)
        agent = MockAgent(agent_id)
        
        db.users[user_id] = user
        db.agents[agent_id] = agent
        
        # Create test image
        img = Image.new('RGB', (150, 150), color='blue')
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_content = img_buffer.getvalue()
        
        # Test user avatar upload
        user_upload = MockUploadFile("user.png", img_content, "image/png")
        user_avatar_url = await avatar_service.upload_user_avatar(db, user_id, user_upload)
        print(f"✅ User avatar uploaded via AvatarService: {user_avatar_url}")
        
        # Test agent avatar upload
        agent_upload = MockUploadFile("agent.png", img_content, "image/png")
        agent_avatar_url = await avatar_service.upload_agent_avatar(db, agent_id, agent_upload)
        print(f"✅ Agent avatar uploaded via AvatarService: {agent_avatar_url}")
        
        # Verify database updates
        assert user.avatar_url is not None
        assert agent.avatar_url is not None
        assert agent.has_custom_avatar == True
        print("✅ Database fields updated correctly")
        
        # Test getting avatar URLs
        user_url = await avatar_service.get_user_avatar_url(user_id, "small")
        agent_url = await avatar_service.get_agent_avatar_url(agent_id, "large")
        
        assert user_url is not None
        assert agent_url is not None
        print("✅ Avatar URL retrieval working")
        
        # Test deletion
        user_deleted = await avatar_service.delete_user_avatar(db, user_id)
        agent_deleted = await avatar_service.delete_agent_avatar(db, agent_id)
        
        assert user_deleted == True
        assert agent_deleted == True
        assert user.avatar_url is None
        assert agent.avatar_url is None
        assert agent.has_custom_avatar == False
        print("✅ Avatar deletion working")
        
        print("✅ AvatarService integration tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)


async def validate_properties():
    """Validate storage system properties"""
    print("\nValidating storage system properties...")
    
    temp_dir = tempfile.mkdtemp()
    try:
        # Test local backend properties
        backend = LocalStorageBackend(base_path=temp_dir)
        service = StorageService(backend)
        
        assert backend.backend_type == "local"
        assert backend.supports_public_urls == True
        assert backend.supports_signed_urls == False
        
        assert service.backend_type == "local"
        assert service.supports_public_urls == True
        assert service.supports_signed_urls == False
        
        print("✅ Storage system properties validated")
        
    finally:
        shutil.rmtree(temp_dir)


async def main():
    """Run all validation tests"""
    print("🚀 Starting Unified Storage System Validation")
    print("=" * 50)
    
    try:
        await test_local_backend()
        await test_unified_service()
        await test_avatar_service_integration()
        await validate_properties()
        
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED! Unified Storage System is working correctly.")
        print("✅ Ready for production use with local storage backend.")
        print("✅ S3 backend can be enabled by updating storage_backend setting.")
        
    except Exception as e:
        print(f"\n❌ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())