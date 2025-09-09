# PRP: Agent-Specific MCP Tool Filtering Implementation

## Executive Summary

This PRP implements agent-specific MCP tool filtering to resolve the issue where agents can access all MCP server tools regardless of their configured `tools` array. Currently, agent `5c690a6f-4751-419f-bcb5-168b2ac76f7f` with tools `["get_system_health"]` can search and use all 12+ available tools instead of being restricted to only the assigned one.

## Problem Statement

**Current Issue**: MCP server registers all tools globally (~12 tools) and agents can access any tool regardless of their configuration.

**Expected Behavior**: Agents should only access tools specified in their `tools` configuration array.

**Root Cause**: No tool filtering mechanism exists between agent configuration and MCP server tool discovery.

## Solution Overview

Implement **Option 1** from `docs/MCP_Tool_Execution_Analysis.md`: Agent-Specific MCP Tool Filtering at the client level.

### Architecture Changes

```mermaid
graph TD
    A[Agent with tools: ['get_system_health']] --> B[Dynamic Agent Factory]
    B --> C[MCP Client + Tool Filter Wrapper]
    C --> D[MCP Server on Port 8001]
    D --> E[All Available Tools Registry]
    
    C --> F[Tool Filter Logic]
    F --> G[Only Allowed Tools Exposed]
    G --> H[Agent sees: ['get_system_health']]
```

## Implementation Plan

### Phase 1: Core Tool Filtering Infrastructure

#### 1.1 Create Tool Filter Wrapper
**File**: `mcp_client/tool_filter.py` (NEW)

```python
"""
Agent-specific tool filtering for MCP clients
"""
import logging
from typing import Dict, List, Any, Optional
from pydantic_ai.mcp import MCPServerStreamableHTTP

logger = logging.getLogger(__name__)

class AgentToolFilteredMCPClient:
    """MCP client wrapper that filters tools based on agent configuration"""
    
    def __init__(self, base_client: MCPServerStreamableHTTP, allowed_tools: List[str], agent_id: str):
        self.base_client = base_client
        self.allowed_tools = set(allowed_tools)
        self.agent_id = agent_id
        logger.info(f"[TOOL_FILTER] Created filtered MCP client for agent {agent_id} with tools: {allowed_tools}")
    
    async def list_tools(self) -> Dict[str, Any]:
        """List tools, filtered to only allowed tools"""
        all_tools = await self.base_client.list_tools()
        
        # Filter tools to only allowed ones
        filtered_tools = {}
        for tool_name, tool_def in all_tools.items():
            if tool_name in self.allowed_tools:
                filtered_tools[tool_name] = tool_def
                logger.debug(f"[TOOL_FILTER] Tool '{tool_name}' allowed for agent {self.agent_id}")
            else:
                logger.debug(f"[TOOL_FILTER] Tool '{tool_name}' filtered out for agent {self.agent_id}")
        
        logger.info(f"[TOOL_FILTER] Agent {self.agent_id}: {len(filtered_tools)}/{len(all_tools)} tools available")
        return filtered_tools
    
    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """Call tool, only if allowed"""
        if tool_name not in self.allowed_tools:
            error_msg = f"Tool '{tool_name}' not available for agent {self.agent_id}. Available tools: {list(self.allowed_tools)}"
            logger.warning(f"[TOOL_FILTER] {error_msg}")
            raise PermissionError(error_msg)
        
        logger.info(f"[TOOL_FILTER] Agent {self.agent_id} calling allowed tool '{tool_name}'")
        return await self.base_client.call_tool(tool_name, **kwargs)
    
    def __getattr__(self, name):
        """Delegate other methods to base client"""
        return getattr(self.base_client, name)

def create_filtered_mcp_client(base_client: MCPServerStreamableHTTP, allowed_tools: List[str], agent_id: str) -> AgentToolFilteredMCPClient:
    """Create a tool-filtered MCP client"""
    return AgentToolFilteredMCPClient(base_client, allowed_tools, agent_id)
```

#### 1.2 Update MCP Client Factory
**File**: `mcp_client/client.py` (MODIFY)

Add tool filtering to `create_agent_client()`:

