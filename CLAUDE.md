# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Ticket Creator Backend API - A FastAPI-based service for Chrome extension providing AI-powered ticket management, real-time processing, and third-party integrations. Features Pydantic AI agents, MCP (Model Context Protocol) server, file processing, and comprehensive WebSocket support.

## Development Commands

### Quick Start
```bash
# Start all services with Docker
docker compose up -d

# Check service health  
curl http://localhost:8000/health
curl http://localhost:8001/health  # MCP server
```

### Local Development
```bash
# Install dependencies
poetry install

# Start database and Redis only
docker compose up -d postgres redis

# Run database migrations
poetry run alembic upgrade head

# Start development servers (3 terminals needed)
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
poetry run python mcp_server/start_mcp_server.py  
poetry run celery -A app.celery_app worker --loglevel=info
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run specific test suites
poetry run pytest tests/test_simple.py -v
poetry run pytest tests/test_api_endpoints.py -v
poetry run pytest tests/test_services.py -v
poetry run pytest tests/test_ai_agents.py -v

# Run tests in Docker (recommended)
docker compose exec app poetry run pytest tests/test_simple.py -v
```

### Database Operations
```bash
# Create migration
poetry run alembic revision --autogenerate -m "Description"

# Apply migrations
poetry run alembic upgrade head

# Rollback migration  
poetry run alembic downgrade -1
```

## Architecture Overview

### Core Application Stack
- **FastAPI** application with async/await support
- **SQLAlchemy 2.0** ORM with **PostgreSQL 15** database
- **Pydantic v2** validation and **Pydantic AI** agents
- **Celery** with Redis broker for background tasks
- **WebSocket** support for real-time updates
- **Alembic** database migrations

### AI Integration Architecture
- **Pydantic AI Agents**: customer_support_agent.py, categorization_agent.py
- **MCP (Model Context Protocol)** server on port 8001 for tool-based AI interactions
- **Multi-provider support**: OpenAI, Google Gemini with fallback chains
- **AI configuration** via `app/config/ai_config.yaml` with environment overrides
- **File processing**: OCR, audio transcription, document analysis

### Service Organization
```
app/
├── agents/              # Pydantic AI agents for ticket processing
├── api/v1/             # FastAPI route handlers 
├── celery_app.py       # Background task configuration
├── config/             # Settings and AI configuration
├── middleware/         # Rate limiting and authentication
├── models/             # SQLAlchemy database models
├── schemas/            # Pydantic request/response schemas
├── services/           # Business logic layer
├── tasks/              # Celery background tasks
└── websocket/          # Real-time connection protocols

mcp_server/             # MCP server for AI tool integration
mcp_client/             # MCP client for connecting to tools
tests/                  # Comprehensive test suites
```

### Docker Services
- **app**: Main FastAPI application (port 8000)
- **mcp-server**: MCP tools server (port 8001)  
- **postgres**: Database (port 5432)
- **redis**: Cache and task broker (port 6379)
- **celery-worker**: Background task processor
- **flower**: Celery monitoring dashboard (port 5555)
- **test**: Testing service (profile: test)

## Key Technical Details

### Environment Configuration
Critical environment variables required:
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/ai_tickets
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=your-key
GEMINI_API_KEY=your-key
JWT_SECRET_KEY=your-256-bit-secret
```

### AI Agent Configuration
AI behavior configured in `app/config/ai_config.yaml`:
- **Multi-provider strategy**: Primary/fallback chains with cost controls
- **Agent-specific settings**: Different models for customer support vs categorization
- **Performance thresholds**: Auto-fallback on timeout, retry configuration
- **Quality controls**: Confidence scoring, safety measures

### API Endpoints Structure
- **Authentication**: `/api/v1/auth/*` (login, register, refresh, logout)
- **Tickets**: `/api/v1/tickets/*` (CRUD + AI-powered creation)
- **Files**: `/api/v1/files/*` (upload with processing, download)  
- **AI Services**: `/api/v1/ai/*` (categorization, file analysis)
- **Integrations**: `/api/v1/integrations/*` (third-party platforms)
- **WebSockets**: `/ws/*` (real-time updates)
- **System**: `/health`, `/docs`, `/redoc`

### Testing Strategy
- **test_simple.py**: Basic functionality and imports
- **test_api_endpoints.py**: API route testing
- **test_services.py**: Business logic validation  
- **test_ai_agents.py**: AI agent behavior testing
- **Docker testing**: Isolated test environment with separate database