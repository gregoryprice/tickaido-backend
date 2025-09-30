# FastMCP Client Authentication Implementation PRP

## Overview

Replace the current custom MCP client implementation with the official FastMCP client and implement token-based authentication following FastMCP best practices. This will simplify the authentication flow and eliminate the complex middleware approach.

## Problem Statement

The current MCP implementation has several issues:
1. Custom authentication wrapper that's complex and error-prone
2. Middleware-based principal injection that doesn't work reliably with FastMCP
3. Direct database access in MCP tools creates tight coupling
4. TaskGroup exceptions and connection issues with the current approach
5. 307 redirects and HTTP client lifecycle management problems

## Proposed Solution

### 1. Replace MCP Client with Official FastMCP Client

**Current Implementation:**
```python
# mcp_client/client.py - Complex custom wrapper
class MCPClient:
    def create_mcp_client(self, principal: Optional[Principal] = None):
        # Custom HTTP client creation
        # Manual JWT token injection
        # Complex authentication wrapper
```

**New Implementation:**
```python
# mcp_client/fast_client.py - Official FastMCP client
from fastmcp.client import FastMCPClient

class FastMCPClientWrapper:
    def __init__(self):
        self.client = FastMCPClient(
            url="http://mcp-server:8001/mcp",
            headers={"Authorization": "Bearer dev-alice-token"}
        )
        
    async def call_tool(self, tool_name: str, **kwargs):
        return await self.client.call_tool(tool_name, **kwargs)
```

**Package Dependencies:**
```toml
# pyproject.toml
[tool.poetry.dependencies]
fastmcp = "^0.3.0"  # Latest version from https://gofastmcp.com
```

### 2. Implement FastMCP Server with Token Authentication

**Current Implementation:**
```python
# mcp_server/start_mcp_server.py - Complex middleware approach
from fastmcp import FastMCP
# Custom middleware that doesn't work properly
```

**New Implementation:**
```python
# mcp_server/auth_server.py - Token-based authentication
from fastmcp import FastMCP
from fastmcp.auth import TokenAuth

# Configure token-based authentication
auth = TokenAuth({
    "dev-alice-token": {
        "user_id": "alice",
        "organization_id": "dev-org",
        "permissions": ["create_ticket", "list_tickets", "search_tickets"]
    },
    "ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8": {
        "user_id": "9cdd4c6c-a65d-464b-b3ba-64e6781fba2b",
        "organization_id": "20a8aae5-ec85-42a9-b025-45ee32a2f9a1",
        "permissions": ["create_ticket", "list_tickets", "search_tickets", "get_ticket"]
    }
})

mcp = FastMCP("AI Ticket Creator MCP Server", auth=auth)

@mcp.tool()
async def list_tickets(
    page: int = 1,
    page_size: int = 10,
    status: str = "",
    category: str = "",
    priority: str = ""
) -> str:
    """List tickets using API calls instead of direct database access."""
    # Get authentication context
    context = mcp.get_auth_context()
    user_id = context["user_id"]
    org_id = context["organization_id"]
    
    # Make API call to backend instead of direct database access
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://app:8000/api/v1/tickets",
            headers={"X-User-ID": user_id, "X-Organization-ID": org_id},
            params={"page": page, "page_size": page_size, "status": status}
        )
        return response.text
```

### 3. Enable Comprehensive Logging

```python
# mcp_server/auth_server.py
import logging
from fastmcp.logging import setup_logging

# Enable FastMCP logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log all tool calls and authentication
@mcp.middleware
async def logging_middleware(request, call_next):
    logger.info(f"Tool call: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response
```

### 4. Update Pydantic AI Agent Integration

**Current Implementation:**
```python
# app/services/dynamic_agent_factory.py
# Complex agent client creation with custom authentication
agent_client = mcp_client.get_agent_client(agent_id, tools, principal)
```

