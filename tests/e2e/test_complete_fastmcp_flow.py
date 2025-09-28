#!/usr/bin/env python3
"""
End-to-End Tests for Complete FastMCP Flow

Tests the complete flow from API request through Pydantic AI to FastMCP tools.
This includes the exact API call specified in the PRP requirements.
"""

import pytest
import httpx
import asyncio
import json
from unittest.mock import patch


class TestCompleteFastMCPFlow:
    """End-to-end tests for complete FastMCP integration."""
    
    @pytest.mark.asyncio
    async def test_chat_api_with_tool_calling(self):
        """Test the exact API call from the PRP requirements."""
        # This test verifies the exact flow specified in the PRP:
        # POST /api/v1/chat/.../messages with "what tools can you call?"
        
        # Mock the FastMCP client interactions to avoid actual server dependency
        with patch('mcp_client.fast_client.FastMCPClientWrapper.ping') as mock_ping:
            mock_ping.return_value = True
            
            with patch('mcp_client.fast_client.FastMCPClientWrapper.call_tool') as mock_call_tool:
                # Mock tool response that shows available tools
                mock_call_tool.return_value = json.dumps({
                    "success": True,
                    "available_tools": [
                        "list_tickets",
                        "create_ticket", 
                        "search_tickets",
                        "get_ticket",
                        "get_system_health"
                    ],
                    "message": "I can help you with the following tools: list_tickets, create_ticket, search_tickets, get_ticket, and get_system_health."
                })
                
                # Make the exact API call from PRP requirements
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        "http://localhost:8000/api/v1/chat/20a8aae5-ec85-42a9-b025-45ee32a2f9a1/threads/4aba8e44-6900-4c76-8b33-f8b96ca0e75b/messages",
                        headers={
                            "Authorization": "Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8",
                            "Content-Type": "application/json"
                        },
                        json={
                            "content": "what tools can you call?",
                            "message_type": "user"
                        }
                    )
                    
                    # Verify successful response
                    assert response.status_code == 200
                    data = response.json()
                    
                    # Verify response structure
                    assert "content" in data
                    assert "confidence" in data
                    assert "tools_used" in data
                    
                    # Verify tool information is in response
                    assert "tool" in data["content"].lower()
                    assert data["confidence"] > 0
                    
                    # Verify tools were actually called
                    assert len(data.get("tools_used", [])) > 0
                    
                    # Verify specific tool names are mentioned
                    content_lower = data["content"].lower()
                    expected_tools = ["list_tickets", "create_ticket", "search_tickets"]
                    for tool in expected_tools:
                        assert tool in content_lower or tool.replace("_", " ") in content_lower
    
    @pytest.mark.asyncio
    async def test_tool_functionality_end_to_end(self):
        """Test individual tools work end-to-end."""
        test_cases = [
            {
                "message": "list my tickets",
                "expected_tools": ["list_tickets"],
                "expected_content_keywords": ["ticket", "list"],
                "mock_response": {
                    "success": True,
                    "tickets": [
                        {"id": "1", "title": "Test Ticket", "status": "open"}
                    ],
                    "total": 1
                }
            },
            {
                "message": "create a ticket for testing FastMCP",
                "expected_tools": ["create_ticket"],
                "expected_content_keywords": ["ticket", "created", "testing"],
                "mock_response": {
                    "success": True,
                    "ticket_id": "123",
                    "title": "Testing FastMCP",
                    "status": "created"
                }
            },
            {
                "message": "search for tickets about FastMCP",
                "expected_tools": ["search_tickets"],
                "expected_content_keywords": ["search", "ticket", "fastmcp"],
                "mock_response": {
                    "success": True,
                    "results": [
                        {"id": "2", "title": "FastMCP Integration", "relevance": 0.9}
                    ],
                    "total": 1
                }
            }
        ]
        
        for test_case in test_cases:
            with patch('mcp_client.fast_client.FastMCPClientWrapper.ping') as mock_ping:
                mock_ping.return_value = True
                
                with patch('mcp_client.fast_client.FastMCPClientWrapper.call_tool') as mock_call_tool:
                    mock_call_tool.return_value = json.dumps(test_case["mock_response"])
                    
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            "http://localhost:8000/api/v1/chat/20a8aae5-ec85-42a9-b025-45ee32a2f9a1/threads/4aba8e44-6900-4c76-8b33-f8b96ca0e75b/messages",
                            headers={
                                "Authorization": "Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8",
                                "Content-Type": "application/json"
                            },
                            json={
                                "content": test_case["message"],
                                "message_type": "user"
                            }
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        
                        # Check that response is valid
                        assert "content" in data
                        assert data.get("confidence", 0) > 0
                        
                        # Check that expected tools were used (if tools_used is available)
                        if "tools_used" in data and data["tools_used"]:
                            tools_used = [tool.get("name", tool) for tool in data["tools_used"]]
                            for expected_tool in test_case["expected_tools"]:
                                assert any(expected_tool in str(tool) for tool in tools_used)
                        
                        # Check content contains expected keywords
                        content = data["content"].lower()
                        for keyword in test_case["expected_content_keywords"]:
                            assert keyword in content or keyword.replace("_", " ") in content
    
    @pytest.mark.asyncio
    async def test_authentication_flow_integration(self):
        """Test that authentication flows properly through the system."""
        # Test with valid token
        principal = Principal(
            user_id="9cdd4c6c-a65d-464b-b3ba-64e6781fba2b",
            organization_id="20a8aae5-ec85-42a9-b025-45ee32a2f9a1",
            email="ai@tickaido.com",
            api_token="ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"
        )
        
        # Create FastMCP client from principal
        client = FastMCPClientWrapper.from_principal(principal)
        
        assert client.is_authenticated()
        assert client.token == principal.api_token
        
        # Mock authentication validation
        with patch.object(client, '_get_client') as mock_get_client:
            mock_mcp_client = AsyncMock()
            mock_mcp_client.__aenter__.return_value = mock_mcp_client
            mock_mcp_client.__aexit__.return_value = None
            mock_mcp_client.ping.return_value = True
            mock_get_client.return_value = mock_mcp_client
            
            # Test that authenticated client can connect
            is_connected = await client.ping()
            assert is_connected is True
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling throughout the FastMCP integration."""
        # Test with no authentication
        client = FastMCPClientWrapper()
        
        # Mock server connection failure
        with patch.object(client, '_get_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Server unavailable")
            
            # Test that errors are handled gracefully
            result = await client.ping()
            assert result is False
            
            tools = await client.list_tools()
            assert tools == []
            
            error_result = await client.call_tool("test_tool")
            assert "error" in error_result
            assert "Server unavailable" in error_result
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """Test that FastMCP handles concurrent tool calls properly."""
        client = FastMCPClientWrapper(
            token="ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"
        )
        
        # Mock successful tool calls
        with patch.object(client, '_get_client') as mock_get_client:
            mock_mcp_client = AsyncMock()
            mock_mcp_client.__aenter__.return_value = mock_mcp_client
            mock_mcp_client.__aexit__.return_value = None
            
            # Mock different responses for each call
            call_count = 0
            async def mock_call_tool(tool_name, params):
                nonlocal call_count
                call_count += 1
                result = type('Result', (), {
                    'content': f'{{"success": true, "call_id": {call_count}, "tool": "{tool_name}"}}'
                })()
                return result
            
            mock_mcp_client.call_tool = mock_call_tool
            mock_get_client.return_value = mock_mcp_client
            
            # Make concurrent tool calls
            tasks = [
                client.call_tool("list_tickets", page=1),
                client.call_tool("list_tickets", page=2),
                client.call_tool("get_system_health"),
                client.call_tool("list_tickets", page=3)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Verify all calls succeeded
            assert len(results) == 4
            for i, result in enumerate(results, 1):
                result_data = json.loads(result)
                assert result_data["success"] is True
                assert result_data["call_id"] == i
            
            # Verify all calls were made
            assert call_count == 4