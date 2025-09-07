name: "Chat Integration Feature - Complete AI-Powered Conversational Interface with WebSocket Support"
description: |

## Purpose
Context-rich PRP for implementing a complete chat integration system with conversational AI, streaming responses, comprehensive conversation management, and WebSocket real-time capabilities. Designed for one-pass implementation with full validation loops and multi-phase approach.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Implement a complete chat integration system that provides AI-powered conversational assistance with real-time streaming, conversation persistence, comprehensive authentication, and seamless integration with existing customer support agents. Phase II will extend with WebSocket real-time capabilities for enhanced user experience.

## Why
- **Business Value**: Enable users to interact with AI support through natural conversation interface
- **User Experience**: Provide real-time streaming responses and WebSocket updates for better engagement
- **Integration**: Leverage existing Pydantic AI agents and MCP tools for intelligent responses
- **Architecture**: Extend current FastAPI/SQLAlchemy stack with chat capabilities and real-time features
- **Scalability**: WebSocket architecture supports multiple concurrent conversations

## What

### Phase I: REST API Foundation
A complete conversational AI REST API system with:
- Persistent conversation management (create, list, update, delete)
- Real-time message streaming using Server-Sent Events
- Integration with existing customer support AI agents
- Comprehensive JWT authentication with user isolation
- Database relationships with proper indexes and constraints

### Phase II: WebSocket Real-Time Architecture
Enhanced real-time capabilities with:
- WebSocket protocol handlers for bidirectional communication
- Redis pub/sub for cross-instance message broadcasting
- Protocol-based message routing system
- Real-time conversation updates and notifications
- Advanced MCP client integration for tool-based AI interactions

### Success Criteria
- [ ] **Phase I**: All 6 REST API endpoints matching OpenAPI specification exactly
- [ ] **Phase I**: Real-time streaming responses using SSE
- [ ] **Phase I**: Conversation persistence with user isolation
- [ ] **Phase I**: Integration with existing customer_support_agent
- [ ] **Phase I**: Complete test coverage (unit + integration)
- [ ] **Phase I**: Database migration without breaking changes
- [ ] **Phase II**: WebSocket protocol handlers with message routing
- [ ] **Phase II**: Redis pub/sub integration for scalability
- [ ] **Phase II**: Advanced MCP client integration
- [ ] **Phase II**: Real-time conversation updates via WebSocket
- [ ] Performance: <500ms response time for non-streaming endpoints
- [ ] Security: Proper JWT authentication and data isolation throughout

## All Needed Context

### Documentation & References (list all context needed to implement the feature)
```yaml
# MUST READ - Include these in your context window
- url: https://docs.python.org/3/library/asyncio.html
  why: Async patterns for streaming and concurrent operations
  
- url: https://fastapi.tiangolo.com/advanced/server-sent-events/
  why: Server-Sent Events implementation patterns with StreamingResponse
  
- url: https://fastapi.tiangolo.com/advanced/websockets/
  why: WebSocket implementation patterns and connection management
  
- url: https://docs.sqlalchemy.org/en/20/orm/relationships.html
  why: SQLAlchemy 2.0 relationship patterns for conversation/message models

- file: app/api/v1/tickets.py
  why: Existing API router patterns, pagination, filtering, and error handling
  
- file: app/models/ticket.py
  why: SQLAlchemy model patterns with enums, relationships, and base classes
  
- file: app/schemas/ticket.py
  why: Pydantic schema patterns with validation, responses, and requests

- file: app/services/ticket_service.py
  why: Service layer patterns for CRUD operations, filtering, and business logic

- file: app/agents/customer_support_agent.py
  why: AI agent integration patterns and response generation

- file: app/dependencies.py
  why: Authentication patterns and dependency injection for current_user

- file: app/models/base.py
  why: Base model patterns with TimestampMixin, UUIDMixin, and declarative base

- file: app/schemas/base.py
  why: Pydantic base schema patterns and configuration

- file: docs/example-chat.json
  why: Complete OpenAPI specification for exact endpoint contracts
  critical: All response schemas MUST match exactly - ConversationResponse, MessageResponse

# SHIPWELL REFERENCE PATTERNS (Phase II)
- file: /Users/aristotle/projects/shipwell_trade_compliance/backend/app/websocket/protocols/chat_protocol.py
  why: Complete WebSocket protocol handler with all chat operations and message routing
  critical: Authentication, conversation ownership validation, streaming patterns

- file: /Users/aristotle/projects/shipwell_trade_compliance/backend/app/websocket/manager.py  
  why: Redis-enabled WebSocket manager with pub/sub, connection management, and client tracking
  critical: Redis integration, client cleanup, notification types

- file: /Users/aristotle/projects/shipwell_trade_compliance/backend/app/services/mcp_client_service.py
  why: MCP client service with stdio transport and tool availability management
  critical: MCP client lifecycle, error handling, connection reset patterns

- file: /Users/aristotle/projects/shipwell_trade_compliance/backend/app/routes/chat.py
  why: Complete REST API endpoints with authentication, WebSocket endpoints, and timezone handling
  critical: JWT auth dependency injection, conversation ownership validation

- file: /Users/aristotle/projects/shipwell_trade_compliance/backend/app/models_chat.py
  why: Chat database models with proper indexes, foreign keys, and soft delete patterns
  critical: Performance indexes, audit fields, token tracking
```

### Current Codebase tree (run `tree` in the root of the project) to get an overview of the codebase
```bash
app/
├── agents/              # Pydantic AI agents (customer_support_agent.py)
├── api/v1/             # FastAPI route handlers (tickets.py patterns)
├── models/             # SQLAlchemy database models (ticket.py patterns)
├── schemas/            # Pydantic request/response schemas (ticket.py patterns)
├── services/           # Business logic layer (ticket_service.py patterns)
├── dependencies.py     # JWT auth with get_current_user
├── main.py            # Router registration patterns
└── database.py        # Async session management
```

