#!/usr/bin/env python3
"""
Tests for JIRA Integration Framework
Validates the new integration interface and ticket creation workflow
"""

import pytest
from unittest.mock import MagicMock
from app.integrations.base.integration_interface import IntegrationInterface
from app.integrations.base.integration_result import IntegrationTestResult, IntegrationTicketResult
from app.integrations.jira import JiraIntegration
from app.services.integration_service import IntegrationService
from app.schemas.ticket import TicketCreateRequest
from app.schemas.integration import IntegrationTestRequest


class TestIntegrationInterface:
    """Test the generic integration interface"""
    
    def test_integration_interface_abstract(self):
        """Test that IntegrationInterface is properly abstract"""
        with pytest.raises(TypeError):
            # Should not be able to instantiate abstract class
            IntegrationInterface()
    
    def test_integration_test_result_helpers(self):
        """Test the IntegrationTestResult helper methods"""
        success_result = IntegrationTestResult.success("Test passed", {"key": "value"})
        assert success_result["success"] is True
        assert success_result["message"] == "Test passed"
        assert success_result["details"]["key"] == "value"
        
        failure_result = IntegrationTestResult.failure("Test failed", {"error": "details"})
        assert failure_result["success"] is False
        assert failure_result["message"] == "Test failed"
        assert failure_result["details"]["error"] == "details"
    
    def test_integration_ticket_result_helpers(self):
        """Test the IntegrationTicketResult helper methods"""
        success_result = IntegrationTicketResult.success(
            "PROJ-123", 
            "https://jira.com/browse/PROJ-123",
            {"full": "response"}
        )
        assert success_result["success"] is True
        assert success_result["external_ticket_id"] == "PROJ-123"
        assert success_result["external_ticket_url"] == "https://jira.com/browse/PROJ-123"
        assert success_result["details"]["full"] == "response"
        
        failure_result = IntegrationTicketResult.failure("Creation failed")
        assert failure_result["success"] is False
        assert failure_result["external_ticket_id"] is None
        assert failure_result["external_ticket_url"] is None


class TestJiraIntegrationInterface:
    """Test JIRA integration interface implementation"""
    
    @pytest.mark.asyncio
    async def test_jira_integration_implements_interface(self):
        """Test that JiraIntegration properly implements IntegrationInterface"""
        jira = JiraIntegration("https://test.atlassian.net", "test@example.com", "token")
        
        # Check that it implements the interface
        assert isinstance(jira, IntegrationInterface)
        
        # Check that all abstract methods are implemented
        assert hasattr(jira, 'test_connection')
        assert hasattr(jira, 'test_authentication')
        assert hasattr(jira, 'test_permissions')
        assert hasattr(jira, 'create_ticket')
        assert hasattr(jira, 'get_configuration_schema')
        assert hasattr(jira, 'close')
        
        await jira.close()
    
    @pytest.mark.asyncio
    async def test_jira_configuration_schema(self):
        """Test JIRA configuration schema"""
        jira = JiraIntegration("https://test.atlassian.net", "test@example.com", "token")
        
        schema = await jira.get_configuration_schema()
        
        assert schema["type"] == "object"
        assert "base_url" in schema["required"]
        assert "email" in schema["required"]
        assert "api_token" in schema["required"]
        assert "project_key" in schema["required"]
        
        await jira.close()


class TestTicketCreateRequestSchema:
    """Test updated ticket creation schemas"""
    
    def test_ticket_create_request_with_integration(self):
        """Test TicketCreateRequest with integration_id field"""
        from uuid import uuid4
        integration_id = uuid4()
        data = {
            "title": "Test ticket",
            "description": "Test description",
            "integration_id": integration_id,
            "create_externally": True
        }
        
        request = TicketCreateRequest(**data)
        assert request.integration_id == integration_id
        assert request.create_externally is True
    
    def test_ticket_create_request_without_integration(self):
        """Test TicketCreateRequest without integration_id field"""
        data = {
            "title": "Test ticket",
            "description": "Test description"
        }
        
        request = TicketCreateRequest(**data)
        assert request.integration_id is None
        assert request.create_externally is True  # Default value


class TestIntegrationTestRequestSchema:
    """Test updated integration test request schema"""
    
    def test_integration_test_request_with_auto_activate(self):
        """Test IntegrationTestRequest with auto_activate_on_success field"""
        data = {
            "test_types": ["connection", "authentication"],
            "auto_activate_on_success": True
        }
        
        request = IntegrationTestRequest(**data)
        assert request.auto_activate_on_success is True
    
    def test_integration_test_request_default_auto_activate(self):
        """Test IntegrationTestRequest default auto_activate_on_success value"""
        data = {
            "test_types": ["connection"]
        }
        
        request = IntegrationTestRequest(**data)
        assert request.auto_activate_on_success is True  # Default value (updated to True)


class TestIntegrationServiceGeneric:
    """Test the generic integration service functionality"""
    
    def test_integration_service_factory_method(self):
        """Test that the integration service factory method works"""
        service = IntegrationService()
        
        # Create a mock integration
        mock_integration = MagicMock()
        mock_integration.platform_name = "jira"
        mock_integration.base_url = "https://test.atlassian.net"
        mock_integration.get_credentials.return_value = {
            "email": "test@example.com",
            "api_token": "token123"
        }
        
        # Test factory method
        impl = service._get_integration_implementation(mock_integration)
        assert isinstance(impl, JiraIntegration)
        assert impl.base_url == "https://test.atlassian.net"
        assert impl.email == "test@example.com"
    
    def test_integration_service_unsupported_type(self):
        """Test that unsupported integration types raise ValueError"""
        service = IntegrationService()
        
        # Create mock integration with unsupported type
        mock_integration = MagicMock()
        mock_integration.platform_name = "zendesk"  # Not implemented yet
        
        with pytest.raises(ValueError, match="Unsupported integration type"):
            service._get_integration_implementation(mock_integration)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])