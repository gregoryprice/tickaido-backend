# Conversation Archive/Unarchive API Implementation Proposal

## Overview

This proposal outlines the implementation of archive and unarchive functionality for chat conversations in the AI Ticket Creator Backend API. The feature will allow users to organize their conversations by archiving completed or inactive conversations while maintaining the ability to restore them when needed.

## Current State Analysis

The existing `ChatConversation` model already includes an `is_archived` field (line 26 in `app/models/chat.py`), but the functionality is not implemented in the API endpoints or services.

### Existing Model Fields
```python
# From ChatConversation model
is_archived = Column(Boolean, default=False)
```

## Proposed Implementation

### 1. API Endpoints

Add two new endpoints to the existing chat router (`app/api/v1/chat.py`):

#### Archive Conversation
```
PATCH /api/v1/chat/conversations/{conversation_id}/archive
```

#### Unarchive Conversation  
```
PATCH /api/v1/chat/conversations/{conversation_id}/unarchive
```

### 2. Service Layer Methods

Extend the `ChatService` class (`app/services/chat_service.py`) with:

```python
async def archive_conversation(
    self,
    db: AsyncSession,
    conversation_id: UUID,
    user_id: UUID
) -> Optional[ChatConversation]

async def unarchive_conversation(
    self,
    db: AsyncSession,
    conversation_id: UUID,
    user_id: UUID
) -> Optional[ChatConversation]
```

### 3. Enhanced List Functionality

Modify the existing `list_conversations` endpoint to support filtering:
- Add optional query parameter `archived` (default: `False`)

### 4. Schema Updates

Add new Pydantic response schemas in `app/schemas/chat.py`:

```python
class ArchiveConversationResponse(BaseModel):
    id: UUID
    is_archived: bool
    archived_at: datetime
    message: str
```

### 5. Database Considerations

#### Index Optimization
Add composite index for efficient archived conversation queries:
```sql
CREATE INDEX idx_chat_conversation_user_archived 
ON chat_conversations(user_id, is_archived, updated_at);
```

#### Migration Required
No database migration needed as `is_archived` field already exists.

## Detailed Implementation Plan

### Phase 1: Service Layer Implementation

#### Step 1.1: Archive Service Method
**Implementation:**
- Add `archive_conversation` method to `ChatService`
- Validate conversation ownership
- Set `is_archived = True`
- Update `updated_at` timestamp
- Return updated conversation or None if not found

**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Create unit tests for archive service method
poetry run pytest tests/test_chat_integration.py::test_archive_conversation_service -v

# Test cases must include:
# - Archive existing conversation (success)
# - Archive non-existent conversation (returns None)
# - Archive conversation owned by different user (returns None)
# - Archive already archived conversation (success, idempotent)
# - Database error handling
```

**Exit Criteria:**
- [ ] All archive service tests pass
- [ ] Code coverage > 90% for new method
- [ ] No regression in existing chat service tests
- [ ] Manual verification in database shows `is_archived=True` and `updated_at` changed

#### Step 1.2: Unarchive Service Method
**Implementation:**
- Add `unarchive_conversation` method to `ChatService`
- Validate conversation ownership
- Set `is_archived = False`
- Update `updated_at` timestamp
- Return updated conversation or None if not found

**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Create unit tests for unarchive service method
poetry run pytest tests/test_chat_integration.py::test_unarchive_conversation_service -v

# Test cases must include:
# - Unarchive archived conversation (success)
# - Unarchive non-existent conversation (returns None)
# - Unarchive conversation owned by different user (returns None)
# - Unarchive already unarchived conversation (success, idempotent)
# - Database error handling
```

**Exit Criteria:**
- [ ] All unarchive service tests pass
- [ ] Code coverage > 90% for new method
- [ ] No regression in existing chat service tests
- [ ] Manual verification in database shows `is_archived=False` and `updated_at` changed

#### Step 1.3: Enhanced List Method
**Implementation:**
- Modify existing `list_conversations` to accept `archived` parameter
- Update query conditions based on `is_archived` database field
- Maintain existing pagination and sorting

**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Test enhanced list functionality
poetry run pytest tests/test_chat_integration.py::test_list_conversations_with_archive_filters -v

# Test cases must include:
# - List conversations (default behavior unchanged, archived=False)
# - List with archived=True (shows only archived conversations)
# - List with archived=False (shows only non-archived conversations)
# - Pagination works with archive filters
# - Sorting maintained with archive filters
# - Performance test with large dataset
```

**Exit Criteria:**
- [ ] All enhanced list service tests pass
- [ ] Backward compatibility confirmed (existing API calls unchanged)
- [ ] Performance benchmarks meet requirements
- [ ] No regression in existing list functionality

### Phase 2: API Endpoint Implementation

#### Step 2.1: Schema Implementation
**Implementation:**
- Add `ArchiveConversationResponse` schema in `app/schemas/chat.py`
- Update existing schemas if needed for archive support

**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Test schema validation
poetry run pytest tests/test_schemas.py::test_archive_conversation_response -v

# Test cases must include:
# - Schema validation with valid data
# - Schema serialization/deserialization
# - Field type validation
# - Required field validation
```

