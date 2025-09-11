# System Title Agent Refactor - Product Requirements Document (PRD)

## Executive Summary

This PRD outlines the refactoring of the System Title Agent to be truly organization-independent and automatically created on application startup. The current implementation ties the system title agent to the TickAido organization, which is conceptually incorrect since title generation is a universal system service that should serve all organizations equally.

## Problem Statement

### Current Issues
1. **Organization Dependency**: The system title agent is currently tied to the TickAido organization (`organization_id=tickaido_org.id`), making it organization-specific rather than truly system-wide.
2. **Initialization Dependency**: Agent creation requires the TickAido organization to exist, creating unnecessary coupling.
3. **Conceptual Misalignment**: Title generation is a system utility that should be available to all organizations without favoritism.
4. **Startup Complexity**: Current startup logic has multiple failure points and dependencies.

### Current Implementation Analysis
- **Location**: `app/services/agent_service.py:630-717` (`create_system_title_agent`)
- **Current Behavior**: Creates system title agent assigned to TickAido organization
- **Database Schema**: Uses `organization_id` foreign key constraint that prevents true system agents
- **Startup Process**: Called in `app/main.py:240-254` during application initialization

## Proposed Solution

### 1. True System Agent Architecture
- **System agents** have `organization_id = NULL` and serve all organizations universally
- **Database schema** allows NULL values for `organization_id` in agents table
- **Access control** treats NULL organization_id as system-wide permission

### 2. Startup-Based Agent Creation
- **Automatic creation** of system title agent during application startup
- **Idempotent operation** that safely handles existing agents
- **No external dependencies** - works without TickAido organization
- **Fail-safe initialization** with proper error handling and fallbacks

### 3. Configuration Management
- **Default configuration** loaded from `app/config/ai_config.yaml`
- **System-optimized settings** for efficiency and cost control
- **Immutable agent type** (`title_generation`) for system identification

## Technical Requirements

### Database Schema Changes
```sql
-- Allow NULL organization_id for system agents
ALTER TABLE agents ALTER COLUMN organization_id DROP NOT NULL;

-- Update existing system title agent to be organization-independent
UPDATE agents 
SET organization_id = NULL 
WHERE agent_type = 'title_generation' 
  AND name = 'System Title Generator';
```

### Agent Service Modifications

#### 1. Update `get_system_title_agent()` method
```python
# Query modification to find system agents
stmt = select(Agent).where(
    Agent.agent_type == "title_generation",
    Agent.is_active.is_(True),
    Agent.organization_id.is_(None),  # System agent has NULL organization
    Agent.is_deleted == False
)
```

#### 2. Update `create_system_title_agent()` method
```python
# Create true system agent
agent = Agent(
    organization_id=None,  # System agent - no organization
    agent_type="title_generation",
    name="System Title Generator",
    is_active=True,
    status="active"
)
```

#### 3. Add startup initialization method
```python
async def initialize_system_agents(self, db: Optional[AsyncSession] = None) -> bool:
    """
    Initialize all required system agents on application startup.
    
    Returns:
        bool: True if all system agents are ready
    """
```

### Startup Process Enhancement
- **Early initialization** in `startup_event()` before other services
- **Comprehensive logging** for troubleshooting
- **Graceful degradation** if agent creation fails
- **Health check endpoint** to verify system agent status

### Configuration Specifications

#### System Title Agent Configuration
```yaml
# app/config/ai_config.yaml - System Title Agent section
system_title_agent:
  name: "System Title Generator"
  agent_type: "title_generation"
  role: "Title Generation Utility"
  prompt: |
    You are an expert at creating concise, descriptive titles for customer support conversations.
    
    Analyze the conversation and generate a clear, specific title that captures the essence of the discussion.
    
    TITLE GENERATION RULES:
    1. Maximum 8 words, ideally 4-6 words
    2. Use specific, descriptive terms
    3. Avoid generic words: "Help", "Support", "Question", "Issue"
    4. Include technical terms when relevant
    5. Capture the primary topic/problem
    6. Use title case formatting
    
    Focus on the main issue or request being discussed.
  communication_style: "professional"
  response_length: "brief"
  use_streaming: false
  timeout_seconds: 15
  tools: []
  memory_retention: 1
  max_context_size: 10000
  use_memory_context: false
  max_iterations: 1
```