**New Implementation:**
```python
# app/services/dynamic_agent_factory.py
from mcp_client.fast_client import FastMCPClientWrapper

# Simple client creation with token authentication
async def create_agent_from_model(self, agent_model: AgentModel, principal: Principal):
    # Create FastMCP client with token
    token = principal.api_token  # JWT token from principal
    mcp_client = FastMCPClientWrapper(token=token)
    
    # Create Pydantic AI agent
    pydantic_agent = PydanticAgent(
        model=model_string,
        deps_type=Principal,
        output_type=ChatResponse,
        system_prompt=system_prompt,
        toolsets=[mcp_client]  # Use FastMCP client directly
    )
```

### 5. Convert MCP Tools to Use API Calls

**Current Implementation:**
```python
# mcp_server/tools/ticket_tools.py - Direct database access
async with get_db_session() as db:
    query = select(Ticket).where(...)
    result = await db.execute(query)
```

**New Implementation:**
```python
# mcp_server/tools/api_ticket_tools.py - API-based tools
@mcp.tool()
async def list_tickets(page: int = 1, page_size: int = 10, status: str = "") -> str:
    """List tickets via API call."""
    context = mcp.get_auth_context()
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://app:8000/api/v1/tickets",
            headers={
                "X-User-ID": context["user_id"],
                "X-Organization-ID": context["organization_id"]
            },
            params={"page": page, "page_size": page_size, "status": status}
        )
        
        if response.status_code == 200:
            return response.text
        else:
            return json.dumps({
                "error": f"API call failed: {response.status_code}",
                "message": response.text
            })

@mcp.tool()
async def create_ticket(title: str, description: str, category: str = "general") -> str:
    """Create ticket via API call."""
    context = mcp.get_auth_context()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://app:8000/api/v1/tickets/ai-create",
            headers={
                "X-User-ID": context["user_id"],
                "X-Organization-ID": context["organization_id"]
            },
            json={"title": title, "description": description, "category": category}
        )
        return response.text
```

## Implementation Steps

### Phase 1: FastMCP Client Replacement
1. **Install FastMCP Package**
   ```bash
   poetry add fastmcp@^0.3.0
   ```

2. **Create FastMCP Client Wrapper**
   - File: `mcp_client/fast_client.py`
   - Implement `FastMCPClientWrapper` class
   - Support token-based authentication
   - Enable logging

3. **Update Dynamic Agent Factory**
   - Replace custom MCP client with FastMCP client
   - Simplify agent creation logic
   - Remove complex authentication wrapper

### Phase 2: FastMCP Server with Token Auth
1. **Create New MCP Server**
   - File: `mcp_server/auth_server.py`
   - Implement token-based authentication
   - Configure user tokens and permissions
   - Enable comprehensive logging

2. **Convert Tools to API-based**
   - File: `mcp_server/tools/api_ticket_tools.py`
   - Replace direct database access with HTTP API calls
   - Use authentication context from FastMCP
   - Maintain same tool signatures

3. **Update Docker Configuration**
   - Update `mcp-server` service to use new server
   - Configure environment variables for API endpoints
   - Ensure proper networking between services

### Phase 3: Testing and Validation
1. **Create End-to-End Test**
   - File: `tests/e2e/test_fastmcp_integration.py`
   - Test complete flow from Pydantic AI to FastMCP to API
   - Verify token authentication works
   - Test all tool functions

2. **Manual Testing Script**
   ```bash
   # Test API endpoint directly
   curl -X POST http://localhost:8000/api/v1/chat/20a8aae5-ec85-42a9-b025-45ee32a2f9a1/threads/4aba8e44-6900-4c76-8b33-f8b96ca0e75b/messages \
     -H "Authorization: Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8" \
     -H "Content-Type: application/json" \
     -d '{"content": "what tools can you call?", "message_type": "user"}'
   ```

## Comprehensive Testing Strategy

### Phase 1: Unit Tests Update