**Exit Criteria:**
- [ ] Schema tests pass
- [ ] Schema documentation generated correctly
- [ ] No conflicts with existing schemas

#### Step 2.2: Archive Endpoint
**Implementation:**
- Add `PATCH /conversations/{conversation_id}/archive` endpoint
- Path parameter validation
- Authentication required
- Response formatting
- Error handling

**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Test archive endpoint
poetry run pytest tests/test_chat_api_basic.py::test_archive_conversation_endpoint -v

# Test cases must include:
# - Archive conversation (200 success)
# - Archive non-existent conversation (404)
# - Archive without authentication (401)
# - Archive conversation owned by different user (404)
# - Archive with invalid UUID (400)
# - Archive already archived conversation (200, idempotent)
# - Database connection error (500)

# Integration test
curl -X PATCH "http://localhost:8000/api/v1/chat/conversations/{id}/archive" \
     -H "Authorization: Bearer <token>"
```

**Exit Criteria:**
- [ ] All archive endpoint tests pass
- [ ] Manual API testing successful
- [ ] OpenAPI documentation updated and accurate
- [ ] Error responses match specification

#### Step 2.3: Unarchive Endpoint
**Implementation:**
- Add `PATCH /conversations/{conversation_id}/unarchive` endpoint
- Path parameter validation
- Authentication required
- Response formatting
- Error handling

**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Test unarchive endpoint
poetry run pytest tests/test_chat_api_basic.py::test_unarchive_conversation_endpoint -v

# Test cases must include:
# - Unarchive conversation (200 success)
# - Unarchive non-existent conversation (404)
# - Unarchive without authentication (401)
# - Unarchive conversation owned by different user (404)
# - Unarchive with invalid UUID (400)
# - Unarchive already unarchived conversation (200, idempotent)
# - Database connection error (500)

# Integration test
curl -X PATCH "http://localhost:8000/api/v1/chat/conversations/{id}/unarchive" \
     -H "Authorization: Bearer <token>"
```

**Exit Criteria:**
- [ ] All unarchive endpoint tests pass
- [ ] Manual API testing successful
- [ ] OpenAPI documentation updated and accurate
- [ ] Error responses match specification

#### Step 2.4: Enhanced List Endpoint
**Implementation:**
- Add query parameter `archived` to existing endpoint
- Maintain backward compatibility
- Update response handling
- Update documentation

**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Test enhanced list endpoint
poetry run pytest tests/test_chat_api_basic.py::test_list_conversations_with_filters -v

# Test cases must include:
# - Default behavior unchanged (backward compatibility, archived=False)
# - archived=true returns only archived conversations
# - archived=false returns only non-archived conversations
# - Invalid parameter values handled gracefully
# - Pagination works with archive filter
# - Authentication required
# - Empty result sets handled properly

# Integration tests
curl "http://localhost:8000/api/v1/chat/conversations" \
     -H "Authorization: Bearer <token>"
curl "http://localhost:8000/api/v1/chat/conversations?archived=true" \
     -H "Authorization: Bearer <token>"
curl "http://localhost:8000/api/v1/chat/conversations?archived=false" \
     -H "Authorization: Bearer <token>"
```

**Exit Criteria:**
- [ ] All enhanced list tests pass
- [ ] Backward compatibility confirmed with existing clients
- [ ] Performance acceptable with large datasets
- [ ] API documentation accurate

### Phase 3: Integration & End-to-End Testing

#### Step 3.1: Complete Integration Testing
**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Run full test suite
poetry run pytest tests/ -v

# Specific integration test scenarios
poetry run pytest tests/test_chat_integration.py::test_full_archive_workflow -v

# Test workflow:
# 1. Create conversation
# 2. Add messages
# 3. Archive conversation
# 4. Verify not in default list
# 5. Verify in archived list
# 6. Unarchive conversation
# 7. Verify back in default list
# 8. Delete conversation
# 9. Verify archive state persists for deleted items
```

**Exit Criteria:**
- [ ] All existing tests continue to pass (no regressions)
- [ ] New integration tests pass
- [ ] End-to-end workflow validates correctly
- [ ] Performance benchmarks met

#### Step 3.2: Database Performance Validation
**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Performance testing with large datasets
poetry run pytest tests/test_chat_performance.py -v

# Database query analysis
# - List queries perform well with archive filters
# - Archive/unarchive operations are fast
# - No N+1 query problems
# - Index usage verified
```

**Exit Criteria:**
- [ ] Query performance within acceptable limits
- [ ] Database indexes utilized effectively
- [ ] Memory usage acceptable
- [ ] No performance regressions

#### Step 3.3: Security & Authorization Testing
**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Security testing
poetry run pytest tests/test_chat_security.py -v

# Test scenarios:
# - Cannot archive/unarchive conversations owned by other users
# - JWT token validation works correctly
# - Rate limiting applies to new endpoints
# - SQL injection attempts fail safely
# - Input validation prevents malicious payloads
```

