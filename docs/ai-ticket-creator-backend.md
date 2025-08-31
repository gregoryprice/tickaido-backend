name: "AI Ticket Creator Backend API - Complete Implementation PRP"
description: |

## Purpose
Comprehensive PRP for implementing a complete backend API for AI Ticket Creator Chrome extension with ticket management, AI automation, third-party integrations, and file attachment capabilities.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Progressive Success**: Start simple, test and validate with actual API calls and test cases, then enhance
4. **Global rules**: You must follow all rules in CLAUDE.md

---

## Goal
Build a production-ready FastAPI backend service for the AI Ticket Creator Chrome extension that provides comprehensive ticket management with AI-powered automation, third-party integrations (Salesforce, Jira, Zendesk, GitHub, Slack, Teams), file attachment capabilities with AI transcription for supported formats, and real-time notifications.

## Why
- **Business value**: Streamline support ticket creation and management with AI automation
- **User impact**: Enable seamless ticket creation from browser with context capture
- **Integration value**: Connect all major business tools in unified workflow
- **AI automation**: Reduce manual categorization and routing work
- **Chrome extension support**: Provide robust backend for published Chrome extension

## What
A FastAPI backend service with:
- REST API for normalized ticket CRUD operations
- **AI-powered customer support agent with configurable prompts for ticket creation**
- AI-powered ticket categorization, priority assignment, and routing using **Pydantic AI agents**
- **MCP server providing tools for the AI agent** (file analysis, integration APIs, etc.)
- File attachment system supporting all file types (documents, images, videos, audio, etc.)
- AI transcription for audio/video files and OCR for image files
- File attachment to third-party integration tickets using each platform's native API
- Real-time WebSocket notifications for file processing status and ticket updates
- Third-party integrations (Salesforce, Jira, Zendesk, Intercom, GitHub, Slack, Teams)
- **Dynamic AI configuration management endpoint** for updating prompts, models, and parameters
- Analytics and reporting endpoints for basic health, reporting
- JWT-based authentication with role-based access control

### Success Criteria
- [ ] All API endpoints documented with OpenAPI/Redocly
- [ ] Complete test suite with 99%+ coverage
- [ ] All third-party integrations working with proper error handling
- [ ] AI transcription pipeline processing audio/video files and OCR for images
- [ ] Pydantic AI agents working with MCP server integration
- [ ] AI configuration management endpoint for dynamic prompt updates
- [ ] Real-time notifications via WebSocket
- [ ] Docker containerization with compose setup
- [ ] Production-ready configuration management

## All Needed Context

### Documentation & References (list all context needed to implement the feature)
```yaml
# MUST READ - Include these in your context window
- url: https://fastapi.tiangolo.com/tutorial/
  why: FastAPI fundamentals, dependency injection, background tasks
  
- file: /Users/aristotle/projects/shipwell_trade_compliance/backend/app/main.py
  why: Example FastAPI application structure with middleware, CORS, route organization
  
- file: /Users/aristotle/projects/shipwell_trade_compliance/backend/config/ai_config.yaml
  why: AI configuration pattern to follow exactly - critical for AI features
  
- url: https://testdriven.io/blog/fastapi-and-celery/
  section: Asynchronous Tasks with FastAPI and Celery
  critical: Background job patterns for file processing, AI transcription, third-party API calls
  
- url: https://developer.chrome.com/docs/extensions/how-to/web-platform/screen-capture
  section: Audio recording and screen capture
  critical: Understanding Chrome extension file upload data formats
  
- url: https://deepgram.com/learn/live-transcription-fastapi
  why: AI transcription implementation patterns with FastAPI
  
- file: /Users/aristotle/projects/shipwell_trade_compliance/pyproject.toml
  why: Poetry dependency management pattern to follow
  
- file: /Users/aristotle/projects/shipwell_trade_compliance/backend/Dockerfile
  why: Docker containerization pattern to follow exactly
  
- url: https://github.com/Redocly/redoc
  why: OpenAPI documentation generation requirements
```

### Current Codebase tree (run `tree` in the root of the project) to get an overview of the codebase
```bash
.
├── .claude/
│   ├── commands/
│   │   ├── generate-prp.md
│   │   └── execute-prp.md
├── docs/
│   ├── INITIAL.md
│   └── PRPs/
│       └── prp_base.md
├── CLAUDE.md
└── README.md
```

### Desired Codebase tree with files to be added and responsibility of file
```bash
.
├── .claude/                         # Claude Code commands
├── app/                            # FastAPI application (no nested backend)
│   ├── __init__.py
│   ├── main.py                     # FastAPI app initialization, middleware, routes
│   ├── config/                     # Configuration management
│   │   ├── __init__.py
│   │   ├── ai_config.yaml          # AI providers, models, settings
│   │   └── settings.py             # Pydantic settings management
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base.py                # Base model class
│   │   ├── ticket.py              # Ticket model
│   │   ├── user.py                # User model
│   │   ├── integration.py         # Third-party integration models
│   │   └── file.py                # File attachment models
│   ├── schemas/                   # Pydantic schemas for API
│   │   ├── __init__.py
│   │   ├── ticket.py              # Ticket request/response schemas
│   │   ├── user.py                # User schemas
│   │   └── file.py                # File attachment schemas
│   ├── routes/                    # API endpoints
│   │   ├── __init__.py
│   │   ├── tickets.py             # Ticket CRUD operations
│   │   ├── auth.py                # Authentication endpoints
│   │   ├── integrations.py        # Third-party integration endpoints
│   │   ├── files.py               # File upload/processing endpoints
│   │   ├── analytics.py           # Analytics and reporting
│   │   └── websocket.py           # Real-time notifications
│   ├── services/                  # Business logic services
│   │   ├── __init__.py
│   │   ├── ticket_service.py      # Ticket management logic
│   │   ├── ai_service.py          # AI categorization, transcription, OCR
│   │   ├── integration_service.py # Third-party API clients
│   │   ├── file_service.py        # File processing, transcription, OCR
│   │   └── notification_service.py # WebSocket notifications
│   ├── tasks/                     # Celery background tasks
│   │   ├── __init__.py
│   │   ├── file_processing.py     # Background file transcription/OCR
│   │   ├── integration_sync.py    # Third-party data sync
│   │   └── ai_tasks.py            # AI processing tasks
│   ├── middleware/                # Custom middleware
│   │   ├── __init__.py
│   │   ├── auth_middleware.py     # JWT authentication
│   │   └── rate_limiting.py       # API rate limiting
│   ├── websocket/                 # WebSocket protocol architecture
│   │   ├── protocols/
│   │   │   ├── base_protocol.py   # Abstract base class with utilities
│   │   │   ├── ticket_protocol.py # Ticket-specific messages  
│   │   │   └── file_protocol.py   # File processing messages
│   │   ├── manager.py             # Redis WebSocket manager
│   │   ├── message_router.py      # Routes messages to protocols
│   │   └── redis_pubsub.py       # Redis pub/sub integration
│   ├── database.py                # Database connection, session management
│   ├── celery_app.py             # Celery configuration
│   └── dependencies.py            # FastAPI dependency injection
├── alembic/                       # Database migrations
│   ├── env.py
│   └── versions/
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── conftest.py                # Pytest configuration, fixtures
│   ├── test_tickets.py            # Ticket API tests
│   ├── test_integrations.py       # Integration tests
│   ├── test_ai_service.py         # AI service tests
│   ├── test_files.py              # File processing tests
│   ├── test_websocket_protocols.py # WebSocket protocol tests
│   ├── test_ticket_protocol.py    # Ticket protocol specific tests
│   └── test_file_protocol.py      # File protocol specific tests
├── Dockerfile                     # Docker container definition
├── alembic.ini                    # Alembic configuration
├── compose.yml                    # Multi-service orchestration (modern Docker Compose)
├── pyproject.toml                 # Poetry dependencies, project config
├── .env.example                   # Environment variables template
├── .gitignore                    # Git ignore patterns
├── openapi.json                   # Generated OpenAPI specification
└── redocly.yaml                   # Redocly documentation configuration
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: FastAPI requires async functions for background tasks
# Example: Use async def for all endpoint handlers processing uploads

# CRITICAL: Celery tasks must be JSON serializable
# Example: Pass file paths/IDs to tasks, not file objects

# CRITICAL: SQLAlchemy 2.0 uses different session patterns
# Example: Use async sessions consistently throughout

# CRITICAL: Chrome extension sends multipart/form-data for file uploads
# Example: Use FastAPI's UploadFile for handling all file types

# CRITICAL: AI providers have rate limits and timeout requirements
# Example: Implement fallback chains and retry logic as in ai_config.yaml

# CRITICAL: WebSocket connections require proper lifecycle management
# Example: Handle connection drops, reconnection logic
# Example: MUST use Redis pub/sub architecture for scalability

# CRITICAL: WebSocket message protocols MUST follow exact structure
# Example: All messages require {"type": "message_type", "data": {...}}
# Example: Response messages include protocol, timestamp, success/error fields

# CRITICAL: Third-party APIs require webhook verification
# Example: Implement signature validation for Slack, GitHub webhooks

# CRITICAL: Poetry requires exact Python version matching - NO pip allowed
# Example: Use python = ">=3.12,<4.0" pattern from example project
# Example: NEVER use pip commands, only use poetry add/install/remove

# CRITICAL: Pydantic AI agents MUST use MCP server integration
# Example: Use pydantic_ai.Agent with MCP tools for ticket creation
# Example: NEVER create custom tool calling - use MCP protocol exclusively
```

## Implementation Blueprint

### AI Agent Architecture (MUST USE PYDANTIC AI + MCP)

Based on proven patterns from `/Users/aristotle/projects/shipwell_trade_compliance`, implement AI agents with MCP server integration:

```yaml
# CRITICAL: AI Agent Architecture Pattern
app/
├── agents/                         # Pydantic AI agents
│   ├── __init__.py
│   ├── customer_support_agent.py   # Main ticket creation agent
│   ├── categorization_agent.py     # Ticket categorization agent
│   └── prompts.py                  # Configurable agent prompts
├── services/
│   ├── ai_agent_service.py         # Agent orchestration service
│   └── ai_config_service.py        # Dynamic AI configuration management
├── routes/
│   ├── ai_config.py               # AI configuration management endpoint
│   └── agent.py                   # AI agent interaction endpoints
mcp_server/                        # FastMCP server (separate service)
├── start_mcp_server.py           # Main MCP server
├── tools/                         # MCP tools for AI agents
│   ├── ticket_tools.py            # Ticket creation/management tools
│   ├── file_analysis_tools.py     # File processing tools
│   ├── integration_tools.py       # Third-party API tools
│   └── knowledge_tools.py         # Knowledge base tools
└── requirements.txt
mcp_client/                        # MCP client for connecting to server
├── __init__.py
└── client.py                      # PydanticAI MCP client
```

#### Customer Support Agent Prompt System:
```yaml
# CRITICAL: Configurable prompts for ticket creation (stored in database)
DEFAULT_SUPPORT_AGENT_PROMPT: |
  "You are an expert customer support agent helping users create detailed support tickets.
  
  Your role is to:
  1. Analyze user requests, attachments, and context from Chrome extension
  2. Create comprehensive, well-structured support tickets
  3. Categorize tickets by urgency, type, and department
  4. Extract relevant information from uploaded files (screenshots, recordings, documents)
  5. Route tickets to appropriate teams or integrations (Jira, Salesforce, etc.)
  
  When creating tickets:
  - Use clear, professional language
  - Include all relevant context from user input and files
  - Set appropriate priority levels based on issue severity
  - Add relevant tags and categories for easy filtering
  - Include steps to reproduce if provided
  - Attach processed file analysis (transcriptions, OCR results)
  
  Available tools via MCP:
  - analyze_file: Process uploaded files for text/audio extraction  
  - create_jira_ticket: Create tickets in Jira projects
  - create_salesforce_case: Create cases in Salesforce
  - search_knowledge_base: Find existing solutions
  - categorize_issue: Auto-categorize based on content
  
  Always be helpful, thorough, and ensure tickets contain actionable information."

# AI Configuration Structure (dynamic updates via API)
AI_AGENT_CONFIG:
  customer_support_agent:
    model: "gpt-4o-mini"           # Configurable model
    temperature: 0.2               # Configurable parameters
    max_tokens: 2000
    timeout: 30
    system_prompt: "{{DYNAMIC_PROMPT}}"  # Updates via /ai-config endpoint
    tools_enabled: ["analyze_file", "create_jira_ticket", "create_salesforce_case"]
  
  categorization_agent:
    model: "gpt-4o-mini" 
    temperature: 0.1               # Lower temp for consistent categorization
    max_tokens: 500
    system_prompt: "{{CATEGORIZATION_PROMPT}}"
    
  file_analysis_agent:
    model: "gpt-4o"                # Better model for file analysis
    temperature: 0.1
    max_tokens: 1500
    system_prompt: "{{FILE_ANALYSIS_PROMPT}}"
```

#### MCP Server Tools Architecture:
```python
# MCP Server Tools (using FastMCP)
@mcp.tool()
async def analyze_file(file_path: str, file_type: str) -> Dict[str, Any]:
    """
    Analyze uploaded file and extract relevant information.
    Supports transcription, OCR, and metadata extraction.
    """
    
@mcp.tool()  
async def create_ticket(
    title: str,
    description: str, 
    category: str,
    priority: str,
    attachments: List[str] = None,
    integration: str = None
) -> Dict[str, Any]:
    """Create a support ticket with specified details and routing."""

@mcp.tool()
async def search_knowledge_base(query: str) -> List[Dict[str, Any]]:
    """Search existing knowledge base for similar issues and solutions."""

@mcp.tool()
async def categorize_issue(description: str, attachments: List[str] = None) -> Dict[str, Any]:
    """Auto-categorize support issue based on content analysis."""

@mcp.tool()
async def create_integration_ticket(
    integration_type: str,  # "jira", "salesforce", "github"
    ticket_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Create ticket in specified third-party integration."""
```

### WebSocket Message Protocols (MUST FOLLOW EXACT PATTERNS)

Based on proven patterns from `/Users/aristotle/projects/shipwell_trade_compliance`, implement WebSocket message protocols with Redis pub/sub architecture:

```yaml
# CRITICAL: WebSocket Architecture Pattern
app/websocket/
├── protocols/
│   ├── base_protocol.py        # Abstract base class with utilities
│   ├── ticket_protocol.py      # Ticket-specific messages  
│   └── file_protocol.py        # File processing messages
├── manager.py                  # Redis WebSocket manager
├── message_router.py           # Routes messages to protocols
└── redis_pubsub.py            # Redis pub/sub integration

# Message Structure (ALL messages MUST follow this format):
{
  "type": "message_type",       # REQUIRED: message type identifier
  "data": {},                   # REQUIRED: message payload
  "request_id": "uuid",         # OPTIONAL: client request tracking
  "timestamp": "ISO-8601"       # AUTO-ADDED: server timestamp
}

# Response Structure (ALL responses MUST include):
{
  "type": "response_type", 
  "protocol": "ticket|file",    # REQUIRED: protocol identifier
  "success": true|false,        # REQUIRED: operation status
  "timestamp": "ISO-8601",      # REQUIRED: server timestamp
  "data": {},                   # REQUIRED: response payload
  "error": "message"            # REQUIRED if success=false
}
```

#### Ticket Protocol Messages:
```yaml
# Client -> Server Messages
TICKET_MESSAGES:
  subscribe_ticket:             # Subscribe to ticket updates
    required: ["ticket_id"]
    example: {"type": "subscribe_ticket", "data": {"ticket_id": "123"}}
  
  unsubscribe_ticket:           # Unsubscribe from ticket updates
    required: ["ticket_id"] 
    example: {"type": "unsubscribe_ticket", "data": {"ticket_id": "123"}}
  
  get_ticket_status:            # Get current ticket status
    required: ["ticket_id"]
    example: {"type": "get_ticket_status", "data": {"ticket_id": "123"}}

# Server -> Client Notifications
TICKET_NOTIFICATIONS:
  ticket_status_update:         # Ticket status changed
    data: {"ticket_id", "status", "updated_by", "timestamp"}
  
  ticket_assigned:              # Ticket assigned to user
    data: {"ticket_id", "assigned_to", "assigned_by", "timestamp"}
  
  ticket_comment_added:         # New comment added
    data: {"ticket_id", "comment_id", "author", "content", "timestamp"}
  
  ai_categorization_complete:   # AI finished categorizing
    data: {"ticket_id", "category", "priority", "confidence", "timestamp"}
```

