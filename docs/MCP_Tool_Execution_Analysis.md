# MCP Tool Execution Analysis: Why Agents Search All Tools Instead of Assigned Ones

## Problem Statement

Your agent `5c690a6f-4751-419f-bcb5-168b2ac76f7f` (API Support Specialist) is configured with only one tool `["get_system_health"]`, but it's searching through **all available tools** instead of limiting itself to just the assigned ones.

## Architecture Overview

```mermaid
graph TD
    A[Agent with tools: ['get_system_health']] --> B[Dynamic Agent Factory]
    B --> C[MCP Client]
    C --> D[MCP Server on Port 8001]
    D --> E[All Available Tools Registry]
    E --> F[ticket_tools.py - 9+ tools]
    E --> G[integration_tools.py - 2+ tools] 
    E --> H[system_tools.py - 1+ tools]
```

## Root Cause Analysis

### 1. **Tool Registration vs Tool Filtering Issue**

**Location**: `/mcp_server/start_mcp_server.py:67-70`
```python
# Register all MCP tools
register_all_ticket_tools(mcp)      # Registers 9+ ticket tools
register_all_integration_tools(mcp) # Registers 2+ integration tools  
register_all_system_tools(mcp)      # Registers 1+ system tools
```

**The Problem**: The MCP server registers **ALL** available tools globally, not per-agent.

### 2. **Agent-Specific Tool Filtering Not Implemented**

**Location**: `/mcp_client/client.py:525-576`
```python
def create_agent_client(self, agent_id: str, tools_enabled: list, organization_id: str = None, auth_token: Optional[str] = None):
    # tools_enabled parameter is passed but NOT used for filtering
    # Agent gets access to ALL tools registered on MCP server
```

**The Issue**: The `tools_enabled` list is logged but never used to restrict tool access.

### 3. **Missing Tool Filtering Mechanism**

The current flow:
1. Agent is created with `tools: ["get_system_health"]`
2. MCP client connects to MCP server
3. MCP server exposes **all 11+ registered tools** 
4. Agent can access any tool, not just `get_system_health`

## Current Architecture Problems

### 1. **Global Tool Registry**
- **File**: `mcp_server/start_mcp_server.py`
- **Issue**: All tools are registered globally on the MCP server
- **Effect**: Every agent sees all tools regardless of configuration

### 2. **No Agent-Specific Tool Filtering**
- **File**: `mcp_client/client.py`
- **Issue**: `tools_enabled` parameter exists but is unused
- **Effect**: Agent tool restrictions are not enforced

### 3. **Tool Discovery vs Tool Access**
- **Current Behavior**: Agent can discover and use all tools
- **Expected Behavior**: Agent should only access assigned tools

## Technical Analysis

### Agent Configuration (Working)
```json
{
  "id": "5c690a6f-4751-419f-bcb5-168b2ac76f7f",
  "tools": ["get_system_health"],
  "mcp_enabled": true,
  "tools_count": 1
}
```

### MCP Server Tool Registration (Problem Area)
```python
# mcp_server/start_mcp_server.py
register_all_ticket_tools(mcp)      # Creates ~9 tools
register_all_integration_tools(mcp) # Creates ~2 tools  
register_all_system_tools(mcp)      # Creates ~1 tools

# Total: ~12 tools available to ANY agent
```

### Agent Client Creation (Missing Filtering)
```python
# mcp_client/client.py:557
agent_client = create_authenticated_mcp_client(mcp_url, auth_token=auth_token)
# tools_enabled list is NOT passed to restrict available tools
```

## Solutions

### Option 1: Agent-Specific MCP Tool Filtering (Recommended)

Modify the MCP client to filter tools based on agent configuration:

```python
# In mcp_client/client.py
def create_agent_client(self, agent_id: str, tools_enabled: list, ...):
    # Create agent-specific tool filter
    agent_client = create_authenticated_mcp_client(mcp_url, auth_token=auth_token)
    
    # Apply tool filtering wrapper
    agent_client = self._apply_tool_filter(agent_client, tools_enabled)
    return agent_client

def _apply_tool_filter(self, client, allowed_tools):
    # Wrap client to only expose allowed tools
    # Implementation needed
```

### Option 2: Dynamic MCP Server Per Agent

Create isolated MCP server instances with only specific tools:

```python
# Create agent-specific MCP server with only required tools
mcp_agent = FastMCP(f"Agent-{agent_id}")
if "get_system_health" in tools_enabled:
    register_system_health_tool(mcp_agent)
# Only register tools that agent needs
```

### Option 3: MCP Server Tool Access Control

Add tool access control at the MCP server level:

```python
# In mcp_server/start_mcp_server.py
@mcp.tool()
async def get_system_health(context=None):
    # Check if requesting agent has permission
    agent_id = extract_agent_id(context)
    if not has_tool_permission(agent_id, "get_system_health"):
        return "Access denied: Tool not available for this agent"
```

## Implementation Priority

1. **High Priority**: Option 1 - Client-side filtering (least disruptive)
2. **Medium Priority**: Option 3 - Server-side access control (more secure)
3. **Low Priority**: Option 2 - Per-agent servers (resource intensive)

## Verification Steps

1. **Before Fix**: Agent can list and use all ~12 tools
2. **After Fix**: Agent can only see/use `get_system_health` tool
3. **Test**: Verify other tools return "not available" or are filtered out

## Impact Analysis

- **Security**: Prevents agents from using unintended tools
- **Performance**: Reduces tool discovery overhead  
- **Compliance**: Ensures agents operate within defined boundaries
- **User Experience**: Clear tool limitations per agent

## Files That Need Changes

1. `mcp_client/client.py` - Add tool filtering logic
2. `app/services/dynamic_agent_factory.py` - Pass tool restrictions
3. Optional: `mcp_server/start_mcp_server.py` - Add access control
4. Tests: Verify tool filtering works correctly

---

**Summary**: Your agent is searching all tools because the MCP server exposes all tools globally, and the client doesn't filter based on the agent's `tools` configuration. The solution requires implementing tool filtering in the MCP client or access control in the MCP server.