#### 1.1 Update Existing MCP Client Tests
```python
# tests/unit/test_mcp_client.py - Update for FastMCP
import pytest
from mcp_client.fast_client import FastMCPClientWrapper

class TestFastMCPClient:
    """Test FastMCP client wrapper functionality."""
    
    def test_client_creation(self):
        """Test FastMCP client creation with token."""
        client = FastMCPClientWrapper(token="test-token")
        assert client is not None
        assert client.token == "test-token"
    
    def test_client_authentication_headers(self):
        """Test that client sets proper Authorization headers."""
        client = FastMCPClientWrapper(token="test-token-123")
        headers = client.get_headers()
        assert headers["Authorization"] == "Bearer test-token-123"
    
    @pytest.mark.asyncio
    async def test_tool_call_format(self):
        """Test that tool calls are properly formatted."""
        # Mock the FastMCP client response
        with patch('fastmcp.client.FastMCPClient.call_tool') as mock_call:
            mock_call.return_value = {"success": True, "data": []}
            
            client = FastMCPClientWrapper(token="test-token")
            result = await client.call_tool("list_tickets", page=1)
            
            # Verify call was made with correct parameters
            mock_call.assert_called_once_with("list_tickets", page=1)
            assert result["success"] is True
```

#### 1.2 Update Dynamic Agent Factory Tests
```python
# tests/unit/services/test_dynamic_agent_factory.py - Update for FastMCP integration
class TestDynamicAgentFactoryWithFastMCP:
    """Test agent factory with FastMCP integration."""
    
    @pytest.mark.asyncio
    async def test_create_agent_with_fastmcp_tools(self):
        """Test agent creation with FastMCP tools."""
        agent_model = create_test_agent_model(tools=["list_tickets", "create_ticket"])
        principal = create_test_principal()
        
        agent = await dynamic_agent_factory.create_agent_from_model(
            agent_model, principal
        )
        
        assert agent is not None
        # Verify FastMCP toolset is attached
        assert len(agent.toolsets) == 1
        assert hasattr(agent.toolsets[0], 'call_tool')
    
    @pytest.mark.asyncio 
    async def test_agent_tool_calling(self):
        """Test that agent can call tools through FastMCP."""
        with patch('mcp_client.fast_client.FastMCPClientWrapper.call_tool') as mock_call:
            mock_call.return_value = '{"success": true, "tickets": []}'
            
            agent_model = create_test_agent_model(tools=["list_tickets"])
            principal = create_test_principal()
            
            response = await dynamic_agent_factory.process_message_with_agent(
                agent_model, "list my tickets", create_test_context(), principal
            )
            
            assert response.confidence > 0
            assert mock_call.called
```

#### 1.3 New FastMCP Server Tests
```python
# tests/unit/test_fastmcp_server.py - New test file
import pytest
import httpx
from fastapi.testclient import TestClient

class TestFastMCPServer:
    """Test FastMCP server with token authentication."""
    
    def test_server_startup(self):
        """Test that FastMCP server starts correctly."""
        from mcp_server.auth_server import app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_token_authentication(self):
        """Test token-based authentication."""
        from mcp_server.auth_server import auth
        
        # Test valid token
        context = auth.authenticate("ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8")
        assert context is not None
        assert context["user_id"] == "9cdd4c6c-a65d-464b-b3ba-64e6781fba2b"
        
        # Test invalid token
        context = auth.authenticate("invalid-token")
        assert context is None
    
    @pytest.mark.asyncio
    async def test_api_based_tool_calls(self):
        """Test that tools make API calls instead of direct DB access."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = '{"success": true, "tickets": []}'
            
            from mcp_server.tools.api_ticket_tools import list_tickets
            
            # Mock auth context
            with patch('fastmcp.FastMCP.get_auth_context') as mock_context:
                mock_context.return_value = {
                    "user_id": "test-user",
                    "organization_id": "test-org"
                }
                
                result = await list_tickets(page=1, page_size=5)
                
                # Verify API call was made
                mock_get.assert_called_once()
                assert "success" in result
```

### Phase 2: Integration Tests

