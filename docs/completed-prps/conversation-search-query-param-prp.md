# PRP: Conversation Search Query Parameter

**Status**: Draft  
**Created**: 2025-09-03  
**Author**: System Architecture Team  

## Goal

Add a "q" query parameter to the `GET /api/v1/chat/conversations` endpoint that allows text searching of conversation titles and message content, returning filtered conversations based on the search query.

## Why

- **Improved User Experience**: Users can quickly find specific conversations without scrolling through entire list
- **Chrome Extension Efficiency**: Enables search functionality in the extension popup/interface
- **Content Discovery**: Users can locate conversations based on what they discussed, not just titles
- **Productivity Enhancement**: Reduces time spent looking for historical conversations

## What

Enhance the existing `GET /api/v1/chat/conversations` endpoint to accept an optional `q` query parameter that performs full-text search across:

1. **Conversation titles** (`ChatConversation.title`)
2. **Message content** (`ChatMessage.content` from both user and assistant messages)

### Success Criteria
- [ ] Search parameter "q" added to existing conversations endpoint
- [ ] Search functionality works across conversation titles and message content
- [ ] Results maintain existing pagination and archive filtering
- [ ] Search is case-insensitive and supports partial matching
- [ ] Performance remains acceptable with proper indexing
- [ ] All existing functionality preserved (backward compatibility)

## All Needed Context

### Documentation & References
```yaml
- file: app/api/v1/chat.py
  why: Current endpoint implementation and query patterns
  
- file: app/models/chat.py  
  why: Database model structure for search indexing strategy
  
- file: app/services/chat_service.py
  why: Existing list_conversations method to extend
  
- file: app/schemas/chat.py
  why: Understand response schemas and validation patterns

- docfile: docs/implemented-prps/unified-conversation-patch-endpoint-prp.md
  why: Reference for proper PRP implementation patterns and validation approach
```

### Current Codebase Structure
```
app/
├── api/v1/chat.py              # Existing endpoint: GET /conversations
├── models/chat.py              # ChatConversation, ChatMessage models  
├── services/chat_service.py    # list_conversations() method to extend
└── schemas/chat.py             # ConversationResponse schema
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: PostgreSQL full-text search with SQLAlchemy 2.0 async
# Use PostgreSQL's built-in search operators (ILIKE, to_tsvector, plainto_tsquery)
# GOTCHA: Cross-table joins with message content require proper indexing
# PATTERN: Use existing pagination and filtering patterns from list_conversations
# SECURITY: Ensure search only returns conversations owned by requesting user
```

## Implementation Blueprint

### Data Models and Structure

The search will utilize existing models with potential database index optimization:

```python
# app/models/chat.py - Consider adding search indexes
class ChatConversation(BaseModel):
    # Existing fields...
    title = Column(String(500))  # Search target
    
    # New potential indexes for search optimization:
    __table_args__ = (
        # Existing indexes...
        Index('idx_chat_conversation_title_search', 'title'),  # For title search
        Index('idx_chat_conversation_user_title', 'user_id', 'title'),  # Compound search
    )

class ChatMessage(BaseModel):
    # Existing fields...
    content = Column(Text, nullable=False)  # Search target
    
    # New potential indexes for search optimization:
    __table_args__ = (
        # Existing indexes...
        Index('idx_chat_message_content_search', 'content'),  # For content search
        Index('idx_chat_message_conv_content', 'conversation_id', 'content'),  # Compound
    )
```

### List of Tasks to be Completed

