#!/usr/bin/env python3
"""
Tests for unified storage system
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from uuid import uuid4

from app.services.storage.local_backend import LocalStorageBackend
from app.services.storage.storage_service import StorageService
from app.services.storage.factory import create_storage_backend, create_storage_service


class TestLocalStorageBackend:
    """Tests for LocalStorageBackend"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def backend(self, temp_dir):
        """Create LocalStorageBackend instance for testing"""
        return LocalStorageBackend(
            base_path=temp_dir,
            base_url="/test-storage"
        )
    
    @pytest.mark.asyncio
    async def test_upload_file(self, backend):
        """Test file upload"""
        content = b"test file content"
        key = "test/file.txt"
        content_type = "text/plain"
        metadata = {"test": "value"}
        
        # Upload file
        url = await backend.upload_file(content, key, content_type, metadata)
        
        # Check URL format
        assert url == "/test-storage/test/file.txt"
        
        # Check file exists
        assert await backend.file_exists(key)
        
        # Check content
        downloaded = await backend.download_file(key)
        assert downloaded == content
    
    @pytest.mark.asyncio
    async def test_file_info(self, backend):
        """Test file info retrieval"""
        content = b"test content"
        key = "info/test.txt"
        metadata = {"custom": "metadata"}
        
        # Upload file
        await backend.upload_file(content, key, "text/plain", metadata)
        
        # Get file info
        info = await backend.get_file_info(key)
        
        assert info is not None
        assert info["size"] == len(content)
        assert info["content_type"] == "text/plain"
        assert info["custom"] == "metadata"
        assert "uploaded_at" in info
    
    @pytest.mark.asyncio
    async def test_delete_file(self, backend):
        """Test file deletion"""
        content = b"delete me"
        key = "delete/test.txt"
        
        # Upload file
        await backend.upload_file(content, key)
        assert await backend.file_exists(key)
        
        # Delete file
        success = await backend.delete_file(key)
        assert success
        assert not await backend.file_exists(key)
    
    @pytest.mark.asyncio
    async def test_list_files(self, backend):
        """Test file listing"""
        # Upload multiple files
        files = [
            ("list/file1.txt", b"content1"),
            ("list/file2.txt", b"content2"),
            ("other/file3.txt", b"content3"),
        ]
        
        for key, content in files:
            await backend.upload_file(content, key)
        
        # List all files
        all_files = await backend.list_files()
        assert len(all_files) >= 3
        
        # List with prefix
        list_files = await backend.list_files("list/")
        assert len(list_files) == 2
        assert "list/file1.txt" in list_files
        assert "list/file2.txt" in list_files
        
        # List with limit
        limited_files = await backend.list_files("", limit=1)
        assert len(limited_files) == 1
    
    def test_backend_properties(self, backend):
        """Test backend properties"""
        assert backend.backend_type == "local"
        assert backend.supports_public_urls == True
        assert backend.supports_signed_urls == False