#### File Protocol Messages:
```yaml
# Client -> Server Messages  
FILE_MESSAGES:
  subscribe_job:                # Subscribe to file processing job
    required: ["job_id"]
    example: {"type": "subscribe_job", "data": {"job_id": "file-123"}}
  
  unsubscribe_job:              # Unsubscribe from job updates
    required: ["job_id"]
    example: {"type": "unsubscribe_job", "data": {"job_id": "file-123"}}
  
  get_job_status:               # Get current processing status
    required: ["job_id"]
    example: {"type": "get_job_status", "data": {"job_id": "file-123"}}

# Server -> Client Notifications
FILE_NOTIFICATIONS:
  file_upload_started:          # File upload began
    data: {"job_id", "filename", "file_size", "ticket_id", "timestamp"}
  
  file_upload_completed:        # File upload finished
    data: {"job_id", "filename", "file_path", "ticket_id", "timestamp"}
  
  file_processing_progress:     # Processing progress update
    data: {"job_id", "stage", "progress", "message", "timestamp"}
    stages: ["validation", "transcription", "ocr", "integration_upload"]
  
  transcription_completed:      # AI transcription finished
    data: {"job_id", "filename", "transcription", "confidence", "timestamp"}
  
  ocr_completed:                # OCR processing finished
    data: {"job_id", "filename", "extracted_text", "confidence", "timestamp"}
  
  file_processing_failed:       # Processing failed
    data: {"job_id", "filename", "error", "stage", "timestamp"}
```

### Data models and structure

Create the core data models, we ensure type safety and consistency.
```python
# SQLAlchemy Models (models/):
- BaseModel with created_at, updated_at, id fields
- TicketModel with status, priority, category, ai_metadata
- UserModel with roles, integrations, preferences
- FileModel with file_path, file_type, transcription, ocr_text, processing_status
- IntegrationModel for third-party connections
- AIAgentConfigModel with prompts, model settings, tool configurations

# Pydantic Schemas (schemas/):
- TicketCreate, TicketUpdate, TicketResponse with validation
- FileUpload, FileResponse with file handling and processing status
- IntegrationConfig with provider-specific settings
- WebSocketMessage, WebSocketResponse with protocol validation
- AIAgentConfig with dynamic prompt and model parameter validation
- MCPToolRequest, MCPToolResponse for MCP server communication

# Pydantic AI Agent Models (agents/):
- CustomerSupportContext with user input, files, conversation history
- TicketCreationResult with structured ticket data and routing decisions
- CategoryAnalysisResult with category, priority, confidence scores
- FileAnalysisResult with extracted text, metadata, insights
```

### list of tasks to be completed to fullfill the PRP in the order they should be completed

```yaml
Task 1: Project Infrastructure Setup
CREATE pyproject.toml:
  - MIRROR pattern from: /Users/aristotle/projects/shipwell_trade_compliance/pyproject.toml
  - MODIFY dependencies for ticket management (remove trade-specific packages)
  - ADD required packages: fastapi, celery, redis, postgresql, openai

CREATE compose.yml:
  - MIRROR pattern from: /Users/aristotle/projects/shipwell_trade_compliance/docker-compose.yml
  - MODIFY services for ticket backend (remove trade-specific services)
  - ENSURE PostgreSQL, Redis, Celery worker services

CREATE Dockerfile:
  - MIRROR exactly from: /Users/aristotle/projects/shipwell_trade_compliance/backend/Dockerfile
  - MODIFY COPY paths to use app/ instead of backend/app/
  - PRESERVE all system dependencies and security measures

Task 2: Core Application Structure
CREATE app/main.py:
  - MIRROR pattern from: /Users/aristotle/projects/shipwell_trade_compliance/backend/app/main.py
  - MODIFY route imports for ticket management
  - PRESERVE middleware, CORS, startup/shutdown patterns

CREATE app/database.py:
  - MIRROR pattern from example project
  - CONFIGURE PostgreSQL connection for ticket data

CREATE app/config/settings.py:
  - MIRROR pattern from example project
  - ADD ticket-specific configuration

Task 3: AI Configuration System
CREATE app/config/ai_config.yaml:
  - COPY exactly from: /Users/aristotle/projects/shipwell_trade_compliance/backend/config/ai_config.yaml
  - MODIFY model configurations for customer support and ticket categorization
  - PRESERVE all provider configurations, fallback chains

CREATE app/services/ai_config_service.py:
  - IMPLEMENT dynamic AI configuration management
  - ADD endpoint for updating agent prompts, models, parameters
  - INCLUDE database storage for configuration changes

Task 4: MCP Server Implementation (CRITICAL - Use FastMCP)
CREATE mcp_server/start_mcp_server.py:
  - COPY base structure from: /Users/aristotle/projects/shipwell_trade_compliance/backend/mcp_server/start_mcp_server.py
  - MODIFY for customer support tools instead of trade compliance
  - PRESERVE FastMCP integration patterns and logging

CREATE mcp_server/tools/ticket_tools.py:
  - IMPLEMENT @mcp.tool() decorated functions for ticket operations
  - ADD create_ticket, update_ticket, search_tickets tools
  - INCLUDE integration routing tools (Jira, Salesforce, GitHub)

CREATE mcp_server/tools/file_analysis_tools.py:
  - IMPLEMENT @mcp.tool() for analyze_file, extract_text_from_image, transcribe_audio
  - ADD file metadata extraction and content analysis tools
  - CONNECT to existing AI transcription/OCR services

CREATE mcp_server/tools/integration_tools.py:
  - IMPLEMENT @mcp.tool() for third-party API interactions
  - ADD create_jira_ticket, create_salesforce_case, create_github_issue tools
  - INCLUDE authentication and error handling for each integration

CREATE mcp_server/tools/knowledge_tools.py:
  - IMPLEMENT @mcp.tool() for search_knowledge_base, find_similar_tickets
  - ADD contextual search and solution recommendation tools

Task 5: MCP Client Integration  
CREATE mcp_client/client.py:
  - COPY exactly from: /Users/aristotle/projects/shipwell_trade_compliance/backend/mcp_client/client.py
  - MODIFY connection settings for customer support MCP server
  - PRESERVE PydanticAI MCP integration patterns

Task 6: Pydantic AI Agents (CRITICAL - Use pydantic_ai.Agent)
CREATE app/agents/customer_support_agent.py:
  - MIRROR pattern from: /Users/aristotle/projects/shipwell_trade_compliance/backend/app/agents/tariff_research_agent.py
  - IMPLEMENT Agent with MCP client integration for ticket creation
  - ADD structured result models for ticket data

CREATE app/agents/categorization_agent.py:
  - IMPLEMENT Pydantic AI agent for ticket categorization
  - USE MCP tools for category analysis and priority assignment
  - INCLUDE confidence scoring and reasoning

CREATE app/agents/prompts.py:
  - IMPLEMENT configurable prompts for all agents (stored in database)
  - ADD DEFAULT_SUPPORT_AGENT_PROMPT with comprehensive instructions
  - INCLUDE prompt templates for different ticket types and scenarios

CREATE app/services/ai_agent_service.py:
  - MIRROR service pattern from: /Users/aristotle/projects/shipwell_trade_compliance/backend/app/services/ai_chat_service.py
  - IMPLEMENT agent orchestration with MCP client integration
  - ADD error handling, timeout management, result processing

Task 7: Database Models
CREATE app/models/base.py:
  - MIRROR base model patterns from example project
  - IMPLEMENT created_at, updated_at, soft delete patterns

CREATE app/models/ticket.py:
  - IMPLEMENT comprehensive ticket model
  - ADD AI metadata fields, status enums, agent_session_id
  - INCLUDE foreign keys for users, files

CREATE app/models/user.py:
CREATE app/models/file.py:
CREATE app/models/integration.py:
  - FOLLOW same patterns as ticket model

CREATE app/models/ai_agent_config.py:
  - IMPLEMENT AI configuration storage model
  - ADD prompt templates, model parameters, tool configurations
  - INCLUDE versioning and rollback capabilities

Task 8: Pydantic Schemas
CREATE app/schemas/:
  - MIRROR schema patterns from example project
  - IMPLEMENT comprehensive validation
  - ADD file upload schemas for all file types
  - ADD AI agent configuration schemas with prompt validation

Task 9: API Endpoints
CREATE app/routes/tickets.py:
  - IMPLEMENT full CRUD operations
  - ADD AI-powered ticket creation endpoint using Pydantic AI agents
  - FOLLOW REST conventions from example project

CREATE app/routes/files.py:
  - IMPLEMENT file upload endpoint for all file types
  - ADD processing status endpoints (transcription, OCR)
  - HANDLE multipart form data from Chrome extension

CREATE app/routes/ai_config.py: 
  - IMPLEMENT dynamic AI configuration management endpoint
  - ADD GET /ai-config/{agent_type} to retrieve current configuration
  - ADD PUT /ai-config/{agent_type} to update prompts, models, parameters
  - ADD POST /ai-config/{agent_type}/test to test configuration changes
  - INCLUDE configuration history and rollback functionality

CREATE app/routes/agent.py:
  - IMPLEMENT AI agent interaction endpoints
  - ADD POST /agent/create-ticket for customer support agent
  - ADD POST /agent/categorize for categorization agent
  - ADD POST /agent/analyze-files for file analysis agent

CREATE app/routes/integrations.py:
CREATE app/routes/auth.py:
CREATE app/routes/analytics.py:
CREATE app/routes/websocket.py:
  - MIRROR patterns from example project
  - ADAPT for ticket management use case

Task 10: Business Logic Services
CREATE app/services/ticket_service.py:
CREATE app/services/file_service.py:
CREATE app/services/integration_service.py:
CREATE app/services/notification_service.py:
  - IMPLEMENT core business logic
  - SEPARATE from API layer
  - ADD proper error handling

Task 11: Background Tasks with Celery
CREATE app/celery_app.py:
  - MIRROR celery configuration from example project
  - CONFIGURE Redis as broker

CREATE app/tasks/:
  - IMPLEMENT file transcription/OCR tasks
  - ADD integration sync tasks
  - ADD AI agent task queuing for long-running operations
  - FOLLOW async patterns from example project

Task 12: WebSocket Protocol Implementation
CREATE app/websocket/protocols/base_protocol.py:
  - COPY exactly from: /Users/aristotle/projects/shipwell_trade_compliance/backend/app/websocket/protocols/base_protocol.py
  - PRESERVE all validation, error handling, logging patterns

CREATE app/websocket/protocols/ticket_protocol.py:
  - MIRROR pattern from: /Users/aristotle/projects/shipwell_trade_compliance/backend/app/websocket/protocols/file_protocol.py
  - IMPLEMENT ticket subscription messages: subscribe_ticket, unsubscribe_ticket, get_ticket_status
  - ADD ticket notification handlers for status updates, assignments, comments

CREATE app/websocket/protocols/file_protocol.py:
  - COPY exactly from: /Users/aristotle/projects/shipwell_trade_compliance/backend/app/websocket/protocols/file_protocol.py
  - MODIFY for ticket file processing (remove trade-specific logic)
  - PRESERVE all Redis pub/sub patterns, job tracking

CREATE app/websocket/manager.py:
  - MIRROR pattern from: /Users/aristotle/projects/shipwell_trade_compliance/backend/app/websocket/manager.py
  - IMPLEMENT Redis pub/sub WebSocket manager
  - ADD notification types for ticket management

CREATE app/websocket/message_router.py:
  - COPY from: /Users/aristotle/projects/shipwell_trade_compliance/backend/app/websocket/message_router.py
  - MODIFY message type mappings for ticket and file protocols
  - PRESERVE routing logic and error handling

CREATE app/websocket/redis_pubsub.py:
  - COPY exactly from: /Users/aristotle/projects/shipwell_trade_compliance/backend/app/websocket/redis_pubsub.py
  - PRESERVE Redis integration patterns

Task 13: Authentication & Middleware
CREATE app/middleware/:
  - MIRROR auth patterns from example project
  - IMPLEMENT JWT authentication
  - ADD rate limiting for uploads and AI agent requests

Task 14: Database Migrations
CREATE alembic/:
  - MIRROR migration patterns from example project
  - IMPLEMENT initial schema migrations including AI agent config tables
  - ADD indexes for performance

Task 15: AI Agent and MCP Test Suite
CREATE tests/test_mcp_server.py:
  - TEST all MCP tools (@mcp.tool() functions)
  - VALIDATE tool parameter validation and response formats
  - TEST error handling for invalid inputs and API failures

CREATE tests/test_pydantic_ai_agents.py:
  - TEST customer support agent with various input scenarios
  - TEST categorization agent accuracy and consistency
  - TEST file analysis agent with different file types
  - MOCK MCP client for isolated agent testing

CREATE tests/test_ai_config_service.py:
  - TEST AI configuration CRUD operations
  - TEST prompt update validation and rollback functionality
  - TEST configuration history and versioning

Task 16: WebSocket Test Suite
CREATE tests/test_websocket_protocols.py:
  - MIRROR test patterns from: /Users/aristotle/projects/shipwell_trade_compliance/backend/tests/test_websocket.py
  - IMPLEMENT tests for EVERY message type defined in protocols
  - TEST Redis pub/sub message routing
  - VALIDATE protocol message structure and responses

CREATE tests/test_ticket_protocol.py:
  - TEST subscribe_ticket message handling
  - TEST unsubscribe_ticket message handling  
  - TEST get_ticket_status message handling
  - TEST ticket_status_update notifications
  - TEST ticket_assigned notifications
  - TEST ai_categorization_complete notifications
  - VALIDATE error responses for invalid messages

CREATE tests/test_file_protocol.py:
  - TEST subscribe_job message handling
  - TEST unsubscribe_job message handling
  - TEST get_job_status message handling
  - TEST file_upload_started notifications
  - TEST file_processing_progress notifications
  - TEST transcription_completed notifications
  - TEST ocr_completed notifications
  - TEST file_processing_failed notifications
  - VALIDATE job subscription management

Task 17: Comprehensive Test Suite
CREATE tests/:
  - MIRROR test patterns from example project
  - IMPLEMENT comprehensive API tests including AI agent endpoints
  - ADD integration tests for third-party APIs and MCP server
  - ENSURE 95%+ test coverage including WebSocket protocols and AI agents

Task 18: Documentation Generation
CREATE openapi.json generation:
  - MIRROR OpenAPI patterns from example project
  - IMPLEMENT Redocly documentation
  - ENSURE auto-generation on API changes
  - DOCUMENT WebSocket message protocols and AI agent endpoints in API docs
  - INCLUDE MCP server tool documentation

Task 19: Environment Configuration
CREATE .env.example:
  - ADD all required environment variables
  - DOCUMENT third-party API keys and AI model API keys
  - INCLUDE database URLs, Redis config
  - ADD WebSocket Redis configuration
  - ADD MCP server URL and AI agent configuration

Task 20: Production Deployment
VALIDATE compose startup:
  - ENSURE all services start correctly (app, MCP server, Redis, PostgreSQL)
  - TEST database migrations including AI agent config tables
  - VERIFY API endpoints respond including AI agent endpoints
  - VALIDATE WebSocket connections and Redis pub/sub
  - TEST MCP server connectivity and tool availability
```

### Per task pseudocode as needed added to each task