```yaml
Task 1: "Extend chat service list_conversations method"
MODIFY app/services/chat_service.py:
  - FIND method: "async def list_conversations"
  - ADD parameter: query: Optional[str] = None
  - INJECT search logic using PostgreSQL ILIKE for title and JOIN for message content
  - PRESERVE existing pagination, user filtering, and archive logic

Task 2: "Update chat API endpoint to accept query parameter"  
MODIFY app/api/v1/chat.py:
  - FIND endpoint: "@router.get("/conversations", response_model=List[ConversationResponse])"
  - ADD parameter: q: Optional[str] = Query(None, description="Search query for titles and content")
  - PASS query parameter to chat_service.list_conversations
  - PRESERVE existing archived parameter and user authentication

Task 3: "Add database migration for search optimization indexes"
CREATE new alembic migration:
  - ADD indexes for title and content search optimization
  - ENSURE backward compatibility
  - TEST migration rollback functionality

Task 4: "Create comprehensive test coverage with MANDATORY validation gates"
CREATE tests/test_conversation_search.py:
  - COVER search functionality across titles and content
  - TEST case sensitivity, partial matching, special characters
  - VERIFY user isolation and security
  - VALIDATE pagination works with search results
  - GATE: ALL tests must pass before proceeding to next phase

Task 5: "Validate all existing tests continue to pass (REGRESSION PREVENTION)"
RUN complete test suite validation:
  - EXECUTE: poetry run pytest tests/ -v
  - REQUIREMENT: 100% pass rate, ZERO failures allowed
  - GATE: If ANY test fails, STOP and investigate root cause

Task 6: "Validate OpenAPI documentation auto-generation"  
VERIFY FastAPI auto-generates documentation:
  - CHECK: /openapi.json includes new "q" parameter
  - CHECK: /docs shows parameter in Swagger UI
  - CHECK: /redoc shows parameter documentation
  - GATE: Documentation must be automatically updated without manual changes
```

### Per Task Pseudocode

```python
# Task 1 - Service Layer Extension
async def list_conversations(
    self,
    db: AsyncSession,
    user_id: UUID,
    offset: int = 0,
    limit: int = 20,
    archived: Optional[bool] = False,
    query: Optional[str] = None  # NEW PARAMETER
) -> Tuple[List[ChatConversation], int]:
    # PATTERN: Build base conditions as before
    conditions = [
        ChatConversation.user_id == str(user_id),
        ChatConversation.is_deleted.is_(False)
    ]
    
    # EXISTING: Archive filter logic
    if archived is not None:
        conditions.append(ChatConversation.is_archived.is_(archived))
    
    # NEW: Search logic
    if query and query.strip():
        search_term = f"%{query.strip()}%"
        
        # Search in conversation titles
        title_condition = ChatConversation.title.ilike(search_term)
        
        # Search in message content (requires subquery)
        message_subquery = select(ChatMessage.conversation_id).where(
            ChatMessage.content.ilike(search_term)
        ).distinct()
        content_condition = ChatConversation.id.in_(message_subquery)
        
        # Combine with OR logic
        search_condition = or_(title_condition, content_condition)
        conditions.append(search_condition)
    
    # PRESERVE: Existing query structure and pagination
    query = select(ChatConversation).where(*conditions).order_by(desc(ChatConversation.updated_at))
    # ... rest of existing implementation
```

### Integration Points
```yaml
DATABASE:
  - migration: "Add search optimization indexes for title and content"
  - indexes: 
    - "CREATE INDEX idx_chat_conversation_title_search ON chat_conversations USING gin(to_tsvector('english', title))"
    - "CREATE INDEX idx_chat_message_content_search ON chat_messages USING gin(to_tsvector('english', content))"
  
API:
  - extend: app/api/v1/chat.py GET /conversations endpoint
  - add_param: "q: Optional[str] = Query(None, description='Search conversations by title and content')"
  
SCHEMA:
  - no_changes: Existing ConversationResponse schema sufficient
  - validation: Query parameter validation via FastAPI Query() helper
```

## Validation Loop & Testing Strategy

**CRITICAL IMPLEMENTATION RULE**: You CANNOT proceed to the next task until ALL tests and validation pass. Each phase has mandatory gates that MUST be satisfied before moving forward.

### Phase 1: Code Implementation & Quality Gates

#### 1.1 Syntax & Style Validation (MANDATORY GATE)
```bash
# MUST PASS before proceeding - fix ALL errors
poetry run ruff check app/api/v1/chat.py app/services/chat_service.py --fix
poetry run mypy app/api/v1/chat.py app/services/chat_service.py

# GATE CRITERIA: ZERO errors, ZERO warnings
# Expected output: "All checks passed!" or no errors
# If ANY errors: STOP, fix errors, re-run until clean
```

