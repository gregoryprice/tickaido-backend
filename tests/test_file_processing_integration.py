#!/usr/bin/env python3
"""
File Processing Integration Tests - Simplified validation for Phase 1
VALIDATION GATE: Integration tests must ALL PASS to complete Phase 1
"""

import pytest
import uuid
from app.services.file_processing_service import FileProcessingService
from app.models.file import File, FileStatus, FileType


class TestFileProcessingIntegration:
    """Simplified integration tests for file processing system"""
    
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
    async def test_text_content_extraction_from_context(self):
        """REQUIRED TEST: Text extraction from extracted_context JSON"""
        
        processor = FileProcessingService()
        
        # Test document content extraction
        document_context = {
            "document": {
                "pages": [
                    {"text": "Page 1 content with authentication error"},
                    {"text": "Page 2 content with login details"}
                ]
            }
        }
        
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
    
    @pytest.mark.asyncio
    async def test_file_status_transitions(self):
        """REQUIRED TEST: File status transitions work correctly"""
        
        file_obj = File(
            id=uuid.uuid4(),
            filename="test.txt",
            file_path="test/test.txt",
            mime_type="text/plain",
            file_size=100,
            file_hash="test_hash",
            file_type=FileType.TEXT,
            uploaded_by_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            status=FileStatus.UPLOADED,
            processing_attempts=0  # Initialize to 0
        )
        
        # Test processing start
        file_obj.start_processing()
        assert file_obj.status == FileStatus.PROCESSING
        assert file_obj.processing_started_at is not None
        assert file_obj.processing_attempts == 1
        
        # Test successful completion
        file_obj.complete_processing()
        assert file_obj.status == FileStatus.PROCESSED
        assert file_obj.processing_completed_at is not None
        assert file_obj.processing_time_seconds is not None
        
        # Test failure handling
        file_obj.fail_processing("Test error")
        assert file_obj.status == FileStatus.FAILED
        assert file_obj.processing_error == "Test error"
    
    @pytest.mark.asyncio
    async def test_extracted_context_json_structure(self):
        """REQUIRED TEST: extracted_context JSON structure validation"""
        
        # Test document structure
        document_context = {
            "document": {
                "pages": [
                    {
                        "page_number": 1,
                        "text": "Sample text content",
                        "blocks": [
                            {
                                "type": "paragraph",
                                "text": "Sample paragraph",
                                "confidence": 0.95,
                                "geometry": {
                                    "bounding_box": {"left": 0.1, "top": 0.2, "width": 0.8, "height": 0.1}
                                }
                            }
                        ]
                    }
                ],
                "metadata": {"total_pages": 1, "language": "en"}
            }
        }
        
        # Verify JSON serialization works
        import json
        serialized = json.dumps(document_context)
        deserialized = json.loads(serialized)
        
        assert deserialized == document_context
        
        # Test image structure
        image_context = {
            "image": {
                "description": "Screenshot showing login error",
                "objects": ["button", "dialog", "form"],
                "text_regions": [
                    {
                        "text": "Error: Invalid credentials",
                        "confidence": 0.92,
                        "geometry": {"x": 100, "y": 200, "width": 300, "height": 50}
                    }
                ],
                "metadata": {"width": 1920, "height": 1080}
            }
        }
        
        serialized = json.dumps(image_context)
        deserialized = json.loads(serialized)
        assert deserialized == image_context
        
        # Test audio structure
        audio_context = {
            "audio": {
                "transcription": {
                    "text": "Hello, I'm having trouble logging in",
                    "language": "en-US",
                    "confidence": 0.94,
                    "duration_seconds": 45,
                    "segments": [
                        {
                            "start": 0.0,
                            "end": 5.2,
                            "text": "Hello, I'm having trouble",
                            "confidence": 0.96
                        }
                    ]
                },
                "analysis": {
                    "sentiment": "frustrated",
                    "key_topics": ["login", "authentication", "error"],
                    "urgency_level": "medium"
                }
            }
        }
        
        serialized = json.dumps(audio_context)
        deserialized = json.loads(serialized)
        assert deserialized == audio_context
    
    @pytest.mark.asyncio
    async def test_file_properties_with_extracted_context(self):
        """REQUIRED TEST: File properties work with new extracted_context structure"""
        
        # Test file with extracted_context
        file_with_context = File(
            id=uuid.uuid4(),
            filename="report.txt",
            extracted_context={"document": {"pages": [{"text": "content"}]}},
            content_summary="This is a summary"
        )
        
        assert file_with_context.has_content is True
        
        all_content = file_with_context.get_all_content()
        assert "Document Content:" in all_content
        assert "content" in all_content
        assert "AI Summary:" in all_content
        
        # Test file without extracted_context
        file_without_context = File(
            id=uuid.uuid4(),
            filename="empty.txt"
        )
        
        assert file_without_context.has_content is False
        assert file_without_context.get_all_content() == ""
    
    @pytest.mark.asyncio
    async def test_processing_status_tracking(self):
        """REQUIRED TEST: Processing status tracking functionality"""
        
        processor = FileProcessingService()
        
        # Create mock file object
        file_obj = File(
            id=uuid.uuid4(),
            filename="status_test.txt",
            status=FileStatus.PROCESSED,
            extraction_method="document_parser",
            content_summary="Test summary",
            language_detection="en",
            extracted_context={"document": {"pages": [{"text": "test"}]}}
        )
        
        # Mock the file service
        from unittest.mock import AsyncMock
        processor.file_service.get_file = AsyncMock(return_value=file_obj)
        
        status = await processor.get_file_processing_status(None, str(file_obj.id))
        
        assert status["file_id"] == file_obj.id
        assert status["status"] == "processed"
        assert status["extraction_method"] == "document_parser"
        assert status["has_content"] is True
        assert status["content_summary"] == "Test summary"
        assert status["language_detection"] == "en"
    
    @pytest.mark.asyncio
    async def test_content_extraction_error_handling(self):
        """REQUIRED TEST: Error handling in content extraction pipeline"""
        
        file_obj = File(
            id=uuid.uuid4(),
            filename="error_test.txt",
            file_path="test/error_test.txt",
            mime_type="text/plain",
            file_size=100,
            file_hash="error_hash",
            file_type=FileType.TEXT,  # Use text type to trigger processing
            uploaded_by_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            status=FileStatus.UPLOADED,
            processing_attempts=0  # Initialize to 0
        )
        
        processor = FileProcessingService()
        
        # Mock file service to raise an exception during content retrieval
        from unittest.mock import AsyncMock
        processor.file_service.get_file_content = AsyncMock(side_effect=Exception("Storage error"))
        
        # Mock database session
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        
        # Process should handle error gracefully
        await processor.process_uploaded_file(mock_db, file_obj)
        
        # File should be marked as failed, not crash the system
        assert file_obj.status == FileStatus.FAILED
        assert file_obj.processing_error is not None
        assert "Storage error" in file_obj.processing_error


# VALIDATION GATE: Integration tests must ALL PASS to complete Phase 1
if __name__ == "__main__":
    pytest.main([__file__, "-v"])