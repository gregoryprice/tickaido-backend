#!/usr/bin/env python3
"""
JIRA integration module
Contains JIRA-specific integration and attachment services
"""

from .jira_attachment_service import AttachmentResult, AttachmentSummary, JiraAttachmentService
from .jira_integration import JiraIntegration

__all__ = [
    "JiraIntegration",
    "JiraAttachmentService",
    "AttachmentResult",
    "AttachmentSummary"
]