class TestStorageService:
    """Tests for StorageService (generic file operations)"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def service(self, temp_dir):
        """Create StorageService instance for testing"""
        backend = LocalStorageBackend(
            base_path=temp_dir,
            base_url="/test-storage"
        )
        return StorageService(backend)
    
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
    async def test_upload_file(self, service, mock_upload_file):
        """Test generic file upload"""
        content = b"This is a test file"
        upload_file = mock_upload_file("test.txt", content, "text/plain")
        storage_key = "test/file.txt"
        metadata = {"user_id": "123", "type": "document"}
        
        # Upload file
        file_url = await service.upload_file(upload_file, storage_key, metadata)
        
        assert file_url is not None
        assert storage_key in file_url
    
    @pytest.mark.asyncio
    async def test_upload_content(self, service):
        """Test raw content upload"""
        content = b"Raw content data"
        storage_key = "content/test.bin"
        content_type = "application/octet-stream"
        
        # Upload content
        file_url = await service.upload_content(content, storage_key, content_type)
        
        assert file_url is not None
        assert storage_key in file_url
    
    @pytest.mark.asyncio
    async def test_download_file(self, service):
        """Test file download"""
        content = b"Download test content"
        storage_key = "download/test.txt"
        
        # Upload first
        await service.upload_content(content, storage_key, "text/plain")
        
        # Download
        downloaded = await service.download_file(storage_key)
        assert downloaded == content
    
    @pytest.mark.asyncio
    async def test_file_operations(self, service):
        """Test basic file operations"""
        content = b"File operations test"
        storage_key = "ops/test.txt"
        
        # Upload
        await service.upload_content(content, storage_key, "text/plain")
        
        # Check exists
        exists = await service.file_exists(storage_key)
        assert exists == True
        
        # Get info
        info = await service.get_file_info(storage_key)
        assert info is not None
        assert info['size'] == len(content)
        
        # Get URL
        url = await service.get_file_url(storage_key)
        assert url is not None
        
        # Delete
        success = await service.delete_file(storage_key)
        assert success == True
        
        # Verify deleted
        exists_after = await service.file_exists(storage_key)
        assert exists_after == False
    
    @pytest.mark.asyncio
    async def test_list_files(self, service):
        """Test file listing"""
        # Upload multiple files
        files = [
            ("list/file1.txt", b"content1"),
            ("list/file2.txt", b"content2"),
            ("other/file3.txt", b"content3"),
        ]
        
        for key, content in files:
            await service.upload_content(content, key, "text/plain")
        
        # List all files
        all_files = await service.list_files()
        assert len(all_files) >= 3
        
        # List with prefix
        list_files = await service.list_files("list/")
        assert len(list_files) == 2
        
        # List with limit
        limited_files = await service.list_files("", limit=1)
        assert len(limited_files) == 1
    
    @pytest.mark.asyncio
    async def test_generate_storage_key(self, service):
        """Test storage key generation"""
        # Test attachment key
        attachment_key = await service.generate_storage_key("attachments", "test.pdf")
        assert "attachments/" in attachment_key
        assert attachment_key.endswith(".pdf")
        
        # Test document key
        doc_key = await service.generate_storage_key("documents", "doc.docx")
        assert "documents/" in doc_key
        assert doc_key.endswith(".docx")
        
        # Test temp key
        temp_key = await service.generate_storage_key("temp", "temp.jpg")
        assert "temp/" in temp_key
        assert temp_key.endswith(".jpg")
    
    def test_service_properties(self, service):
        """Test service properties"""
        assert service.backend_type == "local"
        assert service.supports_public_urls == True
        assert service.supports_signed_urls == False


class TestStorageFactory:
    """Tests for storage factory functions"""
    
    def test_create_local_backend(self):
        """Test creating local storage backend"""
        backend = create_storage_backend("local")
        assert backend.backend_type == "local"
        assert isinstance(backend, LocalStorageBackend)
    
    def test_create_storage_service(self):
        """Test creating storage service"""
        service = create_storage_service(backend_type="local")
        assert isinstance(service, StorageService)
        assert service.backend_type == "local"
    
    def test_invalid_backend_type(self):
        """Test creating backend with invalid type"""
        with pytest.raises(ValueError):
            create_storage_backend("invalid")


@pytest.mark.asyncio
class TestStorageIntegration:
    """Integration tests for generic storage operations"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_complete_file_workflow(self, temp_dir):
        """Test complete file upload, retrieve, and delete workflow"""
        # Setup service
        backend = LocalStorageBackend(base_path=temp_dir, base_url="/test")
        service = StorageService(backend)
        
        # Create test file content
        content = b"Test document content for storage"
        storage_key = "documents/test-doc.txt"
        content_type = "text/plain"
        metadata = {"user_id": "123", "type": "document"}
        
        # 1. Upload file
        file_url = await service.upload_content(content, storage_key, content_type, metadata)
        assert file_url is not None
        assert storage_key in file_url
        
        # 2. Check file exists
        assert await service.file_exists(storage_key)
        
        # 3. Download file content
        downloaded_content = await service.download_file(storage_key)
        assert downloaded_content == content
        
        # 4. Get file URL
        url = await service.get_file_url(storage_key)
        assert url == file_url
        
        # 5. Get file info
        info = await service.get_file_info(storage_key)
        assert info is not None
        assert info['size'] == len(content)
        
        # 6. Delete file
        success = await service.delete_file(storage_key)
        assert success
        
        # 7. Verify file is deleted
        assert not await service.file_exists(storage_key)