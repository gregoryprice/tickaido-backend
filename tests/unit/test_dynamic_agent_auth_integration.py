#!/usr/bin/env python3
"""
Integration tests for Dynamic Agent Factory authentication.

Tests the integration between:
- Dynamic Agent Factory and MCP Client authentication  
- Principal-based toolset creation
- Authenticated vs unauthenticated fallback behavior
- Tool filtering with authentication
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
from app.services.dynamic_agent_factory import DynamicAgentFactory, dynamic_agent_factory
from app.models.ai_agent import Agent as AgentModel
from app.schemas.principal import Principal
from pydantic_ai import Agent as PydanticAgent


class TestDynamicAgentAuthIntegration:
    """Test suite for Dynamic Agent Factory authentication integration."""
    
    def create_test_principal(self, api_token=None, expired=False) -> Principal:
        """Create a test principal for testing."""
        if not api_token:
            api_token = "ai_dev_test_token_123"
        
        expires_at = datetime.now(timezone.utc)
        if expired:
            expires_at -= timedelta(hours=1)
        else:
            expires_at += timedelta(hours=1)
        
        return Principal(
            user_id="test-user-123",
            organization_id="test-org-456",
            email="test@example.com",
            full_name="Test User",
            api_token=api_token,
            roles=["user"],
            permissions=["ticket.create", "ticket.read"],
            token_issued_at=datetime.now(timezone.utc),
            token_expires_at=expires_at
        )
    
    def create_test_agent_model(self, tools=None, agent_type="customer_support") -> AgentModel:
        """Create a test agent model for testing."""
        if tools is None:
            tools = ["create_ticket", "list_tickets"]
        
        agent_model = Mock(spec=AgentModel)
        agent_model.id = "test-agent-123"
        agent_model.agent_type = agent_type
        agent_model.is_ready = True
        agent_model.prompt = "You are a helpful AI assistant."
        agent_model.model_provider = "openai"
        agent_model.model_name = "primary"
        agent_model.use_memory_context = True
        agent_model.max_context_size = 4000
        agent_model.max_iterations = 10
        
        # Mock configuration
        config = {
            "tools": tools,
            "model_provider": "openai",
            "model_name": "primary"
        }
        agent_model.get_configuration.return_value = config
        
        return agent_model
    
    @patch('mcp_client.client.mcp_client')
    @patch('pydantic_ai.Agent')
    def test_create_agent_with_principal_and_tools(self, mock_pydantic_agent, mock_mcp_client):
        """Test creating agent with Principal and tools creates authenticated MCP client."""
        factory = DynamicAgentFactory()
        agent_model = self.create_test_agent_model(tools=["create_ticket", "list_tickets"])
        principal = self.create_test_principal()
        
        # Mock MCP client creation
        mock_agent_mcp_client = Mock()
        mock_mcp_client.create_agent_client.return_value = mock_agent_mcp_client
        
        # Mock PydanticAgent creation
        mock_pydantic_agent_instance = Mock()
        mock_pydantic_agent.return_value = mock_pydantic_agent_instance
        
        result = await factory.create_agent(agent_model, principal)
        
        assert result is not None
        assert result == mock_pydantic_agent_instance
        
        # Verify authenticated MCP client was created
        mock_mcp_client.create_agent_client.assert_called_once_with(
            agent_id=str(agent_model.id),
            tools=["create_ticket", "list_tickets"],
            principal=principal
        )
        
        # Verify PydanticAgent was created with toolsets
        mock_pydantic_agent.assert_called_once()
        call_kwargs = mock_pydantic_agent.call_args[1]
        assert 'toolsets' in call_kwargs
        assert call_kwargs['toolsets'] == [mock_agent_mcp_client]
        assert call_kwargs['deps_type'] == Principal
    
    @patch('mcp_client.client.mcp_client')
    @patch('pydantic_ai.Agent')
    def test_create_agent_with_principal_no_tools(self, mock_pydantic_agent, mock_mcp_client):
        """Test creating agent with Principal but no tools."""
        factory = DynamicAgentFactory()
        agent_model = self.create_test_agent_model(tools=[])
        principal = self.create_test_principal()
        
        # Mock PydanticAgent creation
        mock_pydantic_agent_instance = Mock()
        mock_pydantic_agent.return_value = mock_pydantic_agent_instance
        
        result = await factory.create_agent(agent_model, principal)
        
        assert result is not None
        assert result == mock_pydantic_agent_instance
        
        # Should not create MCP client when no tools
        mock_mcp_client.create_agent_client.assert_not_called()
        
        # Verify PydanticAgent was created without toolsets
        mock_pydantic_agent.assert_called_once()
        call_kwargs = mock_pydantic_agent.call_args[1]
        assert 'toolsets' not in call_kwargs or call_kwargs.get('toolsets') == []
    
    @patch('mcp_client.client.mcp_client')
    @patch('pydantic_ai.Agent')
    def test_create_agent_no_principal_with_tools(self, mock_pydantic_agent, mock_mcp_client):
        """Test creating agent without Principal but with tools (fallback behavior)."""
        factory = DynamicAgentFactory()
        agent_model = self.create_test_agent_model(tools=["create_ticket"])
        
        # Mock unauthenticated MCP client creation
        mock_unauthenticated_client = Mock()
        mock_mcp_client.create_mcp_client.return_value = mock_unauthenticated_client
        
        # Mock PydanticAgent creation
        mock_pydantic_agent_instance = Mock()
        mock_pydantic_agent.return_value = mock_pydantic_agent_instance
        
        result = await factory.create_agent(agent_model, principal=None)
        
        assert result is not None
        assert result == mock_pydantic_agent_instance
        
        # Should not try to create authenticated client
        mock_mcp_client.create_agent_client.assert_not_called()
        
        # Should create unauthenticated fallback client
        mock_mcp_client.create_mcp_client.assert_called_once_with(principal=None)
        
        # Verify PydanticAgent was created with unauthenticated toolset
        mock_pydantic_agent.assert_called_once()
        call_kwargs = mock_pydantic_agent.call_args[1]
        assert 'toolsets' in call_kwargs
        assert call_kwargs['toolsets'] == [mock_unauthenticated_client]
    
    @patch('mcp_client.client.mcp_client')
    @patch('pydantic_ai.Agent')
    def test_create_agent_mcp_client_creation_fails(self, mock_pydantic_agent, mock_mcp_client):
        """Test agent creation when MCP client creation fails."""
        factory = DynamicAgentFactory()
        agent_model = self.create_test_agent_model(tools=["create_ticket"])
        principal = self.create_test_principal()
        
        # Mock MCP client creation failure
        mock_mcp_client.create_agent_client.return_value = None
        
        # Mock PydanticAgent creation
        mock_pydantic_agent_instance = Mock()
        mock_pydantic_agent.return_value = mock_pydantic_agent_instance
        
        result = await factory.create_agent(agent_model, principal)
        
        assert result is not None
        assert result == mock_pydantic_agent_instance
        
        # Verify MCP client creation was attempted
        mock_mcp_client.create_agent_client.assert_called_once()
        
        # Verify PydanticAgent was created without toolsets (empty list)
        mock_pydantic_agent.assert_called_once()
        call_kwargs = mock_pydantic_agent.call_args[1]
        assert call_kwargs.get('toolsets', []) == []
    
    @patch('mcp_client.client.mcp_client')
    @patch('pydantic_ai.Agent') 
    def test_create_agent_with_expired_principal(self, mock_pydantic_agent, mock_mcp_client):
        """Test creating agent with expired Principal."""
        factory = DynamicAgentFactory()
        agent_model = self.create_test_agent_model(tools=["create_ticket"])
        expired_principal = self.create_test_principal(expired=True)
        
        # Mock MCP client creation failure due to expired token
        mock_mcp_client.create_agent_client.return_value = None
        
        # Mock fallback unauthenticated client
        mock_unauthenticated_client = Mock()
        mock_mcp_client.create_mcp_client.return_value = mock_unauthenticated_client
        
        # Mock PydanticAgent creation
        mock_pydantic_agent_instance = Mock()
        mock_pydantic_agent.return_value = mock_pydantic_agent_instance
        
        result = await factory.create_agent(agent_model, expired_principal)
        
        assert result is not None
        
        # Should attempt authenticated client first
        mock_mcp_client.create_agent_client.assert_called_once_with(
            agent_id=str(agent_model.id),
            tools=["create_ticket"],
            principal=expired_principal
        )
        
        # Should fallback to unauthenticated client
        mock_mcp_client.create_mcp_client.assert_called_once_with(principal=None)
    
    def test_agent_ready_check(self):
        """Test that agent creation fails if agent model is not ready."""
        factory = DynamicAgentFactory()
        agent_model = self.create_test_agent_model()
        agent_model.is_ready = False
        principal = self.create_test_principal()
        
        result = await factory.create_agent(agent_model, principal)
        
        assert result is None
    
    def test_get_model_string(self):
        """Test model string generation for different configurations."""
        factory = DynamicAgentFactory()
        agent_model = self.create_test_agent_model()
        
        # Test with default configuration
        config = {"model_provider": "openai", "model_name": "primary"}
        model_string = factory._get_model_string(agent_model, config)
        assert model_string == "openai:gpt-4o-mini"
        
        # Test with backup model
        config = {"model_provider": "openai", "model_name": "backup"}
        model_string = factory._get_model_string(agent_model, config)
        assert model_string == "openai:gpt-4"
        
        # Test with custom model name
        config = {"model_provider": "openai", "model_name": "gpt-3.5-turbo-16k"}
        model_string = factory._get_model_string(agent_model, config)
        assert model_string == "openai:gpt-3.5-turbo-16k"
    
    def test_agent_context_customizations(self):
        """Test agent-specific context customizations."""
        factory = DynamicAgentFactory()
        
        base_context = {
            "user_input": "Test message",
            "conversation_history": [],
            "user_metadata": {"user_id": "123"},
            "session_id": "session_456",
            "organization_id": "org_789"
        }
        
        # Test customer support customizations
        customer_customizations = factory._get_agent_context_customizations("customer_support", base_context)
        assert customer_customizations == {}  # Default behavior
        
        # Test technical support customizations
        tech_customizations = factory._get_agent_context_customizations("technical_support", base_context)
        expected_metadata = {**base_context["user_metadata"], "context_type": "technical"}
        assert tech_customizations["user_metadata"] == expected_metadata
        
        # Test document analysis customizations
        doc_customizations = factory._get_agent_context_customizations("document_analysis", base_context)
        assert len(doc_customizations["conversation_history"]) <= 5  # Shorter history
        assert doc_customizations["user_metadata"]["context_type"] == "document_analysis"
    
    @patch('mcp_client.client.mcp_client')
    @patch('pydantic_ai.Agent')
    def test_agent_caching_behavior(self, mock_pydantic_agent, mock_mcp_client):
        """Test agent caching behavior with authentication context."""
        factory = DynamicAgentFactory()
        agent_model = self.create_test_agent_model()
        principal = self.create_test_principal()
        
        # Mock MCP client creation
        mock_agent_mcp_client = Mock()
        mock_mcp_client.create_agent_client.return_value = mock_agent_mcp_client
        
        # Mock PydanticAgent creation
        mock_pydantic_agent_instance = Mock()
        mock_pydantic_agent.return_value = mock_pydantic_agent_instance
        
        # Create agent twice with same principal
        result1 = await factory.create_agent(agent_model, principal)
        result2 = await factory.create_agent(agent_model, principal)
        
        # Should be cached (same instance returned)
        assert result1 == result2
        
        # PydanticAgent should only be created once due to caching
        assert mock_pydantic_agent.call_count == 1
        
        # Create with different principal
        different_principal = self.create_test_principal(api_token="different_token")
        result3 = await factory.create_agent(agent_model, different_principal)
        
        # Should create new instance for different principal
        assert mock_pydantic_agent.call_count == 2
    
    @pytest.mark.asyncio
    async def test_process_message_with_principal_integration(self):
        """Test message processing with Principal authentication integration."""
        factory = DynamicAgentFactory()
        agent_model = self.create_test_agent_model()
        principal = self.create_test_principal()
        
        # Mock agent context
        from app.schemas.ai_response import AgentContext
        context = AgentContext(
            user_input="Create a ticket for me",
            uploaded_files=[],
            conversation_history=[],
            user_metadata={"user_id": "123"},
            session_id="session_456",
            organization_id="org_789"
        )
        
        with patch.object(factory, 'create_agent') as mock_create_agent:
            # Mock PydanticAgent
            mock_pydantic_agent = Mock()
            mock_result = Mock()
            mock_result.output = Mock()
            mock_result.output.content = "I've created a ticket for you"
            mock_result.output.confidence = 0.95
            mock_result.output.requires_escalation = False
            mock_result.output.tools_used = ["create_ticket"]
            
            mock_pydantic_agent.run.return_value = mock_result
            mock_create_agent.return_value = mock_pydantic_agent
            
            # Mock agent service for usage recording
            with patch('app.services.ai_agent_service.ai_agent_service') as mock_agent_service:
                mock_agent_service.record_agent_usage = AsyncMock()
                
                result = await factory.process_message_with_agent(
                    agent_model=agent_model,
                    message="Create a ticket for me",
                    context=context,
                    principal=principal
                )
                
                assert result is not None
                assert result.content == "I've created a ticket for you"
                assert result.tools_used == ["create_ticket"]
                
                # Verify agent was created with Principal
                mock_create_agent.assert_called_once_with(agent_model, principal=principal)
                
                # Verify agent.run was called with Principal as deps
                mock_pydantic_agent.run.assert_called_once()
                call_kwargs = mock_pydantic_agent.run.call_args[1]
                assert call_kwargs['deps'] == principal
                
                # Verify usage was recorded
                mock_agent_service.record_agent_usage.assert_called_once_with(
                    agent_id=agent_model.id,
                    success=True,
                    tools_called=1
                )
    
    @pytest.mark.asyncio
    async def test_process_message_agent_creation_fails(self):
        """Test message processing when agent creation fails."""
        factory = DynamicAgentFactory()
        agent_model = self.create_test_agent_model()
        principal = self.create_test_principal(expired=True)
        
        from app.schemas.ai_response import AgentContext
        context = AgentContext(
            user_input="Create a ticket for me",
            uploaded_files=[],
            conversation_history=[],
            user_metadata={"user_id": "123"}
        )
        
        with patch.object(factory, 'create_agent') as mock_create_agent:
            mock_create_agent.return_value = None  # Agent creation fails
            
            with patch('app.services.ai_agent_service.ai_agent_service') as mock_agent_service:
                mock_agent_service.record_agent_usage = AsyncMock()
                
                result = await factory.process_message_with_agent(
                    agent_model=agent_model,
                    message="Create a ticket for me", 
                    context=context,
                    principal=principal
                )
                
                assert result is not None
                assert "temporarily unavailable" in result.content.lower()
                assert result.confidence == 0.0
                assert result.requires_escalation is True
                assert result.tools_used == []
                
                # Verify failed usage was recorded
                mock_agent_service.record_agent_usage.assert_called_once_with(
                    agent_id=agent_model.id,
                    success=False
                )


class TestGlobalDynamicAgentFactory:
    """Test the global dynamic_agent_factory instance."""
    
    def test_global_instance_exists(self):
        """Test that global dynamic_agent_factory instance exists."""
        from app.services.dynamic_agent_factory import dynamic_agent_factory
        assert dynamic_agent_factory is not None
        assert isinstance(dynamic_agent_factory, DynamicAgentFactory)
    
    @patch('mcp_client.client.mcp_client')
    def test_global_instance_uses_global_mcp_client(self, mock_mcp_client):
        """Test that global factory uses global MCP client."""
        from app.services.dynamic_agent_factory import dynamic_agent_factory
        
        # The global factory should use the global mcp_client
        # This is verified by checking the import at the top of the module
        # and that create_agent calls use mcp_client.create_agent_client()
        
        # Mock to prevent actual network calls
        mock_mcp_client.create_agent_client.return_value = None
        
        agent_model = Mock()
        agent_model.id = "test-agent"
        agent_model.is_ready = True
        agent_model.get_configuration.return_value = {"tools": ["test_tool"]}
        
        principal = Principal(
            user_id="test-user",
            organization_id="test-org",
            email="test@example.com",
            api_token="test_token"
        )
        
        # This should use the global mcp_client
        result = await dynamic_agent_factory.create_agent(agent_model, principal)
        
        # Verify the global mcp_client was called
        mock_mcp_client.create_agent_client.assert_called()


@pytest.mark.integration
class TestDynamicAgentFactoryIntegration:
    """Integration tests for Dynamic Agent Factory with real components."""
    
    @pytest.mark.asyncio
    async def test_full_agent_creation_flow_with_auth(self):
        """Test complete agent creation flow with authentication."""
        # This would require actual database and MCP server
        # For now, test the component integration with mocks
        
        factory = DynamicAgentFactory()
        
        # Create realistic test data
        agent_model = Mock(spec=AgentModel)
        agent_model.id = "real-agent-123"
        agent_model.is_ready = True
        agent_model.agent_type = "customer_support"
        agent_model.prompt = "You are a helpful customer support agent."
        agent_model.model_provider = "openai"
        agent_model.model_name = "primary"
        agent_model.get_configuration.return_value = {
            "tools": ["create_ticket", "list_tickets", "update_ticket"],
            "model_provider": "openai",
            "model_name": "primary"
        }
        
        principal = Principal(
            user_id="real-user-456",
            organization_id="real-org-789",
            email="user@company.com",
            full_name="Real User",
            api_token="ai_dev_real_token_abc123",
            roles=["user", "support"],
            permissions=["ticket.create", "ticket.read", "ticket.update"],
            organization_role="member",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=2)
        )
        
        with patch('mcp_client.client.mcp_client') as mock_mcp_client:
            with patch('pydantic_ai.Agent') as mock_pydantic_agent:
                # Mock successful MCP client creation
                mock_agent_mcp_client = Mock()
                mock_mcp_client.create_agent_client.return_value = mock_agent_mcp_client
                
                # Mock PydanticAgent creation
                mock_pydantic_agent_instance = Mock()
                mock_pydantic_agent.return_value = mock_pydantic_agent_instance
                
                result = await factory.create_agent(agent_model, principal)
                
                assert result is not None
                
                # Verify complete authentication flow
                mock_mcp_client.create_agent_client.assert_called_once_with(
                    agent_id="real-agent-123",
                    tools=["create_ticket", "list_tickets", "update_ticket"],
                    principal=principal
                )
                
                # Verify PydanticAgent configuration
                mock_pydantic_agent.assert_called_once()
                call_kwargs = mock_pydantic_agent.call_args[1]
                
                assert call_kwargs['model'] == "openai:gpt-4o-mini"
                assert call_kwargs['deps_type'] == Principal
                assert call_kwargs['toolsets'] == [mock_agent_mcp_client]
                assert call_kwargs['system_prompt'] == "You are a helpful customer support agent."