#!/usr/bin/env python3
"""
JIRA integration module
Contains JIRA-specific integration and attachment services
"""

from .jira_integration import JiraIntegration
from .jira_attachment_service import JiraAttachmentService, AttachmentResult, AttachmentSummary

__all__ = [
    "JiraIntegration",
    "JiraAttachmentService",
    "AttachmentResult",
    "AttachmentSummary"
]
