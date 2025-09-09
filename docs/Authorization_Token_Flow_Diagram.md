# Authorization Token Flow: Chat Endpoint → MCP Server → Response

## System Architecture Diagram

```mermaid
sequenceDiagram
    participant Client as Client/Browser
    participant ChatAPI as Chat API<br/>/api/v1/chat/{agent_id}/threads/{thread_id}/messages
    participant AuthProvider as Auth Provider<br/>decode_jwt_token()
    participant AIChatService as AI Chat Service<br/>send_message_to_thread()
    participant DynamicAgentFactory as Dynamic Agent Factory<br/>process_message_with_agent()
    participant MCPClient as MCP Client Factory<br/>get_agent_client()
    participant ToolFilter as Tool Filter<br/>create_filtered_mcp_client()
    participant MCPServer as MCP Server<br/>:8001/mcp
    participant MCPAuth as MCP Auth Middleware<br/>TokenAuthMiddleware
    participant BackendAPI as Backend API<br/>:8000/api/v1/*

    Note over Client, BackendAPI: 🔐 JWT Token Authorization Flow

    Client->>+ChatAPI: POST /api/v1/chat/{agent_id}/threads/{thread_id}/messages<br/>Authorization: Bearer {JWT_TOKEN}
    
    Note over ChatAPI: 1. Token Extraction
    ChatAPI->>ChatAPI: Extract JWT from Authorization header<br/>jwt_token = auth_header[7:]
    
    Note over ChatAPI: 2. Token Validation
    ChatAPI->>+AuthProvider: decode_jwt_token(jwt_token)
    AuthProvider-->>-ChatAPI: payload (user_id, email, exp, etc.)
    
    Note over ChatAPI: 3. Chat Service Call
    ChatAPI->>+AIChatService: send_message_to_thread(<br/>  agent_id, thread_id, user_id, message,<br/>  auth_token=jwt_token<br/>)
    
    Note over AIChatService: 4. Context Creation
    AIChatService->>AIChatService: context._original_token = auth_token<br/>Store JWT for MCP tools
    
    Note over AIChatService: 5. Dynamic Agent Processing
    AIChatService->>+DynamicAgentFactory: process_message_with_agent(<br/>  agent_model, message, context,<br/>  auth_token=context._original_token<br/>)
    
    Note over DynamicAgentFactory: 6. MCP Client Creation
    DynamicAgentFactory->>+MCPClient: get_agent_client(<br/>  agent_id=agent_model.id,<br/>  tools_enabled=['get_system_health'],<br/>  auth_token=auth_token<br/>)
    
    Note over MCPClient: 7. Base Client Creation
    MCPClient->>MCPClient: create_authenticated_mcp_client(<br/>  url='http://mcp-server:8001/mcp',<br/>  auth_token=auth_token<br/>)
    
    Note over MCPClient: 8. Tool Filtering Application
    MCPClient->>+ToolFilter: create_filtered_mcp_client(<br/>  base_client, tools=['get_system_health'],<br/>  agent_id<br/>)
    
    Note over ToolFilter: 9. Official PydanticAI Filtering
    ToolFilter->>ToolFilter: filtered_toolset = base_client.filtered(<br/>  filter_func: tool_name in allowed_tools<br/>)
    ToolFilter-->>-MCPClient: filtered_toolset
    
    MCPClient-->>-DynamicAgentFactory: filtered_mcp_client
    
    Note over DynamicAgentFactory: 10. Agent Creation & Execution
    DynamicAgentFactory->>DynamicAgentFactory: PydanticAgent(<br/>  model='openai:gpt-4o-mini',<br/>  toolsets=[filtered_mcp_client]<br/>)
    DynamicAgentFactory->>DynamicAgentFactory: agent.run(message, usage_limits)
    
    Note over DynamicAgentFactory: 11. Tool Discovery & Filtering
    DynamicAgentFactory->>+ToolFilter: Agent requests tool list
    ToolFilter->>ToolFilter: Filter tools: only 'get_system_health' allowed
    ToolFilter-->>-DynamicAgentFactory: Filtered tool list

    Note over DynamicAgentFactory: 12. Tool Call Execution
    DynamicAgentFactory->>+MCPServer: Tool call: get_system_health
    
    Note over MCPServer: 13. MCP Authentication
    MCPServer->>+MCPAuth: TokenAuthMiddleware.process()
    Note over MCPAuth: Currently disabled for debugging
    MCPAuth->>MCPAuth: TODO: Verify JWT token<br/>Extract user context
    MCPAuth-->>-MCPServer: context (user_id, org_id)
    
    Note over MCPServer: 14. Backend API Call
    MCPServer->>+BackendAPI: GET /health<br/>Authorization: Bearer {JWT_TOKEN}
    BackendAPI->>BackendAPI: Validate JWT & check system health
    BackendAPI-->>-MCPServer: {"status": "healthy", "services": {...}}
    
    Note over MCPServer: 15. Response Chain
    MCPServer-->>-DynamicAgentFactory: Tool result: system health data
    DynamicAgentFactory-->>-AIChatService: ChatResponse with tool results
    AIChatService-->>-ChatAPI: Processed response
    ChatAPI-->>-Client: HTTP 200: {"content": "System is healthy...", "tools_used": ["get_system_health"]}

    Note over Client, BackendAPI: 🔄 Token Flow Complete
```