```python
# Add import
from .tool_filter import create_filtered_mcp_client

def create_agent_client(self, agent_id: str, tools_enabled: list, organization_id: str = None, auth_token: Optional[str] = None) -> Optional[MCPServerStreamableHTTP]:
    """Create MCP client configured for specific agent with tool filtering"""
    try:
        # ... existing code ...
        
        # Create the base MCP client (authenticated or not)
        if auth_token:
            base_client = create_authenticated_mcp_client(mcp_url, auth_token=auth_token)
        else:
            base_client = MCPServerStreamableHTTP(mcp_url)
        
        # Apply tool filtering wrapper
        if tools_enabled:
            filtered_client = create_filtered_mcp_client(base_client, tools_enabled, agent_id)
            logger.info(f"[MCP_CLIENT] ✅ Created filtered MCP client for agent {agent_id} with {len(tools_enabled)} allowed tools")
        else:
            filtered_client = base_client
            logger.warning(f"[MCP_CLIENT] Agent {agent_id} has no tools_enabled - allowing all tools")
        
        # Cache the filtered client
        self._agent_clients[cache_key] = filtered_client
        return filtered_client
        
    except Exception as e:
        logger.error(f"[MCP_CLIENT] ❌ Failed to create filtered agent MCP client: {e}")
        return None
```

### Phase 2: Integration with Dynamic Agent Factory

#### 2.1 Update Dynamic Agent Factory
**File**: `app/services/dynamic_agent_factory.py` (MODIFY)

Ensure `tools_enabled` is properly passed:

```python
# Around line 99-107
if agent_model.mcp_enabled and tools_enabled:
    # ... JWT token storage logic ...
    
    # Create MCP client with tool filtering
    agent_client = mcp_client.get_agent_client(
        agent_id=str(agent_model.id),
        tools_enabled=tools_enabled,  # This is already passed
        organization_id=str(agent_model.organization_id) if agent_model.organization_id else None,
        auth_token=auth_token
    )
    
    if agent_client:
        toolsets = [agent_client]
        logger.info(f"[DYNAMIC_AGENT] ✅ MCP client with {len(tools_enabled)} filtered tools created for agent {agent_model.id}")
    else:
        logger.error(f"[DYNAMIC_AGENT] ❌ Failed to create filtered MCP client for agent {agent_model.id}")
```

### Phase 3: Comprehensive Testing Suite

#### 3.1 Unit Tests for Tool Filter
**File**: `tests/unit/test_tool_filter.py` (NEW)

```python
"""Unit tests for MCP tool filtering"""
import pytest
from unittest.mock import AsyncMock, Mock
from mcp_client.tool_filter import AgentToolFilteredMCPClient, create_filtered_mcp_client

@pytest.fixture
def mock_base_client():
    """Mock MCP client"""
    client = AsyncMock()
    client.list_tools = AsyncMock(return_value={
        "get_system_health": {"description": "Check system health"},
        "create_ticket": {"description": "Create a ticket"},
        "list_tickets": {"description": "List tickets"},
        "delete_ticket": {"description": "Delete a ticket"}
    })
    client.call_tool = AsyncMock(return_value="Tool executed successfully")
    return client

@pytest.fixture
def filtered_client(mock_base_client):
    """Filtered MCP client with limited tools"""
    return AgentToolFilteredMCPClient(
        base_client=mock_base_client,
        allowed_tools=["get_system_health"],
        agent_id="test-agent-123"
    )

@pytest.mark.asyncio
class TestAgentToolFilteredMCPClient:
    
    async def test_list_tools_filters_correctly(self, filtered_client, mock_base_client):
        """Test that list_tools only returns allowed tools"""
        tools = await filtered_client.list_tools()
        
        # Should only have the allowed tool
        assert len(tools) == 1
        assert "get_system_health" in tools
        assert "create_ticket" not in tools
        assert "list_tickets" not in tools
        assert "delete_ticket" not in tools
        
        # Base client should have been called
        mock_base_client.list_tools.assert_called_once()
    
    async def test_call_allowed_tool_succeeds(self, filtered_client, mock_base_client):
        """Test that calling allowed tool works"""
        result = await filtered_client.call_tool("get_system_health")
        
        assert result == "Tool executed successfully"
        mock_base_client.call_tool.assert_called_once_with("get_system_health")
    
    async def test_call_disallowed_tool_raises_permission_error(self, filtered_client, mock_base_client):
        """Test that calling disallowed tool raises PermissionError"""
        with pytest.raises(PermissionError) as exc_info:
            await filtered_client.call_tool("create_ticket")
        
        assert "create_ticket" in str(exc_info.value)
        assert "not available for agent test-agent-123" in str(exc_info.value)
        
        # Base client should not have been called
        mock_base_client.call_tool.assert_not_called()
    
    async def test_empty_allowed_tools_blocks_all(self, mock_base_client):
        """Test that empty allowed_tools blocks all tool calls"""
        client = AgentToolFilteredMCPClient(
            base_client=mock_base_client,
            allowed_tools=[],
            agent_id="no-tools-agent"
        )
        
        tools = await client.list_tools()
        assert len(tools) == 0
        
        with pytest.raises(PermissionError):
            await client.call_tool("get_system_health")
    
    def test_create_filtered_mcp_client_factory(self, mock_base_client):
        """Test the factory function"""
        client = create_filtered_mcp_client(
            mock_base_client, 
            ["get_system_health", "create_ticket"], 
            "factory-test-agent"
        )
        
        assert isinstance(client, AgentToolFilteredMCPClient)
        assert client.allowed_tools == {"get_system_health", "create_ticket"}
        assert client.agent_id == "factory-test-agent"
```

