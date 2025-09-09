name: "Agent Max Iterations Refactor - Rename tool_call_limit to max_iterations and Use Agent-Level Limits"
description: |

## Purpose
Refactor the agent system to use `max_iterations` field from the AI agent model as the primary iteration limit, rename the global `tool_call_limit` configuration to `max_iterations` for consistency, and update all references throughout the codebase and test suite.

## Core Principles
1. **Agent-Level Control**: Each agent should have its own iteration limit via `max_iterations`
2. **Default Fallback**: Use `max_iterations` config as default when agent `max_iterations` is not specified during creation
3. **Hard Limits**: Enforce maximum of 10 iterations and minimum of 1 for safety
4. **MCP Integration**: Update MCP server to respect agent-specific limits

---

## Goal
Replace the current system where all agents use the global `tool_call_limit` configuration with a system where each agent uses its own `max_iterations` field, while also renaming the config setting to `max_iterations` for consistency and updating all references throughout the codebase.

## Why
- **Flexibility**: Different agent types may need different iteration limits (e.g., simple categorization vs complex customer support)
- **Agent Autonomy**: Each agent instance can have customized behavior
- **Better Resource Management**: Fine-grained control over computational resources per agent
- **Consistency**: Unified naming convention - `max_iterations` everywhere instead of mixed `tool_call_limit`/`max_iterations`
- **Clarity**: The name `max_iterations` better describes what the setting controls

## What
Modify the agent system to:
1. Rename `tool_call_limit` to `max_iterations` in config file and all references
2. Use `agent.max_iterations` as the primary iteration limit in all AI service calls
3. Set `max_iterations` to `config.max_iterations` as default during agent creation if not specified
4. Enforce bounds: 1 ≤ max_iterations ≤ 10
5. Update MCP server to use agent-specific limits instead of global config
6. Update all services, methods, and variable names that reference `tool_call_limit`

### Success Criteria
- [ ] Config file renamed `tool_call_limit` to `max_iterations`
- [ ] All code references renamed from `tool_call_limit` to `max_iterations`
- [ ] All agent creation sets `max_iterations` to config `max_iterations` if not provided
- [ ] All AI service calls use `agent.max_iterations` instead of global config
- [ ] Max iterations are bounded between 1 and 10
- [ ] MCP server uses agent-specific limits
- [ ] Method names updated (e.g., `get_tool_call_limit` → `get_max_iterations`)
- [ ] All tests pass with new naming and iteration logic
- [ ] No `tool_call_limit` references remain in the codebase

## All Needed Context

### Documentation & References
```yaml
- file: app/models/ai_agent.py
  why: Contains max_iterations field definition and constraints
  
- file: app/schemas/agent.py
  why: Pydantic schemas with max_iterations validation rules
  
- file: app/services/ai_config_service.py
  why: Current tool_call_limit configuration and getter method
  
- file: app/config/ai_config.yaml
  why: Global tool_call_limit setting (currently 5)
  
- file: app/services/dynamic_agent_factory.py
  why: Current usage of tool_call_limit for UsageLimits
  
- file: app/services/ai_chat_service_old.py
  why: Multiple instances of tool_call_limit usage with UsageLimits
```

### Current Codebase Structure
```bash
app/
├── config/
│   ├── ai_config.yaml          # Global tool_call_limit: 5
│   └── settings.py
├── models/
│   └── ai_agent.py            # max_iterations field (default=5, 1-20 range)
├── schemas/
│   └── agent.py               # max_iterations validation (1-20 range)
├── services/
│   ├── ai_config_service.py   # get_tool_call_limit() method
│   ├── dynamic_agent_factory.py  # Uses tool_call_limit
│   ├── ai_chat_service_old.py    # Multiple tool_call_limit usages
│   └── agent_service.py       # Agent CRUD operations
└── mcp_server/
    └── start_mcp_server.py    # MCP server entry point
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: Pydantic AI UsageLimits uses request_limit parameter
from pydantic_ai.usage import UsageLimits
usage_limits = UsageLimits(request_limit=iterations)  # NOT max_iterations!

# CRITICAL: Current schema allows 1-20 range but we want max 10
# app/schemas/agent.py:44 and app/schemas/agent.py:79 have le=20
max_iterations: int = Field(default=5, ge=1, le=20)  # Need to change le=10

# CRITICAL: Database model has no upper bound constraint
# app/models/ai_agent.py:162-167 only has default=5, no max constraint

# GOTCHA: MCP server currently doesn't use any iteration limits
# Need to pass agent context or limits to MCP server somehow
```

## Implementation Blueprint

### Data Models and Structure
Update existing models to enforce new bounds and usage patterns:

```python
# Update database model constraint (requires migration)
class AIAgent(Base):
    max_iterations = Column(
        Integer,
        nullable=False,
        default=5,
        comment="Maximum number of tool call iterations (1-10)"
    )
    # Add database constraint for 1-10 range

# Update Pydantic schemas for stricter validation
class AgentCreate(BaseModel):
    max_iterations: int = Field(default=5, ge=1, le=10)

class AgentUpdate(BaseModel):
    max_iterations: Optional[int] = Field(None, ge=1, le=10)
```

