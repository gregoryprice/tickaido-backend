#!/usr/bin/env python3
"""
Integration Tests for Enhanced File Serving
Tests the complete file serving workflow with new URL structure according to PRP
"""

import pytest
import tempfile
import uuid
from io import BytesIO
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.file import File as FileModel, FileStatus, FileType
from app.models.user import User
from app.models.organization import Organization


class TestFileServingIntegration:
    """Integration tests for enhanced file serving"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock user fixture"""
        user = MagicMock()
        user.id = uuid.uuid4()
        user.organization_id = uuid.uuid4()
        user.email = "test@example.com"
        return user
    
    @pytest.fixture
    def mock_file_image(self):
        """Mock image file fixture"""
        file_obj = MagicMock()
        file_obj.id = uuid.uuid4()
        file_obj.filename = "test-image.jpg"
        file_obj.mime_type = "image/jpeg"
        file_obj.file_type = FileType.IMAGE
        file_obj.status = FileStatus.PROCESSED
        file_obj.file_size = 1024
        file_obj.organization_id = uuid.uuid4()
        file_obj.record_download = MagicMock()
        return file_obj
    
    @pytest.fixture
    def mock_file_pdf(self):
        """Mock PDF file fixture"""
        file_obj = MagicMock()
        file_obj.id = uuid.uuid4()
        file_obj.filename = "document.pdf"
        file_obj.mime_type = "application/pdf"
        file_obj.file_type = FileType.DOCUMENT
        file_obj.status = FileStatus.PROCESSED
        file_obj.file_size = 2048
        file_obj.organization_id = uuid.uuid4()
        file_obj.record_download = MagicMock()
        return file_obj

    @patch('app.api.v1.files.get_current_user')
    @patch('app.api.v1.files.get_db_session')
    @patch('app.api.v1.files.FileService')
    def test_image_inline_rendering(self, mock_file_service_class, mock_db, mock_auth, client, mock_user, mock_file_image):
        """Test images render inline in browser"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db.return_value = AsyncMock()
        
        mock_file_service = AsyncMock()
        mock_file_service_class.return_value = mock_file_service
        mock_file_service.get_file.return_value = mock_file_image
        mock_file_service.get_file_content.return_value = b"fake image content"
        
        # Set matching organization
        mock_file_image.organization_id = mock_user.organization_id
        
        # Test new endpoint
        response = client.get(f"/api/v1/files/{mock_file_image.id}/storage/{mock_file_image.filename}")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert "inline" in response.headers["content-disposition"]
        assert mock_file_image.filename in response.headers["content-disposition"]

    @patch('app.api.v1.files.get_current_user')
    @patch('app.api.v1.files.get_db_session')
    @patch('app.api.v1.files.FileService')
    def test_pdf_inline_viewing(self, mock_file_service_class, mock_db, mock_auth, client, mock_user, mock_file_pdf):
        """Test PDFs open inline in browser"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db.return_value = AsyncMock()
        
        mock_file_service = AsyncMock()
        mock_file_service_class.return_value = mock_file_service
        mock_file_service.get_file.return_value = mock_file_pdf
        mock_file_service.get_file_content.return_value = b"fake pdf content"
        
        # Set matching organization
        mock_file_pdf.organization_id = mock_user.organization_id
        
        # Test new endpoint
        response = client.get(f"/api/v1/files/{mock_file_pdf.id}/storage/{mock_file_pdf.filename}")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "inline" in response.headers["content-disposition"]
        assert "document.pdf" in response.headers["content-disposition"]

    @patch('app.api.v1.files.get_current_user')
    @patch('app.api.v1.files.get_db_session')  
    @patch('app.api.v1.files.FileService')
    def test_download_files_behavior(self, mock_file_service_class, mock_db, mock_auth, client, mock_user):
        """Test non-viewable files trigger downloads"""
        # Setup mock for zip file
        mock_file_zip = MagicMock()
        mock_file_zip.id = uuid.uuid4()
        mock_file_zip.filename = "archive.zip"
        mock_file_zip.mime_type = "application/zip"
        mock_file_zip.file_type = FileType.ARCHIVE
        mock_file_zip.status = FileStatus.PROCESSED
        mock_file_zip.file_size = 4096
        mock_file_zip.organization_id = mock_user.organization_id
        mock_file_zip.record_download = MagicMock()
        
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db.return_value = AsyncMock()
        
        mock_file_service = AsyncMock()
        mock_file_service_class.return_value = mock_file_service
        mock_file_service.get_file.return_value = mock_file_zip
        mock_file_service.get_file_content.return_value = b"fake zip content"
        
        # Test new endpoint
        response = client.get(f"/api/v1/files/{mock_file_zip.id}/storage/{mock_file_zip.filename}")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers["content-disposition"]
        assert "archive.zip" in response.headers["content-disposition"]

    @patch('app.api.v1.files.get_current_user')
    @patch('app.api.v1.files.get_db_session')
    @patch('app.api.v1.files.FileService')
    def test_backward_compatibility(self, mock_file_service_class, mock_db, mock_auth, client, mock_user, mock_file_image):
        """Test old /content endpoint still works"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db.return_value = AsyncMock()
        
        mock_file_service = AsyncMock()
        mock_file_service_class.return_value = mock_file_service
        mock_file_service.get_file.return_value = mock_file_image
        mock_file_service.get_file_content.return_value = b"fake image content"
        
        # Set matching organization
        mock_file_image.organization_id = mock_user.organization_id
        
        # Test old endpoint still works
        response = client.get(f"/api/v1/files/{mock_file_image.id}/content")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        # Old endpoint should still force attachment (legacy behavior)
        assert "attachment" in response.headers["content-disposition"]

    def test_security_filename_mismatch(self, client):
        """Test filename parameter must match actual file"""
        file_id = uuid.uuid4()
        wrong_filename = "wrong-file.jpg"
        
        with patch('app.api.v1.files.get_current_user') as mock_auth, \
             patch('app.api.v1.files.get_db_session') as mock_db, \
             patch('app.api.v1.files.FileService') as mock_file_service_class:
            
            # Setup mocks
            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user.organization_id = uuid.uuid4()
            mock_auth.return_value = mock_user
            mock_db.return_value = AsyncMock()
            
            # Mock file with different filename
            mock_file = MagicMock()
            mock_file.id = file_id
            mock_file.filename = "correct-file.jpg"  # Different from requested filename
            mock_file.organization_id = mock_user.organization_id
            
            mock_file_service = AsyncMock()
            mock_file_service_class.return_value = mock_file_service
            mock_file_service.get_file.return_value = mock_file
            
            # Test should return 404 for filename mismatch
            response = client.get(f"/api/v1/files/{file_id}/storage/{wrong_filename}")
            assert response.status_code == 404

    def test_security_path_traversal_protection(self, client):
        """Test path traversal protection"""
        file_id = uuid.uuid4()
        malicious_filenames = [
            "../../../etc/passwd",
            "..\\\\..\\\\system32\\\\config",
            "test/../secret.txt"
        ]
        
        with patch('app.api.v1.files.get_current_user') as mock_auth, \
             patch('app.api.v1.files.get_db_session') as mock_db:
            
            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_auth.return_value = mock_user
            mock_db.return_value = AsyncMock()
            
            for malicious_filename in malicious_filenames:
                response = client.get(f"/api/v1/files/{file_id}/storage/{malicious_filename}")
                assert response.status_code == 400, f"Should reject malicious filename: {malicious_filename}"


class TestUploadResponseUrlFormat:
    """Test upload endpoint returns new URL format"""
    
    @patch('app.api.v1.files.get_current_user')
    @patch('app.api.v1.files.get_db_session')
    @patch('app.api.v1.files.FileService')
    @patch('app.tasks.file_tasks.process_file_upload.delay')
    def test_upload_response_url_format(self, mock_celery_task, mock_file_service_class, mock_db, mock_auth):
        """Test POST /upload returns new URL format"""
        client = TestClient(app)
        
        # Setup mocks
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.organization_id = uuid.uuid4()
        mock_auth.return_value = mock_user
        mock_db.return_value = AsyncMock()
        
        # Mock uploaded file object
        mock_file_obj = MagicMock()
        mock_file_obj.id = uuid.uuid4()
        mock_file_obj.filename = "uploaded-image.jpg"
        mock_file_obj.mime_type = "image/jpeg"
        mock_file_obj.file_type = FileType.IMAGE
        mock_file_obj.status = FileStatus.UPLOADED
        mock_file_obj.file_size = 1024
        mock_file_obj.is_text_file = False
        mock_file_obj.is_image_file = True
        mock_file_obj.is_media_file = False
        
        mock_file_service = AsyncMock()
        mock_file_service_class.return_value = mock_file_service
        mock_file_service.create_file_record.return_value = mock_file_obj
        
        # Mock Celery task
        mock_task_result = MagicMock()
        mock_task_result.id = "task-123"
        mock_celery_task.return_value = mock_task_result
        
        # Test file upload
        test_file_content = b"fake image content"
        response = client.post(
            "/api/v1/files/upload",
            files={"file": ("uploaded-image.jpg", BytesIO(test_file_content), "image/jpeg")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify URL format includes /storage/{filename}
        expected_path = f"/storage/{mock_file_obj.filename}"
        assert expected_path in data["url"], f"URL should include storage path: {data['url']}"
        
        # Verify URL is fully qualified
        assert data["url"].startswith("http"), f"URL should be fully qualified: {data['url']}"