### Desired Codebase tree with files to be added and responsibility of file
```bash
# Phase I: REST API Foundation
app/
├── models/
│   └── chat.py                    # DBConversation, DBMessage models with indexes
├── schemas/
│   └── chat.py                    # Chat request/response schemas matching OpenAPI
├── services/
│   └── chat_service.py           # Business logic for chat operations with user isolation
├── api/v1/
│   └── chat.py                   # REST API endpoints with JWT auth and SSE streaming
└── agents/
    └── chat_agent.py            # Specialized agent for chat responses

# Phase II: WebSocket Enhancement  
app/
├── websocket/
│   ├── __init__.py
│   ├── manager.py               # WebSocket connection manager with Redis pub/sub
│   ├── protocols/
│   │   ├── __init__.py
│   │   ├── base_protocol.py     # Abstract protocol handler base class
│   │   └── chat_protocol.py     # Chat-specific protocol handler
│   └── message_router.py        # Protocol message routing system
├── services/
│   └── mcp_chat_service.py      # Enhanced MCP integration for chat tools
└── api/v1/
    └── websockets.py            # WebSocket endpoint management

alembic/versions/
└── xxx_add_chat_models.py        # Migration for conversation/message tables with indexes

tests/
├── test_chat_api.py              # API endpoint tests
├── test_chat_service.py          # Service layer tests  
├── test_chat_models.py           # Model relationship tests
├── test_websocket_chat.py        # WebSocket protocol tests (Phase II)
└── test_mcp_integration.py       # MCP client integration tests (Phase II)
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: JWT Authentication with proper dependency injection
# Example: current_user: DBUser = Depends(get_current_active_user)
# PATTERN: Always validate conversation ownership with user_id filter

# CRITICAL: FastAPI StreamingResponse requires proper content-type
# Example: StreamingResponse must use "text/event-stream" for SSE
# PATTERN: Headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}

# CRITICAL: SQLAlchemy 2.0 async patterns with relationships
# Example: Use selectinload() for eager loading relationships in async context
# PATTERN: Always use async sessions with await db.execute(query)

# CRITICAL: Pydantic v2 model configuration
# Example: ConfigDict(from_attributes=True) required for ORM integration
# PATTERN: Use BaseResponse with UUIDMixin and TimestampMixin

# CRITICAL: UUID primary keys with postgresql dialect
# Example: Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
# PATTERN: Always use UUID strings in API responses

# CRITICAL: Datetime with timezone handling
# Example: datetime.now(timezone.utc) for consistent timestamps
# PATTERN: Store UTC, convert to user timezone in response

# CRITICAL: Async generator for SSE streaming  
# Example: Must yield strings ending with \n\n for proper SSE format
# PATTERN: data: {"content": "chunk"}\n\n for each chunk

# CRITICAL: WebSocket authentication before accept() (Phase II)
# Example: Authenticate token BEFORE calling await websocket.accept()
# PATTERN: Close with specific codes (1008) for auth failures

# CRITICAL: Redis pub/sub patterns for WebSocket scaling (Phase II)
# Example: Use RedisMessage dataclass for structured messaging
# PATTERN: Channel-based routing: "websocket:chat", "websocket:broadcast"

# CRITICAL: MCP client stdio transport initialization (Phase II)
# Example: MCPServerStdio(args=script.split(), cwd="/app")
# PATTERN: Connection lifecycle with reset_connection() for failures
```

## Implementation Blueprint

### Phase I: REST API Foundation

### Data models and structure

Create the core data models to ensure type safety, relationships, and consistency.
```python
# SQLAlchemy Models (app/models/chat.py):
class DBConversation(BaseModel):
    # UUID primary key, user relationship, title, timestamps
    # One-to-many relationship with DBMessage
    # Soft delete capability with deleted_at field
    # Performance indexes: user_id, updated_at, is_deleted
    # Audit fields: is_auditable, retention_days
    # Token tracking: total_tokens_used for cost management
    
class DBMessage(BaseModel):  
    # UUID primary key, conversation foreign key, role (user/assistant)
    # Content text field, timestamps, AI metadata
    # Index on conversation_id for efficient querying
    # AI response metadata: model_used, confidence_score
    # Entity references for trade compliance context

# Pydantic Schemas (app/schemas/chat.py):
class ConversationResponse(BaseResponse):
    # Matches OpenAPI spec exactly: id, title, created_at, updated_at, total_messages
    # CRITICAL: UUID fields as strings, datetime fields as ISO strings
    
class MessageResponse(BaseResponse):
    # Matches OpenAPI spec: id, role, content, created_at
    # AI metadata: confidence_score, entity_references, entity_links
    
class SendMessageRequest(BaseSchema):
    # Single message field with validation (min_length=1, max_length=10000)
    
class CreateConversationRequest(BaseSchema):
    # Optional title field matching schema constraints (max_length=500)
```

### Incremental Implementation Plan with Validation Gates

**⚠️ CRITICAL RULE: DO NOT PROCEED TO NEXT INCREMENT UNTIL ALL TESTS PASS**

Each increment must be fully validated before moving forward. Every step includes:
1. **Implementation** - Write the minimal code for this increment
2. **Validation** - Run specific tests and checks
3. **Gate Check** - All tests must pass before proceeding

```yaml
## PHASE I: REST API FOUNDATION

### INCREMENT 1.1: Basic Database Models (Foundation)
**Goal**: Create minimal conversation model with user relationship

IMPLEMENTATION:
CREATE app/models/chat.py:
  - ONLY DBConversation model with: id, user_id, title, created_at, updated_at
  - USE existing BaseModel, TimestampMixin, UUIDMixin patterns
  - ADD user_id foreign key: ForeignKey('users.id')
  - NO relationships yet, NO DBMessage model yet

MODIFY app/models/__init__.py:
  - ADD: from app.models.chat import DBConversation

VALIDATION COMMANDS:
```bash
# Syntax validation
poetry run ruff check app/models/chat.py --fix
poetry run mypy app/models/chat.py

