#!/usr/bin/env python3
"""
Comprehensive tests for AI agents including customer support and categorization agents.
Tests integration with MCP client and Pydantic AI functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any, List
import json

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


class TestCustomerSupportAgent:
    """Test suite for Customer Support Agent"""
    
    @pytest.fixture
    def agent(self):
        """Create a customer support agent instance"""
        return CustomerSupportAgent()
    
    @pytest.fixture
    def sample_context(self):
        """Create sample context for testing"""
        return CustomerSupportContext(
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
    
    def test_customer_support_context_creation(self, sample_context):
        """Test CustomerSupportContext model validation"""
        assert sample_context.user_input == "I'm having trouble logging into my account"
        assert len(sample_context.uploaded_files) == 1
        assert sample_context.session_id == "session_123"
        assert sample_context.integration_preference == "jira"
    
    def test_ticket_creation_result_validation(self):
        """Test TicketCreationResult model validation"""
        result = TicketCreationResult(
            ticket_title="Login Issue",
            ticket_description="User cannot access account",
            category="user_access",
            priority="high",
            urgency="medium",
            department="support",
            confidence_score=0.9,
            recommended_integration="jira",
            file_analysis_summary="Screenshot shows error message",
            next_actions=["Reset password", "Check account status"],
            knowledge_base_matches=[{"id": "kb-001", "title": "Login Troubleshooting"}],
            estimated_resolution_time="2 hours",
            tags=["login", "authentication", "urgent"]
        )
        
        assert result.ticket_title == "Login Issue"
        assert result.confidence_score == 0.9
        assert "login" in result.tags
    
    @patch('app.services.ai_config_service.ai_config_service')
    @patch('mcp_client.client.mcp_client')
    async def test_agent_initialization(self, mock_mcp_client, mock_ai_config, agent):
        """Test agent initialization with mocked dependencies"""
        # Mock configuration
        mock_ai_config.get_agent_config.return_value = {
            "model_provider": "openai",
            "model_name": "gpt-4o-mini",
            "temperature": 0.7,
            "system_prompt": "You are a helpful assistant"
        }
        
        # Mock MCP client
        mock_mcp_client.get_mcp_client.return_value = MagicMock()
        
        await agent.ensure_initialized()
        
        assert agent._initialized is True
        mock_ai_config.get_agent_config.assert_called_once_with("customer_support_agent")
    
    @patch('app.services.ai_config_service.ai_config_service')
    @patch('mcp_client.client.mcp_client')
    async def test_agent_initialization_failure(self, mock_mcp_client, mock_ai_config, agent):
        """Test agent initialization failure handling"""
        # Mock configuration failure
        mock_ai_config.get_agent_config.return_value = None
        
        await agent.ensure_initialized()
        
        assert agent.agent is None
    
    @patch('app.services.ai_config_service.ai_config_service')
    @patch('mcp_client.client.mcp_client')
    async def test_create_ticket_with_ai_success(self, mock_mcp_client, mock_ai_config, agent, sample_context):
        """Test successful ticket creation with AI"""
        # Mock configuration
        mock_ai_config.get_agent_config.return_value = {
            "model_provider": "openai",
            "model_name": "gpt-4o-mini"
        }
        
        # Mock MCP client
        mock_mcp_client.get_mcp_client.return_value = MagicMock()
        
        # Mock AI agent result
        mock_result = MagicMock()
        mock_result.data = TicketCreationResult(
            ticket_title="Login Issue",
            ticket_description="User experiencing authentication problems",
            category="user_access",
            priority="high",
            urgency="medium",
            department="support",
            confidence_score=0.85
        )
        
        agent.agent = AsyncMock()
        agent.agent.run.return_value = mock_result
        agent._initialized = True
        
        result = await agent.create_ticket_with_ai(sample_context)
        
        assert result is not None
        assert result.ticket_title == "Login Issue"
        assert result.category == "user_access"
    
    async def test_create_ticket_with_ai_no_agent(self, agent, sample_context):
        """Test ticket creation when agent is not available"""
        agent.agent = None
        agent._initialized = False
        
        with patch.object(agent, 'ensure_initialized') as mock_init:
            mock_init.return_value = None
            
            result = await agent.create_ticket_with_ai(sample_context)
            
            assert result is None
    
    def test_prepare_prompt_context(self, agent, sample_context):
        """Test prompt context preparation"""
        prompt = agent._prepare_prompt_context(sample_context)
        
        assert "I'm having trouble logging into my account" in prompt
        assert "error_screenshot.png" in prompt
        assert "2 previous messages" in prompt
        assert "jira" in prompt
    
    @patch('mcp_client.client.mcp_client')
    async def test_analyze_files_for_context(self, mock_mcp_client, agent):
        """Test file analysis functionality"""
        mock_mcp_client.is_available.return_value = True
        
        file_paths = ["/tmp/error.png", "/tmp/log.txt"]
        result = await agent.analyze_files_for_context(file_paths)
        
        assert isinstance(result, dict)
        assert "/tmp/error.png" in result
        assert "/tmp/log.txt" in result
    
    @patch('mcp_client.client.mcp_client')
    async def test_analyze_files_no_mcp(self, mock_mcp_client, agent):
        """Test file analysis when MCP is not available"""
        mock_mcp_client.is_available.return_value = False
        
        result = await agent.analyze_files_for_context(["/tmp/file.png"])
        
        assert "error" in result
        assert "File analysis service unavailable" in result["error"]
    
    @patch('mcp_client.client.mcp_client')
    async def test_search_knowledge_base_for_context(self, mock_mcp_client, agent):
        """Test knowledge base search functionality"""
        mock_mcp_client.is_available.return_value = True
        
        result = await agent.search_knowledge_base_for_context("login issue", "user_access")
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["title"] == "Common Issues and Solutions"
    
    @patch('app.services.ai_config_service.ai_config_service')
    @patch('mcp_client.client.mcp_client')
    async def test_get_agent_status(self, mock_mcp_client, mock_ai_config, agent):
        """Test agent status retrieval"""
        mock_ai_config.get_agent_config.return_value = {
            "model_provider": "openai",
            "model_name": "gpt-4o-mini",
            "temperature": 0.7
        }
        
        mock_mcp_client.get_connection_info.return_value = {"status": "connected"}
        mock_mcp_client.get_available_tools.return_value = ["create_ticket", "analyze_file"]
        
        agent.agent = MagicMock()
        
        status = await agent.get_agent_status()
        
        assert status["agent_type"] == "customer_support_agent"
        assert status["initialized"] is True
        assert status["configuration"]["model_provider"] == "openai"
        assert "last_updated" in status


class TestCategorizationAgent:
    """Test suite for Categorization Agent"""
    
    @pytest.fixture
    def agent(self):
        """Create a categorization agent instance"""
        return CategorizationAgent()
    
    @pytest.fixture 
    def sample_context(self):
        """Create sample context for categorization"""
        return CategorizationContext(
            user_input="The login button is broken and I can't access my account",
            attachments=["/tmp/screenshot.png"],
            user_metadata={"department": "engineering", "priority": "high"}
        )
    
    def test_categorization_context_creation(self, sample_context):
        """Test CategorizationContext model validation"""
        assert "broken" in sample_context.user_input
        assert len(sample_context.attachments) == 1
        assert sample_context.user_metadata["department"] == "engineering"
    
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
        assert result.requires_escalation is True
    
    @patch('app.services.ai_config_service.ai_config_service')
    @patch('mcp_client.client.mcp_client')
    async def test_agent_initialization(self, mock_mcp_client, mock_ai_config, agent):
        """Test categorization agent initialization"""
        mock_ai_config.get_agent_config.return_value = {
            "model_provider": "openai",
            "model_name": "gpt-4o-mini",
            "system_prompt": "You categorize support requests"
        }
        
        mock_mcp_client.get_mcp_client.return_value = MagicMock()
        
        await agent.ensure_initialized()
        
        assert agent._initialized is True
    
    @patch('app.services.ai_config_service.ai_config_service')
    @patch('mcp_client.client.mcp_client')
    async def test_categorize_request_success(self, mock_mcp_client, mock_ai_config, agent, sample_context):
        """Test successful request categorization"""
        # Mock initialization
        mock_ai_config.get_agent_config.return_value = {
            "model_provider": "openai",
            "model_name": "gpt-4o-mini"
        }
        mock_mcp_client.get_mcp_client.return_value = MagicMock()
        
        # Mock AI agent result
        mock_result = MagicMock()
        mock_result.data = CategorizationResult(
            category="bug",
            priority="high", 
            urgency="medium",
            department="engineering",
            confidence_score=0.9,
            reasoning="Login functionality issue",
            suggested_tags=["login", "bug"],
            estimated_complexity="medium",
            requires_escalation=False
        )
        
        agent.agent = AsyncMock()
        agent.agent.run.return_value = mock_result
        agent._initialized = True
        
        result = await agent.categorize_request(sample_context)
        
        assert result is not None
        assert result.category == "bug"
        assert result.priority == "high"
    
    async def test_categorize_request_no_agent(self, agent, sample_context):
        """Test categorization when agent is not available"""
        agent.agent = None
        agent._initialized = False
        
        with patch.object(agent, 'ensure_initialized') as mock_init:
            mock_init.return_value = None
            
            result = await agent.categorize_request(sample_context)
            
            assert result is None
    
    def test_prepare_categorization_prompt(self, agent, sample_context):
        """Test categorization prompt preparation"""
        prompt = agent._prepare_categorization_prompt(sample_context)
        
        assert "login button is broken" in prompt
        assert "screenshot.png" in prompt
        assert "engineering" in prompt
    
    @patch('app.services.ai_config_service.ai_config_service')
    @patch('mcp_client.client.mcp_client')
    async def test_get_agent_status(self, mock_mcp_client, mock_ai_config, agent):
        """Test categorization agent status"""
        mock_ai_config.get_agent_config.return_value = {
            "model_provider": "openai",
            "model_name": "gpt-4o-mini"
        }
        
        mock_mcp_client.get_connection_info.return_value = {"status": "connected"}
        mock_mcp_client.get_available_tools.return_value = ["categorize_issue"]
        
        agent.agent = MagicMock()
        
        status = await agent.get_agent_status()
        
        assert status["agent_type"] == "categorization_agent"
        assert status["initialized"] is True


class TestAIAgentIntegration:
    """Integration tests for AI agent interactions"""
    
    @pytest.fixture
    def customer_agent(self):
        return CustomerSupportAgent()
    
    @pytest.fixture 
    def categorization_agent(self):
        return CategorizationAgent()
    
    @patch('app.services.ai_config_service.ai_config_service')
    @patch('mcp_client.client.mcp_client')
    async def test_full_ticket_creation_workflow(self, mock_mcp_client, mock_ai_config, customer_agent, categorization_agent):
        """Test complete workflow from categorization to ticket creation"""
        # Mock configuration for both agents
        mock_ai_config.get_agent_config.return_value = {
            "model_provider": "openai",
            "model_name": "gpt-4o-mini"
        }
        mock_mcp_client.get_mcp_client.return_value = MagicMock()
        
        # Mock categorization result
        categorization_result = CategorizationResult(
            category="bug",
            priority="high",
            urgency="medium", 
            department="engineering",
            confidence_score=0.9,
            reasoning="UI functionality broken",
            suggested_tags=["login", "bug", "ui"],
            estimated_complexity="medium",
            requires_escalation=False
        )
        
        categorization_agent.agent = AsyncMock()
        categorization_agent.agent.run.return_value = MagicMock(data=categorization_result)
        categorization_agent._initialized = True
        
        # Mock ticket creation result
        ticket_result = TicketCreationResult(
            ticket_title="Login Button Bug",
            ticket_description="User reports login button is not functioning properly",
            category="bug",
            priority="high",
            urgency="medium",
            department="engineering",
            confidence_score=0.9,
            recommended_integration="jira",
            tags=["login", "bug", "ui"]
        )
        
        customer_agent.agent = AsyncMock()
        customer_agent.agent.run.return_value = MagicMock(data=ticket_result)
        customer_agent._initialized = True
        
        # Test workflow
        categorization_context = CategorizationContext(
            user_input="The login button is broken"
        )
        
        category_result = await categorization_agent.categorize_request(categorization_context)
        assert category_result.category == "bug"
        
        customer_context = CustomerSupportContext(
            user_input="The login button is broken",
            user_metadata={"category": category_result.category, "priority": category_result.priority}
        )
        
        ticket_creation_result = await customer_agent.create_ticket_with_ai(customer_context)
        assert ticket_creation_result.ticket_title == "Login Button Bug"
        assert ticket_creation_result.category == "bug"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])