#### 1.2 Database Migration Validation (MANDATORY GATE)
```bash
# Test migration creation and application
poetry run alembic revision --autogenerate -m "Add search indexes for conversation search"
poetry run alembic upgrade head

# Test rollback capability
poetry run alembic downgrade -1
poetry run alembic upgrade head

# GATE CRITERIA: Migration applies and rolls back cleanly
# If migration fails: Fix database schema issues before proceeding
```

### Phase 2: Comprehensive Test Coverage (MANDATORY GATE)

#### 2.1 Create New Search-Specific Tests (REQUIRED)
```python
# CREATE tests/test_conversation_search.py with EXACT test cases:
import pytest
from uuid import uuid4
from app.services.chat_service import chat_service
from app.models.chat import ChatConversation, ChatMessage

async def test_search_by_title():
    """Search finds conversations by title - EXACT match required"""
    # Create conversation with title "Project Alpha Discussion"
    # Search with query "Alpha" 
    # ASSERT: conversation found in results
    # ASSERT: search is case-insensitive

async def test_search_by_message_content():
    """Search finds conversations by message content - EXACT match required"""
    # Create conversation and add message with content "database performance issues"
    # Search with query "performance"
    # ASSERT: conversation found in results
    # ASSERT: only conversations with matching messages returned

async def test_search_case_insensitive():
    """Search is case insensitive - EXACT validation required"""
    # Create conversation with title "Bug Report"
    # Test searches: "bug", "BUG", "Bug", "bUg"
    # ASSERT: ALL variations return same results

async def test_search_with_no_results():
    """Search with no matches returns empty list - EXACT validation"""
    # Search for guaranteed non-existent content "xyzabc123unique"
    # ASSERT: Empty list returned
    # ASSERT: Total count is 0

async def test_search_respects_user_isolation():
    """Search only returns user's own conversations - SECURITY CRITICAL"""
    # Create conversations for user A and user B with same search term
    # Search as user A
    # ASSERT: ONLY user A's conversations returned
    # ASSERT: User B's conversations NEVER appear in results

async def test_search_with_pagination():
    """Search results work with pagination - EXACT validation"""
    # Create 25 conversations with matching search term
    # Search with offset=10, limit=10
    # ASSERT: Exactly 10 results returned
    # ASSERT: Correct offset applied (results 10-19)

async def test_search_preserves_archive_filter():
    """Search + archive filtering works together - EXACT validation"""
    # Create archived and non-archived conversations with same search term
    # Search with archived=false and search query
    # ASSERT: Only non-archived matching conversations returned

async def test_search_empty_query_returns_all():
    """Empty or whitespace query returns all conversations - BACKWARD COMPATIBILITY"""
    # Test with: None, "", "   ", "\t\n"
    # ASSERT: Behaves exactly like endpoint without query parameter
    # ASSERT: All user's conversations returned (respecting archive filter)

async def test_search_special_characters():
    """Search handles special characters safely - SECURITY VALIDATION"""
    # Test searches with: SQL injection attempts, regex chars, Unicode
    # ASSERT: No database errors
    # ASSERT: Safe handling of all input types

async def test_search_performance():
    """Search performance meets requirements - PERFORMANCE GATE"""
    # Create 1000+ conversations and messages
    # Execute search queries
    # ASSERT: All searches complete within 500ms
    # ASSERT: No N+1 query issues
```

#### 2.2 Test Execution Gates (MANDATORY)
```bash
# 🚨 CRITICAL: ALL these commands MUST pass before proceeding

# Gate 2.2.1: New search tests MUST pass
poetry run pytest tests/test_conversation_search.py -v
# REQUIREMENT: 100% pass rate, no skipped tests

# Gate 2.2.2: ALL existing chat tests MUST continue passing  
poetry run pytest tests/test_chat_api_basic.py -v
poetry run pytest tests/test_chat_integration.py -v
poetry run pytest tests/test_chat_service_title_generation.py -v
# REQUIREMENT: 100% pass rate, no regression failures

# Gate 2.2.3: ENTIRE test suite MUST pass (critical for backward compatibility)
poetry run pytest tests/ -v
# REQUIREMENT: 100% pass rate across ALL tests
# If ANY test fails: STOP, investigate, fix root cause

# Gate 2.2.4: Database integration tests in Docker environment
docker compose up -d postgres redis
docker compose exec app poetry run pytest tests/test_conversation_search.py -v
# REQUIREMENT: Tests pass in production-like environment
```