```python
# Task 3: AI Service Implementation
async def categorize_ticket(ticket_description: str) -> TicketCategory:
    # PATTERN: Use AI config from yaml file (see example project)
    config = load_ai_config()
    
    # GOTCHA: AI providers require fallback chains for reliability
    async with get_ai_client(config.primary_provider) as client:
        # CRITICAL: Use structured prompts for consistent categorization
        prompt = build_categorization_prompt(ticket_description)
        
        try:
            # PATTERN: Implement retry with exponential backoff
            @retry(attempts=3, backoff=exponential)
            async def _categorize():
                response = await client.generate(
                    prompt=prompt,
                    max_tokens=config.models.primary.max_tokens,
                    temperature=0.1  # Low temperature for consistent categorization
                )
                return parse_category_response(response)
            
            return await _categorize()
            
        except AIProviderError:
            # FALLBACK: Use secondary provider from config
            return await categorize_with_fallback(ticket_description, config)

# Task 6: File Upload Endpoint
@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),  # PATTERN: Use FastAPI UploadFile
    ticket_id: int = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> FileResponse:
    # PATTERN: Validate file type and size (see security patterns)
    validate_file_type_and_size(file)
    
    # GOTCHA: Chrome extension sends large files - stream processing required
    file_path = await save_uploaded_file(file, ticket_id)
    
    # PATTERN: Create database record immediately, process in background
    file_record = await create_file_record(ticket_id, file_path, file.content_type)
    
    # CRITICAL: Use Celery for CPU-intensive processing (transcription/OCR)
    if is_audio_video_file(file.content_type):
        background_tasks.add_task(
            transcribe_file_task.delay,
            file_record.id,
            file_path
        )
    elif is_image_file(file.content_type):
        background_tasks.add_task(
            ocr_file_task.delay,
            file_record.id,
            file_path
        )
    
    return FileResponse.from_orm(file_record)

# Task 8: Celery Background Tasks
@celery_app.task(bind=True, max_retries=3)
def transcribe_file_task(self, file_id: int, file_path: str):
    # PATTERN: Handle task failures gracefully
    try:
        # GOTCHA: AI transcription can be slow - update progress
        update_file_status(file_id, "processing")
        
        # CRITICAL: Use AI service with proper configuration
        transcription = ai_service.transcribe_audio_video(file_path)
        
        # PATTERN: Update database with results
        update_file_transcription(file_id, transcription)
        
        # PATTERN: Send WebSocket notification when complete
        notify_file_processing_complete(file_id, "transcription")
        
    except Exception as exc:
        # PATTERN: Retry with exponential backoff
        self.retry(countdown=60 * (2 ** self.request.retries))

@celery_app.task(bind=True, max_retries=3)
def ocr_file_task(self, file_id: int, file_path: str):
    # PATTERN: Handle task failures gracefully
    try:
        # GOTCHA: OCR can be slow for large images - update progress
        update_file_status(file_id, "processing")
        
        # CRITICAL: Use AI service with proper configuration
        ocr_text = ai_service.extract_text_from_image(file_path)
        
        # PATTERN: Update database with results
        update_file_ocr_text(file_id, ocr_text)
        
        # PATTERN: Send WebSocket notification when complete
        notify_file_processing_complete(file_id, "ocr")
        
    except Exception as exc:
        # PATTERN: Retry with exponential backoff
        self.retry(countdown=60 * (2 ** self.request.retries))

# Task 9: WebSocket Protocol Implementation
class TicketProtocol(BaseProtocol):
    """Ticket-specific WebSocket message handler"""
    
    def get_supported_message_types(self) -> Set[str]:
        return {"subscribe_ticket", "unsubscribe_ticket", "get_ticket_status"}
    
    async def handle_message(self, client_id: str, message: Dict[str, Any], user: DBUser, db):
        message_type = message.get("type")
        
        # PATTERN: Route to specific handlers based on example project
        handlers = {
            "subscribe_ticket": self._handle_subscribe_ticket,
            "unsubscribe_ticket": self._handle_unsubscribe_ticket,
            "get_ticket_status": self._handle_get_ticket_status
        }
        
        handler = handlers.get(message_type)
        if handler:
            await handler(client_id, message, user, db)
        else:
            await self.send_error_response(client_id, f"Unknown message type: {message_type}")
    
    async def _handle_subscribe_ticket(self, client_id: str, message: Dict[str, Any], user: DBUser, db):
        # CRITICAL: Validate message structure (from base protocol)
        is_valid, error_msg = self.validate_message_structure(message, {"ticket_id"})
        if not is_valid:
            await self.send_error_response(client_id, error_msg, "subscribe_ticket")
            return
        
        ticket_id = message["data"]["ticket_id"]
        
        # PATTERN: Subscribe client to Redis channel for ticket updates
        success = await websocket_manager.subscribe_to_ticket(client_id, ticket_id, str(user.id))
        
        if success:
            await self.send_success_response(client_id, {
                "type": "subscription_response",
                "ticket_id": ticket_id,
                "success": True
            }, NotificationType.TASK_COMPLETION)

# CRITICAL: Send notifications when ticket events occur
async def notify_ticket_status_update(ticket_id: str, user_id: str, status: str, updated_by: str):
    """Send ticket status update notification via WebSocket"""
    notification_data = {
        "type": "ticket_status_update",
        "ticket_id": ticket_id,
        "status": status,
        "updated_by": updated_by,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # PATTERN: Broadcast via Redis to all subscribers
    await websocket_manager.broadcast_ticket_update(ticket_id, user_id, notification_data)

# Task 4: MCP Server Implementation
from fastmcp import FastMCP
from typing import Dict, Any, List

# Initialize FastMCP server
mcp = FastMCP("Customer Support Tools")

@mcp.tool()
async def analyze_file(file_path: str, file_type: str, analysis_type: str = "auto") -> Dict[str, Any]:
    """
    Analyze uploaded file and extract relevant information.
    Supports transcription, OCR, and metadata extraction.
    """
    # PATTERN: Route to appropriate analysis service based on file type
    if file_type.startswith("audio/") or file_type.startswith("video/"):
        # CRITICAL: Use existing AI transcription service
        transcription_result = await transcription_service.transcribe_file(file_path)
        return {
            "analysis_type": "transcription",
            "extracted_text": transcription_result.text,
            "confidence": transcription_result.confidence,
            "metadata": {"duration": transcription_result.duration}
        }
    elif file_type.startswith("image/"):
        # CRITICAL: Use existing OCR service  
        ocr_result = await ocr_service.extract_text(file_path)
        return {
            "analysis_type": "ocr",
            "extracted_text": ocr_result.text,
            "confidence": ocr_result.confidence,
            "metadata": {"image_size": ocr_result.dimensions}
        }
    else:
        # PATTERN: Handle document files with metadata extraction
        return {
            "analysis_type": "metadata",
            "extracted_text": "",
            "metadata": await extract_file_metadata(file_path)
        }

@mcp.tool()
async def create_ticket(
    title: str,
    description: str,
    category: str,
    priority: str,
    attachments: List[str] = None,
    integration: str = None
) -> Dict[str, Any]:
    """Create a support ticket with specified details and routing."""
    # PATTERN: Use existing ticket service for creation
    ticket_data = {
        "title": title,
        "description": description,
        "category": category,
        "priority": priority,
        "attachments": attachments or [],
        "ai_generated": True
    }
    
    # CRITICAL: Create ticket in main database first
    ticket = await ticket_service.create_ticket(ticket_data)
    
    # PATTERN: Route to integration if specified
    if integration:
        integration_result = await route_to_integration(integration, ticket)
        ticket.integration_id = integration_result.external_id
        await ticket_service.update_ticket(ticket.id, ticket)
    
    return {
        "ticket_id": ticket.id,
        "external_id": getattr(ticket, 'integration_id', None),
        "integration": integration,
        "status": "created"
    }

# Task 6: Pydantic AI Agent Implementation  
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel

class CustomerSupportContext(BaseModel):
    """Context for customer support operations"""
    user_input: str
    uploaded_files: List[str] = []
    conversation_history: List[Dict[str, Any]] = []
    user_metadata: Dict[str, Any] = {}

class TicketCreationResult(BaseModel):
    """Structured output from customer support agent"""
    ticket_title: str
    ticket_description: str
    category: str
    priority: str
    confidence_score: float
    recommended_integration: str = None
    file_analysis_summary: str = ""
    next_actions: List[str] = []

# PATTERN: Initialize agent with MCP client from example project
customer_support_agent = Agent(
    'gpt-4o-mini',
    result_type=TicketCreationResult,
    system_prompt="""You are an expert customer support agent helping users create detailed support tickets...
    {DYNAMIC_PROMPT_FROM_DATABASE}""",
    tools=[mcp_client]  # CRITICAL: Use MCP client for tool access
)

async def create_ticket_with_ai(user_input: str, files: List[str] = None) -> TicketCreationResult:
    """Use Pydantic AI agent to create ticket from user input."""
    # PATTERN: Build context from user input and files
    context = CustomerSupportContext(
        user_input=user_input,
        uploaded_files=files or []
    )
    
    # CRITICAL: Use agent with MCP tools for file analysis and ticket creation
    result = await customer_support_agent.run(
        f"Create a support ticket based on: {context.user_input}. "
        f"Analyze attached files: {context.uploaded_files}",
        message_history=[],
    )
    
    return result.data

# Task 9: AI Configuration Management Endpoint
from fastapi import APIRouter, HTTPException
from app.schemas.ai_config import AIAgentConfigUpdate

router = APIRouter(prefix="/ai-config", tags=["AI Configuration"])

@router.get("/{agent_type}")
async def get_ai_config(agent_type: str) -> Dict[str, Any]:
    """Get current AI agent configuration"""
    # PATTERN: Load from database with fallback to defaults
    config = await ai_config_service.get_agent_config(agent_type)
    if not config:
        raise HTTPException(status_code=404, f"Configuration for {agent_type} not found")
    
    return {
        "agent_type": agent_type,
        "model": config.model,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "system_prompt": config.system_prompt,
        "tools_enabled": config.tools_enabled,
        "updated_at": config.updated_at
    }

@router.put("/{agent_type}")
async def update_ai_config(
    agent_type: str, 
    config_update: AIAgentConfigUpdate
) -> Dict[str, Any]:
    """Update AI agent configuration with prompt and model changes"""
    # CRITICAL: Validate configuration before applying
    validation_result = await ai_config_service.validate_config(agent_type, config_update)
    if not validation_result.is_valid:
        raise HTTPException(status_code=400, validation_result.errors)
    
    # PATTERN: Store in database with versioning
    updated_config = await ai_config_service.update_agent_config(
        agent_type, config_update
    )
    
    # CRITICAL: Reload agent with new configuration
    await ai_agent_service.reload_agent(agent_type)
    
    return {
        "agent_type": agent_type,
        "status": "updated",
        "version": updated_config.version,
        "changes": config_update.dict(exclude_unset=True)
    }
```

### Integration Points
```yaml
DATABASE:
  - migration: "Create tickets, users, files, integrations tables"
  - indexes: "CREATE INDEX idx_ticket_status ON tickets(status, created_at)"
  - constraints: "Foreign key relationships between tickets-users-files"
  
CONFIG:
  - add to: app/config/settings.py
  - pattern: "DATABASE_URL = Field(env='DATABASE_URL')"
  - add to: app/config/ai_config.yaml
  - pattern: "Copy exactly from example project, modify models for ticket use case"
  
ROUTES:
  - add to: app/main.py  
  - pattern: "app.include_router(tickets_router, prefix='/api/v1')"
  
CELERY:
  - add to: compose.yml
  - pattern: "Redis service, Celery worker service with proper depends_on"
  
WEBSOCKETS:
  - add to: app/routes/websocket.py
  - pattern: "ConnectionManager for real-time ticket status updates"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check app/ --fix              # Auto-fix what's possible
mypy app/                          # Type checking
poetry check                       # Poetry file validation - NO pip allowed

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests each new feature/file/function use existing test patterns
```python
# CREATE tests/test_tickets.py with these test cases:
def test_create_ticket():
    """Basic ticket creation works"""
    ticket_data = {"title": "Test ticket", "description": "Test description"}
    response = client.post("/api/v1/tickets", json=ticket_data)
    assert response.status_code == 201
    assert response.json()["status"] == "open"

def test_ai_categorization():
    """AI categorization endpoint works"""
    response = client.post("/api/v1/tickets/categorize", 
                          json={"description": "Login issues"})
    assert response.status_code == 200
    assert response.json()["category"] in ["technical", "user_access", "bug"]

def test_file_upload():
    """File upload endpoint handles multipart data"""
    with open("test_video.mp4", "rb") as video_file:
        response = client.post("/api/v1/files/upload",
                              files={"file": video_file},
                              data={"ticket_id": 1})
    assert response.status_code == 201
    assert "processing_status" in response.json()

def test_image_upload_ocr():
    """Image upload triggers OCR processing"""
    with open("test_image.png", "rb") as image_file:
        response = client.post("/api/v1/files/upload",
                              files={"file": image_file},
                              data={"ticket_id": 1})
    assert response.status_code == 201
    assert response.json()["file_type"].startswith("image/")
    assert "processing_status" in response.json()

def test_integration_webhook():
    """Third-party webhook processing works"""
    slack_payload = {"channel": "support", "message": "New ticket"}
    response = client.post("/api/v1/integrations/slack/webhook",
                          json=slack_payload)
    assert response.status_code == 200

# CRITICAL: AI Agent and MCP Server Tests
# CREATE tests/test_mcp_server.py with comprehensive MCP tool tests:

@pytest.mark.asyncio
async def test_analyze_file_tool():
    """Test MCP analyze_file tool with different file types"""
    # Test audio file analysis
    audio_result = await analyze_file("/path/to/audio.mp3", "audio/mp3")
    assert audio_result["analysis_type"] == "transcription"
    assert "extracted_text" in audio_result
    assert "confidence" in audio_result

    # Test image file analysis
    image_result = await analyze_file("/path/to/image.png", "image/png")
    assert image_result["analysis_type"] == "ocr"
    assert "extracted_text" in image_result
    assert "confidence" in image_result

@pytest.mark.asyncio
async def test_create_ticket_tool():
    """Test MCP create_ticket tool"""
    ticket_result = await create_ticket(
        title="Test Issue",
        description="Test description", 
        category="technical",
        priority="high",
        integration="jira"
    )
    assert ticket_result["status"] == "created"
    assert "ticket_id" in ticket_result
    assert ticket_result["integration"] == "jira"

@pytest.mark.asyncio
async def test_pydantic_ai_customer_support_agent():
    """Test Pydantic AI customer support agent"""
    # Mock MCP client
    mock_mcp_client = AsyncMock()
    mock_mcp_client.analyze_file.return_value = {
        "extracted_text": "Error screenshot showing login failure",
        "confidence": 0.95
    }

    # Test agent with file analysis
    result = await create_ticket_with_ai(
        user_input="I can't log in to the application, attached screenshot shows the error",
        files=["/path/to/screenshot.png"]
    )
    
    assert isinstance(result, TicketCreationResult)
    assert result.category in ["technical", "user_access", "bug"]
    assert result.priority in ["low", "medium", "high", "critical"]
    assert result.confidence_score >= 0.0
    assert "login" in result.ticket_description.lower()

@pytest.mark.asyncio
async def test_ai_config_management():
    """Test AI configuration update functionality"""
    # Test configuration retrieval
    config = await ai_config_service.get_agent_config("customer_support_agent")
    assert config is not None
    assert config.model in ["gpt-4o", "gpt-4o-mini"]
    
    # Test configuration update
    update_data = AIAgentConfigUpdate(
        system_prompt="Updated customer support prompt",
        temperature=0.3
    )
    
    updated_config = await ai_config_service.update_agent_config(
        "customer_support_agent", update_data
    )
    
    assert updated_config.system_prompt == "Updated customer support prompt"
    assert updated_config.temperature == 0.3
    assert updated_config.version > config.version

# CRITICAL: WebSocket Protocol Tests (MIRROR from example project)
# CREATE tests/test_websocket_protocols.py with comprehensive tests:

@pytest.mark.asyncio
async def test_ticket_protocol_subscribe_message():
    """Test ticket subscription WebSocket message"""
    protocol = TicketProtocol()
    mock_client_id = "test-client-123"
    mock_user = MagicMock()
    mock_user.id = "user-456"
    
    # Valid subscription message
    message = {
        "type": "subscribe_ticket",
        "data": {"ticket_id": "ticket-789"}
    }
    
    with patch('app.websocket.protocols.ticket_protocol.websocket_manager') as mock_manager:
        mock_manager.subscribe_to_ticket = AsyncMock(return_value=True)
        
        await protocol.handle_message(mock_client_id, message, mock_user, None)
        
        # Verify subscription was called
        mock_manager.subscribe_to_ticket.assert_called_once_with(
            mock_client_id, "ticket-789", "user-456"
        )

