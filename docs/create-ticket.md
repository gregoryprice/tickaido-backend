# PRP: Re-enable Ticket Management Tools with Pydantic AI Toolsets

**Product Requirement Plan (PRP)**  
**Feature**: Enhanced AI-Powered Ticket Management with Secure Authentication  
**Version**: 1.0  
**Date**: 2025-09-14  
**Status**: **UPDATED - Implementation Required**  

## Overview

This PRP outlines the re-implementation of ticket management tools (`create_tickets`, `list_tickets`, `edit_ticket`) using Pydantic AI toolsets with proper JWT-based authentication and authorization. The implementation will leverage modern security patterns with Principal-based access control and dynamic tool filtering.

## Current State Analysis (UPDATED)

### Existing Components ✅ WORKING
- ✅ **API Layer**: Full CRUD operations at `/app/api/v1/tickets.py`
- ✅ **Authentication**: Dual authentication system in `/app/middleware/auth_middleware.py`
  - ✅ **Clerk Integration**: Full support with JIT user/org provisioning
  - ✅ **API Token Support**: Environment-specific API tokens with permissions
- ✅ **Models**: Complete ticket model with enums at `/app/models/ticket.py`
- ✅ **MCP Tools**: Working ticket tools at `/mcp_server/tools/ticket_tools.py`
- ✅ **AI Service**: Basic AI service at `/app/services/ai_service.py`
- ⚠️ **AI Agents**: Legacy categorization agent (needs org-scoped replacement)

### Current Authentication Flow ✅ IMPLEMENTED
- ✅ **FastAPI Middleware**: `AuthMiddleware` supports Clerk + API tokens
- ✅ **MCP Authentication**: Tools extract user context from JWT tokens
- ✅ **Tool Authentication**: Tools use `user_context` and `user_token` for backend calls
- ✅ **Organization Isolation**: Working via `current_user.organization_id`

### **CRITICAL GAPS** ❌ MISSING
- ❌ **Principal Service**: Referenced in docs but NOT IMPLEMENTED
- ❌ **Principal-based Auth**: MCP still uses raw JWT tokens, not Principal objects
- ❌ **Unified Tool Security**: No centralized authorization layer
- ❌ **Permission System**: No RBAC/ABAC implementation
- ❌ **Agent Integration**: AI agents not integrated with MCP tool security

## System Architecture Diagrams

### Authentication Flow Overview

```mermaid
graph TB
    subgraph "Client Layer"
        UI[Chat Interface/API Client]
        JWT[JWT Token]
    end
    
    subgraph "API Gateway"
        AuthMW[Auth Middleware]
        PrincipalSvc[Principal Service]
    end
    
    subgraph "Core Application"
        API[Ticket API Endpoints]
        Agent[Pydantic AI Agent]
        Toolset[Secure Toolset]
    end
    
    subgraph "Tool Layer"
        LocalTools[Local Function Tools]
        MCPTools[MCP Server Tools]
        Filter[Filtered Toolset]
        Approval[Approval Toolset]
    end
    
    subgraph "Data Layer"
        DB[(PostgreSQL)]
        Redis[(Redis Cache)]
    end
    
    UI -->|Bearer Token| AuthMW
    AuthMW -->|Extract User| PrincipalSvc
    PrincipalSvc -->|Build Principal| API
    API -->|Context + Principal| Agent
    Agent -->|RunContext| Toolset
    Toolset --> Filter
    Filter --> Approval
    Approval --> LocalTools
    Approval --> MCPTools
    LocalTools --> DB
    MCPTools --> DB
    PrincipalSvc --> Redis
```

### Principal Extraction Flow

```mermaid
sequenceDiagram
    participant Client
    participant AuthMW as Auth Middleware
    participant PrincipalSvc as Principal Service
    participant UserDB as User Database
    participant Redis
    participant API as API Endpoint

    Client->>AuthMW: Request with JWT Bearer Token
    AuthMW->>AuthMW: Extract JWT from Header
    AuthMW->>PrincipalSvc: extract_principal(token, db)
    
    PrincipalSvc->>Redis: Check Principal Cache
    alt Cache Hit
        Redis-->>PrincipalSvc: Cached Principal
    else Cache Miss
        PrincipalSvc->>PrincipalSvc: verify_token(token)
        PrincipalSvc->>UserDB: Query User + Organization
        UserDB-->>PrincipalSvc: User + Org Data
        PrincipalSvc->>PrincipalSvc: Build Permissions Map
        PrincipalSvc->>Redis: Cache Principal (TTL: 15min)
    end
    
    PrincipalSvc-->>AuthMW: Principal Object
    AuthMW->>API: Request + Principal Context
    API-->>Client: Response
```

### End-to-End Tool Execution Flow

```mermaid
sequenceDiagram
    participant User as Chat Interface
    participant API as FastAPI Endpoint
    participant Agent as Pydantic AI Agent
    participant Toolset as Secure Toolset
    participant Filter as Permission Filter
    participant Approval as Approval System
    participant Tool as create_ticket Tool
    participant Service as Ticket Service
    participant DB as Database
    participant MCP as MCP Server

    Note over User,MCP: Complete Flow: "Create a ticket for login issues"
    
    User->>API: POST /api/v1/tickets/ai-create<br/>{"user_input": "Login issues", ...}<br/>Authorization: Bearer JWT_TOKEN
    
    API->>API: Extract Principal from JWT
    Note right of API: Principal {<br/>user_id: "user123",<br/>org_id: "org456",<br/>roles: ["support_user"],<br/>permissions: {"tickets.create": true}<br/>}
    
    API->>Agent: create_ticket_with_ai(input, Principal)
    Agent->>Agent: Analyze user input with AI
    Agent->>Toolset: Execute create_ticket tool
    
    Toolset->>Filter: Check tool permission
    Filter->>Filter: principal.has_permission("tickets.create")?
    Filter-->>Toolset: ✅ Permission granted
    
    Toolset->>Approval: Check approval needed
    Approval->>Approval: create_ticket in sensitive_ops?
    Approval-->>Toolset: ❌ No approval required
    
    Toolset->>Tool: create_ticket(ctx=RunContext[Principal], title, description, ...)
    Tool->>Tool: Extract Principal from ctx.deps
    Tool->>Service: ticket_service.create_ticket(principal.org_id, principal.user_id, ...)
    Service->>DB: INSERT ticket with org isolation
    DB-->>Service: Ticket created
    Service-->>Tool: Ticket object
    Tool-->>Toolset: {"id": "ticket789", "status": "new", ...}
    
    Toolset->>MCP: Optional: Update external systems
    MCP-->>Toolset: Integration result
    
    Toolset-->>Agent: Tool execution result
    Agent->>Agent: Generate AI response
    Agent-->>API: {"ticket": {...}, "ai_analysis": {...}}
    API-->>User: HTTP 201 Created + Ticket Data
    
    Note over User,MCP: Security: No raw JWT tokens in tool layer<br/>Organization isolation enforced<br/>Permission-based access control
```

### Toolset Composition Architecture

```mermaid
graph TB
    subgraph "Toolset Composition"
        Factory[Toolset Factory]
        
        subgraph "Base Toolsets"
            LocalToolset[Local Function Toolset]
            MCPToolset[MCP Server Toolset]
        end
        
        subgraph "Security Layers"
            FilteredToolset[Filtered Toolset<br/>RBAC/ABAC]
            ApprovalToolset[Approval Required Toolset<br/>Sensitive Operations]
        end
        
        subgraph "Tool Functions"
            CreateTicket[create_ticket]
            ListTickets[list_tickets] 
            EditTicket[edit_ticket]
            DeleteTicket[delete_ticket]
            GetStats[get_ticket_stats]
        end
    end
    
    subgraph "Permission Matrix"
        PermMatrix["{<br/>  'support_user': {<br/>    'tickets.create': true,<br/>    'tickets.read': true,<br/>    'tickets.update': false<br/>  },<br/>  'support_admin': {<br/>    'tickets.*': true,<br/>    'tickets.delete': true<br/>  }<br/>}"]
    end
    
    Factory --> LocalToolset
    Factory --> MCPToolset
    LocalToolset --> FilteredToolset
    MCPToolset --> FilteredToolset
    FilteredToolset --> ApprovalToolset
    ApprovalToolset --> CreateTicket
    ApprovalToolset --> ListTickets
    ApprovalToolset --> EditTicket
    ApprovalToolset --> DeleteTicket
    ApprovalToolset --> GetStats
    
    FilteredToolset -.->|Consults| PermMatrix
    
    style FilteredToolset fill:#ffeb3b
    style ApprovalToolset fill:#f44336,color:#fff
    style PermMatrix fill:#e3f2fd
```

### **ACTUAL IMPLEMENTATION:** Create Ticket Through AI Chat

```mermaid
sequenceDiagram
    participant User
    participant ChatUI as Chat UI
    participant FastAPI as FastAPI Server
    participant AuthMW as Auth Middleware (IMPLEMENTED)
    participant AIService as AI Service (BASIC)
    participant TicketService as Ticket Service
    participant PostgreSQL
    
    Note over User,PostgreSQL: **CURRENT FLOW:** User creates ticket via AI chat (NO MCP INTEGRATION)
    
    User->>ChatUI: "I can't login to the system, getting 500 errors"
    ChatUI->>FastAPI: POST /api/v1/tickets/ai-create<br/>Authorization: Bearer eyJ0eXAi...<br/>Content-Type: application/json<br/>{<br/>  "user_input": "I can't login to the system, getting 500 errors",<br/>  "conversation_context": []<br/>}
    
    FastAPI->>AuthMW: Middleware intercepts request
    AuthMW->>AuthMW: Extract JWT from Authorization header
    AuthMW->>PrincipalSvc: extract_principal(jwt_token, db_session)
    
    PrincipalSvc->>PrincipalSvc: jwt.decode(token) -> payload
    PrincipalSvc->>PostgreSQL: SELECT * FROM users WHERE id = payload.sub
    PostgreSQL-->>PrincipalSvc: User{id, email, org_id, roles: ["support_user"]}
    PrincipalSvc->>PrincipalSvc: Build permissions from role mapping
    PrincipalSvc-->>AuthMW: Principal{<br/>  user_id: "550e8400-e29b-41d4-a716-446655440000",<br/>  organization_id: "123e4567-e89b-12d3-a456-426614174000",<br/>  email: "john@company.com",<br/>  roles: ["support_user"],<br/>  permissions: {<br/>    "tickets.create": true,<br/>    "tickets.read": true,<br/>    "tickets.update": false<br/>  }<br/>}
    
    AuthMW->>FastAPI: Request with Principal context
    FastAPI->>TicketAgent: create_ticket_with_ai(user_input, principal)
    
    TicketAgent->>TicketAgent: AI Analysis:<br/>- Category: "technical"<br/>- Priority: "high"<br/>- Title: "Login System 500 Errors"<br/>- Description: Enhanced with context
    
    TicketAgent->>SecureToolset: Run create_ticket tool with RunContext[Principal]
    SecureToolset->>SecureToolset: Permission Filter Check:<br/>principal.has_permission("tickets.create") -> True
    SecureToolset->>SecureToolset: Approval Check:<br/>"create_ticket" in sensitive_operations -> False
    
    SecureToolset->>CreateTool: create_ticket(<br/>  ctx=RunContext[Principal],<br/>  title="Login System 500 Errors",<br/>  description="User reports 500 errors when attempting to login...",<br/>  category="technical",<br/>  priority="high"<br/>)
    
    CreateTool->>CreateTool: Extract principal = ctx.deps
    CreateTool->>TicketService: create_ticket(<br/>  db=ctx.db,<br/>  ticket_data={<br/>    "title": "Login System 500 Errors",<br/>    "description": "...",<br/>    "category": "technical",<br/>    "priority": "high",<br/>    "organization_id": principal.organization_id,<br/>    "created_by_id": principal.user_id<br/>  }<br/>)
    
    TicketService->>PostgreSQL: INSERT INTO tickets (...)<br/>WHERE organization_id = '123e4567-...'
    PostgreSQL-->>TicketService: TICKET_ID: "789a0123-..."
    TicketService-->>CreateTool: Ticket{<br/>  id: "789a0123-...",<br/>  title: "Login System 500 Errors",<br/>  status: "new",<br/>  category: "technical",<br/>  priority: "high"<br/>}
    
    CreateTool-->>SecureToolset: Tool execution result
    SecureToolset-->>TicketAgent: {"id": "789a0123-...", "status": "created"}
    
    TicketAgent->>TicketAgent: Generate AI response with ticket details
    TicketAgent-->>FastAPI: {<br/>  "ticket": {<br/>    "id": "789a0123-...",<br/>    "title": "Login System 500 Errors",<br/>    "status": "new",<br/>    "category": "technical",<br/>    "priority": "high"<br/>  },<br/>  "ai_analysis": {<br/>    "confidence_score": 0.95,<br/>    "reasoning": "Classified as technical issue...",<br/>    "recommended_department": "engineering"<br/>  }<br/>}
    
    FastAPI-->>ChatUI: HTTP 201 Created<br/>Response body with ticket data
    ChatUI-->>User: "✅ I've created ticket #789a0123 for your login issue.<br/>It's been categorized as a high-priority technical issue<br/>and routed to the engineering team."
    
    Note over User,PostgreSQL: Security Enforced:<br/>- JWT verified at API boundary only<br/>- Principal object carries identity/permissions<br/>- Organization isolation in database<br/>- No raw tokens in tool layer
```