# Import validation
poetry run python -c "from app.models.chat import DBConversation; print('✅ Import successful')"
poetry run python -c "from app.models import DBConversation; print('✅ Module import successful')"
```

GATE CHECK:
- [ ] No syntax or type errors
- [ ] Model can be imported without errors
- [ ] Model has all required fields: id, user_id, title, created_at, updated_at
- [ ] Foreign key relationship defined correctly

**🚫 STOP: Do not proceed until all checks pass**

---

### INCREMENT 1.2: Database Migration for Conversations
**Goal**: Create and apply migration for conversations table

IMPLEMENTATION:
EXECUTE migration creation:
  - poetry run alembic revision --autogenerate -m "Add chat conversations table"

VERIFY migration file contains:
  - conversations table creation
  - user_id foreign key constraint
  - proper column types and constraints

VALIDATION COMMANDS:
```bash
# Migration validation
poetry run alembic check
poetry run python -c "import alembic.command; print('✅ Alembic can load migration')"

# Apply migration
poetry run alembic upgrade head

# Verify table exists
poetry run python -c "
from app.database import engine
from sqlalchemy import inspect, text
inspector = inspect(engine)
tables = inspector.get_table_names()
assert 'chat_conversations' in tables, 'conversations table not found'
print('✅ Conversations table created')
"
```

GATE CHECK:
- [ ] Migration file created successfully
- [ ] Migration applies without errors
- [ ] conversations table exists in database
- [ ] Foreign key constraint on user_id exists
- [ ] All columns have correct types

**🚫 STOP: Do not proceed until migration is fully applied and validated**

---

### INCREMENT 1.3: Basic Conversation Schema
**Goal**: Create minimal Pydantic schema for conversation responses

IMPLEMENTATION:
CREATE app/schemas/chat.py:
  - ConversationResponse class ONLY
  - Fields: id (str), title (str), created_at (str), updated_at (str)
  - Inherit from BaseResponse pattern
  - NO other schemas yet

VALIDATION COMMANDS:
```bash
# Schema validation
poetry run ruff check app/schemas/chat.py --fix
poetry run mypy app/schemas/chat.py

# Schema instantiation test
poetry run python -c "
from app.schemas.chat import ConversationResponse
from datetime import datetime
import uuid

# Test schema creation
schema = ConversationResponse(
    id=str(uuid.uuid4()),
    title='Test',
    created_at=datetime.now().isoformat(),
    updated_at=datetime.now().isoformat()
)
print('✅ Schema validation successful')
print(f'Schema: {schema.model_dump()}')
"
```

GATE CHECK:
- [ ] Schema imports without errors
- [ ] Schema can be instantiated with test data
- [ ] All fields have correct types (str for id, datetime fields)
- [ ] Schema inherits from BaseResponse correctly

**🚫 STOP: Do not proceed until schema validation passes**

---

### INCREMENT 1.4: Basic Service Layer
**Goal**: Create minimal service with conversation creation and listing

IMPLEMENTATION:
CREATE app/services/chat_service.py:
  - ChatService class with TWO methods only:
    * create_conversation(db, user_id, title) -> DBConversation
    * list_conversations(db, user_id, offset=0, limit=20) -> Tuple[List[DBConversation], int]
  - CRITICAL: Always filter by user_id
  - NO AI integration yet, NO message handling yet

VALIDATION COMMANDS:
```bash
# Service validation
poetry run ruff check app/services/chat_service.py --fix
poetry run mypy app/services/chat_service.py

# Service functionality test
poetry run python -c "
import asyncio
from app.services.chat_service import ChatService
from app.database import get_db_session
from app.models import DBUser
from sqlalchemy.ext.asyncio import AsyncSession

async def test_service():
    chat_service = ChatService()
    
    # Test service instantiation
    print('✅ ChatService instantiated')
    
    # Verify methods exist
    assert hasattr(chat_service, 'create_conversation')
    assert hasattr(chat_service, 'list_conversations')
    print('✅ Required methods exist')

asyncio.run(test_service())
"
```

GATE CHECK:
- [ ] Service imports and instantiates without errors
- [ ] Both required methods exist with correct signatures
- [ ] Methods use async/await patterns
- [ ] User filtering is implemented in both methods

**🚫 STOP: Do not proceed until service layer validation passes**

---

### INCREMENT 1.5: Single API Endpoint (List Conversations)
**Goal**: Implement ONE endpoint with full authentication

IMPLEMENTATION:
CREATE app/api/v1/chat.py:
  - APIRouter setup with prefix="/chat", tags=["Chat Assistant"]
  - ONE endpoint only: GET /conversations
  - MUST use: current_user: DBUser = Depends(get_current_active_user)
  - Return List[ConversationResponse]
  - NO other endpoints yet

MODIFY app/main.py:
  - Import and register chat router
  - app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat Assistant"])

VALIDATION COMMANDS:
```bash
# API validation
poetry run ruff check app/api/v1/chat.py --fix
poetry run mypy app/api/v1/chat.py

# Router registration test
poetry run python -c "
from app.main import app
routes = [route.path for route in app.routes]
chat_routes = [r for r in routes if '/chat' in r]
assert len(chat_routes) > 0, 'Chat routes not registered'
print(f'✅ Chat routes registered: {chat_routes}')
"

# Authentication dependency test
poetry run python -c "
from app.api.v1.chat import router
from fastapi import Depends
from app.dependencies import get_current_active_user

# Find the list_conversations endpoint
for route in router.routes:
    if hasattr(route, 'path') and route.path == '/conversations':
        dependencies = route.dependant.dependencies
        auth_deps = [d for d in dependencies if 'get_current_active_user' in str(d.call)]
        assert len(auth_deps) > 0, 'Authentication dependency not found'
        print('✅ Authentication dependency validated')
        break
else:
    raise AssertionError('List conversations endpoint not found')
