#!/usr/bin/env python3
"""
Comment schemas for ticket comment management with generic integration platform support
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CommentCreate(BaseModel):
    """Schema for creating a new comment"""
    
    body: str = Field(
        ...,
        description="Comment content (supports text and markdown)",
        min_length=1,
        max_length=10000
    )
    is_internal: bool = Field(
        default=False,
        description="Whether comment is internal-only or visible to customers"
    )
    
    @field_validator('body')
    @classmethod
    def validate_body(cls, v: str) -> str:
        """Validate and clean content"""
        if not v or not v.strip():
            raise ValueError("Comment body cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "body": "This is a **markdown** comment with [links](https://example.com) and `code`",
                "is_internal": False
            }
        }


class CommentUpdate(BaseModel):
    """Schema for updating an existing comment"""
    
    body: Optional[str] = Field(
        None,
        description="Updated comment content (supports text and markdown)",
        min_length=1,
        max_length=10000
    )
    is_internal: Optional[bool] = Field(
        None,
        description="Whether comment is internal-only or visible to customers"
    )
    
    @field_validator('body')
    @classmethod
    def validate_body(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean content"""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Comment body cannot be empty")
        return v.strip() if v else v

    class Config:
        json_schema_extra = {
            "example": {
                "body": "Updated **markdown** content",
                "is_internal": True
            }
        }


class CommentAuthor(BaseModel):
    """Schema for comment author data"""
    
    id: Optional[UUID] = Field(None, description="User ID")
    email: str = Field(..., description="User email")
    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")
    full_name: Optional[str] = Field(None, description="User full name")
    image_url: Optional[str] = Field(None, description="User profile image URL")
    has_image: Optional[bool] = Field(None, description="Whether user has profile image")
    identifier: str = Field(..., description="User identifier (usually email)")
    username: Optional[str] = Field(None, description="Username")
    profile_image_url: Optional[str] = Field(None, description="Profile image URL")


class CommentResponse(BaseModel):
    """Schema for comment response data"""
    
    id: UUID = Field(..., description="Unique comment identifier")
    ticket_id: UUID = Field(..., description="ID of the parent ticket")
    author: CommentAuthor = Field(..., description="Comment author information")
    body: str = Field(..., description="Comment content (supports text and markdown)")
    body_html: str = Field(..., description="Rendered HTML version of content")
    body_plain_text: str = Field(..., description="Plain text version without markdown syntax")
    created_at: datetime = Field(..., description="Timestamp when comment was created")
    updated_at: datetime = Field(..., description="Timestamp when comment was last updated")
    external_comment_id: Optional[str] = Field(None, description="External platform comment ID for synchronization")
    integration_id: Optional[UUID] = Field(None, description="Integration platform this comment was synchronized with")
    is_internal: bool = Field(..., description="Whether comment is internal-only")
    is_synchronized: bool = Field(..., description="Whether comment is synchronized with external platform")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "ticket_id": "123e4567-e89b-12d3-a456-426614174001",
                "author": {
                    "id": "123e4567-e89b-12d3-a456-426614174003",
                    "email": "user@company.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "full_name": "John Doe",
                    "image_url": "https://example.com/avatar.jpg",
                    "has_image": True,
                    "identifier": "user@company.com",
                    "username": None,
                    "profile_image_url": "https://example.com/profile.jpg"
                },
                "body": "This is a **markdown** comment",
                "body_html": "<p>This is a <strong>markdown</strong> comment</p>",
                "body_plain_text": "This is a markdown comment",
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z",
                "external_comment_id": "10001",
                "integration_id": "123e4567-e89b-12d3-a456-426614174002",
                "is_internal": False,
                "is_synchronized": True
            }
        }


class CommentListResponse(BaseModel):
    """Schema for paginated comment list response"""
    
    comments: list[CommentResponse] = Field(..., description="List of comments")
    total: int = Field(..., description="Total number of comments")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of comments per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")

    class Config:
        json_schema_extra = {
            "example": {
                "comments": [],
                "total": 25,
                "page": 1,
                "per_page": 10,
                "has_next": True,
                "has_prev": False
            }
        }