## Architecture Design

### 1. Principal-Based Authentication Layer

#### Complete Principal Object Structure
```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from uuid import UUID

@dataclass
class Principal:
    """
    Principal represents the authenticated identity with complete authorization context.
    This object replaces raw JWT tokens throughout the system and provides structured
    access to user identity, permissions, and organizational context.
    """
    
    # Core Identity Fields
    user_id: str = field(
        metadata={"description": "Unique user identifier (UUID string)"}
    )
    organization_id: str = field(
        metadata={"description": "User's organization UUID for multi-tenant isolation"}
    )
    email: str = field(
        metadata={"description": "User's email address for identification and logging"}
    )
    username: Optional[str] = field(
        default=None,
        metadata={"description": "Optional username/display name"}
    )
    
    # Authorization Fields
    roles: List[str] = field(
        default_factory=list,
        metadata={
            "description": "List of role names (e.g., 'support_user', 'admin', 'viewer')"
        }
    )
    scopes: List[str] = field(
        default_factory=list,
        metadata={
            "description": "OAuth-style scopes for fine-grained access (e.g., 'tickets:read', 'org:admin')"
        }
    )
    permissions: Dict[str, bool] = field(
        default_factory=dict,
        metadata={
            "description": "Computed permission map derived from roles/scopes (e.g., {'tickets.create': True})"
        }
    )
    
    # Organizational Context
    organization_name: Optional[str] = field(
        default=None,
        metadata={"description": "Human-readable organization name for logging/display"}
    )
    department: Optional[str] = field(
        default=None,
        metadata={"description": "User's department within organization for routing"}
    )
    team: Optional[str] = field(
        default=None,
        metadata={"description": "User's team for fine-grained access control"}
    )
    
    # Session & Security Context
    session_id: Optional[str] = field(
        default=None,
        metadata={"description": "Unique session identifier for audit trails"}
    )
    token_issued_at: Optional[datetime] = field(
        default=None,
        metadata={"description": "When the JWT token was issued (for token freshness checks)"}
    )
    token_expires_at: Optional[datetime] = field(
        default=None,
        metadata={"description": "When the JWT token expires (for proactive refresh)"}
    )
    last_activity: Optional[datetime] = field(
        default=None,
        metadata={"description": "Last known activity timestamp for session management"}
    )
    
    # Additional Context
    context: Dict[str, Any] = field(
        default_factory=dict,
        metadata={
            "description": "Additional contextual data (IP address, user agent, feature flags, etc.)"
        }
    )
    integrations: List[str] = field(
        default_factory=list,
        metadata={
            "description": "Available integrations for this user/org (JIRA, ServiceNow, etc.)"
        }
    )
    feature_flags: Dict[str, bool] = field(
        default_factory=dict,
        metadata={
            "description": "Feature flags enabled for this user/organization"
        }
    )
    
    # Authorization Methods
    def has_permission(self, permission: str) -> bool:
        """
        Check if Principal has a specific permission.
        
        Args:
            permission: Permission string in format 'resource.action' (e.g., 'tickets.create')
            
        Returns:
            bool: True if permission is granted
            
        Examples:
            principal.has_permission('tickets.create')  # Check ticket creation
            principal.has_permission('users.*')         # Check user admin access
        """
        # Wildcard permission checks (most specific to least specific)
        # 1. Check for exact permission: 'tickets.create'
        if self.permissions.get(permission, False):
            return True
        
        # 2. Check for resource wildcard: 'tickets.*' 
        resource = permission.split('.')[0] if '.' in permission else permission
        resource_wildcard = f"{resource}.*"
        if self.permissions.get(resource_wildcard, False):
            return True
            
        # 3. Check for global admin permission: '*'
        if self.permissions.get("*", False):
            return True
            
        return False
    
    def has_role(self, role: str) -> bool:
        """
        Check if Principal has a specific role.
        
        Args:
            role: Role name (e.g., 'admin', 'support_user')
            
        Returns:
            bool: True if role is assigned
        """
        return role in self.roles
    
    def has_any_role(self, roles: List[str]) -> bool:
        """
        Check if Principal has any of the specified roles.
        
        Args:
            roles: List of role names to check
            
        Returns:
            bool: True if any role matches
        """
        return any(role in self.roles for role in roles)
    
    def has_scope(self, scope: str) -> bool:
        """
        Check if Principal has a specific OAuth scope.
        
        Args:
            scope: Scope string (e.g., 'tickets:read', 'org:admin')
            
        Returns:
            bool: True if scope is granted
        """
        return scope in self.scopes
    
    def can_access_organization(self, org_id: str) -> bool:
        """
        Check if Principal can access a specific organization.
        Currently enforces single-org isolation, but could be extended
        for multi-org access in the future.
        
        Args:
            org_id: Organization UUID to check
            
        Returns:
            bool: True if access is allowed
        """
        return self.organization_id == org_id
    
    def is_admin(self) -> bool:
        """
        Check if Principal has administrative privileges.
        
        Returns:
            bool: True if user has admin role or permissions
        """
        return (
            self.has_role('admin') or 
            self.has_role('org_admin') or 
            self.has_permission('users.*')
        )
    
    def get_audit_context(self) -> Dict[str, Any]:
        """
        Get context information for audit logging.
        
        Returns:
            Dict containing user, org, session info for audit trails
        """
        return {
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'email': self.email,
            'session_id': self.session_id,
            'roles': self.roles,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def is_token_fresh(self, max_age_minutes: int = 60) -> bool:
        """
        Check if the underlying JWT token is still fresh.
        
        Args:
            max_age_minutes: Maximum acceptable token age in minutes
            
        Returns:
            bool: True if token is considered fresh
        """
        if not self.token_issued_at:
            return False
            
        age = datetime.utcnow() - self.token_issued_at
        return age.total_seconds() < (max_age_minutes * 60)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Principal to dictionary for serialization.
        Used for caching and passing context between services.
        
        Returns:
            Dict representation of Principal
        """
        return {
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'email': self.email,
            'username': self.username,
            'roles': self.roles,
            'scopes': self.scopes,
            'permissions': self.permissions,
            'organization_name': self.organization_name,
            'department': self.department,
            'team': self.team,
            'session_id': self.session_id,
            'context': self.context,
            'integrations': self.integrations,
            'feature_flags': self.feature_flags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Principal':
        """
        Create Principal from dictionary (used for cache deserialization).
        
        Args:
            data: Dictionary representation of Principal
            
        Returns:
            Principal instance
        """
        # Handle datetime fields if present
        token_issued_at = None
        token_expires_at = None
        last_activity = None
        
        if 'token_issued_at' in data and data['token_issued_at']:
            token_issued_at = datetime.fromisoformat(data['token_issued_at'])
        if 'token_expires_at' in data and data['token_expires_at']:
            token_expires_at = datetime.fromisoformat(data['token_expires_at'])
        if 'last_activity' in data and data['last_activity']:
            last_activity = datetime.fromisoformat(data['last_activity'])
            
        return cls(
            user_id=data['user_id'],
            organization_id=data['organization_id'],
            email=data['email'],
            username=data.get('username'),
            roles=data.get('roles', []),
            scopes=data.get('scopes', []),
            permissions=data.get('permissions', {}),
            organization_name=data.get('organization_name'),
            department=data.get('department'),
            team=data.get('team'),
            session_id=data.get('session_id'),
            token_issued_at=token_issued_at,
            token_expires_at=token_expires_at,
            last_activity=last_activity,
            context=data.get('context', {}),
            integrations=data.get('integrations', []),
            feature_flags=data.get('feature_flags', {})
        )
```

### **COMPREHENSIVE PERMISSION SYSTEM ARCHITECTURE**

This section defines how permissions work for both **Users** and **AI Agents** in the Principal-based authentication system.

#### **User Permission System**

##### **Permission Format**
Permissions follow the format `resource.action` with hierarchical wildcard support:

```
tickets.create          # Specific permission
tickets.read            # Read tickets
tickets.update          # Update existing tickets
tickets.delete          # Delete tickets
tickets.*               # All ticket operations  
users.read              # Read user data
users.create            # Create new users
users.update            # Update existing users
users.delete            # Delete users
users.*                 # All user operations
*                       # GLOBAL ADMIN - All permissions
```

##### **Permission Hierarchy (Most to Least Specific)**
1. **Exact Permission**: `tickets.create` 
2. **Resource Wildcard**: `tickets.*` (grants all ticket operations)
3. **Global Admin**: `*` (grants ALL permissions on platform)

##### **Permission Examples**
```python
# User with specific permissions
permissions = {
    "tickets.create": True,
    "tickets.read": True, 
    "tickets.update": False,
    "tickets.delete": False,
    "users.read": True
}

# User with resource wildcard
permissions = {
    "tickets.*": True,        # Can do anything with tickets (create, read, update, delete)
    "users.read": True        # Can only read users
}

# Global admin user
permissions = {
    "*": True                 # Can do EVERYTHING on platform
}
```

#### **AI Agent Permission System**

##### **Agent Toolset Permission Requirements**
Each AI agent receives a **filtered toolset** based on the user's permissions who initiated the chat:

```python
# Agent Chat Flow with Permissions
user_permissions = {"tickets.create": True, "tickets.read": True}

# AI Agent gets filtered toolset
agent_tools = [
    "create_ticket",     # ✅ Allowed (user has tickets.create)
    "list_tickets",      # ✅ Allowed (user has tickets.read)  
    "delete_ticket"      # ❌ BLOCKED (user lacks tickets.delete)
]
```

##### **Tool-to-Permission Mapping**
```python
TOOL_PERMISSION_MAP = {
    # Ticket Management Tools
    "create_ticket": "tickets.create",
    "create_ticket_with_ai": "tickets.create", 
    "list_tickets": "tickets.read",
    "get_ticket": "tickets.read",
    "update_ticket": "tickets.update",
    "patch_ticket": "tickets.update", 
    "delete_ticket": "tickets.delete",
    "assign_ticket": "tickets.update",
    
    # User Management Tools  
    "list_users": "users.read",
    "create_user": "users.create",
    "update_user": "users.update",
    "delete_user": "users.delete"
}
```

##### **Agent Security Enforcement**
```python
# In Pydantic AI Agent with MCP Tools
class SecureTicketAgent(Agent):
    async def run_tools(self, tools: List[str], user_principal: Principal):
        # Filter tools based on user permissions
        allowed_tools = []
        
        for tool_name in tools:
            required_permission = TOOL_PERMISSION_MAP.get(tool_name)
            if not required_permission:
                continue  # Skip unmapped tools
                
            if user_principal.has_permission(required_permission):
                allowed_tools.append(tool_name)
            else:
                logger.warning(f"Tool {tool_name} blocked - user lacks {required_permission}")
        
        # Agent can only use allowed tools
        return await self.execute_with_filtered_tools(allowed_tools)
```

#### **Permission Creation and Management**

##### **Role-Based Permission Assignment**
```python
# Default role permissions (configured in PrincipalService)
ROLE_PERMISSIONS = {
    'admin': {
        '*': True,  # ticket permissions
    },
    'member': {
        'tickets.*': True,
        'users.read': True,
    },
    'agent': {
        'tickets.read': True,
        'tickets.create': True,
        'tickets.update': True
    }
}
```

##### **API Token Permission Management**
API tokens can have custom permission sets defined when created:

```python
# API Token with custom permissions
api_token = APIToken(
    user_id=user.id,
    organization_id=org.id,
    permissions=[
        "*"
    ]
)
```

##### **Dynamic Permission Updates**
Permissions are computed in real-time from:
1. **User Roles** → Mapped to permissions via `ROLE_PERMISSIONS`
2. **API Token Permissions** → Direct permission list
3. **Organization Context** → Organization-level permission overrides
4. **Feature Flags** → Can enable/disable permission groups

##### **Permission Caching Strategy**
```python
# Principal permissions cached for performance
cache_key = f"principal:{user_id}:{org_id}:{token_hash}"
cached_principal = await redis.get(cache_key)

# Cache TTL: 15 minutes (refreshed on permission changes)
# Invalidated when: user roles change, API token updated, logout
```