### List of Tasks to Complete

```yaml
Task 1: Rename config setting from tool_call_limit to max_iterations
MODIFY app/config/ai_config.yaml:
  - FIND: tool_call_limit: 5  # Maximum number of tool calls per AI request
  - REPLACE: max_iterations: 5  # Maximum number of AI agent iterations per request

Task 2: Update ai_config_service.py method names and references
MODIFY app/services/ai_config_service.py:
  - FIND: def get_tool_call_limit(self) -> int:
  - REPLACE: def get_max_iterations(self) -> int:
  - FIND: tool_call_limit = ai_strategy.get("tool_call_limit", 10)
  - REPLACE: max_iterations = ai_strategy.get("max_iterations", 10)
  - FIND: logger.debug(f"Tool call limit from config: {tool_call_limit}")
  - REPLACE: logger.debug(f"Max iterations from config: {max_iterations}")
  - FIND: return tool_call_limit
  - REPLACE: return max_iterations

Task 3: Update Pydantic schemas for max_iterations bounds
MODIFY app/schemas/agent.py:
  - FIND: max_iterations: int = Field(default=5, ge=1, le=20)
  - REPLACE: max_iterations: int = Field(default=5, ge=1, le=10)
  - FIND: max_iterations: Optional[int] = Field(None, ge=1, le=20)
  - REPLACE: max_iterations: Optional[int] = Field(None, ge=1, le=10)

Task 4: Create database migration for max_iterations constraint
CREATE: alembic/versions/xxx_add_max_iterations_constraint.py
  - ADD check constraint: max_iterations >= 1 AND max_iterations <= 10
  - PRESERVE existing data (all current values should be valid)

Task 5: Update agent creation to use config max_iterations as default
MODIFY app/services/agent_service.py:
  - FIND: Agent creation logic
  - INJECT: Set max_iterations = config.get_max_iterations() if not provided
  - ENSURE: Bounds checking (1-10) is applied

Task 6: Update dynamic_agent_factory.py to use agent.max_iterations
MODIFY app/services/dynamic_agent_factory.py:
  - FIND: tool_call_limit = ai_config_service.get_tool_call_limit()
  - REPLACE: # Use agent.max_iterations instead of global config
  - FIND: usage_limits = UsageLimits(request_limit=tool_call_limit)
  - REPLACE: usage_limits = UsageLimits(request_limit=agent.max_iterations)

Task 7: Update ai_chat_service_old.py - all 8 tool_call_limit usages
MODIFY app/services/ai_chat_service_old.py:
  - FIND: tool_call_limit = ai_config_service.get_tool_call_limit() (Line 882)
  - REPLACE: # Use agent.max_iterations instead of global config
  - FIND: usage_limits = UsageLimits(request_limit=tool_call_limit) (Line 883)
  - REPLACE: usage_limits = UsageLimits(request_limit=agent.max_iterations)
  - REPEAT: For all 8 instances at lines 882/883, 924/925, 1071/1072, 1192/1194, 1382/1384, 1588/1590
  - UPDATE: All log messages from "tool call limit" to "max iterations"

Task 8: Update MCP server integration
MODIFY mcp_server integration:
  - INVESTIGATE: How to pass agent context to MCP server
  - IMPLEMENT: Agent-specific iteration limits in MCP calls
  - FALLBACK: Use default limit if agent context unavailable

Task 9: Add validation helper function
CREATE app/utils/agent_validation.py:
  - FUNCTION: validate_max_iterations(value: int) -> int
  - ENSURE: 1 <= value <= 10, raise ValueError if invalid
  - USE: In agent creation and update logic

Task 10: Update all remaining variable names and references
GLOBAL SEARCH AND REPLACE:
  - FIND: All instances of "tool_call_limit" in variable names
  - REPLACE: With "max_iterations" 
  - FIND: All instances of "get_tool_call_limit()" method calls
  - REPLACE: With "get_max_iterations()"
  - VERIFY: No "tool_call_limit" strings remain in codebase

Task 11: Update tests and documentation
MODIFY test files (if any exist with tool_call_limit references):
  - UPDATE: Any test mocks or fixtures using tool_call_limit
  - UPDATE: Test method names containing tool_call_limit
  - ADD: Tests for config max_iterations validation
  - ADD: Tests for agent creation using config default
  - ADD: Bounds checking tests (values 0, 1, 10, 11)
  - ADD: Integration tests with MCP server limits
```

### Per Task Pseudocode

