# PRP: MCP Authorization Header Missing - JWT Token Not Passed to MCP Server

## Problem Statement

The MCP server is not receiving the Authorization header with JWT tokens when tools are called from chat messages, causing all MCP tool calls to fail with authentication errors.

### Reproduction
1. Login with valid credentials (`admin@company.com`)
2. Get an agent from the List Agents endpoint
3. Create a new thread
4. Send a message asking about available tools ("What are all the tools you can call?")
5. The MCP server logs show: `WARNING:auth.middleware:MCP tool call missing Authorization header`

### Root Cause Analysis

After tracing the authorization flow from the chat API through to the MCP server, I identified the following issue:

1. **JWT Token Extraction (✅ Working)**: In `/app/api/v1/chat.py:178-189`, the JWT token is correctly extracted from the `Authorization: Bearer <token>` header and passed to `ai_chat_service.send_message_to_thread()`.

2. **Token Storage (✅ Working)**: In `/app/services/ai_chat_service.py:253-259`, the token is verified and stored in the `ThreadContext._original_token` field.

3. **Agent Processing (❌ Issue)**: In `/app/services/dynamic_agent_factory.py:167-170`, the Pydantic AI agent is called with `pydantic_agent.run(message, usage_limits=usage_limits)`, but the authentication context is not passed to the MCP client.

4. **MCP Client Creation (❌ Issue)**: In `/mcp_client/client.py:567-586`, the `get_agent_client()` method creates `MCPServerStreamableHTTP` clients without any authentication headers or token context.

5. **MCP Server Authentication (✅ Working)**: In `/mcp_server/auth/middleware.py:84-89`, the middleware correctly expects an `Authorization: Bearer <token>` header but never receives it.

### Technical Gap

The **critical missing link** is that PydanticAI's `MCPServerStreamableHTTP` client doesn't support passing authentication headers. The current architecture assumes:

1. JWT tokens are extracted and validated in the main app
2. These tokens are passed through the processing chain
3. MCP clients can make authenticated calls to the MCP server

However, **PydanticAI's MCP client implementation doesn't provide a mechanism to inject authentication headers into HTTP requests** sent to the MCP server.

## Solution: Extend MCP Client with Authentication Support

This solution maintains security by ensuring all MCP calls are authenticated, follows the principle of least privilege, and preserves audit trails for all tool usage.

### Technical Architecture

The solution involves creating an authenticated wrapper around PydanticAI's `MCPServerStreamableHTTP` client that injects JWT tokens into HTTP requests sent to the MCP server.

**Core Components:**

1. **AuthenticatedMCPClient**: Custom wrapper that extends or decorates the existing MCP client
2. **Token Propagation**: Updates to pass JWT tokens through the processing chain
3. **Client Factory Updates**: Modifications to create authenticated clients when tokens are available

### Implementation Plan

#### Phase 1: Research and Design (Days 1-2)

1. **Analyze PydanticAI MCP Client Internals**:
   - Study `MCPServerStreamableHTTP` implementation in PydanticAI source
   - Identify HTTP client used internally (likely httpx)
   - Map out extension points for header injection
   - Document current authentication flow gaps

2. **Design Authentication Architecture**:
   - Define `AuthenticatedMCPClient` interface and implementation approach
   - Plan token propagation through processing chain
   - Design error handling for authentication failures
   - Create fallback strategy for non-authenticated scenarios

#### Phase 2: Core Implementation (Days 3-7)

1. **Implement AuthenticatedMCPClient**:
   ```python
   # mcp_client/authenticated_client.py
   from typing import Optional, Dict, Any
   from pydantic_ai.mcp import MCPServerStreamableHTTP
   import httpx
   
   class AuthenticatedMCPClient(MCPServerStreamableHTTP):
       """MCP client with JWT authentication support"""
       
       def __init__(self, url: str, auth_token: Optional[str] = None):
           self.auth_token = auth_token
           super().__init__(url)
           
       def _get_auth_headers(self) -> Dict[str, str]:
           """Get authentication headers for MCP requests"""
           if self.auth_token:
               return {"Authorization": f"Bearer {self.auth_token}"}
           return {}
           
       async def _make_request(self, method: str, url: str, **kwargs):
           """Override request method to inject auth headers"""
           headers = kwargs.get('headers', {})
           headers.update(self._get_auth_headers())
           kwargs['headers'] = headers
           return await super()._make_request(method, url, **kwargs)
   ```

