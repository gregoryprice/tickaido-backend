#!/usr/bin/env python3
"""
Integration model for third-party service connections
"""

import enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum as SQLEnum, JSON, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.services.encryption_service import get_encryption_service, mask_credentials


class IntegrationCategory(enum.Enum):
    """Integration categories based on functionality"""
    TICKETING = "ticketing"
    CRM = "crm"
    MESSAGING = "messaging"
    COMMUNICATION = "communication"
    PROJECT_MANAGEMENT = "project_management"
    CODE_REPOSITORY = "code_repository"
    WEBHOOK = "webhook"


class IntegrationStatus(enum.Enum):
    """Integration connection status"""
    ACTIVE = "active"
    INACTIVE = "inactive" 
    PENDING = "pending"
    ERROR = "error"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class Integration(BaseModel):
    """
    Integration configuration for third-party services.
    Manages connections, credentials, and routing rules.
    """
    
    __tablename__ = "integrations"
    
    # Basic integration information
    name = Column(
        String(255),
        nullable=False,
        comment="Display name for the integration"
    )
    
    integration_category = Column(
        SQLEnum(IntegrationCategory, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
        comment="Functional category of the integration"
    )
    
    platform_name = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Name of the integration platform (jira, slack, etc.)"
    )
    
    status = Column(
        SQLEnum(IntegrationStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=IntegrationStatus.PENDING,
        nullable=False,
        index=True,
        comment="Current integration status"
    )
    
    enabled = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether the integration is enabled for use"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Description of integration purpose"
    )
    
    # Connection configuration
    base_url = Column(
        String(500),
        nullable=True,
        comment="Base URL for API endpoints"
    )
    
    api_version = Column(
        String(20),
        nullable=True,
        comment="API version being used"
    )
    
    # Authentication configuration
    auth_type = Column(
        String(50),
        nullable=False,
        default="api_key",
        comment="Authentication type (api_key, oauth2, basic, bearer)"
    )
    
    credentials_encrypted = Column(
        Text,
        nullable=True,
        comment="Encrypted authentication credentials (base64 encoded)"
    )
    
    oauth_scopes = Column(
        JSON,
        nullable=True,
        comment="OAuth scopes if using OAuth authentication"
    )
    
    # Connection health
    last_health_check_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last health check timestamp"
    )
    
    health_check_status = Column(
        String(20),
        nullable=True,
        comment="Last health check result (healthy, unhealthy, unknown)"
    )
    
    health_check_error = Column(
        Text,
        nullable=True,
        comment="Error message from last health check"
    )
    
    connection_test_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of connection tests performed"
    )
    
    # Usage tracking
    total_requests = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total API requests made"
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
    
    last_request_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last API request"
    )
    
    last_success_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last successful request"
    )
    
    last_error_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last error"
    )
    
    last_error_message = Column(
        Text,
        nullable=True,
        comment="Last error message"
    )
    
    # Rate limiting
    rate_limit_per_hour = Column(
        Integer,
        nullable=True,
        comment="Rate limit requests per hour"
    )
    
    current_hour_requests = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Requests made in current hour"
    )
    
    rate_limit_reset_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When rate limit counter resets"
    )
    
    # Routing configuration
    routing_rules = Column(
        JSON,
        nullable=True,
        comment="Rules for when to use this integration"
    )
    
    default_priority = Column(
        Integer,
        default=100,
        nullable=False,
        comment="Priority for routing (lower = higher priority)"
    )
    
    supports_categories = Column(
        JSON,
        nullable=True,
        comment="List of ticket categories this integration supports"
    )
    
    supports_priorities = Column(
        JSON,
        nullable=True,
        comment="List of ticket priorities this integration supports"
    )
    
    department_mapping = Column(
        JSON,
        nullable=True,
        comment="Mapping of internal departments to integration teams/queues"
    )
    
    # Integration-specific configuration
    custom_fields_mapping = Column(
        JSON,
        nullable=True,
        comment="Mapping of internal fields to integration fields"
    )
    
    webhook_url = Column(
        String(500),
        nullable=True,
        comment="Webhook URL for receiving events"
    )
    
    webhook_secret_encrypted = Column(
        Text,
        nullable=True,
        comment="Encrypted webhook authentication secret"
    )
    
    sync_enabled = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether to sync data bidirectionally"
    )
    
    sync_frequency_minutes = Column(
        Integer,
        default=60,
        nullable=False,
        comment="Sync frequency in minutes"
    )
    
    last_sync_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful sync timestamp"
    )
    
    # Notification configuration
    notification_events = Column(
        JSON,
        nullable=True,
        comment="Events that should trigger notifications"
    )
    
    notification_channels = Column(
        JSON,
        nullable=True,
        comment="Channels for sending notifications"
    )
    
    # Environment and deployment
    environment = Column(
        String(50),
        default="production",
        nullable=False,
        comment="Environment (production, staging, development)"
    )
    
    region = Column(
        String(50),
        nullable=True,
        comment="Service region if applicable"
    )
    
    # Monitoring and alerting
    monitoring_enabled = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether to monitor this integration"
    )
    
    alert_on_failure = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether to send alerts on failures"
    )
    
    failure_threshold = Column(
        Integer,
        default=5,
        nullable=False,
        comment="Number of failures before alerting"
    )
    
    consecutive_failures = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Current consecutive failure count"
    )
    
    # Maintenance and lifecycle
    maintenance_window_start = Column(
        String(10),
        nullable=True,
        comment="Maintenance window start time (HH:MM UTC)"
    )
    
    maintenance_window_end = Column(
        String(10),
        nullable=True,
        comment="Maintenance window end time (HH:MM UTC)"
    )
    
    auto_disable_on_error = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether to auto-disable on repeated errors"
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When integration credentials expire"
    )
    
    # Activation tracking
    last_activation_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When integration was last activated"
    )
    
    activation_method = Column(
        String(20),
        nullable=True,
        comment="How integration was activated (manual, automatic)"
    )
    
    # Organization relationship
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey('organizations.id'),
        nullable=True,  # Allow null during migration
        index=True,
        comment="Organization/company this integration belongs to"
    )
    
    # Relationships
    organization = relationship(
        "Organization",
        back_populates="integrations"
    )
    
    tickets = relationship(
        "Ticket",
        back_populates="integration"
    )
    
    def __repr__(self):
        return f"<Integration(id={self.id}, name={self.name}, type={self.integration_type}, status={self.status})>"
    
    @property
    def is_healthy(self) -> bool:
        """Check if integration is healthy"""
        return (
            self.status == IntegrationStatus.ACTIVE and 
            self.health_check_status == "healthy"
        )
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100.0
    
    @property
    def is_rate_limited(self) -> bool:
        """Check if currently rate limited"""
        if not self.rate_limit_per_hour or not self.rate_limit_reset_at:
            return False
        
        now = datetime.now(timezone.utc)
        if now > self.rate_limit_reset_at.replace(tzinfo=timezone.utc):
            return False  # Rate limit has reset
        
        return self.current_hour_requests >= self.rate_limit_per_hour
    
    @property
    def is_expired(self) -> bool:
        """Check if integration credentials are expired"""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)
    
    @property
    def in_maintenance_window(self) -> bool:
        """Check if currently in maintenance window"""
        if not self.maintenance_window_start or not self.maintenance_window_end:
            return False
        
        now = datetime.now(timezone.utc)
        current_time = now.strftime("%H:%M")
        
        return self.maintenance_window_start <= current_time <= self.maintenance_window_end
    
    def record_request(self, success: bool, error_message: Optional[str] = None):
        """Record an API request attempt"""
        now = datetime.now(timezone.utc)
        
        self.total_requests += 1
        self.last_request_at = now
        
        # Reset rate limit counter if needed
        if (not self.rate_limit_reset_at or 
            now > self.rate_limit_reset_at.replace(tzinfo=timezone.utc)):
            self.current_hour_requests = 0
            self.rate_limit_reset_at = now.replace(minute=0, second=0, microsecond=0)
        
        self.current_hour_requests += 1
        
        if success:
            self.successful_requests += 1
            self.last_success_at = now
            self.consecutive_failures = 0
        else:
            self.failed_requests += 1
            self.last_error_at = now
            self.last_error_message = error_message
            self.consecutive_failures += 1
            
            # Auto-disable if configured and threshold reached
            if (self.auto_disable_on_error and 
                self.consecutive_failures >= self.failure_threshold):
                self.status = IntegrationStatus.ERROR
    
    def update_health_check(self, healthy: bool, error_message: Optional[str] = None):
        """Update health check status"""
        self.last_health_check_at = datetime.now(timezone.utc)
        self.health_check_status = "healthy" if healthy else "unhealthy"
        self.health_check_error = error_message if not healthy else None
        self.connection_test_count += 1
        
        # Update integration status based on health
        if healthy and self.status == IntegrationStatus.ERROR:
            self.status = IntegrationStatus.ACTIVE
        elif not healthy and self.status == IntegrationStatus.ACTIVE:
            self.consecutive_failures += 1
    
    def can_handle_ticket(self, category: str, priority: str, department: str) -> bool:
        """Check if integration can handle a specific ticket"""
        if not self.enabled or self.status != IntegrationStatus.ACTIVE or not self.is_healthy:
            return False
        
        if self.in_maintenance_window:
            return False
        
        if self.is_rate_limited:
            return False
        
        # Check category support
        if (self.supports_categories and 
            category not in self.supports_categories):
            return False
        
        # Check priority support
        if (self.supports_priorities and 
            priority not in self.supports_priorities):
            return False
        
        # Check department mapping
        if (self.department_mapping and 
            department not in self.department_mapping):
            return False
        
        return True
    
    def get_routing_priority(self, ticket_data: Dict[str, Any]) -> int:
        """Get routing priority for a specific ticket"""
        base_priority = self.default_priority
        
        # Apply routing rules if configured
        if self.routing_rules:
            for rule in self.routing_rules:
                if self._matches_rule(ticket_data, rule):
                    base_priority += rule.get("priority_adjustment", 0)
        
        return base_priority
    
    def _matches_rule(self, ticket_data: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """Check if ticket matches a routing rule"""
        conditions = rule.get("conditions", [])
        
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator", "equals")
            value = condition.get("value")
            
            ticket_value = ticket_data.get(field)
            
            if operator == "equals" and ticket_value != value:
                return False
            elif operator == "contains" and value not in str(ticket_value):
                return False
            elif operator == "in" and ticket_value not in value:
                return False
        
        return True
    
    def set_enabled(self, enabled: bool, reason: Optional[str] = None):
        """
        Set enabled status and automatically manage integration status.
        
        Args:
            enabled: Whether to enable or disable the integration
            reason: Optional reason for the status change
        """
        self.enabled = enabled
        
        if enabled:
            # When enabling, set to ACTIVE (if healthy) or PENDING
            if self.is_healthy:
                self.status = IntegrationStatus.ACTIVE
            else:
                self.status = IntegrationStatus.PENDING
            self.last_activation_at = datetime.now(timezone.utc)
            self.activation_method = "enabled"
        else:
            # When disabling, set to INACTIVE
            self.status = IntegrationStatus.INACTIVE
            if reason:
                self.last_error_message = f"Disabled: {reason}"
                self.last_error_at = datetime.now(timezone.utc)

    def activate(self, method: str = "manual"):
        """Activate the integration"""
        self.enabled = True
        self.status = IntegrationStatus.ACTIVE
        self.consecutive_failures = 0
        self.health_check_error = None
        self.last_activation_at = datetime.now(timezone.utc)
        self.activation_method = method
    
    def deactivate(self, reason: Optional[str] = None):
        """Deactivate the integration"""
        self.status = IntegrationStatus.INACTIVE
        if reason:
            self.last_error_message = reason
            self.last_error_at = datetime.now(timezone.utc)
    
    def suspend(self, reason: Optional[str] = None):
        """Suspend the integration temporarily"""
        self.status = IntegrationStatus.SUSPENDED
        if reason:
            self.last_error_message = reason
            self.last_error_at = datetime.now(timezone.utc)
    
    # Credential management methods
    def set_credentials(self, credentials: Dict[str, Any]):
        """
        Set and encrypt credentials for the integration.
        
        Args:
            credentials: Dictionary containing sensitive credentials
        """
        if not credentials:
            self.credentials_encrypted = None
            return
        
        encryption_service = get_encryption_service()
        self.credentials_encrypted = encryption_service.encrypt_credentials(credentials)
    
    def get_credentials(self) -> Dict[str, Any]:
        """
        Get decrypted credentials for the integration.
        
        Returns:
            Dict[str, Any]: Decrypted credentials dictionary
        """
        if not self.credentials_encrypted:
            return {}
        
        encryption_service = get_encryption_service()
        return encryption_service.decrypt_credentials(self.credentials_encrypted)
    
    def get_masked_credentials(self) -> Dict[str, Any]:
        """
        Get credentials with sensitive values masked for safe display.
        
        Returns:
            Dict[str, Any]: Credentials with masked sensitive values
        """
        credentials = self.get_credentials()
        return mask_credentials(credentials)
    
    def set_webhook_secret(self, secret: str):
        """
        Set and encrypt webhook secret.
        
        Args:
            secret: Webhook secret to encrypt
        """
        if not secret:
            self.webhook_secret_encrypted = None
            return
        
        encryption_service = get_encryption_service()
        self.webhook_secret_encrypted = encryption_service.encrypt_data(secret)
    
    def get_webhook_secret(self) -> Optional[str]:
        """
        Get decrypted webhook secret.
        
        Returns:
            str: Decrypted webhook secret or None
        """
        if not self.webhook_secret_encrypted:
            return None
        
        encryption_service = get_encryption_service()
        return encryption_service.decrypt_data(self.webhook_secret_encrypted)
    
    def has_valid_credentials(self) -> bool:
        """
        Check if integration has valid credentials for its auth type.
        
        Returns:
            bool: True if credentials are valid for the auth type
        """
        credentials = self.get_credentials()
        if not credentials:
            return False
        
        # Check based on auth type
        if self.auth_type == "api_key":
            return "api_key" in credentials and credentials["api_key"]
        elif self.auth_type == "oauth2":
            return all(k in credentials for k in ["client_id", "client_secret"])
        elif self.auth_type == "basic":
            return all(k in credentials for k in ["username", "password"]) or \
                   all(k in credentials for k in ["email", "api_token"])  # JIRA style
        elif self.auth_type == "bearer":
            return "token" in credentials and credentials["token"]
        
        return True  # For custom auth types
    
    @classmethod
    def get_category_for_platform(cls, platform_name: str) -> Optional[IntegrationCategory]:
        """
        Get the integration category for a given platform name.
        
        Args:
            platform_name: Platform name (e.g., 'jira', 'slack')
            
        Returns:
            IntegrationCategory or None if not found
        """
        platform_mapping = {
            'jira': IntegrationCategory.TICKETING,
            'servicenow': IntegrationCategory.TICKETING,
            'zendesk': IntegrationCategory.TICKETING,
            'freshdesk': IntegrationCategory.TICKETING,
            'salesforce': IntegrationCategory.CRM,
            'hubspot': IntegrationCategory.CRM,
            'slack': IntegrationCategory.MESSAGING,
            'teams': IntegrationCategory.MESSAGING,
            'email': IntegrationCategory.COMMUNICATION,
            'sms': IntegrationCategory.COMMUNICATION,
            'zoom': IntegrationCategory.COMMUNICATION,
            'github': IntegrationCategory.CODE_REPOSITORY,
            'asana': IntegrationCategory.PROJECT_MANAGEMENT,
            'trello': IntegrationCategory.PROJECT_MANAGEMENT,
            'webhook': IntegrationCategory.WEBHOOK,
        }
        return platform_mapping.get(platform_name.lower())
    
    
    def to_dict(self, include_credentials: bool = False, include_stats: bool = True) -> dict:
        """
        Convert integration to dictionary with optional credential inclusion.
        
        Args:
            include_credentials: Include authentication credentials (masked for safety)
            include_stats: Include usage statistics
            
        Returns:
            dict: Integration data
        """
        data = super().to_dict()
        
        # Always remove encrypted fields from output
        sensitive_fields = [
            'credentials_encrypted', 'webhook_secret_encrypted'
        ]
        for field in sensitive_fields:
            data.pop(field, None)
        
        # Handle credentials based on request
        if include_credentials:
            # Include masked credentials for display
            data['credentials'] = self.get_masked_credentials()
            data['has_webhook_secret'] = bool(self.webhook_secret_encrypted)
        else:
            # Remove any credential information
            data.pop('credentials', None)
        
        # Remove stats if not requested
        if not include_stats:
            stats_fields = [
                'total_requests', 'successful_requests', 'failed_requests',
                'current_hour_requests', 'connection_test_count'
            ]
            for field in stats_fields:
                data.pop(field, None)
        
        # Add computed properties
        data['is_healthy'] = self.is_healthy
        data['success_rate'] = round(self.success_rate, 2)
        data['is_rate_limited'] = self.is_rate_limited
        data['is_expired'] = self.is_expired
        data['in_maintenance_window'] = self.in_maintenance_window
        data['has_valid_credentials'] = self.has_valid_credentials()
        
        return data