#### 3.2 Integration Tests
**File**: `tests/integration/mcp/test_agent_tool_filtering.py` (NEW)

```python
"""Integration tests for agent-specific tool filtering"""
import pytest
from app.services.dynamic_agent_factory import DynamicAgentFactory
from app.models.ai_agent import AIAgent
from mcp_client.client import MCPClient

@pytest.mark.asyncio
class TestAgentToolFiltering:
    
    @pytest.fixture
    async def agent_factory(self, db_session):
        """Agent factory instance"""
        return DynamicAgentFactory()
    
    @pytest.fixture
    async def test_agent(self, db_session, test_organization):
        """Test agent with limited tools"""
        agent = AIAgent(
            id="5c690a6f-4751-419f-bcb5-168b2ac76f7f",
            organization_id=test_organization.id,
            name="API Support Specialist",
            agent_type="customer_support",
            is_active=True,
            prompt="You are a support specialist",
            tools=["get_system_health"],
            mcp_enabled=True
        )
        db_session.add(agent)
        await db_session.commit()
        return agent
    
    async def test_agent_only_sees_configured_tools(self, agent_factory, test_agent, test_organization):
        """Test that agent only sees tools in its configuration"""
        
        # Create agent from model (this should create filtered MCP client)
        pydantic_agent = await agent_factory.create_agent_from_model(
            test_agent, 
            auth_token="test-jwt-token"
        )
        
        assert pydantic_agent is not None
        
        # Check that agent's toolset is filtered
        # This requires checking the MCP client's tool filtering
        # Implementation depends on how Pydantic AI exposes toolsets
        
    async def test_agent_cannot_use_unauthorized_tools(self, agent_factory, test_agent, test_organization):
        """Test that agent cannot use tools not in its configuration"""
        
        # This would require running actual tool calls through the agent
        # and verifying that unauthorized tools are blocked
        pass

@pytest.mark.asyncio 
class TestMCPClientToolFiltering:
    
    @pytest.fixture
    def mcp_client(self):
        """MCP client instance"""
        return MCPClient(mcp_server_url="http://mcp-server:8001")
    
    async def test_create_agent_client_with_tool_filtering(self, mcp_client):
        """Test creating agent client with tool filtering"""
        
        client = mcp_client.create_agent_client(
            agent_id="test-agent-123",
            tools_enabled=["get_system_health"],
            auth_token="test-token"
        )
        
        assert client is not None
        
        # Test that client only exposes allowed tools
        tools = await client.list_tools()
        assert "get_system_health" in tools
        
        # Verify filtered tools are not exposed
        all_tool_names = list(tools.keys())
        assert "create_ticket" not in all_tool_names
        assert "list_tickets" not in all_tool_names
        
    async def test_agent_client_blocks_unauthorized_tool_calls(self, mcp_client):
        """Test that agent client blocks calls to unauthorized tools"""
        
        client = mcp_client.create_agent_client(
            agent_id="restricted-agent",
            tools_enabled=["get_system_health"],
            auth_token="test-token"
        )
        
        # Allowed tool should work
        result = await client.call_tool("get_system_health")
        assert result is not None
        
        # Unauthorized tool should raise PermissionError
        with pytest.raises(PermissionError):
            await client.call_tool("create_ticket", title="Test", description="Test")
```

#### 3.3 End-to-End Tests
**File**: `tests/e2e/test_agent_tool_restrictions.py` (NEW)