## Implementation Plan

### Phase 1: Database Schema Update
1. **Create Alembic migration** to allow NULL organization_id
2. **Update existing system title agents** to have NULL organization_id
3. **Test migration** in development and staging environments

### Phase 2: Agent Service Refactor
1. **Update query methods** to handle NULL organization_id
2. **Modify agent creation** to create true system agents
3. **Add startup initialization** method for system agents
4. **Update error handling** and logging

### Phase 3: Startup Process Integration
1. **Integrate system agent initialization** in startup_event()
2. **Add health checks** for system agent status
3. **Implement monitoring** and alerting for system agent failures
4. **Update documentation** and API specifications

### Phase 4: Testing and Validation
1. **Unit tests** for system agent service methods
2. **Integration tests** for startup process
3. **End-to-end tests** for title generation functionality
4. **Database migration tests** for schema changes

## Testing Strategy

### Database Testing
```bash
# Test migration
poetry run alembic upgrade head

# Verify schema changes
poetry run python -c "
from app.models.ai_agent import Agent
from app.database import get_async_db_session
# Test NULL organization_id creation
"
```

### Service Testing
```bash
# Test system agent creation
poetry run pytest tests/unit/services/test_agent_service.py::test_create_system_title_agent -v

# Test startup process
poetry run pytest tests/integration/test_startup_process.py -v

# Test title generation end-to-end
poetry run pytest tests/e2e/test_title_generation_flow.py -v
```

### Complete Test Suite
```bash
# Run all tests after refactor
poetry run pytest --tb=short -q

# Test specific scenarios
poetry run pytest -k "title_generation or system_agent" -v
```

## Success Criteria

### Functional Requirements
- ✅ System title agent created automatically on startup
- ✅ System title agent has `organization_id = NULL`
- ✅ Title generation works for all organizations
- ✅ No dependency on TickAido organization for system agent
- ✅ Startup process is idempotent and fail-safe

### Technical Requirements
- ✅ Database schema allows NULL organization_id for agents
- ✅ All existing tests pass after refactor
- ✅ New tests cover system agent functionality
- ✅ API endpoints work correctly with system agents
- ✅ Health checks verify system agent status

### Performance Requirements
- ✅ Startup time doesn't increase significantly
- ✅ Title generation response time remains under 5 seconds
- ✅ System agent initialization completes within 10 seconds
- ✅ Database queries are optimized for NULL organization_id

## Risk Assessment

### High Risk
- **Database migration failure** - Mitigated by thorough testing and rollback procedures
- **Startup process failure** - Mitigated by graceful degradation and comprehensive logging

### Medium Risk
- **Existing code dependencies** - Mitigated by comprehensive testing of all system integrations
- **Performance impact** - Mitigated by benchmarking and optimization

### Low Risk
- **Configuration changes** - Well-defined and testable
- **API compatibility** - No breaking changes expected

## Rollback Plan

### Emergency Rollback
1. **Database rollback**: `poetry run alembic downgrade -1`
2. **Code rollback**: Revert to previous commit
3. **Service restart**: `docker compose restart app`

### Graceful Rollback
1. **Update system agents** to use TickAido organization again
2. **Run migration** to restore NOT NULL constraint if needed
3. **Update startup process** to previous implementation
4. **Verify all functionality** returns to baseline

## Monitoring and Alerting

### Key Metrics
- **System agent availability**: Agent exists and is active
- **Title generation success rate**: >95% success rate
- **Response time**: <5 seconds average
- **Startup time**: Total application startup duration

### Health Checks
```python
# Add to health endpoint
{
    "system_title_agent": {
        "exists": true,
        "active": true,
        "organization_id": null,
        "last_used": "2025-01-15T10:30:00Z"
    }
}
```

## Conclusion

This refactor transforms the system title agent from an organization-specific service to a true system utility. The changes improve architectural consistency, reduce startup dependencies, and provide a foundation for other system-wide AI agents in the future.

The implementation prioritizes safety with comprehensive testing, graceful error handling, and clear rollback procedures. Upon completion, the system will have a more robust and maintainable title generation service that serves all organizations equally.