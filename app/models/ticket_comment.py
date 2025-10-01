#!/usr/bin/env python3
"""
Ticket Comment model for generic ticketing platform integration
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class TicketComment(BaseModel):
    """
    Comment model for support tickets with generic integration platform support.
    Supports markdown content with platform-specific conversion handled by integrations.
    """
    
    __tablename__ = "ticket_comments"
    
    # Foreign key to parent ticket
    ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to parent ticket"
    )
    
    # Generic external integration synchronization
    external_comment_id = Column(
        Text,
        nullable=True,
        index=True,
        comment="External platform comment ID for synchronization (JIRA, ServiceNow, etc.)"
    )
    
    integration_id = Column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id"),
        nullable=True,
        index=True,
        comment="Integration platform this comment was synchronized with"
    )
    
    # Comment author information
    author_email = Column(
        Text,
        nullable=False,
        index=True,
        comment="Email address of comment author"
    )
    
    author_display_name = Column(
        Text,
        nullable=True,
        comment="Display name of comment author"
    )
    
    # Comment content (supports text and markdown)
    body = Column(
        Text,
        nullable=False,
        comment="Comment content (supports text and markdown)"
    )
    
    body_html = Column(
        Text,
        nullable=True,
        comment="Rendered HTML version of content"
    )
    
    # Platform-specific content for integrations
    external_format_data = Column(
        JSONB,
        nullable=True,
        comment="Platform-specific formatted content (e.g., ADF for JIRA, rich text for ServiceNow)"
    )
    
    # Internal vs external visibility
    is_internal = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether comment is internal-only or visible to customers"
    )
    
    # Relationships
    ticket = relationship(
        "Ticket",
        back_populates="comments",
        foreign_keys=[ticket_id]
    )
    
    integration = relationship(
        "Integration",
        foreign_keys=[integration_id]
    )
    
    # Indexes for efficient queries (defined at class level)
    __table_args__ = (
        Index('idx_ticket_comments_ticket_id', 'ticket_id'),
        Index('idx_ticket_comments_external_id', 'external_comment_id'),
        Index('idx_ticket_comments_integration_id', 'integration_id'),
        Index('idx_ticket_comments_author_email', 'author_email'),
        Index('idx_ticket_comments_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<TicketComment(id={self.id}, ticket_id={self.ticket_id}, author={self.author_email})>"
    
    def render_html(self) -> str:
        """
        Render content to HTML.
        Uses cached HTML if available, otherwise converts content to HTML.
        """
        if self.body_html:
            return self.body_html
        
        # Convert content to HTML (supports markdown)
        try:
            import markdown
            html = markdown.markdown(
                self.body,
                extensions=['extra', 'codehilite', 'toc', 'tables']
            )
            return html
        except ImportError:
            # Fallback if markdown library not available
            return f"<p>{self.body}</p>"
        except Exception:
            # Fallback for any conversion errors
            return f"<pre>{self.body}</pre>"
    
    @property
    def body_plain_text(self) -> str:
        """
        Extract plain text from content by removing markdown syntax.
        """
        try:
            import re
            # Basic markdown removal - remove common markdown syntax
            text = self.body
            # Remove headers
            text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
            # Remove bold/italic
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
            text = re.sub(r'\*(.*?)\*', r'\1', text)
            # Remove links but keep link text
            text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
            # Remove code blocks
            text = re.sub(r'```[\s\S]*?```', '', text)
            text = re.sub(r'`([^`]+)`', r'\1', text)
            # Clean up extra whitespace
            text = re.sub(r'\n\s*\n', '\n\n', text.strip())
            return text
        except Exception:
            # Fallback
            return self.body
    
    @property
    def is_synchronized(self) -> bool:
        """Check if comment is synchronized with external integration platform"""
        return bool(self.external_comment_id and self.integration_id)
    
    @property
    def author_short_name(self) -> str:
        """Get short display name for author"""
        if self.author_display_name:
            return self.author_display_name
        # Extract name part from email
        return self.author_email.split('@')[0] if self.author_email else "Unknown"
    
    def update_content(self, content: str):
        """
        Update comment content with new text/markdown.
        Clears cached HTML to force re-rendering.
        
        Args:
            content: New content (supports text and markdown)
        """
        self.body = content.strip()
        self.body_html = None  # Clear cache to force re-render
        self.updated_at = datetime.now(timezone.utc)
    
    def cache_html(self):
        """
        Pre-render and cache HTML version of markdown content.
        """
        self.body_html = self.render_html()
    
    def sync_with_integration(
        self,
        integration_data: dict,
        external_comment_id: str,
        integration_id: str
    ):
        """
        Synchronize comment with external integration platform.
        
        Args:
            integration_data: Platform-specific comment data
            external_comment_id: External platform comment ID
            integration_id: Integration platform ID
        """
        self.external_comment_id = external_comment_id
        self.integration_id = integration_id
        self.external_format_data = integration_data
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self, include_html: bool = True, include_external_data: bool = False) -> dict:
        """
        Convert comment to dictionary with optional fields.
        
        Args:
            include_html: Whether to include rendered HTML body
            include_external_data: Whether to include platform-specific data
            
        Returns:
            dict: Comment data
        """
        data = super().to_dict()
        
        # Add computed properties
        data['body_plain_text'] = self.body_plain_text
        data['is_synchronized'] = self.is_synchronized
        data['author_short_name'] = self.author_short_name
        
        if include_html:
            data['body_html'] = self.render_html()
        
        if include_external_data and self.external_format_data:
            data['external_format_data'] = self.external_format_data
        
        return data
    
    @classmethod
    def create_from_content(
        cls,
        ticket_id: str,
        author_email: str,
        content: str,
        author_display_name: str = None,
        is_internal: bool = False,
        integration_id: str = None
    ) -> 'TicketComment':
        """
        Factory method to create comment from content (supports text and markdown).
        
        Args:
            ticket_id: UUID of the parent ticket
            author_email: Email of the comment author
            content: Comment content (supports text and markdown)
            author_display_name: Display name of the comment author
            is_internal: Whether comment is internal-only
            integration_id: Integration platform ID (optional)
            
        Returns:
            New TicketComment instance
        """
        comment = cls(
            ticket_id=ticket_id,
            author_email=author_email,
            author_display_name=author_display_name,
            body=content.strip(),
            is_internal=is_internal,
            integration_id=integration_id
        )
        
        # Pre-render HTML
        comment.cache_html()
        
        return comment