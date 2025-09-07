# PRP: AI Agent Architecture Refactoring

**Status:** Planning  
**Date:** September 3, 2025  
**Author:** Claude Code  
**Related Systems:** AI Services, Customer Support Agent, MCP Integration, Organization Management  

## Summary

This PRP outlines a comprehensive refactoring of the AI service architecture to implement a proper agent-based design with organization-level configuration management. The refactoring will enable proper MCP tool integration, organization-scoped agent instances, and comprehensive agent lifecycle management.

## Current State Analysis

### **Issues Discovered in Docker Logs:**

✅ **MCP Client Status:**
- MCP client successfully connects: `✅ AI Ticket Creator MCP client initialized and ready`
- All 13 tools available: `['create_ticket', 'create_ticket_with_ai', 'get_ticket', ...]`
- Connection healthy: `{'is_connected': True, 'client_available': True}`

❌ **Tool Integration Problem:**
- **Tools not being called:** `Tools used: []` in all chat responses
- **MCP integration disabled:** `MCP client integration disabled for basic AI functionality`
- **Agent created without MCP:** `Customer Support chat agent created (MCP server available but not integrated)`

**Root Cause:** Line 334 in `ai_chat_service.py`:
```python
# Create agent without MCP tools for now (MCP integration can be added later)
```

### **Current Architecture Problems:**

1. **Stateless Agent Creation:** Agents are created per request, no persistence
2. **No Organization Scoping:** All users share the same agent configuration
3. **MCP Integration Disabled:** Tools available but not connected to agents
4. **No Agent Management:** No way to configure, update, or manage agents
5. **Limited Configuration:** Static prompts and model settings

## Proposed Architecture

### **Core Components**

#### 1. **AIAgent Model** (Database Entity)
```python
class AIAgent(BaseModel):
    """Organization-scoped AI agent with persistent configuration"""
    id: UUID
    organization_id: UUID
    agent_type: str = "customer_support"  # Future: multiple agent types
    name: str = "Customer Support Agent"
    is_active: bool = True
    configuration: AIAgentConfiguration
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime]
    
    # Relationships
    organization: Organization
    usage_stats: List[AgentUsageStats]
```

#### 2. **AIAgentConfiguration Model** (Embedded/Separate)
```python
class AIAgentConfiguration(BaseModel):
    """Complete agent configuration with MCP tools - defaults from ai_config.yaml"""
    # Core AI Settings (from ai_config.yaml agents.customer_support_agent)
    system_prompt: str = Field(default_factory=lambda: load_prompt_template("customer_support_default"))
    model_provider: str = "openai"  # From ai_config.yaml
    model_name: str = "primary"     # From ai_config.yaml  
    temperature: float = 0.2        # From ai_config.yaml
    max_tokens: int = 2000          # From ai_config.yaml
    timeout: int = 30               # From ai_config.yaml
    
    # MCP Tool Configuration (updated from old config)
    tools_enabled: List[str] = [
        # All 13 current MCP tools (updated from old 4-tool list)
        "create_ticket", "create_ticket_with_ai", "get_ticket",
        "update_ticket", "delete_ticket", "update_ticket_status", 
        "assign_ticket", "search_tickets", "list_tickets", "get_ticket_stats",
        "list_integrations", "get_active_integrations", "get_system_health"
    ]
    mcp_enabled: bool = True  # Enable MCP integration by default
    
    # Behavioral Settings (from ai_config.yaml)
    confidence_threshold: float = 0.7  # From ai_config.yaml
    auto_escalation_enabled: bool = True
    integration_routing_enabled: bool = True
    
    # Customization (organization-specific overrides)
    response_style: str = "professional"  # professional, casual, technical
    default_priority: str = "medium"
    default_category: str = "general"

def load_prompt_template(template_name: str) -> str:
    """Load prompt template from ai_config.yaml"""
    # Loads from ai_config.yaml:prompt_templates:customer_support_default
    # Falls back to CUSTOMER_SUPPORT_CHAT_PROMPT if config not available
```

#### 3. **CustomerSupportAgent Class** (Service Layer)
```python
class CustomerSupportAgent:
    """Organization-scoped customer support agent with MCP integration"""
    
    def __init__(self, organization_id: UUID, configuration: AIAgentConfiguration):
        self.organization_id = organization_id
        self.configuration = configuration
        self.pydantic_agent: Optional[Agent] = None
        self.mcp_tools: List[str] = []
        
    async def initialize(self) -> None:
        """Initialize Pydantic AI agent with MCP tools"""
        
    async def process_message(self, message: str, context: CustomerSupportContext) -> ChatResponse:
        """Process user message with full MCP tool access"""
        
    async def update_configuration(self, updates: AIAgentConfigurationUpdate) -> None:
        """Update agent configuration and rebuild if needed"""
        
    def get_available_tools(self) -> List[str]:
        """Get list of enabled MCP tools"""
        
    def is_active(self) -> bool:
        """Check if agent is active and ready"""
```

### **Organization-Scoped Agent Management**

#### **Automatic Agent Creation:**
- **Each organization automatically gets a Customer Support Agent** when created
- Agent is created with **default configuration from `ai_config.yaml`**
- **No manual setup required** - agents are ready immediately
- Organizations can **customize agent configuration** after creation

#### **Singleton Pattern per Organization:**
- Each organization has **exactly one Customer Support Agent**
- Agent configuration is **organization-specific**
- Users within an organization share the same agent instance
- Agent configuration can be **customized per organization** while maintaining defaults

#### **Agent Lifecycle:**
1. **Automatic Creation:** When organization is created, agent is automatically provisioned
2. **Default Configuration:** Agent starts with settings from `ai_config.yaml`
3. **Activation:** Agent becomes active and ready to handle requests immediately  
4. **Configuration Updates:** Organizations can modify prompts, tools, model settings
5. **Deactivation:** Temporarily disable agent (fallback to basic responses)
6. **Reactivation:** Re-enable agent with previous configuration
7. **Deletion:** Remove agent (organization loses AI capabilities, can recreate)

## API Endpoints Design

### **Agent Management Endpoints**

```http
# Organization Agent Management (Automatic Creation)
GET    /api/v1/agents/organization/{org_id}           # Get organization's agent (auto-creates if missing)
PUT    /api/v1/agents/organization/{org_id}           # Update agent configuration
DELETE /api/v1/agents/organization/{org_id}           # Delete organization agent
POST   /api/v1/agents/organization/{org_id}/recreate  # Recreate agent with defaults from ai_config.yaml

# Agent Status Management
PATCH  /api/v1/agents/{agent_id}/activate             # Activate agent
PATCH  /api/v1/agents/{agent_id}/deactivate           # Deactivate agent  
PATCH  /api/v1/agents/{agent_id}/reset-config         # Reset to ai_config.yaml defaults
GET    /api/v1/agents/{agent_id}/status               # Get agent status and health

# Agent Configuration Management
GET    /api/v1/agents/{agent_id}/configuration        # Get full configuration
PUT    /api/v1/agents/{agent_id}/configuration        # Update configuration (preserves custom settings)
GET    /api/v1/agents/{agent_id}/tools                # Get enabled tools
PUT    /api/v1/agents/{agent_id}/tools                # Update enabled tools
GET    /api/v1/agents/{agent_id}/config-source        # Show which settings come from ai_config.yaml vs custom

# Agent Analytics
GET    /api/v1/agents/{agent_id}/stats                # Get usage statistics
GET    /api/v1/agents/{agent_id}/performance          # Get performance metrics
```

