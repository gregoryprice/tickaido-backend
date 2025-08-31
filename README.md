# AI Ticket Creator - Backend API

## Project Overview

Backend service for the AI Ticket Creator Chrome extension, providing comprehensive API endpoints for AI-powered ticket management, file processing, real-time notifications, and third-party integrations.

## Core Features

### 🎫 AI-Powered Ticket Management
- REST API for ticket CRUD operations with Pydantic validation
- **Pydantic AI agents** for intelligent ticket categorization and priority assignment
- **MCP (Model Context Protocol)** server integration for tool-based AI interactions
- Automated ticket routing and assignment
- Real-time status updates via WebSocket connections

### 🤖 Advanced AI Integration
- **Customer Support Agent**: Natural language ticket creation with context analysis
- **Categorization Agent**: Intelligent ticket classification and priority scoring
- **Multi-modal file processing**: Audio transcription, image OCR, document analysis
- **Knowledge base search** with semantic similarity matching
- Configurable AI models (OpenAI, Anthropic, local models)

### 📁 File Processing & Analysis
- Support for multiple file types: images, audio, video, documents
- **AI-powered transcription** for audio/video files
- **OCR capabilities** for image-based content extraction
- **Real-time processing** with Celery background tasks
- Automated metadata extraction and content analysis

### 🔗 Third-Party Integrations
- **Salesforce**: Case management and synchronization
- **Jira**: Issue tracking integration with project mapping
- **ServiceNow**: Enterprise service management
- **Zendesk**: Customer support platform integration
- **GitHub**: Issue creation and management
- **Slack & Microsoft Teams**: Real-time notifications
- **Zoom**: Meeting integration and recording analysis

### 🔐 Security & Authentication
- **JWT-based authentication** with refresh token support
- **Role-based access control** (Admin, User roles)
- **API rate limiting** with Redis-backed sliding window
- **bcrypt password hashing** with secure configuration
- **WebSocket authentication** for real-time connections

### 📊 Monitoring & Analytics
- **Health check endpoints** with service status monitoring
- **Flower dashboard** for Celery task monitoring
- **Comprehensive logging** with structured error handling
- **Performance metrics** and system health indicators

## Tech Stack

### Core Framework
- **Runtime**: Python 3.12
- **Framework**: FastAPI with async/await support
- **Database**: PostgreSQL 15 with SQLAlchemy 2.0 ORM
- **Migration**: Alembic for database schema management
- **Validation**: Pydantic v2 for request/response validation

### AI & Processing
- **AI Framework**: Pydantic AI with multi-provider support
- **MCP Integration**: FastMCP for tool-based AI interactions
- **Task Queue**: Celery with Redis broker
- **File Processing**: Pillow, PyPDF2, speech recognition libraries

### Infrastructure
- **Containerization**: Docker with multi-service compose setup
- **Documentation**: OpenAPI 3.0 with Swagger UI and ReDoc
- **Testing**: pytest with asyncio support
- **Monitoring**: Flower for Celery, structured logging

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.12+ (for local development)
- PostgreSQL 15+ (handled by Docker)
- Redis (handled by Docker)

### Quick Start with Docker

```bash
# Clone the repository
git clone <repository-url>
cd support-extension

# Copy environment configuration
cp .env.example .env
# Edit .env with your API keys and configuration

# Start all services
docker compose up -d

# Check service health
curl http://localhost:8000/health
curl http://localhost:8001/health  # MCP server
```

### Services Overview
- **Main API**: http://localhost:8000 (FastAPI with Swagger docs at `/docs`)
- **MCP Server**: http://localhost:8001 (AI tools and integrations)
- **Flower Dashboard**: http://localhost:5555 (Celery task monitoring)
- **PostgreSQL**: localhost:5432 (Database)
- **Redis**: localhost:6379 (Cache and task broker)

### Environment Configuration

Key environment variables (see `.env.example` for complete list):