**Exit Criteria:**
- [ ] All security tests pass
- [ ] Authorization properly enforced
- [ ] Input validation comprehensive
- [ ] Rate limiting functional

### Phase 4: Documentation & Deployment Preparation

#### Step 4.1: Documentation Updates
**Implementation:**
- Update OpenAPI specification
- Update API documentation
- Create migration notes if needed

**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Documentation validation
# - OpenAPI spec generates without errors
# - All endpoints documented
# - Example requests/responses accurate
# - Postman collection updated and tested
```

**Exit Criteria:**
- [ ] OpenAPI spec validates
- [ ] Documentation complete and accurate
- [ ] Examples tested and working

#### Step 4.2: Final Validation
**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Complete system test
docker compose up -d
poetry run pytest tests/ -v --cov=app --cov-report=html

# Manual API testing with Postman/curl
# Load testing if applicable
# Cross-browser testing if UI involved
```

**Exit Criteria:**
- [ ] All tests pass in clean environment
- [ ] Code coverage targets met (>90% for new code)
- [ ] Manual testing validates all scenarios
- [ ] Performance acceptable under load

## API Specification

### Archive Conversation

**Request:**
```http
PATCH /api/v1/chat/conversations/{conversation_id}/archive
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "is_archived": true,
  "archived_at": "2024-01-15T10:30:00Z",
  "message": "Conversation archived successfully"
}
```

### Unarchive Conversation

**Request:**
```http
PATCH /api/v1/chat/conversations/{conversation_id}/unarchive
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "is_archived": false,
  "archived_at": null,
  "message": "Conversation unarchived successfully"
}
```

### Enhanced List Conversations

**Request:**
```http
GET /api/v1/chat/conversations?archived=true
Authorization: Bearer <token>
```

**Response (200):**
```json
[
  {
    "id": "456e7890-e12b-34d5-a789-426614174001",
    "title": "Technical Question",
    "is_archived": true,
    "created_at": "2024-01-10T09:00:00Z",
    "updated_at": "2024-01-14T15:30:00Z",
    "total_messages": 12
  }
]
```

## Error Handling

### Standard Error Responses

- **404 Not Found:** Conversation doesn't exist or user doesn't have access
- **400 Bad Request:** Invalid conversation ID format
- **401 Unauthorized:** Missing or invalid authentication token
- **500 Internal Server Error:** Database or server errors

## Security Considerations

1. **Ownership Validation:** All operations validate that the current user owns the conversation
2. **Soft Operations:** Archive/unarchive are non-destructive operations
3. **Audit Trail:** Operations update the `updated_at` timestamp for tracking
4. **Rate Limiting:** Existing middleware applies to new endpoints

## Performance Impact

- **Database Queries:** Minimal impact as operations are simple boolean updates
- **Indexing:** Existing indexes on `user_id` and `updated_at` support efficient queries
- **Caching:** No additional caching complexity introduced

## Backward Compatibility

- **Existing Endpoints:** No breaking changes to current API
- **Default Behavior:** List conversations excludes archived by default (unchanged)
- **Database Schema:** No migration required

## Testing Strategy

1. **Service Layer Tests:**
   - Archive/unarchive functionality
   - Ownership validation
   - Error handling

2. **API Integration Tests:**
   - Endpoint functionality
   - Authentication
   - Response formats

3. **Performance Tests:**
   - Query performance with archived conversations
   - Large dataset handling

## Implementation Timeline

- **Phase 1 (Service Layer + Validation):** 4-6 hours
  - Implementation: 2-3 hours
  - Testing & Validation: 2-3 hours
- **Phase 2 (API Endpoints + Validation):** 6-8 hours
  - Implementation: 3-4 hours
  - Testing & Validation: 3-4 hours
- **Phase 3 (Integration & E2E Testing):** 4-6 hours
  - Integration Testing: 2-3 hours
  - Performance & Security: 2-3 hours
- **Phase 4 (Documentation & Final Validation):** 2-3 hours
  - Documentation: 1-2 hours
  - Final Validation: 1 hour
- **Total Estimated Time:** 16-23 hours

**Critical Path Dependencies:**
- Each phase MUST be completed and validated before proceeding
- All tests MUST pass before moving to next step
- No step can be skipped or validation bypassed
- Code coverage requirements MUST be met (>90% for new code)

## Files to Modify

1. `app/services/chat_service.py` - Add archive/unarchive methods
2. `app/api/v1/chat.py` - Add new endpoints and enhance list endpoint
3. `app/schemas/chat.py` - Add response schemas
4. `tests/test_chat_integration.py` - Add service tests
5. `tests/test_chat_api_basic.py` - Add API tests
6. `openapi.yaml` - Update API documentation (if manually maintained)

## Future Enhancements

1. **Bulk Operations:** Archive/unarchive multiple conversations
2. **Auto-Archive:** Automatically archive conversations after inactivity period
3. **Archive Analytics:** Track archival patterns and usage
4. **Search Integration:** Include archived conversations in search with explicit flag