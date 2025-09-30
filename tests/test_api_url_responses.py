#!/usr/bin/env python3
"""
API URL Response Validation Tests
Tests that all API endpoints return correct URL formats according to PRP specifications
"""

import pytest
import uuid
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from io import BytesIO

from app.main import app
from app.models.file import File as FileModel, FileStatus, FileType


class TestAPIUrlResponses:
    """Test all API endpoints return correct URL formats"""
    
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
    def mock_file(self):
        """Mock file fixture"""
        file_obj = MagicMock()
        file_obj.id = uuid.uuid4()
        file_obj.filename = "test-document.pdf"
        file_obj.mime_type = "application/pdf"
        file_obj.file_type = FileType.DOCUMENT
        file_obj.status = FileStatus.PROCESSED
        file_obj.file_size = 2048
        file_obj.organization_id = uuid.uuid4()
        file_obj.extraction_method = "vision_ocr"
        file_obj.content_summary = "Test document summary"
        file_obj.extracted_context = {"text": "sample text"}
        file_obj.language_detection = "en"
        file_obj.processing_started_at = None
        file_obj.processing_completed_at = None
        file_obj.processing_error = None
        file_obj.created_at = "2023-01-01T00:00:00Z"
        file_obj.updated_at = "2023-01-01T00:00:00Z"
        file_obj.is_text_file = False
        file_obj.is_image_file = False
        file_obj.is_media_file = False
        return file_obj

    @patch('app.api.v1.files.get_current_user')
    @patch('app.api.v1.files.get_db_session')
    @patch('app.api.v1.files.FileService')
    @patch('app.tasks.file_tasks.process_file_upload.delay')
    def test_upload_response_url_format(self, mock_celery_task, mock_file_service_class, mock_db, mock_auth, client, mock_user, mock_file):
        """Test POST /upload returns new URL format"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db.return_value = AsyncMock()
        
        mock_file_service = AsyncMock()
        mock_file_service_class.return_value = mock_file_service
        mock_file_service.create_file_record.return_value = mock_file
        
        # Mock Celery task
        mock_task_result = MagicMock()
        mock_task_result.id = "task-123"
        mock_celery_task.return_value = mock_task_result
        
        # Test file upload
        test_file_content = b"fake file content"
        response = client.post(
            "/api/v1/files/upload",
            files={"file": ("test-document.pdf", BytesIO(test_file_content), "application/pdf")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify URL format includes /storage/{filename}
        assert "/storage/test-document.pdf" in data["url"]
        
        # Verify URL is fully qualified (starts with http/https)
        assert data["url"].startswith(("http://", "https://"))
        
        # Verify URL structure matches expected pattern
        expected_pattern = f"/api/v1/files/{mock_file.id}/storage/{mock_file.filename}"
        assert expected_pattern in data["url"]

    @patch('app.api.v1.files.get_current_user')
    @patch('app.api.v1.files.get_db_session')
    @patch('app.api.v1.files.FileService')
    def test_get_file_metadata_url_format(self, mock_file_service_class, mock_db, mock_auth, client, mock_user, mock_file):
        """Test GET /{file_id} returns new URL format"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db.return_value = AsyncMock()
        mock_file.organization_id = mock_user.organization_id  # Match organization
        
        mock_file_service = AsyncMock()
        mock_file_service_class.return_value = mock_file_service
        mock_file_service.get_file.return_value = mock_file
        
        # Test get file metadata
        response = client.get(f"/api/v1/files/{mock_file.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify URL format includes /storage/{filename}
        assert "/storage/test-document.pdf" in data["url"]
        
        # Verify URL is fully qualified
        assert data["url"].startswith(("http://", "https://"))
        
        # Verify filename is included in URL
        assert mock_file.filename in data["url"]

    @patch('app.api.v1.files.get_current_user')
    @patch('app.api.v1.files.get_db_session')
    @patch('app.api.v1.files.FileService')
    def test_list_files_url_format(self, mock_file_service_class, mock_db, mock_auth, client, mock_user, mock_file):
        """Test GET /files returns new URL formats"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db.return_value = AsyncMock()
        mock_file.organization_id = mock_user.organization_id  # Match organization
        
        mock_file_service = AsyncMock()
        mock_file_service_class.return_value = mock_file_service
        mock_file_service.get_files_for_organization.return_value = [mock_file]
        
        # Test list files
        response = client.get("/api/v1/files")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "files" in data
        assert len(data["files"]) == 1
        
        file_data = data["files"][0]
        
        # Verify URL format includes /storage/{filename}
        assert "/storage/test-document.pdf" in file_data["url"]
        
        # Verify URL is fully qualified
        assert file_data["url"].startswith(("http://", "https://"))
        
        # Verify filename is included in URL
        assert mock_file.filename in file_data["url"]

    @patch('app.api.v1.files.get_current_user')
    @patch('app.api.v1.files.get_db_session')
    @patch('app.api.v1.files.FileService')
    @patch('app.tasks.file_tasks.process_file_upload.delay')
    def test_url_consistency_across_endpoints(self, mock_celery_task, mock_file_service_class, mock_db, mock_auth, client, mock_user):
        """Test URL format consistency across all endpoints"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db.return_value = AsyncMock()
        
        # Create a specific mock file for this test
        test_file = MagicMock()
        test_file.id = uuid.uuid4()
        test_file.filename = "consistency-test.jpg"
        test_file.mime_type = "image/jpeg"
        test_file.file_type = FileType.IMAGE
        test_file.status = FileStatus.PROCESSED
        test_file.file_size = 1024
        test_file.organization_id = mock_user.organization_id
        test_file.extraction_method = None
        test_file.content_summary = None
        test_file.extracted_context = None
        test_file.language_detection = None
        test_file.processing_started_at = None
        test_file.processing_completed_at = None
        test_file.processing_error = None
        test_file.created_at = "2023-01-01T00:00:00Z"
        test_file.updated_at = "2023-01-01T00:00:00Z"
        test_file.is_text_file = False
        test_file.is_image_file = True
        test_file.is_media_file = False
        
        mock_file_service = AsyncMock()
        mock_file_service_class.return_value = mock_file_service
        mock_file_service.create_file_record.return_value = test_file
        mock_file_service.get_file.return_value = test_file
        mock_file_service.get_files_for_organization.return_value = [test_file]
        
        # Mock Celery task
        mock_task_result = MagicMock()
        mock_task_result.id = "task-123"
        mock_celery_task.return_value = mock_task_result
        
        # 1. Upload file and get URL
        upload_response = client.post(
            "/api/v1/files/upload",
            files={"file": ("consistency-test.jpg", BytesIO(b"test content"), "image/jpeg")}
        )
        assert upload_response.status_code == 200
        upload_url = upload_response.json()["url"]
        
        # 2. Get file metadata and check URL
        metadata_response = client.get(f"/api/v1/files/{test_file.id}")
        assert metadata_response.status_code == 200
        metadata_url = metadata_response.json()["url"]
        
        # 3. List files and check URL
        list_response = client.get("/api/v1/files")
        assert list_response.status_code == 200
        list_url = list_response.json()["files"][0]["url"]
        
        # 4. Verify all URLs are identical and follow new format
        assert upload_url == metadata_url == list_url, "URLs should be consistent across endpoints"
        
        # Verify URL format
        expected_path = f"/storage/{test_file.filename}"
        assert expected_path in upload_url, "URL should include storage path and filename"
        assert upload_url.startswith(("http://", "https://")), "URL should be fully qualified"
        
        # Verify URL structure
        expected_pattern = f"/api/v1/files/{test_file.id}/storage/{test_file.filename}"
        assert expected_pattern in upload_url, "URL should match expected pattern"


class TestUrlValidationEdgeCases:
    """Test URL validation edge cases"""
    
    @patch('app.api.v1.files.get_current_user')
    @patch('app.api.v1.files.get_db_session')
    @patch('app.api.v1.files.FileService')
    def test_special_characters_in_filename(self, mock_file_service_class, mock_db, mock_auth):
        """Test URL construction with special characters in filename"""
        client = TestClient(app)
        
        # Setup mocks
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.organization_id = uuid.uuid4()
        mock_auth.return_value = mock_user
        mock_db.return_value = AsyncMock()
        
        # Create file with special characters (but valid ones)
        special_file = MagicMock()
        special_file.id = uuid.uuid4()
        special_file.filename = "My Document (2023) - Final.pdf"
        special_file.mime_type = "application/pdf"
        special_file.file_type = FileType.DOCUMENT
        special_file.status = FileStatus.PROCESSED
        special_file.organization_id = mock_user.organization_id
        special_file.extraction_method = None
        special_file.content_summary = None
        special_file.extracted_context = None
        special_file.language_detection = None
        special_file.processing_started_at = None
        special_file.processing_completed_at = None
        special_file.processing_error = None
        special_file.created_at = "2023-01-01T00:00:00Z"
        special_file.updated_at = "2023-01-01T00:00:00Z"
        
        mock_file_service = AsyncMock()
        mock_file_service_class.return_value = mock_file_service
        mock_file_service.get_file.return_value = special_file
        
        # Test get file metadata
        response = client.get(f"/api/v1/files/{special_file.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify filename with special characters is preserved in URL
        assert special_file.filename in data["url"]
        assert "/storage/" in data["url"]

    def test_url_helper_function_robustness(self):
        """Test URL helper functions with various inputs"""
        from app.api.v1.files import build_file_url, get_content_disposition
        
        # Test build_file_url with different request configurations
        mock_request = MagicMock()
        mock_request.url.scheme = 'https'
        mock_request.url.netloc = 'api.example.com'
        
        file_id = uuid.uuid4()
        filename = "test-file.pdf"
        
        url = build_file_url(mock_request, file_id, filename)
        
        # Verify URL structure
        assert url.startswith('https://api.example.com')
        assert str(file_id) in url
        assert filename in url
        assert '/storage/' in url
        
        # Test content disposition with various MIME types
        test_cases = [
            ("image/jpeg", "inline"),
            ("application/pdf", "inline"),
            ("text/plain", "inline"),
            ("application/zip", "attachment"),
            ("video/mp4", "attachment")
        ]
        
        for mime_type, expected_disposition in test_cases:
            result = get_content_disposition(mime_type, "test.file")
            assert result.startswith(expected_disposition), f"MIME type {mime_type} should have {expected_disposition} disposition"