#### Complete Principal Service Implementation
```python
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError
import redis.asyncio as redis

from app.models.user import User
from app.models.organization import Organization
from app.middleware.auth_middleware import auth_service
from app.config.settings import get_settings

logger = logging.getLogger(__name__)

class PrincipalService:
    """
    Service responsible for extracting and managing Principal objects from JWT tokens.
    Handles permission mapping, caching, and organization context resolution.
    """
    
    def __init__(self):
        """Initialize the Principal Service with Redis cache and permission mappings."""
        self.settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
        self.cache_ttl = 900  # 15 minutes
        
        # Role-to-permission mapping configuration
        # This should ideally be loaded from database or config file
        self.role_permissions = {
            'admin': {
                'tickets.*': True,
                'users.*': True
            },
            'org_admin': {
                'tickets.*': True,
                'users.read': True,
                'users.update': True
            },
            'support_admin': {
                'tickets.*': True,
                'users.read': True
            },
            'support_user': {
                'tickets.create': True,
                'tickets.read': True,
                'tickets.update': True
            },
            'viewer': {
                'tickets.read': True
            },
            'agent': {
                'tickets.read': True,
                'tickets.create': True,
                'tickets.update': True
            },
            'guest': {
                # No permissions by default
            }
        }
    
    async def get_redis_client(self) -> Optional[redis.Redis]:
        """Get or create Redis client for caching."""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(
                    self.settings.REDIS_URL,
                    encoding='utf-8',
                    decode_responses=True
                )
                # Test connection
                await self.redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed, caching disabled: {e}")
                self.redis_client = None
        return self.redis_client
    
    async def extract_principal(
        self, 
        token: str, 
        db: AsyncSession,
        request_context: Optional[Dict[str, Any]] = None
    ) -> Principal:
        """
        Extract Principal object from JWT token with full context resolution.
        
        Args:
            token: JWT token string
            db: Database session for user lookup
            request_context: Additional request context (IP, user agent, etc.)
            
        Returns:
            Principal: Complete principal object with permissions and context
            
        Raises:
            AuthenticationError: If token is invalid or user not found
        """
        try:
            # Check cache first
            cache_key = f"principal:{token[:16]}..."  # Use token prefix for cache key
            redis_client = await self.get_redis_client()
            
            if redis_client:
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    logger.debug("Principal cache hit")
                    return Principal.from_dict(json.loads(cached_data))
            
            # Extract user from JWT token
            user = await auth_service.get_user_by_token(token, db)
            if not user:
                raise ValueError("Invalid token or user not found")
            
            # Load organization data
            organization = await self._load_organization(db, user.organization_id)
            
            # Extract JWT payload for session info
            jwt_payload = auth_service.verify_token(token)
            
            # Build comprehensive Principal object
            principal = await self._build_principal(
                user=user,
                organization=organization,
                jwt_payload=jwt_payload,
                request_context=request_context or {}
            )
            
            # Cache the Principal object
            if redis_client:
                await redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(principal.to_dict(), default=str)
                )
                logger.debug("Principal cached successfully")
            
            return principal
            
        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            raise ValueError(f"Invalid token: {e}")
        except Exception as e:
            logger.error(f"Principal extraction failed: {e}")
            raise ValueError(f"Authentication failed: {e}")
    
    async def _load_organization(
        self, 
        db: AsyncSession, 
        org_id: str
    ) -> Optional[Organization]:
        """Load organization data for context."""
        try:
            stmt = select(Organization).where(
                Organization.id == org_id,
                Organization.is_deleted == False
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to load organization {org_id}: {e}")
            return None
    
    async def _build_principal(
        self,
        user: User,
        organization: Optional[Organization],
        jwt_payload: Dict[str, Any],
        request_context: Dict[str, Any]
    ) -> Principal:
        """
        Build complete Principal object from user data and context.
        
        Args:
            user: User model instance
            organization: Organization model instance
            jwt_payload: Decoded JWT payload
            request_context: Request context data
            
        Returns:
            Principal: Fully constructed principal object
        """
        # Extract user roles (could be from user model or JWT)
        roles = getattr(user, 'roles', []) or []
        if not roles and hasattr(user, 'role') and user.role:
            roles = [user.role]  # Handle single role field
        
        # Build permissions from roles
        permissions = self._build_permissions_from_roles(roles)
        
        # Extract scopes from JWT or user
        scopes = jwt_payload.get('scopes', [])
        
        # Build integrations list (from organization settings)
        integrations = []
        if organization and hasattr(organization, 'enabled_integrations'):
            integrations = organization.enabled_integrations or []
        
        # Extract feature flags (from organization or user settings)
        feature_flags = {}
        if organization and hasattr(organization, 'feature_flags'):
            feature_flags.update(organization.feature_flags or {})
        if hasattr(user, 'feature_flags') and user.feature_flags:
            feature_flags.update(user.feature_flags)
        
        # Build session context
        session_context = {
            'ip_address': request_context.get('client_ip'),
            'user_agent': request_context.get('user_agent'),
            'request_id': request_context.get('request_id')
        }
        session_context = {k: v for k, v in session_context.items() if v is not None}
        
        # Extract datetime fields from JWT
        issued_at = None
        expires_at = None
        if 'iat' in jwt_payload:
            issued_at = datetime.fromtimestamp(jwt_payload['iat'], tz=timezone.utc)
        if 'exp' in jwt_payload:
            expires_at = datetime.fromtimestamp(jwt_payload['exp'], tz=timezone.utc)
        
        return Principal(
            user_id=str(user.id),
            organization_id=str(user.organization_id),
            email=user.email,
            username=getattr(user, 'username', None) or getattr(user, 'name', None),
            roles=roles,
            scopes=scopes,
            permissions=permissions,
            organization_name=organization.name if organization else None,
            department=getattr(user, 'department', None),
            team=getattr(user, 'team', None),
            session_id=jwt_payload.get('jti'),  # JWT ID as session ID
            token_issued_at=issued_at,
            token_expires_at=expires_at,
            last_activity=datetime.utcnow(),
            context=session_context,
            integrations=integrations,
            feature_flags=feature_flags
        )
    
    def _build_permissions_from_roles(self, roles: List[str]) -> Dict[str, bool]:
        """
        Build permission map from user roles.
        
        Args:
            roles: List of role names
            
        Returns:
            Dict mapping permission names to boolean values
        """
        permissions = {}
        
        for role in roles:
            role_perms = self.role_permissions.get(role, {})
            permissions.update(role_perms)
        
        return permissions
    
    async def refresh_principal_cache(self, token: str) -> None:
        """
        Refresh cached Principal object (useful for permission updates).
        
        Args:
            token: JWT token to refresh cache for
        """
        cache_key = f"principal:{token[:16]}..."
        redis_client = await self.get_redis_client()
        
        if redis_client:
            await redis_client.delete(cache_key)
            logger.info(f"Principal cache cleared for key: {cache_key}")
    
    async def get_principal_by_user_id(
        self, 
        user_id: str, 
        db: AsyncSession
    ) -> Optional[Principal]:
        """
        Get Principal object by user ID (useful for background tasks).
        
        Args:
            user_id: User UUID
            db: Database session
            
        Returns:
            Optional[Principal]: Principal object if user found
        """
        try:
            # Load user
            stmt = select(User).where(
                User.id == user_id,
                User.is_deleted == False,
                User.is_active == True
            )
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Load organization
            organization = await self._load_organization(db, user.organization_id)
            
            # Build Principal without JWT context
            return await self._build_principal(
                user=user,
                organization=organization,
                jwt_payload={},  # No JWT context for direct user lookup
                request_context={}
            )
            
        except Exception as e:
            logger.error(f"Failed to get principal by user ID {user_id}: {e}")
            return None

# Global service instance
principal_service = PrincipalService()
```
```

## MCP Server Authentication Strategy

### Key Decision: Direct Service Calls vs API Calls

**IMPORTANT**: The MCP server tools will **NOT** make HTTP API calls back to the FastAPI endpoints. Instead, they will directly call the service layer functions to avoid the authentication complexity and circular dependency issues.

```mermaid
graph TB
    subgraph "Current (Problematic) Architecture"
        MCPTool1[MCP Tool] -->|HTTP + JWT| FastAPIEndpoint[FastAPI /api/v1/tickets]
        FastAPIEndpoint -->|Extract Principal| ServiceLayer1[Ticket Service]
        ServiceLayer1 --> Database1[(Database)]
        
        Note1[Problems:<br/>- Circular auth dependency<br/>- JWT token management in tools<br/>- HTTP overhead<br/>- Complex error handling]
    end
    
    subgraph "New (Direct) Architecture"  
        MCPTool2[MCP Tool] -->|Principal Context| ServiceLayer2[Ticket Service]
        ServiceLayer2 --> Database2[(Database)]
        
        Note2[Benefits:<br/>- Principal object passed directly<br/>- No JWT tokens in tool layer<br/>- Direct service calls<br/>- Simplified error handling]
    end
    
    style Note1 fill:#ffebee,color:#c62828
    style Note2 fill:#e8f5e9,color:#2e7d32
```

### MCP Authentication Flow Implementation

```python
class MCPAuthContext:
    """
    Authentication context passed from FastAPI to MCP tools.
    Contains Principal and database session for direct service calls.
    """
    
    def __init__(self, principal: Principal, db_session: AsyncSession):
        self.principal = principal
        self.db_session = db_session
        self.request_id = principal.context.get('request_id')
        
    def get_audit_context(self) -> Dict[str, Any]:
        """Get audit context for logging MCP tool calls."""
        return {
            **self.principal.get_audit_context(),
            'source': 'mcp_tool',
            'request_id': self.request_id
        }

class MCPToolBase:
    """
    Base class for MCP tools with authentication and service layer access.
    All MCP tools should inherit from this to ensure consistent auth handling.
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"mcp.tools.{name}")
    
    async def execute(self, context: MCPAuthContext, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with authenticated context.
        
        Args:
            context: MCP auth context with Principal and DB session
            **kwargs: Tool-specific arguments
            
        Returns:
            Dict with tool execution result
        """
        try:
            # Log tool execution for audit
            audit_ctx = context.get_audit_context()
            self.logger.info(f"Executing tool {self.name}", extra=audit_ctx)
            
            # Call the specific tool implementation
            result = await self._execute_impl(context, **kwargs)
            
            self.logger.info(f"Tool {self.name} completed successfully", extra=audit_ctx)
            return result
            
        except Exception as e:
            self.logger.error(f"Tool {self.name} failed: {e}", extra=audit_ctx)
            raise
    
    async def _execute_impl(self, context: MCPAuthContext, **kwargs) -> Dict[str, Any]:
        """Implement this method in subclasses."""
        raise NotImplementedError

class CreateTicketTool(MCPToolBase):
    """
    MCP tool for creating tickets - calls service layer directly.
    """
    
    def __init__(self):
        super().__init__(
            name="create_ticket",
            description="Create a support ticket with AI categorization"
        )
    
    async def _execute_impl(self, context: MCPAuthContext, **kwargs) -> Dict[str, Any]:
        """
        Create ticket by calling service layer directly with Principal context.
        """
        from app.services.ticket_service import ticket_service
        
        # Validate permissions
        if not context.principal.has_permission('tickets.create'):
            raise PermissionError("User lacks permission to create tickets")
        
        # Extract arguments
        title = kwargs.get('title')
        description = kwargs.get('description')
        category = kwargs.get('category', 'general')
        priority = kwargs.get('priority', 'medium')
        
        if not title or not description:
            raise ValueError("Title and description are required")
        
        # Prepare ticket data with organization context
        ticket_data = {
            'title': title,
            'description': description,
            'category': category,
            'priority': priority,
            'organization_id': context.principal.organization_id,
            'created_by_id': context.principal.user_id,
            'department': context.principal.department
        }
        
        # Call service layer directly (no HTTP calls!)
        ticket = await ticket_service.create_ticket(
            db=context.db_session,
            ticket_data=ticket_data,
            created_by_id=context.principal.user_id
        )
        
        return {
            'id': str(ticket.id),
            'title': ticket.title,
            'status': ticket.status.value,
            'category': ticket.category.value,
            'priority': ticket.priority.value,
            'organization_id': str(ticket.organization_id),
            'created_at': ticket.created_at.isoformat()
        }

class ListTicketsTool(MCPToolBase):
    """
    MCP tool for listing tickets with organization filtering.
    """
    
    def __init__(self):
        super().__init__(
            name="list_tickets", 
            description="List tickets for the user's organization"
        )
    
    async def _execute_impl(self, context: MCPAuthContext, **kwargs) -> Dict[str, Any]:
        """
        List tickets by calling service layer directly with org filtering.
        """
        from app.services.ticket_service import ticket_service
        
        # Validate permissions
        if not context.principal.has_permission('tickets.read'):
            raise PermissionError("User lacks permission to read tickets")
        
        # Extract pagination parameters
        page = kwargs.get('page', 1)
        page_size = min(kwargs.get('page_size', 10), 50)  # Max 50 items
        offset = (page - 1) * page_size
        
        # Extract filter parameters
        filters = {}
        if kwargs.get('status'):
            filters['status'] = [kwargs['status']]
        if kwargs.get('category'):
            filters['category'] = [kwargs['category']]
        if kwargs.get('priority'):
            filters['priority'] = [kwargs['priority']]
        
        # Call service layer with organization isolation
        tickets, total = await ticket_service.list_tickets(
            db=context.db_session,
            organization_id=context.principal.organization_id,  # Enforce org isolation!
            offset=offset,
            limit=page_size,
            filters=filters
        )
        
        # Convert to serializable format
        ticket_data = []
        for ticket in tickets:
            ticket_data.append({
                'id': str(ticket.id),
                'title': ticket.title,
                'status': ticket.status.value,
                'category': ticket.category.value,
                'priority': ticket.priority.value,
                'created_at': ticket.created_at.isoformat(),
                'created_by_id': str(ticket.created_by_id)
            })
        
        return {
            'tickets': ticket_data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }
