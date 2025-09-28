#!/usr/bin/env python3
"""
Integration Tests for FastMCP

Tests the complete FastMCP client-server integration including:
- Client-server communication
- Token authentication flow
- Pydantic AI integration with FastMCP
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.schemas.principal import Principal
from mcp_client.fast_client import FastMCPClientWrapper


class TestFastMCPIntegration:
    """Integration tests for FastMCP client-server communication."""
    
    @pytest.mark.asyncio
    async def test_fastmcp_client_server_communication(self):
        """Test FastMCP client can communicate with server."""
        # Mock successful server communication
        client = FastMCPClientWrapper(
            url="http://localhost:8001",
            token="ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"
        )
        
        # Mock the FastMCP client methods
        with patch.object(client, '_get_client') as mock_get_client:
            mock_mcp_client = AsyncMock()
            mock_mcp_client.__aenter__.return_value = mock_mcp_client
            mock_mcp_client.__aexit__.return_value = None
            
            # Mock tool listing
            mock_tool1 = type('Tool', (), {
                'name': 'list_tickets', 
                'description': 'List tickets with pagination'
            })()
            mock_tool2 = type('Tool', (), {
                'name': 'create_ticket', 
                'description': 'Create a new ticket'
            })()
            mock_mcp_client.list_tools.return_value = [mock_tool1, mock_tool2]
            
            # Mock tool calling
            mock_result = type('Result', (), {
                'content': '{"success": true, "tickets": []}'
            })()
            mock_mcp_client.call_tool.return_value = mock_result
            
            mock_get_client.return_value = mock_mcp_client
            
            # Test tool listing
            tools = await client.list_tools()
            assert len(tools) == 2
            assert any(tool["name"] == "list_tickets" for tool in tools)
            assert any(tool["name"] == "create_ticket" for tool in tools)
            
            # Test tool calling
            result = await client.call_tool("list_tickets", page=1, page_size=5)
            assert result == '{"success": true, "tickets": []}'
            
            # Verify methods were called
            mock_mcp_client.list_tools.assert_called_once()
            mock_mcp_client.call_tool.assert_called_once_with("list_tickets", {"page": 1, "page_size": 5})
    
    @pytest.mark.asyncio
    async def test_pydantic_ai_fastmcp_integration(self):
        """Test Pydantic AI agent with FastMCP tools."""
        from app.services.dynamic_agent_factory import dynamic_agent_factory
        from app.models.ai_agent import Agent as AgentModel
        
        # Create test agent model
        agent_model = AgentModel(
            id="test-agent-123",
            name="Test Agent",
            prompt="You are a helpful AI assistant for testing FastMCP integration.",
            model_provider="openai",
            model_name="gpt-4o-mini",
            organization_id="20a8aae5-ec85-42a9-b025-45ee32a2f9a1",
            is_ready=True,
            use_memory_context=False,
            max_iterations=3,
            max_context_size=1000,
            tools=["list_tickets", "create_ticket"]
        )
        
        # Create test principal
        principal = Principal(
            user_id="9cdd4c6c-a65d-464b-b3ba-64e6781fba2b",
            organization_id="20a8aae5-ec85-42a9-b025-45ee32a2f9a1",
            email="test@test.com",
            api_token="ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"
        )
        
        # Mock FastMCP client interactions
        with patch('mcp_client.fast_client.FastMCPClientWrapper.ping') as mock_ping:
            mock_ping.return_value = True
            
            with patch('mcp_client.fast_client.FastMCPClientWrapper.call_tool') as mock_call_tool:
                mock_call_tool.return_value = '{"success": true, "tools_available": ["list_tickets", "create_ticket"]}'
                
                # Test agent creation
                agent = await dynamic_agent_factory.create_agent_from_model(
                    agent_model, principal
                )
                
                assert agent is not None
                # Verify agent has toolsets
                assert hasattr(agent, 'toolsets')
                assert len(agent.toolsets) > 0
                
                # Mock the agent run to avoid actual LLM calls
                with patch.object(agent, 'run') as mock_run:
                    mock_result = type('Result', (), {
                        'output': type('Response', (), {
                            'content': 'I can help you with tickets using these tools: list_tickets, create_ticket',
                            'confidence': 0.9,
                            'requires_escalation': False,
                            'tools_used': [{'name': 'list_tickets'}]
                        })(),
                        'tools_used': [{'name': 'list_tickets'}]
                    })()
                    mock_run.return_value = mock_result
                    
                    # Test message processing
                    from app.schemas.ai_response import AgentContext
                    context = AgentContext(
                        user_input="what tools can you call?",
                        uploaded_files=[],
                        conversation_history=[],
                        user_metadata={"user_id": principal.user_id},
                        session_id="test-session",
                        organization_id=principal.organization_id
                    )
                    
                    response = await dynamic_agent_factory.process_message_with_agent(
                        agent_model,
                        "what tools can you call?",
                        context,
                        principal
                    )
                    
                    assert response.confidence > 0
                    assert "tool" in response.content.lower()
                    assert not response.requires_escalation
                    
                    # Verify agent.run was called with proper parameters
                    mock_run.assert_called_once()
                    call_args = mock_run.call_args
                    assert call_args[0][0] == "what tools can you call?"  # message
                    assert call_args[1]["deps"] == principal  # deps parameter
    
    @pytest.mark.asyncio
    async def test_fastmcp_client_error_handling(self):
        """Test FastMCP client error handling."""
        client = FastMCPClientWrapper(token="invalid-token")
        
        # Mock client creation failure
        with patch.object(client, '_get_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Authentication failed")
            
            # Test that ping returns False on failure
            result = await client.ping()
            assert result is False
            
            # Test that list_tools returns empty list on failure
            tools = await client.list_tools()
            assert tools == []
            
            # Test that call_tool returns error JSON on failure
            result = await client.call_tool("test_tool", param="value")
            import json
            error_data = json.loads(result)
            assert "error" in error_data
            assert "Authentication failed" in error_data["error"]
    
    @pytest.mark.asyncio
    async def test_authentication_token_handling(self):
        """Test that authentication tokens are properly handled."""
        # Test with valid token
        client = FastMCPClientWrapper(
            token="ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"
        )
        
        assert client.is_authenticated()
        headers = client.get_headers()
        assert headers["Authorization"] == "Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"
        
        # Test without token
        client_unauth = FastMCPClientWrapper()
        assert not client_unauth.is_authenticated()
        assert client_unauth.get_headers() == {}
    
    @pytest.mark.asyncio
    async def test_principal_to_fastmcp_client_conversion(self):
        """Test conversion from Principal to FastMCP client."""
        # Create principal with token
        principal = Principal(
            user_id="test-user-456",
            email="test@example.com",
            organization_id="test-org-789",
            api_token="test-jwt-token-123"
        )
        
        # Create client from principal
        client = FastMCPClientWrapper.from_principal(principal)
        
        assert client.is_authenticated()
        assert client.token == "test-jwt-token-123"
        
        # Test without API token
        principal_no_token = Principal(
            user_id="test-user",
            email="test@example.com",
            organization_id="test-org"
        )
        
        client_no_token = FastMCPClientWrapper.from_principal(principal_no_token)
        assert not client_no_token.is_authenticated()
        assert client_no_token.token is None