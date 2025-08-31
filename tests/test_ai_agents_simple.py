#!/usr/bin/env python3
"""
Simplified tests for AI agents that work with the actual implementation.
Tests basic functionality and integration patterns.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents.customer_support_agent import (
    CustomerSupportAgent, 
    CustomerSupportContext, 
    TicketCreationResult
)
from app.agents.categorization_agent import (
    CategorizationAgent,
    CategorizationContext,
    CategoryAnalysisResult
)


class TestCustomerSupportAgentBasic:
    """Basic tests for Customer Support Agent"""
    
    def test_customer_support_context_creation(self):
        """Test CustomerSupportContext model validation"""
        context = CustomerSupportContext(
            user_input="I'm having trouble logging into my account",
            uploaded_files=["/tmp/error_screenshot.png"],
            conversation_history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi, how can I help?"}
            ],
            user_metadata={"user_id": "123", "plan": "premium"},
            session_id="session_123",
            integration_preference="jira"
        )
        
        assert context.user_input == "I'm having trouble logging into my account"
        assert len(context.uploaded_files) == 1
        assert context.session_id == "session_123"
        assert context.integration_preference == "jira"
    
    def test_ticket_creation_result_validation(self):
        """Test TicketCreationResult model validation"""
        result = TicketCreationResult(
            ticket_title="Login Issue",
            ticket_description="User cannot access account",
            category="user_access",
            priority="high",
            urgency="medium",
            department="support",
            confidence_score=0.9
        )
        
        assert result.ticket_title == "Login Issue"
        assert result.confidence_score == 0.9
        assert result.category == "user_access"
    
    def test_agent_initialization(self):
        """Test agent can be created"""
        agent = CustomerSupportAgent()
        assert agent.agent_type == "customer_support_agent"
        assert agent._initialized is False
    
    def test_prepare_prompt_context(self):
        """Test prompt context preparation"""
        agent = CustomerSupportAgent()
        context = CustomerSupportContext(
            user_input="I'm having trouble logging into my account",
            uploaded_files=["/tmp/error_screenshot.png"],
            conversation_history=[{"role": "user", "content": "Hello"}],
            user_metadata={"user_id": "123"},
            integration_preference="jira"
        )
        
        prompt = agent._prepare_prompt_context(context)
        
        assert "I'm having trouble logging into my account" in prompt
        assert "error_screenshot.png" in prompt
        assert "1 previous messages" in prompt
        assert "jira" in prompt


class TestCategorizationAgentBasic:
    """Basic tests for Categorization Agent"""
    
    def test_categorization_context_creation(self):
        """Test CategorizationContext model validation"""
        context = CategorizationContext(
            title="Login Problem",
            description="The login button is broken and I can't access my account",
            attachments=["/tmp/screenshot.png"],
            user_context={"department": "engineering", "priority": "high"}
        )
        
        assert context.title == "Login Problem"
        assert "broken" in context.description
        assert len(context.attachments) == 1
        assert context.user_context["department"] == "engineering"
    
    def test_categorization_result_validation(self):
        """Test CategoryAnalysisResult model validation"""
        result = CategoryAnalysisResult(
            category="bug",
            priority="high",
            urgency="critical",
            department="engineering",
            confidence_score=0.95,
            reasoning="User reports broken functionality affecting access",
            tags=["login", "bug", "ui"],
            estimated_effort="medium",
            business_impact="high"
        )
        
        assert result.category == "bug"
        assert result.priority == "high"
        assert result.confidence_score == 0.95
        assert "login" in result.tags
    
    def test_agent_initialization(self):
        """Test categorization agent can be created"""
        agent = CategorizationAgent()
        assert agent.agent_type == "categorization_agent"
        assert agent._initialized is False


class TestAIAgentMocking:
    """Test AI agent behavior with mocking"""
    
    @pytest.mark.asyncio
    @patch('app.services.ai_config_service.ai_config_service')
    @patch('mcp_client.client.mcp_client')
    async def test_customer_agent_initialization_mocked(self, mock_mcp_client, mock_ai_config):
        """Test customer agent initialization with mocked dependencies"""
        # Mock configuration
        mock_ai_config.get_agent_config.return_value = {
            "model_provider": "openai",
            "model_name": "gpt-4o-mini",
            "temperature": 0.7,
            "system_prompt": "You are a helpful assistant"
        }
        
        # Mock MCP client
        mock_mcp_client.get_mcp_client.return_value = MagicMock()
        
        agent = CustomerSupportAgent()
        await agent.ensure_initialized()
        
        assert agent._initialized is True
        mock_ai_config.get_agent_config.assert_called_once_with("customer_support_agent")
    
    @pytest.mark.asyncio
    @patch('app.services.ai_config_service.ai_config_service')
    @patch('mcp_client.client.mcp_client')
    async def test_categorization_agent_initialization_mocked(self, mock_mcp_client, mock_ai_config):
        """Test categorization agent initialization with mocked dependencies"""
        # Mock configuration
        mock_ai_config.get_agent_config.return_value = {
            "model_provider": "openai",
            "model_name": "gpt-3.5-turbo",
            "system_prompt": "You categorize support requests"
        }
        
        # Mock MCP client
        mock_mcp_client.get_mcp_client.return_value = MagicMock()
        
        agent = CategorizationAgent()
        await agent.ensure_initialized()
        
        assert agent._initialized is True
        mock_ai_config.get_agent_config.assert_called_once_with("categorization_agent")


class TestAgentErrorHandling:
    """Test agent error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_customer_agent_no_config(self):
        """Test customer agent handling when no config is available"""
        agent = CustomerSupportAgent()
        
        with patch('app.services.ai_config_service.ai_config_service') as mock_config:
            mock_config.get_agent_config.return_value = None
            
            await agent.ensure_initialized()
            
            assert agent.agent is None
    
    @pytest.mark.asyncio
    async def test_categorization_agent_no_config(self):
        """Test categorization agent handling when no config is available"""
        agent = CategorizationAgent()
        
        with patch('app.services.ai_config_service.ai_config_service') as mock_config:
            mock_config.get_agent_config.return_value = None
            
            await agent.ensure_initialized()
            
            assert agent.agent is None
    
    @pytest.mark.asyncio
    @patch('mcp_client.client.mcp_client')
    async def test_file_analysis_no_mcp(self, mock_mcp_client):
        """Test file analysis when MCP is not available"""
        mock_mcp_client.is_available.return_value = False
        
        agent = CustomerSupportAgent()
        result = await agent.analyze_files_for_context(["/tmp/file.png"])
        
        assert "error" in result
        assert "File analysis service unavailable" in result["error"]
    
    @pytest.mark.asyncio
    @patch('mcp_client.client.mcp_client')
    async def test_knowledge_base_search_no_mcp(self, mock_mcp_client):
        """Test knowledge base search when MCP is not available"""
        mock_mcp_client.is_available.return_value = False
        
        agent = CustomerSupportAgent()
        result = await agent.search_knowledge_base_for_context("login issue")
        
        assert isinstance(result, list)
        assert len(result) == 0  # Empty list when MCP unavailable


if __name__ == "__main__":
    pytest.main([__file__, "-v"])