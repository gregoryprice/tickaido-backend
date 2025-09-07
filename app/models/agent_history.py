#!/usr/bin/env python3
"""
Agent History model for tracking configuration changes and agent lifecycle events
"""

from typing import Optional, Any, List
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import json

from app.models.base import BaseModel


class AgentHistory(BaseModel):
    """
    Track all changes to agent configuration and status over time.
    
    This model provides a comprehensive audit trail of agent modifications,
    enabling rollback capabilities and change analysis.
    """
    
    __tablename__ = "agent_history"
    
    # Agent relationship
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Agent this history entry belongs to"
    )
    
    # Change metadata
    changed_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="User who made the change"
    )
    
    change_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of change (configuration_update, status_change, activation, etc.)"
    )
    
    field_changed = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Field that was changed (prompt, role, is_active, etc.)"
    )
    
    # Change details
    old_value = Column(
        Text,
        nullable=True,
        comment="Previous value (JSON for complex fields)"
    )
    
    new_value = Column(
        Text,
        nullable=True,
        comment="New value (JSON for complex fields)"
    )
    
    change_timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        index=True,
        comment="When the change occurred"
    )
    
    change_reason = Column(
        Text,
        nullable=True,
        comment="Optional reason for the change"
    )
    
    ip_address = Column(
        String(45),
        nullable=True,
        comment="IP address of the request that made the change"
    )
    
    # Additional metadata
    request_metadata = Column(
        Text,
        nullable=True,
        comment="Additional request metadata (user agent, etc.)"
    )
    
    # Relationships
    agent = relationship(
        "Agent",
        back_populates="history",
        lazy="select"
    )
    
    changed_by = relationship(
        "User",
        lazy="select"
    )
    
    def __repr__(self):
        return f"<AgentHistory(id={self.id}, agent_id={self.agent_id}, field={self.field_changed}, change_type={self.change_type})>"
    
    @classmethod
    async def record_change(
        cls,
        agent_id: UUID,
        user_id: UUID,
        change_type: str,
        field_changed: str,
        old_value: Any,
        new_value: Any,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> 'AgentHistory':
        """
        Record a change to an agent.
        
        Args:
            agent_id: Agent that was changed
            user_id: User who made the change
            change_type: Type of change
            field_changed: Which field was changed
            old_value: Previous value
            new_value: New value
            reason: Optional reason for change
            ip_address: Optional IP address
            
        Returns:
            AgentHistory: Created history record
        """
        # Convert complex objects to JSON strings
        old_json = json.dumps(old_value) if not isinstance(old_value, (str, type(None))) else old_value
        new_json = json.dumps(new_value) if not isinstance(new_value, (str, type(None))) else new_value
        
        # Create history entry
        history_entry = cls(
            agent_id=agent_id,
            changed_by_user_id=user_id,
            change_type=change_type,
            field_changed=field_changed,
            old_value=old_json,
            new_value=new_json,
            change_reason=reason,
            ip_address=ip_address,
            change_timestamp=datetime.now(timezone.utc)
        )
        
        return history_entry
    
    @classmethod
    async def get_agent_history(
        cls,
        agent_id: UUID,
        limit: int = 50,
        offset: int = 0,
        change_type: Optional[str] = None,
        field_filter: Optional[str] = None
    ) -> List['AgentHistory']:
        """
        Get history for an agent with filtering options.
        
        Args:
            agent_id: Agent to get history for
            limit: Maximum number of records
            offset: Number of records to skip
            change_type: Filter by change type
            field_filter: Filter by field name
            
        Returns:
            List[AgentHistory]: History records
        """
        # This would be implemented in the service layer with async database queries
        # Placeholder for the method signature
        pass
    
    @classmethod
    async def get_field_history(
        cls,
        agent_id: UUID,
        field: str,
        limit: int = 10
    ) -> List['AgentHistory']:
        """
        Get history for a specific field of an agent.
        
        Args:
            agent_id: Agent ID
            field: Field name to get history for
            limit: Maximum number of records
            
        Returns:
            List[AgentHistory]: Field history records
        """
        # This would be implemented in the service layer
        # Useful for seeing how a specific configuration has evolved
        pass
    
    @property
    def parsed_old_value(self) -> Any:
        """Parse old_value from JSON if needed"""
        if self.old_value and self.old_value.startswith(('{', '[')):
            try:
                return json.loads(self.old_value)
            except (json.JSONDecodeError, TypeError):
                pass
        return self.old_value
    
    @property
    def parsed_new_value(self) -> Any:
        """Parse new_value from JSON if needed"""
        if self.new_value and self.new_value.startswith(('{', '[')):
            try:
                return json.loads(self.new_value)
            except (json.JSONDecodeError, TypeError):
                pass
        return self.new_value
    
    @property
    def change_summary(self) -> str:
        """Generate a human-readable summary of the change"""
        if self.change_type == "configuration_update":
            return f"Updated {self.field_changed} configuration"
        elif self.change_type == "status_change":
            return f"Changed {self.field_changed} from {self.old_value} to {self.new_value}"
        elif self.change_type == "activation":
            return "Agent activated"
        elif self.change_type == "deactivation":
            return "Agent deactivated"
        else:
            return f"{self.change_type}: {self.field_changed}"
    
    def to_dict(self, include_values: bool = True) -> dict:
        """Convert history record to dictionary"""
        data = super().to_dict()
        
        # Add computed properties
        data['change_summary'] = self.change_summary
        
        if include_values:
            data['parsed_old_value'] = self.parsed_old_value
            data['parsed_new_value'] = self.parsed_new_value
        else:
            # Remove values for privacy in some contexts
            data.pop('old_value', None)
            data.pop('new_value', None)
        
        return data