### **Request/Response Schemas**

```python
# Agent Creation Request
class CreateAgentRequest(BaseModel):
    name: str = "Customer Support Agent"
    configuration: AIAgentConfiguration

# Agent Update Request  
class UpdateAgentRequest(BaseModel):
    name: Optional[str] = None
    configuration: Optional[AIAgentConfigurationUpdate] = None

# Agent Response
class AgentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    agent_type: str
    is_active: bool
    configuration: AIAgentConfiguration
    status: AgentStatus
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

# Tool Configuration
class ToolConfiguration(BaseModel):
    enabled_tools: List[str]
    available_tools: List[str] = [
        # All 13 MCP tools
        "create_ticket", "create_ticket_with_ai", "get_ticket", "update_ticket",
        "delete_ticket", "update_ticket_status", "assign_ticket", "search_tickets", 
        "list_tickets", "get_ticket_stats", "list_integrations", 
        "get_active_integrations", "get_system_health"
    ]
```

## Configuration Integration with ai_config.yaml

### **Default Configuration Loading:**
```python
async def load_default_agent_configuration() -> AIAgentConfiguration:
    """Load default configuration from ai_config.yaml"""
    
    # Load from app/config/ai_config.yaml
    config = await ai_config_service.get_agent_config("customer_support_agent")
    
    return AIAgentConfiguration(
        # Load from ai_config.yaml:prompt_templates:customer_support_default
        system_prompt=await load_prompt_template("customer_support_default"),
        
        # Load from ai_config.yaml:agents:customer_support_agent
        model_provider=config.get("model_provider", "openai"),
        model_name=config.get("model_name", "primary"), 
        temperature=config.get("temperature", 0.2),
        max_tokens=config.get("max_tokens", 2000),
        timeout=config.get("timeout", 30),
        confidence_threshold=config.get("confidence_threshold", 0.7),
        
        # Updated tool list (replace old 4-tool list with all 13 tools)
        tools_enabled=[
            "create_ticket", "create_ticket_with_ai", "get_ticket",
            "update_ticket", "delete_ticket", "update_ticket_status",
            "assign_ticket", "search_tickets", "list_tickets", "get_ticket_stats", 
            "list_integrations", "get_active_integrations", "get_system_health"
        ],
        mcp_enabled=True  # Enable by default (current config disables this)
    )
```

### **Organization Agent Auto-Creation:**
```python
async def ensure_organization_agent(organization_id: UUID) -> CustomerSupportAgent:
    """Ensure organization has a customer support agent (create if missing)"""
    
    # Check if agent exists
    agent = await ai_agent_service.get_organization_agent(organization_id)
    
    if not agent:
        logger.info(f"🤖 Auto-creating Customer Support Agent for organization {organization_id}")
        
        # Load default configuration from ai_config.yaml
        default_config = await load_default_agent_configuration()
        
        # Create agent with defaults
        agent = await ai_agent_service.create_organization_agent(
            organization_id=organization_id,
            configuration=default_config,
            auto_created=True
        )
        
        logger.info(f"✅ Customer Support Agent auto-created for organization {organization_id}")
        
    return agent

# Called automatically during:
# 1. Organization creation (post_create hook)
# 2. First chat message (if agent missing)
# 3. API requests requiring agent access
```

## Pre-Implementation: Test Suite Refactoring

### **🧪 REQUIRED: Test Suite Updates Before Starting**

Before beginning any refactoring phases, the existing test suite must be updated to support the new architecture and provide proper validation coverage.

#### **Current Test Suite Analysis:**
```bash
# Current test status (from pytest output):
# 176 tests total, many failing due to missing dependencies
# MCP server tests: 9 passed, 26 skipped 
# Core functionality tests needed for validation
```

#### **Test Infrastructure Updates:**

1. **Fix Dependency Issues:**
```bash
# Install missing dependencies that cause test collection failures:
poetry install --with test
poetry add --group test pydantic-ai httpx-sse pytest-mock

# Verify basic imports work:
poetry run pytest tests/test_simple.py -v
```

2. **Create Test Configuration:**
```python
# tests/conftest.py - ADD test configuration
@pytest.fixture
async def test_organization():
    """Create test organization for agent testing"""
    
@pytest.fixture  
async def test_mcp_client():
    """Create test MCP client with mock server"""
    
@pytest.fixture
async def test_agent_configuration():
    """Create test agent configuration from ai_config.yaml"""
```

3. **Mock Infrastructure:**
```python
# tests/mocks/mock_mcp_server.py - NEW
class MockMCPServer:
    """Mock MCP server for testing tool calls"""
    
# tests/mocks/mock_ai_config.py - NEW  
class MockAIConfig:
    """Mock ai_config.yaml for testing configuration loading"""
```

#### **Baseline Test Requirements:**
```bash
# These tests MUST pass before starting any refactoring:
poetry run pytest tests/test_mcp_server.py -v                    # MCP tools working
poetry run pytest tests/test_simple.py -v                       # Basic imports
poetry run pytest tests/test_api_basic.py -v                    # API basics
poetry run pytest tests/test_docker_validation.py -v           # Docker health

# Current status check:
docker compose ps  # All services must be healthy
docker compose logs --tail=50 | grep -E "(ERROR|FATAL)"  # Should be minimal
```

## Implementation Plan with Testing & Validation

### **🚨 CRITICAL REQUIREMENT: Testing & Validation Gates**

**Before proceeding to ANY next phase:**
1. ✅ **All tests must pass** - Run full test suite and fix failures
2. ✅ **Docker logs must be clean** - Monitor `docker compose logs` for errors
3. ✅ **Functionality validated** - Manual testing of implemented features
4. ✅ **Integration tests pass** - MCP client/server communication verified

### **Phase 1: MCP Client Setup & Immediate Tool Integration** 
**Objective:** Fix current MCP integration to enable tool calling

#### **Implementation Steps:**
1. **Update MCP Client Implementation** - Follow https://ai.pydantic.dev/mcp/client/ patterns
   - Use `MCPServerStreamableHTTP` with proper URL and elicitation callback
   - Fix `ai_chat_service.py` line 334: Add `toolsets=[mcp_server]` to Agent creation
   - Remove `# MCP integration disabled` comments and enable tools

2. **Enable Tool Calling in Current Agent**
   - Update `create_chat_agent()` to use MCP tools immediately
   - Test with simple queries like "What integrations are active?"

3. **Add Basic Elicitation Support**
   - Implement elicitation callback for missing parameter requests
   - Add chat service handling for elicitation prompts

#### **🧪 Phase 1 Testing Requirements:**
```bash
# Test Suite Updates Required:
tests/test_mcp_client_integration.py     # NEW - Test MCP client with Pydantic AI
tests/test_ai_chat_service_tools.py      # NEW - Test tool calling in chat service
tests/test_elicitation_handling.py       # NEW - Test elicitation workflows

# Existing Test Updates:
tests/test_mcp_server.py                 # Update - Verify all 13 tools accessible
tests/test_ai_chat_service.py           # Update - Test with MCP tools enabled
tests/test_chat_integration.py          # Update - Integration testing with tools

# Validation Commands:
poetry run pytest tests/test_mcp_client_integration.py -v
poetry run pytest tests/test_ai_chat_service_tools.py -v
poetry run pytest tests/test_chat_integration.py -v
```