2. **Update Dynamic Agent Factory**:
   ```python
   # app/services/dynamic_agent_factory.py
   async def create_agent_from_model(self, agent_model: AgentModel, auth_token: Optional[str] = None):
       """Create Pydantic AI agent with optional authentication"""
       
       # Create authenticated MCP client if token provided
       toolsets = []
       if agent_model.mcp_enabled and tools_enabled:
           if auth_token:
               agent_client = AuthenticatedMCPClient(
                   url="http://mcp-server:8001/mcp/",
                   auth_token=auth_token
               )
               logger.info(f"Created authenticated MCP client for agent {agent_model.id}")
           else:
               # Fallback to non-authenticated client
               agent_client = mcp_client.get_agent_client(
                   agent_id=str(agent_model.id),
                   tools_enabled=tools_enabled
               )
               logger.warning(f"Created non-authenticated MCP client for agent {agent_model.id}")
   ```

3. **Update Processing Chain**:
   ```python
   # app/services/ai_chat_service.py
   async def _send_message_with_auth(self, context: ThreadContext, message: str, attachments: List[dict] = None):
       """Send message with authentication context"""
       
       # Pass auth token to dynamic agent factory
       response = await dynamic_agent_factory.process_message_with_agent(
           agent_model, message, agent_context, auth_token=context._original_token
       )
   ```

#### Phase 3: Integration and Testing (Days 8-10)

1. **Integration Testing**:
   - Test authenticated MCP client with existing MCP server
   - Verify JWT tokens reach MCP server auth middleware
   - Test all 13 MCP tools with authentication
   - Validate error handling for expired/invalid tokens

2. **Update Existing Test Suite**:
   - Extend `test_auth_flow.py` to verify MCP authentication
   - Add unit tests for `AuthenticatedMCPClient`
   - Test token propagation through processing chain
   - Verify fallback behavior when tokens are missing

3. **Performance Testing**:
   - Measure latency impact of authentication
   - Test concurrent authenticated sessions
   - Monitor memory usage with authenticated clients

### Code Changes Required

**New Files:**
- `/mcp_client/authenticated_client.py` - AuthenticatedMCPClient implementation

**Modified Files:**
- `/app/services/dynamic_agent_factory.py` - Add auth_token parameter to methods
- `/app/services/ai_chat_service.py` - Pass tokens to agent factory
- `/mcp_client/client.py` - Update client factory methods
- `/test_auth_flow.py` - Extend to test MCP authentication

### Risk Assessment and Mitigation

**High Risk: PydanticAI Client Extension**
- **Risk**: PydanticAI's `MCPServerStreamableHTTP` may not support header customization
- **Mitigation**: Research alternative approaches (monkey patching, client wrapping, httpx middleware)
- **Fallback**: Implement custom MCP client using httpx directly if needed

**Medium Risk: Performance Impact**
- **Risk**: Authentication adds overhead to every MCP tool call
- **Mitigation**: Implement connection pooling and header caching
- **Monitoring**: Add performance metrics for authenticated vs non-authenticated calls

**Medium Risk: Token Lifecycle Management**
- **Risk**: Tokens may expire during long-running agent conversations
- **Mitigation**: Implement token refresh logic in authenticated client
- **Fallback**: Graceful degradation to error state with clear user messaging

### Testing Strategy

#### 1. Automated End-to-End Testing

**Primary Test Script**: `test_auth_flow.py` (already created)
```python
#!/usr/bin/env python3
"""
Test script to reproduce and validate the authorization flow with MCP server.
This script will:
1. Login with admin@company.com
2. Get an agent from List Agents endpoint
3. Create a new thread
4. Send a message asking about available tools
5. Validate MCP server receives proper authorization headers
"""

class AuthFlowTester:
    def login(self, email: str, password: str) -> bool:
        """Login and get access token - TEST PHASE 1"""
        
    def get_agents(self) -> bool:
        """Get list of agents - TEST PHASE 2"""
        
    def create_thread(self) -> bool:
        """Create a new thread - TEST PHASE 3"""
        
    def send_message(self, message: str) -> bool:
        """Send a message to the thread - TEST PHASE 4"""
        # This will trigger MCP tool calls and validate authentication
        
    def validate_mcp_authentication(self) -> bool:
        """NEW: Validate MCP server received auth headers - TEST PHASE 5"""
        # Check docker logs for successful authentication
        # Verify no "missing Authorization header" warnings
```

