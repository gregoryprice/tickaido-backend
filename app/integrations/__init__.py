#!/usr/bin/env python3
"""
Integration modules
Contains all third-party integration services and interfaces
"""

# Import base classes for external use
from .base import IntegrationInterface, IntegrationTestResult, IntegrationTicketResult

# Import specific integrations
from .jira import JiraIntegration, JiraAttachmentService

__all__ = [
    # Base integration classes
    "IntegrationInterface",
    "IntegrationTestResult", 
    "IntegrationTicketResult",
    # JIRA integration
    "JiraIntegration",
    "JiraAttachmentService"
]