#### **🔍 Phase 1 Docker Log Validation:**
```bash
# Monitor for successful tool integration:
docker compose logs app | grep -E "(Tools used|MCP.*tool|🔧)"
docker compose logs mcp-server | grep -E "(TOOL.*REQUEST|TOOL.*RESPONSE)" 

# Expected log patterns:
# ✅ "Tools used: ['get_active_integrations']"
# ✅ "🔧 MCP TOOL REQUEST #123: get_active_integrations"
# ✅ "✅ MCP TOOL RESPONSE #123: get_active_integrations (150ms)"

# Red flags to watch for:
# ❌ "Tools used: []"
# ❌ "MCP client integration disabled"
# ❌ "agent created without MCP tools"
```

#### **✅ Phase 1 Success Criteria:**
- [ ] MCP client properly configured with elicitation callback
- [ ] AI agent created WITH `toolsets=[mcp_server]` parameter
- [ ] Query "What integrations are active?" results in `get_active_integrations` tool call
- [ ] Docker logs show actual tool calls: `🔧 MCP TOOL REQUEST/RESPONSE`
- [ ] All existing tests still pass
- [ ] New MCP integration tests pass

---

### **Phase 2: Configuration Integration**
**Objective:** Integrate ai_config.yaml for agent defaults

#### **Implementation Steps:**
1. Update `ai_config.yaml` with complete 13-tool list and updated prompts
2. Create configuration loader functions for agent defaults
3. Update chat service to use config-driven agent creation

#### **🧪 Phase 2 Testing Requirements:**
```bash
# Test Suite Updates:
tests/test_ai_config_integration.py      # NEW - Test config file loading
tests/test_agent_configuration.py        # NEW - Test configuration validation
tests/test_prompt_template_loading.py    # NEW - Test prompt loading from config

# Validation Commands:
poetry run pytest tests/test_ai_config_integration.py -v
poetry run pytest tests/test_agent_configuration.py -v
```

#### **🔍 Phase 2 Docker Log Validation:**
```bash
# Monitor for configuration loading:
docker compose logs app | grep -E "(ai_config|prompt.*template|configuration.*loaded)"

# Expected patterns:
# ✅ "Loading agent configuration from ai_config.yaml"
# ✅ "Prompt template loaded: customer_support_default"
# ✅ "Agent created with 13 tools from configuration"
```

---

### **Phase 3: Database Schema & Models**
**Objective:** Create AIAgent database entities with organization scoping

#### **🧪 Phase 3 Testing Requirements:**
```bash
# Test Suite Updates:
tests/test_ai_agent_model.py             # NEW - Test AIAgent database model
tests/test_agent_service_crud.py         # NEW - Test agent CRUD operations
tests/test_organization_agent_relationship.py  # NEW - Test org scoping

# Migration Testing:
poetry run alembic upgrade head           # Apply new schema
poetry run pytest tests/test_database_migration.py -v
```

#### **🔍 Phase 3 Docker Log Validation:**
```bash
# Monitor database operations:
docker compose logs postgres | grep -E "(ERROR|FATAL)"
docker compose logs app | grep -E "(agent.*created|migration.*complete)"
```

---

### **Phase 4: Agent Service Layer**
**Objective:** Implement AIAgentService with automatic provisioning

#### **🧪 Phase 4 Testing Requirements:**
```bash
# Test Suite Updates:
tests/test_ai_agent_service.py           # NEW - Test service layer operations
tests/test_automatic_agent_creation.py   # NEW - Test auto-provisioning
tests/test_organization_hooks.py         # NEW - Test org creation hooks

# Integration Testing:
poetry run pytest tests/test_agent_lifecycle.py -v
```

---

### **Phase 5: Customer Support Agent Refactoring**
**Objective:** Implement persistent, configurable CustomerSupportAgent

#### **🧪 Phase 5 Testing Requirements:**
```bash
# Test Suite Updates:
tests/test_customer_support_agent_refactored.py  # NEW - Test new agent class
tests/test_agent_tool_integration.py             # NEW - Test MCP tool calling
tests/test_agent_elicitation.py                  # NEW - Test elicitation workflows
```

---

### **Phase 6: Chat Service Integration**
**Objective:** Update chat service to use organization-scoped agents

#### **🧪 Phase 6 Testing Requirements:**
```bash
# Test Suite Updates:
tests/test_chat_service_agent_integration.py    # NEW - Test agent integration
tests/test_organization_scoped_chat.py          # NEW - Test org scoping
tests/test_chat_elicitation_flow.py             # NEW - Test elicitation in chat

# End-to-End Testing:
poetry run pytest tests/test_chat_e2e.py -v
```

---

### **Phase 7: API Layer & Documentation**
**Objective:** Complete agent management API and regenerate documentation

#### **🧪 Phase 7 Testing Requirements:**
```bash
# Test Suite Updates:
tests/test_agent_api_endpoints.py        # NEW - Test agent management API
tests/test_agent_crud_api.py            # NEW - Test CRUD operations via API
tests/test_api_authentication.py        # UPDATE - Test org-scoped access

# API Testing:
poetry run pytest tests/test_api_endpoints.py -v
poetry run pytest tests/test_integration_comprehensive.py -v
```

#### **📋 Phase 7 Documentation Generation:**
```bash
# Regenerate OpenAPI Specification:
curl http://localhost:8000/openapi.json > docs/openapi.json
poetry run python scripts/generate_openapi_docs.py

# Regenerate Postman Collection:
poetry run python scripts/generate_postman_collection.py
# Output: docs/postman/AI_Ticket_Creator_API.postman_collection.json

# Update API Documentation:
poetry run python scripts/update_api_docs.py
```

#### **🔍 Final Docker Log Validation:**
```bash
# Comprehensive system health check:
docker compose logs --tail=50 | grep -E "(ERROR|FATAL|WARN)"
docker compose logs app | grep -E "(agent.*initialized|Tools used|MCP.*tool)"
docker compose logs mcp-server | grep -E "(TOOL.*REQUEST|TOOL.*RESPONSE)"

# Expected final state:
# ✅ "Customer Support Agent auto-created for organization"
# ✅ "Agent initialized with 13 MCP tools enabled"
# ✅ "🔧 MCP Tools used: ['get_active_integrations', 'create_ticket_with_ai']"
# ✅ "All systems healthy - no errors in logs"
```

## Test Suite Refactoring Requirements

### **New Test Files Required:**

#### **MCP Integration Tests:**
```python
# tests/test_mcp_client_integration.py
class TestMCPClientIntegration:
    async def test_mcp_client_connection()
    async def test_mcp_tool_discovery()
    async def test_mcp_tool_calling()
    async def test_elicitation_handling()

# tests/test_ai_chat_service_tools.py  
class TestAIChatServiceTools:
    async def test_agent_created_with_tools()
    async def test_tool_calling_in_chat()
    async def test_elicitation_in_chat()
    async def test_tool_error_handling()
```

#### **Agent Management Tests:**
```python
# tests/test_ai_agent_model.py
class TestAIAgentModel:
    async def test_agent_creation()
    async def test_organization_relationship()
    async def test_configuration_validation()
    async def test_agent_status_management()

# tests/test_ai_agent_service.py
class TestAIAgentService:
    async def test_automatic_agent_creation()
    async def test_organization_scoped_agents()
    async def test_agent_crud_operations()
    async def test_configuration_updates()
```

#### **Integration Tests:**
```python
# tests/test_organization_agent_integration.py
class TestOrganizationAgentIntegration:
    async def test_auto_creation_on_org_creation()
    async def test_agent_availability_guarantee()
    async def test_singleton_per_organization()
    async def test_agent_inheritance_from_config()

# tests/test_chat_e2e.py
class TestChatEndToEnd:
    async def test_complete_chat_flow_with_tools()
    async def test_elicitation_workflow()
    async def test_tool_calling_across_conversation()
    async def test_integration_discovery_flow()
```