```

### Complete MCP-to-FastAPI Integration Flow

```mermaid
sequenceDiagram
    participant FastAPI as FastAPI Endpoint
    participant PrincipalSvc as Principal Service  
    participant MCPClient as MCP Client
    participant MCPServer as MCP Server
    participant MCPTool as MCP Tool
    participant ServiceLayer as Service Layer
    participant Database
    
    Note over FastAPI,Database: No HTTP calls between MCP and FastAPI!
    
    FastAPI->>PrincipalSvc: extract_principal(jwt_token)
    PrincipalSvc-->>FastAPI: Principal object
    
    FastAPI->>MCPClient: call_tool("create_ticket", principal, db_session)
    MCPClient->>MCPServer: Forward tool call with Principal context
    MCPServer->>MCPTool: execute(MCPAuthContext(principal, db))
    
    MCPTool->>MCPTool: Validate principal.has_permission('tickets.create')
    MCPTool->>ServiceLayer: ticket_service.create_ticket(db, ticket_data, user_id)
    ServiceLayer->>Database: INSERT with organization isolation
    Database-->>ServiceLayer: Created ticket
    ServiceLayer-->>MCPTool: Ticket object
    
    MCPTool-->>MCPServer: Tool execution result
    MCPServer-->>MCPClient: Tool result  
    MCPClient-->>FastAPI: Tool result
    FastAPI-->>FastAPI: Generate AI response
```

### 2. Complete Pydantic AI Toolset Architecture

#### Function Toolset for Local Tools
```python
from pydantic_ai.tools import FunctionToolset
from pydantic_ai import Agent, RunContext
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ToolExecutionContext:
    """
    Context object passed to Pydantic AI tools containing Principal and database access.
    This replaces raw JWT tokens and provides structured access to user identity.
    """
    
    principal: Principal
    db_session: AsyncSession
    request_metadata: Dict[str, Any]
    
    def get_user_context(self) -> Dict[str, Any]:
        """Get user context for tool execution."""
        return {
            'user_id': self.principal.user_id,
            'organization_id': self.principal.organization_id,
            'email': self.principal.email,
            'roles': self.principal.roles,
            'permissions': list(self.principal.permissions.keys())
        }
    
    def validate_permission(self, permission: str) -> None:
        """Validate permission and raise exception if not granted."""
        if not self.principal.has_permission(permission):
            raise PermissionError(
                f"User {self.principal.email} lacks permission '{permission}'"
            )
    
    def enforce_organization_access(self, resource_org_id: str) -> None:
        """Enforce organization isolation for multi-tenant security."""
        if not self.principal.can_access_organization(resource_org_id):
            raise PermissionError(
                f"User cannot access resources from organization {resource_org_id}"
            )