```env
# Database
DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/ai_tickets"

# AI Configuration
OPENAI_API_KEY="your-openai-key"
ANTHROPIC_API_KEY="your-anthropic-key"

# Authentication
JWT_SECRET_KEY="your-256-bit-secret-key"

# Third-party Integrations
SALESFORCE_CLIENT_ID="your-salesforce-client-id"
SALESFORCE_CLIENT_SECRET="your-salesforce-client-secret"
JIRA_URL="your-jira-instance-url"
JIRA_EMAIL="your-jira-email"
JIRA_API_TOKEN="your-jira-token"
SLACK_BOT_TOKEN="your-slack-bot-token"

# System Configuration
REDIS_URL="redis://localhost:6379/0"
LOG_LEVEL="INFO"
ENVIRONMENT="development"
```

## API Endpoints

### Authentication
```
POST   /api/v1/auth/login         # User login
POST   /api/v1/auth/register      # User registration
POST   /api/v1/auth/refresh       # Token refresh
DELETE /api/v1/auth/logout        # User logout
```

### Tickets
```
GET    /api/v1/tickets            # List tickets with pagination
POST   /api/v1/tickets            # Create ticket (with AI processing)
GET    /api/v1/tickets/{id}       # Get ticket details
PUT    /api/v1/tickets/{id}       # Update ticket
DELETE /api/v1/tickets/{id}       # Delete ticket
POST   /api/v1/tickets/ai         # AI-powered ticket creation
```

### File Management
```
POST   /api/v1/files/upload       # Upload file with processing
GET    /api/v1/files/{id}         # Get file details
GET    /api/v1/files/{id}/content # Download file content
DELETE /api/v1/files/{id}         # Delete file
```

### AI Services
```
POST   /api/v1/ai/categorize      # Categorize ticket content
POST   /api/v1/ai/analyze-file    # Analyze uploaded file
GET    /api/v1/ai/agents/status   # Get AI agents status
```

### Integrations
```
GET    /api/v1/integrations              # List available integrations
POST   /api/v1/integrations/{platform}  # Connect integration
GET    /api/v1/integrations/{platform}  # Get integration status
PUT    /api/v1/integrations/{platform}  # Update integration settings
DELETE /api/v1/integrations/{platform}  # Disconnect integration
```

### WebSocket Endpoints
```
WS     /ws/tickets               # Real-time ticket updates
WS     /ws/files                 # File processing status
WS     /ws/notifications         # System notifications
```

### System & Monitoring
```
GET    /health                   # System health check
GET    /docs                     # Swagger UI documentation
GET    /redoc                    # ReDoc documentation
GET    /openapi.json             # OpenAPI specification
```

## Development

### Local Development Setup

```bash
# Install Poetry for dependency management
pip install poetry

# Install dependencies
poetry install

# Set up environment
cp .env.example .env

# Start database and Redis
docker compose up -d postgres redis

# Run database migrations
poetry run alembic upgrade head

# Start development server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start MCP server
poetry run python mcp_server/start_mcp_server.py

# In another terminal, start Celery worker
poetry run celery -A app.celery_app.celery_app worker --loglevel=info
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run specific test suites
poetry run pytest tests/test_simple.py -v          # Basic functionality
poetry run pytest tests/test_api_endpoints.py -v   # API endpoints
poetry run pytest tests/test_services.py -v        # Business logic

# Run tests in Docker (recommended)
docker compose exec app poetry run pytest tests/test_simple.py -v
```

### Database Operations

```bash
# Create new migration
poetry run alembic revision --autogenerate -m "Description"

# Apply migrations
poetry run alembic upgrade head

# Rollback migration
poetry run alembic downgrade -1
```

## Project Structure

