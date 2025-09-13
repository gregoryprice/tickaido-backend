# Agent Avatar Management Refactor PRP

**Document Type:** Product Requirements & Planning  
**Created:** 2025-09-12  
**Status:** Proposed  

## Executive Summary

This PRP outlines the refactoring of agent avatar management endpoints to separate avatar handling from agent creation/update operations, following the established pattern used for user avatar management. The refactor will create dedicated avatar endpoints and remove `avatar_url` from agent CRUD operations.

## Current State Analysis

### Existing Agent Avatar Implementation
- **Current endpoint:** `/api/v1/agents/{agent_id}/avatar` (already implemented in `agent_avatars.py`)
- **Agent creation:** Includes `avatar_url` field in POST request body
- **Agent updates:** Includes `avatar_url` field in PUT request body
- **Mixed concerns:** Avatar management mixed with agent configuration

### Current User Avatar Pattern (Reference Implementation)
- **Upload:** `POST /api/v1/users/{user_id}/avatar`
- **Get:** `GET /api/v1/users/{user_id}/avatar?size=medium`
- **Delete:** `DELETE /api/v1/users/{user_id}/avatar`
- **Info:** `GET /api/v1/users/{user_id}/avatar/info`

## Proposed Changes

### 1. New Agent Avatar Endpoint Structure

#### Target Endpoints
```
POST   /api/v1/agents/{agent_id}/avatar      # Upload agent avatar
GET    /api/v1/agents/{agent_id}/avatar      # Get agent avatar  
DELETE /api/v1/agents/{agent_id}/avatar      # Delete agent avatar
GET    /api/v1/agents/{agent_id}/avatar/info # Get agent avatar info
```

#### Key Differences from Current Implementation
- **Keep existing URL structure:** Maintain `{agent_id}` in path for consistency
- **Similar to user pattern:** Follow user avatar endpoint structure with agent-specific path
- **Dedicated concern:** Avatar operations separated from agent CRUD

### 2. Agent Schema Modifications

#### Remove from AgentCreateRequest (`app/schemas/agent.py:26`)
```python
# REMOVE this field:
avatar_url: Optional[str] = Field(None, max_length=500, description="URL for agent avatar image")
```

#### Remove from AgentUpdateRequest (`app/schemas/agent.py:60`)
```python  
# REMOVE this field:
avatar_url: Optional[str] = Field(None, max_length=500, description="URL for agent avatar image")
```

#### Keep in AgentResponse (Read-only)
```python
# KEEP this field for response data:
avatar_url: Optional[str] = None  # Read-only, populated from database
```

**Note:** The `GET /api/v1/agents/{agent_id}` and `GET /api/v1/agents/` endpoints will continue to return the `avatar_url` field populated from the database, but this field can only be modified through dedicated avatar endpoints.

### 3. Agent CRUD Endpoint Updates

#### Agent Creation - `POST /api/v1/agents/` (`app/api/v1/agents.py:52-57`)
**Current:**
```python
agent = await agent_service.create_agent(
    organization_id=current_user.organization_id,
    name=agent_data.name,
    agent_type=agent_data.agent_type,
    avatar_url=agent_data.avatar_url,  # REMOVE
    configuration=agent_data.model_dump(exclude={'name', 'agent_type', 'avatar_url'}),
    # ...
)
```

**Updated:**
```python
agent = await agent_service.create_agent(
    organization_id=current_user.organization_id,
    name=agent_data.name,
    agent_type=agent_data.agent_type,
    avatar_url=None,  # Always null on creation
    configuration=agent_data.model_dump(exclude={'name', 'agent_type'}),
    # ...
)
```