**Test Execution**:
```bash
# Run automated test with log monitoring
python test_auth_flow.py

# Verify MCP authentication in logs
docker logs support-extension-mcp-server-1 --since=1m | grep -i auth
```

#### 2. Phase-Specific Testing and Validation

**Phase 1: Research and Design (Days 1-2) - Testing Requirements**

*Day 1 Testing*:
- **PydanticAI Client Analysis Test**:
  ```python
  # tests/test_pydantic_mcp_client.py
  def test_mcp_client_internals():
      """Validate PydanticAI MCP client structure and extension points"""
      client = MCPServerStreamableHTTP("http://test")
      # Test: Identify HTTP client used (httpx, aiohttp, etc.)
      # Test: Check for header injection points
      # Test: Validate request method overrides
  ```

*Day 2 Testing*:
- **Authentication Architecture Design Test**:
  ```python
  # tests/test_auth_design.py
  def test_authenticated_client_interface():
      """Test the designed AuthenticatedMCPClient interface"""
      # Mock implementation to validate design
      # Test token injection mechanism
      # Test error handling design
  ```

**Phase 2: Core Implementation (Days 3-7) - Testing Requirements**

*Day 3-4 Testing*:
- **AuthenticatedMCPClient Unit Tests**:
  ```python
  # tests/test_authenticated_mcp_client.py
  
  def test_auth_header_injection():
      """Test that JWT tokens are properly injected into headers"""
      client = AuthenticatedMCPClient("http://test", "test-token")
      headers = client._get_auth_headers()
      assert headers["Authorization"] == "Bearer test-token"
      
  def test_request_override():
      """Test that _make_request properly adds auth headers"""
      # Mock HTTP requests and verify headers are included
      
  def test_fallback_behavior():
      """Test behavior when no auth token provided"""
      client = AuthenticatedMCPClient("http://test")  # No token
      headers = client._get_auth_headers()
      assert "Authorization" not in headers
  ```

*Day 5-6 Testing*:
- **Dynamic Agent Factory Integration Tests**:
  ```python
  # tests/test_dynamic_agent_factory_auth.py
  
  def test_authenticated_agent_creation():
      """Test agent creation with auth token"""
      factory = DynamicAgentFactory()
      agent = await factory.create_agent_from_model(
          agent_model, 
          auth_token="valid-jwt-token"
      )
      # Verify authenticated MCP client is created
      
  def test_non_authenticated_fallback():
      """Test fallback when no auth token provided"""
      agent = await factory.create_agent_from_model(agent_model)
      # Verify standard MCP client is created
  ```

*Day 7 Testing*:
- **Processing Chain Integration Tests**:
  ```python
  # tests/test_ai_chat_service_auth.py
  
  def test_token_propagation():
      """Test JWT token propagation through processing chain"""
      context = ThreadContext(...)
      context._original_token = "test-jwt-token"
      
      response = await ai_chat_service._send_message_with_auth(
          context, "test message"
      )
      # Verify token was passed to agent factory
  ```

**Phase 3: Integration and Testing (Days 8-10) - Testing Requirements**

*Day 8 Testing*:
- **Full Integration Test with Real MCP Server**:
  ```python
  # tests/test_mcp_integration_auth.py
  
  async def test_authenticated_tool_call():
      """Test actual tool call with authentication"""
      # Use test_auth_flow.py as foundation
      tester = AuthFlowTester()
      
      # Execute full flow
      success = tester.run_test()
      assert success
      
      # Validate MCP server logs
      logs = get_mcp_server_logs()
      assert "MCP tool authenticated for user" in logs
      assert "missing Authorization header" not in logs
  
  async def test_all_13_mcp_tools():
      """Test each MCP tool with authentication"""
      tools = [
          "create_ticket", "search_tickets", "get_ticket", "update_ticket",
          "delete_ticket", "update_ticket_status", "assign_ticket",
          "list_tickets", "get_ticket_stats", "create_ticket_with_ai",
          "list_integrations", "get_active_integrations", "get_system_health"
      ]
      
      for tool in tools:
          result = await call_authenticated_mcp_tool(tool, test_params)
          assert result is not None
          assert "Authentication failed" not in str(result)
  ```