"
```

GATE CHECK:
- [ ] Chat router imports without errors
- [ ] Router is registered in main app
- [ ] List conversations endpoint exists at correct path
- [ ] Authentication dependency is properly configured
- [ ] Endpoint signature includes current_user parameter

**🚫 STOP: Do not proceed until single endpoint is fully validated**

---

### INCREMENT 1.6: First API Endpoint Test
**Goal**: Create and validate test for list conversations endpoint

IMPLEMENTATION:
CREATE tests/test_chat_api_basic.py:
  - Test class with authentication helper methods
  - TWO tests only:
    * test_list_conversations_requires_auth() - should return 401
    * test_list_conversations_with_auth() - should return 200 with empty list
  - Use existing TestClient patterns from other test files

VALIDATION COMMANDS:
```bash
# Test file validation
poetry run ruff check tests/test_chat_api_basic.py --fix
poetry run mypy tests/test_chat_api_basic.py

# Run the specific tests
poetry run pytest tests/test_chat_api_basic.py -v

# Verify test coverage
poetry run pytest tests/test_chat_api_basic.py -v --tb=short
```

TEST OUTPUT VALIDATION:
```
tests/test_chat_api_basic.py::test_list_conversations_requires_auth PASSED
tests/test_chat_api_basic.py::test_list_conversations_with_auth PASSED
```

GATE CHECK:
- [ ] Both tests pass successfully
- [ ] 401 response for unauthenticated request
- [ ] 200 response for authenticated request  
- [ ] Response has correct structure (list format)
- [ ] No test failures or errors

**🚫 STOP: Do not proceed until API tests pass completely**

---

### INCREMENT 1.7: Add Message Model and Relationship
**Goal**: Add message model with proper relationship to conversations

IMPLEMENTATION:
MODIFY app/models/chat.py:
  - ADD DBMessage model with: id, conversation_id, role, content, created_at
  - ADD relationship in DBConversation: messages = relationship("DBMessage", back_populates="conversation")
  - ADD relationship in DBMessage: conversation = relationship("DBConversation", back_populates="messages")
  - ADD total_messages property to DBConversation

MODIFY app/models/__init__.py:
  - ADD: from app.models.chat import DBConversation, DBMessage

VALIDATION COMMANDS:
```bash
# Model validation
poetry run ruff check app/models/chat.py --fix
poetry run mypy app/models/chat.py

# Relationship validation
poetry run python -c "
from app.models.chat import DBConversation, DBMessage
import inspect

# Check relationships exist
conv_attrs = dir(DBConversation)
assert 'messages' in conv_attrs, 'messages relationship missing from DBConversation'

msg_attrs = dir(DBMessage)
assert 'conversation' in msg_attrs, 'conversation relationship missing from DBMessage'

print('✅ Model relationships validated')
"

# Import validation
poetry run python -c "
from app.models import DBConversation, DBMessage
print('✅ Both models import successfully')
"
```

GATE CHECK:
- [ ] Both models import without errors
- [ ] Relationships are properly defined (back_populates)
- [ ] DBMessage has all required fields
- [ ] total_messages property exists on DBConversation
- [ ] No circular import issues

**🚫 STOP: Do not proceed until model relationships are validated**

---

### INCREMENT 1.8: Message Model Migration
**Goal**: Create and apply migration for messages table

IMPLEMENTATION:
EXECUTE migration creation:
  - poetry run alembic revision --autogenerate -m "Add chat messages table with relationships"

VERIFY migration includes:
  - chat_messages table creation
  - conversation_id foreign key
  - proper indexes for performance

VALIDATION COMMANDS:
```bash
# Migration validation
poetry run alembic check

# Apply migration
poetry run alembic upgrade head

# Verify tables and relationships
poetry run python -c "
from app.database import engine
from sqlalchemy import inspect, text
inspector = inspect(engine)

# Check both tables exist
tables = inspector.get_table_names()
assert 'chat_conversations' in tables, 'conversations table missing'
assert 'chat_messages' in tables, 'messages table missing'

# Check foreign key constraints
fks = inspector.get_foreign_keys('chat_messages')
conversation_fk = [fk for fk in fks if fk['constrained_columns'] == ['conversation_id']]
assert len(conversation_fk) > 0, 'conversation_id foreign key missing'

print('✅ Database migration successful')
print(f'Tables: {tables}')
"
```

GATE CHECK:
- [ ] Migration applies without errors
- [ ] Both tables exist in database
- [ ] Foreign key constraint from messages to conversations exists
- [ ] Indexes are created properly
- [ ] No constraint violations

**🚫 STOP: Do not proceed until message table migration is complete**

---

### INCREMENT 1.9: Complete Schemas
**Goal**: Add remaining schemas with proper validation

IMPLEMENTATION:
MODIFY app/schemas/chat.py:
  - ADD MessageResponse class
  - ADD CreateConversationRequest class  
  - ADD SendMessageRequest class
  - UPDATE ConversationResponse to include total_messages field
  - All schemas must match OpenAPI specification exactly

VALIDATION COMMANDS:
```bash
# Schema validation
poetry run ruff check app/schemas/chat.py --fix
poetry run mypy app/schemas/chat.py

# Schema functionality tests
poetry run python -c "
from app.schemas.chat import ConversationResponse, MessageResponse, CreateConversationRequest, SendMessageRequest
from datetime import datetime
import uuid

# Test all schemas
conv_resp = ConversationResponse(
    id=str(uuid.uuid4()),
    title='Test Chat',
    created_at=datetime.now().isoformat(),
    updated_at=datetime.now().isoformat(),
    total_messages=0
)

msg_resp = MessageResponse(
    id=str(uuid.uuid4()),
    role='user',
    content='Hello world',
    created_at=datetime.now().isoformat()
)

create_req = CreateConversationRequest(title='New Chat')
send_req = SendMessageRequest(message='Test message')

