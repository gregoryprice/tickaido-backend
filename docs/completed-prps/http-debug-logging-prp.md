# HTTP Debug Logging System - Product Requirements Document (PRD)

## Overview

This document outlines the HTTP Debug Logging system implemented for the AI Ticket Creator Backend API to provide comprehensive debugging capabilities for HTTP requests and responses with third-party integrations (Jira, AI providers, and other external services).

## Problem Statement

During development and troubleshooting of third-party integrations, developers need visibility into:
- Actual HTTP request/response payloads sent to/received from external APIs
- Request/response headers for authentication and API versioning issues
- Request timing for performance analysis
- Pretty-formatted JSON for easier debugging

Previously, debugging HTTP communication required manual logging additions or external tools, making it difficult to:
- Troubleshoot integration failures in production
- Validate API request formats against third-party documentation
- Monitor request/response patterns for optimization
- Debug authentication and authorization issues

## Solution

A comprehensive HTTP debug logging utility that provides:
- **Centralized logging**: Single utility for all HTTP debug logging across the application
- **Pretty-printed JSON**: Formatted JSON bodies for easy reading
- **Sensitive data protection**: Automatic sanitization of authentication headers and sensitive parameters
- **Configurable logging**: Enable/disable via environment variables
- **Request correlation**: Unique request IDs to match requests with responses
- **Performance tracking**: Request duration measurements

## Technical Implementation

### Core Components

#### 1. HTTP Debug Logger Utility (`app/utils/http_debug_logger.py`)

**Key Features:**
- `HTTPDebugLogger` class with configurable logging levels
- Pretty JSON formatting with length limiting to prevent log flooding
- Header sanitization (masks sensitive auth tokens, API keys)
- Parameter sanitization (masks passwords, secrets, tokens)
- Request/response correlation via unique request IDs
- Support for both `httpx.Response` objects and dict responses

**Main Functions:**
```python
# Log individual request or response
log_http_request(method, url, headers, params, json_data, data)
log_http_response(response, request_id, duration_ms)

# Log request/response pair in one call
log_http_request_response_pair(method, url, response, headers, params, json_data, data, duration_ms)

# Global configuration
enable_http_debug_logging(enabled=True, log_level=logging.DEBUG)
```

#### 2. Integration Points

**Jira Integration (`app/services/jira_integration.py`):**
- Added debug logging to key methods: `test_connection()`, `get_projects()`, `create_issue()`
- Logs authentication requests, project queries, and ticket creation API calls
- Captures request timing for performance monitoring

**MCP HTTP Client (`mcp_server/tools/http_client.py`):**
- Integrated into the `make_request()` method for all MCP server HTTP communications
- Handles authentication header sanitization for security
- Provides debug visibility into MCP tool HTTP requests

**Integration Service (`app/services/integration_service.py`):**
- Added to Salesforce, Slack, and webhook test methods
- Provides debug logging for integration connectivity tests
- Captures OAuth flows and API authentication processes

#### 3. Configuration System

**Environment Variables:**
- `HTTP_DEBUG_LOGGING_ENABLED`: Boolean flag to enable/disable debug logging
- `HTTP_DEBUG_LOG_LEVEL`: Log level for debug messages (DEBUG, INFO, WARNING, etc.)

**Settings Integration:**
- Added to `app/config/settings.py` with Pydantic field validation
- Automatic loading from environment variables and .env files
- Default values: disabled in production, DEBUG level when enabled

**Application Startup:**
- Initialization in `app/main.py` startup event
- Automatic configuration based on environment settings
- Graceful fallback if initialization fails

### Security Considerations

#### Sensitive Data Protection

**Headers Sanitization:**
- Authorization headers: Shows first 8 and last 4 characters of tokens
- API keys: Completely masked as `[REDACTED]`
- Cookies and session data: Fully masked
- Custom authentication headers: Automatically detected and masked

**Parameter Sanitization:**
- Password fields: Masked in URL parameters and form data
- Secret/token parameters: Automatically detected and masked
- API key parameters: Completely hidden

**Example Sanitized Output:**
```
Authorization: Bearer abcd1234...xyz9
api_key: [REDACTED]
password: [REDACTED]
```

#### Production Safety

- Disabled by default to prevent accidental logging in production
- Configurable log levels to control verbosity
- Length limiting to prevent log file overflow
- No sensitive data exposure in error conditions

## Usage Examples

### Enable Debug Logging

**Via Environment Variables:**
```bash
export HTTP_DEBUG_LOGGING_ENABLED=true
export HTTP_DEBUG_LOG_LEVEL=DEBUG
```

**Via .env File:**
```env
HTTP_DEBUG_LOGGING_ENABLED=true
HTTP_DEBUG_LOG_LEVEL=DEBUG
```

### Sample Debug Output