def markdown_to_html(markdown_content: str) -> str:
    """
    Convert markdown to HTML with support for common extensions.
    
    Args:
        markdown_content: Markdown formatted text
        
    Returns:
        HTML string representation
    """
    if not markdown_content or not markdown_content.strip():
        return ""
    
    try:
        import markdown
        html = markdown.markdown(
            markdown_content,
            extensions=[
                'extra',        # Tables, fenced code blocks, footnotes, etc.
                'codehilite',   # Syntax highlighting for code blocks
                'toc',          # Table of contents
                'tables',       # Table support
                'nl2br'         # Newline to <br> conversion
            ],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'use_pygments': True
                }
            }
        )
        return html.strip()
    except ImportError:
        # Fallback if markdown library not available
        import html
        return f"<p>{html.escape(markdown_content)}</p>"
    except Exception:
        # Fallback for any conversion errors
        import html
        return f"<pre>{html.escape(markdown_content)}</pre>"


def markdown_to_plain_text(markdown_content: str) -> str:
    """
    Convert markdown to plain text by removing markdown syntax.
    
    Args:
        markdown_content: Markdown formatted text
        
    Returns:
        Plain text string
    """
    if not markdown_content or not markdown_content.strip():
        return ""
    
    try:
        import re
        # Basic markdown removal - remove common markdown syntax
        text = markdown_content
        # Remove headers
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # Remove bold/italic
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)
        text = re.sub(r'_(.*?)_', r'\1', text)
        # Remove links but keep link text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Remove images
        text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        # Remove horizontal rules
        text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)
        # Remove list markers
        text = re.sub(r'^\s*[\*\-\+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        # Clean up extra whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)
        return text.strip()
    except Exception:
        # Fallback
        return markdown_content.strip()


def markdown_to_integration_format(markdown_content: str, platform: str) -> Dict[str, Any]:
    """
    Convert markdown to platform-specific format (e.g., ADF for JIRA).
    
    Args:
        markdown_content: Markdown formatted text
        platform: Integration platform name (jira, servicenow, etc.)
        
    Returns:
        Platform-specific formatted content
    """
    if platform.lower() == "jira":
        return markdown_to_adf(markdown_content)
    else:
        # For other platforms, return markdown as-is in a generic format
        return {
            "format": "markdown",
            "content": markdown_content,
            "html": markdown_to_html(markdown_content)
        }


def markdown_to_adf(markdown_content: str) -> Dict[str, Any]:
    """
    Convert markdown to Atlassian Document Format (ADF) for JIRA.
    
    This is a basic implementation. For production, consider using a dedicated
    markdown-to-ADF converter library or enhancing this function.
    
    Args:
        markdown_content: Markdown formatted text
        
    Returns:
        ADF document structure
    """
    if not markdown_content or not markdown_content.strip():
        return {
            "type": "doc",
            "version": 1,
            "content": []
        }
    
    try:
        # Basic markdown to ADF conversion
        # This is a simplified implementation - for full markdown support,
        # consider using a dedicated markdown parser
        
        import re
        lines = markdown_content.strip().split('\n')
        adf_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Handle headers
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                level = min(level, 6)  # ADF supports h1-h6
                text = line.lstrip('#').strip()
                adf_content.append({
                    "type": "heading",
                    "attrs": {"level": level},
                    "content": [{"type": "text", "text": text}]
                })
            else:
                # Convert basic inline formatting
                text = line
                # Bold: **text** -> ADF strong
                text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
                # Italic: *text* -> ADF em  
                text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
                # Code: `text` -> ADF code
                text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
                
                # For now, create a simple paragraph with text
                # TODO: Enhanced conversion for links, lists, etc.
                adf_content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": text}]
                })
        
        return {
            "type": "doc",
            "version": 1,
            "content": adf_content
        }
        
    except Exception:
        # Fallback to simple paragraph
        return {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": markdown_content.strip()
                        }
                    ]
                }
            ]
        }