### **Updated Existing Tests:**
```python
# tests/test_mcp_server.py - UPDATE
class TestMCPServer:
    # Add tests for new tool registration system
    async def test_modular_tool_registration()
    async def test_all_13_tools_available()

# tests/test_ai_chat_service.py - UPDATE  
class TestAIChatService:
    # Update tests to expect tool calling
    async def test_chat_agent_with_mcp_tools()  # Replace old test
    async def test_tool_calling_enabled()       # NEW

# tests/test_chat_integration.py - UPDATE
class TestChatIntegration:
    # Update to test actual tool integration
    async def test_integration_tool_calling()
    async def test_agent_tool_access()
```

## Validation Gates Between Phases

### **Gate 1: MCP Integration Validation**
**Required before Phase 2:**
```bash
# Must pass all tests:
poetry run pytest tests/test_mcp_client_integration.py -v
poetry run pytest tests/test_ai_chat_service_tools.py -v
poetry run pytest tests/test_mcp_server.py -v

# Must show tool calling in logs:
docker compose logs app | grep "Tools used:" | grep -v "Tools used: \[\]"

# Must respond to test query:
curl -X POST http://localhost:8000/api/v1/chat/test \
  -H "Content-Type: application/json" \
  -d '{"message": "What integrations are active?"}'
# Response should show tools_used: ["get_active_integrations"]
```

### **Gate 2: Configuration Integration Validation**
**Required before Phase 3:**
```bash
# Configuration loading tests:
poetry run pytest tests/test_ai_config_integration.py -v
poetry run pytest tests/test_agent_configuration.py -v

# Verify config file integration:
docker compose logs app | grep -E "(config.*loaded|prompt.*template.*loaded)"
```

### **Gate 3: Database Schema Validation**
**Required before Phase 4:**
```bash
# Migration and model tests:
poetry run alembic upgrade head
poetry run pytest tests/test_ai_agent_model.py -v
poetry run pytest tests/test_database_migration.py -v

# Database health check:
docker compose logs postgres | grep -v "LOG:"  # Should show no errors
```

### **Gate 4: Service Layer Validation**
**Required before Phase 5:**
```bash
# Service layer tests:
poetry run pytest tests/test_ai_agent_service.py -v
poetry run pytest tests/test_automatic_agent_creation.py -v

# Verify agent provisioning:
docker compose logs app | grep -E "(agent.*auto-created|agent.*provisioned)"
```

### **Gate 5: Agent Refactoring Validation**
**Required before Phase 6:**
```bash
# Agent implementation tests:
poetry run pytest tests/test_customer_support_agent_refactored.py -v
poetry run pytest tests/test_agent_tool_integration.py -v

# Verify agent functionality:
docker compose logs app | grep -E "(agent.*initialized.*tools|MCP.*tools.*enabled)"
```

### **Gate 6: Chat Integration Validation**
**Required before Phase 7:**
```bash
# Chat service integration tests:
poetry run pytest tests/test_chat_service_agent_integration.py -v
poetry run pytest tests/test_organization_scoped_chat.py -v
poetry run pytest tests/test_chat_elicitation_flow.py -v

# End-to-end validation:
poetry run pytest tests/test_chat_e2e.py -v
```

### **Gate 7: Final System Validation**
**Required before completion:**
```bash
# Complete test suite validation:
poetry run pytest tests/ -v --tb=short

# API endpoint testing:
poetry run pytest tests/test_agent_api_endpoints.py -v
poetry run pytest tests/test_api_endpoints.py -v

# System health validation:
docker compose ps  # All services healthy
docker compose logs --tail=100 | grep -E "(ERROR|FATAL)" | wc -l  # Should be 0

# Manual validation:
curl http://localhost:8000/health  # Should be healthy
curl http://localhost:8001/health  # Should show 13 tools available
```

## Docker Log Monitoring Strategy

### **Continuous Monitoring Commands:**
```bash
# Real-time log monitoring during development:
docker compose logs -f app mcp-server | grep -E "(ERROR|WARN|Tools used|MCP.*tool)"

# Phase-specific monitoring:
# Phase 1: docker compose logs app | grep -E "(MCP.*tool|Tools used|elicitation)"
# Phase 2: docker compose logs app | grep -E "(config.*loaded|template.*loaded)" 
# Phase 3: docker compose logs postgres | grep -E "(ERROR|migration)"
# Phase 4: docker compose logs app | grep -E "(agent.*service|auto.*created)"
# Phase 5: docker compose logs app | grep -E "(agent.*initialized|CustomerSupportAgent)"
# Phase 6: docker compose logs app | grep -E "(chat.*agent|conversation.*agent)"
# Phase 7: docker compose logs app | grep -E "(API.*agent|endpoint.*agent)"
```

### **Log Patterns to Watch:**

#### **✅ Success Patterns:**
```log
✅ Customer Support Agent auto-created for organization {org_id}
✅ Agent initialized with 13 MCP tools enabled
🔧 MCP Tools used: ['get_active_integrations']
📋 MCP TOOL REQUEST #123: get_active_integrations
✅ MCP TOOL RESPONSE #123: get_active_integrations (150ms)
```

#### **❌ Error Patterns to Fix:**
```log
❌ Tools used: []
❌ MCP client integration disabled
❌ agent created without MCP tools
❌ Failed to connect to MCP server
❌ Tool call failed: {error}
ERROR: {any error in logs}
```

## Final Phase: Documentation Regeneration

### **OpenAPI Specification Update:**
```bash
# Regenerate complete OpenAPI spec with new agent endpoints:
curl http://localhost:8000/openapi.json > docs/openapi.json

# Validate OpenAPI spec:
poetry run python scripts/validate_openapi.py docs/openapi.json

# Generate human-readable API docs:
poetry run python scripts/generate_api_docs.py
```

### **Postman Collection Regeneration:**
```bash
# Generate updated Postman collection:
poetry run python scripts/generate_postman_collection.py \
  --openapi docs/openapi.json \
  --output docs/postman/AI_Ticket_Creator_API.postman_collection.json

# Validate Postman collection:
poetry run python scripts/validate_postman_collection.py
```

### **Required Documentation Files:**
- `docs/openapi.json` - Complete API specification with agent endpoints
- `docs/postman/AI_Ticket_Creator_API.postman_collection.json` - Updated collection
- `docs/api/agent_management.md` - Agent API documentation  
- `docs/api/mcp_tools.md` - MCP tool calling documentation
- `docs/examples/agent_configuration.md` - Configuration examples

### **Automated Validation Scripts:**