@pytest.mark.asyncio  
async def test_ticket_protocol_invalid_message():
    """Test ticket protocol handles invalid messages properly"""
    protocol = TicketProtocol()
    
    # Missing required field
    invalid_message = {
        "type": "subscribe_ticket", 
        "data": {}  # Missing ticket_id
    }
    
    with patch.object(protocol, 'send_error_response') as mock_error:
        await protocol.handle_message("client-123", invalid_message, None, None)
        
        # Verify error response was sent
        mock_error.assert_called_once()
        error_call = mock_error.call_args
        assert "Missing required fields" in error_call[0][1]

@pytest.mark.asyncio
async def test_file_protocol_subscribe_job():
    """Test file processing job subscription"""
    protocol = FileProtocol()
    mock_client_id = "client-123"
    mock_user = MagicMock()
    mock_user.id = "user-456"
    
    message = {
        "type": "subscribe_job",
        "data": {"job_id": "file-processing-789"}
    }
    
    with patch('app.websocket.protocols.file_protocol.websocket_manager') as mock_manager:
        mock_manager.subscribe_to_job = AsyncMock(return_value=True)
        
        await protocol.handle_message(mock_client_id, message, mock_user, None)
        
        mock_manager.subscribe_to_job.assert_called_once_with(
            mock_client_id, "file-processing-789", "user-456"
        )

@pytest.mark.asyncio
async def test_websocket_notification_broadcasting():
    """Test WebSocket notification broadcasting via Redis"""
    from app.websocket.protocols.ticket_protocol import notify_ticket_status_update
    
    with patch('app.websocket.protocols.ticket_protocol.websocket_manager') as mock_manager:
        mock_manager.broadcast_ticket_update = AsyncMock()
        
        await notify_ticket_status_update(
            ticket_id="ticket-123",
            user_id="user-456", 
            status="in_progress",
            updated_by="admin-789"
        )
        
        # Verify broadcast was called with correct data structure
        mock_manager.broadcast_ticket_update.assert_called_once()
        call_args = mock_manager.broadcast_ticket_update.call_args[0]
        
        assert call_args[0] == "ticket-123"  # ticket_id
        assert call_args[1] == "user-456"    # user_id
        notification_data = call_args[2]      # notification data
        
        assert notification_data["type"] == "ticket_status_update"
        assert notification_data["ticket_id"] == "ticket-123"
        assert notification_data["status"] == "in_progress"
        assert notification_data["updated_by"] == "admin-789"
        assert "timestamp" in notification_data

@pytest.mark.asyncio
async def test_websocket_connection_cleanup():
    """Test WebSocket connection cleanup when client disconnects"""
    protocol = TicketProtocol() 
    client_id = "disconnecting-client"
    
    # Mock websocket manager with subscriptions
    with patch('app.websocket.protocols.ticket_protocol.websocket_manager') as mock_manager:
        mock_manager.ticket_subscribers = {
            "ticket-123": {client_id, "other-client"},
            "ticket-456": {client_id}
        }
        mock_manager.unsubscribe_from_ticket = AsyncMock(return_value=True)
        
        await protocol.cleanup_client_resources(client_id)
        
        # Verify cleanup was called for all subscriptions
        assert mock_manager.unsubscribe_from_ticket.call_count == 2
```

```bash
# Run and iterate until passing:
poetry run pytest tests/ -v --cov=app
# Target: 95%+ test coverage including WebSocket protocols. If failing: Read error, fix code, re-run
```

### Level 3: Integration Test
```bash
# Start the full stack with modern Docker Compose
docker compose up -d

# Wait for services to be ready
sleep 10

# Test ticket creation API
curl -X POST http://localhost:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{"title": "Test ticket", "description": "Integration test"}'

# Expected: {"id": 1, "status": "open", "category": "general"}

# Test file upload
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@test_video.mp4" \
  -F "ticket_id=1"

# Expected: {"id": 1, "processing_status": "processing"}

# Test image upload with OCR
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@test_image.png" \
  -F "ticket_id=1"

# Expected: {"id": 2, "processing_status": "processing", "file_type": "image/png"}

# Test WebSocket connection and message protocols
curl -X GET http://localhost:8000/api/v1/websocket/health

# Expected: {"status": "ok", "active_connections": 0}

# Test WebSocket ticket subscription (using wscat or similar)
wscat -c ws://localhost:8000/ws
# Send: {"type": "subscribe_ticket", "data": {"ticket_id": "1"}}
# Expected: {"type": "subscription_response", "protocol": "ticket", "success": true}

# Test WebSocket file job subscription  
wscat -c ws://localhost:8000/ws
# Send: {"type": "subscribe_job", "data": {"job_id": "file-123"}}  
# Expected: {"type": "subscription_response", "protocol": "file", "success": true}

# Test AI agent ticket creation
curl -X POST http://localhost:8000/api/v1/agent/create-ticket \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Login issues with screenshot", "files": ["screenshot.png"]}'

# Expected: {"ticket_id": 1, "category": "technical", "priority": "high", "confidence": 0.9}

# Test MCP server connectivity
curl -X GET http://localhost:8001/health

# Expected: {"status": "healthy", "tools_available": ["analyze_file", "create_ticket", "search_knowledge_base"]}

# Test AI configuration management
curl -X GET http://localhost:8000/api/v1/ai-config/customer_support_agent

# Expected: {"agent_type": "customer_support_agent", "model": "gpt-4o-mini", "system_prompt": "..."}

# If error: Check logs at docker compose logs app mcp-server
```

## Final validation Checklist
- [ ] All tests pass: `poetry run pytest tests/ -v --cov=app`
- [ ] No linting errors: `ruff check app/`
- [ ] No type errors: `mypy app/`
- [ ] Docker stack starts: `docker compose up -d && sleep 10 && docker compose ps`
- [ ] API documentation generates: `curl http://localhost:8000/docs`
- [ ] Database migrations work: `docker compose exec app alembic upgrade head`
- [ ] Celery tasks process: `docker compose logs celery`
- [ ] AI service configures: Check AI config loads without errors
- [ ] Third-party integration endpoints respond correctly
- [ ] WebSocket connections handle properly 
- [ ] WebSocket message protocols work correctly: `wscat -c ws://localhost:8000/ws`
- [ ] Redis pub/sub integration functions: Check Redis connection and message routing
- [ ] All WebSocket notification types send properly: Test each message type
- [ ] File uploads process and store correctly
- [ ] WebSocket protocol tests pass: `poetry run pytest tests/test_websocket_protocols.py -v`
- [ ] AI agent tests pass: `poetry run pytest tests/test_pydantic_ai_agents.py -v`
- [ ] MCP server tests pass: `poetry run pytest tests/test_mcp_server.py -v`
- [ ] AI configuration management tests pass: `poetry run pytest tests/test_ai_config_service.py -v`
- [ ] MCP server runs and tools are available: `curl http://localhost:8001/health`
- [ ] AI agent endpoints respond correctly: Test create-ticket endpoint
- [ ] AI configuration can be updated dynamically: Test PUT /ai-config endpoints

---

## Anti-Patterns to Avoid
- ❌ Don't create new patterns when example project patterns work
- ❌ Don't skip AI configuration - copy exactly from example project  
- ❌ Don't ignore Celery task failures - implement proper retry logic
- ❌ Don't hardcode AI provider settings - use config system
- ❌ Don't skip WebSocket lifecycle management
- ❌ Don't ignore third-party API rate limits and error handling
- ❌ Don't skip database indexing for performance
- ❌ Don't use sync functions in async FastAPI context
- ❌ Don't skip file upload validation and security measures
- ❌ Don't ignore Docker health checks and proper startup ordering
- ❌ Don't use pip commands - ONLY use poetry for package management
- ❌ Don't use docker-compose - use modern `docker compose` syntax
- ❌ Don't create custom WebSocket message formats - follow exact protocol patterns
- ❌ Don't skip Redis pub/sub integration - required for WebSocket scalability
- ❌ Don't forget to test every WebSocket message type - each needs comprehensive tests
- ❌ Don't create custom AI tool calling - MUST use MCP server with FastMCP exclusively
- ❌ Don't skip Pydantic AI agent patterns - follow example project structure exactly
- ❌ Don't hardcode AI prompts - store in database with dynamic configuration endpoint
- ❌ Don't skip MCP server health checks - validate tool availability on startup

## Quality Assessment
This PRP provides comprehensive context including:
- ✅ Complete example project structure to mirror
- ✅ Specific technology stack URLs and documentation  
- ✅ Detailed AI configuration patterns
- ✅ Chrome extension file upload integration patterns
- ✅ Background job processing patterns
- ✅ Comprehensive test validation loops
- ✅ Docker containerization patterns
- ✅ Database migration patterns
- ✅ Third-party integration examples
- ✅ Production deployment considerations
- ✅ Comprehensive WebSocket protocol documentation with exact message formats
- ✅ Redis pub/sub architecture patterns from proven example project
- ✅ Complete test coverage for all WebSocket message types
- ✅ WebSocket notification broadcasting patterns
- ✅ Protocol validation and error handling patterns
- ✅ Comprehensive AI agent architecture with Pydantic AI and MCP server integration
- ✅ Dynamic AI configuration management with database storage
- ✅ FastMCP server implementation with customer support tools
- ✅ Customer support agent prompt system with configurable prompts
- ✅ Complete MCP client integration patterns from example project
- ✅ AI agent testing patterns with comprehensive validation

### Docker Compose and Alembic Database Management

#### Docker Compose Structure (compose.yml):
```yaml
# CRITICAL: Multi-service architecture with proper dependencies
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/tickets
      - REDIS_URL=redis://redis:6379
      - MCP_SERVER_URL=http://mcp-server:8001
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      mcp-server:
        condition: service_started
    volumes:
      - ./uploads:/app/uploads
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

  mcp-server:
    build:
      context: .
      dockerfile: mcp_server/Dockerfile
    ports:
      - "8001:8001"  
    environment:
      - BACKEND_URL=http://app:8000
      - DATABASE_URL=postgresql://user:pass@postgres:5432/tickets
    depends_on:
      postgres:
        condition: service_healthy
    command: ["python", "mcp_server/start_mcp_server.py", "--port", "8001"]

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=tickets
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d tickets"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  celery-worker:
    build: .
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/tickets
      - REDIS_URL=redis://redis:6379
      - MCP_SERVER_URL=http://mcp-server:8001
    depends_on:
      - postgres
      - redis
      - mcp-server
    volumes:
      - ./uploads:/app/uploads
    command: ["celery", "-A", "app.celery_app", "worker", "--loglevel=info"]

volumes:
  postgres_data:
  redis_data:
```

#### Dockerfile Structure:
```dockerfile
# CRITICAL: Multi-stage build for production optimization
FROM python:3.12-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.8.3

# Copy project files
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Configure Poetry and install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Production stage
FROM python:3.12-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Copy application code
WORKDIR /app
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY mcp_client/ ./mcp_client/

# Create uploads directory
RUN mkdir -p /app/uploads && chown app:app /app/uploads

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Alembic Database Migration Management:
```yaml
# CRITICAL: Use Alembic for ALL database schema changes
ALEMBIC_STRUCTURE:
  alembic/                         # Database migrations directory  
  ├── env.py                       # Alembic configuration
  ├── script.py.mako              # Migration template  
  └── versions/                    # Migration files
      ├── 001_initial_schema.py    # Initial tables (users, tickets, files)
      ├── 002_add_ai_config.py     # AI agent configuration tables
      ├── 003_add_integrations.py # Integration tables
      └── 004_add_websocket.py    # WebSocket subscription tables

# Migration Commands (NEVER use raw SQL):
poetry run alembic upgrade head    # Apply all migrations
poetry run alembic revision --autogenerate -m "description"  # Generate migration
poetry run alembic downgrade -1   # Rollback one migration
poetry run alembic current        # Show current migration
poetry run alembic history        # Show migration history

# CRITICAL: Migration patterns to follow
MIGRATION_PATTERNS:
  initial_schema: |
    - Users table with authentication fields
    - Tickets table with AI metadata columns
    - Files table with processing status
    - Indexes on frequently queried fields (ticket status, user_id, created_at)
  
  ai_config_schema: |
    - ai_agent_configs table with prompt templates
    - agent_config_versions for versioning/rollback
    - Foreign keys to users for configuration ownership
    
  integration_schema: |
    - integrations table with provider-specific settings
    - integration_tickets table mapping internal to external IDs
    - Encrypted credential storage for API keys
```

**Confidence Score: 9.8/10** - This PRP has comprehensive context including proven AI agent patterns, MCP server architecture, complete Docker orchestration, Alembic migration management, and extensive testing requirements for one-pass implementation success. The AI agent prompts are fully configurable and the MCP server provides scalable tool integration for the Chrome extension.

---

# 🔐 COMPREHENSIVE SECURITY, RISK, PERFORMANCE & CLOUD DEPLOYMENT ANALYSIS

## 🔒 Security Analysis & Hardening

### Critical Security Vulnerabilities & Mitigations

**1. AI/LLM Security Risks**
- **Prompt Injection Attacks**: User input could manipulate AI agents to perform unintended actions
- **Data Leakage**: AI models might expose sensitive information in responses
- **Model Poisoning**: Malicious file uploads could corrupt AI processing

*Mitigations:*
```python
# Input sanitization for AI prompts
def sanitize_user_input(user_input: str) -> str:
    # Remove potential injection patterns
    forbidden_patterns = ["ignore previous", "system:", "assistant:", "forget"]
    sanitized = user_input
    for pattern in forbidden_patterns:
        sanitized = sanitized.replace(pattern, "[FILTERED]")
    return sanitized[:2000]  # Length limit

# Content filtering for AI responses
def filter_ai_response(response: str) -> str:
    # Remove potentially sensitive data patterns
    import re
    # Remove API keys, emails, phone numbers
    response = re.sub(r'[A-Za-z0-9]{20,}', '[REDACTED]', response)
    return response
```

**2. File Upload Security**
- **Malicious File Execution**: Uploaded files could contain malware
- **Path Traversal**: File names could escape intended directories
- **Storage Exhaustion**: Large file uploads could exhaust disk space

*Enhanced Security Implementation:*
```python
import magic
from pathlib import Path
import hashlib

ALLOWED_MIME_TYPES = {
    'image/png', 'image/jpeg', 'image/gif',
    'audio/mpeg', 'audio/wav', 'video/mp4',
    'application/pdf', 'text/plain'
}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

async def secure_file_upload(file: UploadFile) -> Dict[str, Any]:
    # MIME type validation
    file_content = await file.read()
    detected_mime = magic.from_buffer(file_content, mime=True)
    
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, f"File type {detected_mime} not allowed")
    
    # Size validation
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large")
    
    # Generate secure filename
    file_hash = hashlib.sha256(file_content).hexdigest()[:16]
    safe_name = f"{file_hash}_{int(time.time())}.{file.filename.split('.')[-1]}"
    
    # Quarantine scan (integrate with ClamAV)
    if await scan_for_malware(file_content):
        raise HTTPException(400, "Malicious file detected")
    
    return {"safe_filename": safe_name, "content": file_content}
```

**3. WebSocket Security**
- **Connection Hijacking**: Unauthorized clients connecting to WebSocket
- **Message Spoofing**: Malicious clients sending fake messages
- **DoS via Connections**: Too many WebSocket connections

*Security Hardening:*
```python
from fastapi import WebSocket, HTTPException
import jwt

async def authenticate_websocket(websocket: WebSocket, token: str) -> DBUser:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        user = await get_user_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(401, "Invalid user")
        return user
    except jwt.InvalidTokenError:
        await websocket.close(code=4001)  # Unauthorized
        raise HTTPException(401, "Invalid token")

# Rate limiting for WebSocket messages
from collections import defaultdict
import time