**Request Log:**
```
================================================================================
🔍 HTTP REQUEST [req_1704067200123]
Method: POST
URL: https://company.atlassian.net/rest/api/3/issue
Headers:
  authorization: Basic dXNlcjpwYXNz...xyz9
  content-type: application/json
  accept: application/json
JSON Body:
{
  "fields": {
    "project": {
      "key": "SUPPORT"
    },
    "issuetype": {
      "name": "Bug"
    },
    "summary": "Integration test ticket",
    "description": {
      "type": "doc",
      "version": 1,
      "content": [
        {
          "type": "paragraph",
          "content": [
            {
              "type": "text",
              "text": "This is a test ticket for integration debugging"
            }
          ]
        }
      ]
    }
  }
}
================================================================================
```

**Response Log:**
```
================================================================================
📡 HTTP RESPONSE [req_1704067200123]
Status: 201
Duration: 1247.82ms
Headers:
  content-type: application/json;charset=UTF-8
  server: AtlassianEdge
Response Body:
{
  "id": "12345",
  "key": "SUPPORT-123",
  "self": "https://company.atlassian.net/rest/api/3/issue/12345"
}
================================================================================
```

## Implementation Benefits

### For Development
- **Faster debugging**: Immediate visibility into API communication issues
- **API compliance**: Easy validation against third-party API documentation
- **Integration testing**: Comprehensive logging during integration development

### For Operations
- **Production troubleshooting**: Quick diagnosis of integration failures
- **Performance monitoring**: Request timing data for optimization
- **Security auditing**: Sanitized logs safe for security review

### For Maintenance
- **Consistent logging**: Standardized format across all HTTP integrations
- **Centralized control**: Single configuration point for all debug logging
- **Future-proof**: Easy to add to new integrations

## Integration Coverage

### Current Integrations
- ✅ **Jira Integration**: Complete coverage of API calls (auth, projects, issue creation)
- ✅ **MCP HTTP Client**: All MCP server communications
- ✅ **Integration Service**: Salesforce, Slack, and webhook testing
- ✅ **Application Startup**: Automatic configuration based on environment

### Future Integration Points
- **AI Provider Communications**: OpenAI, Anthropic, Google Gemini API calls
- **File Processing Services**: OCR, transcription, document analysis
- **WebSocket Communications**: Real-time update protocols
- **OAuth Flows**: Third-party authentication processes

## Configuration Reference

### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `HTTP_DEBUG_LOGGING_ENABLED` | boolean | `false` | Enable HTTP debug logging |
| `HTTP_DEBUG_LOG_LEVEL` | string | `"DEBUG"` | Log level for debug messages |

### Log Levels
- **DEBUG**: Detailed request/response logging with full bodies
- **INFO**: Basic request/response logging with minimal details
- **WARNING**: Only log failed or suspicious requests
- **ERROR**: Only log request/response errors

## Rollout Plan

### Phase 1: Core Implementation ✅
- [x] HTTP debug logger utility
- [x] Jira integration logging
- [x] MCP HTTP client logging
- [x] Configuration system
- [x] Application startup integration

### Phase 2: Extended Coverage (Next)
- [ ] AI provider integration logging
- [ ] File processing service logging
- [ ] Enhanced error correlation
- [ ] Metrics collection integration

### Phase 3: Advanced Features (Future)
- [ ] Log aggregation and search
- [ ] Performance analytics dashboard
- [ ] Automated anomaly detection
- [ ] Integration with monitoring systems

## Success Metrics

### Development Efficiency
- **Debugging time reduction**: 50% faster issue resolution
- **Integration development speed**: 30% faster new integration development
- **Bug reproduction rate**: 80% of integration issues reproducible from logs

### System Reliability
- **Mean Time to Resolution (MTTR)**: Reduction in integration failure resolution time
- **Error detection rate**: Earlier detection of API communication issues
- **Production stability**: Reduced integration-related outages

### Developer Experience
- **Log utility adoption**: Usage across all new integrations
- **Documentation completeness**: Self-documenting API communication patterns
- **Testing effectiveness**: Enhanced integration test debugging capabilities

## Maintenance and Support

### Code Maintenance
- **Location**: `app/utils/http_debug_logger.py`
- **Dependencies**: Standard library (`json`, `logging`, `time`) + `httpx`
- **Testing**: Unit tests for sanitization and formatting functions
- **Documentation**: Inline docstrings and usage examples

### Monitoring
- **Log volume monitoring**: Track debug log size and frequency
- **Performance impact**: Monitor overhead of debug logging
- **Configuration compliance**: Ensure production safety settings

### Updates and Evolution
- **New integration types**: Easy addition of debug logging to new services
- **Enhanced sanitization**: Add new patterns for sensitive data protection
- **Performance optimization**: Continuous improvement of logging efficiency

---

**Document Version**: 1.0  
**Created**: 2025-01-10  
**Last Updated**: 2025-01-10  
**Status**: Implemented  
**Next Review**: 2025-02-10