class SecureTicketToolset:
    """
    Complete toolset for ticket management with security, filtering, and approval.
    This class composes all toolset layers: Local -> MCP -> Filtered -> Approval.
    """
    
    def __init__(self, mcp_client=None):
        """
        Initialize the secure ticket toolset.
        
        Args:
            mcp_client: Optional MCP client for external tool integration
        """
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize base toolsets
        self.local_toolset = self._create_local_toolset()
        self.mcp_toolset = self._create_mcp_toolset() if mcp_client else None
        
        # Create composed secure toolset
        self.secure_toolset = self._create_secure_composition()
    
    def _create_local_toolset(self) -> FunctionToolset:
        """Create local function toolset with ticket management tools."""
        toolset = FunctionToolset()
        
        @toolset.tool
        async def create_ticket(
            ctx: RunContext[ToolExecutionContext],
            title: str,
            description: str,
            category: str = "general",
            priority: str = "medium",
            urgency: str = "medium",
            department: Optional[str] = None,
            assigned_to_id: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Create a support ticket with comprehensive validation and organization isolation.
            
            Args:
                ctx: Tool execution context with Principal and DB session
                title: Ticket title (required, max 500 chars)
                description: Detailed description (required)
                category: Issue category (technical, billing, feature_request, bug, user_access, general)
                priority: Priority level (low, medium, high, critical)
                urgency: Urgency level (low, medium, high, critical)
                department: Target department for routing
                assigned_to_id: UUID of user to assign ticket to
                
            Returns:
                Dict containing created ticket details
                
            Raises:
                PermissionError: If user lacks create permission
                ValueError: If validation fails
            """
            from app.services.ticket_service import ticket_service
            
            # Extract context
            execution_ctx = ctx.deps
            principal = execution_ctx.principal
            db = execution_ctx.db_session
            
            # Validate permissions
            execution_ctx.validate_permission('tickets.create')
            
            # Validate inputs
            if not title or len(title.strip()) == 0:
                raise ValueError("Title is required and cannot be empty")
            if not description or len(description.strip()) == 0:
                raise ValueError("Description is required and cannot be empty")
            if len(title) > 500:
                raise ValueError("Title cannot exceed 500 characters")
            
            # Validate enum values
            valid_categories = ['technical', 'billing', 'feature_request', 'bug', 'user_access', 'general', 'integration', 'performance', 'security']
            valid_priorities = ['low', 'medium', 'high', 'critical']
            
            if category not in valid_categories:
                raise ValueError(f"Category must be one of: {', '.join(valid_categories)}")
            if priority not in valid_priorities:
                raise ValueError(f"Priority must be one of: {', '.join(valid_priorities)}")
            if urgency not in valid_priorities:
                raise ValueError(f"Urgency must be one of: {', '.join(valid_priorities)}")
            
            # Validate assignment if provided
            if assigned_to_id:
                # TODO: Validate that assigned user exists and is in same organization
                pass
            
            # Prepare ticket data with organization context
            ticket_data = {
                'title': title.strip(),
                'description': description.strip(),
                'category': category,
                'priority': priority,
                'urgency': urgency,
                'organization_id': principal.organization_id,
                'created_by_id': principal.user_id,
                'department': department or principal.department,
                'source_channel': 'ai_chat',
                'source_details': {
                    'tool_name': 'create_ticket',
                    'session_id': principal.session_id
                }
            }
            
            if assigned_to_id:
                ticket_data['assigned_to_id'] = assigned_to_id
            
            # Create ticket through service layer
            try:
                ticket = await ticket_service.create_ticket(
                    db=db,
                    ticket_data=ticket_data,
                    created_by_id=principal.user_id
                )
                
                # Log successful creation
                logger.info(
                    f"Ticket created via AI tool: {ticket.id}",
                    extra=execution_ctx.principal.get_audit_context()
                )
                
                return {
                    'id': str(ticket.id),
                    'title': ticket.title,
                    'description': ticket.description,
                    'status': ticket.status.value,
                    'category': ticket.category.value,
                    'priority': ticket.priority.value,
                    'urgency': ticket.urgency.value,
                    'organization_id': str(ticket.organization_id),
                    'created_by_id': str(ticket.created_by_id),
                    'created_at': ticket.created_at.isoformat(),
                    'department': ticket.department,
                    'assigned_to_id': str(ticket.assigned_to_id) if ticket.assigned_to_id else None
                }
                
            except Exception as e:
                logger.error(
                    f"Failed to create ticket via AI tool: {e}",
                    extra=execution_ctx.principal.get_audit_context()
                )
                raise ValueError(f"Ticket creation failed: {e}")
        
        @toolset.tool
        async def list_tickets(
            ctx: RunContext[ToolExecutionContext],
            page: int = 1,
            page_size: int = 10,
            status: Optional[str] = None,
            category: Optional[str] = None,
            priority: Optional[str] = None,
            assigned_to_me: bool = False,
            search_query: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            List tickets with filtering, pagination, and organization isolation.
            
            Args:
                ctx: Tool execution context with Principal and DB session
                page: Page number (1-based)
                page_size: Items per page (max 50)
                status: Filter by status
                category: Filter by category  
                priority: Filter by priority
                assigned_to_me: Only show tickets assigned to current user
                search_query: Search in title/description
                
            Returns:
                Dict containing paginated ticket list
            """
            from app.services.ticket_service import ticket_service
            
            # Extract context
            execution_ctx = ctx.deps
            principal = execution_ctx.principal
            db = execution_ctx.db_session
            
            # Validate permissions
            execution_ctx.validate_permission('tickets.read')
            
            # Validate pagination
            page = max(1, page)
            page_size = min(max(1, page_size), 50)
            offset = (page - 1) * page_size
            
            # Build filters with organization isolation
            filters = {}
            if status:
                filters['status'] = [status]
            if category:
                filters['category'] = [category]
            if priority:
                filters['priority'] = [priority]
            if assigned_to_me:
                filters['assigned_to_id'] = principal.user_id
            if search_query:
                filters['search'] = search_query.strip()
            
            try:
                # Get tickets with automatic organization filtering
                tickets, total = await ticket_service.list_tickets(
                    db=db,
                    organization_id=principal.organization_id,  # Organization isolation!
                    offset=offset,
                    limit=page_size,
                    filters=filters
                )
                
                # Convert to serializable format
                ticket_list = []
                for ticket in tickets:
                    ticket_list.append({
                        'id': str(ticket.id),
                        'title': ticket.title,
                        'status': ticket.status.value,
                        'category': ticket.category.value,
                        'priority': ticket.priority.value,
                        'urgency': ticket.urgency.value,
                        'created_at': ticket.created_at.isoformat(),
                        'created_by_id': str(ticket.created_by_id),
                        'assigned_to_id': str(ticket.assigned_to_id) if ticket.assigned_to_id else None,
                        'department': ticket.department,
                        'is_overdue': ticket.is_overdue,
                        'age_hours': ticket.age_in_hours
                    })
                
                logger.info(
                    f"Listed {len(ticket_list)} tickets via AI tool",
                    extra=execution_ctx.principal.get_audit_context()
                )
                
                return {
                    'tickets': ticket_list,
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total': total,
                        'total_pages': (total + page_size - 1) // page_size,
                        'has_next': page * page_size < total,
                        'has_prev': page > 1
                    },
                    'filters_applied': filters
                }
                
            except Exception as e:
                logger.error(
                    f"Failed to list tickets via AI tool: {e}",
                    extra=execution_ctx.principal.get_audit_context()
                )
                raise ValueError(f"Failed to retrieve tickets: {e}")
        
        @toolset.tool
        async def edit_ticket(
            ctx: RunContext[ToolExecutionContext],
            ticket_id: str,
            title: Optional[str] = None,
            description: Optional[str] = None,
            status: Optional[str] = None,
            priority: Optional[str] = None,
            category: Optional[str] = None,
            assigned_to_id: Optional[str] = None,
            internal_notes: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Edit an existing ticket with validation and organization isolation.
            
            Args:
                ctx: Tool execution context
                ticket_id: UUID of ticket to edit
                title: New title
                description: New description
                status: New status (new, open, in_progress, pending, resolved, closed, cancelled)
                priority: New priority level
                category: New category
                assigned_to_id: New assignee UUID
                internal_notes: Internal notes (admin only)
                
            Returns:
                Dict containing updated ticket details
            """
            from app.services.ticket_service import ticket_service
            import uuid
            
            # Extract context
            execution_ctx = ctx.deps
            principal = execution_ctx.principal
            db = execution_ctx.db_session
            
            # Validate permissions
            execution_ctx.validate_permission('tickets.update')
            
            # Validate ticket ID
            try:
                uuid.UUID(ticket_id)
            except ValueError:
                raise ValueError("Invalid ticket ID format")
            
            # Build update data
            update_data = {}
            if title is not None:
                if not title.strip():
                    raise ValueError("Title cannot be empty")
                if len(title) > 500:
                    raise ValueError("Title cannot exceed 500 characters")
                update_data['title'] = title.strip()
            
            if description is not None:
                if not description.strip():
                    raise ValueError("Description cannot be empty")
                update_data['description'] = description.strip()
            
            if status is not None:
                valid_statuses = ['new', 'open', 'in_progress', 'pending', 'resolved', 'closed', 'cancelled']
                if status not in valid_statuses:
                    raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
                update_data['status'] = status
            
            if priority is not None:
                valid_priorities = ['low', 'medium', 'high', 'critical']
                if priority not in valid_priorities:
                    raise ValueError(f"Priority must be one of: {', '.join(valid_priorities)}")
                update_data['priority'] = priority
            
            if category is not None:
                valid_categories = ['technical', 'billing', 'feature_request', 'bug', 'user_access', 'general']
                if category not in valid_categories:
                    raise ValueError(f"Category must be one of: {', '.join(valid_categories)}")
                update_data['category'] = category
            
            if assigned_to_id is not None:
                if assigned_to_id:  # Allow empty string to unassign
                    try:
                        uuid.UUID(assigned_to_id)
                        update_data['assigned_to_id'] = assigned_to_id
                    except ValueError:
                        raise ValueError("Invalid assigned_to_id format")
                else:
                    update_data['assigned_to_id'] = None
            
            if internal_notes is not None:
                # Only admin users can set internal notes
                if not principal.is_admin():
                    raise PermissionError("Only administrators can set internal notes")
                update_data['internal_notes'] = internal_notes
            
            if not update_data:
                raise ValueError("At least one field must be provided for update")
            
            try:
                # Update ticket with organization isolation
                updated_ticket = await ticket_service.update_ticket(
                    db=db,
                    ticket_id=ticket_id,
                    organization_id=principal.organization_id,  # Organization isolation!
                    update_data=update_data
                )
                
                if not updated_ticket:
                    raise ValueError("Ticket not found or access denied")
                
                logger.info(
                    f"Ticket updated via AI tool: {ticket_id}",
                    extra=execution_ctx.principal.get_audit_context()
                )
                
                return {
                    'id': str(updated_ticket.id),
                    'title': updated_ticket.title,
                    'description': updated_ticket.description,
                    'status': updated_ticket.status.value,
                    'category': updated_ticket.category.value,
                    'priority': updated_ticket.priority.value,
                    'urgency': updated_ticket.urgency.value,
                    'updated_at': updated_ticket.updated_at.isoformat(),
                    'assigned_to_id': str(updated_ticket.assigned_to_id) if updated_ticket.assigned_to_id else None,
                    'department': updated_ticket.department
                }
                
            except ValueError:
                raise
            except Exception as e:
                logger.error(
                    f"Failed to update ticket {ticket_id} via AI tool: {e}",
                    extra=execution_ctx.principal.get_audit_context()
                )
                raise ValueError(f"Ticket update failed: {e}")
        
        return toolset

    def _create_mcp_toolset(self):
        """Create MCP toolset integration (placeholder for future expansion)."""
        # This would integrate with external MCP servers
        # For now, we focus on local tools with direct service calls
        return None
    
    def _create_secure_composition(self):
        """Create the final secure toolset with filtering and approval."""
        from pydantic_ai.tools import FilteredToolset, ApprovalRequiredToolset
        
        # Start with local toolset
        base_toolset = self.local_toolset
        
        # Add MCP toolset if available
        if self.mcp_toolset:
            base_toolset = base_toolset + self.mcp_toolset
        
        # Apply permission filtering
        filtered_toolset = FilteredToolset(
            base_toolset,
            filter_func=self._permission_filter
        )
        
        # Apply approval requirements for sensitive operations
        secure_toolset = ApprovalRequiredToolset(
            filtered_toolset,
            approval_func=self._approval_required
        )
        
        return secure_toolset
    
    def _permission_filter(self, tool_name: str, ctx: RunContext[ToolExecutionContext]) -> bool:
        """Filter tools based on Principal permissions."""
        principal = ctx.deps.principal
        
        # Map tool names to required permissions
        permission_map = {
            'create_ticket': 'tickets.create',
            'list_tickets': 'tickets.read',
            'edit_ticket': 'tickets.update',
            'delete_ticket': 'tickets.delete',
            'get_ticket_stats': 'tickets.read'
        }
        
        required_permission = permission_map.get(tool_name)
        if not required_permission:
            # Unknown tool - deny by default
            return False
        
        return principal.has_permission(required_permission)
    
    async def _approval_required(self, tool_name: str, ctx: RunContext[ToolExecutionContext]) -> bool:
        """Determine if tool execution requires approval."""
        # Define sensitive operations that require approval
        sensitive_operations = [
            'delete_ticket',
            'bulk_update_tickets',
            'export_tickets',
            'admin_override'
        ]
        
        return tool_name in sensitive_operations
```

## FastMCP Integration with @tool Decorator

### Current MCP Server Structure (To Be Removed)

The existing MCP server in `/mcp_server/tools/ticket_tools.py` uses a registration pattern that will be completely replaced:

```python
# CURRENT APPROACH (TO BE REMOVED)
def register_create_ticket():
    @mcp.tool()
    async def create_ticket(title: str, description: str, ...):
        # Current implementation with HTTP calls and JWT tokens
        pass

def register_all_ticket_tools(mcp_instance: FastMCP):
    global mcp
    mcp = mcp_instance
    register_create_ticket()  # Manual registration
```

### New FastMCP Integration with Principal Context

```python
# NEW APPROACH - FastMCP with Principal Context
from fastmcp import FastMCP
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SecureMCPServer:
    """
    Secure MCP server that integrates with Principal-based authentication.
    Replaces the current mcp_server implementation entirely.
    """
    
    def __init__(self):
        self.mcp = FastMCP("Secure Ticket Management Server")
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize tools with Principal context support
        self._register_secure_tools()
    
    def _register_secure_tools(self):
        """Register all tools with FastMCP using @tool decorator and Principal context."""
        
        @self.mcp.tool()
        async def create_ticket(
            title: str,
            description: str,
            category: str = "general",
            priority: str = "medium",
            urgency: str = "medium",
            department: Optional[str] = None,
            assigned_to_id: Optional[str] = None,
            # Special context parameter for Principal authentication
            _mcp_context: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """
            Create a support ticket with AI categorization and Principal-based security.
            
            This tool integrates with FastMCP's @tool decorator while maintaining
            secure Principal-based authentication instead of raw JWT tokens.
            
            Args:
                title: Ticket title (required, max 500 chars)
                description: Detailed description (required)  
                category: Issue category
                priority: Priority level
                urgency: Urgency level
                department: Target department for routing
                assigned_to_id: UUID of user to assign ticket to
                _mcp_context: Internal MCP context with Principal (injected by middleware)
                
            Returns:
                Dict containing created ticket details with audit trail
            """
            from app.services.ticket_service import ticket_service
            
            # Extract Principal context from MCP middleware injection
            if not _mcp_context or 'principal' not in _mcp_context:
                raise ValueError("Authentication required: No Principal context available")
            
            principal = _mcp_context['principal']
            db_session = _mcp_context['db_session']
            
            # Create execution context
            execution_ctx = ToolExecutionContext(
                principal=principal,
                db_session=db_session,
                request_metadata=_mcp_context.get('metadata', {})
            )
            
            # Validate permissions using Principal
            execution_ctx.validate_permission('tickets.create')
            
            # Validate inputs with comprehensive checks
            if not title or len(title.strip()) == 0:
                raise ValueError("Title is required and cannot be empty")
            if not description or len(description.strip()) == 0:
                raise ValueError("Description is required and cannot be empty")
            if len(title) > 500:
                raise ValueError("Title cannot exceed 500 characters")
            
            # Validate enum values
            valid_categories = ['technical', 'billing', 'feature_request', 'bug', 'user_access', 'general']
            valid_priorities = ['low', 'medium', 'high', 'critical']
            
            if category not in valid_categories:
                raise ValueError(f"Category must be one of: {', '.join(valid_categories)}")
            if priority not in valid_priorities:
                raise ValueError(f"Priority must be one of: {', '.join(valid_priorities)}")
            if urgency not in valid_priorities:
                raise ValueError(f"Urgency must be one of: {', '.join(valid_priorities)}")
            
            # Prepare ticket data with Principal context (no raw JWT!)
            ticket_data = {
                'title': title.strip(),
                'description': description.strip(),
                'category': category,
                'priority': priority,
                'urgency': urgency,
                'organization_id': principal.organization_id,  # Organization isolation
                'created_by_id': principal.user_id,
                'department': department or principal.department,
                'source_channel': 'mcp_tool',
                'source_details': {
                    'tool_name': 'create_ticket',
                    'session_id': principal.session_id,
                    'mcp_server': True
                }
            }
            
            if assigned_to_id:
                ticket_data['assigned_to_id'] = assigned_to_id
            
            try:
                # Call service layer directly (NO HTTP API CALLS!)
                ticket = await ticket_service.create_ticket(
                    db=db_session,
                    ticket_data=ticket_data,
                    created_by_id=principal.user_id
                )
                
                # Audit log with Principal context
                logger.info(
                    f"Ticket created via MCP tool: {ticket.id}",
                    extra=principal.get_audit_context()
                )
                
                return {
                    'success': True,
                    'ticket': {
                        'id': str(ticket.id),
                        'title': ticket.title,
                        'description': ticket.description,
                        'status': ticket.status.value,
                        'category': ticket.category.value,
                        'priority': ticket.priority.value,
                        'urgency': ticket.urgency.value,
                        'organization_id': str(ticket.organization_id),
                        'created_by_id': str(ticket.created_by_id),
                        'created_at': ticket.created_at.isoformat(),
                        'department': ticket.department,
                        'assigned_to_id': str(ticket.assigned_to_id) if ticket.assigned_to_id else None
                    },
                    'audit': {
                        'created_by': principal.email,
                        'organization': principal.organization_name,
                        'session_id': principal.session_id,
                        'tool_source': 'mcp_server'
                    }
                }
                
            except Exception as e:
                logger.error(
                    f"Failed to create ticket via MCP tool: {e}",
                    extra=principal.get_audit_context()
                )
                return {
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
        
        @self.mcp.tool()
        async def list_tickets(
            page: int = 1,
            page_size: int = 10,
            status: Optional[str] = None,
            category: Optional[str] = None,
            priority: Optional[str] = None,
            assigned_to_me: bool = False,
            search_query: Optional[str] = None,
            _mcp_context: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """
            List tickets with filtering, pagination, and automatic organization isolation.
            """
            from app.services.ticket_service import ticket_service
            
            # Extract Principal context
            if not _mcp_context or 'principal' not in _mcp_context:
                raise ValueError("Authentication required: No Principal context available")
            
            principal = _mcp_context['principal']
            db_session = _mcp_context['db_session']
            
            # Create execution context
            execution_ctx = ToolExecutionContext(
                principal=principal,
                db_session=db_session,
                request_metadata=_mcp_context.get('metadata', {})
            )
            
            # Validate permissions
            execution_ctx.validate_permission('tickets.read')
            
            # Validate and normalize pagination
            page = max(1, page)
            page_size = min(max(1, page_size), 50)
            offset = (page - 1) * page_size
            
            # Build filters with organization context
            filters = {}
            if status:
                filters['status'] = [status]
            if category:
                filters['category'] = [category]
            if priority:
                filters['priority'] = [priority]
            if assigned_to_me:
                filters['assigned_to_id'] = principal.user_id
            if search_query:
                filters['search'] = search_query.strip()
            
            try:
                # Call service layer with organization isolation
                tickets, total = await ticket_service.list_tickets(
                    db=db_session,
                    organization_id=principal.organization_id,  # Automatic org filtering!
                    offset=offset,
                    limit=page_size,
                    filters=filters
                )
                
                # Convert to serializable format
                ticket_list = []
                for ticket in tickets:
                    ticket_list.append({
                        'id': str(ticket.id),
                        'title': ticket.title,
                        'status': ticket.status.value,
                        'category': ticket.category.value,
                        'priority': ticket.priority.value,
                        'urgency': ticket.urgency.value,
                        'created_at': ticket.created_at.isoformat(),
                        'created_by_id': str(ticket.created_by_id),
                        'assigned_to_id': str(ticket.assigned_to_id) if ticket.assigned_to_id else None,
                        'department': ticket.department,
                        'is_overdue': ticket.is_overdue,
                        'age_hours': round(ticket.age_in_hours, 2)
                    })
                
                logger.info(
                    f"Listed {len(ticket_list)} tickets via MCP tool",
                    extra=principal.get_audit_context()
                )
                
                return {
                    'success': True,
                    'tickets': ticket_list,
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total': total,
                        'total_pages': (total + page_size - 1) // page_size,
                        'has_next': page * page_size < total,
                        'has_prev': page > 1
                    },
                    'filters_applied': filters,
                    'organization_id': principal.organization_id
                }
                
            except Exception as e:
                logger.error(
                    f"Failed to list tickets via MCP tool: {e}",
                    extra=principal.get_audit_context()
                )
                return {
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
        
        @self.mcp.tool()
        async def edit_ticket(
            ticket_id: str,
            title: Optional[str] = None,
            description: Optional[str] = None,
            status: Optional[str] = None,
            priority: Optional[str] = None,
            category: Optional[str] = None,
            assigned_to_id: Optional[str] = None,
            internal_notes: Optional[str] = None,
            _mcp_context: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """
            Edit an existing ticket with comprehensive validation and organization isolation.
            """
            from app.services.ticket_service import ticket_service
            import uuid
            
            # Extract Principal context
            if not _mcp_context or 'principal' not in _mcp_context:
                raise ValueError("Authentication required: No Principal context available")
            
            principal = _mcp_context['principal']
            db_session = _mcp_context['db_session']
            
            # Create execution context
            execution_ctx = ToolExecutionContext(
                principal=principal,
                db_session=db_session,
                request_metadata=_mcp_context.get('metadata', {})
            )
            
            # Validate permissions
            execution_ctx.validate_permission('tickets.update')
            
            # Validate ticket ID format
            try:
                uuid.UUID(ticket_id)
            except ValueError:
                return {
                    'success': False,
                    'error': 'Invalid ticket ID format',
                    'error_type': 'ValueError'
                }
            
            # Build update data with validation
            update_data = {}
            
            if title is not None:
                if not title.strip():
                    return {'success': False, 'error': 'Title cannot be empty'}
                if len(title) > 500:
                    return {'success': False, 'error': 'Title cannot exceed 500 characters'}
                update_data['title'] = title.strip()
            
            if description is not None:
                if not description.strip():
                    return {'success': False, 'error': 'Description cannot be empty'}
                update_data['description'] = description.strip()
            
            if status is not None:
                valid_statuses = ['new', 'open', 'in_progress', 'pending', 'resolved', 'closed', 'cancelled']
                if status not in valid_statuses:
                    return {
                        'success': False, 
                        'error': f"Status must be one of: {', '.join(valid_statuses)}"
                    }
                update_data['status'] = status
            
            if priority is not None:
                valid_priorities = ['low', 'medium', 'high', 'critical']
                if priority not in valid_priorities:
                    return {
                        'success': False,
                        'error': f"Priority must be one of: {', '.join(valid_priorities)}"
                    }
                update_data['priority'] = priority
            
            if category is not None:
                valid_categories = ['technical', 'billing', 'feature_request', 'bug', 'user_access', 'general']
                if category not in valid_categories:
                    return {
                        'success': False,
                        'error': f"Category must be one of: {', '.join(valid_categories)}"
                    }
                update_data['category'] = category
            
            if assigned_to_id is not None:
                if assigned_to_id:  # Allow empty string to unassign
                    try:
                        uuid.UUID(assigned_to_id)
                        update_data['assigned_to_id'] = assigned_to_id
                    except ValueError:
                        return {'success': False, 'error': 'Invalid assigned_to_id format'}
                else:
                    update_data['assigned_to_id'] = None
            
            if internal_notes is not None:
                # Only admin users can set internal notes
                if not principal.is_admin():
                    return {
                        'success': False,
                        'error': 'Only administrators can set internal notes',
                        'error_type': 'PermissionError'
                    }
                update_data['internal_notes'] = internal_notes
            
            if not update_data:
                return {
                    'success': False,
                    'error': 'At least one field must be provided for update'
                }
            
            try:
                # Update ticket with organization isolation
                updated_ticket = await ticket_service.update_ticket(
                    db=db_session,
                    ticket_id=ticket_id,
                    organization_id=principal.organization_id,  # Organization isolation!
                    update_data=update_data
                )
                
                if not updated_ticket:
                    return {
                        'success': False,
                        'error': 'Ticket not found or access denied',
                        'error_type': 'NotFound'
                    }
                
                logger.info(
                    f"Ticket updated via MCP tool: {ticket_id}",
                    extra=principal.get_audit_context()
                )
                
                return {
                    'success': True,
                    'ticket': {
                        'id': str(updated_ticket.id),
                        'title': updated_ticket.title,
                        'description': updated_ticket.description,
                        'status': updated_ticket.status.value,
                        'category': updated_ticket.category.value,
                        'priority': updated_ticket.priority.value,
                        'urgency': updated_ticket.urgency.value,
                        'updated_at': updated_ticket.updated_at.isoformat(),
                        'assigned_to_id': str(updated_ticket.assigned_to_id) if updated_ticket.assigned_to_id else None,
                        'department': updated_ticket.department
                    },
                    'audit': {
                        'updated_by': principal.email,
                        'organization': principal.organization_name,
                        'session_id': principal.session_id,
                        'fields_updated': list(update_data.keys())
                    }
                }
                
            except Exception as e:
                logger.error(
                    f"Failed to update ticket {ticket_id} via MCP tool: {e}",
                    extra=principal.get_audit_context()
                )
                return {
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
    
    def get_mcp_app(self):
        """Get the FastMCP application for server startup."""
        return self.mcp

# Global MCP server instance
secure_mcp_server = SecureMCPServer()
```

### MCP Context Injection Middleware

The MCP server needs middleware to inject Principal context into tool calls:

```python
# NEW FILE: mcp_server/middleware/principal_injection.py
class PrincipalInjectionMiddleware:
    """
    Middleware to inject Principal context into MCP tool calls.
    This replaces JWT token passing with structured Principal objects.
    """
    
    def __init__(self, principal_service):
        self.principal_service = principal_service
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def process_tool_call(
        self, 
        tool_name: str, 
        args: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Process incoming tool call and inject Principal context.
        
        Args:
            tool_name: Name of the tool being called
            args: Tool arguments from client
            headers: HTTP headers from client request
            
        Returns:
            Updated args with _mcp_context injected
        """
        try:
            # Extract JWT from headers
            auth_header = headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                raise ValueError("Missing or invalid Authorization header")
            
            jwt_token = auth_header[7:]  # Remove 'Bearer ' prefix
            
            # Extract Principal (this is the ONLY place JWT tokens are handled!)
            from app.database import get_db_session
            from app.services.principal_service import principal_service
            
            async with get_db_session() as db:
                principal = await principal_service.extract_principal(
                    token=jwt_token,
                    db=db,
                    request_context={
                        'client_ip': headers.get('X-Forwarded-For'),
                        'user_agent': headers.get('User-Agent'),
                        'request_id': headers.get('X-Request-ID')
                    }
                )
                
                # Inject Principal context into tool args
                args['_mcp_context'] = {
                    'principal': principal,
                    'db_session': db,
                    'metadata': {
                        'tool_name': tool_name,
                        'request_headers': headers,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }
                
                self.logger.info(
                    f"Principal context injected for tool: {tool_name}",
                    extra=principal.get_audit_context()
                )
                
                return args
                
        except Exception as e:
            self.logger.error(f"Failed to inject Principal context: {e}")
            raise ValueError(f"Authentication failed: {e}")
```

## Complete Removal and Refactor Plan

### Phase 1: Remove Current MCP Implementation

```bash
# Files to be COMPLETELY REMOVED:
rm mcp_server/tools/ticket_tools.py           # Old tool registration pattern
rm mcp_server/tools/system_tools.py           # Replace with Principal-based tools  
rm mcp_server/tools/integration_tools.py      # Refactor to use Principal context
rm mcp_server/auth/token_service.py           # Replace with PrincipalService
rm mcp_server/auth/token_verifier.py          # No longer needed - Principal handles this
rm mcp_server/auth/middleware.py              # Replace with PrincipalInjectionMiddleware

# Directories to restructure:
mv mcp_server/start_mcp_server.py mcp_server/start_mcp_server.py.backup
```

### Phase 2: Create New Structure

```bash
# New MCP server structure:
mcp_server/
├── __init__.py
├── server.py                    # NEW: SecureMCPServer class
├── middleware/
│   ├── __init__.py
│   └── principal_injection.py  # NEW: Principal context injection
├── tools/
│   ├── __init__.py
│   └── secure_tools.py         # NEW: All tools with @tool decorator
└── start_server.py             # NEW: Server startup with Principal middleware
```

### Phase 3: Update Server Startup

```python
# NEW FILE: mcp_server/start_server.py
#!/usr/bin/env python3
"""
New MCP server startup with Principal-based authentication.
Replaces the old start_mcp_server.py entirely.
"""
import asyncio
import logging
from fastmcp import FastMCP

from mcp_server.server import secure_mcp_server
from mcp_server.middleware.principal_injection import PrincipalInjectionMiddleware
from app.services.principal_service import principal_service

async def start_secure_mcp_server():
    """Start the secure MCP server with Principal authentication."""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Get MCP app from secure server
    mcp_app = secure_mcp_server.get_mcp_app()
    
    # Initialize Principal injection middleware
    principal_middleware = PrincipalInjectionMiddleware(principal_service)
    
    # Register middleware with MCP server
    mcp_app.add_middleware(principal_middleware.process_tool_call)
    
    logger.info("🔐 Secure MCP Server starting with Principal authentication...")
    logger.info("📋 Available tools: create_ticket, list_tickets, edit_ticket")
    logger.info("🔒 Authentication: Principal-based (no raw JWT tokens in tools)")
    logger.info("🏢 Organization isolation: Automatic")
    
    # Start the server
    await mcp_app.run(host="0.0.0.0", port=8001)

if __name__ == "__main__":
    asyncio.run(start_secure_mcp_server())
```

### Phase 4: Update Docker Configuration

```yaml
# Update docker-compose.yml for new MCP server
version: '3.8'
services:
  mcp-server:
    build: .
    command: python mcp_server/start_server.py  # NEW startup script
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/ai_tickets
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./mcp_server:/app/mcp_server
      - ./app:/app/app  # Access to service layer
```

## Updated Implementation Plan with Complete Refactor

### Phase 1: Principal Authentication System (UPDATED)
**Duration**: 2 days  
**Priority**: Critical

#### Step 1.1: Create Principal Service (NEW)
- **File**: `app/services/principal_service.py`
- **Complete replacement** for JWT-only auth
- **Redis caching** with 15-minute TTL
- **Role-to-permission mapping** system
- **Organization context loading**

#### Step 1.2: Remove Old MCP Authentication (NEW)
- **Remove**: `mcp_server/auth/token_service.py`
- **Remove**: `mcp_server/auth/token_verifier.py`  
- **Remove**: `mcp_server/auth/middleware.py`
- **Backup**: Current MCP files before deletion

#### Step 1.3: Enhanced Auth Middleware (UPDATED)
- **File**: `app/middleware/auth_middleware.py`
- **Add**: `get_current_principal()` dependency
- **Integrate**: PrincipalService for JWT → Principal conversion
- **Update**: All endpoints to use Principal instead of User

#### Validation Criteria (UPDATED)
- [ ] JWT token successfully extracts Principal with all fields
- [ ] Principal contains permissions derived from roles
- [ ] Redis caching works for Principal objects  
- [ ] Organization isolation enforced via Principal.organization_id
- [ ] Old MCP auth files completely removed

#### Tests Required (UPDATED)
```bash
# Test Principal extraction with caching
poetry run pytest tests/unit/services/test_principal_service.py -v

# Test Principal in API endpoints
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/tickets \
  | jq '.items[0].organization_id'  # Should match user's org

# Verify old MCP auth removed
ls mcp_server/auth/  # Should not exist or be empty
```

### Phase 2: Complete MCP Server Refactor (UPDATED)
**Duration**: 2.5 days  
**Priority**: Critical

#### Step 2.1: Remove All Current MCP Tools (NEW)
- **Remove**: `mcp_server/tools/ticket_tools.py` (898 lines)
- **Remove**: `mcp_server/tools/system_tools.py`
- **Remove**: `mcp_server/tools/integration_tools.py`
- **Remove**: `mcp_server/start_mcp_server.py`
- **Create backup** of current implementation

#### Step 2.2: Create New SecureMCPServer (NEW)
- **File**: `mcp_server/server.py`
- **FastMCP integration** with `@tool` decorator
- **Principal context injection** via `_mcp_context` parameter
- **Direct service layer calls** (NO HTTP API calls)
- **Comprehensive error handling** with success/error responses

#### Step 2.3: Create Principal Injection Middleware (NEW)
- **File**: `mcp_server/middleware/principal_injection.py`
- **JWT extraction** from Authorization header
- **Principal creation** via PrincipalService
- **Context injection** into all tool calls
- **Database session management**

#### Step 2.4: New MCP Server Startup (NEW) 
- **File**: `mcp_server/start_server.py`
- **Replace**: `start_mcp_server.py` entirely
- **Principal middleware registration**
- **FastMCP app configuration**
- **Logging and monitoring setup**

#### Validation Criteria (UPDATED)
- [ ] All old MCP files removed and backed up
- [ ] New MCP server starts with Principal authentication
- [ ] Tools receive Principal via `_mcp_context` parameter
- [ ] create_ticket calls ticket_service.create_ticket() directly
- [ ] list_tickets enforces organization isolation automatically
- [ ] edit_ticket validates permissions and updates tickets
- [ ] No HTTP calls between MCP tools and FastAPI endpoints

#### Tests Required (UPDATED)
```bash
# Test new MCP server startup
docker compose up -d mcp-server
docker compose logs mcp-server | grep "Principal authentication"

# Test create_ticket tool with Principal context
curl -X POST http://localhost:8001/mcp/tools/create_ticket \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title": "Test Ticket", "description": "Test from new MCP"}' \
  | jq '.success'  # Should be true

# Test list_tickets with organization filtering
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/mcp/tools/list_tickets \
  | jq '.tickets[].organization_id' | uniq  # Should be single org ID

# Verify no HTTP calls to FastAPI from MCP
docker compose logs mcp-server | grep "HTTP.*8000"  # Should be empty
```

### Phase 3: Pydantic AI Toolset Integration (UPDATED)
**Duration**: 1.5 days  
**Priority**: High

#### Step 3.1: Create ToolExecutionContext (NEW)
- **File**: `app/toolsets/context.py`
- **Principal + database access** for tool execution
- **Permission validation helpers**
- **Organization access enforcement**

#### Step 3.2: Create SecureTicketToolset (NEW)
- **File**: `app/toolsets/ticket_toolset.py`
- **FunctionToolset** with create/list/edit tools
- **FilteredToolset** with permission-based filtering
- **ApprovalRequiredToolset** for sensitive operations
- **Complete toolset composition**

#### Step 3.3: Integrate with Pydantic AI Agent (NEW)
- **File**: `app/agents/ticket_agent.py`
- **Agent initialization** with SecureTicketToolset
- **RunContext[ToolExecutionContext]** support
- **Principal-aware tool execution**

#### Validation Criteria (UPDATED)
- [ ] ToolExecutionContext replaces raw JWT tokens
- [ ] SecureTicketToolset composes all security layers
- [ ] Permission filtering blocks unauthorized tool access
- [ ] Approval workflow triggers for sensitive operations
- [ ] Pydantic AI Agent integrates with secure toolset
- [ ] All tools enforce organization isolation via Principal

#### Tests Required (UPDATED)
```bash
# Test toolset permission filtering
docker compose exec app python -c "
from app.toolsets.ticket_toolset import SecureTicketToolset
from app.services.principal_service import Principal

# Test with limited permissions
principal = Principal(
    user_id='test', organization_id='org1', 
    permissions={'tickets.read': True}  # No create permission
)
toolset = SecureTicketToolset()
# Should filter out create_ticket tool
print('Available tools:', toolset.get_available_tools(principal))
"

# Test tool execution with Principal
docker compose exec app python -c "
import asyncio
from app.toolsets.context import ToolExecutionContext
from app.agents.ticket_agent import TicketAgent

async def test():
    agent = TicketAgent()
    result = await agent.run('Create a ticket for login issues')
    print('Agent result:', result.data)

asyncio.run(test())
"
```

### Phase 4: End-to-End Integration and Validation (UPDATED)
**Duration**: 1 day  
**Priority**: Critical

#### Step 4.1: Integration Testing (UPDATED)
- **FastAPI ↔ Principal Service** integration
- **Principal ↔ MCP Server** context passing  
- **MCP Tools ↔ Service Layer** direct calls
- **Pydantic AI ↔ Secure Toolset** integration

#### Step 4.2: Security Validation (NEW)
- **Organization isolation** testing with multiple orgs
- **Permission enforcement** with different user roles
- **JWT token boundary** verification (only in middleware)
- **Audit logging** validation for all tool calls

#### Step 4.3: Performance and Load Testing (NEW)
- **Principal caching** performance with Redis (15-minute TTL optimization)
- **Concurrent tool calls** with different users (connection pooling)
- **Database connection** management under load (SQLAlchemy async pool)
- **Memory usage** with Principal objects (object pooling and cleanup)
- **AI agent response times** under concurrent requests
- **WebSocket connection scaling** for real-time updates
- **File processing throughput** with Celery worker optimization

#### Final Validation Criteria (COMPREHENSIVE)
- [ ] Complete removal of old MCP implementation verified
- [ ] New MCP server handles all ticket operations via Principal
- [ ] Zero JWT tokens in tool layer confirmed
- [ ] Organization isolation perfect (0 cross-org data leaks)
- [ ] Permission system blocks unauthorized operations
- [ ] Audit logs capture all tool executions with Principal context
- [ ] Performance meets enhanced requirements (<50ms tool filtering overhead)
- [ ] Load testing passes with 500 concurrent requests
- [ ] AI agent response times under 2 seconds for ticket creation
- [ ] WebSocket connections scale to 1000+ concurrent users
- [ ] Database query performance optimized with proper indexing
- [ ] Redis caching hit ratio above 90%
- [ ] Celery task processing under 5 seconds for file operations
- [ ] Security audit confirms no authentication bypass vectors

#### Final End-to-End Test (NEW)
```bash
# Complete workflow test
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"user@org1.com","password":"password"}' \
  -H "Content-Type: application/json" | jq -r .access_token)

# Test via FastAPI (should create ticket with Principal)
curl -X POST http://localhost:8000/api/v1/tickets/ai-create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Cannot access login page, getting 404 errors"}'

# Test via MCP server (should create ticket with same Principal) 
curl -X POST http://localhost:8001/mcp/tools/create_ticket \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "MCP Test Ticket", "description": "Direct MCP tool call"}'

# Verify both tickets belong to same organization
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/tickets \
  | jq '.items[] | {id, title, organization_id}' \
  | jq 'group_by(.organization_id) | length'  # Should be 1 (same org)

# Test with different org user (should see different tickets)
TOKEN2=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"user@org2.com","password":"password"}' \
  -H "Content-Type: application/json" | jq -r .access_token)