class WebSocketRateLimiter:
    def __init__(self, max_messages_per_minute: int = 60):
        self.message_counts = defaultdict(list)
        self.max_messages = max_messages_per_minute
    
    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        self.message_counts[client_id] = [
            timestamp for timestamp in self.message_counts[client_id]
            if now - timestamp < 60  # Keep only last minute
        ]
        
        if len(self.message_counts[client_id]) >= self.max_messages:
            return False
            
        self.message_counts[client_id].append(now)
        return True
```

## ⚠️ Risk Assessment & Mitigation Strategies

### High-Impact Risks & Mitigation Plans

**1. AI Model Dependency Risks**
- **Risk**: OpenAI API outages, rate limits, cost escalation
- **Impact**: Complete AI functionality failure, $10K+/month costs
- **Probability**: Medium (30-40%)

*Multi-Provider Fallback Strategy:*
```yaml
# Enhanced ai_config.yaml with circuit breakers
ai_providers:
  primary:
    provider: "openai"
    model: "gpt-4o-mini"
    max_requests_per_minute: 1000
    circuit_breaker:
      failure_threshold: 5
      recovery_timeout: 300
  
  secondary:
    provider: "anthropic"
    model: "claude-3-haiku"
    max_requests_per_minute: 500
    
  tertiary:
    provider: "azure_openai"
    model: "gpt-35-turbo"
    max_requests_per_minute: 2000
    
cost_controls:
  monthly_budget_usd: 5000
  alert_threshold: 0.8
  hard_stop_threshold: 0.95
```

**2. Data Privacy & Compliance Risks**
- **Risk**: GDPR, CCPA violations from AI processing personal data
- **Impact**: €20M fines, legal liability
- **Probability**: High if not addressed (70-80%)

*Compliance Framework:*
```python
# Data classification and handling
from enum import Enum

class DataClassification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PII = "personally_identifiable"

class PrivacyCompliantProcessor:
    def __init__(self):
        self.pii_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b[\w\.-]+@[\w\.-]+\.\w+\b',  # Email
            r'\b\d{10,15}\b'  # Phone
        ]
    
    async def classify_content(self, content: str) -> DataClassification:
        for pattern in self.pii_patterns:
            if re.search(pattern, content):
                return DataClassification.PII
        return DataClassification.INTERNAL
    
    async def process_with_privacy(self, content: str, classification: DataClassification):
        if classification == DataClassification.PII:
            # Anonymize before AI processing
            content = self.anonymize_pii(content)
            # Log for audit trail
            await self.log_pii_processing(content, "anonymized_for_ai")
        
        return await self.ai_process(content)

# GDPR Right to Erasure implementation
async def handle_data_deletion_request(user_id: str):
    # Delete user data across all systems
    await delete_user_tickets(user_id)
    await delete_user_files(user_id) 
    await delete_ai_processing_logs(user_id)
    await delete_websocket_logs(user_id)
    # Notify integrations
    await notify_integrations_of_deletion(user_id)
```

**3. Third-Party Integration Risks**
- **Risk**: Jira/Salesforce API changes, authentication failures
- **Impact**: 50-80% of tickets fail to sync, customer escalation
- **Probability**: Medium-High (60-70%)

*Resilient Integration Architecture:*
```python
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio
from typing import Protocol

class IntegrationAdapter(Protocol):
    async def create_ticket(self, ticket_data: Dict) -> Dict[str, Any]: ...
    async def health_check(self) -> bool: ...

class ResilientIntegrationService:
    def __init__(self):
        self.adapters = {
            "jira": JiraAdapter(),
            "salesforce": SalesforceAdapter(),
            "github": GitHubAdapter()
        }
        self.fallback_queue = []
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def create_ticket_with_fallback(
        self, 
        ticket_data: Dict, 
        preferred_integration: str
    ) -> Dict[str, Any]:
        # Try preferred integration
        try:
            adapter = self.adapters[preferred_integration]
            if await adapter.health_check():
                return await adapter.create_ticket(ticket_data)
        except Exception as e:
            logger.error(f"Primary integration {preferred_integration} failed: {e}")
        
        # Try fallback integrations
        for name, adapter in self.adapters.items():
            if name != preferred_integration:
                try:
                    if await adapter.health_check():
                        result = await adapter.create_ticket(ticket_data)
                        logger.warning(f"Used fallback integration: {name}")
                        return result
                except Exception:
                    continue
        
        # All integrations failed - queue for retry
        await self.queue_for_retry(ticket_data, preferred_integration)
        raise IntegrationFailureError("All integrations unavailable")

# Integration health monitoring
async def monitor_integration_health():
    while True:
        for name, adapter in integration_service.adapters.items():
            try:
                healthy = await adapter.health_check()
                await update_integration_status(name, healthy)
                if not healthy:
                    await alert_operations_team(f"Integration {name} is down")
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
        
        await asyncio.sleep(300)  # Check every 5 minutes
```

## ⚡ Performance Analysis & Optimization

### Critical Performance Bottlenecks

**1. AI Processing Latency**
- **Current**: 2-15 seconds per AI request
- **Target**: <3 seconds for 95th percentile
- **Risk**: User abandonment after 8+ seconds

*Performance Optimization Strategy:*
```python
import asyncio
from functools import lru_cache
import hashlib