#### **Create Test Automation Scripts:**
```bash
# scripts/validate_phase.sh - Phase validation automation
#!/bin/bash
PHASE=$1
echo "🧪 Validating Phase $PHASE..."

# Run phase-specific tests
case $PHASE in
  1) poetry run pytest tests/test_mcp_client_integration.py tests/test_ai_chat_service_tools.py -v ;;
  2) poetry run pytest tests/test_ai_config_integration.py tests/test_agent_configuration.py -v ;;
  3) poetry run pytest tests/test_ai_agent_model.py tests/test_database_migration.py -v ;;
  4) poetry run pytest tests/test_ai_agent_service.py tests/test_automatic_agent_creation.py -v ;;
  5) poetry run pytest tests/test_customer_support_agent_refactored.py tests/test_agent_tool_integration.py -v ;;
  6) poetry run pytest tests/test_chat_service_agent_integration.py tests/test_chat_e2e.py -v ;;
  7) poetry run pytest tests/ -v --tb=short ;;
esac

# Check Docker logs for phase-specific patterns
echo "🔍 Checking Docker logs..."
docker compose logs --tail=100 | grep -E "(ERROR|FATAL|WARN)"
echo "✅ Phase $PHASE validation complete"

# scripts/test_mcp_integration.sh - MCP integration testing  
#!/bin/bash
echo "🔧 Testing MCP Integration..."

# Test tool calling
curl -X POST http://localhost:8000/api/v1/chat/conversations/test/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "What integrations are active?"}' | jq '.tools_used'

echo "🔍 Checking for tool calls in logs..."
docker compose logs app | grep "Tools used:" | tail -5

# scripts/generate_docs.sh - Documentation regeneration
#!/bin/bash  
echo "📋 Regenerating API Documentation..."

# Generate OpenAPI spec
curl http://localhost:8000/openapi.json > docs/openapi.json

# Generate Postman collection (if script exists)
if [ -f scripts/generate_postman_collection.py ]; then
  poetry run python scripts/generate_postman_collection.py
fi

echo "✅ Documentation regeneration complete"
```

### **Final Validation Checklist:**

#### **Technical Validation:**
- [ ] All 176+ tests pass (current test count from pytest output)
- [ ] Docker compose shows all services healthy (`docker compose ps`)
- [ ] No errors in logs (`docker compose logs | grep -E "(ERROR|FATAL)" | wc -l` = 0)
- [ ] MCP client successfully calls all 13 tools
- [ ] All new test files created and passing

#### **Functional Validation:**
- [ ] Agents auto-created for organizations with ai_config.yaml defaults
- [ ] Tool calling working: Query results in `Tools used: ['tool_name']`
- [ ] Elicitation works for incomplete user requests
- [ ] Configuration loading from ai_config.yaml working
- [ ] Organization scoping working (agents isolated per org)

#### **API Validation:**
- [ ] All agent management endpoints working and tested
- [ ] OpenAPI spec includes all new agent endpoints  
- [ ] Postman collection updated with agent management examples
- [ ] API authentication working for org-scoped agent access

#### **Documentation Validation:**
- [ ] `docs/openapi.json` - Updated with agent endpoints
- [ ] `docs/postman/` - Updated collection with examples
- [ ] `docs/api/` - New agent management documentation
- [ ] All documentation reflects new architecture

#### **Manual Testing Validation:**
```bash
# Ultimate success test:
# 1. Send message: "What integrations are active?"
# 2. Check logs: Should show Tools used: ['get_active_integrations']  
# 3. Check response: Should contain actual integration data
# 4. Verify: Docker logs show successful MCP tool calls

# Test script:
curl -X POST http://localhost:8000/api/v1/chat/test \
  -H "Content-Type: application/json" \
  -d '{"message": "What integrations are active?"}'

# Expected log output:
# ✅ "🔧 MCP Tools used: ['get_active_integrations']"
# ✅ "📋 Tool result: Found 3 active integrations"
```

## Critical Success Metric

**The ultimate test:** After refactoring, this query should work:

**User:** `"What integrations are active?"`
**Expected Result:** 
```log
🔧 MCP Tools used: ['get_active_integrations']
📋 Tool result: {"active_integrations": [...]}
✅ User receives actual integration data (not guidance)
```

**Current Broken State:**
```log 
Tools used: []
❌ User receives guidance about checking integrations (no actual data)
```

## Test Execution and Validation Automation

### **Master Test Script:**
```bash
# scripts/run_refactor_with_validation.sh
#!/bin/bash
set -e

echo "🚀 Starting AI Agent Architecture Refactoring with Full Validation"
echo "=================================================================="

# Pre-implementation validation
echo "📋 Pre-implementation: Fixing test suite..."
poetry install --with test
poetry run pytest tests/test_mcp_server.py -v
if [ $? -ne 0 ]; then
  echo "❌ Baseline tests failed - fix before proceeding"
  exit 1
fi

# Phase 1: MCP Client Setup
echo "🔧 Phase 1: MCP Client Setup & Tool Integration..."
# [Implementation steps here]
bash scripts/validate_phase.sh 1
if [ $? -ne 0 ]; then
  echo "❌ Phase 1 validation failed"
  exit 1
fi

# Phase 2: Configuration Integration  
echo "⚙️ Phase 2: Configuration Integration..."
# [Implementation steps here]
bash scripts/validate_phase.sh 2
if [ $? -ne 0 ]; then
  echo "❌ Phase 2 validation failed"
  exit 1
fi

# [Continue for all phases...]

# Final validation
echo "🎯 Final Validation..."
bash scripts/validate_phase.sh 7
poetry run pytest tests/ -v --tb=short

# Generate documentation
echo "📋 Generating final documentation..."
bash scripts/generate_docs.sh

echo "🎉 Refactoring completed successfully!"
echo "✅ All tests passed, Docker logs clean, MCP tools working"
```

### **Docker Health Monitoring:**
```bash
# scripts/monitor_docker_health.sh
#!/bin/bash

echo "🔍 Monitoring Docker Health During Refactoring..."

# Function to check service health
check_service_health() {
  SERVICE=$1
  echo "Checking $SERVICE..."
  
  # Check if service is running
  if ! docker compose ps $SERVICE | grep -q "Up"; then
    echo "❌ $SERVICE is not running"
    return 1
  fi
  
  # Check for errors in logs
  ERROR_COUNT=$(docker compose logs $SERVICE --tail=100 | grep -E "(ERROR|FATAL)" | wc -l)
  if [ $ERROR_COUNT -gt 0 ]; then
    echo "❌ $SERVICE has $ERROR_COUNT errors in recent logs"
    docker compose logs $SERVICE --tail=10 | grep -E "(ERROR|FATAL)"
    return 1
  fi
  
  echo "✅ $SERVICE is healthy"
  return 0
}

# Check all services
SERVICES="app mcp-server postgres redis celery-worker flower"
for service in $SERVICES; do
  check_service_health $service
done

# Specific MCP integration check
echo "🔧 Checking MCP integration..."
MCP_TOOLS_COUNT=$(curl -s http://localhost:8001/health | jq '.tools_available')
if [ "$MCP_TOOLS_COUNT" -ne 13 ]; then
  echo "❌ Expected 13 MCP tools, found $MCP_TOOLS_COUNT"
  exit 1
fi

echo "✅ All Docker services healthy, MCP integration working"
```

### **Continuous Integration Requirements:**
```yaml
# .github/workflows/refactor_validation.yml (if using GitHub Actions)
name: Refactor Validation
on: [push, pull_request]

jobs:
  validate-refactor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Start services
        run: docker compose up -d
      - name: Wait for services
        run: sleep 30
      - name: Run validation
        run: bash scripts/run_refactor_with_validation.sh
      - name: Check Docker health
        run: bash scripts/monitor_docker_health.sh
      - name: Generate documentation
        run: bash scripts/generate_docs.sh
```

## Delivery Requirements

### **Definition of Done:**
1. ✅ **All phases completed with tests passing**
2. ✅ **Docker logs show tool calling: `Tools used: ['get_active_integrations']`**
3. ✅ **Query "What integrations are active?" returns actual data**
4. ✅ **All 13 MCP tools accessible and working**
5. ✅ **Organizations auto-get agents with ai_config.yaml defaults**
6. ✅ **OpenAPI spec and Postman collection regenerated**
7. ✅ **Documentation updated to reflect new architecture**

