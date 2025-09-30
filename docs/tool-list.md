# Tool List Integration - PRP Document

## Problem Statement

The frontend needs a way to dynamically list all available MCP (Model Context Protocol) tools when creating or configuring AI agents. Currently, agent configuration requires hardcoded tool names in the `tools` field, making it difficult to:

1. **Discover Available Tools**: Frontend cannot dynamically discover what tools are available in the MCP server
2. **Dynamic UI Generation**: Cannot create a dynamic tool selection interface for agent configuration 
3. **Tool Documentation**: No way to provide tool descriptions and parameters to users during agent setup
4. **Version Management**: Tool availability changes cannot be reflected in the UI without code updates

## Proposed Solution

**Create a REST endpoint that wraps MCP `tools/list` operation**:

1. **Add REST endpoint** `/api/v1/tools/` that internally calls MCP `tools/list` ([MCP Spec](https://modelcontextprotocol.io/specification/2025-06-18/server/tools))
2. **Transform MCP schemas** to REST response format for frontend consumption
3. **Maintain existing architecture** - Frontend continues using REST APIs
4. **Build tool selector component** that calls the REST endpoint

This approach leverages MCP `tools/list` benefits while keeping the existing REST architecture intact.

## Current MCP Tool Inventory

### Main MCP Server (auth_server.py)
**API-based tools with token authentication:**

1. **`list_tickets`** - List and retrieve tickets with advanced filtering and pagination
2. **`create_ticket`** - Create a new support ticket with attachments
3. **`search_tickets`** - Search tickets by text query with filtering
4. **`get_ticket`** - Get specific ticket by ID
5. **`update_ticket`** - Update existing ticket with PATCH/PUT support
6. **`get_available_tools`** - List all available tools (meta tool)
7. **`get_system_health`** - Check system and API health status
8. **`add`** - Demo addition tool (development only)

### Principal-based Tools (ticket_tools.py)
**Direct database access with Principal context:**

1. **`create_ticket`** - Principal-based ticket creation
2. **`list_tickets`** - Principal-based ticket listing
3. **`update_ticket`** - Principal-based ticket updates
4. **`get_ticket`** - Principal-based ticket retrieval

### Integration Tools (integration_tools.py)
**Integration management tools:**

1. **`list_integrations`** - List available integrations
2. **`get_active_integrations`** - Get active integrations with capabilities

### System Tools (system_tools.py)
**System monitoring and health:**

1. **`get_system_health`** - System health checks with Principal context

## Technical Implementation

### 1. REST API Endpoint

```python
# app/api/v1/tools.py
from fastapi import APIRouter, Depends, HTTPException
from app.middleware.auth_middleware import get_current_user
from app.schemas.tools import ToolListResponse, ToolInfo, ToolParameter
from app.services.mcp_tool_service import MCPToolService

router = APIRouter(prefix="/tools", tags=["Tools"])

@router.get("/", response_model=ToolListResponse)
async def get_available_tools(
    category: Optional[str] = Query(None, description="Filter by tool category"),
    current_user: User = Depends(get_current_user)
):
    """Get available MCP tools for agent configuration via tools/list"""
    try:
        mcp_service = MCPToolService()
        tools = await mcp_service.get_available_tools(
            user_token=current_user.get_auth_token(),
            category_filter=category
        )
        
        return ToolListResponse(
            tools=tools,
            categories=list(set(tool.category for tool in tools)),
            total_count=len(tools)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tools: {str(e)}")
```

### 2. MCP Service Layer

```python
# app/services/mcp_tool_service.py
class MCPToolService:
    async def get_available_tools(
        self, 
        user_token: str,
        category_filter: Optional[str] = None
    ) -> List[ToolInfo]:
        """Fetch tools from MCP server using tools/list operation"""
        try:
            # Connect to MCP server using existing client infrastructure
            mcp_client = await self.get_mcp_client(user_token)
            
            # Call standard MCP tools/list operation
            tools_response = await mcp_client.list_tools()
            
            # Transform MCP tool definitions to our format
            tools = []
            for tool in tools_response.tools:
                tool_info = ToolInfo(
                    name=tool.name,
                    description=tool.description or "",
                    category=self.categorize_tool(tool.name),
                    parameters=self.parse_input_schema(tool.inputSchema),
                    requires_auth=True,
                    organization_scope=True
                )
                
                # Apply category filter if specified
                if not category_filter or tool_info.category == category_filter:
                    tools.append(tool_info)
            
            return tools
            
        except Exception as e:
            logger.error(f"Failed to fetch MCP tools: {e}")
            raise
    
    def parse_input_schema(self, schema: dict) -> List[ToolParameter]:
        """Parse JSON Schema to extract parameter information"""
        if not schema or not schema.get('properties'):
            return []
        
        parameters = []
        properties = schema['properties']
        required_fields = schema.get('required', [])
        
        for name, prop in properties.items():
            parameters.append(ToolParameter(
                name=name,
                type=prop.get('type', 'string'),
                required=name in required_fields,
                description=prop.get('description'),
                default_value=prop.get('default')
            ))
        
        return parameters
    
    def categorize_tool(self, tool_name: str) -> str:
        """Categorize tools based on naming patterns"""
        if 'ticket' in tool_name.lower():
            return 'ticket_management'
        elif 'search' in tool_name.lower():
            return 'search_discovery'
        elif 'integration' in tool_name.lower():
            return 'integrations'
        elif 'health' in tool_name.lower() or 'system' in tool_name.lower():
            return 'system_monitoring'
        else:
            return 'general'
```

### 3. Response Schemas

```python
# app/schemas/tools.py
class ToolParameter(BaseModel):
    name: str
    type: str = "string"
    required: bool = False
    description: Optional[str] = None
    default_value: Optional[Any] = None

class ToolInfo(BaseModel):
    name: str
    description: str
    category: str
    parameters: List[ToolParameter] = []
    requires_auth: bool = True
    organization_scope: bool = True

class ToolListResponse(BaseModel):
    tools: List[ToolInfo]
    categories: List[str]
    total_count: int
```

### 4. Tool Categories

**Proposed categorization:**

- **`ticket_management`** - Ticket CRUD operations
- **`search_discovery`** - Search and filtering tools  
- **`integrations`** - Third-party integration tools
- **`system_monitoring`** - Health checks and system status
- **`file_operations`** - File handling and attachments
- **`user_management`** - User and organization tools

### 4. Frontend Integration

```typescript
// React component using REST API
interface ToolSelectionProps {
  selectedTools: string[];
  onToolsChange: (tools: string[]) => void;
}

const ToolSelector: React.FC<ToolSelectionProps> = ({ selectedTools, onToolsChange }) => {
  const { data: toolsData, isLoading, error } = useQuery(
    ['available-tools'],
    () => api.get('/api/v1/tools/').then(res => res.data),
    {
      staleTime: 5 * 60 * 1000, // Cache for 5 minutes
      refetchOnWindowFocus: false
    }
  );

  if (isLoading) return <div>Loading available tools...</div>;
  if (error) return <div>Failed to load tools. Please try again.</div>;

  return (
    <div className="tool-selection">
      <div className="tool-summary">
        {toolsData.total_count} tools available across {toolsData.categories.length} categories
      </div>
      
      {toolsData.categories.map(category => (
        <div key={category} className="tool-category">
          <h3>{category.replace('_', ' ').toUpperCase()}</h3>
          {toolsData.tools
            .filter(tool => tool.category === category)
            .map(tool => (
              <ToolCheckbox
                key={tool.name}
                tool={tool}
                selected={selectedTools.includes(tool.name)}
                onChange={onToolsChange}
              />
            ))}
        </div>
      ))}
    </div>
  );
};

// Tool checkbox component with parameter preview
const ToolCheckbox: React.FC<{
  tool: ToolInfo;
  selected: boolean;
  onChange: (tools: string[]) => void;
}> = ({ tool, selected, onChange }) => {
  return (
    <div className="tool-item">
      <label className="tool-checkbox">
        <input
          type="checkbox"
          checked={selected}
          onChange={(e) => {
            // Handle tool selection logic
          }}
        />
        <span className="tool-name">{tool.name}</span>
        <span className="tool-description">{tool.description}</span>
      </label>
      
      {tool.parameters.length > 0 && (
        <div className="tool-parameters">
          <small>{tool.parameters.length} parameters</small>
          <ParameterTooltip parameters={tool.parameters} />
        </div>
      )}
    </div>
  );
};
```

## Implementation Steps

### Phase 1: Backend REST Endpoint
1. **Create tool schemas** (`app/schemas/tools.py`)
2. **Implement MCP service** (`app/services/mcp_tool_service.py`)
3. **Add REST endpoint** (`app/api/v1/tools.py`) 
4. **Integrate with existing MCP client** infrastructure

### Phase 2: Tool Schema Processing
1. **JSON Schema parsing** for MCP tool parameters
2. **Category assignment** logic based on tool names
3. **Tool metadata enhancement** (display names, descriptions)
4. **Error handling** for MCP server connection issues

### Phase 3: Frontend Integration
1. **API client integration** for `/api/v1/tools/` endpoint
2. **Tool selector component** with categories and parameters
3. **Agent configuration UI** integration
4. **Caching and error handling**

### Phase 4: Enhanced Features
1. **Tool search and filtering** capabilities
2. **Parameter tooltips** with validation info  
3. **Tool recommendations** based on agent type
4. **Real-time availability** status indicators

## Benefits

### For Developers
- **Standards Compliance**: Uses official MCP specification `tools/list` internally
- **Consistent Architecture**: Maintains existing REST API patterns  
- **Better DX**: Automatic tool discovery with rich MCP schemas
- **Version Safety**: Frontend automatically adapts to MCP tool changes

### For Users  
- **Better UX**: Visual tool selection with descriptions from tool schemas
- **Discoverability**: Easy to find and understand available capabilities  
- **Rich Metadata**: Parameter types, descriptions, and requirements visible
- **Configuration Confidence**: Clear understanding of what each tool does

### For System
- **MCP Native**: Leverages MCP `tools/list` while maintaining REST architecture
- **Consistency**: Single source of truth from MCP server via REST wrapper
- **Scalability**: New MCP tools automatically appear in frontend UI
- **Maintainability**: Clean separation between MCP protocol and frontend concerns

## Technical Considerations

### Backend MCP Integration
- **Connection Reuse**: Leverage existing MCP client infrastructure
- **Authentication Flow**: Use existing user token passing to MCP server
- **Error Handling**: Graceful degradation when MCP server unavailable  
- **Schema Transformation**: Convert MCP JSON Schema to REST response format

### Performance
- **Tool List Caching**: Cache `tools/list` response for reasonable periods
- **Connection Reuse**: Maintain persistent MCP client connections
- **Lazy Loading**: Load tool schemas on-demand
- **Background Refresh**: Periodically refresh tool availability

### Security & Authorization
- **Token Forwarding**: Pass user authentication to MCP server
- **Tool Filtering**: MCP server filters tools based on user permissions  
- **Organization Scope**: Tools filtered by user's organization access
- **Schema Validation**: Validate tool schemas before UI generation

## Testing Strategy

### Unit Tests  
- MCP `tools/list` client integration
- JSON Schema parsing logic
- Tool categorization algorithms
- Cache management functionality

### Integration Tests
- MCP server `tools/list` connectivity
- Authentication token passing
- Tool schema validation  
- Error handling scenarios

### E2E Tests
- Complete agent configuration workflow with dynamic tools
- Tool selection UI with real MCP data
- Real-time tool availability updates
- Cross-browser MCP client compatibility

## Success Metrics

1. **Standards Compliance**: 100% usage of MCP specification `tools/list`
2. **Zero Backend Overhead**: No additional API endpoints created
3. **Configuration Accuracy**: Reduced invalid tool configurations via schema validation  
4. **User Experience**: Improved agent setup with rich tool metadata

## Key Advantages of REST Wrapper Approach

✅ **MCP Standards Compliant** - Uses official `tools/list` operation internally  
✅ **Consistent Architecture** - Frontend continues using familiar REST patterns  
✅ **Rich Schema Data** - JSON Schema from MCP transformed to REST format  
✅ **Future Proof** - Leverages MCP protocol while maintaining REST interface  
✅ **Authentication Integrated** - Reuses existing JWT auth flow  
✅ **Tool Filtering** - MCP server-side filtering via user permissions  
✅ **Caching & Performance** - REST layer can implement caching strategies