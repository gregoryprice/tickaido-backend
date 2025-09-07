#!/usr/bin/env python3
"""
System Title Generation Agent Runner Tests

Comprehensive unit tests for the TitleGenerationAgentRunner that integrates
with the system title generation agent architecture.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4

from app.services.title_generation_runner import TitleGenerationAgentRunner
from app.schemas.title_generation import TitleGenerationResult
from app.models.ai_agent import Agent


class MockMessage:
    """Mock message for testing"""
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
        self.created_at = datetime.now(timezone.utc)


class TestTitleGenerationAgentRunner:
    """Comprehensive tests for TitleGenerationAgentRunner"""

    def create_mock_system_agent(self) -> Agent:
        """Create a mock system title generation agent"""
        agent = Agent(
            id=uuid4(),
            organization_id=None,  # System agent
            agent_type="title_generation",
            name="System Title Generator",
            is_active=True,
            status="active"
        )
        
        # Set configuration for title generation
        agent.update_configuration({
            "role": "Title Generation Utility",
            "prompt": "You are an expert at creating concise titles...",
            "communication_style": "professional",
            "response_length": "brief",
            "timeout_seconds": 15,
            "tools": []
        })
        
        return agent

    @pytest.mark.asyncio
    async def test_runner_initialization_with_system_agent(self):
        """Test TitleGenerationAgentRunner initialization with system agent"""
        # Create mock system agent
        mock_agent = self.create_mock_system_agent()
        
        # Initialize runner
        runner = TitleGenerationAgentRunner(mock_agent)
        
        # Verify initialization
        assert runner.agent == mock_agent
        assert runner.pydantic_agent is None  # Not initialized until needed
        assert not runner._initialized
        
        # Verify agent validation
        assert runner.agent.agent_type == "title_generation"
        assert runner.agent.organization_id is None  # System agent

    @pytest.mark.asyncio
    async def test_title_generation_with_6_message_limit(self):
        """Test title generation respects 6-message limit optimization"""
        mock_agent = self.create_mock_system_agent()
        runner = TitleGenerationAgentRunner(mock_agent)
        
        # Create 10 messages (more than the 6-message limit)
        messages = [
            MockMessage("user", f"User message {i}")
            for i in range(5)
        ] + [
            MockMessage("assistant", f"Assistant response {i}")
            for i in range(5)
        ]
        
        # Mock the Pydantic AI agent
        mock_result = MagicMock()
        mock_result.output.title = "Generated Title"
        mock_result.output.confidence = 0.85
        
        with patch('app.services.title_generation_runner.PydanticAgent') as mock_agent_class:
            mock_pydantic_agent = AsyncMock()
            mock_pydantic_agent.run = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_pydantic_agent
            
            with patch('app.services.title_generation_runner.ai_config_service'):
                # Generate title
                result = await runner.generate_title(messages)
                
                # Verify result
                assert isinstance(result, TitleGenerationResult)
                assert result.title == "Generated Title"
                assert result.confidence == 0.85
                
                # Verify that the prompt only includes recent messages (max 6)
                call_args = mock_pydantic_agent.run.call_args[0][0]
                # The prompt should limit message processing
                assert "Recent messages" in call_args

    @pytest.mark.asyncio
    async def test_fallback_title_generation(self):
        """Test fallback title generation when AI agent fails"""
        mock_agent = self.create_mock_system_agent()
        runner = TitleGenerationAgentRunner(mock_agent)
        
        # Create test messages
        messages = [
            MockMessage("user", "I need help with password reset"),
            MockMessage("assistant", "I can help you reset your password")
        ]
        
        # Mock AI agent to raise an exception
        with patch('app.services.title_generation_runner.PydanticAgent') as mock_agent_class:
            mock_pydantic_agent = AsyncMock()
            mock_pydantic_agent.run = AsyncMock(side_effect=Exception("AI service unavailable"))
            mock_agent_class.return_value = mock_pydantic_agent
            
            with patch('app.services.title_generation_runner.ai_config_service'):
                # Generate title (should use fallback)
                result = await runner.generate_title(messages)
                
                # Verify fallback result
                assert isinstance(result, TitleGenerationResult)
                assert isinstance(result.title, str)
                assert len(result.title) > 0
                assert result.confidence == 0.1  # Low confidence for fallback
                
                # Should extract keywords or use first user message
                assert "password" in result.title.lower() or "Password" in result.title

    @pytest.mark.asyncio
    async def test_runner_status_reporting(self):
        """Test runner status reporting functionality"""
        mock_agent = self.create_mock_system_agent()
        runner = TitleGenerationAgentRunner(mock_agent)
        
        # Get status before initialization
        status = await runner.get_runner_status()
        
        # Verify status structure
        assert isinstance(status, dict)
        assert "agent_id" in status
        assert "agent_type" in status
        assert "agent_name" in status
        assert "initialized" in status
        assert "system_agent" in status
        assert "configuration" in status
        
        # Verify status values
        assert status["agent_id"] == str(mock_agent.id)
        assert status["agent_type"] == "title_generation"
        assert status["agent_name"] == "System Title Generator"
        assert status["initialized"] is False  # Not initialized yet
        assert status["system_agent"] is True  # organization_id is None
        
        # Verify configuration details
        config = status["configuration"]
        assert config["timeout_seconds"] == 15
        assert config["communication_style"] == "professional"
        assert config["max_messages_processed"] == 6

    @pytest.mark.asyncio
    async def test_title_length_validation(self):
        """Test title length validation (max 8 words)"""
        mock_agent = self.create_mock_system_agent()
        runner = TitleGenerationAgentRunner(mock_agent)
        
        # Test title validation method directly
        long_title = "This is a very long title that exceeds the maximum word limit"
        validated_title = runner._validate_title_length(long_title)
        
        # Should be truncated to 8 words
        words = validated_title.split()
        assert len(words) <= 8
        assert validated_title == "This is a very long title that exceeds"

    @pytest.mark.asyncio
    async def test_empty_messages_handling(self):
        """Test handling of empty or invalid message lists"""
        mock_agent = self.create_mock_system_agent()
        runner = TitleGenerationAgentRunner(mock_agent)
        
        # Test with empty messages
        result = await runner.generate_title([])
        
        assert isinstance(result, TitleGenerationResult)
        assert result.title == "Empty Conversation"
        assert result.confidence == 0.5
        
        # Test with messages that have no content
        empty_messages = [MockMessage("user", ""), MockMessage("assistant", "")]
        result = await runner.generate_title(empty_messages)
        
        assert result.title == "Empty Conversation"

    @pytest.mark.asyncio
    async def test_ai_config_integration(self):
        """Test integration with AI configuration service"""
        mock_agent = self.create_mock_system_agent()
        runner = TitleGenerationAgentRunner(mock_agent)
        
        # Mock AI config service
        mock_config = {
            "model_provider": "openai",
            "model_name": "fast",
            "temperature": 0.3,
            "max_tokens": 50
        }
        
        with patch('app.services.title_generation_runner.ai_config_service') as mock_config_service:
            mock_config_service.get_agent_config = AsyncMock(return_value=mock_config)
            
            with patch('app.services.title_generation_runner.PydanticAgent') as mock_agent_class:
                # Trigger initialization
                await runner.ensure_initialized()
                
                # Verify AI config was used
                mock_config_service.get_agent_config.assert_called_once_with("title_generation_agent")
                
                # Verify PydanticAgent was initialized with correct model
                mock_agent_class.assert_called_once()
                call_kwargs = mock_agent_class.call_args[1]
                assert "openai:gpt-3.5-turbo" in call_kwargs["model"]

    @pytest.mark.asyncio 
    async def test_message_content_formatting(self):
        """Test proper formatting of message content for AI processing"""
        mock_agent = self.create_mock_system_agent()
        runner = TitleGenerationAgentRunner(mock_agent)
        
        messages = [
            MockMessage("user", "Hello, I have a login issue"),
            MockMessage("assistant", "I can help with that. What's the problem?"),
            MockMessage("user", "I can't reset my password")
        ]
        
        # Mock the Pydantic AI agent to capture the prompt
        mock_result = MagicMock()
        mock_result.output.title = "Login Password Reset Issue"
        mock_result.output.confidence = 0.9
        
        with patch('app.services.title_generation_runner.PydanticAgent') as mock_agent_class:
            mock_pydantic_agent = AsyncMock()
            mock_pydantic_agent.run = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_pydantic_agent
            
            with patch('app.services.title_generation_runner.ai_config_service'):
                await runner.generate_title(messages, "Old Title")
                
                # Verify the prompt includes properly formatted messages
                prompt = mock_pydantic_agent.run.call_args[0][0]
                assert "User: Hello, I have a login issue" in prompt
                assert "Assistant: I can help with that" in prompt
                assert "User: I can't reset my password" in prompt
                assert "Current title: \"Old Title\"" in prompt