### **Rollback Plan:**
If any phase fails validation:
1. **Revert changes** to last passing state
2. **Fix issues** identified in tests or Docker logs
3. **Re-run validation** for that phase
4. **Proceed only** when all validation gates pass

The refactoring is designed to be **incremental and safe**, with comprehensive testing and validation at every step to ensure the system remains functional throughout the process.

## MCP Integration Architecture

### **Current Issue:**
```python
# Line 334 in ai_chat_service.py - MCP integration disabled
agent = Agent(
    await get_configured_chat_provider(),
    output_type=ChatResponse,
    system_prompt=CUSTOMER_SUPPORT_CHAT_PROMPT
    # ❌ NO MCP TOOLS PROVIDED
)
```

### **Proposed Solution (Based on https://ai.pydantic.dev/mcp/client/):**
```python
from pydantic_ai.mcp import MCPServerStreamableHTTP
from mcp.types import ElicitRequestParams, ElicitResult
from mcp.shared.context import RequestContext

class CustomerSupportAgent:
    async def initialize(self) -> None:
        """Initialize with proper MCP tools integration"""
        
        if self.configuration.mcp_enabled:
            # Create MCP server connection with elicitation support
            mcp_server = MCPServerStreamableHTTP(
                url="http://mcp-server:8001/mcp",
                elicitation_callback=self._handle_elicitation
            )
            
            # Create Pydantic AI agent WITH MCP tools
            self.pydantic_agent = Agent(
                model=await self._get_model_provider(),
                output_type=ChatResponse,
                system_prompt=self.configuration.system_prompt,
                toolsets=[mcp_server]  # ✅ ADD MCP TOOLSET
            )
            
            logger.info(f"✅ Customer Support Agent initialized with {len(self.configuration.tools_enabled)} MCP tools")
            
        else:
            # Fallback without tools
            self.pydantic_agent = Agent(
                model=await self._get_model_provider(),
                output_type=ChatResponse,
                system_prompt=self.configuration.system_prompt
            )
            logger.warning("⚠️ Customer Support Agent created without MCP tools (disabled in configuration)")

    async def _handle_elicitation(
        self,
        context: RequestContext,
        params: ElicitRequestParams,
    ) -> ElicitResult:
        """
        Handle elicitation requests from MCP server for missing information.
        
        This allows the AI to ask for clarification when users don't provide
        enough information for tool calls (e.g., missing ticket details).
        """
        
        # Log elicitation request
        logger.info(f"🔍 MCP Elicitation Request: {params.message}")
        
        if not params.requestedSchema:
            # Simple text response needed
            return ElicitResult(
                action='accept',
                content={'response': f"Please provide more information: {params.message}"}
            )
        
        # Structured data needed - build user-friendly request
        properties = params.requestedSchema.get('properties', {})
        missing_fields = []
        
        for field, info in properties.items():
            description = info.get('description', field.replace('_', ' ').title())
            field_type = info.get('type', 'string')
            missing_fields.append(f"• {description} ({field_type})")
        
        # Format elicitation message for user
        elicitation_message = f"""
{params.message}

I need the following information to complete your request:
{chr(10).join(missing_fields)}

Please provide the missing details so I can assist you properly.
        """.strip()
        
        # Return structured elicitation that chat service can present to user
        return ElicitResult(
            action='accept',
            content={
                'elicitation_message': elicitation_message,
                'required_fields': list(properties.keys()),
                'field_descriptions': {k: v.get('description', k) for k, v in properties.items()}
            }
        )
```

## Database Schema Changes

### **New Tables:**

```sql
-- AI Agents table
CREATE TABLE ai_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL DEFAULT 'customer_support',
    name VARCHAR(255) NOT NULL DEFAULT 'Customer Support Agent',
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Configuration (JSON column)
    configuration JSONB NOT NULL DEFAULT '{}',
    
    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(organization_id, agent_type)
);

-- Agent usage statistics
CREATE TABLE agent_usage_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES ai_agents(id) ON DELETE CASCADE,
    
    -- Usage metrics
    total_messages BIGINT NOT NULL DEFAULT 0,
    successful_responses BIGINT NOT NULL DEFAULT 0,
    failed_responses BIGINT NOT NULL DEFAULT 0,
    tools_called BIGINT NOT NULL DEFAULT 0,
    avg_response_time_ms DECIMAL(10,2),
    
    -- Time period
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### **Required ai_config.yaml Updates:**

#### **Current Configuration (needs update):**
```yaml
# Line 121: OLD tool list (only 4 tools)
agents:
  customer_support_agent:
    tools_enabled: ["analyze_file", "create_ticket", "categorize_issue", "search_knowledge_base"]
    
# Line 327-332: OLD prompt template (only 4 tools)
prompt_templates:
  customer_support_default: |
    Available tools via MCP:
    - analyze_file: Process uploaded files for text/audio extraction  
    - create_ticket: Create tickets in the system
    - categorize_issue: Auto-categorize based on content
    - search_knowledge_base: Find existing solutions
```

#### **Required Updates:**
```yaml
# UPDATE: Replace old 4-tool list with all 13 current tools
agents:
  customer_support_agent:
    model_provider: "openai"
    model_name: "primary" 
    temperature: 0.2
    max_tokens: 2000
    timeout: 30
    system_prompt_template: "customer_support_default"
    tools_enabled: [
      # Complete current MCP tool set (13 tools)
      "create_ticket", "create_ticket_with_ai", "get_ticket",
      "update_ticket", "delete_ticket", "update_ticket_status",
      "assign_ticket", "search_tickets", "list_tickets", "get_ticket_stats",
      "list_integrations", "get_active_integrations", "get_system_health"
    ]
    mcp_enabled: true  # ADD: Enable MCP integration
    confidence_threshold: 0.7

# UPDATE: Replace old prompt with current CUSTOMER_SUPPORT_CHAT_PROMPT
prompt_templates:
  customer_support_default: |
    You are an AI Customer Support Assistant for a comprehensive support ticket management system...
    # (Use the current CUSTOMER_SUPPORT_CHAT_PROMPT with all 13 tools)
```

### **Runtime Configuration Schema:**
```json
{
    "system_prompt": "...",  // From ai_config.yaml:prompt_templates:customer_support_default
    "model_provider": "openai",  // From ai_config.yaml:agents:customer_support_agent:model_provider
    "model_name": "primary",     // From ai_config.yaml:agents:customer_support_agent:model_name
    "temperature": 0.2,          // From ai_config.yaml:agents:customer_support_agent:temperature
    "max_tokens": 2000,          // From ai_config.yaml:agents:customer_support_agent:max_tokens
    "timeout": 30,               // From ai_config.yaml:agents:customer_support_agent:timeout
    "tools_enabled": [           // From ai_config.yaml:agents:customer_support_agent:tools_enabled
        "create_ticket", "create_ticket_with_ai", "get_ticket",
        "update_ticket", "delete_ticket", "update_ticket_status",
        "assign_ticket", "search_tickets", "list_tickets", 
        "get_ticket_stats", "list_integrations", 
        "get_active_integrations", "get_system_health"
    ],
    "mcp_enabled": true,         // From ai_config.yaml:agents:customer_support_agent:mcp_enabled
    "confidence_threshold": 0.7, // From ai_config.yaml:agents:customer_support_agent:confidence_threshold
    "auto_escalation_enabled": true,
    "integration_routing_enabled": true,
    "response_style": "professional",
    "default_priority": "medium",
    "default_category": "general"
}
```

## Service Layer Design

### **AIAgentService**
```python
class AIAgentService:
    """Service for managing organization-scoped AI agents"""
    
    async def get_organization_agent(self, org_id: UUID) -> Optional[CustomerSupportAgent]
    async def create_organization_agent(self, org_id: UUID, config: AIAgentConfiguration) -> CustomerSupportAgent
    async def update_agent_configuration(self, agent_id: UUID, updates: AIAgentConfigurationUpdate) -> CustomerSupportAgent
    async def activate_agent(self, agent_id: UUID) -> bool
    async def deactivate_agent(self, agent_id: UUID) -> bool
    async def delete_agent(self, agent_id: UUID) -> bool
    async def get_agent_stats(self, agent_id: UUID) -> AgentUsageStats