### Phase 3: API Documentation & OpenAPI Auto-Generation (MANDATORY GATE)

#### 3.1 OpenAPI Auto-Generation Validation
FastAPI automatically generates OpenAPI specification when query parameters are added. Verify this works:

```bash
# Start the application
docker compose up -d

# Verify OpenAPI schema includes new parameter
curl -X GET "http://localhost:8000/openapi.json" | jq '.paths["/api/v1/chat/conversations"].get.parameters'

# EXPECTED OUTPUT: Must include query parameter "q" with proper description
# Example expected structure:
# {
#   "name": "q",
#   "in": "query", 
#   "required": false,
#   "schema": {
#     "type": "string",
#     "title": "Q",
#     "description": "Search conversations by title and content"
#   }
# }
```

#### 3.2 Interactive Documentation Validation  
```bash
# Test Swagger UI includes new parameter
# Visit: http://localhost:8000/docs
# Navigate to: GET /api/v1/chat/conversations
# VERIFY: "q" parameter appears in the parameter list
# VERIFY: Parameter has proper description and type
# VERIFY: "Try it out" functionality works with search parameter

# Test ReDoc documentation  
# Visit: http://localhost:8000/redoc
# Navigate to: Chat Assistant → GET /api/v1/chat/conversations
# VERIFY: Query parameter "q" documented with description
# VERIFY: Examples show proper usage patterns
```

#### 3.3 OpenAPI Export Validation
```bash
# Verify OpenAPI YAML export includes changes
curl -X GET "http://localhost:8000/openapi.yaml" -o updated_openapi.yaml
grep -A 10 -B 10 "conversations" updated_openapi.yaml | grep -A 5 -B 5 '"q"'

# GATE CRITERIA: New parameter present in YAML export
# This ensures main.py:610-623 FileResponse works correctly
```

### Phase 4: End-to-End Integration Testing (MANDATORY GATE)

#### 4.1 Complete API Workflow Test
```bash
# Complete user journey test script - ALL commands MUST succeed

# 1. Start services
docker compose up -d
sleep 10  # Wait for services to be ready

# 2. Register user and get token
TOKEN=$(curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "full_name": "Test User", "password": "TestPass123", "organization_name": "Test Org"}' \
  | jq -r '.access_token')

# 3. Create test conversations with specific content
CONV1=$(curl -X POST "http://localhost:8000/api/v1/chat/conversations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Bug Report Database Performance"}' \
  | jq -r '.id')

CONV2=$(curl -X POST "http://localhost:8000/api/v1/chat/conversations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Feature Request User Interface"}' \
  | jq -r '.id')

# 4. Add messages with searchable content
curl -X POST "http://localhost:8000/api/v1/chat/conversations/$CONV1/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "We are experiencing slow query performance on the user table"}'

# 5. Test search functionality
# Search by title content
SEARCH_RESULTS=$(curl -X GET "http://localhost:8000/api/v1/chat/conversations?q=database" \
  -H "Authorization: Bearer $TOKEN")
echo "$SEARCH_RESULTS" | jq '.[].title' | grep -i "database" || exit 1

# Search by message content  
SEARCH_RESULTS=$(curl -X GET "http://localhost:8000/api/v1/chat/conversations?q=performance" \
  -H "Authorization: Bearer $TOKEN")
echo "$SEARCH_RESULTS" | jq '.[].id' | grep "$CONV1" || exit 1

# Search with archive filter combination
curl -X GET "http://localhost:8000/api/v1/chat/conversations?q=bug&archived=false" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.[] | select(.title | test("Bug"; "i"))' || exit 1

# GATE CRITERIA: ALL curl commands return expected results with exit code 0
```

