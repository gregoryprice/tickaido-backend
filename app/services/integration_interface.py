#!/usr/bin/env python3
"""
Generic Integration Interface
Abstract base class that all integrations must implement
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class IntegrationInterface(ABC):
    """
    Abstract base class that all integrations must implement.
    
    This interface ensures consistent behavior across all integration types
    and allows the integration service to work generically with any integration.
    """
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test basic connection to the integration service.
        
        Returns:
            Dict with standardized test result format:
            {
                "success": bool,
                "message": str,
                "details": Dict[str, Any]
            }
        """
        pass
    
    @abstractmethod
    async def test_authentication(self) -> Dict[str, Any]:
        """
        Test authentication credentials.
        
        Returns:
            Dict with standardized test result format:
            {
                "success": bool,
                "message": str,
                "details": Dict[str, Any]
            }
        """
        pass
    
    @abstractmethod
    async def test_permissions(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test required permissions for ticket creation.
        
        Args:
            test_data: Integration-specific test parameters (e.g., project_key for JIRA)
            
        Returns:
            Dict with standardized test result format:
            {
                "success": bool,
                "message": str,
                "details": Dict[str, Any]
            }
        """
        pass
    
    @abstractmethod
    async def create_ticket(self, ticket_data: Dict[str, Any], is_test: bool = False) -> Dict[str, Any]:
        """
        Create a ticket in the external system.
        
        Args:
            ticket_data: Normalized ticket data with fields:
                - title: str
                - description: str
                - category: str
                - priority: str
                - project_key: str (for integrations that need it)
                - issue_type: str (for integrations that need it)
                - assignee: str (optional)
                - labels: List[str] (optional)
                - custom_fields: Dict[str, Any] (optional)
                
        Returns:
            Dict with standardized creation result format:
            {
                "success": bool,
                "external_ticket_id": str,  # e.g., "PROJ-123"
                "external_ticket_url": str,  # URL to view the ticket
                "details": Dict[str, Any]  # Full API response
            }
        """
        pass
    
    @abstractmethod
    async def get_configuration_schema(self) -> Dict[str, Any]:
        """
        Get configuration schema for this integration type.
        
        Returns:
            JSON schema defining required configuration fields:
            {
                "type": "object",
                "required": List[str],
                "properties": Dict[str, Any]
            }
        """
        pass
    
    @abstractmethod
    async def close(self):
        """
        Clean up resources (close HTTP clients, etc.)
        """
        pass
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


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