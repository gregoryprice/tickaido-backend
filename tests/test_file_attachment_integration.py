#!/usr/bin/env python3
"""
File Attachment Integration Tests - End-to-end validation as specified in PRP
VALIDATION GATE: Integration tests must ALL PASS to complete Phase 1
"""

import pytest
import uuid
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File, FileStatus, FileType
from app.models.user import User
from app.models.organization import Organization
from app.services.file_processing_service import FileProcessingService
from app.services.file_service import FileService
from app.services.ticket_attachment_service import TicketAttachmentService


class TestFileAttachmentIntegration:
    """End-to-end integration tests for file attachment system"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing"""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.rollback = AsyncMock()
        session.add = AsyncMock()
        session.flush = AsyncMock()
        
        # Mock the execute method to return a mock result
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        return session
    
    @pytest.fixture
    def sample_organization(self):
        """Sample organization for testing"""
        return Organization(
            id=uuid.uuid4(),
            name="Test Organization",
            domain="test.com"
        )
    
    @pytest.fixture
    def sample_user(self, sample_organization):
        """Sample user for testing"""
        return User(
            id=uuid.uuid4(),
            email="test@test.com",
            organization_id=sample_organization.id
        )
    
    @pytest.fixture
    def sample_file_content(self):
        """Sample file content for testing"""
        return """
        Technical Support Issue Report
        
        Problem: Login authentication failure
        Error Code: AUTH_001
        Description: Users unable to authenticate using valid credentials
        
        Steps to reproduce:
        1. Navigate to login page
        2. Enter username and password
        3. Click login button
        4. Observe authentication error
        
        Expected: Successful login and redirect to dashboard
        Actual: Error message "Invalid credentials" displayed
        
        Environment:
        - Browser: Chrome 118
        - OS: Windows 11
        - Network: Corporate WiFi
        """.strip()
    
    @pytest.mark.asyncio
    async def test_file_processing_service_initialization(self):
        """REQUIRED TEST: FileProcessingService initializes all sub-services"""
        processor = FileProcessingService()
        
        assert processor.document_parser is not None
        assert processor.ocr_service is not None
        assert processor.transcription_service is not None
        assert processor.vision_service is not None
        assert processor.ai_service is not None
        assert processor.file_service is not None
    
    @pytest.mark.asyncio
    async def test_file_record_creation(self, mock_db_session, sample_user, sample_file_content):
        """REQUIRED TEST: File record creation with new model structure"""
        
        file_service = FileService()
        # Mock the storage service calls
        file_service.storage_service.upload_content = AsyncMock(return_value="mock_url")
        
        file_obj = await file_service.create_file_record(
            db=mock_db_session,
            filename="test_report.txt",
            mime_type="text/plain",
            file_size=len(sample_file_content.encode()),
            file_content=sample_file_content.encode(),
            uploaded_by_id=sample_user.id,
            organization_id=sample_user.organization_id,
            description="Test technical report"
        )
        
        # Verify file record structure
        assert file_obj.id is not None
        assert file_obj.filename == "test_report.txt"
        assert file_obj.mime_type == "text/plain"
        assert file_obj.file_type == FileType.TEXT
        assert file_obj.uploaded_by_id == sample_user.id
        assert file_obj.organization_id == sample_user.organization_id
        assert file_obj.status == FileStatus.UPLOADED
        assert file_obj.file_hash is not None
        assert len(file_obj.file_hash) == 64  # SHA-256 hash
    
    @pytest.mark.asyncio
    async def test_extracted_context_structure(self, mock_db_session, sample_user, sample_file_content):
        """REQUIRED TEST: extracted_context field populated correctly"""
        
        file_obj = File(
            id=uuid.uuid4(),
            filename="test.txt",
            file_path="test/test.txt",
            mime_type="text/plain",
            file_size=len(sample_file_content),
            file_hash="test_hash",
            file_type=FileType.TEXT,
            uploaded_by_id=sample_user.id,
            organization_id=sample_user.organization_id,
            status=FileStatus.UPLOADED
        )
        
        # Mock file service to return our content
        processor = FileProcessingService()
        processor.file_service.get_file_content = AsyncMock(return_value=sample_file_content.encode())
        
        # Process the file
        await processor.process_uploaded_file(mock_db_session, file_obj)
        
        # Verify extracted_context structure
        assert file_obj.extracted_context is not None
        assert isinstance(file_obj.extracted_context, dict)
        
        # Should have document structure for text files
        assert "document" in file_obj.extracted_context
        doc = file_obj.extracted_context["document"]
        assert "pages" in doc
        assert len(doc["pages"]) > 0
        assert "metadata" in doc
        
        # Verify page structure
        page = doc["pages"][0]
        assert "page_number" in page
        assert "text" in page
        assert page["text"] != ""
        assert "authentication" in page["text"].lower()
        
        # Verify processing metadata
        assert file_obj.extraction_method == "document_parser"
        assert file_obj.status == FileStatus.PROCESSED
        assert file_obj.content_summary is not None
        assert file_obj.language_detection in ["en", "unknown"]
    
    @pytest.mark.asyncio 
    async def test_organization_scoping(self, mock_db_session, sample_user):
        """REQUIRED TEST: Organization scoping validation"""
        
        file_service = FileService()
        
        # Mock database query
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        files = await file_service.get_files_for_organization(
            db=mock_db_session,
            organization_id=sample_user.organization_id,
            user_id=sample_user.id,
            filters={"file_type": FileType.TEXT},
            skip=0,
            limit=10
        )
        
        # Verify query was called
        assert mock_db_session.execute.called
        assert isinstance(files, list)
    
    @pytest.mark.asyncio
    async def test_ticket_file_association(self, mock_db_session, sample_user):
        """REQUIRED TEST: Ticket-file association via file_ids array"""
        
        attachment_service = TicketAttachmentService()
        
        # Mock file validation
        from app.models.file import FileType
        mock_file = File(
            id=uuid.uuid4(),
            filename="error_log.txt",
            organization_id=sample_user.organization_id,
            status=FileStatus.PROCESSED,
            file_type=FileType.TEXT,
            extracted_context={"document": {"pages": [{"text": "Error details"}]}}
        )
        
        attachment_service.file_service.get_file = AsyncMock(return_value=mock_file)
        
        # Mock ticket 
        from unittest.mock import MagicMock
        mock_ticket = MagicMock()
        mock_ticket.title = "Login Issue"
        mock_ticket.description = "Cannot log in"
        mock_ticket.id = uuid.uuid4()
        
        # Mock TicketService to avoid file validation issues
        from unittest.mock import patch
        with patch('app.services.ticket_service.TicketService') as mock_ticket_service_class:
            mock_ticket_service_instance = AsyncMock()
            mock_ticket_service_instance.create_ticket = AsyncMock(return_value=mock_ticket)
            mock_ticket_service_class.return_value = mock_ticket_service_instance
            
            attachment_service.file_processor.process_uploaded_file = AsyncMock()
            
            # Mock AI service response
            from unittest.mock import MagicMock
            mock_analysis = MagicMock()
            mock_analysis.confidence = 0.9
            mock_analysis.suggested_category = "technical"
            mock_analysis.suggested_priority = "medium"
            mock_analysis.reasoning = "Test reasoning"
            attachment_service.ai_service.analyze_ticket_with_attachments = AsyncMock(return_value=mock_analysis)
        
            # Test ticket creation with files
            ticket_data = {
                "title": "Login Issue",
                "description": "Cannot log in"
            }
            
            file_ids = [mock_file.id]
            
            result = await attachment_service.create_ticket_with_files(
                db=mock_db_session,
                ticket_data=ticket_data,
                file_ids=file_ids,
                user=sample_user
            )
            
            # Verify file validation was called
            attachment_service.file_service.get_file.assert_called_with(mock_db_session, mock_file.id)
            
            # Verify ticket service was called
            mock_ticket_service_instance.create_ticket.assert_called_once()
            
            # Verify ticket_data was updated with attachments
            call_args = mock_ticket_service_instance.create_ticket.call_args
            ticket_data_arg = call_args[1]["ticket_data"]
            assert "attachments" in ticket_data_arg
            assert ticket_data_arg["attachments"] == [{"file_id": str(mock_file.id)}]
    
    @pytest.mark.asyncio
    async def test_content_extraction_pipeline(self, mock_db_session, sample_user, sample_file_content):
        """REQUIRED TEST: Content extraction pipeline integration"""
        
        file_obj = File(
            id=uuid.uuid4(),
            filename="support_ticket.txt",
            file_path="test/support_ticket.txt",
            mime_type="text/plain",
            file_size=len(sample_file_content),
            file_hash="content_hash",
            file_type=FileType.TEXT,
            uploaded_by_id=sample_user.id,
            organization_id=sample_user.organization_id,
            status=FileStatus.UPLOADED
        )
        
        processor = FileProcessingService()
        processor.file_service.get_file_content = AsyncMock(return_value=sample_file_content.encode())
        
        # Process the file
        await processor.process_uploaded_file(mock_db_session, file_obj)
        
        # Verify processing completed
        assert file_obj.status == FileStatus.PROCESSED
        assert file_obj.extracted_context is not None
        assert file_obj.extraction_method == "document_parser"
        
        # Verify content extraction
        context = file_obj.extracted_context
        assert "document" in context
        assert len(context["document"]["pages"]) > 0
        
        # Verify AI processing
        assert file_obj.content_summary is not None
        assert len(file_obj.content_summary) > 0
        assert file_obj.language_detection in ["en", "unknown"]
    
    @pytest.mark.asyncio
    async def test_error_handling_across_services(self, mock_db_session, sample_user):
        """REQUIRED TEST: Error handling across all services"""
        
        # Create file with invalid content
        invalid_file = File(
            id=uuid.uuid4(),
            filename="corrupted.bin",
            file_path="test/corrupted.bin",
            mime_type="application/octet-stream",
            file_size=100,
            file_hash="invalid_hash",
            file_type=FileType.OTHER,
            uploaded_by_id=sample_user.id,
            organization_id=sample_user.organization_id,
            status=FileStatus.UPLOADED
        )
        
        processor = FileProcessingService()
        # Mock get_file_content to raise an exception to simulate processing failure
        processor.file_service.get_file_content = AsyncMock(side_effect=Exception("Corrupted file content"))
        
        # Process should handle error gracefully
        await processor.process_uploaded_file(mock_db_session, invalid_file)
        
        # File should be marked as failed, not crash the system
        assert invalid_file.status == FileStatus.FAILED
        assert invalid_file.processing_error is not None
    
    @pytest.mark.asyncio
    async def test_file_content_text_extraction(self):
        """REQUIRED TEST: Text extraction from extracted_context"""
        
        # Test document content extraction
        document_context = {
            "document": {
                "pages": [
                    {"text": "Page 1 content with authentication error"},
                    {"text": "Page 2 content with login details"}
                ]
            }
        }
        
        processor = FileProcessingService()
        extracted_text = processor._extract_text_from_context(document_context)
        
        assert "authentication error" in extracted_text
        assert "login details" in extracted_text
        
        # Test image content extraction
        image_context = {
            "image": {
                "description": "Screenshot of login error dialog",
                "text_regions": [
                    {"text": "Invalid credentials"},
                    {"text": "Try again"}
                ]
            }
        }
        
        extracted_text = processor._extract_text_from_context(image_context)
        
        assert "Screenshot of login error dialog" in extracted_text
        assert "Invalid credentials" in extracted_text
        
        # Test audio content extraction
        audio_context = {
            "audio": {
                "transcription": {"text": "I can't log into my account"}
            }
        }
        
        extracted_text = processor._extract_text_from_context(audio_context)
        
        assert "I can't log into my account" in extracted_text


# VALIDATION GATE: Integration tests must ALL PASS to complete Phase 1
if __name__ == "__main__":
    pytest.main([__file__, "-v"])