print('✅ All schemas validated successfully')
print(f'ConversationResponse: {conv_resp.model_dump()}')
print(f'MessageResponse: {msg_resp.model_dump()}')
"
```

GATE CHECK:
- [ ] All schemas import and instantiate without errors
- [ ] Schemas match OpenAPI specification exactly
- [ ] Field types are correct (str, int, Optional fields)
- [ ] Validation works for required vs optional fields
- [ ] No pydantic validation errors

**🚫 STOP: Do not proceed until all schemas are validated**

---

### INCREMENT 1.10: Complete Service Layer
**Goal**: Add remaining service methods with message handling

IMPLEMENTATION:
MODIFY app/services/chat_service.py:
  - ADD get_conversation(db, conversation_id, user_id) -> Optional[DBConversation]
  - ADD get_conversation_messages(db, conversation_id, user_id) -> List[DBMessage]
  - ADD send_message(db, conversation_id, user_id, content) -> DBMessage
  - CRITICAL: All methods must validate user ownership
  - NO AI integration yet - just save user message and return it

VALIDATION COMMANDS:
```bash
# Service validation
poetry run ruff check app/services/chat_service.py --fix
poetry run mypy app/services/chat_service.py

# Service method validation
poetry run python -c "
from app.services.chat_service import ChatService
import inspect

service = ChatService()
methods = ['create_conversation', 'list_conversations', 'get_conversation', 
          'get_conversation_messages', 'send_message']

for method in methods:
    assert hasattr(service, method), f'Method {method} missing'
    sig = inspect.signature(getattr(service, method))
    assert 'user_id' in sig.parameters, f'Method {method} missing user_id parameter'

print('✅ All service methods validated')
print(f'Available methods: {[m for m in dir(service) if not m.startswith(\"_\")]}')
"
```

GATE CHECK:
- [ ] All required service methods exist
- [ ] All methods have user_id parameter for security
- [ ] Methods use proper async/await patterns
- [ ] Type hints are correct
- [ ] User ownership validation is implemented

**🚫 STOP: Do not proceed until service layer is complete**

---

### INCREMENT 1.11: Add Create Conversation Endpoint
**Goal**: Add second API endpoint with full testing

IMPLEMENTATION:
MODIFY app/api/v1/chat.py:
  - ADD POST /conversations endpoint
  - Use CreateConversationRequest schema
  - Return ConversationResponse
  - Include authentication dependency

VALIDATION COMMANDS:
```bash
# API validation
poetry run ruff check app/api/v1/chat.py --fix
poetry run mypy app/api/v1/chat.py

# Endpoint registration test
poetry run python -c "
from app.api.v1.chat import router

# Check both endpoints exist
paths = [route.path for route in router.routes if hasattr(route, 'path')]
assert '/conversations' in paths, 'List conversations endpoint missing'

post_routes = [route for route in router.routes 
              if hasattr(route, 'methods') and 'POST' in route.methods]
assert len(post_routes) > 0, 'POST endpoint missing'

print('✅ Both endpoints registered')
print(f'Available paths: {paths}')
"
```

ADD TO tests/test_chat_api_basic.py:
  - test_create_conversation_requires_auth()
  - test_create_conversation_with_auth()
  - test_create_conversation_with_title()

VALIDATION COMMANDS:
```bash
# Run expanded tests
poetry run pytest tests/test_chat_api_basic.py -v

# Specific test validation
poetry run pytest tests/test_chat_api_basic.py::test_create_conversation_with_auth -v
```

GATE CHECK:
- [ ] New endpoint exists and is registered
- [ ] All tests pass (5 total tests now)
- [ ] Create endpoint requires authentication
- [ ] Create endpoint returns correct response format
- [ ] Database persistence works correctly

**🚫 STOP: Do not proceed until create endpoint is fully tested**

---

### INCREMENT 1.12: Add Message-Related Endpoints
**Goal**: Add message endpoints with proper testing

IMPLEMENTATION:
MODIFY app/api/v1/chat.py:
  - ADD GET /conversations/{conversation_id}/messages
  - ADD POST /conversations/{conversation_id}/messages  
  - Both with authentication and ownership validation
  - Use proper schemas and error handling

VALIDATION COMMANDS:
```bash
# API validation
poetry run ruff check app/api/v1/chat.py --fix
poetry run mypy app/api/v1/chat.py

# Endpoint count validation
poetry run python -c "
from app.api.v1.chat import router

routes_with_paths = [route for route in router.routes if hasattr(route, 'path')]
print(f'Total endpoints: {len(routes_with_paths)}')
assert len(routes_with_paths) >= 4, f'Expected at least 4 endpoints, got {len(routes_with_paths)}'

# Check message-related paths exist
paths = [route.path for route in routes_with_paths]
message_paths = [p for p in paths if 'messages' in p]
assert len(message_paths) >= 2, f'Expected message endpoints, got {message_paths}'

print('✅ Message endpoints validated')
print(f'All paths: {paths}')
"
```

ADD TO tests/test_chat_api_basic.py:
  - test_get_messages_requires_auth()
  - test_get_messages_conversation_not_found()
  - test_send_message_requires_auth()
  - test_send_message_with_auth()

VALIDATION COMMANDS:
```bash
# Run all API tests
poetry run pytest tests/test_chat_api_basic.py -v

# Verify test count
poetry run pytest tests/test_chat_api_basic.py --collect-only -q | grep "test_" | wc -l
```

GATE CHECK:
- [ ] Message endpoints exist and are registered
- [ ] All tests pass (9+ total tests now)
- [ ] Conversation ownership validation works
- [ ] Messages are properly stored and retrieved
- [ ] Error handling for non-existent conversations works

**🚫 STOP: Do not proceed until message endpoints are fully tested**

---

### INCREMENT 1.13: Add Remaining CRUD Endpoints
**Goal**: Complete REST API with update and delete endpoints

IMPLEMENTATION:
MODIFY app/api/v1/chat.py:
  - ADD PATCH /conversations/{conversation_id}/title
  - ADD DELETE /conversations/{conversation_id}
  - Both with authentication and ownership validation
  - Use proper schemas and soft delete pattern

ADD TO tests/test_chat_api_basic.py:
  - test_update_title_requires_auth()
  - test_update_title_conversation_not_found()
  - test_update_title_success()
  - test_delete_conversation_requires_auth()
  - test_delete_conversation_success()

VALIDATION COMMANDS:
```bash
# Complete API validation
poetry run ruff check app/api/v1/chat.py --fix
poetry run mypy app/api/v1/chat.py

