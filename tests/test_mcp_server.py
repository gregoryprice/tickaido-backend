#!/usr/bin/env python3
"""
Comprehensive tests for MCP (Model Context Protocol) server functionality.
Tests all MCP tools, error handling, and integration capabilities.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

# Import MCP server components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.start_mcp_server import (
    mcp,
    create_ticket,
    update_ticket,
    search_tickets,
    analyze_file,
    transcribe_audio,
    extract_text_from_image,
    extract_file_metadata,
    search_knowledge_base,
    categorize_issue,
    get_system_health,
    health_check,
    route_to_integration,
    create_jira_ticket,
    create_salesforce_case,
    create_github_issue,
    log_tool_call
)


class TestMCPToolsTicketManagement:
    """Test suite for MCP ticket management tools"""
    
    @patch('httpx.AsyncClient')
    async def test_create_ticket_success(self, mock_client):
        """Test successful ticket creation"""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "ticket-123",
            "title": "Test Ticket",
            "status": "open",
            "created_at": "2024-01-01T12:00:00Z"
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        result = await create_ticket(
            title="Test Ticket",
            description="This is a test ticket",
            category="technical",
            priority="medium"
        )
        
        result_data = json.loads(result)
        assert result_data["id"] == "ticket-123"
        assert result_data["title"] == "Test Ticket"
        
        # Verify API call
        mock_client_instance.post.assert_called_once()
        call_args = mock_client_instance.post.call_args
        assert "tickets" in call_args[1]["json"]["title"]
    
    @patch('httpx.AsyncClient')
    async def test_create_ticket_with_integration(self, mock_client):
        """Test ticket creation with integration routing"""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "ticket-456",
            "title": "Integration Ticket"
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        with patch('mcp_server.start_mcp_server.route_to_integration') as mock_route:
            mock_route.return_value = {
                "integration": "jira",
                "status": "created",
                "external_id": "JIRA-123"
            }
            
            result = await create_ticket(
                title="Integration Ticket",
                description="Test with integration",
                integration="jira"
            )
            
            result_data = json.loads(result)
            assert "integration_result" in result_data
            assert result_data["integration_result"]["integration"] == "jira"
    
    @patch('httpx.AsyncClient')
    async def test_create_ticket_connection_error(self, mock_client):
        """Test ticket creation with connection error"""
        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = httpx.ConnectError("Connection failed")
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        result = await create_ticket(
            title="Test Ticket",
            description="This should fail"
        )
        
        assert "Cannot connect to backend server" in result
    
    @patch('httpx.AsyncClient')
    async def test_update_ticket_success(self, mock_client):
        """Test successful ticket update"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            "id": "ticket-123",
            "title": "Updated Ticket",
            "status": "in_progress"
        })
        
        mock_client_instance = AsyncMock()
        mock_client_instance.put.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        result = await update_ticket(
            ticket_id="ticket-123",
            title="Updated Ticket",
            status="in_progress"
        )
        
        result_data = json.loads(result)
        assert result_data["title"] == "Updated Ticket"
        assert result_data["status"] == "in_progress"
    
    async def test_update_ticket_no_fields(self):
        """Test update ticket with no fields provided"""
        result = await update_ticket(ticket_id="ticket-123")
        
        assert "At least one field must be provided" in result
    
    @patch('httpx.AsyncClient')
    async def test_search_tickets_success(self, mock_client):
        """Test successful ticket search"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            "items": [
                {"id": "ticket-1", "title": "First Ticket"},
                {"id": "ticket-2", "title": "Second Ticket"}
            ],
            "total": 2,
            "page": 1,
            "size": 10
        })
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        result = await search_tickets(
            query="test",
            status="open",
            page=1,
            page_size=10
        )
        
        result_data = json.loads(result)
        assert result_data["total"] == 2
        assert len(result_data["items"]) == 2
    
    def test_search_tickets_page_size_validation(self):
        """Test page size validation in search tickets"""
        # This would be tested by calling search_tickets with invalid page_size
        # The function should automatically correct invalid values
        pass


class TestMCPFileAnalysisTools:
    """Test suite for MCP file analysis tools"""
    
    async def test_analyze_file_audio(self):
        """Test file analysis for audio files"""
        with patch('mcp_server.start_mcp_server.transcribe_audio') as mock_transcribe:
            mock_transcribe.return_value = json.dumps({
                "transcription": "Hello, this is a test audio file",
                "confidence": 0.95
            })
            
            result = await analyze_file(
                file_path="/tmp/audio.mp3",
                file_type="audio/mpeg",
                analysis_type="transcription"
            )
            
            result_data = json.loads(result)
            assert "transcription" in result_data
            assert result_data["confidence"] == 0.95
    
    async def test_analyze_file_image(self):
        """Test file analysis for image files"""
        with patch('mcp_server.start_mcp_server.extract_text_from_image') as mock_extract:
            mock_extract.return_value = json.dumps({
                "extracted_text": "Error: Page not found",
                "confidence": 0.88
            })
            
            result = await analyze_file(
                file_path="/tmp/screenshot.png", 
                file_type="image/png",
                analysis_type="ocr"
            )
            
            result_data = json.loads(result)
            assert "extracted_text" in result_data
            assert "Error: Page not found" in result_data["extracted_text"]
    
    async def test_analyze_file_document(self):
        """Test file analysis for document files"""
        with patch('mcp_server.start_mcp_server.extract_file_metadata') as mock_metadata:
            mock_metadata.return_value = json.dumps({
                "analysis_type": "metadata",
                "file_type": "application/pdf",
                "metadata": {"file_size": "1024", "pages": 5}
            })
            
            result = await analyze_file(
                file_path="/tmp/document.pdf",
                file_type="application/pdf"
            )
            
            result_data = json.loads(result)
            assert result_data["analysis_type"] == "metadata"
            assert result_data["metadata"]["pages"] == 5
    
    @patch('httpx.AsyncClient')
    async def test_transcribe_audio_success(self, mock_client):
        """Test audio transcription success"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transcription": "This is the transcribed text",
            "confidence": 0.92,
            "language": "en",
            "duration": 45.5
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        result = await transcribe_audio("/tmp/audio.wav", "audio/wav")
        
        result_data = json.loads(result)
        assert result_data["transcription"] == "This is the transcribed text"
        assert result_data["analysis_type"] == "transcription"
        assert result_data["file_path"] == "/tmp/audio.wav"
    
    @patch('httpx.AsyncClient')
    async def test_extract_text_from_image_success(self, mock_client):
        """Test OCR text extraction success"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "extracted_text": "Welcome to our service",
            "confidence": 0.89,
            "language": "en"
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        result = await extract_text_from_image("/tmp/image.jpg", "image/jpeg")
        
        result_data = json.loads(result)
        assert result_data["extracted_text"] == "Welcome to our service"
        assert result_data["analysis_type"] == "ocr"
    
    async def test_extract_file_metadata(self):
        """Test file metadata extraction"""
        result = await extract_file_metadata("/tmp/document.pdf", "application/pdf")
        
        result_data = json.loads(result)
        assert result_data["analysis_type"] == "metadata"
        assert result_data["file_path"] == "/tmp/document.pdf"
        assert result_data["file_type"] == "application/pdf"


class TestMCPIntegrationTools:
    """Test suite for MCP integration tools"""
    
    async def test_route_to_integration_jira(self):
        """Test routing to Jira integration"""
        result = await route_to_integration("jira", "ticket-123")
        
        assert result["integration"] == "jira"
        assert result["status"] == "created"
        assert "SUPPORT-ticket-123" in result["external_id"]
        assert "atlassian.net" in result["url"]
    
    async def test_route_to_integration_salesforce(self):
        """Test routing to Salesforce integration"""
        result = await route_to_integration("salesforce", "ticket-456")
        
        assert result["integration"] == "salesforce"
        assert result["status"] == "created"
        assert "5003000000ticket-456" in result["external_id"]
        assert "salesforce.com" in result["url"]
    
    async def test_route_to_integration_github(self):
        """Test routing to GitHub integration"""
        result = await route_to_integration("github", "ticket-789")
        
        assert result["integration"] == "github"
        assert result["status"] == "created"
        assert "#ticket-789" in result["external_id"]
        assert "github.com" in result["url"]
    
    async def test_route_to_integration_unknown(self):
        """Test routing to unknown integration"""
        result = await route_to_integration("unknown", "ticket-123")
        
        assert "error" in result
        assert "Unknown integration" in result["error"]
    
    async def test_create_jira_ticket(self):
        """Test Jira ticket creation"""
        result = await create_jira_ticket("test-123")
        
        assert result["integration"] == "jira"
        assert result["external_id"] == "SUPPORT-test-123"
    
    async def test_create_salesforce_case(self):
        """Test Salesforce case creation"""
        result = await create_salesforce_case("test-456")
        
        assert result["integration"] == "salesforce"
        assert "5003000000test-456" in result["external_id"]
    
    async def test_create_github_issue(self):
        """Test GitHub issue creation"""
        result = await create_github_issue("test-789")
        
        assert result["integration"] == "github"
        assert result["external_id"] == "#test-789"


class TestMCPKnowledgeBaseTools:
    """Test suite for MCP knowledge base tools"""
    
    async def test_search_knowledge_base_success(self):
        """Test knowledge base search"""
        result = await search_knowledge_base(
            query="login issues",
            max_results=5,
            category="user_access"
        )
        
        result_data = json.loads(result)
        assert result_data["query"] == "login issues"
        assert len(result_data["results"]) == 2
        assert result_data["total_results"] == 2
        assert "search_time_ms" in result_data
    
    async def test_categorize_issue_user_access(self):
        """Test issue categorization for user access"""
        result = await categorize_issue(
            description="I can't login to my account, password reset doesn't work",
            attachments=""
        )
        
        result_data = json.loads(result)
        assert result_data["category"] == "user_access"
        assert result_data["priority"] == "high"
        assert "login" in result_data["analysis"]["keywords_found"]
    
    async def test_categorize_issue_bug(self):
        """Test issue categorization for bugs"""
        result = await categorize_issue(
            description="The application crashes when I click the save button. This is a critical error.",
            attachments="error_log.txt"
        )
        
        result_data = json.loads(result)
        assert result_data["category"] == "bug"
        assert result_data["urgency"] == "critical"
        assert result_data["analysis"]["has_attachments"] is True
    
    async def test_categorize_issue_feature_request(self):
        """Test issue categorization for feature requests"""
        result = await categorize_issue(
            description="It would be great to have a feature that allows bulk operations"
        )
        
        result_data = json.loads(result)
        assert result_data["category"] == "feature_request"
        assert result_data["priority"] == "medium"
        assert result_data["department"] == "engineering"
    
    async def test_categorize_issue_billing(self):
        """Test issue categorization for billing"""
        result = await categorize_issue(
            description="I was charged twice for my subscription this month. Need invoice clarification."
        )
        
        result_data = json.loads(result)
        assert result_data["category"] == "billing"
        assert result_data["priority"] == "medium"


class TestMCPSystemTools:
    """Test suite for MCP system tools"""
    
    @patch('httpx.AsyncClient')
    async def test_get_system_health_success(self, mock_client):
        """Test system health check success"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "uptime": 3600
        })
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        result = await get_system_health()
        
        result_data = json.loads(result)
        assert result_data["status"] == "healthy"
        assert result_data["database"] == "connected"
    
    @patch('httpx.AsyncClient')
    async def test_get_system_health_error(self, mock_client):
        """Test system health check error"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        result = await get_system_health()
        
        assert "HTTP 500" in result
    
    async def test_health_check_endpoint_success(self):
        """Test MCP server health check endpoint"""
        # Create a mock request
        mock_request = MagicMock(spec=Request)
        
        response = await health_check(mock_request)
        
        assert response.status_code == 200
        
        # Parse response content
        content = json.loads(response.body.decode())
        assert content["status"] == "healthy"
        assert content["server"] == "AI Ticket Creator MCP Tools"
        assert content["tools_available"] == 12
        assert "timestamp" in content
    
    async def test_health_check_endpoint_error(self):
        """Test health check endpoint with error"""
        with patch('json.dumps', side_effect=Exception("JSON error")):
            mock_request = MagicMock(spec=Request)
            response = await health_check(mock_request)
            
            assert response.status_code == 500
            content = json.loads(response.body.decode())
            assert content["status"] == "error"


class TestMCPLogging:
    """Test suite for MCP logging functionality"""
    
    def test_log_tool_call_success(self):
        """Test successful tool call logging"""
        with patch('mcp_server.start_mcp_server.tool_logger') as mock_logger:
            log_tool_call(
                tool_name="create_ticket",
                arguments={"title": "Test", "description": "Test desc"},
                response='{"id": "ticket-123"}',
                execution_time_ms=150.5,
                status="success"
            )
            
            # Verify logging calls
            assert mock_logger.info.call_count >= 2  # Request and response logs
    
    def test_log_tool_call_error(self):
        """Test error tool call logging"""
        with patch('mcp_server.start_mcp_server.tool_logger') as mock_logger:
            log_tool_call(
                tool_name="create_ticket",
                arguments={"title": "Test"},
                response="Connection error",
                execution_time_ms=50.0,
                status="error"
            )
            
            # Verify error logging
            assert mock_logger.error.called
    
    def test_log_tool_call_long_response(self):
        """Test logging with long response (truncation)"""
        long_response = "x" * 1500  # Longer than 1000 char limit
        
        with patch('mcp_server.start_mcp_server.tool_logger') as mock_logger:
            log_tool_call(
                tool_name="search_tickets",
                arguments={"query": "test"},
                response=long_response,
                execution_time_ms=200.0,
                status="success"
            )
            
            # Response should be truncated
            call_args = mock_logger.info.call_args_list
            response_log = None
            for call in call_args:
                if "Response Body" in str(call):
                    response_log = str(call)
                    break
            
            assert response_log is not None
            assert "[truncated]" in response_log


class TestMCPErrorHandling:
    """Test suite for MCP error handling"""
    
    async def test_create_ticket_exception_handling(self):
        """Test exception handling in create_ticket"""
        with patch('httpx.AsyncClient', side_effect=Exception("Unexpected error")):
            result = await create_ticket(
                title="Test Ticket",
                description="This should handle the error"
            )
            
            assert "Error: Unexpected error" in result
    
    async def test_analyze_file_exception_handling(self):
        """Test exception handling in analyze_file"""
        with patch('mcp_server.start_mcp_server.transcribe_audio', side_effect=Exception("Analysis error")):
            result = await analyze_file(
                file_path="/tmp/audio.mp3",
                file_type="audio/mpeg"
            )
            
            assert "Error: Analysis error" in result
    
    async def test_search_knowledge_base_exception_handling(self):
        """Test exception handling in search_knowledge_base"""
        with patch('json.dumps', side_effect=Exception("JSON error")):
            result = await search_knowledge_base("test query")
            
            assert "Error: JSON error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])