```

### **Enhanced CustomerSupportAgent**
```python
class CustomerSupportAgent:
    """Organization-scoped customer support agent with MCP integration"""
    
    def __init__(self, organization_id: UUID, configuration: AIAgentConfiguration)
    async def initialize(self) -> None  # Initialize Pydantic AI agent with MCP tools
    async def process_message(self, message: str, context: CustomerSupportContext) -> ChatResponse
    async def update_configuration(self, updates: AIAgentConfigurationUpdate) -> None
    async def get_available_tools(self) -> List[str]
    async def test_tool(self, tool_name: str) -> bool
    async def get_health_status(self) -> AgentHealthStatus
    def is_active(self) -> bool
    def get_configuration(self) -> AIAgentConfiguration
```

## Automatic Agent Provisioning Flow

### **Organization Creation Hook:**
```python
async def create_organization_agent_hook(organization: Organization) -> None:
    """Automatically create customer support agent when organization is created"""
    
    logger.info(f"🤖 Auto-provisioning Customer Support Agent for new organization {organization.id}")
    
    try:
        # Load defaults from ai_config.yaml
        default_config = await load_default_agent_configuration()
        
        # Create agent automatically
        agent = await ai_agent_service.create_organization_agent(
            organization_id=organization.id,
            configuration=default_config,
            auto_created=True,
            name=f"{organization.name} - Customer Support Agent"
        )
        
        logger.info(f"✅ Auto-created Customer Support Agent {agent.id} for organization {organization.name}")
        
    except Exception as e:
        logger.error(f"❌ Failed to auto-create agent for organization {organization.id}: {e}")
        # Non-blocking - agent can be created later during first chat

# Hook integration in organization service:
# await create_organization_agent_hook(new_organization)
```

### **Agent Availability Guarantee:**
```python
async def ensure_agent_available(organization_id: UUID) -> CustomerSupportAgent:
    """Guarantee that organization has an active agent (create if missing)"""
    
    agent = await ai_agent_service.get_organization_agent(organization_id)
    
    if not agent:
        # Agent missing - create with defaults from ai_config.yaml
        logger.info(f"🔄 Creating missing Customer Support Agent for organization {organization_id}")
        default_config = await load_default_agent_configuration()
        
        agent = await ai_agent_service.create_organization_agent(
            organization_id=organization_id,
            configuration=default_config,
            auto_created=True
        )
        
    elif not agent.is_active():
        # Agent exists but inactive - reactivate
        logger.info(f"🔄 Reactivating inactive Customer Support Agent for organization {organization_id}")
        await ai_agent_service.activate_agent(agent.id)
        
    return agent

# Called before every chat message processing
```

## Chat Service Integration

### **Updated ai_chat_service.py**
```python
async def get_organization_agent(organization_id: UUID) -> CustomerSupportAgent:
    """Get organization's customer support agent (auto-creates if missing)"""
    
    # Use availability guarantee - will auto-create from ai_config.yaml if needed
    return await ensure_agent_available(organization_id)

async def process_chat_message(
    conversation_id: UUID,
    message: str, 
    user: User,
    files: List[str] = []
) -> ChatResponse:
    """Process chat message using organization's agent"""
    
    # Get organization's agent
    agent = await get_organization_agent(user.organization_id)
    
    # Build context
    context = CustomerSupportContext(
        user_input=message,
        uploaded_files=files,
        conversation_history=await get_conversation_history(conversation_id),
        user_metadata={
            "user_id": str(user.id),
            "organization_id": str(user.organization_id)
        }
    )
    
    # Process with MCP tools enabled
    response = await agent.process_message(message, context)
    
    # Log tool usage
    if response.tools_used:
        logger.info(f"🔧 MCP Tools used: {response.tools_used}")
        
    return response
```

## Benefits of Refactored Architecture

### **For Organizations:**
- **Customizable Agents:** Each organization can configure their own agent
- **Tool Selection:** Enable/disable specific MCP tools based on needs
- **Brand Customization:** Custom prompts, response styles, priorities
- **Analytics:** Organization-specific agent performance metrics

### **For Developers:**
- **Clean Architecture:** Separation of concerns with service layers
- **Testability:** Isolated components for better testing
- **Maintainability:** Modular design for easier updates
- **Extensibility:** Easy to add new agent types or capabilities

### **For Users:**
- **Consistent Experience:** Same agent across all conversations in organization
- **Tool Access:** Actual MCP tool calling (not just prompts)
- **Better Responses:** AI can perform actions, not just provide guidance
- **Personalization:** Organization-specific agent behavior

### **For System Integration:**
- **MCP Tools Working:** Agents will actually call MCP tools
- **Integration Routing:** Proper external system integration
- **Monitoring:** Agent health and performance tracking
- **Scalability:** Per-organization configuration without conflicts

## Migration Strategy

### **Phase 1: Schema & Models**
1. Create `AIAgent` and related database models
2. Create migration scripts for new tables
3. Add organization relationship constraints

### **Phase 2: Service Layer**
1. Implement `AIAgentService` with CRUD operations
2. Create agent factory for organization-scoped instances
3. Add configuration validation and defaults

### **Phase 3: Agent Implementation**  
1. Refactor `CustomerSupportAgent` to use persistent configuration
2. Implement MCP tool integration with Pydantic AI
3. Add agent lifecycle management

### **Phase 4: API Integration**
1. Create agent management API endpoints
2. Update chat service to use organization agents
3. Add agent configuration UI endpoints

### **Phase 5: Testing & Deployment**
1. Comprehensive testing of agent functionality
2. MCP tool calling verification
3. Performance testing and optimization

## Success Criteria

### **Functional Requirements:**
- ✅ AI agents actually call MCP tools (no more `Tools used: []`)
- ✅ Organization-scoped agent configuration
- ✅ Agent CRUD operations via API
- ✅ MCP integration working with all 13 tools

### **Performance Requirements:**
- ✅ Agent initialization < 2 seconds
- ✅ Message processing < 5 seconds
- ✅ Configuration updates < 1 second
- ✅ Tool calls complete successfully

### **Quality Requirements:**
- ✅ Comprehensive test coverage
- ✅ Proper error handling and fallbacks
- ✅ Monitoring and logging
- ✅ Documentation and examples

## Expected Docker Log Changes

### **Before Refactoring:**
```
MCP client integration disabled for basic AI functionality
Tools used: []
Customer Support chat agent created (MCP server available but not integrated)
```

### **After Refactoring:**
```
✅ Organization agent initialized with 13 MCP tools
🔧 MCP Tools used: ['get_active_integrations'] 
📋 Tool call result: Found 3 active integrations
✅ Customer support response generated with tool integration
```

## Key Architecture Changes

### **1. Automatic Agent Provisioning:**
- ✅ **Zero-Setup Experience:** Every organization automatically gets a Customer Support Agent
- ✅ **Default Configuration:** Agents start with optimized settings from `ai_config.yaml`
- ✅ **Immediate Availability:** No manual agent creation required
- ✅ **Fallback Protection:** Missing agents are auto-created during first chat

### **2. Configuration File Integration:**
- ✅ **Centralized Defaults:** All agent defaults come from `ai_config.yaml`
- ✅ **Prompt Templates:** System prompts loaded from config file templates
- ✅ **Tool Configuration:** MCP tool enablement configurable per agent type
- ✅ **Environment Consistency:** Same defaults across all environments

### **3. Enhanced Agent Management:**
- ✅ **Organization Scoping:** One agent per organization (singleton pattern)
- ✅ **Configuration Flexibility:** Organizations can override defaults
- ✅ **Reset Capability:** Return to ai_config.yaml defaults anytime
- ✅ **Status Management:** Activate, deactivate, recreate agents as needed

### **4. MCP Tool Integration:**
- ✅ **Tools Enabled by Default:** All 13 MCP tools available from start
- ✅ **Configurable Tool Selection:** Organizations can enable/disable specific tools
- ✅ **Actual Tool Calling:** Agents will call MCP tools instead of just providing guidance
- ✅ **Integration Awareness:** AI can discover and use active integrations

## Configuration Migration Required

### **Update ai_config.yaml:**
```yaml
# BEFORE (current - only 4 tools):
agents:
  customer_support_agent:
    tools_enabled: ["analyze_file", "create_ticket", "categorize_issue", "search_knowledge_base"]