# Full endpoint count check
poetry run python -c "
from app.api.v1.chat import router

routes_with_paths = [route for route in router.routes if hasattr(route, 'path')]
print(f'Total endpoints: {len(routes_with_paths)}')

# Should have 6 total endpoints (excluding SSE streaming)
expected_methods = ['GET', 'POST', 'PATCH', 'DELETE']
method_counts = {}

for route in routes_with_paths:
    if hasattr(route, 'methods'):
        for method in route.methods:
            method_counts[method] = method_counts.get(method, 0) + 1

print(f'Method distribution: {method_counts}')
assert len(routes_with_paths) >= 5, f'Expected at least 5 endpoints'
print('✅ All CRUD endpoints validated')
"

# Run comprehensive tests
poetry run pytest tests/test_chat_api_basic.py -v

# Check final test count
TEST_COUNT=$(poetry run pytest tests/test_chat_api_basic.py --collect-only -q | grep "test_" | wc -l)
echo "Total tests: $TEST_COUNT"
```

GATE CHECK:
- [ ] All 6 main endpoints exist (list, create, get messages, send message, update title, delete)
- [ ] All tests pass (13+ total tests)
- [ ] Update and delete require proper authentication
- [ ] Ownership validation works for all endpoints
- [ ] Soft delete is implemented correctly

**🚫 STOP: Do not proceed until full REST API is validated**

---

### INCREMENT 1.14: Add SSE Streaming Endpoint
**Goal**: Implement Server-Sent Events streaming with proper testing

IMPLEMENTATION:
MODIFY app/api/v1/chat.py:
  - ADD GET /conversations/{conversation_id}/stream
  - Implement StreamingResponse with proper SSE format
  - Mock streaming response for now (no AI yet)
  - Include authentication and ownership validation

MODIFY app/services/chat_service.py:
  - ADD mock_stream_response method that yields chunks
  - Simple word-by-word streaming simulation

VALIDATION COMMANDS:
```bash
# API validation
poetry run ruff check app/api/v1/chat.py app/services/chat_service.py --fix
poetry run mypy app/api/v1/chat.py app/services/chat_service.py

# SSE endpoint validation
poetry run python -c "
from app.api.v1.chat import router

# Find streaming endpoint
streaming_routes = []
for route in router.routes:
    if hasattr(route, 'path') and 'stream' in route.path:
        streaming_routes.append(route)

assert len(streaming_routes) > 0, 'Streaming endpoint not found'
print(f'✅ Streaming endpoint found: {[r.path for r in streaming_routes]}')
"
```

CREATE tests/test_chat_streaming.py:
  - test_streaming_requires_auth()
  - test_streaming_conversation_not_found()
  - test_streaming_response_format()
  - test_streaming_content_type()

VALIDATION COMMANDS:
```bash
# Run streaming tests
poetry run pytest tests/test_chat_streaming.py -v

# Verify SSE format
poetry run pytest tests/test_chat_streaming.py::test_streaming_response_format -v -s
```

GATE CHECK:
- [ ] Streaming endpoint exists and is registered
- [ ] All streaming tests pass
- [ ] SSE format is correct (data: prefix, \n\n endings)
- [ ] Content-type is text/event-stream
- [ ] Authentication and ownership validation work for streaming

**🚫 STOP: Do not proceed until SSE streaming is fully validated**

---

### INCREMENT 1.15: Integration Test Suite
**Goal**: Create comprehensive integration tests

IMPLEMENTATION:
CREATE tests/test_chat_integration.py:
  - test_full_conversation_lifecycle()
  - test_multiple_users_isolation()
  - test_conversation_with_messages_flow()
  - test_streaming_with_real_conversation()

VALIDATION COMMANDS:
```bash
# Run all chat-related tests
poetry run pytest tests/test_chat_*.py -v

# Run integration tests specifically
poetry run pytest tests/test_chat_integration.py -v

# Check total test coverage
poetry run pytest tests/test_chat_*.py --collect-only -q | grep "test_" | wc -l
```

FINAL PHASE I VALIDATION:
```bash
# Complete test suite
poetry run pytest tests/test_chat_*.py -v --tb=short

# API validation with Docker
docker compose up -d
sleep 10

# Manual API testing
curl -X GET http://localhost:8000/api/v1/chat/conversations
curl -X POST http://localhost:8000/api/v1/chat/conversations \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Chat"}'

docker compose down
```

GATE CHECK FOR PHASE I COMPLETION:
- [ ] All unit tests pass (20+ tests total)
- [ ] All integration tests pass
- [ ] Manual API testing works
- [ ] All 6 REST endpoints function correctly
- [ ] Authentication works throughout
- [ ] User isolation is enforced
- [ ] SSE streaming works properly
- [ ] Database migrations are clean

**🎯 PHASE I COMPLETE: Ready for Phase II WebSocket Implementation**

## PHASE II: WEBSOCKET REAL-TIME ARCHITECTURE

### INCREMENT 2.1: WebSocket Base Infrastructure
[Similar incremental approach for Phase II...]

```

### Per task pseudocode as needed added to each task