curl -H "Authorization: Bearer $TOKEN2" http://localhost:8000/api/v1/tickets \
  | jq '.items | length'  # Should be 0 (different org, no tickets)
```

## **IMPLEMENTATION STATUS SUMMARY** 📋

### ✅ What's Currently Working (September 2025)
1. **Dual Authentication System**: Clerk + API tokens working properly
2. **Organization Isolation**: Enforced via `current_user.organization_id`  
3. **MCP Tools**: All ticket tools functional with JWT authentication
4. **AI Ticket Creation**: Basic AI service creates tickets (legacy implementation)
5. **API Endpoints**: Full CRUD operations with proper auth middleware

### ❌ What Needs Implementation (Priority Order)
1. **Principal Service**: Create `/app/services/principal_service.py` with permission mapping
2. **Tool Permission Filtering**: Implement `TOOL_PERMISSION_MAP` and agent toolset filtering
3. **MCP Security Layer**: Replace JWT tokens with Principal objects in tools
4. **AI Agent Integration**: Connect Pydantic AI agents with filtered MCP tools  
5. **Permission Management API**: Admin endpoints for role/permission management
6. **Centralized Authorization**: Unified permission checking across all layers

### 🔐 **Permission Management Implementation Plan**

#### **Database Schema Changes**
```sql
-- Add permission tracking to users table
ALTER TABLE users ADD COLUMN custom_permissions JSONB DEFAULT '{}';
ALTER TABLE users ADD COLUMN effective_permissions JSONB DEFAULT '{}'; -- Computed permissions cache