#### 4.2 Performance & Load Testing (MANDATORY GATE)
```bash
# Create load test data
for i in {1..100}; do
  curl -X POST "http://localhost:8000/api/v1/chat/conversations" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"title\": \"Load Test Conversation $i with searchable content\"}" &
done
wait

# Performance test - search MUST complete within 500ms
time curl -X GET "http://localhost:8000/api/v1/chat/conversations?q=searchable" \
  -H "Authorization: Bearer $TOKEN"

# GATE CRITERIA: Search response time < 500ms for 100+ conversations
```

## Final Validation Checklist (ALL REQUIRED)

### Code Quality Gates (MANDATORY)
- [ ] **Syntax Clean**: `poetry run ruff check .` returns ZERO errors
- [ ] **Type Safety**: `poetry run mypy .` returns ZERO errors  
- [ ] **Import Validation**: All imports resolve correctly
- [ ] **Security Review**: No credentials exposed, proper input sanitization

### Test Coverage Gates (MANDATORY) 
- [ ] **New Feature Tests**: `poetry run pytest tests/test_conversation_search.py -v` - 100% pass
- [ ] **Existing Chat Tests**: `poetry run pytest tests/test_chat_api_basic.py tests/test_chat_integration.py tests/test_chat_service_title_generation.py -v` - 100% pass  
- [ ] **Complete Test Suite**: `poetry run pytest tests/ -v` - 100% pass, ZERO failures
- [ ] **Docker Test Environment**: `docker compose exec app poetry run pytest tests/test_conversation_search.py -v` - 100% pass

### API Documentation Gates (MANDATORY)
- [ ] **OpenAPI Generation**: New "q" parameter auto-included in `/openapi.json`
- [ ] **Swagger UI**: Parameter visible and functional at `http://localhost:8000/docs`
- [ ] **ReDoc**: Parameter documented at `http://localhost:8000/redoc`
- [ ] **YAML Export**: Parameter present in `http://localhost:8000/openapi.yaml`

### Functional Validation Gates (MANDATORY)
- [ ] **Title Search**: Finding conversations by partial title match
- [ ] **Content Search**: Finding conversations by message content
- [ ] **Case Insensitive**: Search works regardless of case
- [ ] **User Isolation**: Users only see own conversations in search results
- [ ] **Archive Compatibility**: Search + archive filter works together
- [ ] **Pagination Compatibility**: Search results properly paginated
- [ ] **Empty Query Handling**: Empty/null query returns all conversations (backward compatibility)
- [ ] **Special Characters**: Search safely handles special characters and potential injection attempts

### Performance Gates (MANDATORY)
- [ ] **Response Time**: All search queries complete within 500ms
- [ ] **Database Efficiency**: No N+1 queries, proper index usage
- [ ] **Memory Usage**: No memory leaks during search operations
- [ ] **Concurrent Users**: Search works correctly with multiple simultaneous users

### Security Gates (MANDATORY) 
- [ ] **Data Isolation**: Search never returns other users' conversations
- [ ] **Input Sanitization**: Search query safely handled, no SQL injection possible
- [ ] **Authentication**: Search requires valid JWT token
- [ ] **Authorization**: Search respects user ownership and permissions

## OpenAPI Auto-Generation & Documentation

### FastAPI Automatic Documentation Generation

FastAPI automatically generates comprehensive OpenAPI documentation when you add properly annotated query parameters. The implementation leverages this through:

#### Current Setup in main.py:163-173
```python
app = FastAPI(
    title="AI Ticket Creator Backend API",
    description="API for AI-powered ticket creation...",
    version="1.0.0",
    docs_url="/docs",           # Swagger UI auto-generated
    redoc_url="/redoc",         # ReDoc auto-generated  
    openapi_url="/openapi.json" # OpenAPI spec auto-generated
)
```

#### Custom OpenAPI Enhancement in main.py:1229-1313
The custom `custom_openapi()` function extends the auto-generated schema with additional metadata while preserving all FastAPI auto-generation.