```python
# Task 5: JWT-Authenticated API Endpoints
router = APIRouter(prefix="/chat", tags=["Chat Assistant"])

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: DBUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    pagination: PaginationParams = Depends()
):
    # CRITICAL: Always filter by current_user.id for security
    conversations, total = await chat_service.list_conversations(
        db=db,
        user_id=current_user.id,
        offset=pagination.offset,
        limit=pagination.limit
    )
    
    # PATTERN: Return paginated response matching existing API patterns
    return PaginatedResponse(
        items=[ConversationResponse.from_orm(conv) for conv in conversations],
        total=total,
        offset=pagination.offset,
        limit=pagination.limit
    )

@router.get("/conversations/{conversation_id}/stream")
async def stream_conversation_response(
    conversation_id: UUID,
    message: str = Query(..., min_length=1, max_length=10000),
    current_user: DBUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    # CRITICAL: Validate conversation ownership BEFORE streaming
    conversation = await chat_service.get_conversation(
        db=db, 
        conversation_id=conversation_id, 
        user_id=current_user.id
    )
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # PATTERN: SSE streaming with proper content type and headers
    async def event_stream():
        try:
            # PATTERN: Stream AI response in chunks  
            async for chunk in chat_agent.stream_response(message, conversation_context):
                # CRITICAL: SSE format requires data: prefix and double newline
                yield f"data: {json.dumps({'content': chunk, 'type': 'chunk'})}\n\n"
                
            # CRITICAL: Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'error': 'Streaming failed'})}\n\n"
    
    # CRITICAL: FastAPI StreamingResponse with proper headers
    return StreamingResponse(
        event_stream(), 
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

# Task 10: Chat Protocol WebSocket Handler (Phase II)
class ChatProtocol(BaseProtocol):
    async def _handle_send_message(self, client_id: str, message: Dict[str, Any], user: DBUser, db):
        # CRITICAL: Validate conversation ownership
        conversation_id = message.get("conversation_id")
        conversation = db.query(DBConversation).filter_by(
            id=conversation_id,
            user_id=str(user.id),
            deleted_at=None
        ).first()
        
        if not conversation:
            await self.send_error_response(client_id, "Conversation not found", "send_message")
            return
        
        # PATTERN: Integrate with existing chat service
        response = await chat_service.send_message_with_ai(
            db=db,
            conversation_id=conversation_id,
            message=message.get("content"),
            user=user
        )
        
        # PATTERN: Send structured response via WebSocket
        await self.send_success_response(client_id, {
            "type": "message_response",
            "conversation_id": conversation_id,
            "content": response.content,
            "confidence": response.confidence,
            "message_id": str(response.id)
        }, NotificationType.CHAT_RESPONSE)
        
        # PATTERN: Broadcast to other clients in conversation room via Redis
        await self.broadcast_message({
            "type": "new_message",
            "conversation_id": conversation_id,
            "user_id": str(user.id),
            "content": message.get("content")
        }, "websocket:chat", exclude_client=client_id)
```

### Integration Points
```yaml
AUTHENTICATION:
  - dependency: get_current_active_user from app.dependencies
  - pattern: "current_user: DBUser = Depends(get_current_active_user)" in every endpoint
  - validation: Always filter database queries by current_user.id
  
DATABASE:
  - migration: "Add conversations and messages tables with proper foreign keys"
  - indexes: "CREATE INDEX idx_conversation_user_updated ON conversations(user_id, updated_at DESC)"
  - relationships: "One-to-many from conversations to messages with CASCADE delete"
  
CONFIG:
  - add to: app/config/ai_config.yaml  
  - pattern: "chat_agent configuration with streaming capabilities"
  - redis: Redis URL configuration for WebSocket pub/sub (Phase II)
  
ROUTES:
  - add to: app/main.py
  - pattern: "app.include_router(chat_router, prefix='/api/v1/chat', tags=['Chat Assistant'])"
  - websocket: WebSocket routes registration (Phase II)
  
AI_AGENTS:
  - extend: app/agents/customer_support_agent.py patterns
  - specialize: Conversational responses vs ticket creation
  - context: Include conversation history for better responses
  - mcp: Enhanced MCP tool integration (Phase II)
  
WEBSOCKET (Phase II):
  - manager: Redis-enabled connection management
  - protocols: Protocol-based message routing
  - authentication: JWT validation before WebSocket acceptance
  - rooms: Conversation-based client grouping for targeted updates
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
poetry run ruff check app/models/chat.py app/schemas/chat.py app/services/chat_service.py app/api/v1/chat.py --fix
poetry run mypy app/models/chat.py app/schemas/chat.py app/services/chat_service.py app/api/v1/chat.py

# Phase II validation
poetry run ruff check app/websocket/ app/services/mcp_chat_service.py --fix
poetry run mypy app/websocket/ app/services/mcp_chat_service.py

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests each new feature/file/function use existing test patterns
```python
# CREATE tests/test_chat_api.py with authentication:
def test_list_conversations_requires_auth():
    """Test conversation listing requires valid JWT token"""
    response = client.get("/api/v1/chat/conversations")
    assert response.status_code == 401

def test_list_conversations_with_auth():
    """Test conversation listing with valid authentication"""  
    # Create test user and get JWT token
    token = create_test_user_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/v1/chat/conversations", headers=headers)
    assert response.status_code == 200
    assert "items" in response.json()

def test_conversation_ownership_isolation():
    """Test users can only access their own conversations"""
    # Create two different users
    user1_token = create_test_user_token("user1@test.com")
    user2_token = create_test_user_token("user2@test.com")
    
    # Create conversation as user1
    conv_resp = client.post(
        "/api/v1/chat/conversations",
        json={"title": "User1 Conversation"},
        headers={"Authorization": f"Bearer {user1_token}"}
    )
    conversation_id = conv_resp.json()["id"]
    
    # Try to access as user2 - should fail
    response = client.get(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {user2_token}"}
    )
    assert response.status_code == 404  # Not found due to ownership filter

def test_streaming_endpoint_authentication():
    """Test streaming endpoint requires authentication"""
    response = client.get("/api/v1/chat/conversations/test-id/stream?message=hello")
    assert response.status_code == 401

def test_streaming_endpoint_format():
    """Test streaming endpoint returns proper SSE format"""
    token = create_test_user_token()
    conversation = create_test_conversation(token)
    
    with client.stream(
        "GET", 
        f"/api/v1/chat/conversations/{conversation['id']}/stream?message=test",
        headers={"Authorization": f"Bearer {token}"}
    ) as response:
        assert response.headers["content-type"] == "text/event-stream"
        # Verify SSE format with data: prefix
        content = response.content.decode()
        assert "data: " in content
        assert "\n\n" in content

