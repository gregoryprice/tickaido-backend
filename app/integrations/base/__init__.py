#!/usr/bin/env python3
"""
Base integration module
Contains abstract interfaces and result classes for all integrations
"""

from .integration_interface import IntegrationInterface
from .integration_result import IntegrationTestResult, IntegrationTicketResult

__all__ = [
    "IntegrationInterface",
    "IntegrationTestResult", 
    "IntegrationTicketResult"
]
