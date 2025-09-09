"""
JWT Token Service for MCP Tools
Provides a simple service for storing and retrieving JWT tokens for MCP tool authentication
"""

import logging
from typing import Optional, Dict
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MCPTokenService:
    """
    Service for managing JWT tokens for MCP tool authentication.
    
    Since FastMCP doesn't support passing HTTP context to individual tool calls,
    this service provides a way for MCP tools to access JWT tokens for backend API calls.
    """
    
    def __init__(self):
        self._tokens: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._session_tokens: Dict[str, str] = {}
    
    def store_session_token(self, session_id: str, jwt_token: str) -> None:
        """
        Store JWT token for a specific MCP session.
        
        Args:
            session_id: MCP session ID
            jwt_token: JWT token for authentication
        """
        with self._lock:
            self._session_tokens[session_id] = jwt_token
            logger.info(f"Stored JWT token for MCP session {session_id}")
    
    def get_session_token(self, session_id: str) -> Optional[str]:
        """
        Retrieve JWT token for a specific MCP session.
        
        Args:
            session_id: MCP session ID
            
        Returns:
            JWT token if available, None otherwise
        """
        with self._lock:
            return self._session_tokens.get(session_id)
    
    def store_global_token(self, jwt_token: str) -> None:
        """
        Store global JWT token (fallback for when session ID is not available).
        
        Args:
            jwt_token: JWT token for authentication
        """
        with self._lock:
            self._tokens['global'] = jwt_token
            self._tokens['timestamp'] = datetime.now(timezone.utc).isoformat()
            logger.info("Stored global JWT token for MCP tools")
    
    def get_global_token(self) -> Optional[str]:
        """
        Retrieve global JWT token.
        
        Returns:
            JWT token if available, None otherwise
        """
        with self._lock:
            return self._tokens.get('global')
    
    def get_token_for_request(self, session_id: Optional[str] = None) -> Optional[str]:
        """
        Get JWT token for a tool request, trying session-specific first, then global.
        
        Args:
            session_id: MCP session ID (optional)
            
        Returns:
            JWT token if available, None otherwise
        """
        if session_id:
            token = self.get_session_token(session_id)
            if token:
                return token
        
        return self.get_global_token()
    
    def clear_session(self, session_id: str) -> None:
        """
        Clear JWT token for a specific session.
        
        Args:
            session_id: MCP session ID
        """
        with self._lock:
            if session_id in self._session_tokens:
                del self._session_tokens[session_id]
                logger.info(f"Cleared JWT token for MCP session {session_id}")
    
    def clear_all(self) -> None:
        """Clear all stored JWT tokens."""
        with self._lock:
            self._tokens.clear()
            self._session_tokens.clear()
            logger.info("Cleared all JWT tokens")
    
    def get_auth_headers(self, session_id: Optional[str] = None) -> Dict[str, str]:
        """
        Get authentication headers for backend API calls.
        
        Args:
            session_id: MCP session ID (optional)
            
        Returns:
            Dict with Authorization header if token available, empty dict otherwise
        """
        token = self.get_token_for_request(session_id)
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}


# Global token service instance
token_service = MCPTokenService()