#### Documentation Endpoints Updated Automatically
When you add the `q` parameter with proper FastAPI `Query()` annotation:

```python
@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    archived: bool = Query(False, description="Filter by archive status"),
    q: str = Query(None, description="Search conversations by title and content"),  # NEW
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
```

**Auto-Generated Documentation Includes:**
1. **Parameter Documentation**: Description, type, required/optional status
2. **Example Requests**: Interactive "Try it out" functionality  
3. **Response Schemas**: Existing ConversationResponse schema preserved
4. **Error Responses**: HTTP status codes and error formats

#### Validation Requirements for OpenAPI
- [ ] **Parameter Description**: "Search conversations by title and content" appears in docs
- [ ] **Parameter Type**: Correctly shows as optional string parameter
- [ ] **Example Usage**: Docs show example queries like `?q=project&archived=false`
- [ ] **Interactive Testing**: "Try it out" functionality works in Swagger UI
- [ ] **YAML Export**: Parameter included in downloadable OpenAPI YAML from `/openapi.yaml`

### No Manual Documentation Updates Required
Because FastAPI auto-generates documentation from code annotations, NO manual updates are needed to:
- `openapi.yaml` (if it exists - this is auto-generated)
- Swagger UI documentation at `/docs`
- ReDoc documentation at `/redoc` 
- OpenAPI JSON at `/openapi.json`

The existing `main.py:610-623` endpoint serves any static `openapi.yaml` file, but the live documentation is always auto-generated from the FastAPI application.

## MANDATORY Implementation Strategy with Quality Gates

**🚨 CRITICAL RULE**: Each phase has MANDATORY gates that MUST pass before proceeding. No exceptions.

### Phase 1: Code Implementation with Quality Gates

#### Step 1.1: Database Migration (GATE REQUIRED)
```bash
# Create and apply search optimization indexes
poetry run alembic revision --autogenerate -m "Add search indexes for conversation search"
poetry run alembic upgrade head

# MANDATORY GATE: Migration must apply cleanly
# Test rollback capability
poetry run alembic downgrade -1
poetry run alembic upgrade head

# 🚨 STOP here if migration fails - fix database issues first
```

#### Step 1.2: Service Layer Implementation (GATE REQUIRED)  
```bash
# Implement search logic in chat_service.py
# Add query parameter to list_conversations method
# Implement PostgreSQL ILIKE search across titles and message content

# MANDATORY GATE: Code quality validation
poetry run ruff check app/services/chat_service.py --fix
poetry run mypy app/services/chat_service.py

# 🚨 STOP here if ANY errors - fix ALL issues before proceeding
```

#### Step 1.3: API Endpoint Update (GATE REQUIRED)
```bash  
# Add query parameter to chat API endpoint
# Update FastAPI Query() annotation for auto-documentation

# MANDATORY GATE: Code quality validation
poetry run ruff check app/api/v1/chat.py --fix  
poetry run mypy app/api/v1/chat.py

# 🚨 STOP here if ANY errors - fix ALL issues before proceeding
```

### Phase 2: Comprehensive Test Implementation (GATE REQUIRED)

#### Step 2.1: Create New Test File (REQUIRED)
```bash
# Create tests/test_conversation_search.py with all test cases from section 2.1
# MANDATORY: All 10 test functions must be implemented
# MANDATORY: All tests must use existing test patterns from test_chat_api_basic.py

# GATE: New tests must pass
poetry run pytest tests/test_conversation_search.py -v
# 🚨 REQUIREMENT: 100% pass rate, no skipped tests
```

#### Step 2.2: Regression Testing (CRITICAL GATE)
```bash
# MANDATORY: ALL existing tests must continue passing
poetry run pytest tests/test_chat_api_basic.py -v
poetry run pytest tests/test_chat_integration.py -v  
poetry run pytest tests/test_chat_service_title_generation.py -v

# CRITICAL GATE: Complete test suite validation
poetry run pytest tests/ -v

# 🚨 STOP RULE: If ANY existing test fails, you MUST:
# 1. Investigate the root cause
# 2. Fix the breaking change  
# 3. Re-run all tests until 100% pass rate achieved
# 4. Only then proceed to Phase 3
```