# AFTER (updated - all 13 tools):
agents:
  customer_support_agent:
    model_provider: "openai"
    model_name: "primary"
    temperature: 0.2
    max_tokens: 2000 
    timeout: 30
    system_prompt_template: "customer_support_default"
    tools_enabled: [
      "create_ticket", "create_ticket_with_ai", "get_ticket",
      "update_ticket", "delete_ticket", "update_ticket_status",
      "assign_ticket", "search_tickets", "list_tickets", "get_ticket_stats",
      "list_integrations", "get_active_integrations", "get_system_health"
    ]
    mcp_enabled: true  # NEW: Enable MCP integration
    confidence_threshold: 0.7

# BEFORE (current - old prompt):
prompt_templates:
  customer_support_default: |
    Available tools via MCP:
    - analyze_file: Process uploaded files...
    - create_ticket: Create tickets...
    # (only 4 tools listed)

# AFTER (updated - comprehensive prompt):
prompt_templates:
  customer_support_default: |
    You are an AI Customer Support Assistant for a comprehensive support ticket management system...
    **Available MCP Tools (13 tools organized by category):**
    # (Current CUSTOMER_SUPPORT_CHAT_PROMPT with all 13 tools)
```

## Conclusion

This refactoring will transform the AI service from a stateless, tool-disabled system to a robust, organization-scoped agent management platform with full MCP integration and automatic provisioning. Key improvements:

### **For Organizations:**
- **Zero Setup:** Agents are automatically created with optimal defaults
- **Immediate Availability:** Customer support AI ready from day one
- **Configurable:** Can customize agent behavior while maintaining system defaults
- **Reliable:** Automatic recreation and fallback protection

### **For Configuration Management:**
- **Centralized Defaults:** All defaults managed in `ai_config.yaml`
- **Version Control:** Configuration changes tracked and deployable
- **Environment Consistency:** Same agent behavior across dev/staging/production
- **Easy Updates:** System-wide agent improvements via config file updates

### **For Tool Integration:**
- **Actual Tool Calling:** AI will call MCP tools instead of providing guidance
- **Complete Tool Set:** All 13 tools available and properly integrated
- **Smart Tool Selection:** AI knows which tools to use for each query type
- **Integration Discovery:** AI can find and use active integrations
- **Elicitation Support:** AI can request missing information for proper tool calls

## MCP Elicitation Support

### **Interactive Tool Calling:**
Based on [MCP Elicitation Documentation](https://ai.pydantic.dev/mcp/client/), the refactored agents will support elicitation to request missing information from users when they don't provide enough context for tool calls.

### **Example Elicitation Scenarios:**

#### **Scenario 1: Incomplete Ticket Creation**
**User Query:** `"create a ticket"`
**AI Response:** Instead of guessing or failing, AI uses elicitation:

```json
{
    "message": "I need more information to create a ticket for you.",
    "required_fields": ["title", "description"],
    "field_descriptions": {
        "title": "Brief title for the ticket",
        "description": "Detailed description of the issue"
    }
}
```

#### **Scenario 2: Ticket Search Without Criteria** 
**User Query:** `"show me tickets"`
**AI Response:** AI asks for search criteria:

```json
{
    "message": "I can search for tickets, but need to know what you're looking for.",
    "required_fields": ["search_criteria"],
    "field_descriptions": {
        "status": "Ticket status (open, in_progress, resolved, closed)",
        "priority": "Priority level (low, medium, high, critical)",
        "category": "Issue category (technical, billing, etc.)"
    }
}
```

#### **Scenario 3: Integration Selection**
**User Query:** `"create a ticket in an external system"`
**AI Response:** AI asks which integration to use:

```json
{
    "message": "I can create a ticket in an external system. Which integration would you like to use?",
    "required_fields": ["integration"],
    "available_options": ["jira", "servicenow", "salesforce", "zendesk"]
}
```

### **Elicitation Implementation:**
```python
# In CustomerSupportAgent class
async def process_message_with_elicitation(
    self, 
    message: str, 
    context: CustomerSupportContext
) -> Union[ChatResponse, ElicitationRequest]:
    """Process message with elicitation support"""
    
    try:
        # Use Pydantic AI agent with MCP tools
        async with self.pydantic_agent:
            result = await self.pydantic_agent.run(
                user_input=message,
                context=context
            )
            
        # Log successful tool usage
        if hasattr(result, 'tools_used') and result.tools_used:
            logger.info(f"🔧 MCP Tools called: {result.tools_used}")
            
        return result
        
    except ElicitationRequired as e:
        # MCP server requested more information
        logger.info(f"🔍 Elicitation required: {e.message}")
        
        return ElicitationRequest(
            message=e.message,
            required_fields=e.required_fields,
            field_descriptions=e.field_descriptions
        )
```

### **Chat Service Elicitation Handling:**
```python
async def handle_chat_message(
    conversation_id: UUID,
    message: str,
    user: User
) -> Union[ChatResponse, ElicitationPrompt]:
    """Handle chat with elicitation support"""
    
    # Get organization agent
    agent = await ensure_agent_available(user.organization_id)
    
    # Process message
    result = await agent.process_message_with_elicitation(message, context)
    
    if isinstance(result, ElicitationRequest):
        # AI needs more information - prompt user
        return ElicitationPrompt(
            message="I need some additional information to help you:",
            fields=result.required_fields,
            descriptions=result.field_descriptions,
            conversation_id=conversation_id
        )
    else:
        # Normal response with potential tool calls
        return result
```

### **Benefits of Elicitation:**
- **Better User Experience:** AI asks clarifying questions instead of guessing
- **Accurate Tool Calls:** Ensures proper parameters for MCP tool calls
- **Interactive Workflows:** Multi-step processes with user guidance
- **Error Reduction:** Fewer failed tool calls due to missing parameters

Users will finally be able to ask **"What integrations are active?"** and get actual `get_active_integrations` tool results instead of static responses. The architecture supports automatic agent provisioning, comprehensive configuration management, and full MCP tool integration while solving the current issue where tools are available but never called.