# MCP Client Header Authentication Refactor

## Project Requirements and Planning (PRP)

### Executive Summary

This PRP outlines the comprehensive refactoring of the MCP client authentication system to properly implement authentication headers across all MCP tools and dynamic agents. The current system has inconsistent header implementation that needs standardization with proper token refresh mechanisms and validation.

### Current State Analysis

#### Authentication Implementation Status

1. **MCP Client (`mcp_client/client.py`)**:
   - ✅ Has basic JWT header implementation in `create_mcp_client()`
   - ✅ Uses `Authorization: Bearer {token}` format
   - ✅ Supports both authenticated and unauthenticated clients
   - ❌ Headers not consistently passed through all agent client creation paths
   - ❌ No token refresh mechanism when authentication fails

2. **Dynamic Agent Factory (`app/services/dynamic_agent_factory.py`)**:
   - ❌ Creates MCP toolsets WITHOUT authentication headers (line 83-84)
   - ❌ Hard-coded `mcp_server_url = "http://mcp-server:8001/mcp"`
   - ❌ No integration with Principal-based authentication
   - ❌ No token validation or refresh handling

3. **Test Implementation (`test_mcp_client.py`)**:
   - ✅ Shows correct header format: `Authorization: Bearer {token}` + `X-API-KEY: {token}`
   - ✅ Demonstrates proper MCPServerStreamableHTTP initialization with headers
   - ❌ Hard-coded test tokens instead of dynamic token generation

#### Token Management Status

1. **Principal Schema (`app/schemas/principal.py`)**:
   - ✅ Has `get_auth_token()` method for token extraction
   - ✅ Has `is_token_expired()` and `is_token_valid()` validation
   - ✅ Supports both API tokens and JWT tokens
   - ❌ No automatic refresh mechanism

2. **Auth Middleware (`app/middleware/auth_middleware.py`)**:
   - ✅ Has `validate_token_for_mcp()` method for MCP services
   - ✅ Supports API tokens (ai_dev_xxx format) and JWT tokens
   - ✅ Has `create_access_token()` and `create_refresh_token()` methods
   - ❌ No automatic token refresh on 401 responses

### Required Changes

#### Phase 1: Core MCP Client Refactoring

1. **Update `mcp_client/client.py`**:
   - Modify `create_agent_client()` to always use authenticated headers from Principal
   - Add token validation and refresh logic
   - Implement retry mechanism for 401 responses
   - Add header validation and sanitization
   - Update caching logic to include authentication context

2. **Update Dynamic Agent Factory**:
   - Remove hard-coded MCP server URL
   - Integrate Principal authentication in `create_agent()`
   - Pass authentication headers to all MCP toolsets
   - Add token expiry validation before tool execution
   - Implement fallback to unauthenticated mode if Principal missing

#### Phase 2: Token Refresh Implementation

1. **Add Refresh Mechanism**:
   - Create `TokenRefreshHandler` class
   - Implement automatic refresh on 401/403 responses
   - Add retry logic with exponential backoff
   - Cache refreshed tokens in Principal context

2. **Update Principal Schema**:
   - Add `refresh_token` field
   - Add `refresh_if_needed()` method
   - Add `get_headers_for_mcp()` method
   - Add token refresh callback support

#### Phase 3: Test Infrastructure Updates

1. **Refactor Existing Tests**:
   - Update 12 test files that use MCP client functionality
   - Replace hard-coded tokens with dynamic generation
   - Add authentication failure test scenarios
   - Add token refresh test cases
   - Add header validation tests

2. **Add New Test Suites**:
   - `test_mcp_authentication_flow.py`
   - `test_token_refresh_mechanism.py`
   - `test_dynamic_agent_auth_integration.py`
   - `test_mcp_header_validation.py`

### Implementation Steps

#### Step 1: MCP Client Authentication Headers

**Files to modify:**
- `mcp_client/client.py`

**Changes:**
1. Update `create_agent_client()` method:
   ```python
   def create_agent_client(self, agent_id: str, tools: list, principal: Optional[Principal] = None) -> Optional[MCPServerStreamableHTTP]:
       if not principal or not principal.is_token_valid():
           logger.error(f"[MCP_CLIENT] ❌ No valid principal for agent {agent_id}")
           return None
           
       # Get authentication headers from principal
       headers = self._get_auth_headers_from_principal(principal)
       if not headers:
           logger.error(f"[MCP_CLIENT] ❌ Could not extract auth headers from principal")
           return None
           
       # Create authenticated MCP client with proper headers
       base_client = self._create_authenticated_client(principal, headers)
   ```

2. Add helper methods:
   ```python
   def _get_auth_headers_from_principal(self, principal: Principal) -> Optional[Dict[str, str]]:
       """Extract authentication headers from Principal"""
       
   def _create_authenticated_client(self, principal: Principal, headers: Dict[str, str]) -> Optional[MCPServerStreamableHTTP]:
       """Create MCP client with authentication headers"""
       
   def _handle_auth_failure(self, principal: Principal, response_code: int) -> Optional[Principal]:
       """Handle authentication failures and attempt token refresh"""
   ```