# CREATE tests/test_websocket_chat.py (Phase II):
@pytest.mark.asyncio
async def test_websocket_authentication():
    """Test WebSocket requires valid JWT token"""
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/chat") as websocket:
                # Should disconnect due to missing token
                pass

@pytest.mark.asyncio  
async def test_websocket_protocol_handling():
    """Test WebSocket protocol message routing"""
    token = create_test_user_token()
    conversation = create_test_conversation(token)
    
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/chat?token={token}") as websocket:
            # Test send_message protocol
            websocket.send_json({
                "type": "send_message",
                "conversation_id": conversation["id"],
                "content": "Hello AI"
            })
            
            response = websocket.receive_json()
            assert response["type"] == "message_response"
            assert "content" in response["data"]
```

```bash
# Run and iterate until passing:
poetry run pytest tests/test_chat_models.py tests/test_chat_service.py tests/test_chat_api.py -v

# Phase II WebSocket tests
poetry run pytest tests/test_websocket_chat.py tests/test_mcp_integration.py -v

# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test
```bash
# Start the service
docker compose up -d

# Test authenticated endpoints in sequence
export TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass"}' | jq -r .access_token)

# Test conversation creation with authentication
curl -X POST http://localhost:8000/api/v1/chat/conversations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Chat"}'

# Expected: {"id": "uuid", "title": "Test Chat", "created_at": "...", "updated_at": "...", "total_messages": 0}

# Test conversation listing with authentication
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/chat/conversations

# Expected: {"items": [...], "total": 1, "offset": 0, "limit": 20}

# Test streaming endpoint with authentication
curl -N -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/chat/conversations/{id}/stream?message=Hello"

# Expected: Server-sent events with data: prefix

# Test WebSocket connection (Phase II)
wscat -c "ws://localhost:8000/ws/chat?token=$TOKEN"
# Send: {"type": "create_conversation", "title": "WebSocket Test"}
# Expected: {"type": "notification", "notification_type": "conversation_update", ...}
```

## Final validation Checklist
- [ ] **Authentication**: All endpoints require valid JWT tokens
- [ ] **User Isolation**: Users can only access their own conversations
- [ ] **All tests pass**: `poetry run pytest tests/test_chat_*.py -v`
- [ ] **No linting errors**: `poetry run ruff check app/models/chat.py app/schemas/chat.py app/services/chat_service.py app/api/v1/chat.py`
- [ ] **No type errors**: `poetry run mypy app/models/chat.py app/schemas/chat.py app/services/chat_service.py app/api/v1/chat.py`
- [ ] **Migration applies cleanly**: `poetry run alembic upgrade head`
- [ ] **Manual test successful**: All 6 REST endpoints return expected responses with proper authentication
- [ ] **SSE streaming works**: Browser receives properly formatted events with authentication
- [ ] **User isolation verified**: Database queries properly filter by user_id
- [ ] **AI integration working**: Messages receive intelligent responses
- [ ] **Performance acceptable**: Non-streaming endpoints respond <500ms
- [ ] **Error cases handled gracefully**: 401 (auth), 404 (ownership), 422 (validation), 500 responses
- [ ] **WebSocket authentication**: JWT validation before WebSocket acceptance (Phase II)
- [ ] **Protocol handling**: Message routing works correctly (Phase II)
- [ ] **Redis integration**: Pub/sub messaging functions (Phase II)
- [ ] **MCP client integration**: Tool-based AI responses work (Phase II)
- [ ] **Logs are informative but not verbose**: Appropriate logging levels throughout

---

## Anti-Patterns to Avoid
- ❌ **Don't skip authentication** - Every endpoint MUST require valid JWT token via get_current_active_user
- ❌ **Don't skip user isolation checks** - Always filter database queries by current_user.id
- ❌ **Don't ignore conversation ownership** - Validate user owns conversation before any operation
- ❌ **Don't ignore SSE format requirements** - Must use data: prefix and \n\n
- ❌ **Don't use sync functions in async context** - Use async/await throughout
- ❌ **Don't hardcode conversation limits** - Use pagination patterns from existing APIs
- ❌ **Don't catch all exceptions** - Be specific about error types and return appropriate HTTP codes
- ❌ **Don't forget to commit database transactions** - Always await db.commit() after changes
- ❌ **Don't skip relationship loading** - Use selectinload() for performance
- ❌ **Don't create circular imports** - Keep clear separation between services and models
- ❌ **Don't ignore OpenAPI specification** - Responses must match exactly
- ❌ **Don't authenticate after WebSocket accept** - JWT validation BEFORE await websocket.accept() (Phase II)
- ❌ **Don't ignore Redis connection failures** - Graceful degradation when Redis unavailable (Phase II)
- ❌ **Don't skip MCP client error handling** - Proper fallbacks when MCP tools unavailable (Phase II)

## Phase II: WebSocket Architecture Benefits

### Real-Time Capabilities
- **Bidirectional Communication**: WebSocket enables instant message exchange
- **Live Conversation Updates**: Real-time notifications for message delivery and typing indicators
- **Multi-Client Synchronization**: Changes in one client instantly reflected in others
- **Connection Persistence**: Maintain long-lived connections for better performance

### Scalability Features
- **Redis Pub/Sub Integration**: Cross-instance message broadcasting for horizontal scaling
- **Protocol-Based Routing**: Modular message handling with protocol-specific handlers
- **Connection Management**: Efficient client lifecycle and resource cleanup
- **Room-Based Messaging**: Conversation-specific message targeting

### Enhanced MCP Integration
- **Tool-Based Responses**: Direct integration with trade compliance tools
- **Streaming Tool Responses**: Real-time tool execution feedback
- **Error Handling**: Graceful fallbacks when tools unavailable
- **Connection Lifecycle**: Automatic MCP client management and recovery

## Confidence Score: 9/10
This PRP provides comprehensive context for both REST API foundation and WebSocket enhancement phases. It follows existing patterns precisely, includes executable validation steps, addresses authentication requirements throughout, and provides detailed WebSocket architecture guidance based on proven Shipwell implementation patterns. The two-phase approach ensures progressive success with full validation at each stage.