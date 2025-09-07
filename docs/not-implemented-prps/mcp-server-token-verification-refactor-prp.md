# PRP: MCP Server Authentication Refactor - Token Verification Approach

**Status:** Not Implemented  
**Priority:** High  
**Complexity:** Medium  
**Impact:** Critical  

## Background

The current MCP server authentication implementation is failing with 401 Unauthorized errors when calling MCP tools. The current OAuth 2.1 approach with FastMCP middleware is overly complex and not working correctly. We need to refactor to a simpler, more reliable token verification approach.

### Current Issues
- MCP server returns 401 Unauthorized on tool calls
- Complex OAuth middleware is commented out and non-functional  
- MCP tools require authentication but receive "auth_required" status
- Misalignment between core app JWT authentication and MCP server auth

## Proposed Solution

Refactor the MCP server to act as a **pure resource server** using token verification, following the pattern from https://gofastmcp.com/servers/auth/token-verification.

### Key Principles
1. **Pure Resource Server**: MCP server validates tokens but doesn't manage user identity
2. **Token Verification**: Use cryptographic validation of JWTs issued by the core app
3. **Delegation**: Core app handles user authentication, MCP server handles authorization
4. **Simplicity**: Remove complex OAuth flows, use direct JWT validation

## Implementation Plan

### Phase 1: Remove Complex OAuth Infrastructure

#### Step 1.1: Clean Up OAuth Components
- Remove `oauth_resource_server.py`
- Remove `oauth_discovery.py` 
- Remove OAuth discovery endpoints from `start_mcp_server.py`
- Remove commented OAuth middleware class
- Keep tool registration but remove auth checks

**Files to modify:**
- `mcp_server/start_mcp_server.py`
- Remove: `mcp_server/oauth_resource_server.py`
- Remove: `mcp_server/oauth_discovery.py`

#### Step 1.2: Simplify MCP Server Startup
- Remove OAuth server URL configuration
- Remove complex discovery routes
- Keep core FastMCP initialization and tool registration

### Phase 2: Implement Token Verification

#### Step 2.1: Create JWT Token Verifier
Create `mcp_server/token_verifier.py` with:
- `JWTTokenVerifier` class for HMAC validation
- Use same JWT_SECRET_KEY as core app
- Support for HS256 algorithm (matching core app)
- Token expiration validation
- User ID and claims extraction

#### Step 2.2: Create Simple Auth Middleware
Create `mcp_server/auth_middleware.py` with:
- `TokenAuthMiddleware` for FastMCP
- Extract Authorization header from HTTP requests
- Validate JWT tokens using token verifier
- Store user context for tool access
- Handle authentication errors gracefully

#### Step 2.3: Implement Tool Authorization
- Add user context to tool calls
- Validate user permissions for tool access
- Implement scope-based authorization (read/write/admin)
- Provide user information to tools that need it

### Phase 3: Update Tool Integration

#### Step 3.1: Modify Tool Implementations
Update all tools in `mcp_server/tools/` to:
- Accept user context from middleware
- Make authenticated requests to backend API
- Pass through user JWT token to backend
- Handle authentication errors properly

**Tools to update:**
- `mcp_server/tools/ticket_tools.py`
- `mcp_server/tools/integration_tools.py`
- `mcp_server/tools/system_tools.py`

#### Step 3.2: Backend API Integration
- Ensure backend API accepts JWT tokens from MCP server
- Add user context to all API calls
- Maintain proper organization isolation
- Handle token refresh if needed

### Phase 4: Testing and Validation

#### Step 4.1: Unit Tests
Create comprehensive tests for:
- Token verification functionality
- Auth middleware behavior
- Tool authorization logic
- Error handling scenarios

**Test files to create:**
- `tests/test_mcp_token_verification.py`
- `tests/test_mcp_auth_middleware.py`
- `tests/test_mcp_tool_authorization.py`

#### Step 4.2: Integration Tests
Update existing tests to:
- Use JWT tokens for MCP tool calls
- Test authenticated tool access
- Verify user context passing
- Test error scenarios