*Day 9 Testing*:
- **Error Handling and Edge Cases**:
  ```python
  # tests/test_auth_error_handling.py
  
  def test_expired_token_handling():
      """Test behavior with expired JWT tokens"""
      expired_token = create_expired_jwt_token()
      # Test graceful error handling
      
  def test_invalid_token_format():
      """Test behavior with malformed tokens"""
      invalid_tokens = ["invalid", "Bearer", "Bearer invalid-format"]
      # Test error responses
      
  def test_missing_token_fallback():
      """Test fallback when token is missing"""
      # Verify non-authenticated mode works for development
  ```

*Day 10 Testing*:
- **Performance and Load Testing**:
  ```python
  # tests/test_auth_performance.py
  
  def test_authentication_latency():
      """Measure latency impact of authentication"""
      # Compare authenticated vs non-authenticated call times
      # Verify < 10ms additional latency requirement
      
  def test_concurrent_authenticated_sessions():
      """Test multiple authenticated users simultaneously"""
      # Simulate 10+ concurrent authenticated chat sessions
      # Verify no token mixing or auth failures
  ```

#### 3. Continuous Validation During Development

**Daily Validation Commands**:
```bash
# Automated test execution
python test_auth_flow.py

# MCP server auth validation
docker logs support-extension-mcp-server-1 --since=5m | grep -E "(authenticated|Authorization|missing)"

# Main app auth validation  
docker logs support-extension-app-1 --since=5m | grep -E "(JWT|Bearer|auth)"

# Tool call success validation
docker logs support-extension-mcp-server-1 --since=5m | grep "Processing request of type CallToolRequest"
```

**Log Validation Patterns**:

*Success Indicators*:
```
✅ MCP server: "MCP tool authenticated for user [user-id]"
✅ Main app: "Extracted JWT token for MCP authentication"  
✅ MCP server: "Processing request of type CallToolRequest"
```

*Failure Indicators*:
```
❌ MCP server: "MCP tool call missing Authorization header"
❌ MCP server: "Authentication failed: [error]"
❌ Main app: "Failed to decode JWT token"
```

#### 4. Manual Verification Checklist

**Pre-Implementation Validation**:
- [ ] `test_auth_flow.py` reproduces the authorization issue
- [ ] MCP server logs show "missing Authorization header" warnings
- [ ] All 13 MCP tools are accessible via the current (non-authenticated) flow

**Post-Implementation Validation**:
- [ ] `test_auth_flow.py` runs without authentication errors
- [ ] MCP server logs show "MCP tool authenticated for user" messages
- [ ] All 13 MCP tools work with authenticated requests
- [ ] Performance impact is < 10ms per tool call
- [ ] Non-authenticated fallback works for development scenarios

**Docker Log Monitoring Commands**:
```bash
# Monitor both services during testing
docker logs -f support-extension-app-1 &
docker logs -f support-extension-mcp-server-1 &

# Execute test
python test_auth_flow.py

# Validate authentication flow
docker logs support-extension-mcp-server-1 --since=1m | grep -c "authenticated"  # Should be > 0
docker logs support-extension-mcp-server-1 --since=1m | grep -c "missing Authorization" # Should be 0
```

### Acceptance Criteria

✅ **Authentication Headers**: MCP server logs show `Authorization: Bearer <token>` headers for all tool calls  
✅ **Tool Functionality**: All 13 MCP tools work correctly with authenticated requests  
✅ **Error Handling**: Clear error messages for missing, invalid, or expired tokens  
✅ **Performance**: Less than 10ms additional latency per authenticated tool call  
✅ **Security**: All tool calls include proper user context and maintain audit trails  
✅ **Backward Compatibility**: Non-authenticated flows continue to work for development/testing

### Implementation Notes

This solution addresses a critical security gap where JWT tokens are properly extracted and validated in the main application but never reach the MCP server due to PydanticAI's client limitations. The implementation maintains the existing security model while enabling authenticated tool usage.

The key innovation is creating a transparent authentication layer that wraps PydanticAI's MCP client without requiring changes to the agent processing logic or MCP server authentication middleware.

**Key File Locations:**
- `/app/api/v1/chat.py:178-189` (JWT extraction - working)  
- `/app/services/ai_chat_service.py:253-259` (Token storage - working)
- `/app/services/dynamic_agent_factory.py:167-170` (Agent processing - needs auth token)
- `/mcp_client/client.py:567-586` (Client creation - needs authenticated wrapper)
- `/mcp_server/auth/middleware.py:84-89` (Server authentication - working)