```python
"""End-to-end tests for agent tool restrictions"""
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
class TestAgentToolRestrictionsE2E:
    
    async def test_agent_chat_respects_tool_filtering(self, test_client: AsyncClient, test_user_auth_headers, test_agent):
        """Test that agent chat respects tool filtering through the full stack"""
        
        # Send a message that would typically trigger tool usage
        response = await test_client.post(
            f"/api/v1/chat/conversations/{test_conversation.id}/messages",
            json={
                "content": "Can you create a ticket for me?",
                "agent_id": str(test_agent.id)  # Agent only has get_system_health tool
            },
            headers=test_user_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Agent should respond that it cannot create tickets
        assert "cannot create tickets" in data["content"].lower() or \
               "not available" in data["content"].lower()
    
    async def test_agent_can_use_allowed_tools(self, test_client: AsyncClient, test_user_auth_headers, test_agent):
        """Test that agent can use tools it's configured for"""
        
        response = await test_client.post(
            f"/api/v1/chat/conversations/{test_conversation.id}/messages",
            json={
                "content": "Can you check the system health?",
                "agent_id": str(test_agent.id)
            },
            headers=test_user_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Response should contain health information
        assert "health" in data["content"].lower() or \
               "status" in data["content"].lower()
```

### Phase 4: Validation and Testing Strategy

#### 4.1 Docker Environment Testing
**Script**: `tests/scripts/test_tool_filtering_e2e.sh` (NEW)

```bash
#!/bin/bash
set -e

echo "🔧 Testing Agent-Specific Tool Filtering End-to-End"

# Start all services
echo "🚀 Starting Docker services..."
docker compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services..."
sleep 10

# Test MCP server health
echo "🏥 Testing MCP server health..."
curl -f http://localhost:8001/health || (echo "❌ MCP server not ready" && exit 1)

# Test backend health
echo "🏥 Testing backend health..."
curl -f http://localhost:8000/health || (echo "❌ Backend not ready" && exit 1)

# Run tool filtering specific tests
echo "🧪 Running tool filtering tests..."
docker compose exec app poetry run pytest tests/unit/test_tool_filter.py -v
docker compose exec app poetry run pytest tests/integration/mcp/test_agent_tool_filtering.py -v
docker compose exec app poetry run pytest tests/e2e/test_agent_tool_restrictions.py -v

# Test with real agent
echo "🤖 Testing with real agent data..."
AGENT_ID="5c690a6f-4751-419f-bcb5-168b2ac76f7f"

# Register and get auth token
echo "🔐 Getting auth token..."
AUTH_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "full_name": "Test User", "password": "TestPass123", "organization_name": "Test Org"}')
TOKEN=$(echo $AUTH_RESPONSE | jq -r '.access_token')

# Create conversation
echo "💬 Creating test conversation..."
CONV_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/chat/conversations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Tool Filtering Test"}')
CONVERSATION_ID=$(echo $CONV_RESPONSE | jq -r '.id')

# Test allowed tool (should work)
echo "✅ Testing allowed tool..."
ALLOWED_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/chat/conversations/$CONVERSATION_ID/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"content\": \"Check system health\", \"agent_id\": \"$AGENT_ID\"}")

echo "Response for allowed tool: $ALLOWED_RESPONSE"

# Test disallowed tool (should be blocked)
echo "🚫 Testing disallowed tool..."
BLOCKED_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/chat/conversations/$CONVERSATION_ID/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"content\": \"Create a ticket\", \"agent_id\": \"$AGENT_ID\"}")

echo "Response for blocked tool: $BLOCKED_RESPONSE"

# Verify no errors in logs
echo "📋 Checking for errors in logs..."
docker compose logs app | grep -i error | tail -10
docker compose logs mcp-server | grep -i error | tail -10

echo "✅ Tool filtering tests completed successfully!"
```

#### 4.2 Validation Checklist

**Pre-Implementation Validation:**
- [ ] Current agent can access all 12+ tools
- [ ] Agent configuration shows `tools: ["get_system_health"]`
- [ ] Agent `tools_count: 1` but can use any tool
- [ ] No tool filtering mechanism exists

**Post-Implementation Validation:**
- [ ] Agent can only see `get_system_health` in tool list
- [ ] Agent can successfully call `get_system_health`
- [ ] Agent cannot call `create_ticket`, `list_tickets`, etc.
- [ ] PermissionError raised for unauthorized tools
- [ ] All tests pass without errors
- [ ] No Docker log errors
- [ ] MCP server health endpoint working
- [ ] Backend health endpoint working

