# PRP: Unified Conversation PATCH Endpoint

**Status**: Draft  
**Created**: 2025-09-02  
**Author**: System Architecture Team  

## Overview

This PRP outlines the consolidation of three separate PATCH endpoints (`/title`, `/archive`, `/unarchive`) into a single unified PATCH endpoint `/api/v1/chat/conversations/{conversation_id}` that intelligently handles field updates based on the request body content.

## Current State

The chat API currently has three separate PATCH endpoints for conversation updates:

1. `PATCH /api/v1/chat/conversations/{conversation_id}/title` - Updates conversation title
2. `PATCH /api/v1/chat/conversations/{conversation_id}/archive` - Archives conversation  
3. `PATCH /api/v1/chat/conversations/{conversation_id}/unarchive` - Unarchives conversation

### Current Schemas
- `UpdateConversationTitleRequest`: Contains `title` field
- `ArchiveConversationRequest`: Contains `is_archived` boolean (unused in current implementation)
- `ArchiveConversationResponse`: Returns archive operation status

### Current Limitations
- **API Proliferation**: Multiple endpoints for simple field updates
- **Inconsistent Patterns**: Different response schemas for similar operations
- **Client Complexity**: Clients must know multiple endpoint URLs
- **Maintenance Overhead**: More routes to test, document, and maintain

## Proposed Solution

### New Unified Endpoint
```
PATCH /api/v1/chat/conversations/{conversation_id}
```

### Request Schema
```python
class UpdateConversationRequest(BaseSchema):
    """Unified request schema for conversation updates"""
    
    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=500,
        description="New conversation title"
    )
    is_archived: Optional[bool] = Field(
        None,
        description="Archive status - true to archive, false to unarchive"
    )
```

### Response Schema
```python
class ConversationUpdateResponse(BaseResponse):
    """Unified response schema for conversation updates"""
    
    id: UUID = Field(description="Conversation ID")
    user_id: Union[str, UUID] = Field(description="Owner user ID")
    title: Optional[str] = Field(description="Current conversation title")
    is_archived: bool = Field(description="Current archive status")
    updated_at: datetime = Field(description="Last updated timestamp")
    updated_fields: List[str] = Field(description="List of fields that were updated")
```

### API Behavior

#### Single Field Updates
```json
PATCH /api/v1/chat/conversations/{id}
{
  "title": "New Conversation Title"
}
```

```json
PATCH /api/v1/chat/conversations/{id}
{
  "is_archived": true
}
```

#### Multiple Field Updates
```json
PATCH /api/v1/chat/conversations/{id}
{
  "title": "Updated Title",
  "is_archived": true
}
```

