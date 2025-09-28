#!/usr/bin/env python3
"""
Principal schema for secure authentication and authorization
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class SessionType(str, Enum):
    """Session type enumeration"""
    WEB = "web"
    API = "api"
    JWT = "jwt"
    MCP = "mcp"
    INTEGRATION = "integration"


class Principal(BaseModel):
    """
    Principal represents an authenticated user with full context for authorization decisions.
    This replaces raw JWT tokens in tool layer for security and auditability.
    """
    model_config = ConfigDict(frozen=True, extra='forbid')
    
    # Core Identity
    user_id: str = Field(..., description="Unique user identifier")
    organization_id: str = Field(..., description="User's organization identifier") 
    email: str = Field(..., description="User's email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    
    # Authorization Context
    roles: List[str] = Field(default_factory=list, description="User roles for RBAC")
    permissions: List[str] = Field(default_factory=list, description="Specific permissions")
    scopes: List[str] = Field(default_factory=list, description="OAuth-style scopes")
    
    # Session Context
    session_id: Optional[str] = Field(None, description="Session identifier")
    session_type: SessionType = Field(default=SessionType.WEB, description="Type of session")
    
    # Token Context
    token_issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    token_expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    jwt_payload: Dict[str, Any] = Field(default_factory=dict, description="Original JWT payload")
    api_token: Optional[str] = Field(None, description="API token for authentication (if using API key auth)")
    refresh_token: Optional[str] = Field(None, description="Refresh token for automatic token renewal")
    
    # Organization Context  
    organization_name: Optional[str] = Field(None, description="Organization name")
    organization_plan: Optional[str] = Field(None, description="Organization plan level")
    organization_role: Optional[str] = Field(None, description="User's role in organization")
    
    # Audit Context
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = Field(None, description="Last time principal was used")
    
    def has_permission(self, permission: str) -> bool:
        """Check if principal has specific permission"""
        return (
            permission in self.permissions or 
            "all" in self.permissions or
            "*" in self.permissions
        )
    
    def has_role(self, role: str) -> bool:
        """Check if principal has specific role"""
        return role in self.roles
    
    def has_scope(self, scope: str) -> bool:
        """Check if principal has specific scope"""
        return scope in self.scopes or "all" in self.scopes
    
    def can_access_tool(self, tool_name: str, context: Optional[Dict] = None) -> bool:
        """
        ABAC/RBAC logic for tool access decisions.
        This is the core authorization method used by tool filtering.
        """
        context = context or {}
        
        # Check token expiry first
        if self.is_token_expired():
            return False
        
        # Admin role gets access to everything
        if self.has_role("admin") or self.has_role("super_admin"):
            return True
        
        # Manager role gets broad access
        if self.has_role("manager"):
            # Managers can access most tools except highly sensitive ones
            highly_sensitive = {
                "delete_user", "delete_organization", "system_shutdown",
                "admin_override", "security_bypass"
            }
            if tool_name in highly_sensitive:
                return self.has_permission("admin.override")
            return True
        
        # Tool-specific permission checks
        tool_permission_map = {
            "create_ticket": ["ticket.create", "ticket.write"],
            "get_ticket": ["ticket.read", "ticket.view"],
            "update_ticket": ["ticket.update", "ticket.write"],
            "delete_ticket": ["ticket.delete", "ticket.admin"],
            "list_tickets": ["ticket.read", "ticket.list"],
            "search_tickets": ["ticket.read", "ticket.search"],
            "assign_ticket": ["ticket.assign", "ticket.manage"],
            "create_ticket_with_ai": ["ticket.create", "ai.use"],
            "get_ticket_stats": ["ticket.stats", "analytics.read"],
            "upload_file": ["file.upload", "file.create"],
            "download_file": ["file.download", "file.read"],
            "list_files": ["file.list", "file.read"],
            "delete_file": ["file.delete", "file.admin"],
        }
        
        required_permissions = tool_permission_map.get(tool_name, [])
        if not required_permissions:
            # Unknown tool - deny by default unless user has broad permissions
            return self.has_permission("tool.all") or self.has_role("developer")
        
        # Check if user has any of the required permissions
        for permission in required_permissions:
            if self.has_permission(permission):
                return True
        
        # Check role-based access for common patterns
        if self.has_role("user"):
            # Regular users can access basic read/create operations
            basic_tools = {
                "create_ticket", "get_ticket", "list_tickets", "search_tickets",
                "create_ticket_with_ai", "upload_file", "download_file", "list_files"
            }
            return tool_name in basic_tools
        
        # Default deny
        return False
    
    def is_token_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.now(timezone.utc) > self.token_expires_at
    
    def is_token_valid(self) -> bool:
        """Check if token is valid (not expired and has required fields)"""
        return (
            not self.is_token_expired() and
            bool(self.user_id) and
            bool(self.organization_id) and
            bool(self.email)
        )
    
    def update_last_used(self) -> 'Principal':
        """Update last used timestamp - returns new Principal due to immutability"""
        return self.model_copy(update={'last_used_at': datetime.now(timezone.utc)})
    
    def to_audit_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for audit logging"""
        return {
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "email": self.email,
            "roles": self.roles,
            "permissions": self.permissions,
            "scopes": self.scopes,
            "session_id": self.session_id,
            "session_type": self.session_type,
            "token_expires_at": self.token_expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Principal':
        """Create Principal from dictionary (for Redis deserialization)"""
        # Parse datetime fields
        for field in ['token_issued_at', 'token_expires_at', 'created_at', 'last_used_at']:
            if field in data and data[field]:
                if isinstance(data[field], str):
                    data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
        
        return cls(**data)
    
    def to_cache_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for caching (Redis)"""
        data = self.model_dump()
        
        # Convert datetime fields to ISO strings for JSON serialization
        for field in ['token_issued_at', 'token_expires_at', 'created_at', 'last_used_at']:
            if data.get(field):
                data[field] = data[field].isoformat()
        
        return data
    
    def get_auth_token(self) -> Optional[str]:
        """
        Get the authentication token from the principal.
        
        Returns:
            str: Auth token (API token or JWT raw token) or None if not found
        """
        # Check for API token first (for API key authentication)
        if hasattr(self, 'api_token') and self.api_token:
            return self.api_token
            
        # Check for raw JWT token in jwt_payload
        if self.jwt_payload and 'token' in self.jwt_payload:
            return self.jwt_payload['token']
        
        # Fallback to refresh_token if available (as last resort)
        if hasattr(self, 'refresh_token') and self.refresh_token:
            return self.refresh_token
            
        return None
    
    def get_cache_hash(self) -> str:
        """
        Generate a cache hash for this principal.
        
        Returns:
            str: Hash string suitable for cache keys
        """
        import hashlib
        
        # Create a stable representation for hashing
        # Include key fields that affect authorization/identity
        cache_data = {
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'roles': sorted(self.roles),
            'permissions': sorted(self.permissions),
            'session_type': self.session_type,
            'auth_token_hash': hash(self.get_auth_token()) if self.get_auth_token() else "no_auth"
        }
        
        # Create a stable string representation
        cache_string = json.dumps(cache_data, sort_keys=True)
        
        # Return a short hash
        return hashlib.md5(cache_string.encode()).hexdigest()[:16]
    
    def get_headers_for_mcp(self) -> Dict[str, str]:
        """
        Get authentication headers for MCP requests.
        
        Returns:
            Dict[str, str]: Headers dictionary with authentication tokens
        """
        auth_token = self.get_auth_token()
        if not auth_token:
            return {"Content-Type": "application/json"}
        
        return {
            "Authorization": f"Bearer {auth_token}",
            "X-API-KEY": auth_token,
            "Content-Type": "application/json"
        }
    
    async def refresh_if_needed(self) -> 'Principal':
        """
        Refresh token if needed and return updated principal.
        
        Returns:
            Principal: Updated principal with refreshed token or self if no refresh needed
        """
        try:
            # Import here to avoid circular imports
            from app.services.token_refresh_service import token_refresh_service
            
            # Check if refresh is needed
            if not token_refresh_service.should_refresh_token(self):
                return self
            
            # Attempt refresh
            refreshed_principal = await token_refresh_service.refresh_principal_token(self)
            if refreshed_principal and refreshed_principal.is_token_valid():
                return refreshed_principal
            else:
                # Return self if refresh failed (caller should handle gracefully)
                return self
                
        except Exception:
            # Return self if refresh fails (don't break the calling code)
            return self
    
    def with_refresh_callback(self, callback_fn) -> 'Principal':
        """
        Add token refresh callback support.
        
        Args:
            callback_fn: Function to call when token is refreshed
            
        Returns:
            Principal: Principal with refresh callback attached
        """
        # Store callback in jwt_payload for now (could be improved with a proper callback registry)
        updated_payload = self.jwt_payload.copy()
        updated_payload['_refresh_callback'] = callback_fn
        
        return self.model_copy(update={'jwt_payload': updated_payload})
    
    def get_refresh_callback(self):
        """
        Get the refresh callback function if set.
        
        Returns:
            Function or None: Refresh callback function
        """
        return self.jwt_payload.get('_refresh_callback')


class MCPAuthContext(BaseModel):
    """Context object passed to MCP tools for authentication"""
    model_config = ConfigDict(frozen=True)
    
    principal: Principal
    tool_name: str
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def is_authorized(self) -> bool:
        """Check if principal is authorized for the tool"""
        return self.principal.can_access_tool(self.tool_name)
    
    def to_audit_context(self) -> Dict[str, Any]:
        """Convert to audit context"""
        return {
            "principal": self.principal.to_audit_dict(),
            "tool_name": self.tool_name,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "authorized": self.is_authorized()
        }


class ToolExecutionContext(BaseModel):
    """Context for tool execution with Principal"""
    model_config = ConfigDict(frozen=True)
    
    principal: Principal
    db_session: Optional[Any] = Field(None, description="Database session")
    request_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def user_id(self) -> str:
        return self.principal.user_id
    
    @property 
    def organization_id(self) -> str:
        return self.principal.organization_id
    
    def has_permission(self, permission: str) -> bool:
        return self.principal.has_permission(permission)