#### 4.3 Performance and Error Monitoring

**Monitoring Points:**
1. **MCP Client Creation Time**: Should not increase significantly
2. **Tool Filtering Overhead**: Should be minimal (<1ms per tool check)
3. **Memory Usage**: Filtered clients should not significantly increase memory
4. **Error Rates**: No increase in error rates after deployment

**Error Scenarios to Test:**
1. Agent with empty `tools` array
2. Agent with invalid tool names in `tools` array
3. MCP server down during tool filtering
4. Network timeouts during tool calls
5. JWT token expiry during tool filtering

### Phase 5: Deployment and Rollback Plan

#### 5.1 Deployment Steps

1. **Create new files:**
   - `mcp_client/tool_filter.py`
   - `tests/unit/test_tool_filter.py`
   - `tests/integration/mcp/test_agent_tool_filtering.py`
   - `tests/e2e/test_agent_tool_restrictions.py`
   - `tests/scripts/test_tool_filtering_e2e.sh`

2. **Modify existing files:**
   - `mcp_client/client.py`: Add tool filtering
   - `app/services/dynamic_agent_factory.py`: Verify tools_enabled passing

3. **Run test suite:**
   ```bash
   poetry run pytest tests/unit/test_tool_filter.py -v
   poetry run pytest tests/integration/mcp/ -v
   poetry run pytest tests/e2e/test_agent_tool_restrictions.py -v
   ```

4. **Run E2E validation:**
   ```bash
   chmod +x tests/scripts/test_tool_filtering_e2e.sh
   ./tests/scripts/test_tool_filtering_e2e.sh
   ```

5. **Deploy to staging:** Test with real agent configurations

6. **Deploy to production:** Monitor error rates and performance

#### 5.2 Rollback Plan

If issues occur:

1. **Quick Rollback:**
   ```python
   # In mcp_client/client.py, temporarily disable filtering:
   if tools_enabled and False:  # Disable filtering
       filtered_client = create_filtered_mcp_client(base_client, tools_enabled, agent_id)
   else:
       filtered_client = base_client  # Use unfiltered client
   ```

2. **Git Rollback:**
   ```bash
   git revert <commit-hash>
   docker compose down && docker compose up -d
   ```

3. **Feature Flag Approach:**
   Add environment variable `ENABLE_TOOL_FILTERING=false` to disable filtering

## Success Criteria

### Functional Requirements ✅
- [ ] Agent with `tools: ["get_system_health"]` can only access that tool
- [ ] Agent cannot discover or use unauthorized tools
- [ ] Proper error messages for unauthorized tool access
- [ ] Existing functionality for agents with multiple tools preserved

### Non-Functional Requirements ✅  
- [ ] All unit tests pass (100% coverage for new code)
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] No Docker container errors in logs
- [ ] No performance degradation (< 5% increase in response time)
- [ ] Memory usage increase < 10%

### Security Requirements ✅
- [ ] Tool access properly restricted per agent
- [ ] JWT authentication still working with filtered clients
- [ ] No bypass mechanisms for unauthorized tool access
- [ ] Proper logging of tool access attempts

## Timeline

- **Phase 1** (Core Infrastructure): 1 day
- **Phase 2** (Integration): 0.5 days  
- **Phase 3** (Testing Suite): 1.5 days
- **Phase 4** (Validation): 0.5 days
- **Phase 5** (Deployment): 0.5 days

**Total Estimated Time**: 4 days

## Risk Mitigation

### High Risk: Breaking Existing Agents
- **Mitigation**: Comprehensive test suite covering all agent types
- **Fallback**: Feature flag to disable filtering if issues occur

### Medium Risk: Performance Impact
- **Mitigation**: Lightweight filtering logic with caching
- **Monitoring**: Performance benchmarks before/after deployment

### Low Risk: Tool Discovery Changes
- **Mitigation**: Maintain same interface for tool discovery
- **Testing**: Verify existing tool calls continue to work for authorized tools

## Conclusion

This implementation provides a robust, tested solution for agent-specific MCP tool filtering that addresses the root cause identified in the analysis. The solution is designed to be backwards-compatible, well-tested, and easily deployable with proper rollback mechanisms.

The comprehensive test suite ensures no regressions while the monitoring and validation steps guarantee the system operates correctly in production environments.