**Test files to update:**
- `tests/test_mcp_server.py`
- `tests/test_websocket_protocols.py`
- `tests/test_integration_comprehensive.py`

#### Step 4.3: End-to-End Validation
- Test complete authentication flow
- Verify tool calls with proper authentication
- Validate error responses
- Ensure no Docker log errors
- Run full test suite

## Technical Implementation Details

### JWT Token Verification
```python
# mcp_server/token_verifier.py
import jwt
from typing import Dict, Any, Optional

class JWTTokenVerifier:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return claims"""
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
```

### FastMCP Auth Middleware
```python
# mcp_server/auth_middleware.py
from fastmcp.server.middleware import Middleware, MiddlewareContext

class TokenAuthMiddleware(Middleware):
    def __init__(self, token_verifier: JWTTokenVerifier):
        self.token_verifier = token_verifier
    
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        # Extract Authorization header
        auth_header = self.get_auth_header(context)
        if not auth_header:
            raise ToolError("Authorization required")
        
        # Verify token
        token = auth_header.replace("Bearer ", "")
        user_claims = self.token_verifier.verify_token(token)
        
        # Store user context
        context.set_user_context(user_claims)
        
        return await call_next(context)
```

### Tool Integration Pattern
```python
# mcp_server/tools/ticket_tools.py
@mcp.tool()
async def list_tickets(
    status: str = "",
    page: int = 1,
    page_size: int = 10,
    context: ToolContext = None
) -> str:
    """List tickets with user authentication"""
    
    # Get user from context
    user_context = context.get_user_context()
    if not user_context:
        raise ToolError("Authentication required")
    
    # Make authenticated API request
    headers = {"Authorization": f"Bearer {context.get_original_token()}"}
    
    # Rest of implementation...
```

## Migration Strategy

### Development Environment
1. Implement token verification in development branch
2. Test with existing user JWT tokens from core app
3. Validate all MCP tool functionality
4. Ensure Docker compose still works

### Testing Strategy
1. Create unit tests for new components
2. Update integration tests for authentication
3. Test authentication error scenarios
4. Validate token expiration handling
5. Ensure all tests pass with no failures

### Rollback Plan
- Keep current implementation in separate branch
- Test new implementation thoroughly
- Have ability to revert if issues arise
- Document any configuration changes needed

## Success Criteria

1. **Functional Authentication**: MCP tools work with JWT tokens
2. **No 401 Errors**: All authenticated requests succeed
3. **Clean Docker Logs**: No authentication errors in logs
4. **Complete Test Suite**: All tests pass with no failures
5. **User Context**: Tools have access to user information
6. **Organization Isolation**: Users only see their organization's data
7. **Error Handling**: Proper error responses for auth failures

## Risk Assessment

### Low Risk
- JWT token verification is well-established pattern
- Core app authentication remains unchanged
- Isolated changes to MCP server only

### Medium Risk
- Tool implementations need updates
- Test suite requires updates
- Docker configuration might need adjustments

### Mitigation
- Implement in feature branch
- Comprehensive testing before merge
- Keep current implementation as backup
- Document all changes for rollback

## Dependencies

### Internal
- Core app JWT implementation (`app/middleware/auth_middleware.py`)
- User model and authentication flow
- MCP tool implementations

### External
- PyJWT library (already installed)
- FastMCP middleware system
- Docker container networking

## Timeline Estimate

- **Phase 1**: 1-2 hours (cleanup)
- **Phase 2**: 3-4 hours (token verification)
- **Phase 3**: 4-6 hours (tool integration)  
- **Phase 4**: 6-8 hours (testing)
- **Total**: 14-20 hours over 2-3 days

## Next Steps

1. Create feature branch: `mcp-token-verification`
2. Start with Phase 1: Remove OAuth complexity
3. Implement Phase 2: Token verification
4. Update Phase 3: Tool integration
5. Complete Phase 4: Testing and validation

This refactor will provide a simpler, more reliable authentication mechanism for the MCP server while maintaining security and proper user authorization.