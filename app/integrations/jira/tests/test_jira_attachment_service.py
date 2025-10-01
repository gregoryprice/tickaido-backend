#!/usr/bin/env python3
"""
Tests for JIRA Attachment Service
Validates attachment upload functionality, error handling, and edge cases
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.jira.jira_attachment_service import (
    AttachmentResult,
    AttachmentSummary,
    JiraAttachmentService,
)
from app.integrations.jira.jira_integration import JiraIntegration
from app.models.file import File, FileStatus


class TestJiraAttachmentService:
    """Test the JIRA attachment service functionality"""
    
    @pytest.fixture
    def attachment_service(self):
        """Create a JiraAttachmentService instance"""
        return JiraAttachmentService()
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_jira(self):
        """Mock JIRA integration instance"""
        return AsyncMock(spec=JiraIntegration)
    
    @pytest.fixture
    def mock_file(self):
        """Mock file object"""
        file_id = uuid4()
        file_obj = MagicMock(spec=File)
        file_obj.id = file_id
        file_obj.filename = "test_document.pdf"
        file_obj.organization_id = uuid4()
        file_obj.status = FileStatus.PROCESSED
        file_obj.file_size = 1024
        return file_obj
    
    @pytest.mark.asyncio
    async def test_upload_single_attachment_success(self, attachment_service, mock_db, mock_jira, mock_file):
        """Test successful single file upload to JIRA"""
        file_id = mock_file.id
        user_id = uuid4()
        organization_id = mock_file.organization_id
        issue_key = "TEST-123"
        
        # Mock file service methods
        with patch.object(attachment_service.file_service, 'get_file', return_value=mock_file), \
             patch.object(attachment_service.file_service, 'get_file_content_for_external_upload', 
                         return_value=b"mock file content"):
            
            # Mock JIRA attachment response
            mock_jira.add_attachment.return_value = [
                {
                    "id": "10001",
                    "filename": "test_document.pdf",
                    "size": 1024
                }
            ]
            
            result = await attachment_service.upload_single_attachment(
                db=mock_db,
                jira=mock_jira,
                issue_key=issue_key,
                file_id=file_id,
                user_id=user_id,
                organization_id=organization_id
            )
            
            assert result.success is True
            assert result.file_id == file_id
            assert result.filename == "test_document.pdf"
            assert result.jira_attachment_id == "10001"
            assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_upload_multiple_attachments_success(self, attachment_service, mock_db, mock_jira):
        """Test successful multiple file uploads"""
        # Create mock files
        file_ids = [uuid4(), uuid4(), uuid4()]
        user_id = uuid4()
        organization_id = uuid4()
        issue_key = "TEST-456"
        
        mock_files = []
        for i, file_id in enumerate(file_ids):
            mock_file = MagicMock(spec=File)
            mock_file.id = file_id
            mock_file.filename = f"document_{i}.pdf"
            mock_file.organization_id = organization_id
            mock_file.status = FileStatus.UPLOADED
            mock_file.file_size = 1024 * (i + 1)
            mock_files.append(mock_file)
        
        # Mock file service to return appropriate file for each ID
        async def mock_get_file(db, fid):
            for mock_file in mock_files:
                if mock_file.id == fid:
                    return mock_file
            return None
        
        with patch.object(attachment_service.file_service, 'get_file', side_effect=mock_get_file), \
             patch.object(attachment_service.file_service, 'get_file_content_for_external_upload', 
                         return_value=b"mock file content"):
            
            # Mock JIRA responses - all successful
            mock_jira.add_attachment.side_effect = [
                [{"id": f"1000{i}", "filename": f"document_{i}.pdf", "size": 1024 * (i + 1)}]
                for i in range(len(file_ids))
            ]
            
            summary = await attachment_service.upload_ticket_attachments(
                db=mock_db,
                jira=mock_jira,
                issue_key=issue_key,
                file_ids=file_ids,
                user_id=user_id,
                organization_id=organization_id
            )
            
            assert summary.total_files == 3
            assert summary.successful_uploads == 3
            assert summary.failed_uploads == 0
            
            # Check individual results
            for i, result in enumerate(summary.results):
                assert result.success is True
                assert result.filename == f"document_{i}.pdf"
                assert result.jira_attachment_id == f"1000{i}"
    
    @pytest.mark.asyncio
    async def test_file_not_found_handling(self, attachment_service, mock_db, mock_jira):
        """Test graceful handling when file doesn't exist"""
        file_id = uuid4()
        user_id = uuid4()
        organization_id = uuid4()
        issue_key = "TEST-789"
        
        # Mock file service to return None (file not found)
        with patch.object(attachment_service.file_service, 'get_file', return_value=None):
            
            result = await attachment_service.upload_single_attachment(
                db=mock_db,
                jira=mock_jira,
                issue_key=issue_key,
                file_id=file_id,
                user_id=user_id,
                organization_id=organization_id
            )
            
            assert result.success is False
            assert result.file_id == file_id
            assert "File not found" in result.error_message
    
    @pytest.mark.asyncio
    async def test_organization_boundary_validation(self, attachment_service, mock_db, mock_jira, mock_file):
        """Test file access across organization boundaries"""
        file_id = mock_file.id
        user_id = uuid4()
        different_org_id = uuid4()  # Different from mock_file.organization_id
        issue_key = "TEST-101"
        
        with patch.object(attachment_service.file_service, 'get_file', return_value=mock_file), \
             patch.object(attachment_service.file_service, 'get_file_content_for_external_upload', 
                         side_effect=PermissionError("File belongs to different organization")):
            
            result = await attachment_service.upload_single_attachment(
                db=mock_db,
                jira=mock_jira,
                issue_key=issue_key,
                file_id=file_id,
                user_id=user_id,
                organization_id=different_org_id
            )
            
            assert result.success is False
            assert "Access denied" in result.error_message
    
    @pytest.mark.asyncio
    async def test_deleted_file_handling(self, attachment_service, mock_db, mock_jira, mock_file):
        """Test handling of files with deleted status"""
        file_id = mock_file.id
        user_id = uuid4()
        organization_id = mock_file.organization_id
        issue_key = "TEST-202"
        
        # Set file status to deleted
        mock_file.status = FileStatus.DELETED
        
        with patch.object(attachment_service.file_service, 'get_file', return_value=mock_file), \
             patch.object(attachment_service.file_service, 'get_file_content_for_external_upload', 
                         side_effect=ValueError("File has been deleted")):
            
            result = await attachment_service.upload_single_attachment(
                db=mock_db,
                jira=mock_jira,
                issue_key=issue_key,
                file_id=file_id,
                user_id=user_id,
                organization_id=organization_id
            )
            
            assert result.success is False
            assert "File has been deleted" in result.error_message
    
    @pytest.mark.asyncio
    async def test_jira_api_authentication_failure(self, attachment_service, mock_db, mock_jira, mock_file):
        """Test JIRA API auth failure handling"""
        file_id = mock_file.id
        user_id = uuid4()
        organization_id = mock_file.organization_id
        issue_key = "TEST-303"
        
        with patch.object(attachment_service.file_service, 'get_file', return_value=mock_file), \
             patch.object(attachment_service.file_service, 'get_file_content_for_external_upload', 
                         return_value=b"mock file content"):
            
            # Mock JIRA to raise authentication error
            mock_jira.add_attachment.side_effect = ValueError("Permission denied - unable to add attachments to this JIRA issue")
            
            result = await attachment_service.upload_single_attachment(
                db=mock_db,
                jira=mock_jira,
                issue_key=issue_key,
                file_id=file_id,
                user_id=user_id,
                organization_id=organization_id
            )
            
            assert result.success is False
            assert "Permission denied" in result.error_message
    
    @pytest.mark.asyncio
    async def test_jira_file_size_limit_exceeded(self, attachment_service, mock_db, mock_jira, mock_file):
        """Test handling of files exceeding JIRA limits"""
        file_id = mock_file.id
        user_id = uuid4()
        organization_id = mock_file.organization_id
        issue_key = "TEST-404"
        
        with patch.object(attachment_service.file_service, 'get_file', return_value=mock_file), \
             patch.object(attachment_service.file_service, 'get_file_content_for_external_upload', 
                         return_value=b"mock file content"):
            
            # Mock JIRA to raise file size error
            mock_jira.add_attachment.side_effect = ValueError("File size (15.2MB) exceeds JIRA attachment limit (10MB)")
            
            result = await attachment_service.upload_single_attachment(
                db=mock_db,
                jira=mock_jira,
                issue_key=issue_key,
                file_id=file_id,
                user_id=user_id,
                organization_id=organization_id
            )
            
            assert result.success is False
            assert "exceeds JIRA attachment limit" in result.error_message
    
    @pytest.mark.asyncio
    async def test_partial_success_scenario(self, attachment_service, mock_db, mock_jira):
        """Test mixed success/failure for multiple files"""
        file_ids = [uuid4(), uuid4(), uuid4()]
        user_id = uuid4()
        organization_id = uuid4()
        issue_key = "TEST-505"
        
        # Create mock files
        mock_files = []
        for i, file_id in enumerate(file_ids):
            mock_file = MagicMock(spec=File)
            mock_file.id = file_id
            mock_file.filename = f"document_{i}.pdf"
            mock_file.organization_id = organization_id
            mock_file.status = FileStatus.UPLOADED
            mock_files.append(mock_file)
        
        # Mock file service
        async def mock_get_file(db, fid):
            for mock_file in mock_files:
                if mock_file.id == fid:
                    return mock_file
            return None
        
        # Mock mixed results: first succeeds, second fails, third succeeds
        jira_responses = [
            [{"id": "10001", "filename": "document_0.pdf"}],  # Success
            ValueError("File type not supported"),  # Failure  
            [{"id": "10003", "filename": "document_2.pdf"}]  # Success
        ]
        
        with patch.object(attachment_service.file_service, 'get_file', side_effect=mock_get_file), \
             patch.object(attachment_service.file_service, 'get_file_content_for_external_upload', 
                         return_value=b"mock file content"):
            
            mock_jira.add_attachment.side_effect = jira_responses
            
            summary = await attachment_service.upload_ticket_attachments(
                db=mock_db,
                jira=mock_jira,
                issue_key=issue_key,
                file_ids=file_ids,
                user_id=user_id,
                organization_id=organization_id
            )
            
            assert summary.total_files == 3
            assert summary.successful_uploads == 2
            assert summary.failed_uploads == 1
            
            # Check specific results
            assert summary.results[0].success is True
            assert summary.results[1].success is False
            assert summary.results[2].success is True
            assert "not supported" in summary.results[1].error_message
    
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, attachment_service, mock_db, mock_jira, mock_file):
        """Test network timeout with retry logic (simulated)"""
        file_id = mock_file.id
        user_id = uuid4()
        organization_id = mock_file.organization_id
        issue_key = "TEST-606"
        
        with patch.object(attachment_service.file_service, 'get_file', return_value=mock_file), \
             patch.object(attachment_service.file_service, 'get_file_content_for_external_upload', 
                         return_value=b"mock file content"):
            
            # Mock JIRA to raise timeout error
            mock_jira.add_attachment.side_effect = ValueError("Upload timeout after 3 attempts")
            
            result = await attachment_service.upload_single_attachment(
                db=mock_db,
                jira=mock_jira,
                issue_key=issue_key,
                file_id=file_id,
                user_id=user_id,
                organization_id=organization_id
            )
            
            assert result.success is False
            assert "timeout" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_corrupted_file_content(self, attachment_service, mock_db, mock_jira, mock_file):
        """Test handling of corrupted file data"""
        file_id = mock_file.id
        user_id = uuid4()
        organization_id = mock_file.organization_id
        issue_key = "TEST-707"
        
        with patch.object(attachment_service.file_service, 'get_file', return_value=mock_file), \
             patch.object(attachment_service.file_service, 'get_file_content_for_external_upload', 
                         return_value=None):  # Simulate content retrieval failure
            
            result = await attachment_service.upload_single_attachment(
                db=mock_db,
                jira=mock_jira,
                issue_key=issue_key,
                file_id=file_id,
                user_id=user_id,
                organization_id=organization_id
            )
            
            assert result.success is False
            assert "File content not available" in result.error_message
    
    def test_attachment_result_to_dict(self):
        """Test AttachmentResult to_dict conversion"""
        file_id = uuid4()
        result = AttachmentResult(
            file_id=file_id,
            filename="test.pdf",
            success=True,
            jira_attachment_id="10001",
            error_message=None
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["file_id"] == str(file_id)
        assert result_dict["filename"] == "test.pdf"
        assert result_dict["upload_status"] == "success"
        assert result_dict["jira_attachment_id"] == "10001"
        assert result_dict["error_message"] is None
    
    def test_attachment_summary_to_dict(self):
        """Test AttachmentSummary to_dict conversion"""
        results = [
            AttachmentResult(uuid4(), "file1.pdf", True, "10001"),
            AttachmentResult(uuid4(), "file2.pdf", False, None, "Error"),
            AttachmentResult(uuid4(), "file3.pdf", True, "10003")
        ]
        
        summary = AttachmentSummary(results)
        summary_dict = summary.to_dict()
        
        assert summary_dict["total_files"] == 3
        assert summary_dict["successful_uploads"] == 2
        assert summary_dict["failed_uploads"] == 1
    
    @pytest.mark.asyncio
    async def test_empty_file_list(self, attachment_service, mock_db, mock_jira):
        """Test handling of empty file list"""
        user_id = uuid4()
        organization_id = uuid4()
        issue_key = "TEST-808"
        
        summary = await attachment_service.upload_ticket_attachments(
            db=mock_db,
            jira=mock_jira,
            issue_key=issue_key,
            file_ids=[],
            user_id=user_id,
            organization_id=organization_id
        )
        
        assert summary.total_files == 0
        assert summary.successful_uploads == 0
        assert summary.failed_uploads == 0
        assert len(summary.results) == 0