#### 2.1 FastMCP Client-Server Integration
```python
# tests/integration/test_fastmcp_integration.py
import pytest
import httpx
from testcontainers import DockerCompose

class TestFastMCPIntegration:
    """Integration tests for FastMCP client-server communication."""
    
    @pytest.fixture(scope="class")
    def docker_services(self):
        """Start services for integration testing."""
        with DockerCompose(".", compose_file_name="compose.test.yml") as compose:
            # Wait for services to be ready
            compose.wait_for("http://localhost:8001/health")
            compose.wait_for("http://localhost:8000/health")
            yield compose
    
    @pytest.mark.asyncio
    async def test_fastmcp_client_server_communication(self, docker_services):
        """Test FastMCP client can communicate with server."""
        from mcp_client.fast_client import FastMCPClientWrapper
        
        client = FastMCPClientWrapper(
            url="http://localhost:8001/mcp",
            token="ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"
        )
        
        # Test tool listing
        tools = await client.list_tools()
        assert len(tools) > 0
        assert any(tool.name == "list_tickets" for tool in tools)
        
        # Test tool calling
        result = await client.call_tool("list_tickets", page=1, page_size=5)
        assert "success" in result or "tickets" in result
    
    @pytest.mark.asyncio
    async def test_pydantic_ai_fastmcp_integration(self, docker_services):
        """Test Pydantic AI agent with FastMCP tools."""
        from app.services.dynamic_agent_factory import dynamic_agent_factory
        from app.models.ai_agent import Agent as AgentModel
        from app.schemas.principal import Principal
        
        # Create test agent with FastMCP tools
        agent_model = create_test_agent_model(
            tools=["list_tickets", "create_ticket"]
        )
        principal = Principal(
            user_id="9cdd4c6c-a65d-464b-b3ba-64e6781fba2b",
            organization_id="20a8aae5-ec85-42a9-b025-45ee32a2f9a1",
            email="test@test.com",
            api_token="ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"
        )
        
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model,
            "what tools can you call?",
            create_test_context(),
            principal
        )
        
        assert response.confidence > 0
        assert "tool" in response.content.lower()
        # Verify no TaskGroup exceptions occurred
        assert not response.requires_escalation
```

### Phase 3: End-to-End Tests

#### 3.1 Complete API Flow Test
```python
# tests/e2e/test_complete_fastmcp_flow.py
import pytest
import httpx
import asyncio
from testcontainers import DockerCompose

class TestCompleteFastMCPFlow:
    """End-to-end tests for complete FastMCP integration."""
    
    @pytest.fixture(scope="class")
    def full_environment(self):
        """Start complete environment for E2E testing."""
        with DockerCompose(".", compose_file_name="compose.test.yml") as compose:
            # Wait for all services
            services = ["app", "mcp-server", "postgres", "redis"]
            for service in services:
                compose.wait_for(f"http://localhost:800{services.index(service)}/health")
            yield compose
    
    @pytest.mark.asyncio
    async def test_chat_api_with_tool_calling(self, full_environment):
        """Test the exact API call from the PRP requirements."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:8000/api/v1/chat/20a8aae5-ec85-42a9-b025-45ee32a2f9a1/threads/4aba8e44-6900-4c76-8b33-f8b96ca0e75b/messages",
                headers={
                    "Authorization": "Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8",
                    "Content-Type": "application/json"
                },
                json={
                    "content": "what tools can you call?",
                    "message_type": "user"
                }
            )
            
            # Verify successful response
            assert response.status_code == 200
            data = response.json()
            
            # Verify tool information is in response
            assert "tool" in data["content"].lower()
            assert data["confidence"] > 0
            
            # Verify tools were actually called
            assert len(data.get("tools_used", [])) > 0
    
    @pytest.mark.asyncio
    async def test_tool_functionality_end_to_end(self, full_environment):
        """Test individual tools work end-to-end."""
        test_cases = [
            {
                "message": "list my tickets",
                "expected_tools": ["list_tickets"],
                "expected_content_keywords": ["ticket", "list"]
            },
            {
                "message": "create a ticket for testing FastMCP",
                "expected_tools": ["create_ticket"],
                "expected_content_keywords": ["ticket", "created", "testing"]
            },
            {
                "message": "search for tickets about FastMCP",
                "expected_tools": ["search_tickets"],
                "expected_content_keywords": ["search", "ticket", "fastmcp"]
            }
        ]
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            for test_case in test_cases:
                response = await client.post(
                    "http://localhost:8000/api/v1/chat/20a8aae5-ec85-42a9-b025-45ee32a2f9a1/threads/4aba8e44-6900-4c76-8b33-f8b96ca0e75b/messages",
                    headers={
                        "Authorization": "Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8",
                        "Content-Type": "application/json"
                    },
                    json={
                        "content": test_case["message"],
                        "message_type": "user"
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Check that expected tools were used
                tools_used = [tool["name"] for tool in data.get("tools_used", [])]
                for expected_tool in test_case["expected_tools"]:
                    assert expected_tool in tools_used
                
                # Check content contains expected keywords
                content = data["content"].lower()
                for keyword in test_case["expected_content_keywords"]:
                    assert keyword in content
```