-- Add permission tracking to API tokens
ALTER TABLE api_tokens ADD COLUMN permissions TEXT[] DEFAULT ARRAY[]::TEXT[];

-- Create permission audit log
CREATE TABLE permission_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    action VARCHAR(50) NOT NULL, -- 'granted', 'revoked', 'role_changed'
    permission_name VARCHAR(255),
    old_value JSONB,
    new_value JSONB,
    changed_by_user_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### **Admin API Endpoints**
```python
# Permission Management API (admin only)
@router.post("/api/v1/admin/users/{user_id}/permissions")
async def grant_user_permission(user_id: str, permission: str, current_user: User):
    # Requires 'users.manage' permission
    
@router.delete("/api/v1/admin/users/{user_id}/permissions/{permission}")  
async def revoke_user_permission(user_id: str, permission: str, current_user: User):
    # Requires 'users.manage' permission

@router.put("/api/v1/admin/users/{user_id}/role")
async def change_user_role(user_id: str, new_role: str, current_user: User):
    # Requires 'users.manage' permission + audit logging
    
@router.get("/api/v1/admin/permissions/audit")
async def get_permission_audit_log(current_user: User):
    # Requires 'users.*' permission
```

#### **Runtime Permission Checks**
```python
# Permission checking in API endpoints
@require_permission("tickets.create")
async def create_ticket(ticket_data, current_user: User):
    principal = await principal_service.get_principal_for_user(current_user)
    
    if not principal.has_permission("tickets.create"):
        raise HTTPException(403, "Insufficient permissions")
        
# Permission checking in MCP tools
async def create_ticket_tool(context):
    principal = context.principal  # Injected by MCP middleware
    
    if not principal.has_permission("tickets.create"):
        return "Error: You don't have permission to create tickets"
```

#### **Permission Testing Strategy**
```python
# Unit tests for permission system
def test_exact_permission():
    principal = Principal(permissions={"tickets.create": True})
    assert principal.has_permission("tickets.create") == True
    assert principal.has_permission("tickets.delete") == False

def test_wildcard_permission():
    principal = Principal(permissions={"tickets.*": True})
    assert principal.has_permission("tickets.create") == True
    assert principal.has_permission("tickets.delete") == True
    assert principal.has_permission("users.read") == False

def test_global_admin_permission():
    principal = Principal(permissions={"*": True})
    assert principal.has_permission("tickets.create") == True
    assert principal.has_permission("users.delete") == True
    assert principal.has_permission("users.*") == True

def test_agent_tool_filtering():
    principal = Principal(permissions={"tickets.read": True})
    tools = ["create_ticket", "list_tickets", "delete_ticket"]
    
    filtered = filter_tools_by_permissions(tools, principal)
    assert filtered == ["list_tickets"]  # Only read permission
```

### 🗑️ Deprecated Code Removed
- ❌ `mcp_server/auth/token_service.py` - Thread-based token storage
- ❌ `mcp_server/auth/token_verifier.py` - Basic JWT verification  
- ❌ `mcp_server/auth/middleware.py` - Non-Principal FastMCP middleware
- ❌ `mcp_server/auth/` directory - Entire deprecated auth module

### 📈 Current System Assessment
**Security**: ✅ Working (JWT/API tokens validated at boundaries)  
**Functionality**: ✅ Working (All ticket operations functional)  
**Architecture**: ⚠️ Suboptimal (No Principal abstraction, JWT tokens in tools)  
**Scalability**: ✅ Working (Organization isolation enforced)  
**Maintainability**: ❌ Needs improvement (Auth logic scattered, no unified permissions)

### 🚀 Next Steps for Implementation
1. **Create Principal Service** - Implement the service referenced throughout docs
2. **Refactor MCP Authentication** - Replace JWT extraction with Principal injection
3. **Add Permission Layer** - Implement role-based access control
4. **Integrate AI Agents** - Connect Pydantic AI with secure MCP tools
5. **Add Centralized Logging** - Audit trail for all Principal-based operations

**CONCLUSION**: The current system is functional and secure but lacks the architectural improvements outlined in this PRP. The Principal-based authentication system remains unimplemented despite extensive documentation.
        async def create_ticket(
            ctx: RunContext[Principal],
            title: str,
            description: str,
            category: str = "general",
            priority: str = "medium"
        ) -> Dict[str, Any]:
            # Access Principal through ctx.deps
            principal = ctx.deps
            
            # Create ticket with org context
            ticket_data = {
                "title": title,
                "description": description,
                "category": category,
                "priority": priority,
                "organization_id": principal.organization_id,
                "created_by_id": principal.user_id
            }
            
            # Call service layer
            ticket = await ticket_service.create_ticket(
                db=ctx.db,
                ticket_data=ticket_data,
                created_by_id=principal.user_id
            )
            return ticket.to_dict()
```

#### MCP Server Integration
```python
from pydantic_ai.tools import MCPToolset

class MCPIntegrationToolset:
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.toolset = MCPToolset(mcp_client)
    
    async def get_available_tools(self, principal: Principal) -> List[str]:
        # Get all MCP tools and filter based on permissions
        all_tools = await self.mcp_client.list_tools()
        return [
            tool.name for tool in all_tools 
            if principal.has_permission(f"mcp.{tool.name}")
        ]
```

#### Combined Toolset with Filtering
```python
from pydantic_ai.tools import FilteredToolset, ApprovalRequiredToolset

class SecureTicketToolset:
    def __init__(self, local_toolset, mcp_toolset):
        # Combine toolsets
        combined = local_toolset + mcp_toolset
        
        # Apply filtering based on Principal
        self.filtered_toolset = FilteredToolset(
            combined,
            filter_func=self._permission_filter
        )
        
        # Apply approval for sensitive operations
        self.secure_toolset = ApprovalRequiredToolset(
            self.filtered_toolset,
            approval_func=self._approval_required
        )
    
    def _permission_filter(self, tool_name: str, ctx: RunContext[Principal]) -> bool:
        principal = ctx.deps
        
        # RBAC/ABAC logic
        if tool_name == "create_ticket":
            return principal.has_permission("tickets.create")
        elif tool_name == "list_tickets":
            return principal.has_permission("tickets.read")
        elif tool_name == "edit_ticket":
            return principal.has_permission("tickets.update")
        
        return False
    
    async def _approval_required(self, tool_name: str, ctx: RunContext[Principal]) -> bool:
        # Require approval for high-impact operations
        sensitive_ops = ["delete_ticket", "bulk_update_tickets"]
        return tool_name in sensitive_ops
```

## Implementation Plan

### Phase 1: Principal Authentication System
**Duration**: 2 days  
**Priority**: Critical

#### Step 1.1: Create Principal Service
- **File**: `app/services/principal_service.py`
- **Dependencies**: `auth_middleware.py`, `user.py`, `organization.py`
- **Tasks**:
  1. Implement `Principal` dataclass
  2. Create `PrincipalService.extract_principal()`
  3. Add permission mapping logic
  4. Implement role-based permission calculation

#### Step 1.2: Enhance Auth Middleware
- **File**: `app/middleware/auth_middleware.py`
- **Tasks**:
  1. Add `get_current_principal()` dependency
  2. Integrate with `PrincipalService`
  3. Cache Principal in request context
  4. Update existing endpoints to use Principal

#### Step 1.3: Update API Endpoints
- **File**: `app/api/v1/tickets.py`
- **Tasks**:
  1. Replace `User` dependency with `Principal`
  2. Use Principal for authorization checks
  3. Pass Principal context to services
  4. Update permission validation

#### Validation Criteria
- [ ] JWT token successfully extracts Principal
- [ ] Principal contains correct user/org/roles data
- [ ] API endpoints receive Principal instead of raw User
- [ ] Permission checks work with Principal.has_permission()
- [ ] Organization isolation maintained through Principal.organization_id

#### Tests Required
```bash
# Test Principal extraction
poetry run pytest tests/unit/services/test_principal_service.py -v

