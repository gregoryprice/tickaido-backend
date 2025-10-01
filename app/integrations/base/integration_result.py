#!/usr/bin/env python3
"""
Integration Result Classes
Standardized result classes for integration operations
"""

from typing import Any, Dict


class IntegrationTestResult:
    """
    Standardized test result helper class
    """
    
    @staticmethod
    def success(message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a successful test result"""
        return {
            "success": True,
            "message": message,
            "details": details or {}
        }
    
    @staticmethod
    def failure(message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a failed test result"""
        return {
            "success": False,
            "message": message,
            "details": details or {}
        }


class IntegrationTicketResult:
    """
    Standardized ticket creation result helper class
    """
    
    @staticmethod
    def success(
        external_ticket_id: str,
        external_ticket_url: str,
        details: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a successful ticket creation result"""
        return {
            "success": True,
            "external_ticket_id": external_ticket_id,
            "external_ticket_url": external_ticket_url,
            "details": details or {}
        }
    
    @staticmethod
    def failure(error_message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a failed ticket creation result"""
        return {
            "success": False,
            "external_ticket_id": None,
            "external_ticket_url": None,
            "error_message": error_message,
            "details": details or {}
        }