## Detailed Token Flow Components

### 1. **Initial Request** - Client → Chat API
```http
POST /api/v1/chat/5c690a6f-4751-419f-bcb5-168b2ac76f7f/threads/{thread_id}/messages
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "content": "Check system health",
  "role": "user"
}
```

### 2. **Token Extraction** - Chat API
**File**: `app/api/v1/chat.py:178-189`
```python
# Extract JWT token for MCP authentication
auth_header = http_request.headers.get("authorization", "")
jwt_token = None

if auth_header.startswith("Bearer "):
    jwt_token = auth_header[7:]  # Remove "Bearer " prefix
    payload = decode_jwt_token(jwt_token)
```

### 3. **Token Storage** - AI Chat Service  
**File**: `app/services/ai_chat_service.py:258`
```python
# Store JWT token in context for MCP tools
context._original_token = auth_token
```

### 4. **Agent Factory Integration** - Dynamic Agent Factory
**File**: `app/services/dynamic_agent_factory.py:163`
```python
# Pass auth token to agent creation
pydantic_agent = await self.create_agent_from_model(
    agent_model, 
    auth_token=auth_token  # JWT flows to MCP client
)
```

### 5. **MCP Client Creation** - MCP Client Factory
**File**: `mcp_client/client.py:557-565`
```python
# Create authenticated base client
base_client = create_authenticated_mcp_client(mcp_url, auth_token=auth_token)

# Apply tool filtering with official PydanticAI mechanism  
filtered_client = create_filtered_mcp_client(base_client, tools_enabled, agent_id)
```

### 6. **Tool Filtering** - Tool Filter
**File**: `mcp_client/tool_filter.py:10-33`
```python
def create_filtered_mcp_client(base_client, allowed_tools, agent_id):
    def tool_filter_func(ctx, tool_def):
        return tool_def.name in allowed_tools  # Only allow configured tools
    
    # Official PydanticAI filtering
    return base_client.filtered(tool_filter_func)
```

### 7. **MCP Server Authentication** - MCP Auth Middleware
**File**: `mcp_server/auth/middleware.py:16-27`
```python
# Currently disabled for debugging
class TokenAuthMiddleware(Middleware):
    def process(self, context):
        # TODO: Extract JWT from MCP request
        # TODO: Validate token and set user context
        pass
```

### 8. **Tool Execution** - MCP Server Tools
**File**: `mcp_server/tools/system_tools.py:62-67`
```python
# Tool makes authenticated call to backend
headers = {"Authorization": f"Bearer {user_token}"}
response = await http_client.make_request(
    method="GET",
    endpoint="/health",
    auth_headers=headers
)
```

## Key Architecture Points

### **✅ Working Components**
1. **JWT Extraction**: Chat API correctly extracts Bearer tokens
2. **Token Validation**: AuthProvider decodes and validates JWT
3. **Token Flow**: JWT flows through the entire processing chain
4. **Tool Filtering**: Official PydanticAI filtering applied (new implementation)
5. **Tool Execution**: MCP tools can make authenticated backend calls

### **🚨 Current Limitations**
1. **MCP Auth Middleware**: Currently disabled for debugging
   - JWT tokens reach MCP server but aren't validated
   - User context not extracted from tokens
   
2. **Direct Backend Calls**: Some MCP tools bypass MCP auth entirely
   - Make direct HTTP calls to backend with JWT headers
   - Simpler but bypasses MCP security layer

### **🔐 Security Flow**
- **Frontend → Backend**: JWT Bearer token in Authorization header
- **Backend → MCP**: JWT token passed through processing chain  
- **MCP → Backend**: JWT token included in tool API calls
- **Tool Filtering**: Agents restricted to configured tools only

## Token Lifecycle

1. **Issue**: User login → JWT token generated
2. **Storage**: Client stores token for API requests
3. **Transmission**: Token sent in Authorization header
4. **Validation**: Backend validates token signature/expiry
5. **Propagation**: Token flows to MCP client/tools
6. **Authentication**: MCP tools use token for backend API calls
7. **Filtering**: Only allowed tools can execute
8. **Response**: Results flow back through same chain

---

**Implementation Status**: ✅ Token flow working end-to-end with official PydanticAI tool filtering