```python
# Task 5: Agent creation with defaults
async def create_agent(agent_data: AgentCreate, user_id: int):
    # Get default from config if not provided
    if not hasattr(agent_data, 'max_iterations') or agent_data.max_iterations is None:
        ai_config = AIConfigService()
        default_iterations = ai_config.get_max_iterations()  # Renamed method
        # Ensure default respects bounds
        agent_data.max_iterations = min(max(default_iterations, 1), 10)
    
    # Validate bounds (Pydantic should handle this too)
    if not 1 <= agent_data.max_iterations <= 10:
        raise ValueError("max_iterations must be between 1 and 10")
    
    # Create agent with validated max_iterations
    agent = AIAgent(**agent_data.model_dump(), user_id=user_id)
    return await agent_repository.create(agent)

# Task 6: Dynamic agent factory update  
async def create_pydantic_agent(agent: AIAgent):
    # Use agent's max_iterations instead of global config
    usage_limits = UsageLimits(request_limit=agent.max_iterations)
    
    # Rest of agent creation logic...
    return Agent(
        model=model_config,
        usage_limits=usage_limits,
        # ...other config
    )

# Task 8: MCP server integration (conceptual)
class MCPAgentContext:
    def __init__(self, agent_id: int, max_iterations: int):
        self.agent_id = agent_id
        self.max_iterations = max_iterations
    
    def get_iteration_limit(self) -> int:
        return min(self.max_iterations, 10)  # Hard limit enforcement

# Task 9: Validation helper
def validate_max_iterations(value: int) -> int:
    """Validate and clamp max_iterations to valid range."""
    if not isinstance(value, int):
        raise ValueError("max_iterations must be an integer")
    if value < 1:
        raise ValueError("max_iterations must be at least 1")
    if value > 10:
        raise ValueError("max_iterations cannot exceed 10")
    return value
```

### Integration Points
```yaml
DATABASE:
  - migration: "Add CHECK constraint for max_iterations (1-10)"
  - update: "Ensure all existing agents have valid max_iterations"
  
CONFIG:
  - rename: config/ai_config.yaml tool_call_limit to max_iterations
  - pattern: "Use as fallback when agent max_iterations not specified"
  
MCP_SERVER:
  - investigate: "How to pass agent context to MCP server calls"
  - implement: "Agent-aware iteration limiting in MCP tools"
  
SERVICES:
  - update: "All services using tool_call_limit to use agent.max_iterations"
  - ensure: "Agent context availability in all AI service methods"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check app/services/ app/schemas/ app/models/ --fix
mypy app/services/ app/schemas/ app/models/

# Expected: No errors. Pay attention to type hints for max_iterations usage.
```

### Level 2: Unit Tests
```python
# Test agent creation with defaults
def test_agent_creation_uses_config_default():
    """Agent created without max_iterations uses tool_call_limit default"""
    agent_data = AgentCreate(name="Test", agent_type="customer_support")
    # max_iterations should default to config.tool_call_limit (currently 5)
    agent = create_agent(agent_data, user_id=1)
    assert agent.max_iterations == 5  # or whatever config.tool_call_limit is

def test_max_iterations_bounds_validation():
    """Max iterations must be between 1 and 10"""
    # Test lower bound
    with pytest.raises(ValueError, match="must be at least 1"):
        validate_max_iterations(0)
    
    # Test upper bound  
    with pytest.raises(ValueError, match="cannot exceed 10"):
        validate_max_iterations(11)
    
    # Test valid values
    assert validate_max_iterations(1) == 1
    assert validate_max_iterations(10) == 10

def test_ai_service_uses_agent_max_iterations():
    """AI services use agent.max_iterations instead of global config"""
    agent = Mock(max_iterations=3)
    with patch('app.services.dynamic_agent_factory.UsageLimits') as mock_limits:
        create_pydantic_agent(agent)
        mock_limits.assert_called_with(request_limit=3)
```

```bash
# Run and iterate until passing:
poetry run pytest tests/unit/services/ tests/unit/schemas/ -v
# Focus on agent creation, validation, and AI service tests
```

### Level 3: Integration Test
```bash
# Test agent creation API
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Test Agent",
    "agent_type": "customer_support",
    "role": "Test role"
  }'

# Expected: Agent created with max_iterations = 5 (config default)
# Verify: Check database that max_iterations was set correctly

# Test bounds validation
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Invalid Agent",
    "agent_type": "customer_support", 
    "max_iterations": 15
  }'

# Expected: 422 validation error about max_iterations > 10
```

## Final Validation Checklist
- [ ] All tests pass: `poetry run pytest`
- [ ] No linting errors: `ruff check app/`
- [ ] No type errors: `mypy app/`
- [ ] Database migration runs successfully
- [ ] Config file updated: tool_call_limit → max_iterations
- [ ] Method renamed: get_tool_call_limit() → get_max_iterations()
- [ ] All variable names updated from tool_call_limit to max_iterations
- [ ] Agent creation uses config default when max_iterations not specified
- [ ] All AI services use agent.max_iterations instead of global config
- [ ] Max iterations are properly bounded (1-10)
- [ ] MCP server integration respects agent limits
- [ ] No "tool_call_limit" references remain in codebase
- [ ] API validation rejects invalid max_iterations values

---

## Anti-Patterns to Avoid
- ❌ Don't leave any tool_call_limit references in the codebase
- ❌ Don't allow max_iterations > 10 - this is a hard safety limit
- ❌ Don't break existing agent creation flow - maintain backwards compatibility
- ❌ Don't ignore bounds checking - enforce limits at all entry points
- ❌ Don't forget to update method names and variable names
- ❌ Don't hardcode iteration limits - always use agent.max_iterations
- ❌ Don't forget to update log messages and comments referencing tool_call_limit