#### Step 2: Dynamic Agent Factory Integration

**Files to modify:**
- `app/services/dynamic_agent_factory.py`

**Changes:**
1. Update `create_agent()` method to use authenticated MCP toolsets:
   ```python
   # Replace hard-coded MCP server creation (lines 83-84)
   if tools and principal:
       try:
           # Get agent-specific authenticated MCP client
           agent_mcp_client = mcp_client.create_agent_client(
               agent_id=str(agent_model.id),
               tools=tools,
               principal=principal
           )
           if agent_mcp_client:
               toolsets = [agent_mcp_client]
               logger.info(f"✅ Created authenticated MCP toolset for {agent_model.id}")
           else:
               logger.error(f"❌ Failed to create authenticated MCP toolset for {agent_model.id}")
               toolsets = []
   ```

#### Step 3: Token Refresh Mechanism

**Files to create:**
- `app/services/token_refresh_service.py`

**Implementation:**
```python
class TokenRefreshService:
    async def refresh_principal_token(self, principal: Principal) -> Optional[Principal]:
        """Refresh token for principal if expired or expiring soon"""
        
    async def handle_mcp_auth_failure(self, principal: Principal, error_code: int) -> Optional[Principal]:
        """Handle MCP authentication failures and attempt recovery"""
        
    def should_refresh_token(self, principal: Principal) -> bool:
        """Check if token should be refreshed proactively"""
```

#### Step 4: Test Updates

**Files requiring updates:**

1. **Unit Tests:**
   - `tests/unit/test_authenticated_mcp_client.py` - Update authentication header tests
   - `tests/unit/test_fastmcp_client.py` - Add Principal integration tests  
   - `tests/unit/services/test_dynamic_agent_factory_fastmcp.py` - Add auth integration tests

2. **Integration Tests:**
   - `tests/integration/test_fastmcp_integration.py` - Add end-to-end auth flow
   - `tests/integration/mcp/test_mcp_token_verification.py` - Add token refresh tests

3. **E2E Tests:**
   - `tests/e2e/test_complete_fastmcp_flow.py` - Add auth failure scenarios

**New test scenarios to add:**
- Token expiry during tool execution
- 401 response handling and retry
- Token refresh success/failure paths
- Header validation and sanitization
- Multiple agent authentication isolation
- API token vs JWT token behavior differences

#### Step 5: Validation and Error Handling

**Requirements:**
1. All MCP tool calls must include proper authentication headers
2. 401 responses trigger automatic token refresh (max 2 retries)
3. Token refresh failures fall back to unauthenticated mode where allowed
4. All authentication errors are properly logged with context
5. No hard-coded tokens in production code
6. Docker logs show no authentication errors during normal operation

### Validation Criteria

#### Functional Requirements
- [ ] All MCP toolsets created with authentication headers from Principal
- [ ] Token refresh works for both API tokens and JWT tokens
- [ ] 401 responses trigger automatic retry with refreshed token
- [ ] Agent-specific tool filtering works with authenticated clients
- [ ] Unauthenticated fallback works when Principal unavailable

#### Testing Requirements
- [ ] All existing MCP tests pass with new authentication
- [ ] New authentication test suites achieve >95% coverage
- [ ] Token refresh scenarios tested in isolation and integration
- [ ] Error scenarios (expired tokens, network failures) handled gracefully
- [ ] Performance impact of authentication <10% overhead

#### Deployment Requirements  
- [ ] Docker compose up shows no authentication errors in logs
- [ ] All health checks pass with authentication enabled
- [ ] MCP server receives properly authenticated requests
- [ ] Token refresh doesn't cause service disruption
- [ ] Backward compatibility with existing API consumers

### Risk Analysis

#### High Risk
- **Breaking changes to MCP client interface**: Mitigation - Maintain backward compatibility
- **Token refresh failures causing service outages**: Mitigation - Fallback mechanisms
- **Performance degradation from additional auth overhead**: Mitigation - Caching and optimization

#### Medium Risk  
- **Test coverage gaps for edge cases**: Mitigation - Comprehensive test matrix
- **Docker log noise from auth failures**: Mitigation - Proper log levels and filtering

#### Low Risk
- **Configuration complexity**: Mitigation - Clear documentation and validation

### Success Metrics

1. **Code Quality**: All MCP authentication flows use standardized headers
2. **Reliability**: <1% authentication failure rate in production
3. **Performance**: Authentication adds <100ms latency to tool calls
4. **Maintainability**: Authentication logic centralized in reusable components
5. **Security**: No plaintext tokens in logs or error messages

### Dependencies

- No external dependencies required
- Uses existing FastMCP, Pydantic AI, and authentication infrastructure
- Relies on current Principal/JWT/API token system

### Timeline Estimate

- **Phase 1**: 2-3 days (Core MCP client refactoring)
- **Phase 2**: 1-2 days (Token refresh implementation)  
- **Phase 3**: 2-3 days (Test updates and new test suites)
- **Total**: 5-8 days for complete implementation and validation

This PRP provides a comprehensive roadmap for standardizing MCP client authentication with proper token management and validation across the entire system.