#### Response Format
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "user-123",
  "title": "Updated Title",
  "is_archived": true,
  "updated_at": "2025-09-02T10:30:00Z",
  "updated_fields": ["title", "is_archived"]
}
```

## Implementation Requirements

### Validation Rules

1. **Request Validation**:
   - At least one field (`title` or `is_archived`) must be provided
   - `title` must be 1-500 characters when provided
   - `is_archived` must be boolean when provided
   - Empty request body should return 400 Bad Request

2. **Business Logic Validation**:
   - User must own the conversation (existing auth middleware)
   - Conversation must exist and not be deleted
   - Title updates should trim whitespace and validate non-empty after trim

3. **Field Update Logic**:
   - Only provided fields are updated (partial updates)
   - `updated_at` timestamp always updated when any field changes
   - `updated_fields` array reflects actual changes made
   - No-op updates (same value) should not update timestamps

### Error Handling

| Error Condition | Status Code | Response |
|---|---|---|
| Empty request body | 400 | `{"detail": "At least one field must be provided"}` |
| Invalid title length | 422 | Standard Pydantic validation error |
| Conversation not found | 404 | `{"detail": "Conversation not found"}` |
| Unauthorized access | 404 | `{"detail": "Conversation not found"}` (security) |
| Database error | 500 | `{"detail": "Internal server error"}` |

### Database Operations

1. **Single Query Approach**: Use single UPDATE query with SET conditions for provided fields
2. **Optimistic Updates**: Compare values before updating to avoid unnecessary writes
3. **Atomic Operations**: Ensure all field updates occur in single transaction
4. **Audit Logging**: Log field changes for compliance (existing audit system)

## Testing Strategy

### Unit Tests

1. **Schema Validation Tests** (`test_chat_schemas.py`):
   ```python
   def test_update_conversation_request_title_only():
   def test_update_conversation_request_archive_only():
   def test_update_conversation_request_both_fields():
   def test_update_conversation_request_empty_body():
   def test_update_conversation_request_invalid_title():
   ```

2. **Service Layer Tests** (`test_chat_service.py`):
   ```python
   def test_update_conversation_title_only():
   def test_update_conversation_archive_only():
   def test_update_conversation_multiple_fields():
   def test_update_conversation_no_changes():
   def test_update_conversation_not_found():
   ```

3. **API Endpoint Tests** (`test_chat_api_endpoints.py`):
   ```python
   def test_patch_conversation_title():
   def test_patch_conversation_archive():
   def test_patch_conversation_combined():
   def test_patch_conversation_empty_body():
   def test_patch_conversation_unauthorized():
   def test_patch_conversation_not_found():
   ```

### Integration Tests

1. **Database Integration Tests**:
   - Verify atomic updates across multiple fields
   - Test rollback behavior on constraint violations
   - Validate timestamp updates and audit logging

2. **Authentication Integration**:
   - Verify user ownership validation
   - Test cross-user access prevention
   - Validate JWT token handling

3. **WebSocket Integration**:
   - Verify real-time updates are broadcast for relevant changes
   - Test WebSocket message format for conversation updates

### Load Tests

1. **Concurrent Update Tests**:
   - Multiple users updating different conversations simultaneously
   - Same user updating same conversation with race conditions
   - Database connection pool handling under load

## Implementation Strategy

### Phase 1: Replace Endpoints (Week 1)
1. Remove existing `/title`, `/archive`, and `/unarchive` endpoints
2. Implement new unified endpoint `/api/v1/chat/conversations/{conversation_id}`
3. Create new request/response schemas
4. Update service layer with unified update method
5. Add comprehensive test coverage
6. **GATE**: All tests must pass before proceeding to Phase 2
   - Run `poetry run pytest tests/test_chat_api_endpoints.py -v`
   - Run `poetry run pytest tests/test_chat_service.py -v`
   - Run `poetry run pytest tests/test_chat_schemas.py -v`
   - All existing project tests must continue to pass: `poetry run pytest`

### Phase 2: Client Updates (Week 2)
1. Update frontend clients to use new unified endpoint
2. Update API documentation and examples
3. Update OpenAPI spec with new endpoint schema
4. Clean up unused schemas and service methods
5. **GATE**: All integration tests must pass before proceeding to Phase 3
   - Run full test suite: `poetry run pytest`
   - Verify no regression in API response times
   - Confirm WebSocket integration tests pass

### Phase 3: Final Validation (Week 3)
1. Complete end-to-end testing with updated clients
2. Performance testing and optimization
3. Security review of new endpoint
4. **GATE**: Complete project validation before marking implementation complete
   - Run full test suite: `poetry run pytest`
   - Run linting: `poetry run ruff check .`
   - Run type checking: `poetry run mypy .`
   - Verify all API documentation is updated
   - Confirm no dead code remains from removed endpoints

## Benefits

### Developer Experience
- **Simplified API**: Single endpoint for conversation updates
- **Flexible Updates**: Update one or multiple fields in single request
- **Consistent Responses**: Unified response format across all update operations
- **Better Tooling**: Single endpoint means better IDE autocomplete and API client generation

### Performance
- **Fewer Network Calls**: Combined updates reduce round trips
- **Database Efficiency**: Single query for multiple field updates
- **Reduced Payload Size**: No duplicate metadata across separate requests

### Maintenance
- **Less Code**: Single endpoint handler vs. three separate handlers
- **Unified Testing**: Single test suite covers all update scenarios
- **Consistent Behavior**: Single codebase ensures consistent validation and error handling

## Risks and Mitigations

### Risk: Breaking Changes
**Mitigation**: Direct replacement approach requires coordinated frontend/backend deployment but eliminates API versioning complexity

### Risk: Increased Complexity
**Mitigation**: Clear schema validation and comprehensive test coverage prevent edge cases

### Risk: Deployment Coordination
**Mitigation**: Feature flag approach allows safe rollout and rollback if needed

### Risk: Performance Regression
**Mitigation**: Database query optimization and performance testing during implementation

## Success Metrics

1. **API Implementation**: Unified endpoint successfully replaces three separate endpoints
2. **Error Rates**: <1% increase in 4xx/5xx errors during implementation
3. **Response Times**: No degradation in P95 response times
4. **Code Coverage**: 100% test coverage for new endpoint
5. **Developer Feedback**: Positive feedback from frontend team on API simplification
6. **Test Quality Gates**: All phases must pass their respective test gates:
   - Phase 1: 100% pass rate on new endpoint tests + all existing tests
   - Phase 2: 100% pass rate on integration tests + performance benchmarks
   - Phase 3: 100% pass rate on final validation + code quality checks

## Future Considerations

1. **Additional Fields**: Schema extensible for future conversation metadata updates
2. **Batch Operations**: Potential extension to update multiple conversations
3. **Optimistic Concurrency**: Consider ETags for conflict resolution on concurrent updates
4. **GraphQL**: Unified approach aligns well with potential GraphQL migration