"""
Tests for AI Config Service max_iterations functionality.

This module tests the AI configuration service's ability to load and provide
max_iterations configuration values for agent iteration limiting.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.ai_config_service import AIConfigService


class TestAIConfigServiceMaxIterations:
    """Test AI Config Service max_iterations methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = AIConfigService()
    
    @patch.object(AIConfigService, 'load_config')
    def test_get_max_iterations_from_config(self, mock_load_config):
        """Test getting max_iterations from config file."""
        # Mock config with max_iterations
        mock_config = {
            "ai_strategy": {
                "max_iterations": 7
            }
        }
        mock_load_config.return_value = mock_config
        
        result = self.service.get_max_iterations()
        assert result == 7
    
    @patch.object(AIConfigService, 'load_config')
    def test_get_max_iterations_default_when_missing(self, mock_load_config):
        """Test default value when max_iterations is missing from config."""
        # Mock config without max_iterations
        mock_config = {
            "ai_strategy": {}
        }
        mock_load_config.return_value = mock_config
        
        result = self.service.get_max_iterations()
        assert result == 10  # Default value
    
    @patch.object(AIConfigService, 'load_config')
    def test_get_max_iterations_default_when_ai_strategy_missing(self, mock_load_config):
        """Test default value when ai_strategy section is missing."""
        # Mock config without ai_strategy
        mock_config = {}
        mock_load_config.return_value = mock_config
        
        result = self.service.get_max_iterations()
        assert result == 10  # Default value
    
    @patch.object(AIConfigService, 'load_config')
    def test_get_max_iterations_handles_config_error(self, mock_load_config):
        """Test that config errors are handled gracefully."""
        # Mock config loading error
        mock_load_config.side_effect = Exception("Config file not found")
        
        with patch('app.services.ai_config_service.logger') as mock_logger:
            result = self.service.get_max_iterations()
            assert result == 10  # Default fallback
            mock_logger.warning.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.object(AIConfigService, 'load_config')
    async def test_load_default_agent_configuration_includes_max_iterations(self, mock_load_config):
        """Test that default agent configuration includes max_iterations."""
        # Mock the config and agent config
        mock_config = {
            "ai_strategy": {
                "max_iterations": 6
            },
            "customer_support_agent": {
                "system_prompt_template": "customer_support_default",
                "model_provider": "openai",
                "model_name": "primary"
            }
        }
        mock_load_config.return_value = mock_config
        
        with patch.object(self.service, 'get_agent_config') as mock_get_agent:
            with patch.object(self.service, 'load_prompt_template') as mock_load_prompt:
                mock_get_agent.return_value = mock_config["customer_support_agent"]
                mock_load_prompt.return_value = "Test prompt"
                
                result = await self.service.load_default_agent_configuration()
                
                # Check that max_iterations is included in the result
                assert "max_iterations" in result
                assert result["max_iterations"] == 6
    
    @pytest.mark.asyncio
    @patch.object(AIConfigService, 'get_max_iterations')
    async def test_max_iterations_bounds_in_default_config(self, mock_get_max_iterations):
        """Test that max_iterations in default config respects bounds."""
        # Test with value that should be within bounds
        mock_get_max_iterations.return_value = 5
        
        with patch.object(self.service, 'load_config'), \
             patch.object(self.service, 'get_agent_config'), \
             patch.object(self.service, 'load_prompt_template'):
            
            result = await self.service.load_default_agent_configuration()
            assert result["max_iterations"] == 5


class TestMaxIterationsIntegration:
    """Integration tests for max_iterations functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = AIConfigService()
    
    def test_method_renamed_from_get_tool_call_limit(self):
        """Test that the old method name is no longer available."""
        # Ensure the old method doesn't exist
        assert not hasattr(self.service, 'get_tool_call_limit')
        
        # Ensure the new method exists
        assert hasattr(self.service, 'get_max_iterations')
        assert callable(getattr(self.service, 'get_max_iterations'))
    
    @patch.object(AIConfigService, 'load_config') 
    def test_consistent_naming_in_logs(self, mock_load_config):
        """Test that log messages use consistent 'max iterations' naming."""
        mock_config = {
            "ai_strategy": {
                "max_iterations": 3
            }
        }
        mock_load_config.return_value = mock_config
        
        with patch('app.services.ai_config_service.logger') as mock_logger:
            self.service.get_max_iterations()
            
            # Check that debug log uses new terminology
            mock_logger.debug.assert_called_with("Max iterations from config: 3")


if __name__ == "__main__":
    pytest.main([__file__])