```
app/
├── agents/                 # Pydantic AI agents
│   ├── customer_support_agent.py
│   ├── categorization_agent.py
│   └── prompts.py
├── api/                   # API routes
│   └── v1/               # API version 1
│       ├── auth.py
│       ├── tickets.py
│       ├── files.py
│       └── integrations.py
├── celery_app/           # Background task processing
│   ├── celery_app.py
│   └── tasks/
├── config/               # Configuration management
│   ├── settings.py
│   └── ai_config.yaml
├── database/             # Database configuration
│   ├── database.py
│   └── migrations/       # Alembic migrations
├── middleware/           # FastAPI middleware
│   ├── auth_middleware.py
│   └── rate_limiting.py
├── models/               # SQLAlchemy models
│   ├── base.py
│   ├── ticket.py
│   ├── user.py
│   ├── file.py
│   └── integration.py
├── schemas/              # Pydantic schemas
│   ├── ticket.py
│   ├── user.py
│   └── file.py
├── services/             # Business logic services
│   ├── ticket_service.py
│   ├── ai_service.py
│   ├── file_service.py
│   ├── user_service.py
│   └── integration_service.py
├── websocket/            # WebSocket handlers
│   └── protocols/
└── main.py              # FastAPI application

mcp_server/               # MCP server implementation
├── start_mcp_server.py
└── tools/               # MCP tools

mcp_client/              # MCP client integration
└── client.py

tests/                   # Test suites
├── test_simple.py       # Basic functionality tests
├── test_api_endpoints.py # API endpoint tests
├── test_services.py     # Service layer tests
└── test_ai_agents.py    # AI agent tests

docker-compose.yml       # Multi-service Docker setup
Dockerfile              # Main application container
pyproject.toml          # Poetry configuration and dependencies
alembic.ini            # Database migration configuration
```

## AI Configuration

The system supports multiple AI providers configured via `ai_config.yaml`:

```yaml
ai_providers:
  openai:
    api_key_env: "OPENAI_API_KEY"
    models:
      - gpt-4o-mini
      - gpt-3.5-turbo
  anthropic:
    api_key_env: "ANTHROPIC_API_KEY"
    models:
      - claude-3-sonnet-20240229

agents:
  customer_support_agent:
    model_provider: "openai"
    model_name: "gpt-4o-mini"
    temperature: 0.7
    system_prompt: "You are a helpful customer support agent..."
  
  categorization_agent:
    model_provider: "openai"
    model_name: "gpt-3.5-turbo"
    temperature: 0.3
    system_prompt: "You categorize support tickets accurately..."
```

## Docker Services

The application runs as a multi-container setup:

| Service | Description | Port | Health Check |
|---------|-------------|------|--------------|
| **app** | Main FastAPI application | 8000 | `/health` |
| **mcp-server** | MCP tools server | 8001 | `/health` |
| **postgres** | PostgreSQL database | 5432 | Built-in |
| **redis** | Cache and task broker | 6379 | Built-in |
| **celery-worker** | Background task processor | - | Flower dashboard |
| **flower** | Celery monitoring | 5555 | Web interface |

## Deployment

### Production Deployment

```bash
# Set production environment
export ENVIRONMENT=production

# Build and deploy
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Run database migrations
docker compose exec app poetry run alembic upgrade head

# Check all services
docker compose ps
```

### Health Monitoring

All services provide health check endpoints:

```bash
# Check main API health
curl http://localhost:8000/health

# Check MCP server health  
curl http://localhost:8001/health

# Monitor Celery tasks
open http://localhost:5555
```

## Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** following the existing code style
4. **Add comprehensive tests** for new functionality
5. **Run the test suite**: `docker compose exec app poetry run pytest`
6. **Update documentation** as needed
7. **Submit a pull request** with detailed description

### Development Guidelines

- Follow **Python PEP 8** style guidelines
- Use **type hints** for all function parameters and returns
- Write **comprehensive tests** for new features
- Add **docstrings** for all public functions and classes
- Update **OpenAPI documentation** for new endpoints
- Ensure all **tests pass** before submitting PR

## License

MIT License - see LICENSE file for details

---

## Quick Reference

### Essential Commands

```bash
# Start everything
docker compose up -d

# View logs
docker compose logs -f app

# Run tests
docker compose exec app poetry run pytest tests/test_simple.py -v

# Database migration
docker compose exec app poetry run alembic upgrade head

# Check system health
curl http://localhost:8000/health
```

### Important URLs
- **API Documentation**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health  
- **MCP Server**: http://localhost:8001/health
- **Task Monitor**: http://localhost:5555
- **ReDoc**: http://localhost:8000/redoc