class AIPerformanceOptimizer:
    def __init__(self):
        self.response_cache = {}  # Redis-backed cache
        self.request_pool = asyncio.Semaphore(10)  # Limit concurrent requests
        
    @lru_cache(maxsize=1000)
    def get_cache_key(self, prompt: str, model: str) -> str:
        content_hash = hashlib.md5(prompt.encode()).hexdigest()
        return f"ai_response:{model}:{content_hash}"
    
    async def optimized_ai_request(
        self, 
        prompt: str, 
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        # Check cache first
        cache_key = self.get_cache_key(prompt, model)
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Use semaphore to limit concurrent requests
        async with self.request_pool:
            # Parallel processing for complex requests
            if len(prompt) > 5000:
                return await self.chunk_and_process(prompt, model)
            
            response = await self.ai_client.generate(prompt, model)
            
            # Cache successful responses for 1 hour
            await redis_client.setex(
                cache_key, 3600, json.dumps(response)
            )
            return response
    
    async def chunk_and_process(self, prompt: str, model: str) -> Dict[str, Any]:
        # Split large prompts into chunks for parallel processing
        chunks = self.split_prompt(prompt, max_size=2000)
        
        # Process chunks in parallel
        tasks = [
            self.ai_client.generate(chunk, model) 
            for chunk in chunks
        ]
        results = await asyncio.gather(*tasks)
        
        # Combine results
        return self.merge_responses(results)

# Async batch processing for multiple tickets
class BatchTicketProcessor:
    async def process_tickets_batch(
        self, 
        tickets: List[Dict], 
        batch_size: int = 5
    ) -> List[Dict]:
        results = []
        
        for i in range(0, len(tickets), batch_size):
            batch = tickets[i:i + batch_size]
            
            # Process batch in parallel
            tasks = [
                self.process_single_ticket(ticket) 
                for ticket in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            results.extend(batch_results)
            
            # Brief pause to avoid rate limits
            await asyncio.sleep(0.1)
        
        return results
```

**2. File Processing Performance**
- **Current**: 30-120 seconds for video transcription
- **Target**: <30 seconds for 95% of files
- **Scaling**: Process 100+ files simultaneously

*Optimized File Processing Pipeline:*
```python
from celery import group, chord
import asyncio

class OptimizedFileProcessor:
    def __init__(self):
        self.transcription_queue = "high_priority"
        self.ocr_queue = "medium_priority" 
        
    async def process_file_optimized(
        self, 
        file_path: str, 
        file_type: str
    ) -> Dict[str, Any]:
        file_size = os.path.getsize(file_path)
        
        # Route based on file size and type
        if file_type.startswith("video/") and file_size > 50 * 1024 * 1024:
            # Large video - chunk processing
            return await self.process_large_video(file_path)
        elif file_type.startswith("audio/"):
            # Audio - use fast Whisper model
            return await self.fast_transcribe.delay(file_path)
        elif file_type.startswith("image/"):
            # Image - parallel OCR with multiple engines
            return await self.parallel_ocr(file_path)
        else:
            return await self.standard_process(file_path)
    
    async def process_large_video(self, file_path: str) -> Dict[str, Any]:
        # Split video into 5-minute chunks
        chunks = await self.split_video_async(file_path, chunk_duration=300)
        
        # Process chunks in parallel using Celery chord
        chunk_tasks = group([
            transcribe_chunk.s(chunk_path) for chunk_path in chunks
        ])
        
        callback = merge_transcription_results.s()
        job = chord(chunk_tasks)(callback)
        
        # Return job ID for progress tracking
        return {"job_id": job.id, "status": "processing", "chunks": len(chunks)}

# High-performance database queries
class OptimizedTicketQueries:
    @staticmethod
    async def get_tickets_with_performance(
        user_id: int, 
        limit: int = 20,
        status_filter: str = None
    ) -> List[Dict]:
        query = """
        SELECT 
            t.id, t.title, t.status, t.priority, t.created_at,
            u.name as user_name,
            COUNT(f.id) as file_count,
            STRING_AGG(f.filename, ', ') as file_names
        FROM tickets t
        LEFT JOIN users u ON t.user_id = u.id  
        LEFT JOIN files f ON t.id = f.ticket_id
        WHERE t.user_id = $1
        AND ($2::text IS NULL OR t.status = $2::text)
        GROUP BY t.id, t.title, t.status, t.priority, t.created_at, u.name
        ORDER BY t.created_at DESC
        LIMIT $3
        """
        
        async with get_db_connection() as conn:
            rows = await conn.fetch(query, user_id, status_filter, limit)
            return [dict(row) for row in rows]

# Connection pooling and optimization
DATABASE_CONFIG = {
    "min_connections": 10,
    "max_connections": 50,
    "connection_timeout": 30,
    "command_timeout": 60,
    "server_settings": {
        "jit": "off",  # Disable JIT for faster small queries
        "application_name": "ticket_api"
    }
}
```

**3. WebSocket Performance & Scaling**
- **Target**: Support 10,000+ concurrent connections
- **Current Risk**: Memory exhaustion at 1,000+ connections

*High-Performance WebSocket Architecture:*
```python
import aioredis
from typing import Set
import ujson as json

class ScalableWebSocketManager:
    def __init__(self):
        self.redis = aioredis.from_url("redis://localhost:6379/0")
        self.connections: Dict[str, WebSocket] = {}
        self.connection_metadata = {}  # Store in Redis for scaling
        
    async def connect_optimized(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        
        # Store connection metadata in Redis for horizontal scaling
        await self.redis.hset(
            "websocket_connections",
            client_id,
            json.dumps({
                "connected_at": time.time(),
                "server_id": os.getenv("SERVER_ID", "server-1"),
                "subscriptions": []
            })
        )
        
        self.connections[client_id] = websocket
        
        # Set up heartbeat
        asyncio.create_task(self.heartbeat_loop(client_id, websocket))
    
    async def broadcast_optimized(
        self, 
        channel: str, 
        message: Dict[str, Any],
        target_clients: Set[str] = None
    ):
        # Use Redis pub/sub for horizontal scaling
        redis_message = {
            "channel": channel,
            "message": message,
            "target_clients": list(target_clients) if target_clients else None,
            "server_id": os.getenv("SERVER_ID", "server-1")
        }
        
        await self.redis.publish(
            f"websocket_broadcast:{channel}",
            json.dumps(redis_message)
        )
    
    async def handle_redis_message(self, message_data: Dict[str, Any]):
        channel = message_data["channel"]
        message = message_data["message"] 
        target_clients = message_data.get("target_clients")
        
        # Only broadcast to local connections
        clients_to_notify = (
            set(target_clients) & set(self.connections.keys())
            if target_clients
            else set(self.connections.keys())
        )
        
        # Batch send messages for performance
        if len(clients_to_notify) > 10:
            await self.batch_send_messages(clients_to_notify, message)
        else:
            tasks = [
                self.send_to_client(client_id, message)
                for client_id in clients_to_notify
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def batch_send_messages(self, client_ids: Set[str], message: Dict):
        # Send in batches of 50 to prevent overwhelming the event loop
        batch_size = 50
        client_list = list(client_ids)
        
        for i in range(0, len(client_list), batch_size):
            batch = client_list[i:i + batch_size]
            
            tasks = [
                self.send_to_client(client_id, message) 
                for client_id in batch
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Small delay between batches
            if i + batch_size < len(client_list):
                await asyncio.sleep(0.01)
```

## 📈 Scalability Architecture & Design Patterns

### Horizontal Scaling Strategy

**1. Multi-Tier Scaling Architecture**
```mermaid
graph TB
    LB[Load Balancer<br/>ALB/NLB] --> API1[API Instance 1]
    LB --> API2[API Instance 2] 
    LB --> API3[API Instance N]
    
    API1 --> Cache[Redis Cluster<br/>3 Masters + 3 Replicas]
    API2 --> Cache
    API3 --> Cache
    
    API1 --> DB_PRIMARY[PostgreSQL Primary<br/>Write Operations]
    API2 --> DB_READ1[Read Replica 1]
    API3 --> DB_READ2[Read Replica 2]
    
    DB_PRIMARY --> DB_READ1
    DB_PRIMARY --> DB_READ2
    
    API1 --> CELERY_BROKER[Redis/RabbitMQ<br/>Message Broker]
    
    CELERY_BROKER --> WORKER1[Celery Worker 1<br/>File Processing]
    CELERY_BROKER --> WORKER2[Celery Worker 2<br/>AI Processing] 
    CELERY_BROKER --> WORKER3[Celery Worker N<br/>Integration Sync]
    
    API1 --> MCP1[MCP Server 1]
    API2 --> MCP2[MCP Server 2]
    API3 --> MCP3[MCP Server N]
```

**2. Database Scaling Patterns**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import random

class DatabaseScaler:
    def __init__(self):
        # Primary database for writes
        self.primary_engine = create_engine(
            "postgresql://user:pass@primary-db:5432/tickets",
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True
        )
        
        # Read replicas for scaling reads
        self.read_replicas = [
            create_engine(f"postgresql://user:pass@replica-{i}:5432/tickets")
            for i in range(1, 4)  # 3 read replicas
        ]
        
        self.primary_session = sessionmaker(bind=self.primary_engine)
        self.read_sessions = [
            sessionmaker(bind=engine) for engine in self.read_replicas
        ]
    
    def get_write_session(self):
        """Always use primary for writes"""
        return self.primary_session()
    
    def get_read_session(self):
        """Load balance reads across replicas"""
        session_maker = random.choice(self.read_sessions)
        return session_maker()
    
    async def get_tickets_scalable(
        self, 
        user_id: int, 
        filters: Dict[str, Any] = None
    ) -> List[Dict]:
        # Use read replica for query
        session = self.get_read_session()
        try:
            # Implement query with proper indexing
            query = session.query(Ticket).filter(Ticket.user_id == user_id)
            
            if filters:
                if filters.get('status'):
                    query = query.filter(Ticket.status == filters['status'])
                if filters.get('created_after'):
                    query = query.filter(Ticket.created_at >= filters['created_after'])
            
            # Use pagination for large datasets  
            return query.limit(50).offset(filters.get('offset', 0)).all()
        finally:
            session.close()

# Database sharding for extreme scale
class ShardedTicketService:
    def __init__(self):
        # Shard by user_id hash for even distribution
        self.shards = {
            'shard_0': DatabaseScaler("postgresql://...shard-0:5432/tickets"),
            'shard_1': DatabaseScaler("postgresql://...shard-1:5432/tickets"),  
            'shard_2': DatabaseScaler("postgresql://...shard-2:5432/tickets"),
        }
    
    def get_shard_for_user(self, user_id: int) -> str:
        shard_id = user_id % len(self.shards)
        return f'shard_{shard_id}'
    
    async def create_ticket_sharded(self, user_id: int, ticket_data: Dict) -> Ticket:
        shard_name = self.get_shard_for_user(user_id)
        db_scaler = self.shards[shard_name]
        
        session = db_scaler.get_write_session()
        try:
            ticket = Ticket(**ticket_data, user_id=user_id)
            session.add(ticket)
            session.commit()
            return ticket
        finally:
            session.close()
```

**3. Caching Strategy for Scale**
```python
from redis.exceptions import RedisError
import pickle
from typing import Optional, Any

class MultiTierCaching:
    def __init__(self):
        # L1: In-memory cache (per instance)
        self.l1_cache = {}
        self.l1_max_size = 1000
        
        # L2: Redis cluster (shared across instances)
        self.redis_cluster = redis.RedisCluster(
            startup_nodes=[
                {"host": "redis-cluster-1", "port": "6379"},
                {"host": "redis-cluster-2", "port": "6379"},
                {"host": "redis-cluster-3", "port": "6379"},
            ],
            decode_responses=True,
            skip_full_coverage_check=True
        )
        
    async def get(self, key: str) -> Optional[Any]:
        # Try L1 cache first
        if key in self.l1_cache:
            return self.l1_cache[key]
        
        # Try L2 cache (Redis)
        try:
            value = await self.redis_cluster.get(key)
            if value:
                data = pickle.loads(value)
                # Warm L1 cache
                self.set_l1_cache(key, data)
                return data
        except RedisError:
            pass  # Fall through to database
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        # Set in both caches
        self.set_l1_cache(key, value)
        
        try:
            await self.redis_cluster.setex(
                key, ttl, pickle.dumps(value)
            )
        except RedisError:
            pass  # L1 cache still works
    
    def set_l1_cache(self, key: str, value: Any):
        # LRU eviction if cache full
        if len(self.l1_cache) >= self.l1_max_size:
            # Remove oldest item
            oldest_key = next(iter(self.l1_cache))
            del self.l1_cache[oldest_key]
        
        self.l1_cache[key] = value

# Application-specific caching
class TicketCacheService:
    def __init__(self):
        self.cache = MultiTierCaching()
        
    async def get_user_tickets_cached(
        self, 
        user_id: int, 
        filters: Dict[str, Any] = None
    ) -> List[Dict]:
        cache_key = f"user_tickets:{user_id}:{hash(str(filters))}"
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # Fall back to database
        tickets = await self.get_tickets_from_db(user_id, filters)
        
        # Cache for 5 minutes
        await self.cache.set(cache_key, tickets, ttl=300)
        return tickets
    
    async def invalidate_user_cache(self, user_id: int):
        # Pattern-based cache invalidation
        pattern = f"user_tickets:{user_id}:*"
        
        try:
            # Get all matching keys
            keys = await self.cache.redis_cluster.keys(pattern)
            if keys:
                await self.cache.redis_cluster.delete(*keys)
        except RedisError:
            pass  # Cache invalidation failure is not critical
```

**4. Auto-Scaling Configuration**
```yaml
# Kubernetes HPA configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ticket-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ticket-api
  minReplicas: 3
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: External
    external:
      metric:
        name: websocket_connections
        selector:
          matchLabels:
            service: ticket-api
      target:
        type: AverageValue
        averageValue: "1000"

---
# Celery Worker Auto-scaling
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: celery-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1 
    kind: Deployment
    name: celery-worker
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: External
    external:
      metric:
        name: celery_queue_length
        selector:
          matchLabels:
            queue: file_processing
      target:
        type: AverageValue
        averageValue: "10"  # Scale up if more than 10 jobs queued

---  
# MCP Server Auto-scaling
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-server-hpa  
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
```

**5. Circuit Breaker & Rate Limiting Patterns**
```python
import asyncio
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
import time

class CircuitBreakerState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests  
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: Exception = Exception

class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise CircuitBreakerError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        return (
            time.time() - self.last_failure_time 
            >= self.config.recovery_timeout
        )

# Distributed rate limiting
class DistributedRateLimiter:
    def __init__(self, redis_client, window_size: int = 60):
        self.redis = redis_client
        self.window_size = window_size
        
    async def is_allowed(
        self, 
        identifier: str, 
        limit: int, 
        window: int = None
    ) -> bool:
        window = window or self.window_size
        current_time = int(time.time())
        window_start = current_time - window
        
        pipe = self.redis.pipeline()
        
        # Remove expired entries
        pipe.zremrangebyscore(
            f"rate_limit:{identifier}", 
            0, 
            window_start
        )
        
        # Count current requests
        pipe.zcard(f"rate_limit:{identifier}")
        
        # Add current request
        pipe.zadd(
            f"rate_limit:{identifier}", 
            {current_time: current_time}
        )
        
        # Set expiry
        pipe.expire(f"rate_limit:{identifier}", window + 1)
        
        results = await pipe.execute()
        current_count = results[1]
        
        return current_count < limit
```

---

# 🏗️ PHASE-BASED DEVELOPMENT STRATEGY WITH TDD

## Complete Development Timeline

| Phase | Duration | Key Deliverables | Test Coverage Target | Success Criteria |
|-------|----------|------------------|---------------------|------------------|
| **Phase 1** | Weeks 1-3 | Core API, Auth, Basic CRUD | >95% | All basic endpoints working |
| **Phase 2** | Weeks 4-6 | AI Integration, MCP Server | >90% | AI agents creating tickets |
| **Phase 3** | Weeks 7-9 | WebSocket Protocols | >85% | Real-time notifications working |
| **Phase 4** | Weeks 10-12 | Third-party Integrations | >80% | All integrations functional |
| **Phase 5** | Weeks 13-15 | Performance & Security | >85% | Load tests passing |
| **Phase 6** | Weeks 16-18 | Cloud Deployment | >90% | Production launch successful |

### Phase 1: Core Infrastructure & Basic API (Weeks 1-3)

**Deliverables:**
- FastAPI application structure with Docker Compose
- Database models and migrations (Alembic)
- Basic CRUD endpoints for tickets
- Authentication system with JWT
- Basic file upload functionality

**Phase 1 Test Plan:**
```python
# tests/test_phase1_infrastructure.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.models.base import Base

# TDD Test Cases for Phase 1
class TestPhase1Infrastructure:
    """
    Phase 1 TDD Tests: Core Infrastructure
    
    Test-driven development approach:
    1. Write tests first (RED)
    2. Implement minimal code to pass (GREEN) 
    3. Refactor for quality (REFACTOR)
    """
    
    @pytest.fixture
    def client(self):
        # Test database setup
        engine = create_engine("postgresql://test:test@localhost:5432/ticket_test")
        TestSessionLocal = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        def override_get_db():
            db = TestSessionLocal()
            try:
                yield db
            finally:
                db.close()
        
        app.dependency_overrides[get_db] = override_get_db
        return TestClient(app)
    
    # RED: Write failing test first
    def test_app_startup(self, client):
        """Test that FastAPI app starts correctly"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    # RED: Write failing test first  
    def test_database_connection(self, client):
        """Test database connectivity"""
        response = client.get("/health/db")
        assert response.status_code == 200
        assert response.json()["database"] == "connected"
    
    # RED: Write failing test for user creation
    def test_create_user_endpoint(self, client):
        """Test user creation with proper validation"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com", 
            "password": "securepassword123"
        }
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        assert response.json()["username"] == "testuser"
        assert "password" not in response.json()  # Security check
    
    # RED: Write failing test for JWT authentication
    def test_jwt_authentication(self, client):
        """Test JWT token generation and validation"""
        # First create a user
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepassword123"
        }
        client.post("/api/v1/auth/register", json=user_data)
        
        # Test login
        login_data = {"username": "testuser", "password": "securepassword123"}
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"
        
        # Test protected endpoint with token
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["username"] == "testuser"

# tests/test_phase1_ticket_crud.py
class TestPhase1TicketCRUD:
    """TDD tests for basic ticket CRUD operations"""
    
    @pytest.fixture
    def authenticated_client(self, client):
        # Create user and get token
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepassword123"
        }
        client.post("/api/v1/auth/register", json=user_data)
        
        login_data = {"username": "testuser", "password": "securepassword123"}
        response = client.post("/api/v1/auth/login", json=login_data)
        token = response.json()["access_token"]
        
        client.headers.update({"Authorization": f"Bearer {token}"})
        return client
    
    # RED: Write failing test for ticket creation
    def test_create_ticket_basic(self, authenticated_client):
        """Test basic ticket creation"""
        ticket_data = {
            "title": "Test Issue",
            "description": "This is a test ticket",
            "priority": "medium",
            "category": "technical"
        }
        response = authenticated_client.post("/api/v1/tickets", json=ticket_data)
        assert response.status_code == 201
        assert response.json()["title"] == "Test Issue"
        assert response.json()["status"] == "open"
        assert response.json()["id"] is not None
    
    # RED: Write failing test for ticket validation
    def test_create_ticket_validation(self, authenticated_client):
        """Test ticket creation validation"""
        # Missing required fields
        invalid_ticket = {"title": ""}
        response = authenticated_client.post("/api/v1/tickets", json=invalid_ticket)
        assert response.status_code == 422
        
        # Invalid priority value
        invalid_ticket = {
            "title": "Test",
            "description": "Test", 
            "priority": "invalid_priority"
        }
        response = authenticated_client.post("/api/v1/tickets", json=invalid_ticket)
        assert response.status_code == 422
    
    # RED: Write failing test for ticket retrieval
    def test_get_user_tickets(self, authenticated_client):
        """Test retrieving user's tickets"""
        # Create a ticket first
        ticket_data = {
            "title": "Test Issue",
            "description": "This is a test ticket"
        }
        create_response = authenticated_client.post("/api/v1/tickets", json=ticket_data)
        ticket_id = create_response.json()["id"]
        
        # Get user's tickets
        response = authenticated_client.get("/api/v1/tickets")
        assert response.status_code == 200
        assert len(response.json()) >= 1
        assert any(ticket["id"] == ticket_id for ticket in response.json())
    
    # RED: Write failing test for ticket update
    def test_update_ticket(self, authenticated_client):
        """Test ticket update functionality"""
        # Create ticket
        ticket_data = {"title": "Original Title", "description": "Original description"}
        create_response = authenticated_client.post("/api/v1/tickets", json=ticket_data)
        ticket_id = create_response.json()["id"]
        
        # Update ticket
        update_data = {"title": "Updated Title", "status": "in_progress"}
        response = authenticated_client.put(f"/api/v1/tickets/{ticket_id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"
        assert response.json()["status"] == "in_progress"

# tests/test_phase1_file_upload.py  
class TestPhase1FileUpload:
    """TDD tests for basic file upload functionality"""
    
    def test_file_upload_basic(self, authenticated_client):
        """Test basic file upload"""
        # Create a test file
        test_file_content = b"This is a test file content"
        
        # Create ticket first
        ticket_data = {"title": "Test Ticket", "description": "For file upload"}
        ticket_response = authenticated_client.post("/api/v1/tickets", json=ticket_data)
        ticket_id = ticket_response.json()["id"]
        
        # Upload file
        files = {"file": ("test.txt", test_file_content, "text/plain")}
        data = {"ticket_id": ticket_id}
        response = authenticated_client.post("/api/v1/files/upload", files=files, data=data)
        
        assert response.status_code == 201
        assert response.json()["filename"] == "test.txt"
        assert response.json()["ticket_id"] == ticket_id
        assert response.json()["file_size"] == len(test_file_content)
    
    def test_file_upload_validation(self, authenticated_client):
        """Test file upload validation"""
        # Test file size limit
        large_file = b"x" * (100 * 1024 * 1024 + 1)  # Over 100MB
        files = {"file": ("large.txt", large_file, "text/plain")}
        data = {"ticket_id": 1}
        
        response = authenticated_client.post("/api/v1/files/upload", files=files, data=data)
        assert response.status_code == 413  # Payload Too Large
        
        # Test invalid file type (if restrictions exist)
        files = {"file": ("test.exe", b"executable", "application/x-executable")}
        response = authenticated_client.post("/api/v1/files/upload", files=files, data=data)
        assert response.status_code == 400  # Bad Request
```

**Phase 1 Validation Commands:**
```bash
# Run Phase 1 tests
poetry run pytest tests/test_phase1_* -v --cov=app --cov-report=term-missing

# Expected results:
# - All infrastructure tests pass
# - Basic CRUD operations work
# - File upload functionality works
# - Test coverage > 90% for Phase 1 code

# Start local development environment
docker compose up -d postgres redis

# Run database migrations
poetry run alembic upgrade head

# Start API server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Phase 2: AI Integration & MCP Server (Weeks 4-6)

**Deliverables:**
- MCP Server with FastMCP tools
- Pydantic AI agents (customer support, categorization)
- AI configuration management system
- File processing pipeline (transcription, OCR)
- Dynamic AI prompt management

**Phase 2 TDD Test Strategy:**
```python
# tests/test_phase2_mcp_server.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from mcp_server.tools.ticket_tools import analyze_file, create_ticket
from mcp_server.tools.file_analysis_tools import transcribe_audio, extract_text_from_image

class TestPhase2MCPServer:
    """
    Phase 2 TDD Tests: MCP Server Integration
    
    Focus on testing MCP tools and AI agent integration
    """
    
    # RED: Write failing test for MCP server startup
    @pytest.mark.asyncio
    async def test_mcp_server_startup(self):
        """Test MCP server starts and registers tools"""
        from mcp_server.start_mcp_server import mcp
        
        # Check that all expected tools are registered
        expected_tools = [
            "analyze_file",
            "create_ticket", 
            "search_knowledge_base",
            "create_integration_ticket"
        ]
        
        registered_tools = mcp.list_tools()
        for tool in expected_tools:
            assert tool in registered_tools
    
    # RED: Write failing test for analyze_file tool
    @pytest.mark.asyncio
    async def test_analyze_file_tool_audio(self):
        """Test analyze_file MCP tool with audio file"""
        with patch('mcp_server.tools.file_analysis_tools.transcription_service') as mock_service:
            # Mock transcription service response
            mock_service.transcribe_file.return_value = AsyncMock(return_value={
                "text": "Hello, this is a test audio file",
                "confidence": 0.95,
                "duration": 30.5
            })
            
            result = await analyze_file(
                file_path="/tmp/test_audio.mp3",
                file_type="audio/mp3",
                analysis_type="transcription"
            )
            
            assert result["analysis_type"] == "transcription"
            assert result["extracted_text"] == "Hello, this is a test audio file"
            assert result["confidence"] == 0.95
            assert result["metadata"]["duration"] == 30.5
    
    # RED: Write failing test for analyze_file tool with images
    @pytest.mark.asyncio
    async def test_analyze_file_tool_image(self):
        """Test analyze_file MCP tool with image file"""
        with patch('mcp_server.tools.file_analysis_tools.ocr_service') as mock_service:
            mock_service.extract_text.return_value = AsyncMock(return_value={
                "text": "Error: Login failed",
                "confidence": 0.88,
                "dimensions": {"width": 1920, "height": 1080}
            })
            
            result = await analyze_file(
                file_path="/tmp/screenshot.png",
                file_type="image/png", 
                analysis_type="ocr"
            )
            
            assert result["analysis_type"] == "ocr"
            assert result["extracted_text"] == "Error: Login failed"
            assert result["confidence"] == 0.88
            assert result["metadata"]["image_size"]["width"] == 1920
    
    # RED: Write failing test for create_ticket MCP tool
    @pytest.mark.asyncio
    async def test_create_ticket_tool(self):
        """Test create_ticket MCP tool"""
        with patch('mcp_server.tools.ticket_tools.ticket_service') as mock_service:
            # Mock ticket creation
            mock_ticket = MagicMock()
            mock_ticket.id = 123
            mock_ticket.title = "Login Issue"
            mock_ticket.status = "open"
            
            mock_service.create_ticket.return_value = AsyncMock(return_value=mock_ticket)
            
            result = await create_ticket(
                title="Login Issue",
                description="User cannot log in to application",
                category="technical",
                priority="high",
                attachments=["screenshot.png"],
                integration="jira"
            )
            
            assert result["ticket_id"] == 123
            assert result["status"] == "created"
            assert result["integration"] == "jira"
            
            # Verify service was called with correct parameters
            mock_service.create_ticket.assert_called_once()
            call_args = mock_service.create_ticket.call_args[0][0]
            assert call_args["title"] == "Login Issue"
            assert call_args["ai_generated"] == True

# tests/test_phase2_pydantic_ai_agents.py
class TestPhase2PydanticAI:
    """TDD tests for Pydantic AI agents"""
    
    @pytest.mark.asyncio
    async def test_customer_support_agent_initialization(self):
        """Test customer support agent initializes correctly"""
        from app.agents.customer_support_agent import customer_support_agent
        from pydantic_ai import Agent
        
        assert isinstance(customer_support_agent, Agent)
        assert customer_support_agent.result_type is not None
        assert "customer support agent" in customer_support_agent.system_prompt.lower()
    
    @pytest.mark.asyncio 
    async def test_customer_support_agent_simple_request(self):
        """Test customer support agent with simple ticket request"""
        from app.services.ai_agent_service import create_ticket_with_ai
        
        with patch('app.agents.customer_support_agent.customer_support_agent.run') as mock_run:
            # Mock AI agent response
            mock_result = MagicMock()
            mock_result.data = MagicMock()
            mock_result.data.ticket_title = "Cannot Access Application"
            mock_result.data.ticket_description = "User reports being unable to log into the application. Error message suggests invalid credentials."
            mock_result.data.category = "technical"
            mock_result.data.priority = "high"
            mock_result.data.confidence_score = 0.85
            mock_result.data.recommended_integration = "jira"
            
            mock_run.return_value = mock_result
            
            result = await create_ticket_with_ai(
                user_input="I can't log in to the app, keeps saying invalid credentials",
                files=[]
            )
            
            assert result.ticket_title == "Cannot Access Application"
            assert result.category == "technical"
            assert result.priority == "high"
            assert result.confidence_score >= 0.8
    
    @pytest.mark.asyncio
    async def test_customer_support_agent_with_files(self):
        """Test customer support agent with file analysis"""
        from app.services.ai_agent_service import create_ticket_with_ai
        
        with patch('app.agents.customer_support_agent.customer_support_agent.run') as mock_run:
            with patch('mcp_client.client.analyze_file') as mock_analyze:
                # Mock file analysis
                mock_analyze.return_value = {
                    "extracted_text": "Error: Connection timeout",
                    "confidence": 0.92
                }
                
                # Mock AI agent response
                mock_result = MagicMock()
                mock_result.data.ticket_title = "Connection Timeout Error"
                mock_result.data.ticket_description = "User experiencing connection timeout based on screenshot analysis"
                mock_result.data.category = "technical"
                mock_result.data.priority = "medium"
                mock_result.data.file_analysis_summary = "Screenshot shows connection timeout error"
                
                mock_run.return_value = mock_result
                
                result = await create_ticket_with_ai(
                    user_input="Getting an error, attached screenshot",
                    files=["/tmp/error_screenshot.png"]
                )
                
                assert result.ticket_title == "Connection Timeout Error"
                assert "timeout" in result.file_analysis_summary.lower()
                assert result.category == "technical"

# tests/test_phase2_ai_config.py
class TestPhase2AIConfig:
    """TDD tests for AI configuration management"""
    
    @pytest.mark.asyncio
    async def test_get_ai_config_endpoint(self, authenticated_client):
        """Test retrieving AI configuration"""
        response = authenticated_client.get("/api/v1/ai-config/customer_support_agent")
        assert response.status_code == 200
        
        config = response.json()
        assert config["agent_type"] == "customer_support_agent"
        assert "model" in config
        assert "temperature" in config
        assert "system_prompt" in config
        assert "tools_enabled" in config
    
    @pytest.mark.asyncio
    async def test_update_ai_config_endpoint(self, authenticated_client):
        """Test updating AI configuration"""
        update_data = {
            "system_prompt": "You are an enhanced customer support agent...",
            "temperature": 0.3,
            "max_tokens": 2500
        }
        
        response = authenticated_client.put(
            "/api/v1/ai-config/customer_support_agent",
            json=update_data
        )
        assert response.status_code == 200
        
        result = response.json()
        assert result["status"] == "updated"
        assert "version" in result
        assert result["changes"]["temperature"] == 0.3
    
    @pytest.mark.asyncio
    async def test_ai_config_validation(self, authenticated_client):
        """Test AI configuration validation"""
        # Invalid temperature value
        invalid_data = {"temperature": 2.5}  # Should be between 0 and 2
        
        response = authenticated_client.put(
            "/api/v1/ai-config/customer_support_agent",
            json=invalid_data
        )
        assert response.status_code == 400
        assert "validation" in response.json()["detail"].lower()

# tests/test_phase2_file_processing.py
class TestPhase2FileProcessing:
    """TDD tests for enhanced file processing pipeline"""
    
    @pytest.mark.asyncio
    async def test_audio_file_transcription_pipeline(self, authenticated_client):
        """Test complete audio file transcription pipeline"""
        # Create ticket
        ticket_data = {"title": "Voice Message", "description": "User left voice message"}
        ticket_response = authenticated_client.post("/api/v1/tickets", json=ticket_data)
        ticket_id = ticket_response.json()["id"]
        
        # Mock audio file
        audio_content = b"fake_audio_data"
        
        with patch('app.tasks.file_processing.transcribe_file_task.delay') as mock_task:
            mock_task.return_value.id = "task_123"
            
            files = {"file": ("message.mp3", audio_content, "audio/mp3")}
            data = {"ticket_id": ticket_id}
            
            response = authenticated_client.post("/api/v1/files/upload", files=files, data=data)
            
            assert response.status_code == 201
            assert response.json()["file_type"] == "audio/mp3"
            assert response.json()["processing_status"] == "queued"
            
            # Verify transcription task was queued
            mock_task.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_image_ocr_pipeline(self, authenticated_client):
        """Test complete image OCR processing pipeline"""
        # Create ticket
        ticket_data = {"title": "Error Screenshot", "description": "User provided error screenshot"}
        ticket_response = authenticated_client.post("/api/v1/tickets", json=ticket_data)
        ticket_id = ticket_response.json()["id"]
        
        # Mock image file
        image_content = b"fake_image_data"
        
        with patch('app.tasks.file_processing.ocr_file_task.delay') as mock_task:
            mock_task.return_value.id = "task_456"
            
            files = {"file": ("error.png", image_content, "image/png")}
            data = {"ticket_id": ticket_id}
            
            response = authenticated_client.post("/api/v1/files/upload", files=files, data=data)
            
            assert response.status_code == 201
            assert response.json()["file_type"] == "image/png"
            assert response.json()["processing_status"] == "queued"
            
            # Verify OCR task was queued
            mock_task.assert_called_once()
```

**Phase 2 Validation Commands:**
```bash
# Run Phase 2 specific tests
poetry run pytest tests/test_phase2_* -v --cov=app --cov-report=term-missing

# Test MCP server independently
cd mcp_server
python -m pytest tests/ -v

# Start MCP server for integration testing  
python mcp_server/start_mcp_server.py --port 8001

# Test MCP server health
curl http://localhost:8001/health

# Expected: {"status": "healthy", "tools_available": ["analyze_file", "create_ticket"]}

# Integration test: AI agent with MCP tools
poetry run pytest tests/test_integration_ai_mcp.py -v
```

### Phase 3: WebSocket Protocols & Real-time Features (Weeks 7-9)

**Deliverables:**
- Redis-based WebSocket architecture
- Ticket and file processing protocols  
- Real-time notifications system
- Protocol message validation
- Connection management and scaling

**Phase 3 TDD Test Strategy:**
```python
# tests/test_phase3_websocket_protocols.py
import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import WebSocket

class TestPhase3WebSocketProtocols:
    """
    Phase 3 TDD Tests: WebSocket Protocol Implementation
    
    Test all WebSocket message types and protocol behaviors
    """
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis for WebSocket testing"""
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock()
        mock_redis.subscribe = AsyncMock()
        mock_redis.hset = AsyncMock()
        mock_redis.hget = AsyncMock()
        return mock_redis
    
    # RED: Write failing test for WebSocket connection
    @pytest.mark.asyncio
    async def test_websocket_connection_authentication(self):
        """Test WebSocket connection with JWT authentication"""
        from app.routes.websocket import websocket_endpoint
        
        with TestClient(app) as client:
            # Get valid JWT token first
            user_data = {"username": "testuser", "email": "test@example.com", "password": "test123"}
            client.post("/api/v1/auth/register", json=user_data)
            
            login_response = client.post("/api/v1/auth/login", json={
                "username": "testuser", "password": "test123"
            })
            token = login_response.json()["access_token"]
            
            # Test WebSocket connection with token
            with client.websocket_connect(f"/ws?token={token}") as websocket:
                # Should successfully connect
                assert websocket is not None
                
                # Test invalid token
                with pytest.raises(Exception):
                    client.websocket_connect("/ws?token=invalid_token")
    
    # RED: Write failing test for ticket protocol messages
    @pytest.mark.asyncio
    async def test_ticket_protocol_subscribe_message(self, mock_redis):
        """Test ticket subscription WebSocket message"""
        from app.websocket.protocols.ticket_protocol import TicketProtocol
        
        protocol = TicketProtocol()
        mock_websocket = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = 123
        
        # Test valid subscription message
        message = {
            "type": "subscribe_ticket",
            "data": {"ticket_id": "456"}
        }
        
        with patch('app.websocket.protocols.ticket_protocol.websocket_manager') as mock_manager:
            mock_manager.subscribe_to_ticket = AsyncMock(return_value=True)
            
            await protocol.handle_message("client_123", message, mock_user, None)
            
            # Verify subscription was called
            mock_manager.subscribe_to_ticket.assert_called_once_with(
                "client_123", "456", "123"
            )
    
    # RED: Write failing test for message validation
    @pytest.mark.asyncio
    async def test_ticket_protocol_message_validation(self):
        """Test ticket protocol message validation"""
        from app.websocket.protocols.ticket_protocol import TicketProtocol
        
        protocol = TicketProtocol()
        
        # Test missing required fields
        invalid_message = {
            "type": "subscribe_ticket",
            "data": {}  # Missing ticket_id
        }
        
        with patch.object(protocol, 'send_error_response') as mock_error:
            await protocol.handle_message("client_123", invalid_message, None, None)
            
            mock_error.assert_called_once()
            error_args = mock_error.call_args[0]
            assert "Missing required fields" in error_args[1]
    
    # RED: Write failing test for file protocol
    @pytest.mark.asyncio
    async def test_file_protocol_job_subscription(self):
        """Test file processing job subscription"""
        from app.websocket.protocols.file_protocol import FileProtocol
        
        protocol = FileProtocol()
        mock_user = MagicMock()
        mock_user.id = 789
        
        message = {
            "type": "subscribe_job",
            "data": {"job_id": "file_processing_123"}
        }
        
        with patch('app.websocket.protocols.file_protocol.websocket_manager') as mock_manager:
            mock_manager.subscribe_to_job = AsyncMock(return_value=True)
            
            await protocol.handle_message("client_789", message, mock_user, None)
            
            mock_manager.subscribe_to_job.assert_called_once_with(
                "client_789", "file_processing_123", "789"
            )
    
    # RED: Write failing test for notification broadcasting
    @pytest.mark.asyncio
    async def test_notification_broadcasting(self, mock_redis):
        """Test WebSocket notification broadcasting"""
        from app.websocket.protocols.ticket_protocol import notify_ticket_status_update
        
        with patch('app.websocket.protocols.ticket_protocol.websocket_manager') as mock_manager:
            mock_manager.broadcast_ticket_update = AsyncMock()
            
            await notify_ticket_status_update(
                ticket_id="123",
                user_id="456",
                status="in_progress", 
                updated_by="user_789"
            )
            
            # Verify broadcast was called
            mock_manager.broadcast_ticket_update.assert_called_once()
            call_args = mock_manager.broadcast_ticket_update.call_args[0]
            
            assert call_args[0] == "123"  # ticket_id
            assert call_args[1] == "456"  # user_id
            
            notification_data = call_args[2]
            assert notification_data["type"] == "ticket_status_update"
            assert notification_data["status"] == "in_progress"
            assert "timestamp" in notification_data

# tests/test_phase3_redis_integration.py
class TestPhase3RedisIntegration:
    """TDD tests for Redis pub/sub integration"""
    
    @pytest.mark.asyncio
    async def test_redis_pubsub_setup(self):
        """Test Redis pub/sub connection setup"""
        from app.websocket.redis_pubsub import RedisPubSub
        
        with patch('aioredis.from_url') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            pubsub = RedisPubSub("redis://localhost:6379")
            await pubsub.connect()
            
            assert pubsub.redis is not None
            mock_redis.assert_called_once_with("redis://localhost:6379")
    
    @pytest.mark.asyncio
    async def test_redis_message_routing(self):
        """Test Redis message routing to WebSocket clients"""
        from app.websocket.message_router import MessageRouter
        
        router = MessageRouter()
        
        # Mock WebSocket manager
        with patch('app.websocket.message_router.websocket_manager') as mock_manager:
            mock_manager.send_to_client = AsyncMock()
            
            # Simulate Redis message
            redis_message = {
                "type": "ticket_status_update",
                "data": {"ticket_id": "123", "status": "resolved"},
                "target_clients": ["client_1", "client_2"]
            }
            
            await router.route_message("ticket_updates", json.dumps(redis_message))
            
            # Verify message was sent to target clients
            assert mock_manager.send_to_client.call_count == 2

# tests/test_phase3_websocket_scaling.py  
class TestPhase3WebSocketScaling:
    """TDD tests for WebSocket horizontal scaling"""
    
    @pytest.mark.asyncio
    async def test_connection_metadata_storage(self):
        """Test storing WebSocket connection metadata in Redis"""
        from app.websocket.manager import ScalableWebSocketManager
        
        with patch('aioredis.from_url') as mock_redis_factory:
            mock_redis = AsyncMock()
            mock_redis_factory.return_value = mock_redis
            
            manager = ScalableWebSocketManager()
            mock_websocket = AsyncMock()
            
            await manager.connect_optimized(mock_websocket, "client_123")
            
            # Verify connection metadata stored in Redis
            mock_redis.hset.assert_called_once()
            call_args = mock_redis.hset.call_args[0]
            assert call_args[0] == "websocket_connections"
            assert call_args[1] == "client_123"
    
    @pytest.mark.asyncio
    async def test_cross_server_message_handling(self):
        """Test handling messages from other server instances"""
        from app.websocket.manager import ScalableWebSocketManager
        
        manager = ScalableWebSocketManager()
        
        # Simulate message from another server
        message_data = {
            "channel": "ticket_updates",
            "message": {"type": "ticket_assigned", "ticket_id": "123"},
            "server_id": "server-2"  # Different server
        }
        
        with patch.object(manager, 'batch_send_messages') as mock_send:
            await manager.handle_redis_message(message_data)
            
            # Should not process messages from same server
            # But should process from different servers
            mock_send.assert_called_once()
```

**Phase 3 Validation Commands:**
```bash
# Run Phase 3 WebSocket tests
poetry run pytest tests/test_phase3_* -v --cov=app.websocket --cov-report=term-missing

# Test WebSocket connections with wscat
npm install -g wscat

# Start services
docker compose up -d redis
poetry run uvicorn app.main:app --reload &

# Test WebSocket connection  
wscat -c "ws://localhost:8000/ws?token=YOUR_JWT_TOKEN"

# Test message protocols
# Send: {"type": "subscribe_ticket", "data": {"ticket_id": "123"}}
# Expected: {"type": "subscription_response", "protocol": "ticket", "success": true}

# Test Redis pub/sub manually
redis-cli
> PUBLISH websocket_broadcast:ticket_updates '{"type":"ticket_status_update","data":{"ticket_id":"123","status":"resolved"}}'

# Load test WebSocket connections
poetry run python scripts/websocket_load_test.py --connections 100
```

### Local Development Workflow

**Development Environment Setup:**
```bash
# Initial setup (run once)
git clone <repository>
cd ai-ticket-creator-backend

# Install Poetry if not installed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Setup pre-commit hooks
poetry run pre-commit install

# Create environment file
cp .env.example .env
# Edit .env with your configuration

# Start local infrastructure
docker compose up -d postgres redis

# Run database migrations
poetry run alembic upgrade head

# Start MCP server (separate terminal)
poetry run python mcp_server/start_mcp_server.py --port 8001

# Start Celery worker (separate terminal)
poetry run celery -A app.celery_app worker --loglevel=info

# Start API server (separate terminal)
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Daily Development Workflow:**
```bash
# Morning startup
docker compose up -d  # Start infrastructure
poetry run alembic upgrade head  # Apply any new migrations

# TDD Development Cycle for each feature:

# 1. RED: Write failing test first
poetry run pytest tests/test_new_feature.py::test_specific_function -v
# Expected: Test fails ❌

# 2. GREEN: Write minimal code to pass test
# Edit source code...
poetry run pytest tests/test_new_feature.py::test_specific_function -v
# Expected: Test passes ✅

# 3. REFACTOR: Improve code quality while keeping tests passing
# Refactor code...
poetry run pytest tests/test_new_feature.py -v
# Expected: All tests still pass ✅

# 4. Run full test suite to ensure no regression
poetry run pytest tests/ --cov=app --cov-report=term-missing
# Expected: All tests pass, coverage > 90% ✅

# 5. Code quality checks
poetry run ruff check app/ --fix  # Auto-fix linting issues
poetry run mypy app/              # Type checking
poetry run bandit -r app/         # Security scanning

# 6. Commit changes
git add .
git commit -m "feat: implement new feature with TDD"
git push origin feature-branch
```

**Testing Strategy per Phase:**
```yaml
Phase_Testing_Approach:
  phase_1_core_infrastructure:
    test_focus: "Database models, basic API endpoints, authentication"
    run_command: "pytest tests/test_phase1_* -v"
    coverage_target: "> 95%"
    
  phase_2_ai_integration:
    test_focus: "MCP server, Pydantic AI agents, AI configuration"
    run_command: "pytest tests/test_phase2_* -v --cov=app.agents --cov=mcp_server"
    mock_strategy: "Mock all external AI API calls"
    
  phase_3_websocket_protocols:
    test_focus: "WebSocket message handling, Redis pub/sub, protocol validation"
    run_command: "pytest tests/test_phase3_* -v --cov=app.websocket"
    special_setup: "Redis container required for integration tests"
    
  phase_4_integrations:
    test_focus: "Third-party integrations, Celery tasks, webhook handling"
    run_command: "pytest tests/test_phase4_* -v --cov=app.services --cov=app.tasks"
    mock_strategy: "Mock all external API calls (Jira, Salesforce, etc.)"
    
  phase_5_performance:
    test_focus: "Caching, analytics, security, load testing"
    run_command: "pytest tests/test_phase5_* -v -m 'not slow'"
    load_tests: "pytest tests/test_phase5_load_testing.py -m slow"
```

---

# ☁️ AWS CLOUD DEPLOYMENT ARCHITECTURE

## Production-Ready AWS Infrastructure

**1. Core Services Architecture**
```yaml
# AWS Architecture Overview
PRODUCTION_STACK:
  compute:
    service: "Amazon EKS"
    node_groups:
      - name: "api-nodes"
        instance_type: "m5.large" 
        min_size: 3
        max_size: 50
        desired_size: 5
      - name: "worker-nodes"
        instance_type: "c5.xlarge"  # CPU-optimized for file processing
        min_size: 2
        max_size: 20
        desired_size: 3
    
  database:
    primary:
      service: "RDS PostgreSQL"
      instance_type: "db.r5.xlarge"
      multi_az: true
      backup_retention: 30
    read_replicas:
      count: 3
      instance_type: "db.r5.large"
      regions: ["us-west-2a", "us-west-2b", "us-west-2c"]
  
  cache:
    service: "ElastiCache Redis"
    node_type: "cache.r6g.large"
    num_cache_clusters: 3
    automatic_failover: true
    transit_encryption: true
    
  storage:
    files: 
      service: "S3"
      storage_class: "Standard-IA"  # For file attachments
      lifecycle_policy: "30 days -> Glacier"
    backups:
      service: "S3"
      storage_class: "Glacier Deep Archive"
    
  load_balancing:
    application: "Application Load Balancer"
    network: "Network Load Balancer"  # For WebSocket connections
    
  monitoring:
    metrics: "CloudWatch"
    logs: "CloudWatch Logs"
    tracing: "X-Ray"
    alerts: "SNS + PagerDuty"
```

**2. Kubernetes Deployment Manifests**
```yaml
# api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ticket-api
  namespace: production
spec:
  replicas: 5
  selector:
    matchLabels:
      app: ticket-api
  template:
    metadata:
      labels:
        app: ticket-api
    spec:
      serviceAccountName: ticket-api-sa
      containers:
      - name: ticket-api
        image: YOUR_ECR_REPO/ticket-api:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-secrets
              key: openai-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"  
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        
---
apiVersion: v1
kind: Service
metadata:
  name: ticket-api-service
  namespace: production
spec:
  selector:
    app: ticket-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
  
---
# celery-worker-deployment.yaml  
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
      - name: celery-worker
        image: YOUR_ECR_REPO/ticket-api:v1.0.0
        command: ["celery", "-A", "app.celery_app", "worker", "--loglevel=info"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret  
              key: url
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-secrets
              key: openai-key
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"

---
# mcp-server-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
    spec:
      containers:
      - name: mcp-server
        image: YOUR_ECR_REPO/mcp-server:v1.0.0
        ports:
        - containerPort: 8001
        env:
        - name: BACKEND_URL
          value: "http://ticket-api-service:80"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "125m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

**3. Terraform Infrastructure as Code**
```hcl
# main.tf - Complete AWS Infrastructure
terraform {
  required_version = ">= 1.0"
  backend "s3" {
    bucket = "ticket-api-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-west-2"
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC and Networking
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name        = "ticket-api-vpc"
    Environment = "production"
  }
}

resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  
  tags = {
    Name = "ticket-api-private-${count.index + 1}"
    Type = "private"
  }
}

resource "aws_subnet" "public" {
  count                   = 3
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 10}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  
  tags = {
    Name = "ticket-api-public-${count.index + 1}"
    Type = "public"
  }
}

# EKS Cluster
resource "aws_eks_cluster" "main" {
  name     = "ticket-api-cluster"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.24"

  vpc_config {
    subnet_ids = concat(aws_subnet.private[*].id, aws_subnet.public[*].id)
    
    endpoint_config {
      private_access = true
      public_access  = true
      public_access_cidrs = ["0.0.0.0/0"]
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
  ]
}

# RDS Database
resource "aws_db_subnet_group" "main" {
  name       = "ticket-api-db-subnet"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "ticket-api-db-subnet"
  }
}

resource "aws_db_instance" "primary" {
  identifier = "ticket-api-primary"
  
  engine         = "postgres"
  engine_version = "14.7"
  instance_class = "db.r5.xlarge"
  
  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_type         = "gp2"
  storage_encrypted    = true
  
  db_name  = "ticketapi"
  username = var.db_username
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "Sun:04:00-Sun:05:00"
  
  multi_az               = true
  publicly_accessible    = false
  
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn
  
  deletion_protection = true
  
  tags = {
    Name        = "ticket-api-primary"
    Environment = "production"
  }
}

# RDS Read Replicas
resource "aws_db_instance" "read_replica" {
  count = 2
  
  identifier = "ticket-api-replica-${count.index + 1}"
  
  replicate_source_db = aws_db_instance.primary.identifier
  instance_class      = "db.r5.large"
  
  auto_minor_version_upgrade = false
  publicly_accessible       = false
  
  tags = {
    Name        = "ticket-api-replica-${count.index + 1}"
    Environment = "production"
  }
}

# ElastiCache Redis Cluster
resource "aws_elasticache_subnet_group" "main" {
  name       = "ticket-api-cache-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "ticket-api-redis"
  description                = "Redis cluster for ticket API"
  
  node_type            = "cache.r6g.large"
  port                 = 6379
  parameter_group_name = "default.redis6.x"
  
  num_cache_clusters = 3
  
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                = var.redis_auth_token
  
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  tags = {
    Name        = "ticket-api-redis"
    Environment = "production"
  }
}

# S3 Bucket for File Storage
resource "aws_s3_bucket" "file_storage" {
  bucket = "ticket-api-files-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket_versioning" "file_storage" {
  bucket = aws_s3_bucket.file_storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "file_storage" {
  bucket = aws_s3_bucket.file_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "ticket-api-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = aws_subnet.public[*].id

  enable_deletion_protection = false

  tags = {
    Name        = "ticket-api-alb"
    Environment = "production"
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "app" {
  name              = "/aws/eks/ticket-api/app"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "celery" {
  name              = "/aws/eks/ticket-api/celery"
  retention_in_days = 30
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "db_username" {
  description = "Database username"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Database password" 
  type        = string
  sensitive   = true
}

variable "redis_auth_token" {
  description = "Redis authentication token"
  type        = string
  sensitive   = true
}

# Outputs
output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "database_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.primary.endpoint
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_replication_group.main.configuration_endpoint_address
}

output "s3_bucket" {
  description = "S3 bucket for file storage"
  value       = aws_s3_bucket.file_storage.bucket
}
```

**4. CI/CD Pipeline with GitHub Actions**
```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS

on:
  push:
    branches: [main]
    tags: ['v*']

env:
  AWS_REGION: us-west-2
  EKS_CLUSTER_NAME: ticket-api-cluster
  ECR_REPOSITORY: ticket-api

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: ticketapi_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python 3.12
      uses: actions/setup-python@v4
      with:
        python-version: "3.12"
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
      with:
        version: 1.8.3
        virtualenvs-create: true
        virtualenvs-in-project: true
    
    - name: Load cached venv
      id: cached-poetry-dependencies
      uses: actions/cache@v3
      with:
        path: .venv
        key: venv-${{ runner.os }}-${{ steps.setup-python.outputs.python-version }}-${{ hashFiles('**/poetry.lock') }}
    
    - name: Install dependencies
      if: steps.cached-poetry-dependencies.outputs.cache-hit != 'true'
      run: poetry install --no-interaction --no-ansi
    
    - name: Run tests
      run: |
        poetry run pytest tests/ -v --cov=app --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:test@localhost:5432/ticketapi_test
        REDIS_URL: redis://localhost:6379/0
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}
    
    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Build, tag, and push API image to Amazon ECR
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
    
    - name: Build, tag, and push MCP Server image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -f mcp_server/Dockerfile -t $ECR_REGISTRY/mcp-server:$IMAGE_TAG .
        docker push $ECR_REGISTRY/mcp-server:$IMAGE_TAG

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}
    
    - name: Update kubeconfig
      run: |
        aws eks update-kubeconfig --region ${{ env.AWS_REGION }} --name ${{ env.EKS_CLUSTER_NAME }}
    
    - name: Deploy to EKS
      env:
        IMAGE_TAG: ${{ github.sha }}
      run: |
        # Update deployment with new image
        kubectl set image deployment/ticket-api ticket-api=${{ secrets.ECR_REGISTRY }}/${{ env.ECR_REPOSITORY }}:$IMAGE_TAG
        kubectl set image deployment/mcp-server mcp-server=${{ secrets.ECR_REGISTRY }}/mcp-server:$IMAGE_TAG
        
        # Wait for rollout to complete
        kubectl rollout status deployment/ticket-api --timeout=300s
        kubectl rollout status deployment/mcp-server --timeout=300s
    
    - name: Run database migrations
      run: |
        kubectl run migration-job --image=${{ secrets.ECR_REGISTRY }}/${{ env.ECR_REPOSITORY }}:${{ github.sha }} --restart=Never --command -- alembic upgrade head
        kubectl wait --for=condition=complete job/migration-job --timeout=300s
        kubectl delete job migration-job
```

**5. Monitoring & Observability**
```yaml
# monitoring-stack.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
    - job_name: 'ticket-api'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names: ['production']
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: ticket-api
    - job_name: 'celery-workers'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names: ['production'] 
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: celery-worker

---
# CloudWatch Dashboard
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "ticket-api-alb"],
          ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "ticket-api-alb"],
          ["AWS/ApplicationELB", "HTTPCode_Target_4XX_Count", "LoadBalancer", "ticket-api-alb"],
          ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", "ticket-api-alb"]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-west-2",
        "title": "API Performance"
      }
    },
    {
      "type": "metric", 
      "properties": {
        "metrics": [
          ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", "ticket-api-primary"],
          ["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", "ticket-api-primary"],
          ["AWS/RDS", "ReadLatency", "DBInstanceIdentifier", "ticket-api-primary"],
          ["AWS/RDS", "WriteLatency", "DBInstanceIdentifier", "ticket-api-primary"]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-west-2",
        "title": "Database Performance"
      }
    }
  ]
}
```

**6. Cost Optimization Strategy**
```yaml
# Cost optimization recommendations
COST_OPTIMIZATION:
  compute:
    - Use Spot Instances for Celery workers (60-70% cost savings)
    - Right-size instances based on actual usage metrics
    - Use Graviton2 instances where possible (20% cost savings)
    
  database:
    - Use Aurora Serverless v2 for variable workloads
    - Implement connection pooling to reduce instance size
    - Schedule read replicas to scale down during low traffic
    
  storage:
    - Use S3 Intelligent-Tiering for automatic cost optimization
    - Implement lifecycle policies for old files
    - Use CloudFront CDN to reduce S3 requests
    
  monitoring:
    - Use CloudWatch Logs Insights instead of third-party tools
    - Set up billing alerts at 80% and 95% of budget
    - Use AWS Cost Explorer for ongoing optimization

# Monthly cost estimate (production workload)
ESTIMATED_MONTHLY_COSTS:
  compute: 
    eks_cluster: $216  # 3 m5.large nodes
    spot_workers: $150 # 5 c5.large spot instances  
  database:
    rds_primary: $450  # db.r5.xlarge multi-AZ
    read_replicas: $200 # 2x db.r5.large
  cache:
    elasticache: $220  # 3 cache.r6g.large nodes
  storage:
    s3: $100  # 1TB with lifecycle policies
    ebs: $50   # EKS node storage
  networking:
    alb: $25
    data_transfer: $50
  monitoring:
    cloudwatch: $75
  
  TOTAL: ~$1,536/month (scales with usage)
```

## 📋 Executive Summary & Implementation Roadmap

### Critical Success Factors

**Phase 1: Foundation (Months 1-2)**
- Implement security hardening for file uploads and AI processing
- Set up multi-provider AI fallback with circuit breakers  
- Deploy basic AWS infrastructure with Terraform
- Establish monitoring and alerting

**Phase 2: Scale Preparation (Months 3-4)**  
- Implement database read replicas and connection pooling
- Deploy Redis clustering for WebSocket scaling
- Set up auto-scaling groups and load balancers
- Implement comprehensive caching strategy

**Phase 3: Production Hardening (Months 5-6)**
- Deploy full CI/CD pipeline with automated testing
- Implement disaster recovery and backup strategies  
- Set up comprehensive monitoring and observability
- Conduct load testing and performance optimization

### Key Risk Mitigations Implemented

1. **AI Model Reliability**: Multi-provider fallback reduces single-point-of-failure risk from 70% to <10%
2. **Security**: File scanning, input sanitization, and encryption reduce breach risk by 85%
3. **Scalability**: Auto-scaling architecture supports 10x growth without manual intervention
4. **Performance**: Caching and optimization reduce response times from 8s to <3s
5. **Cost Control**: Spot instances and intelligent scaling reduce costs by 40-60%

### Production Readiness Checklist

- [ ] **Security**: Implement all security measures including file scanning and input validation
- [ ] **Performance**: Deploy caching layers and database read replicas  
- [ ] **Monitoring**: Set up CloudWatch dashboards and PagerDuty alerts
- [ ] **Scaling**: Configure auto-scaling for all service tiers
- [ ] **Disaster Recovery**: Implement automated backups and cross-AZ redundancy
- [ ] **Cost Optimization**: Deploy spot instances and lifecycle policies
- [ ] **Compliance**: Implement GDPR data handling and audit logging

**Estimated Timeline**: 6 months to production-ready deployment
**Estimated Budget**: $1,500-2,000/month operating costs at launch scale
**Expected Performance**: <3s API response times, 99.9% uptime, support for 10,000+ concurrent users

The architecture provides enterprise-grade reliability, security, and scalability while maintaining cost efficiency through AWS best practices and modern cloud-native patterns.