#### Agent Updates - `PUT /api/v1/agents/{agent_id}` (`app/api/v1/agents.py:95`)
**Remove avatar_url handling:**
- Filter out any `avatar_url` values from update request
- If client sends `avatar_url`, ignore it (don't include in updates dict)

### 4. Avatar Endpoint Implementation

#### Keep Existing `/agents/{agent_id}/avatar` endpoints
- **Current file:** `app/api/v1/agent_avatars.py` 
- **Current prefix:** `/agents` (line 22)
- **Keep existing URL structure:** Maintain `{agent_id}` parameter in all avatar endpoints
- **No path changes needed:** Current implementation already matches target structure

#### Current Avatar Upload (No Changes Needed)
```python
# EXISTING: Agent avatar upload already uses agent_id in path
@router.post("/{agent_id}/avatar", response_model=AvatarResponse)
async def upload_agent_avatar(
    agent_id: UUID,  # Agent ID in URL path (keep existing)
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
```

#### Special Case: Empty File Upload for Avatar Removal
```python
# When file is empty/blank, treat as avatar deletion
if file.size == 0 or not file.filename:
    # Call delete avatar logic
    success = await avatar_service.delete_agent_avatar(db, agent_id)
    return AvatarResponse(message="Avatar removed successfully")
```

### 5. Database Model Updates (Optional)

The existing `Agent` model in `app/models/ai_agent.py` already has:
- `avatar_url` field (line 51-55) - **KEEP**
- `has_custom_avatar` field (line 57-62) - **KEEP**

No database schema changes required.

### 6. Service Layer Updates

#### Avatar Service (`app/services/avatar_service.py`)
- **Keep existing methods:** `upload_agent_avatar()`, `get_agent_avatar_url()`, `delete_agent_avatar()`
- **Update agent model:** Ensure `avatar_url` is set to null when avatar deleted
- **Update agent model:** Ensure `has_custom_avatar` flag is maintained correctly

#### Agent Service (`app/services/agent_service.py`)
- **Remove avatar_url parameter** from `create_agent()` method signature
- **Filter avatar_url** from `update_agent()` operations
- **Keep avatar_url field** in database model (agents can still have avatar URLs)

## Implementation Plan

### Phase 1: Schema and Model Updates
1. **Update agent schemas** - Remove `avatar_url` from create/update requests
2. **Update agent creation endpoint** - Remove `avatar_url` handling
3. **Update agent update endpoint** - Filter out `avatar_url` from updates
4. **Test agent CRUD operations** - Ensure avatar_url cannot be set via CRUD

### Phase 2: Avatar Endpoint Enhancement  
1. **Keep existing avatar endpoints** in `agent_avatars.py` (no URL changes needed)
2. **Implement empty file deletion** feature in avatar upload endpoint
3. **Test avatar upload/delete/get operations**
4. **Verify avatar URLs are properly returned** in agent GET responses

### Phase 3: Test Updates and Integration Testing
1. **Update existing tests** - Modify tests that expect `avatar_url` in agent create/update
2. **Add avatar endpoint tests** - Ensure empty file deletion works
3. **End-to-end workflow testing** - Test agent creation → avatar upload → agent retrieval
4. **API documentation updates** - Update OpenAPI specs
5. **Performance impact assessment**

## Benefits

1. **Separation of Concerns:** Avatar management separate from agent configuration
2. **Consistency:** Matches established user avatar endpoint pattern  
3. **Cleaner APIs:** Agent CRUD focused solely on agent properties
4. **Flexibility:** Avatars can be managed independently of agent updates
5. **Security:** Clear authorization boundaries for different operations

## Risks and Considerations

1. **Breaking Changes:** Existing clients using `avatar_url` in agent create/update will break (acceptable)
2. **Migration Effort:** Frontend code will need updates to use avatar endpoints instead of CRUD
3. **Test Updates Required:** Multiple test files need updates for new behavior
4. **Documentation:** OpenAPI specs and documentation need comprehensive updates

## Success Criteria

1. ✅ Agent creation/update endpoints no longer accept `avatar_url`
2. ✅ Avatar upload/delete works via dedicated `/agents/avatar` endpoints
3. ✅ Empty file upload removes agent avatar
4. ✅ Agent responses still return `avatar_url` (read-only)
5. ✅ All existing avatar functionality preserved
6. ✅ Consistent with user avatar management pattern
7. ✅ No database schema changes required
8. ✅ Comprehensive test coverage

## Implementation Summary

The refactor is primarily focused on **separating concerns** rather than changing URL structures:

### What Changes:
- **Agent CREATE requests:** Remove `avatar_url` field from request body
- **Agent UPDATE requests:** Remove `avatar_url` field from request body  
- **Agent CRUD logic:** Filter out `avatar_url` from create/update operations
- **Empty file upload:** Add logic to delete avatar when empty file uploaded

### What Stays the Same:
- **Agent GET responses:** Continue returning `avatar_url` field (populated from database)
- **Avatar endpoint URLs:** Keep existing `/api/v1/agents/{agent_id}/avatar` structure
- **Avatar endpoint functionality:** Upload, get, delete, and info endpoints work as-is
- **Database schema:** No changes to Agent model or database tables

### Key Benefits:
- **Cleaner separation:** Avatar management separated from agent configuration
- **API consistency:** Agent CRUD focused on agent properties, avatars handled separately  
- **Clear responsibility boundaries:** Each endpoint has a single, well-defined purpose
- **Simplified client logic:** Clients know exactly which endpoint to use for each operation

## Test Files That Need Updates

### 1. Agent API Tests (`tests/test_api_endpoints.py` or similar)
- **Agent creation tests:** Remove `avatar_url` from create request payloads
- **Agent update tests:** Remove `avatar_url` from update request payloads  
- **Validation tests:** Add tests ensuring `avatar_url` is rejected in create/update requests
- **Response tests:** Verify agent GET responses still include `avatar_url` field

### 2. Agent Service Tests (`tests/unit/services/test_agent_service.py` or similar)  
- **Service method tests:** Update `create_agent()` and `update_agent()` method tests
- **Configuration tests:** Ensure avatar_url is not part of agent configuration updates
- **Field filtering tests:** Test that avatar_url is properly filtered from update operations

### 3. Avatar-Specific Tests (`tests/unit/services/test_avatar_service.py`)
- **Empty file upload tests:** Add tests for empty file → avatar deletion behavior
- **Avatar upload tests:** Ensure avatar upload updates agent.avatar_url in database
- **Avatar deletion tests:** Verify avatar deletion clears agent.avatar_url field

### 4. Schema Validation Tests (`tests/test_schemas.py` or similar)
- **AgentCreateRequest tests:** Verify `avatar_url` field is not accepted
- **AgentUpdateRequest tests:** Verify `avatar_url` field is not accepted
- **AgentResponse tests:** Verify `avatar_url` field is included in responses

### 5. Integration Tests (`tests/test_integration.py` or similar)
- **Full workflow tests:** Create agent → upload avatar → verify GET response includes avatar_url
- **Cross-endpoint tests:** Test interaction between agent CRUD and avatar endpoints
- **Authorization tests:** Ensure proper org-level access control for avatar operations
