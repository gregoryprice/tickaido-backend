# API Documentation

This directory contains documentation and configuration files for the AI Ticket Creator Backend API.

## Files

- **`../openapi.yaml`** - Complete OpenAPI 3.0 specification
- **`../redocly.yaml`** - Redocly configuration for documentation generation and linting

## Documentation Access

### Live Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.yaml

### Local Development

1. **Validate OpenAPI Spec**:
   ```bash
   npx @redocly/cli lint ../openapi.yaml
   ```

2. **Generate Static Documentation**:
   ```bash
   npx @redocly/cli build-docs ../openapi.yaml --output ./api-docs.html
   ```

3. **Preview Documentation**:
   ```bash
   npx @redocly/cli preview-docs ../openapi.yaml
   ```

## API Overview

The AI Ticket Creator Backend API provides:

### Core Features
- **AI-Powered Ticket Creation** - Smart ticket creation using natural language processing
- **File Processing** - Upload and analyze multiple file types with AI transcription/OCR
- **Real-time Notifications** - WebSocket-based real-time updates
- **Third-party Integrations** - Salesforce, Jira, ServiceNow, Zendesk, GitHub, Slack, Teams, Zoom
- **Chrome Extension Support** - Optimized for browser extension workflows

### Authentication
- JWT-based authentication with role-based access control
- Bearer token required for most endpoints
- Support for external authentication providers

### Rate Limiting
- 1000 requests per hour per API key
- Burst limit: 100 requests per minute
- Special limits for file upload endpoints

### Response Format
All API responses follow consistent patterns:
- Success responses include data and metadata
- Error responses include detailed error information
- Paginated responses include pagination metadata

### File Processing
Supported file types:
- **Images**: PNG, JPG, JPEG, GIF (OCR processing)
- **Audio**: MP3, WAV, M4A (AI transcription)
- **Video**: MP4, AVI, MOV (AI transcription)
- **Documents**: PDF, DOCX, TXT (content extraction)

### WebSocket Events
Real-time events for:
- Ticket status updates
- File processing progress
- Assignment notifications
- Integration sync status

## Integration Examples

### Creating a Ticket with AI
```bash
curl -X POST "http://localhost:8000/api/v1/tickets/ai-create" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "I cannot log into my account after the recent update",
    "uploaded_files": ["/path/to/screenshot.png"],
    "user_preferences": {
      "preferred_priority": "high",
      "department": "technical_support"
    }
  }'
```

### Searching Tickets
```bash
curl -X GET "http://localhost:8000/api/v1/tickets?q=login%20issue&status=open&priority=high&page=1&size=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

## Error Handling

The API uses standard HTTP status codes:
- **200** - Success
- **201** - Created
- **400** - Bad Request (validation error)
- **401** - Unauthorized
- **403** - Forbidden
- **404** - Not Found
- **429** - Rate Limited
- **500** - Internal Server Error

Error responses include:
```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "timestamp": "2025-01-01T12:00:00Z",
  "request_id": "unique-request-identifier"
}
```

## Development Workflow

1. **Make API Changes** - Update endpoints in `/app/api/`
2. **Update OpenAPI Spec** - Modify `openapi.yaml`
3. **Validate Specification** - Run `npx @redocly/cli lint`
4. **Test Changes** - Use `/docs` or `/redoc` to test
5. **Generate Documentation** - Build static docs for deployment

## Production Deployment

### Environment Variables
- `OPENAPI_URL` - URL for OpenAPI spec (default: `/openapi.json`)
- `DOCS_URL` - URL for Swagger UI (default: `/docs`)  
- `REDOC_URL` - URL for ReDoc (default: `/redoc`)

### Security Considerations
- Disable `/docs` and `/redoc` in production if needed
- Use HTTPS for all API communication
- Implement proper CORS policies
- Rate limit based on production requirements

## Support

For API support and questions:
- **Documentation**: http://localhost:8000/
- **Issues**: GitHub repository issues
- **Email**: support@aiticketcreator.com