### Phase 4: Docker Log Validation

#### 4.1 Automated Log Checking
```python
# tests/validation/test_docker_logs.py
import pytest
import subprocess
import re
from typing import List, Dict

class TestDockerLogsValidation:
    """Validate that Docker logs contain no errors after FastMCP implementation."""
    
    def get_container_logs(self, service_name: str) -> str:
        """Get logs for a specific Docker service."""
        try:
            result = subprocess.run(
                ["docker", "compose", "logs", service_name],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to get logs for {service_name}: {e}")
    
    def test_app_service_logs_no_errors(self):
        """Test that app service has no error logs."""
        logs = self.get_container_logs("app")
        
        # Check for common error patterns
        error_patterns = [
            r"ERROR.*TaskGroup",
            r"ERROR.*unhandled errors",
            r"ERROR.*MCP.*failed",
            r"❌.*MCP",
            r"CRITICAL",
            r"Exception.*not caught",
            r"Traceback.*most recent call"
        ]
        
        errors = []
        for pattern in error_patterns:
            matches = re.findall(pattern, logs, re.IGNORECASE)
            errors.extend(matches)
        
        if errors:
            pytest.fail(f"Found {len(errors)} error patterns in app logs:\n" + "\n".join(errors[:5]))
    
    def test_mcp_server_logs_healthy(self):
        """Test that MCP server logs show healthy operation."""
        logs = self.get_container_logs("mcp-server")
        
        # Check for success patterns
        success_patterns = [
            r"✅.*FastMCP.*server.*started",
            r"✅.*Token.*authentication.*enabled",
            r"✅.*Tools.*registered",
            r"INFO.*Starting.*FastMCP"
        ]
        
        success_count = 0
        for pattern in success_patterns:
            if re.search(pattern, logs, re.IGNORECASE):
                success_count += 1
        
        assert success_count >= 2, f"MCP server logs show insufficient success indicators: {success_count}/4"
        
        # Check for error patterns
        error_patterns = [
            r"ERROR.*authentication",
            r"ERROR.*tool.*call",
            r"❌.*Failed",
            r"CRITICAL"
        ]
        
        errors = []
        for pattern in error_patterns:
            matches = re.findall(pattern, logs, re.IGNORECASE)
            errors.extend(matches)
        
        if errors:
            pytest.fail(f"Found {len(errors)} errors in MCP server logs:\n" + "\n".join(errors))
    
    def test_no_connection_errors(self):
        """Test that there are no connection errors between services."""
        services = ["app", "mcp-server", "postgres", "redis"]
        
        connection_error_patterns = [
            r"Connection.*refused",
            r"Connection.*reset",
            r"Connection.*timeout",
            r"Unable to connect",
            r"HTTP.*50[0-9]",
            r"307.*Temporary Redirect"  # Should be eliminated
        ]
        
        all_errors = []
        for service in services:
            logs = self.get_container_logs(service)
            service_errors = []
            
            for pattern in connection_error_patterns:
                matches = re.findall(pattern, logs, re.IGNORECASE)
                service_errors.extend([f"{service}: {match}" for match in matches])
            
            all_errors.extend(service_errors)
        
        if all_errors:
            pytest.fail(f"Found connection errors:\n" + "\n".join(all_errors[:10]))
```