### Phase 3: Documentation & Final Validation (GATE REQUIRED)

#### Step 3.1: OpenAPI Auto-Generation Verification (REQUIRED)
```bash
# Start application and verify documentation
docker compose up -d
sleep 10

# MANDATORY CHECKS:
curl -X GET "http://localhost:8000/openapi.json" | jq '.paths["/api/v1/chat/conversations"].get.parameters'
# 🚨 MUST contain "q" parameter with proper schema

# Manual verification required:
# 1. Visit http://localhost:8000/docs
# 2. Find GET /api/v1/chat/conversations endpoint
# 3. Verify "q" parameter visible with description
# 4. Test "Try it out" functionality with sample search
```

#### Step 3.2: End-to-End Workflow Test (FINAL GATE)
```bash
# Execute complete user workflow script from section 4.1
# ALL commands must succeed with exit code 0
# Test both title and content search scenarios
# Verify pagination and archive filtering combinations

# 🚨 FINAL GATE: Complete workflow must work end-to-end
# If ANY step fails: Fix issue and restart validation from Phase 1
```

### MANDATORY Test Execution Order

**Execute tests in this EXACT order - each phase gates the next:**

```bash
# Phase 1: Code Quality (MUST pass first)
poetry run ruff check app/api/v1/chat.py app/services/chat_service.py --fix
poetry run mypy app/api/v1/chat.py app/services/chat_service.py

# Phase 2: New Feature Tests (MUST pass before regression testing)
poetry run pytest tests/test_conversation_search.py -v

# Phase 3: Chat-Specific Regression Tests (MUST pass before full suite)
poetry run pytest tests/test_chat_api_basic.py tests/test_chat_integration.py -v

# Phase 4: Complete Regression Testing (FINAL GATE)
poetry run pytest tests/ -v

# Phase 5: Docker Environment Validation (PRODUCTION READINESS)
docker compose up -d postgres redis
docker compose exec app poetry run pytest tests/test_conversation_search.py -v
docker compose exec app poetry run pytest tests/ --maxfail=1
```

**🚨 FAILURE HANDLING PROTOCOL:**
- **Any Phase 1 failure**: Fix code quality issues immediately, do not proceed
- **Any Phase 2 failure**: Debug new search implementation, fix logic errors  
- **Any Phase 3 failure**: Investigate regression in existing chat functionality
- **Any Phase 4 failure**: Stop implementation, identify breaking changes across entire codebase
- **Any Phase 5 failure**: Environment or deployment issue, check Docker setup

## Anti-Patterns to Avoid
- ❌ Don't break existing API contracts - preserve all current parameters and behavior
- ❌ Don't implement complex full-text search without proper indexing
- ❌ Don't ignore empty query handling - should return all results like current behavior
- ❌ Don't skip security validation - search must respect user ownership
- ❌ Don't use synchronous database operations in async context
- ❌ Don't hardcode search logic - make it configurable for different search strategies
- ❌ Don't ignore performance implications of JOIN queries across large datasets

## Security Considerations

### Data Access Control
- **User Isolation**: Search results MUST only include conversations owned by the requesting user
- **Content Privacy**: Search should not leak information about conversations from other users
- **Query Sanitization**: Input validation prevents SQL injection via search terms

### Performance Security
- **Query Complexity**: Limit search query length to prevent resource exhaustion
- **Rate Limiting**: Existing rate limiting applies to search requests
- **Index Strategy**: Proper indexing prevents table scans that could impact performance

## Future Enhancements

1. **Advanced Search Operators**: Support for quotes, AND/OR logic, date ranges
2. **Search Highlighting**: Return matched text snippets with highlighting
3. **Search Analytics**: Track popular search terms for UX improvements
4. **Full-Text Search**: Upgrade to PostgreSQL's advanced full-text search capabilities
5. **Search Suggestions**: AI-powered search query suggestions based on conversation history