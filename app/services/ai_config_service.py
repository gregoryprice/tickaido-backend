#!/usr/bin/env python3
"""
AI Configuration Service

Handles dynamic AI configuration management including agent prompts,
model parameters, and runtime configuration updates.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class AIAgentConfigUpdate(BaseModel):
    """Pydantic model for AI agent configuration updates"""
    system_prompt: Optional[str] = Field(None, description="Updated system prompt")
    model_provider: Optional[str] = Field(None, description="AI provider (openai, google)")
    model_name: Optional[str] = Field(None, description="Model configuration name")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: Optional[int] = Field(None, gt=0, le=10000, description="Max tokens")
    timeout: Optional[int] = Field(None, gt=0, le=300, description="Timeout in seconds")
    tools: Optional[List[str]] = Field(None, description="Enabled MCP tools")
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence threshold")


class AIConfigValidationResult(BaseModel):
    """Result of AI configuration validation"""
    is_valid: bool = Field(description="Whether configuration is valid")
    errors: List[str] = Field(default=[], description="Validation error messages")
    warnings: List[str] = Field(default=[], description="Validation warnings")


class AIConfigService:
    """
    Service for managing AI configuration including dynamic updates,
    validation, and persistence.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.config_file_path = os.path.join("app", "config", "ai_config.yaml")
        self._config_cache: Optional[Dict[str, Any]] = None
        self._last_reload: Optional[datetime] = None
        
    def load_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load AI configuration from YAML file with caching.
        
        Args:
            force_reload: Force reload from file even if cached
            
        Returns:
            Dict[str, Any]: AI configuration dictionary
        """
        try:
            # Check if we need to reload
            if (self._config_cache is None or 
                force_reload or 
                self._should_reload_config()):
                
                logger.info(f"Loading AI configuration from {self.config_file_path}")
                
                with open(self.config_file_path) as file:
                    config_content = file.read()
                    
                    # Substitute environment variables
                    config_content = self._substitute_env_variables(config_content)
                    
                    # Parse YAML
                    self._config_cache = yaml.safe_load(config_content)
                    self._last_reload = datetime.now()
                    
                    logger.info("✅ AI configuration loaded successfully")
            
            return self._config_cache
            
        except FileNotFoundError:
            logger.error(f"AI configuration file not found: {self.config_file_path}")
            return self._get_default_config()
        except yaml.YAMLError as e:
            logger.error(f"Error parsing AI configuration YAML: {e}")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading AI configuration: {e}")
            return self._get_default_config()
    
    def _substitute_env_variables(self, content: str) -> str:
        """
        Substitute environment variables in configuration content.
        
        Args:
            content: YAML content with ${VAR} placeholders
            
        Returns:
            str: Content with environment variables substituted
        """
        import re
        
        def replace_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, f"${{{var_name}}}")  # Keep placeholder if not found
        
        # Replace ${VAR_NAME} with environment variable values
        return re.sub(r'\$\{([^}]+)\}', replace_var, content)
    
    def _should_reload_config(self) -> bool:
        """Check if configuration file has been modified since last load"""
        try:
            if not self._last_reload:
                return True
                
            file_mtime = datetime.fromtimestamp(os.path.getmtime(self.config_file_path))
            return file_mtime > self._last_reload
        except Exception:
            return False
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default AI configuration if file loading fails"""
        return {
            "ai_providers": {
                "openai": {
                    "enabled": True,
                    "models": {
                        "primary": {
                            "name": "gpt-4o-mini",
                            "max_tokens": 2000,
                            "temperature": 0.2,
                            "timeout": 30
                        }
                    }
                }
            },
            "agents": {
                "customer_support_agent": {
                    "model_provider": "openai",
                    "model_name": "primary",
                    "temperature": 0.2,
                    "max_tokens": 2000,
                    "timeout": 30
                }
            }
        }
    
    async def get_agent_config(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific AI agent.
        
        Args:
            agent_type: Agent type (e.g., "customer_support_agent")
            
        Returns:
            Optional[Dict[str, Any]]: Agent configuration or None if not found
        """
        try:
            config = self.load_config()
            agents_config = config.get("agents", {})
            
            if agent_type not in agents_config:
                logger.warning(f"Agent type '{agent_type}' not found in configuration")
                return None
            
            agent_config = agents_config[agent_type].copy()
            
            # Add prompt template if available
            prompt_templates = config.get("prompt_templates", {})
            prompt_template_name = agent_config.get("system_prompt_template")
            if prompt_template_name and prompt_template_name in prompt_templates:
                agent_config["system_prompt"] = prompt_templates[prompt_template_name]
            
            # Add metadata
            agent_config.update({
                "agent_type": agent_type,
                "loaded_at": datetime.now().isoformat(),
                "version": 1  # Will be incremented for database-stored configs
            })
            
            return agent_config
            
        except Exception as e:
            logger.error(f"Error getting agent configuration for {agent_type}: {e}")
            return None
    
    async def validate_config(self, agent_type: str, config_update: AIAgentConfigUpdate) -> AIConfigValidationResult:
        """
        Validate AI agent configuration update.
        
        Args:
            agent_type: Agent type being updated
            config_update: Configuration update to validate
            
        Returns:
            AIConfigValidationResult: Validation result
        """
        errors = []
        warnings = []
        
        try:
            # Validate agent type exists
            current_config = await self.get_agent_config(agent_type)
            if not current_config:
                errors.append(f"Agent type '{agent_type}' not found")
                return AIConfigValidationResult(is_valid=False, errors=errors)
            
            # Validate model provider and name
            if config_update.model_provider:
                config = self.load_config()
                providers = config.get("ai_providers", {})
                
                if config_update.model_provider not in providers:
                    errors.append(f"Unknown model provider: {config_update.model_provider}")
                
                elif config_update.model_name:
                    provider_config = providers[config_update.model_provider]
                    models = provider_config.get("models", {})
                    
                    if config_update.model_name not in models:
                        errors.append(f"Unknown model name '{config_update.model_name}' for provider '{config_update.model_provider}'")
            
            # Validate tools
            if config_update.tools:
                valid_tools = [
                    "analyze_file", "create_ticket", "categorize_issue", 
                    "search_knowledge_base", "extract_text_from_image", "transcribe_audio"
                ]
                
                invalid_tools = [tool for tool in config_update.tools if tool not in valid_tools]
                if invalid_tools:
                    errors.append(f"Unknown tools: {invalid_tools}")
            
            # Validate system prompt length
            if config_update.system_prompt:
                if len(config_update.system_prompt) > 10000:
                    warnings.append("System prompt is very long and may impact performance")
                elif len(config_update.system_prompt) < 50:
                    warnings.append("System prompt is very short and may not provide adequate guidance")
            
            # Validate temperature and other parameters are within reasonable ranges
            if config_update.temperature is not None:
                if config_update.temperature > 1.0:
                    warnings.append("High temperature may produce less consistent results")
                elif config_update.temperature < 0.1:
                    warnings.append("Very low temperature may produce repetitive results")
            
            return AIConfigValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error validating configuration: {e}")
            return AIConfigValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"]
            )
    
    async def update_agent_config(self, agent_type: str, config_update: AIAgentConfigUpdate) -> Optional[Dict[str, Any]]:
        """
        Update AI agent configuration with validation.
        
        Args:
            agent_type: Agent type to update
            config_update: Configuration updates
            
        Returns:
            Optional[Dict[str, Any]]: Updated configuration or None if failed
        """
        try:
            # Validate configuration first
            validation_result = await self.validate_config(agent_type, config_update)
            if not validation_result.is_valid:
                logger.error(f"Configuration validation failed: {validation_result.errors}")
                return None
            
            # Get current configuration
            current_config = await self.get_agent_config(agent_type)
            if not current_config:
                logger.error(f"Agent type '{agent_type}' not found")
                return None
            
            # Apply updates
            updated_config = current_config.copy()
            
            # Update fields from config_update
            update_dict = config_update.dict(exclude_unset=True)
            for key, value in update_dict.items():
                if value is not None:
                    updated_config[key] = value
            
            # Update metadata
            updated_config["updated_at"] = datetime.now().isoformat()
            updated_config["version"] = updated_config.get("version", 1) + 1
            
            # TODO: Store in database for persistence
            # This would be implemented when the AI agent config model is created
            # await self._store_config_in_database(agent_type, updated_config)
            
            logger.info(f"✅ Updated configuration for agent '{agent_type}'")
            return updated_config
            
        except Exception as e:
            logger.error(f"Error updating agent configuration: {e}")
            return None
    
    async def get_all_agent_types(self) -> List[str]:
        """
        Get list of all available agent types.
        
        Returns:
            List[str]: List of agent type names
        """
        try:
            config = self.load_config()
            agents_config = config.get("agents", {})
            return list(agents_config.keys())
        except Exception as e:
            logger.error(f"Error getting agent types: {e}")
            return []
    
    async def get_provider_info(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an AI provider.
        
        Args:
            provider_name: Name of the provider (e.g., "openai")
            
        Returns:
            Optional[Dict[str, Any]]: Provider configuration
        """
        try:
            config = self.load_config()
            providers = config.get("ai_providers", {})
            
            if provider_name not in providers:
                return None
            
            provider_config = providers[provider_name].copy()
            
            # Remove sensitive information
            if "api_key" in provider_config:
                provider_config["api_key"] = "[REDACTED]"
            if "api_key_file" in provider_config:
                provider_config["api_key_file"] = "[REDACTED]"
            
            return provider_config
            
        except Exception as e:
            logger.error(f"Error getting provider info: {e}")
            return None
    
    async def test_configuration(self, agent_type: str, test_input: str = "Hello, this is a test message.") -> Dict[str, Any]:
        """
        Test an AI agent configuration with a simple input.
        
        Args:
            agent_type: Agent type to test
            test_input: Test input message
            
        Returns:
            Dict[str, Any]: Test result
        """
        try:
            # Get agent configuration
            agent_config = await self.get_agent_config(agent_type)
            if not agent_config:
                return {
                    "success": False,
                    "error": f"Agent type '{agent_type}' not found"
                }
            
            # TODO: Implement actual AI model testing
            # This would involve initializing the agent and running a test query
            # For now, return a mock successful test
            
            return {
                "success": True,
                "agent_type": agent_type,
                "test_input": test_input,
                "response": "Test configuration successful (mock response)",
                "model_used": f"{agent_config.get('model_provider')}/{agent_config.get('model_name')}",
                "response_time": 0.5,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error testing configuration: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def load_prompt_template(self, template_name: str) -> str:
        """
        Load prompt template from ai_config.yaml
        
        Args:
            template_name: Name of the template (e.g., "customer_support_default")
            
        Returns:
            str: Prompt template content
        """
        try:
            config = self.load_config()
            prompt_templates = config.get("prompt_templates", {})
            
            if template_name not in prompt_templates:
                logger.warning(f"Prompt template '{template_name}' not found in configuration")
                
                # Fallback to CUSTOMER_SUPPORT_CHAT_PROMPT if available
                if template_name == "customer_support_default":
                    # Import here to avoid circular imports
                    from app.agents.prompts import CUSTOMER_SUPPORT_CHAT_PROMPT
                    logger.info("Using fallback CUSTOMER_SUPPORT_CHAT_PROMPT")
                    return CUSTOMER_SUPPORT_CHAT_PROMPT
                    
                return "You are a helpful AI assistant."
                
            template_content = prompt_templates[template_name]
            logger.debug(f"Loaded prompt template: {template_name}")
            return template_content
            
        except Exception as e:
            logger.error(f"Error loading prompt template {template_name}: {e}")
            return "You are a helpful AI assistant."
    
    def get_max_iterations(self) -> int:
        """
        Get the max iterations from AI configuration.
        
        Returns:
            int: Maximum number of AI agent iterations per request (default: 10)
        """
        try:
            config = self.load_config()
            ai_strategy = config.get("ai_strategy", {})
            max_iterations = ai_strategy.get("max_iterations", 10)
            logger.debug(f"Max iterations from config: {max_iterations}")
            return max_iterations
        except Exception as e:
            logger.warning(f"Error loading max iterations from config: {e}, using default: 10")
            return 10
    
    async def load_default_agent_configuration(self) -> Dict[str, Any]:
        """
        Load default agent configuration from ai_config.yaml using AI providers and strategy
        
        Returns:
            Dict[str, Any]: Default agent configuration with core settings
        """
        try:
            config = self.load_config()
            
            # Get AI strategy configuration
            ai_strategy = config.get("ai_strategy", {})
            primary_provider = ai_strategy.get("primary_provider", "openai")
            model_strategy = ai_strategy.get("model_strategy", {})
            model_name = model_strategy.get(primary_provider, "primary")
            
            # Load prompt template
            system_prompt = await self.load_prompt_template("customer_support_default")
            
            # Build complete configuration using AI strategy
            default_config = {
                "system_prompt": system_prompt,
                "model_provider": primary_provider,
                "model_name": model_name,
                "temperature": 0.2,
                "max_tokens": 2000,
                "timeout": 30,
                "confidence_threshold": 0.7,
                "mcp_enabled": True,
                
                # Agent iteration limit from config
                "max_iterations": self.get_max_iterations()
            }
            
            logger.info("✅ Default agent configuration loaded from ai_config.yaml")
            return default_config
            
        except Exception as e:
            logger.error(f"Error loading default agent configuration: {e}")
            return self._get_fallback_agent_configuration()
    
    def _get_fallback_agent_configuration(self) -> Dict[str, Any]:
        """
        Get fallback agent configuration if ai_config.yaml loading fails
        
        Returns:
            Dict[str, Any]: Fallback configuration with core settings
        """
        logger.warning("Using fallback agent configuration")
        
        return {
            "system_prompt": "You are an AI Customer Support Assistant.",
            "model_provider": "openai",
            "model_name": "primary",
            "temperature": 0.2,
            "max_tokens": 2000,
            "timeout": 30,
            "confidence_threshold": 0.7,
            "mcp_enabled": True,
            "max_iterations": 10
        }


# Global AI configuration service instance
ai_config_service = AIConfigService()