### Phase 5: Performance and Load Testing

#### 5.1 FastMCP Performance Tests
```python
# tests/performance/test_fastmcp_performance.py
import pytest
import asyncio
import time
import httpx
from statistics import mean, median

class TestFastMCPPerformance:
    """Performance tests to ensure FastMCP implementation is efficient."""
    
    @pytest.mark.asyncio
    async def test_tool_call_latency(self):
        """Test that tool calls complete within acceptable time."""
        from mcp_client.fast_client import FastMCPClientWrapper
        
        client = FastMCPClientWrapper(token="ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8")
        
        latencies = []
        for _ in range(10):
            start_time = time.time()
            await client.call_tool("list_tickets", page=1, page_size=5)
            latency = time.time() - start_time
            latencies.append(latency)
        
        avg_latency = mean(latencies)
        median_latency = median(latencies)
        
        # Assert performance requirements
        assert avg_latency < 2.0, f"Average latency too high: {avg_latency:.2f}s"
        assert median_latency < 1.5, f"Median latency too high: {median_latency:.2f}s"
        assert max(latencies) < 5.0, f"Max latency too high: {max(latencies):.2f}s"
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """Test FastMCP handles concurrent tool calls efficiently."""
        from mcp_client.fast_client import FastMCPClientWrapper
        
        client = FastMCPClientWrapper(token="ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8")
        
        async def make_tool_call():
            return await client.call_tool("list_tickets", page=1, page_size=3)
        
        # Test 5 concurrent calls
        start_time = time.time()
        tasks = [make_tool_call() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # All calls should succeed
        assert len(results) == 5
        for result in results:
            assert "success" in result or "tickets" in result
        
        # Should complete faster than 5 sequential calls
        assert total_time < 10.0, f"Concurrent calls took too long: {total_time:.2f}s"
```

### Phase 6: Test Configuration Updates

#### 6.1 Update Test Configuration Files
```yaml
# compose.test.yml - Test environment configuration
version: '3.8'

services:
  app:
    build: .
    environment:
      - DATABASE_URL=postgresql+asyncpg://test:test@postgres:5432/test_db
      - MCP_SERVER_URL=http://mcp-server:8001
      - FASTMCP_TOKEN=ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8
    depends_on:
      - postgres
      - redis
      - mcp-server
    ports:
      - "8000:8000"

  mcp-server:
    build:
      context: .
      dockerfile: mcp_server/Dockerfile
    environment:
      - FASTMCP_LOG_LEVEL=DEBUG
      - API_BASE_URL=http://app:8000
    ports:
      - "8001:8001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=test_db
      - POSTGRES_USER=test
      - POSTGRES_PASSWORD=test
    ports:
      - "5433:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"
```

#### 6.2 Update pytest configuration
```ini
# pytest.ini - Updated test configuration
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=app
    --cov=mcp_client
    --cov=mcp_server
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80

markers =
    asyncio: async test functions
    integration: integration tests
    e2e: end-to-end tests
    performance: performance tests
    docker: tests requiring docker services

filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

## Test Execution Plan

### Sequential Test Phases
1. **Unit Tests** - Fast, isolated component tests
2. **Integration Tests** - Service-to-service communication
3. **E2E Tests** - Complete user flow validation
4. **Docker Log Validation** - Zero error tolerance
5. **Performance Tests** - Latency and concurrency validation

### Test Commands
```bash
# Run all tests with coverage
poetry run pytest --cov=app --cov=mcp_client --cov=mcp_server

# Run specific test categories
poetry run pytest tests/unit/ -v
poetry run pytest tests/integration/ -v
poetry run pytest tests/e2e/ -v
poetry run pytest tests/validation/ -v
poetry run pytest tests/performance/ -v

