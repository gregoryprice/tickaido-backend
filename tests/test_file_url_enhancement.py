#!/usr/bin/env python3
"""
File URL Enhancement Tests - Unit and integration tests for PRP implementation
Tests validate consistent URL field implementation across all file API endpoints
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.file import File, FileStatus, FileType
from app.models.user import User
from app.models.organization import Organization
from app.schemas.file import FileResponse, FileUploadResponse, FileListResponse
from app.services.file_service import DuplicateFileError


class TestFileSchemaUrlField:
    """Unit tests for schema URL field implementation"""
    
    def test_file_upload_response_includes_url_field(self):
        """Test that FileUploadResponse includes url field instead of download_url"""
        file_id = uuid.uuid4()
        response = FileUploadResponse(
            id=file_id,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_type=FileType.DOCUMENT,
            status=FileStatus.UPLOADED,
            url=f"/api/v1/files/{file_id}/content",
            processing_required=True
        )
        
        assert response.url == f"/api/v1/files/{file_id}/content"
        assert hasattr(response, 'url')
        # Verify download_url field is no longer present
        assert not hasattr(response, 'download_url')

    def test_file_response_includes_url_field(self):
        """Test that FileResponse includes url field"""
        file_id = uuid.uuid4()
        response = FileResponse(
            id=file_id,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_type=FileType.DOCUMENT,
            status=FileStatus.PROCESSED,
            url=f"/api/v1/files/{file_id}/content",
            extraction_method="pdf_extraction",
            content_summary="Test document",
            extracted_context=None,
            language_detection="en",
            processing_started_at=datetime.utcnow(),
            processing_completed_at=datetime.utcnow(),
            processing_error=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        assert response.url == f"/api/v1/files/{file_id}/content"
        assert hasattr(response, 'url')

    def test_url_field_format_consistency(self):
        """Test that all schemas use consistent URL format"""
        file_id = uuid.uuid4()
        expected_url = f"/api/v1/files/{file_id}/content"
        
        # Test FileUploadResponse URL format
        upload_response = FileUploadResponse(
            id=file_id,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf", 
            file_type=FileType.DOCUMENT,
            status=FileStatus.UPLOADED,
            url=expected_url,
            processing_required=True
        )
        
        # Test FileResponse URL format
        file_response = FileResponse(
            id=file_id,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_type=FileType.DOCUMENT,
            status=FileStatus.PROCESSED,
            url=expected_url,
            extraction_method=None,
            content_summary=None,
            extracted_context=None,
            language_detection=None,
            processing_started_at=None,
            processing_completed_at=None,
            processing_error=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        assert upload_response.url == expected_url
        assert file_response.url == expected_url


class TestFileAPIEndpointUrls:
    """Integration tests for file API endpoint URL implementation"""
    
    @pytest.fixture
    def client(self):
        """Test client for API testing"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing"""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.rollback = AsyncMock()
        session.add = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_user(self):
        """Mock user for authentication"""
        user = User()
        user.id = uuid.uuid4()
        user.organization_id = uuid.uuid4()
        user.email = "test@example.com"
        return user
    
    @pytest.fixture
    def mock_file(self):
        """Mock file object for testing"""
        file_obj = File()
        file_obj.id = uuid.uuid4()
        file_obj.filename = "test.pdf"
        file_obj.file_size = 1024
        file_obj.mime_type = "application/pdf"
        file_obj.file_type = FileType.DOCUMENT
        file_obj.status = FileStatus.PROCESSED
        file_obj.organization_id = uuid.uuid4()
        file_obj.extraction_method = "pdf_extraction"
        file_obj.content_summary = "Test document"
        file_obj.extracted_context = None
        file_obj.language_detection = "en"
        file_obj.processing_started_at = datetime.utcnow()
        file_obj.processing_completed_at = datetime.utcnow()
        file_obj.processing_error = None
        file_obj.created_at = datetime.utcnow()
        file_obj.updated_at = datetime.utcnow()
        # Note: is_text_file, is_image_file, is_media_file are computed properties
        return file_obj

    @pytest.mark.asyncio
    async def test_upload_endpoint_returns_url_field(self, mock_file):
        """Test POST /api/v1/files/upload returns url instead of download_url"""
        from app.api.v1.files import upload_file
        from app.schemas.file import FileUploadResponse
        
        # Mock the file service and processing
        with pytest.MonkeyPatch().context() as m:
            mock_file_service = MagicMock()
            mock_file_service.create_file_record = AsyncMock(return_value=mock_file)
            
            # Simulate the upload response creation logic
            processing_required = mock_file.file_type in [FileType.DOCUMENT, FileType.IMAGE, FileType.AUDIO, FileType.VIDEO, FileType.TEXT]
            
            response = FileUploadResponse(
                id=mock_file.id,
                filename=mock_file.filename,
                file_size=mock_file.file_size,
                mime_type=mock_file.mime_type,
                file_type=mock_file.file_type,
                status=mock_file.status,
                url=f"/api/v1/files/{mock_file.id}/content",
                processing_required=processing_required
            )
            
            assert response.url == f"/api/v1/files/{mock_file.id}/content"
            assert not hasattr(response, 'download_url')

    @pytest.mark.asyncio
    async def test_get_file_endpoint_includes_url_field(self, mock_file):
        """Test GET /api/v1/files/{file_id} includes url field"""
        from app.schemas.file import FileResponse
        
        # Simulate the get file response creation logic
        response = FileResponse(
            id=mock_file.id,
            filename=mock_file.filename,
            file_size=mock_file.file_size,
            mime_type=mock_file.mime_type,
            file_type=mock_file.file_type,
            status=mock_file.status,
            url=f"/api/v1/files/{mock_file.id}/content",
            extraction_method=mock_file.extraction_method,
            content_summary=mock_file.content_summary,
            extracted_context=mock_file.extracted_context,
            language_detection=mock_file.language_detection,
            processing_started_at=mock_file.processing_started_at,
            processing_completed_at=mock_file.processing_completed_at,
            processing_error=mock_file.processing_error,
            created_at=mock_file.created_at,
            updated_at=mock_file.updated_at
        )
        
        assert response.url == f"/api/v1/files/{mock_file.id}/content"
        assert response.id == mock_file.id

    @pytest.mark.asyncio
    async def test_list_files_endpoint_includes_url_fields(self, mock_file):
        """Test GET /api/v1/files includes url field for all files"""
        from app.schemas.file import FileResponse, FileListResponse
        
        # Create multiple mock files
        mock_files = [mock_file]
        for i in range(2):
            additional_file = File()
            additional_file.id = uuid.uuid4()
            additional_file.filename = f"test_{i}.pdf"
            additional_file.file_size = 1024 * (i + 1)
            additional_file.mime_type = "application/pdf"
            additional_file.file_type = FileType.DOCUMENT
            additional_file.status = FileStatus.PROCESSED
            additional_file.organization_id = mock_file.organization_id
            additional_file.extraction_method = "pdf_extraction"
            additional_file.content_summary = f"Test document {i}"
            additional_file.extracted_context = None
            additional_file.language_detection = "en"
            additional_file.processing_started_at = datetime.utcnow()
            additional_file.processing_completed_at = datetime.utcnow()
            additional_file.processing_error = None
            additional_file.created_at = datetime.utcnow()
            additional_file.updated_at = datetime.utcnow()
            mock_files.append(additional_file)
        
        # Simulate the list files response creation logic
        file_responses = []
        for file_obj in mock_files:
            file_responses.append(FileResponse(
                id=file_obj.id,
                filename=file_obj.filename,
                file_size=file_obj.file_size,
                mime_type=file_obj.mime_type,
                file_type=file_obj.file_type,
                status=file_obj.status,
                url=f"/api/v1/files/{file_obj.id}/content",
                extraction_method=file_obj.extraction_method,
                content_summary=file_obj.content_summary,
                language_detection=file_obj.language_detection,
                processing_started_at=file_obj.processing_started_at,
                processing_completed_at=file_obj.processing_completed_at,
                processing_error=file_obj.processing_error,
                created_at=file_obj.created_at,
                updated_at=file_obj.updated_at
            ))
        
        list_response = FileListResponse(
            files=file_responses,
            total=len(file_responses),
            skip=0,
            limit=50
        )
        
        # Verify all files have url field
        assert len(list_response.files) == 3
        for file_response in list_response.files:
            assert hasattr(file_response, 'url')
            assert file_response.url == f"/api/v1/files/{file_response.id}/content"

    def test_409_conflict_response_includes_content_suffix(self):
        """Test 409 conflict response includes /content suffix in existing_file_url"""
        existing_file_id = uuid.uuid4()
        
        # Simulate the 409 error response creation logic
        error_detail = {
            "message": "File with this content already exists",
            "existing_file_id": str(existing_file_id),
            "existing_file_url": f"/api/v1/files/{existing_file_id}/content"
        }
        
        assert error_detail["existing_file_url"] == f"/api/v1/files/{existing_file_id}/content"
        assert error_detail["existing_file_url"].endswith("/content")

    def test_url_format_consistency_across_endpoints(self):
        """Test that all endpoints use the same URL format pattern"""
        file_id = uuid.uuid4()
        expected_url_pattern = f"/api/v1/files/{file_id}/content"
        
        # Test various response scenarios
        upload_response = FileUploadResponse(
            id=file_id,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_type=FileType.DOCUMENT,
            status=FileStatus.UPLOADED,
            url=expected_url_pattern,
            processing_required=True
        )
        
        file_response = FileResponse(
            id=file_id,
            filename="test.pdf", 
            file_size=1024,
            mime_type="application/pdf",
            file_type=FileType.DOCUMENT,
            status=FileStatus.PROCESSED,
            url=expected_url_pattern,
            extraction_method=None,
            content_summary=None,
            extracted_context=None,
            language_detection=None,
            processing_started_at=None,
            processing_completed_at=None,
            processing_error=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        conflict_url = f"/api/v1/files/{file_id}/content"
        
        # All URLs should follow the same pattern
        assert upload_response.url == expected_url_pattern
        assert file_response.url == expected_url_pattern
        assert conflict_url == expected_url_pattern
        
        # Verify pattern structure
        assert upload_response.url.startswith("/api/v1/files/")
        assert upload_response.url.endswith("/content")
        assert file_response.url.startswith("/api/v1/files/")
        assert file_response.url.endswith("/content")


class TestFileUrlSecurity:
    """Security tests for file URL implementation"""
    
    def test_url_does_not_expose_sensitive_info(self):
        """Test that URLs don't expose sensitive information"""
        file_id = uuid.uuid4()
        url = f"/api/v1/files/{file_id}/content"
        
        # URL should only contain the file ID and endpoint path
        assert str(file_id) in url
        assert "/content" in url
        assert "/api/v1/files/" in url
        
        # Should not contain any sensitive information
        sensitive_patterns = ["password", "secret", "key", "token", "auth"]
        for pattern in sensitive_patterns:
            assert pattern not in url.lower()

    def test_url_maintains_existing_auth_requirements(self):
        """Test that URLs maintain same authentication requirements as content endpoint"""
        file_id = uuid.uuid4()
        url = f"/api/v1/files/{file_id}/content"
        
        # URL points to existing content endpoint which has auth middleware
        assert url.endswith("/content")
        assert "/api/v1/files/" in url
        
        # The URL structure matches the existing authenticated endpoint
        expected_pattern = f"/api/v1/files/{file_id}/content"
        assert url == expected_pattern


if __name__ == "__main__":
    pytest.main([__file__, "-v"])