# Test API with Principal
poetry run pytest tests/integration/api/test_tickets_principal.py -v

# Test permission validation
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/tickets \
  | jq '.items | length' # Should return tickets for user's org only
```

### Phase 2: Local Function Toolset
**Duration**: 1.5 days  
**Priority**: High

#### Step 2.1: Create Ticket Management Toolset
- **File**: `app/toolsets/ticket_toolset.py`
- **Tasks**:
  1. Implement `TicketManagementToolset` class
  2. Create `create_ticket` tool with Principal context
  3. Create `list_tickets` tool with org filtering
  4. Create `edit_ticket` tool with permission checks
  5. Add input validation and error handling

#### Step 2.2: Integrate with Pydantic AI Agent
- **File**: `app/agents/ticket_agent.py`
- **Tasks**:
  1. Create new `TicketAgent` class
  2. Initialize with `TicketManagementToolset`
  3. Configure with appropriate model and temperature
  4. Add RunContext[Principal] support

#### Validation Criteria
- [ ] Tools receive Principal through RunContext.deps
- [ ] create_ticket creates tickets with correct org/user context
- [ ] list_tickets filters by organization_id from Principal
- [ ] edit_ticket validates permissions before updates
- [ ] All tools handle errors gracefully

#### Tests Required
```bash
# Test toolset functions
poetry run pytest tests/unit/toolsets/test_ticket_toolset.py -v

# Test agent integration
poetry run pytest tests/integration/agents/test_ticket_agent.py -v

# Test with Docker container
docker compose exec app python -c "
from app.toolsets.ticket_toolset import TicketManagementToolset
from app.services.principal_service import Principal
import asyncio

async def test():
    principal = Principal(user_id='test', organization_id='test-org')
    toolset = TicketManagementToolset()
    result = await toolset.create_ticket.func(principal, 'Test', 'Description')
    print('Ticket created:', result['id'])

asyncio.run(test())
"
```

### Phase 3: MCP Server Toolset Integration
**Duration**: 2 days  
**Priority**: High

#### Step 3.1: Enhance MCP Client
- **File**: `mcp_client/client.py`
- **Tasks**:
  1. Add `MCPIntegrationToolset` class
  2. Implement tool discovery with permissions
  3. Add Principal context passing to MCP calls
  4. Create tool availability filtering

#### Step 3.2: Update MCP Server
- **File**: `mcp_server/tools/ticket_tools.py`
- **Tasks**:
  1. Update tools to accept Principal context
  2. Remove raw JWT token handling
  3. Use Principal for all authorization
  4. Update http_client to pass Principal headers

#### Step 3.3: Create MCP Auth Middleware
- **File**: `mcp_server/auth/principal_middleware.py`
- **Tasks**:
  1. Extract Principal from incoming requests
  2. Validate permissions for MCP tool access
  3. Pass Principal to tool context
  4. Handle auth failures gracefully

#### Validation Criteria
- [ ] MCP client discovers tools based on Principal permissions
- [ ] MCP server receives Principal context, not raw tokens
- [ ] Tool filtering works based on user roles/scopes
- [ ] Cross-service calls maintain Principal context
- [ ] Auth failures return helpful error messages

#### Tests Required
```bash
# Test MCP toolset
poetry run pytest tests/integration/mcp/test_mcp_toolset.py -v

# Test MCP server with Principal
curl -H "X-Principal: {\"user_id\":\"test\",\"org_id\":\"org1\"}" \
  http://localhost:8001/mcp/tools/list_tickets

# Test tool filtering
docker compose exec mcp-server python -c "
from mcp_server.auth.principal_middleware import extract_principal
principal = extract_principal({'user_id': 'test', 'roles': ['viewer']})
print('Available tools:', principal.get_allowed_tools())
"
```

### Phase 4: Filtered and Approval Toolsets
**Duration**: 1.5 days  
**Priority**: Medium

#### Step 4.1: Implement Permission Filtering
- **File**: `app/toolsets/secure_toolset.py`
- **Tasks**:
  1. Create `SecureTicketToolset` class
  2. Implement `FilteredToolset` with RBAC logic
  3. Add dynamic permission checking
  4. Create permission matrix configuration

#### Step 4.2: Add Approval Workflow
- **File**: `app/toolsets/approval_toolset.py`
- **Tasks**:
  1. Implement `ApprovalRequiredToolset`
  2. Create approval logic for sensitive operations
  3. Add audit logging for approved actions
  4. Integrate with notification system

#### Step 4.3: Combine All Toolsets
- **File**: `app/toolsets/__init__.py`
- **Tasks**:
  1. Create unified toolset factory
  2. Compose local + MCP + filtering + approval
  3. Add configuration-based toolset selection
  4. Create toolset registry

#### Validation Criteria
- [ ] Tool filtering prevents unauthorized access
- [ ] Approval workflow triggers for sensitive operations
- [ ] Combined toolset includes all required tools
- [ ] Permission matrix correctly enforces access control
- [ ] Audit logs capture tool usage and approvals

#### Tests Required
```bash
# Test permission filtering
poetry run pytest tests/unit/toolsets/test_secure_toolset.py -v

# Test approval workflow
poetry run pytest tests/integration/toolsets/test_approval_workflow.py -v

# End-to-end test
docker compose exec app python -c "
from app.toolsets import create_secure_toolset
from app.services.principal_service import create_principal
import asyncio

async def test():
    principal = await create_principal('user_token')
    toolset = create_secure_toolset(principal)
    # This should require approval
    result = await toolset.run_tool('delete_ticket', ticket_id='123')
    print('Result:', result)

asyncio.run(test())
"
```

### Phase 5: Integration and End-to-End Testing
**Duration**: 1 day  
**Priority**: Critical

#### Step 5.1: Full System Integration
- **Tasks**:
  1. Integrate all components in main application
  2. Update agent initialization with secure toolsets
  3. Add comprehensive error handling
  4. Update API documentation

#### Step 5.2: Performance Testing
- **Tasks**:
  1. Load test with 500+ concurrent requests (enhanced from basic testing)
  2. Measure toolset overhead (<25ms target)
  3. Optimize permission checking with Redis caching
  4. Profile memory usage with Principal object pooling
  5. Stress test WebSocket connections (1000+ concurrent)
  6. Benchmark AI agent response times (2s target for 95th percentile)
  7. Test Celery worker scaling under high file processing load
  8. Validate database connection pool efficiency

#### Step 5.3: Security Validation
- **Tasks**:
  1. Test with various user roles/permissions
  2. Validate organization isolation
  3. Test token expiration handling
  4. Security audit of Principal extraction

#### Final Validation Criteria
- [ ] All ticket management operations work with Principal auth
- [ ] Users can only access their organization's data
- [ ] Tool filtering prevents unauthorized operations
- [ ] Approval workflow functions correctly
- [ ] Performance meets enhanced thresholds (<25ms for tool filtering)
- [ ] Load testing with 500 concurrent users passes
- [ ] AI agent response times under 2 seconds (95th percentile)
- [ ] WebSocket scaling to 1000+ concurrent connections
- [ ] Redis cache hit ratio above 90%
- [ ] Security audit passes all checks

#### End-to-End Tests
```bash
# Full integration test
poetry run pytest tests/e2e/test_secure_ticket_management.py -v

# Performance test suite
docker compose exec app python scripts/test_toolset_performance.py

# Enhanced performance tests
docker compose exec app python scripts/test_concurrent_load.py --users 500
docker compose exec app python scripts/test_websocket_scaling.py --connections 1000
docker compose exec app python scripts/test_ai_agent_performance.py --iterations 100
docker compose exec app python scripts/test_redis_cache_performance.py
docker compose exec app python scripts/test_database_pool_efficiency.py

# Stress test with monitoring
docker compose exec app python scripts/stress_test_with_metrics.py --duration 300

# Security test
docker compose exec app python scripts/security_audit.py

# Manual API test with real authentication
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"test@example.com","password":"password"}' \
  -H "Content-Type: application/json" | jq -r .access_token)

# Test ticket creation through AI
curl -X POST http://localhost:8000/api/v1/tickets/ai-create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "I need help with login issues",
    "conversation_context": []
  }'

# Verify ticket was created with correct organization
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/tickets | jq '.items[0].organization_id'
```

## Risk Assessment and Mitigation

### High Risk Items
1. **Token Security**: Raw tokens not passed through tools
   - **Mitigation**: Implement Principal extraction at API boundaries only
2. **Permission Bypass**: Tool filtering could be circumvented
   - **Mitigation**: Multiple layers of authorization checks
3. **Performance Impact**: Additional auth overhead
   - **Mitigation**: Cache Principal objects and permissions

### Medium Risk Items
1. **MCP Integration Complexity**: Cross-service auth coordination
   - **Mitigation**: Comprehensive integration testing
2. **Approval Workflow**: Could block critical operations
   - **Mitigation**: Configurable approval requirements

## Success Metrics

### Functional Requirements
- [ ] 100% of ticket operations work with Principal-based auth
- [ ] Organization isolation maintained (0 cross-org data leaks)
- [ ] Permission filtering blocks unauthorized operations
- [ ] Approval workflow processes sensitive operations

### Performance Requirements  
- [ ] Tool filtering adds <25ms latency (enhanced from <50ms)
- [ ] Principal extraction adds <5ms per request (enhanced from <10ms)
- [ ] System handles 500 concurrent authenticated requests (enhanced from 100)
- [ ] Database connection pool maintains 95% availability under load
- [ ] Redis caching reduces principal lookup time by 80%
- [ ] AI agent processing time under 2 seconds for 95th percentile
- [ ] WebSocket message latency under 100ms for real-time updates
- [ ] File processing queue maintains throughput of 100 files/minute

### Security Requirements
- [ ] Zero raw JWT tokens in tool layer
- [ ] All operations auditable through Principal context
- [ ] Permission changes take effect immediately
- [ ] Token expiration properly handled

## Performance and Scalability Architecture

### Caching Strategy
- **Redis Principal Cache**: 15-minute TTL with smart invalidation on permission changes
- **Database Query Cache**: Optimized with proper indexing on user_id, organization_id
- **Tool Authorization Cache**: Permission sets cached per user/organization combination
- **AI Model Response Cache**: Cache frequently requested categorizations and responses

### Connection Management
- **Database Pool**: SQLAlchemy async connection pool (min: 5, max: 20 connections)
- **Redis Pool**: Connection pool with automatic failover and circuit breaker
- **WebSocket Management**: Connection pooling with heartbeat monitoring
- **HTTP Client Pool**: Reusable connections for external API calls

### Horizontal Scaling Support
- **Stateless Design**: All components designed for horizontal scaling
- **Load Balancer Ready**: Health checks and graceful shutdown support
- **Database Sharding Ready**: Organization-based data partitioning capability
- **Celery Auto-scaling**: Dynamic worker scaling based on queue depth

### Performance Monitoring
- **Metrics Collection**: Prometheus-compatible metrics for all operations
- **Response Time Tracking**: P50, P95, P99 percentiles for all endpoints
- **Resource Usage Monitoring**: Memory, CPU, and database connection tracking
- **Alert Thresholds**: Automated alerts for performance degradation

## Rollout Plan

### Development Environment
1. Implement all phases in feature branch
2. Run comprehensive test suite
3. Security review and approval
4. Merge to main branch

### Staging Environment
1. Deploy with feature flags and performance monitoring
2. Run enhanced load tests (500+ concurrent users)
3. Validate with test users and performance benchmarks
4. Performance optimization and Redis cache tuning
5. WebSocket scaling validation
6. AI agent response time optimization

### Production Environment
1. Gradual rollout with comprehensive monitoring and alerting
2. Fallback plan to previous implementation with performance baselines
3. Monitor error rates, response times, and resource utilization
4. Auto-scaling configuration for Celery workers
5. Performance dashboard with real-time metrics
6. Full rollout after validation of all performance requirements

## Conclusion

This implementation will provide a secure, high-performance, scalable foundation for AI-powered ticket management using Pydantic AI toolsets. The Principal-based authentication system ensures proper authorization while maintaining clean separation of concerns between authentication and business logic.

The enhanced performance architecture supports horizontal scaling with optimized caching strategies, connection pooling, and comprehensive monitoring. The system is designed to handle 500+ concurrent users with sub-2-second AI response times and 90%+ cache hit ratios.

The phased approach allows for incremental validation and reduces risk, while the comprehensive testing strategy ensures reliability, security, and performance at scale.