# Run with Docker log validation
docker compose up -d && poetry run pytest tests/validation/test_docker_logs.py

# Run the specific API test from PRP requirements
poetry run pytest tests/e2e/test_complete_fastmcp_flow.py::TestCompleteFastMCPFlow::test_chat_api_with_tool_calling -v
```

## Expected Benefits

1. **Simplified Architecture**: Official FastMCP client eliminates custom authentication wrapper
2. **Reliable Authentication**: Token-based auth is simpler and more reliable than JWT middleware
3. **Better Separation of Concerns**: MCP server uses API calls instead of direct database access
4. **Improved Logging**: FastMCP built-in logging provides better visibility
5. **Easier Maintenance**: Using official packages reduces maintenance burden
6. **Cleaner Error Handling**: No more TaskGroup exceptions or HTTP client lifecycle issues

## Files to Create/Modify

### New Files
- `mcp_client/fast_client.py` - FastMCP client wrapper
- `mcp_server/auth_server.py` - New FastMCP server with token auth
- `mcp_server/tools/api_ticket_tools.py` - API-based tools
- `tests/e2e/test_fastmcp_integration.py` - E2E tests

### Modified Files
- `app/services/dynamic_agent_factory.py` - Use FastMCP client
- `docker-compose.yml` - Update MCP server configuration
- `pyproject.toml` - Add FastMCP dependency
- `.env` - Add FastMCP configuration

### Removed Files
- `mcp_client/authenticated_client.py` - No longer needed
- `mcp_server/middleware/principal_injection.py` - Replaced by token auth
- `mcp_server/tools/ticket_tools.py` - Replaced by API-based tools

## Success Criteria

### Core Functionality
✅ **FastMCP client successfully connects to server with token authentication**
✅ **All MCP tools work through API calls instead of direct database access**  
✅ **Pydantic AI agents can call MCP tools without TaskGroup exceptions**
✅ **Token `ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8` works for authentication**
✅ **Comprehensive logging shows all authentication and tool calls**
✅ **No 307 redirects or HTTP client lifecycle issues**

### Testing Requirements
✅ **All unit tests pass (100% success rate)**
- MCP client tests updated for FastMCP
- Dynamic agent factory tests updated  
- FastMCP server tests added

✅ **All integration tests pass (100% success rate)**
- FastMCP client-server communication verified
- Pydantic AI with FastMCP integration tested
- Service-to-service communication validated

✅ **E2E test passes with exact API call from requirements:**
```bash
POST /api/v1/chat/20a8aae5-ec85-42a9-b025-45ee32a2f9a1/threads/4aba8e44-6900-4c76-8b33-f8b96ca0e75b/messages
Authorization: Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8
{"content": "what tools can you call?"}
```

✅ **Docker log validation passes (zero errors)**
- No TaskGroup exceptions in app logs
- No MCP connection errors
- No 307 Temporary Redirect responses
- No authentication failures
- All services show healthy startup messages

✅ **Performance tests meet requirements**
- Tool call latency < 2.0s average
- Concurrent tool calls work efficiently
- No memory leaks or resource exhaustion

### Test Coverage Requirements
✅ **Minimum 80% code coverage maintained**
✅ **All existing tests updated to work with FastMCP**
✅ **New tests added for FastMCP-specific functionality**
✅ **Test suite runs without warnings or failures**

### Deployment Validation
✅ **Docker compose up -d succeeds without errors**
✅ **All services pass health checks**
✅ **MCP server logs show successful tool registration**
✅ **App logs show successful FastMCP client creation**

### Manual Verification Checklist
- [ ] FastMCP package installed at latest version (^0.3.0)
- [ ] Token authentication configured correctly  
- [ ] All tools converted to API-based calls
- [ ] Logging enabled and working
- [ ] Test API call returns expected response
- [ ] No error patterns in any Docker service logs
- [ ] Performance within acceptable limits

This implementation will provide a clean, maintainable, and reliable MCP integration using official FastMCP packages with proper token-based authentication, backed by comprehensive testing that ensures zero errors and optimal performance.