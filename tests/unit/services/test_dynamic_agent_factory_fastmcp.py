#!/usr/bin/env python3
"""
Unit Tests for Dynamic Agent Factory with FastMCP Integration

Tests the updated dynamic agent factory functionality with FastMCP:
- Agent creation with FastMCP tools
- Principal-based authentication
- Tool calling through FastMCP
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.dynamic_agent_factory import dynamic_agent_factory
from app.models.ai_agent import Agent as AgentModel
from app.schemas.principal import Principal
from app.schemas.ai_response import AgentContext, ChatResponse


def create_test_agent_model(tools: list = None) -> AgentModel:
    """Create a test agent model for testing."""
    return AgentModel(
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
        tools=tools or []
    )


def create_test_principal() -> Principal:
    """Create a test principal for testing."""
    return Principal(
        user_id="9cdd4c6c-a65d-464b-b3ba-64e6781fba2b",
        organization_id="20a8aae5-ec85-42a9-b025-45ee32a2f9a1",
        email="test@test.com",
        api_token="ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8",
        permissions=["create_ticket", "list_tickets", "search_tickets"]
    )


def create_test_context() -> AgentContext:
    """Create a test agent context."""
    return AgentContext(
        user_input="test message",
        uploaded_files=[],
        conversation_history=[],
        user_metadata={"user_id": "9cdd4c6c-a65d-464b-b3ba-64e6781fba2b"},
        session_id="test-session-123",
        organization_id="20a8aae5-ec85-42a9-b025-45ee32a2f9a1"
    )


class TestDynamicAgentFactoryWithFastMCP:
    """Test agent factory with FastMCP integration."""
    
    @pytest.mark.asyncio
    async def test_create_agent_with_fastmcp_tools(self):
        """Test agent creation with FastMCP tools."""
        agent_model = create_test_agent_model(tools=["list_tickets", "create_ticket"])
        principal = create_test_principal()
        
        # Mock FastMCP client creation and ping
        with patch('mcp_client.fast_client.FastMCPClientWrapper.from_principal') as mock_from_principal:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_from_principal.return_value = mock_client
            
            agent = await dynamic_agent_factory.create_agent_from_model(
                agent_model, principal
            )
            
            assert agent is not None
            # Verify FastMCP toolset is attached
            assert hasattr(agent, 'toolsets')
            assert len(agent.toolsets) == 1
            
            # Verify client was created with principal
            mock_from_principal.assert_called_once_with(principal)
    
    @pytest.mark.asyncio
    async def test_create_agent_without_tools(self):
        """Test agent creation without tools."""
        agent_model = create_test_agent_model(tools=[])
        principal = create_test_principal()
        
        agent = await dynamic_agent_factory.create_agent_from_model(
            agent_model, principal
        )
        
        assert agent is not None
        # Agent should be created without toolsets when no tools configured
        assert hasattr(agent, 'toolsets')
        assert len(agent.toolsets) == 0
    
    @pytest.mark.asyncio
    async def test_create_agent_without_principal(self):
        """Test agent creation without principal (should skip tools)."""
        agent_model = create_test_agent_model(tools=["list_tickets"])
        
        agent = await dynamic_agent_factory.create_agent_from_model(
            agent_model, principal=None
        )
        
        assert agent is not None
        # Should create agent without tools when no principal provided
        assert hasattr(agent, 'toolsets')
        assert len(agent.toolsets) == 0
    
    @pytest.mark.asyncio
    async def test_create_agent_fastmcp_ping_failure(self):
        """Test agent creation when FastMCP server is not reachable."""
        agent_model = create_test_agent_model(tools=["list_tickets"])
        principal = create_test_principal()
        
        # Mock FastMCP client creation but ping failure
        with patch('mcp_client.fast_client.FastMCPClientWrapper.from_principal') as mock_from_principal:
            mock_client = AsyncMock()
            mock_client.ping.return_value = False  # Server not reachable
            mock_from_principal.return_value = mock_client
            
            agent = await dynamic_agent_factory.create_agent_from_model(
                agent_model, principal
            )
            
            assert agent is not None
            # Should still create agent even if ping fails (might be timing issue)
            assert hasattr(agent, 'toolsets')
            assert len(agent.toolsets) == 1
    
    @pytest.mark.asyncio 
    async def test_agent_tool_calling_through_fastmcp(self):
        """Test that agent can call tools through FastMCP."""
        agent_model = create_test_agent_model(tools=["list_tickets"])
        principal = create_test_principal()
        context = create_test_context()
        
        # Mock FastMCP client creation
        with patch('mcp_client.fast_client.FastMCPClientWrapper.from_principal') as mock_from_principal:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_from_principal.return_value = mock_client
            
            # Mock agent creation and execution
            with patch('app.services.dynamic_agent_factory.PydanticAgent') as mock_agent_class:
                # Mock agent instance
                mock_agent = AsyncMock()
                mock_agent.toolsets = [mock_client]
                
                # Mock agent run result
                mock_result = type('Result', (), {
                    'output': ChatResponse(
                        content="I listed your tickets successfully",
                        confidence=0.85,
                        requires_escalation=False,
                        tools_used=[{"name": "list_tickets", "status": "success"}]
                    ),
                    'tools_used': [{"name": "list_tickets", "status": "success"}]
                })()
                
                mock_agent.run.return_value = mock_result
                mock_agent_class.return_value = mock_agent
                
                # Mock AI agent service for usage recording
                with patch('app.services.ai_agent_service.ai_agent_service.record_agent_usage') as mock_record:
                    mock_record.return_value = None
                    
                    response = await dynamic_agent_factory.process_message_with_agent(
                        agent_model, "list my tickets", context, principal
                    )
                    
                    # Verify successful response
                    assert response.confidence > 0
                    assert "ticket" in response.content.lower()
                    assert not response.requires_escalation
                    assert len(response.tools_used) > 0
                    
                    # Verify agent was called with correct parameters
                    mock_agent.run.assert_called_once()
                    call_args = mock_agent.run.call_args
                    assert call_args[0][0] == "list my tickets"  # message
                    assert call_args[1]["deps"] == principal  # deps parameter
                    
                    # Verify usage was recorded
                    mock_record.assert_called_once_with(
                        agent_id=agent_model.id,
                        success=True,
                        tools_called=1
                    )
    
    @pytest.mark.asyncio
    async def test_agent_cache_functionality(self):
        """Test that agent caching works with FastMCP clients."""
        agent_model = create_test_agent_model(tools=["list_tickets"])
        principal = create_test_principal()
        
        # Mock FastMCP client creation
        with patch('mcp_client.fast_client.FastMCPClientWrapper.from_principal') as mock_from_principal:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_from_principal.return_value = mock_client
            
            # Create agent first time
            agent1 = await dynamic_agent_factory.create_agent_from_model(
                agent_model, principal
            )
            
            # Create agent second time (should use cache)
            agent2 = await dynamic_agent_factory.create_agent_from_model(
                agent_model, principal
            )
            
            # Should be the same cached agent
            assert agent1 is agent2
            
            # FastMCP client should only be created once
            assert mock_from_principal.call_count == 1
    
    @pytest.mark.asyncio
    async def test_fastmcp_client_creation_failure(self):
        """Test agent creation when FastMCP client creation fails."""
        agent_model = create_test_agent_model(tools=["list_tickets"])
        principal = create_test_principal()
        
        # Mock FastMCP client creation failure
        with patch('mcp_client.fast_client.FastMCPClientWrapper.from_principal') as mock_from_principal:
            mock_from_principal.side_effect = Exception("FastMCP client creation failed")
            
            agent = await dynamic_agent_factory.create_agent_from_model(
                agent_model, principal
            )
            
            # Should still create agent without tools when client creation fails
            assert agent is not None
            assert hasattr(agent, 'toolsets')
            assert len(agent.toolsets) == 0
    
    @pytest.mark.asyncio
    async def test_model_string_generation(self):
        """Test that model strings are generated correctly for FastMCP agents."""
        # Test different model configurations
        test_cases = [
            {
                "model_provider": "openai",
                "model_name": "primary",
                "expected": "openai:gpt-4o-mini"
            },
            {
                "model_provider": "openai", 
                "model_name": "backup",
                "expected": "openai:gpt-4"
            },
            {
                "model_provider": "google",
                "model_name": "fast",
                "expected": "google:gpt-3.5-turbo"
            }
        ]
        
        for test_case in test_cases:
            agent_model = create_test_agent_model()
            agent_model.model_provider = test_case["model_provider"]
            agent_model.model_name = test_case["model_name"]
            
            # Test model string generation
            model_string = dynamic_agent_factory._get_model_string(agent_model, {})
            assert model_string == test_case["expected"]
    
    @pytest.mark.asyncio
    async def test_usage_limits_configuration(self):
        """Test that usage limits are properly configured for FastMCP agents."""
        agent_model = create_test_agent_model(tools=["list_tickets"])
        principal = create_test_principal()
        context = create_test_context()
        
        # Mock settings
        with patch('app.config.settings.get_settings') as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.ai_request_limit = 10
            mock_settings_obj.ai_total_tokens_limit = 8000
            mock_settings.return_value = mock_settings_obj
            
            # Mock FastMCP client
            with patch('mcp_client.fast_client.FastMCPClientWrapper.from_principal') as mock_from_principal:
                mock_client = AsyncMock()
                mock_client.ping.return_value = True
                mock_from_principal.return_value = mock_client
                
                # Mock PydanticAgent and its run method
                with patch('app.services.dynamic_agent_factory.PydanticAgent') as mock_agent_class:
                    mock_agent = AsyncMock()
                    mock_agent_class.return_value = mock_agent
                    
                    # Mock run result
                    mock_result = type('Result', (), {
                        'output': ChatResponse(
                            content="Test response",
                            confidence=0.8,
                            requires_escalation=False,
                            tools_used=[]
                        )
                    })()
                    mock_agent.run.return_value = mock_result
                    
                    # Mock usage recording
                    with patch('app.services.ai_agent_service.ai_agent_service.record_agent_usage'):
                        response = await dynamic_agent_factory.process_message_with_agent(
                            agent_model, "test message", context, principal
                        )
                        
                        # Verify agent was created with usage limits
                        mock_agent_class.assert_called_once()
                        
                        # Verify run was called with usage limits
                        mock_agent.run.assert_called_once()
                        call_kwargs = mock_agent.run.call_args[1]
                        
                        assert "usage_limits" in call_kwargs
                        usage_limits = call_kwargs["usage_limits"]
                        
                        # Usage limits should respect both settings and agent model limits
                        expected_request_limit = min(10, agent_model.max_iterations)
                        expected_token_limit = min(8000, agent_model.max_iterations * 1000)
                        
                        assert usage_limits.request_limit == expected_request_limit
                        assert usage_limits.total_tokens_limit == expected_token_limit


class TestDynamicAgentFactoryErrorHandling:
    """Test error handling in dynamic agent factory with FastMCP."""
    
    @pytest.mark.asyncio
    async def test_agent_creation_failure_handling(self):
        """Test handling when agent creation fails."""
        agent_model = create_test_agent_model()
        agent_model.is_ready = False  # Make agent not ready
        
        principal = create_test_principal()
        
        agent = await dynamic_agent_factory.create_agent_from_model(
            agent_model, principal
        )
        
        # Should return None when agent is not ready
        assert agent is None
    
    @pytest.mark.asyncio
    async def test_message_processing_failure_handling(self):
        """Test handling when message processing fails."""
        agent_model = create_test_agent_model(tools=["list_tickets"])
        principal = create_test_principal()
        context = create_test_context()
        
        # Mock agent creation to succeed
        with patch('mcp_client.fast_client.FastMCPClientWrapper.from_principal') as mock_from_principal:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_from_principal.return_value = mock_client
            
            # Mock PydanticAgent creation
            with patch('app.services.dynamic_agent_factory.PydanticAgent') as mock_agent_class:
                mock_agent = AsyncMock()
                mock_agent_class.return_value = mock_agent
                
                # Mock agent run to raise exception
                mock_agent.run.side_effect = Exception("Simulated agent failure")
                
                # Mock usage recording
                with patch('app.services.ai_agent_service.ai_agent_service.record_agent_usage') as mock_record:
                    response = await dynamic_agent_factory.process_message_with_agent(
                        agent_model, "test message", context, principal
                    )
                    
                    # Should return error response
                    assert response.confidence == 0.0
                    assert response.requires_escalation is True
                    assert "error" in response.content.lower()
                    
                    # Should record failed usage
                    mock_record.assert_called_with(
                        agent_id=agent_model.id,
                        success=False
                    )
    
    @pytest.mark.asyncio
    async def test_configuration_extraction(self):
        """Test configuration extraction from agent model."""
        agent_model = create_test_agent_model(tools=["list_tickets", "create_ticket"])
        
        # Mock agent model configuration
        mock_config = {
            "tools": ["list_tickets", "create_ticket"],
            "model_provider": "openai",
            "model_name": "gpt-4o-mini"
        }
        
        with patch.object(agent_model, 'get_configuration', return_value=mock_config):
            principal = create_test_principal()
            
            # Mock FastMCP client
            with patch('mcp_client.fast_client.FastMCPClientWrapper.from_principal') as mock_from_principal:
                mock_client = AsyncMock()
                mock_client.ping.return_value = True
                mock_from_principal.return_value = mock_client
                
                agent = await dynamic_agent_factory.create_agent_from_model(
                    agent_model, principal
                )
                
                assert agent is not None
                # Verify configuration was used
                agent_model.get_configuration.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_principal_token_validation(self):
        """Test that principal token is properly validated."""
        agent_model = create_test_agent_model(tools=["list_tickets"])
        
        # Test with principal without API token
        principal_no_token = Principal(
            user_id="test-user",
            organization_id="test-org",
            email="test@example.com"
            # No api_token
        )
        
        agent = await dynamic_agent_factory.create_agent_from_model(
            agent_model, principal_no_token
        )
        
        # Should create agent without tools when no token available
        assert agent is not None
        assert hasattr(agent, 'toolsets')
        assert len(agent.toolsets) == 0
    
    @pytest.mark.asyncio
    async def test_context_building_functionality(self):
        """Test context building with FastMCP integration."""
        # Test different agent types
        test_cases = [
            {
                "agent_type": "customer_support",
                "expected_context_type": None  # Default, no special context type
            },
            {
                "agent_type": "technical_support", 
                "expected_context_type": "technical"
            },
            {
                "agent_type": "document_analysis",
                "expected_context_type": "document_analysis"
            }
        ]
        
        base_data = {
            "message": "test message",
            "conversation_history": [{"role": "user", "content": "previous message"}],
            "file_context": "",
            "user_metadata": {"user_id": "test-user"},
            "session_id": "test-session",
            "organization_id": "test-org"
        }
        
        for test_case in test_cases:
            context = await dynamic_agent_factory.build_context(
                agent_type=test_case["agent_type"],
                **base_data
            )
            
            assert context is not None
            assert context.user_input == "test message"
            assert context.session_id == "test-session"
            assert context.organization_id == "test-org"
            
            # Check context type customization
            if test_case["expected_context_type"]:
                assert context.user_metadata.get("context_type") == test_case["expected_context_type"]