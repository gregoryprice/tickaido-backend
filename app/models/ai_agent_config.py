#!/usr/bin/env python3
"""
AI Agent Configuration model for dynamic AI system management
"""

import enum
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class AIAgentType(enum.Enum):
    """Types of AI agents in the system"""
    CUSTOMER_SUPPORT = "customer_support_agent"
    CATEGORIZATION = "categorization_agent"
    FILE_ANALYSIS = "file_analysis_agent"
    TITLE_GENERATION = "title_generation"
    SENTIMENT_ANALYSIS = "sentiment_analysis_agent"
    ROUTING = "routing_agent"
    ESCALATION = "escalation_agent"
    SUMMARY = "summary_agent"
    TRANSLATION = "translation_agent"


class AIAgentConfig(BaseModel):
    """
    AI Agent Configuration model for managing dynamic AI settings.
    Supports versioning, A/B testing, and configuration inheritance.
    """
    
    __tablename__ = "ai_agent_configs"
    
    # Agent identification
    agent_type = Column(
        SQLEnum(AIAgentType),
        nullable=False,
        index=True,
        comment="Type of AI agent this configuration applies to"
    )
    
    name = Column(
        String(255),
        nullable=False,
        comment="Human-readable name for this configuration"
    )
    
    version = Column(
        String(20),
        nullable=False,
        default="1.0.0",
        comment="Configuration version (semantic versioning)"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Description of configuration purpose and changes"
    )
    
    # Configuration status
    is_active = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether this configuration is currently active"
    )
    
    is_default = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is the default configuration"
    )
    
    environment = Column(
        String(50),
        default="production",
        nullable=False,
        index=True,
        comment="Environment this configuration applies to"
    )
    
    # AI Model configuration
    model_provider = Column(
        String(50),
        nullable=False,
        default="openai",
        comment="AI provider (openai, anthropic, google, azure)"
    )
    
    model_name = Column(
        String(100),
        nullable=False,
        default="gpt-4o-mini",
        comment="Specific model name/version"
    )
    
    model_parameters = Column(
        JSON,
        nullable=True,
        comment="Model-specific parameters (temperature, max_tokens, etc.)"
    )
    
    # Prompt configuration
    system_prompt = Column(
        Text,
        nullable=True,
        comment="System prompt template for the agent"
    )
    
    prompt_template = Column(
        Text,
        nullable=True,
        comment="User message prompt template"
    )
    
    prompt_variables = Column(
        JSON,
        nullable=True,
        comment="Variables used in prompt templates"
    )
    
    few_shot_examples = Column(
        JSON,
        nullable=True,
        comment="Few-shot learning examples for the agent"
    )
    
    # Output format configuration
    output_schema = Column(
        JSON,
        nullable=True,
        comment="Expected output schema/format"
    )
    
    validation_rules = Column(
        JSON,
        nullable=True,
        comment="Rules for validating agent output"
    )
    
    post_processing_rules = Column(
        JSON,
        nullable=True,
        comment="Rules for post-processing agent responses"
    )
    
    # Performance tuning
    temperature = Column(
        String(10),
        default="0.7",
        nullable=False,
        comment="Model temperature for response variability"
    )
    
    max_tokens = Column(
        Integer,
        nullable=True,
        comment="Maximum tokens in response"
    )
    
    timeout_seconds = Column(
        Integer,
        default=30,
        nullable=False,
        comment="Request timeout in seconds"
    )
    
    retry_attempts = Column(
        Integer,
        default=3,
        nullable=False,
        comment="Number of retry attempts on failure"
    )
    
    # Quality and safety settings
    confidence_threshold = Column(
        String(10),
        default="0.8",
        nullable=False,
        comment="Minimum confidence threshold for responses"
    )
    
    content_filters = Column(
        JSON,
        nullable=True,
        comment="Content filtering rules and thresholds"
    )
    
    safety_settings = Column(
        JSON,
        nullable=True,
        comment="Safety configuration for the agent"
    )
    
    # Cost management
    cost_per_request_usd = Column(
        String(20),
        nullable=True,
        comment="Estimated cost per request in USD"
    )
    
    daily_budget_usd = Column(
        String(20),
        nullable=True,
        comment="Daily budget limit in USD"
    )
    
    monthly_budget_usd = Column(
        String(20),
        nullable=True,
        comment="Monthly budget limit in USD"
    )
    
    # Usage tracking
    total_requests = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total requests made with this configuration"
    )
    
    successful_requests = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of successful requests"
    )
    
    failed_requests = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of failed requests"
    )
    
    average_response_time_ms = Column(
        Integer,
        nullable=True,
        comment="Average response time in milliseconds"
    )
    
    last_used_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time this configuration was used"
    )
    
    # A/B Testing support
    ab_test_group = Column(
        String(50),
        nullable=True,
        comment="A/B test group identifier"
    )
    
    ab_test_percentage = Column(
        Integer,
        nullable=True,
        comment="Percentage of traffic for A/B testing"
    )
    
    ab_test_start_date = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="A/B test start date"
    )
    
    ab_test_end_date = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="A/B test end date"
    )
    
    # Configuration inheritance
    parent_config_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_agent_configs.id"),
        nullable=True,
        comment="Parent configuration for inheritance"
    )
    
    inheritance_rules = Column(
        JSON,
        nullable=True,
        comment="Rules for inheriting from parent configuration"
    )
    
    # Monitoring and alerts
    monitoring_enabled = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether to monitor this configuration"
    )
    
    alert_thresholds = Column(
        JSON,
        nullable=True,
        comment="Thresholds for triggering alerts"
    )
    
    performance_metrics = Column(
        JSON,
        nullable=True,
        comment="Performance metrics and benchmarks"
    )
    
    # Lifecycle management
    created_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="User who created this configuration"
    )
    
    approved_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="User who approved this configuration"
    )
    
    approved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When configuration was approved"
    )
    
    deprecated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When configuration was deprecated"
    )
    
    deprecation_reason = Column(
        Text,
        nullable=True,
        comment="Reason for deprecating this configuration"
    )
    
    # Change tracking
    change_log = Column(
        JSON,
        nullable=True,
        comment="Log of changes made to this configuration"
    )
    
    tags = Column(
        JSON,
        nullable=True,
        comment="Tags for organizing and searching configurations"
    )
    
    # Relationships
    parent_config = relationship(
        "AIAgentConfig",
        remote_side="AIAgentConfig.id",
        backref="child_configs"
    )
    
    created_by = relationship(
        "User",
        foreign_keys=[created_by_id]
    )
    
    approved_by = relationship(
        "User",
        foreign_keys=[approved_by_id]
    )
    
    def __repr__(self):
        return f"<AIAgentConfig(id={self.id}, agent_type={self.agent_type}, version={self.version}, active={self.is_active})>"
    
    @property
    def is_deprecated(self) -> bool:
        """Check if configuration is deprecated"""
        return self.deprecated_at is not None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100.0
    
    @property
    def is_ab_test_active(self) -> bool:
        """Check if A/B test is currently active"""
        if not self.ab_test_start_date or not self.ab_test_end_date:
            return False
        
        now = datetime.now(timezone.utc)
        return (
            self.ab_test_start_date.replace(tzinfo=timezone.utc) <= now <= 
            self.ab_test_end_date.replace(tzinfo=timezone.utc)
        )
    
    @property
    def cost_per_day_usd(self) -> Optional[float]:
        """Estimate daily cost based on usage"""
        if not self.cost_per_request_usd or self.total_requests == 0:
            return None
        
        if not self.created_at:
            return None
        
        age_days = (datetime.now(timezone.utc) - self.created_at.replace(tzinfo=timezone.utc)).days
        if age_days == 0:
            age_days = 1
        
        daily_requests = self.total_requests / age_days
        return daily_requests * float(self.cost_per_request_usd)
    
    def get_effective_config(self) -> Dict[str, Any]:
        """Get effective configuration including inherited values"""
        config = {
            "agent_type": self.agent_type.value,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "model_parameters": self.model_parameters or {},
            "system_prompt": self.system_prompt,
            "prompt_template": self.prompt_template,
            "temperature": float(self.temperature),
            "max_tokens": self.max_tokens,
            "timeout_seconds": self.timeout_seconds,
            "retry_attempts": self.retry_attempts,
            "confidence_threshold": float(self.confidence_threshold),
            "content_filters": self.content_filters or {},
            "safety_settings": self.safety_settings or {},
        }
        
        # Apply inheritance if configured
        if self.parent_config and self.inheritance_rules:
            parent_config = self.parent_config.get_effective_config()
            config = self._merge_inherited_config(parent_config, config)
        
        return config
    
    def _merge_inherited_config(self, parent_config: Dict[str, Any], child_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge parent and child configurations based on inheritance rules"""
        merged = parent_config.copy()
        
        inheritance_rules = self.inheritance_rules or {}
        
        for key, value in child_config.items():
            if value is not None:  # Child overrides parent if value is provided
                if key in inheritance_rules:
                    rule = inheritance_rules[key]
                    if rule == "merge" and isinstance(value, dict):
                        # Merge dictionaries
                        merged[key] = {**merged.get(key, {}), **value}
                    elif rule == "append" and isinstance(value, list):
                        # Append lists
                        merged[key] = merged.get(key, []) + value
                    else:
                        # Override
                        merged[key] = value
                else:
                    merged[key] = value
        
        return merged
    
    def record_usage(self, success: bool, response_time_ms: int):
        """Record usage statistics"""
        self.total_requests += 1
        self.last_used_at = datetime.now(timezone.utc)
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # Update average response time
        if self.average_response_time_ms:
            # Weighted average
            total_time = (self.average_response_time_ms * (self.total_requests - 1)) + response_time_ms
            self.average_response_time_ms = int(total_time / self.total_requests)
        else:
            self.average_response_time_ms = response_time_ms
    
    def activate(self):
        """Activate this configuration"""
        self.is_active = True
        
        # Deactivate other configurations of the same type in same environment
        # Note: This would typically be done at the service layer
    
    def deactivate(self):
        """Deactivate this configuration"""
        self.is_active = False
    
    def deprecate(self, reason: str, user_id: Optional[str] = None):
        """Deprecate this configuration"""
        self.deprecated_at = datetime.now(timezone.utc)
        self.deprecation_reason = reason
        self.is_active = False
        
        # Log the change
        change_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "deprecated",
            "reason": reason,
            "user_id": user_id
        }
        
        if self.change_log:
            self.change_log.append(change_entry)
        else:
            self.change_log = [change_entry]
    
    def approve(self, user_id: str):
        """Approve this configuration for use"""
        self.approved_by_id = user_id
        self.approved_at = datetime.now(timezone.utc)
        
        # Log the change
        change_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "approved",
            "user_id": user_id
        }
        
        if self.change_log:
            self.change_log.append(change_entry)
        else:
            self.change_log = [change_entry]
    
    def clone_for_ab_test(self, test_name: str, percentage: int, modifications: Dict[str, Any]) -> 'AIAgentConfig':
        """Clone configuration for A/B testing"""
        cloned = AIAgentConfig(
            agent_type=self.agent_type,
            name=f"{self.name} - A/B Test: {test_name}",
            version=f"{self.version}-ab-{test_name}",
            description=f"A/B test variant of {self.name}",
            environment=self.environment,
            model_provider=self.model_provider,
            model_name=self.model_name,
            model_parameters=self.model_parameters,
            system_prompt=self.system_prompt,
            prompt_template=self.prompt_template,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout_seconds=self.timeout_seconds,
            retry_attempts=self.retry_attempts,
            confidence_threshold=self.confidence_threshold,
            ab_test_group=test_name,
            ab_test_percentage=percentage,
            parent_config_id=self.id
        )
        
        # Apply modifications
        for key, value in modifications.items():
            if hasattr(cloned, key):
                setattr(cloned, key, value)
        
        return cloned
    
    def to_dict(self, include_sensitive: bool = False, include_stats: bool = True) -> dict:
        """
        Convert configuration to dictionary.
        
        Args:
            include_sensitive: Include sensitive configuration data
            include_stats: Include usage statistics
            
        Returns:
            dict: Configuration data
        """
        data = super().to_dict()
        
        # Remove sensitive data if not requested
        if not include_sensitive:
            sensitive_fields = [
                'model_parameters', 'safety_settings', 'content_filters',
                'daily_budget_usd', 'monthly_budget_usd'
            ]
            for field in sensitive_fields:
                data.pop(field, None)
        
        # Remove stats if not requested
        if not include_stats:
            stats_fields = [
                'total_requests', 'successful_requests', 'failed_requests',
                'average_response_time_ms'
            ]
            for field in stats_fields:
                data.pop(field, None)
        
        # Add computed properties
        data['is_deprecated'] = self.is_deprecated
        data['success_rate'] = round(self.success_rate, 2)
        data['is_ab_test_active'] = self.is_ab_test_active
        data['cost_per_day_usd'] = self.cost_per_day_usd
        
        return data