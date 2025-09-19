# JIRA Attachments Integration PRD

## Overview

This Product Requirements Document (PRD) outlines the implementation of JIRA attachment functionality to support file attachments when creating tickets through the AI Ticket Creator API.

## Background

Currently, the system supports file uploads and storage but does not attach these files to external JIRA issues when tickets are created. This functionality is critical for maintaining context and supporting materials in external ticketing systems.

## Requirements

### Functional Requirements

1. **Attachment Upload to JIRA**
   - When a ticket is created with `attachments` field containing file IDs
   - The system should upload those files as attachments to the corresponding JIRA issue
   - Support all file types currently supported by the file upload system

2. **File Content Retrieval**
   - Retrieve file content from the internal file storage system
   - Support files stored via `/api/v1/files/upload` endpoint
   - Maintain file metadata (filename, mime-type, size)

3. **Error Handling**
   - Handle JIRA API attachment failures gracefully
   - Log attachment failures without failing the entire ticket creation process
   - Provide feedback on attachment success/failure in the API response

4. **Security & Access Control**
   - Verify user access to files before uploading to JIRA
   - Ensure files belong to the same organization as the ticket creator
   - Respect file access permissions and organization boundaries

### Non-Functional Requirements

1. **Performance**
   - Process attachments asynchronously to avoid blocking ticket creation
   - Support multiple file uploads in parallel
   - Set reasonable timeout limits for JIRA attachment uploads

2. **Reliability**
   - Implement retry logic for transient failures
   - Maintain audit trail of attachment operations
   - Ensure ticket creation succeeds even if attachments fail

## Technical Implementation

### JIRA API Integration Details

#### JIRA REST API Endpoints
1. **Issue Creation**: `POST /rest/api/3/issue`
2. **Attachment Upload**: `POST /rest/api/3/issue/{issueIdOrKey}/attachments`

#### JIRA API Authentication
- **Method**: Basic Authentication (email + API token)
- **Headers**: 
  - `Authorization: Basic <base64(email:api_token)>`
  - `Accept: application/json`
  - `Content-Type: multipart/form-data` (for attachments)

#### Data Mapping: Internal → JIRA

| Internal Field | JIRA Field | JIRA Format | Notes |
|---|---|---|---|
| `title` | `summary` | String | Direct mapping |
| `description` | `description` | ADF (Atlassian Document Format) | Convert plain text to ADF |
| `category` | `issuetype.name` | String | Map via category_to_issue_type |
| `priority` | `priority.name` | String | Optional, may not be available |
| `custom_fields` | Custom field IDs | Varies | Map to JIRA custom fields |
| `attachments[].file_id` | File upload | multipart/form-data | Retrieve and upload file content |

#### Category to Issue Type Mapping
```json
{
  "technical": "Bug",
  "billing": "Task", 
  "feature_request": "Story",
  "bug": "Bug",
  "general": "Task",
  "integration": "Task",
  "performance": "Bug",
  "security": "Bug",
  "user_access": "Task"
}
```

#### JIRA Attachment API Request Format
```http
POST /rest/api/3/issue/TINT-3/attachments HTTP/1.1
Host: shipwell.atlassian.net
Authorization: Basic <base64_credentials>
Accept: application/json
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW

------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="file"; filename="screenshot.png"
Content-Type: image/png

<binary file content>
------WebKitFormBoundary7MA4YWxkTrZu0gW--
```

#### JIRA Attachment API Response Format
```json
[
  {
    "id": "10001",
    "filename": "screenshot.png",
    "size": 125874,
    "content": "https://shipwell.atlassian.net/secure/attachment/10001/screenshot.png",
    "thumbnail": "https://shipwell.atlassian.net/secure/thumbnail/10001/_thumb_10001.png",
    "author": {
      "accountId": "557058:f58131cb-b67d-43c7-b30d-6b58d40bd077",
      "displayName": "Greg Price"
    },
    "created": "2025-09-18T10:30:00.000+0000"
  }
]
```

### API Changes

#### Enhanced Ticket Creation Response
The existing ticket creation response will be enhanced with attachment information:

```json
{
  "id": "9c9d1df3-4d3f-4d55-9278-063d6178c193",
  "title": "Application Login Issue - Unable to Access Dashboard",
  "external_ticket_id": "TINT-3",
  "external_ticket_url": "https://shipwell.atlassian.net/browse/TINT-3",
  "attachments": [
    {
      "file_id": "a5cf8037-77a6-49fc-8314-1ada9cb75ba7",
      "filename": "screenshot.png",
      "jira_attachment_id": "10001",
      "upload_status": "success",
      "error_message": null
    }
  ],
  "integration_result": {
    "success": true,
    "integration_id": "820703db-1835-47e2-b09c-6933b927bb8e",
    "external_ticket_id": "TINT-3",
    "external_ticket_url": "https://shipwell.atlassian.net/browse/TINT-3",
    "response": {
      "key": "TINT-3",
      "id": "76383",
      "attachments": [...],
      "attachment_summary": {
        "total_files": 1,
        "successful_uploads": 1,
        "failed_uploads": 0
      }
    }
  }
}
```

### Code Organization & Integration Structure

#### Integration Folder Reorganization
As part of this implementation, all integration services must be reorganized into a dedicated `app/integrations/` folder structure:

```
app/
├── integrations/
│   ├── __init__.py
│   ├── base/
│   │   ├── __init__.py
│   │   ├── integration_interface.py      # Base interface
│   │   └── integration_result.py         # Result classes
│   ├── jira/
│   │   ├── __init__.py
│   │   ├── jira_integration.py          # Main JIRA service (moved from services/)
│   │   ├── jira_attachment_service.py   # JIRA attachment handling
│   │   ├── jira_field_mapper.py         # Field mapping utilities
│   │   └── tests/
│   │       ├── test_jira_integration.py
│   │       └── test_jira_attachments.py
│   ├── salesforce/
│   │   ├── __init__.py
│   │   ├── salesforce_integration.py    # Future Salesforce integration
│   │   └── tests/
│   └── shared/
│       ├── __init__.py
│       ├── attachment_service.py        # Shared attachment utilities
│       └── field_mapping.py             # Common field mapping
```

#### Migration Requirements
1. **Move existing files**:
   - `app/services/jira_integration.py` → `app/integrations/jira/jira_integration.py`
   - `app/services/integration_interface.py` → `app/integrations/base/integration_interface.py`
   - Update all import statements across the codebase

2. **Create new structure**:
   - New `JiraAttachmentService` in `app/integrations/jira/jira_attachment_service.py`
   - Shared utilities in `app/integrations/shared/`

3. **Update imports**:
   ```python
   # Old imports
   from app.services.jira_integration import JiraIntegration
   from app.services.integration_interface import IntegrationInterface
   
   # New imports  
   from app.integrations.jira import JiraIntegration
   from app.integrations.base import IntegrationInterface
   ```

### Integration Points

#### File Service Integration
- Extend `FileService` to support file content retrieval for external uploads
- Add method `get_file_content_for_external_upload(file_id, user_id, organization_id)`

#### JIRA Integration Enhancement  
- Extend `JiraIntegration.add_attachment()` method (exists in current implementation)
- Add `JiraAttachmentService` for dedicated attachment handling
- Implement proper error handling and retry logic
- Organize in new `app/integrations/jira/` structure

#### Ticket Service Changes
- Update imports to use new integration folder structure
- Modify ticket creation workflow to handle attachments
- Add attachment processing to external ticket creation flow
- Update response schema to include attachment results

### Database Schema

No database changes required - leveraging existing:
- `files` table for file storage and metadata
- `tickets.attachments` JSON field for file ID references
- `integrations` table for JIRA configuration

### Service Architecture

#### New Integration Structure
```python
# app/integrations/base/integration_interface.py
class IntegrationInterface(ABC):
    """Base interface for all external integrations"""
    
# app/integrations/jira/jira_integration.py  
class JiraIntegration(IntegrationInterface):
    """JIRA-specific integration implementation"""
    
# app/integrations/jira/jira_attachment_service.py
class JiraAttachmentService:
    """Dedicated service for JIRA attachment operations"""
    
    async def upload_ticket_attachments(
        self,
        db: AsyncSession,
        jira: JiraIntegration,
        issue_key: str,
        file_ids: List[UUID],
        user_id: UUID,
        organization_id: UUID
    ) -> AttachmentSummary:
        """Upload multiple files as JIRA attachments"""
        
    async def upload_single_attachment(
        self,
        db: AsyncSession,
        jira: JiraIntegration,
        issue_key: str,
        file_id: UUID,
        user_id: UUID,
        organization_id: UUID
    ) -> AttachmentResult:
        """Upload single file with full error handling"""

# app/integrations/shared/attachment_service.py
class BaseAttachmentService:
    """Shared utilities for attachment handling across integrations"""
    
    def validate_file_access(self, file_id: UUID, user_id: UUID, org_id: UUID) -> bool:
        """Common file access validation logic"""
        
    def get_attachment_content(self, file_id: UUID) -> bytes:
        """Common file content retrieval"""
```

## Implementation Plan

### Phase 0: Code Reorganization (Required First)
1. **Create integration folder structure**:
   ```bash
   mkdir -p app/integrations/{base,jira,salesforce,shared}
   mkdir -p app/integrations/jira/tests
   touch app/integrations/{__init__,base/__init__,jira/__init__,salesforce/__init__,shared/__init__}.py
   ```

2. **Move existing integration files**:
   - Move `app/services/jira_integration.py` → `app/integrations/jira/jira_integration.py`
   - Move `app/services/integration_interface.py` → `app/integrations/base/integration_interface.py`
   - Create `app/integrations/base/integration_result.py` for result classes

3. **Update all import statements**:
   - Search and replace across codebase: `from app.services.jira_integration` → `from app.integrations.jira`
   - Update `app/services/ticket_service.py` imports
   - Update test imports
   - Update any other service imports

4. **Verify reorganization**:
   - Run existing tests to ensure no import errors
   - Verify Docker services start without errors
   - Ensure all integration functionality still works

### Phase 1: Core Attachment Functionality  
1. Create `JiraAttachmentService` in `app/integrations/jira/jira_attachment_service.py`
2. Create shared utilities in `app/integrations/shared/attachment_service.py`
3. Extend JIRA integration to support file attachments
4. Update ticket creation workflow to process attachments
5. Add comprehensive error handling and logging

### Phase 2: Enhanced Features & Testing
1. Implement retry logic for failed uploads  
2. Add parallel attachment processing
3. Create comprehensive test suite in `app/integrations/jira/tests/`
4. Add monitoring and metrics

### Phase 3: Validation & Deployment
1. Integration testing with real JIRA instances
2. Performance testing with large files
3. Security review and validation
4. Production deployment and monitoring

### Code Reorganization Validation

#### Pre-Implementation Checklist
- [ ] All integration files moved to `app/integrations/` structure
- [ ] Import statements updated throughout codebase
- [ ] Existing tests pass with new import structure
- [ ] Docker services start without errors
- [ ] No broken imports in any Python files

#### Import Update Examples
```python
# Files requiring import updates:
# app/services/ticket_service.py
from app.integrations.jira import JiraIntegration
from app.integrations.base import IntegrationInterface

# tests/integration/integrations/test_jira_integration_framework.py  
from app.integrations.jira import JiraIntegration

# Any other files importing integration services
```

## Edge Cases & Error Handling Strategy

### Critical Edge Cases

#### 1. File Access Issues
- **File not found**: Return error in attachment result, continue with ticket creation
- **File deleted**: Check `file.status != 'deleted'` before upload attempt
- **Organization boundary violation**: Verify `file.organization_id == user.organization_id`
- **Permission denied**: User lacks access to file within organization
- **File content unavailable**: File record exists but content missing from storage

#### 2. JIRA API Failures
- **Authentication failure**: Invalid API token or expired credentials
- **Network timeouts**: JIRA instance unreachable or slow response
- **Rate limiting**: JIRA API rate limits exceeded
- **File size limits**: JIRA attachment size restrictions (default 10MB)
- **Unsupported file types**: JIRA blocks certain file extensions
- **Project permissions**: User lacks permission to add attachments to project
- **Issue state**: Issue is read-only or in a workflow state that prevents attachments

#### 3. Process Interruption Scenarios
- **Connection loss**: Network interruption during file upload
- **Service restart**: Application restart during attachment processing  
- **Database transaction failure**: DB rollback during ticket creation
- **Partial success**: Some attachments succeed, others fail
- **JIRA issue creation succeeds but attachment fails**: Issue exists but incomplete

#### 4. Data Integrity Issues  
- **Corrupted file content**: File content is corrupted in storage
- **Invalid file metadata**: Missing filename, mime-type, or size
- **Concurrent modifications**: File modified during upload process
- **Memory limitations**: Large files causing OOM issues

### Error Handling Solutions

#### 1. Graceful Degradation
```python
# Pseudo-code for error handling strategy
async def process_attachments(jira, issue_key, file_ids):
    results = []
    for file_id in file_ids:
        try:
            result = await upload_single_attachment(file_id)
            results.append(result)
        except FileNotFoundError:
            results.append(AttachmentResult(
                file_id=file_id,
                success=False,
                error_message="File not found or deleted"
            ))
        except PermissionError:
            results.append(AttachmentResult(
                file_id=file_id, 
                success=False,
                error_message="Access denied"
            ))
        except JiraAPIError as e:
            if e.status_code == 413:  # File too large
                results.append(AttachmentResult(
                    file_id=file_id,
                    success=False, 
                    error_message="File exceeds JIRA size limit"
                ))
            else:
                results.append(AttachmentResult(
                    file_id=file_id,
                    success=False,
                    error_message=f"JIRA API error: {e.message}"
                ))
    
    # Always return results, never fail the entire ticket creation
    return AttachmentSummary(results)
```

#### 2. Retry Logic for Transient Failures
- **Network timeouts**: Retry up to 3 times with exponential backoff
- **Rate limiting**: Implement backoff and retry after rate limit reset
- **Connection errors**: Retry with fresh connection

#### 3. Audit Trail and Monitoring
- **Correlation IDs**: Track each attachment operation with unique ID
- **Structured logging**: Log all attachment operations with context
- **Metrics collection**: Track success rates, failure reasons, file sizes
- **Alerting**: Alert on high failure rates or specific error patterns

#### 4. Partial Success Handling
```json
// Example response with mixed results
{
  "external_ticket_id": "TINT-3",
  "attachment_summary": {
    "total_files": 3,
    "successful_uploads": 2,
    "failed_uploads": 1
  },
  "attachments": [
    {
      "file_id": "file1",
      "upload_status": "success",
      "jira_attachment_id": "10001"
    },
    {
      "file_id": "file2", 
      "upload_status": "success",
      "jira_attachment_id": "10002"
    },
    {
      "file_id": "file3",
      "upload_status": "failed",
      "error_message": "File exceeds JIRA size limit (10MB)"
    }
  ]
}
```

### Response Strategy
- **Never fail ticket creation** due to attachment errors
- **Continue processing** remaining attachments even if one fails  
- **Provide detailed feedback** on each attachment operation
- **Log comprehensive error details** for debugging and monitoring
- **Support manual retry** through separate attachment API endpoint

## Comprehensive Testing Strategy

### Pre-Implementation Testing Requirements
1. **Code Reorganization Validation**: 
   - All integration files successfully moved to `app/integrations/` structure
   - All import statements updated and functional
   - No broken imports across codebase
2. **Docker Environment**: Ensure clean docker-compose environment with no errors
3. **Database Migration**: Verify all Alembic migrations apply successfully  
4. **Service Health**: Confirm all services (app, postgres, redis, celery) start properly
5. **Baseline Tests**: Existing test suite must pass 100% with new folder structure

### Unit Tests (`app/integrations/jira/tests/test_jira_attachment_service.py`)

#### Core Functionality Tests  
```python
class TestJiraAttachmentService:
    async def test_upload_single_attachment_success(self):
        """Test successful single file upload to JIRA"""
        
    async def test_upload_multiple_attachments_success(self):
        """Test successful multiple file uploads"""
        
    async def test_file_not_found_handling(self):
        """Test graceful handling when file doesn't exist"""
        
    async def test_organization_boundary_validation(self):
        """Test file access across organization boundaries"""
        
    async def test_deleted_file_handling(self):
        """Test handling of files with deleted status"""
        
    async def test_jira_api_authentication_failure(self):
        """Test JIRA API auth failure handling"""
        
    async def test_jira_file_size_limit_exceeded(self):
        """Test handling of files exceeding JIRA limits"""
        
    async def test_partial_success_scenario(self):
        """Test mixed success/failure for multiple files"""
        
    async def test_network_timeout_handling(self):
        """Test network timeout with retry logic"""
        
    async def test_corrupted_file_content(self):
        """Test handling of corrupted file data"""
```

#### Mock JIRA API Responses
```python
# Mock successful JIRA attachment response
JIRA_ATTACHMENT_SUCCESS_RESPONSE = [
    {
        "id": "10001",
        "filename": "test_file.pdf",
        "size": 125874,
        "content": "https://test.atlassian.net/secure/attachment/10001/test_file.pdf",
        "author": {"displayName": "Test User"},
        "created": "2025-09-18T10:30:00.000+0000"
    }
]

# Mock JIRA error responses
JIRA_FILE_TOO_LARGE_RESPONSE = {
    "errorMessages": ["The attachment is too large"],
    "errors": {}
}
```

### Integration Tests (`app/integrations/jira/tests/test_jira_attachment_integration.py`)

#### End-to-End Test Cases
```python
class TestJiraAttachmentIntegration:
    async def test_ticket_creation_with_single_attachment(self):
        """
        Test the exact scenario from the provided POST request:
        - Create ticket with attachment file_id: a5cf8037-77a6-49fc-8314-1ada9cb75ba7
        - Verify JIRA issue creation (TINT-3)  
        - Verify attachment upload to JIRA
        - Validate API response format
        """
        
    async def test_ticket_creation_with_multiple_attachments(self):
        """Test ticket with multiple file attachments"""
        
    async def test_attachment_failure_does_not_break_ticket_creation(self):
        """Ensure ticket still gets created even if attachments fail"""
        
    async def test_mixed_success_failure_attachments(self):
        """Test some attachments succeed while others fail"""
        
    async def test_large_file_attachment_handling(self):
        """Test handling of files approaching JIRA size limits"""
        
    async def test_concurrent_ticket_creation_with_attachments(self):
        """Test multiple simultaneous ticket creation with attachments"""
```

### Specific Test Case: Provided POST Request

#### Test Implementation
```python
@pytest.mark.asyncio
async def test_provided_post_request_scenario(client, test_db, test_user, jira_integration):
    """
    Test the exact POST request scenario provided in requirements
    """
    # 1. Setup: Create test file with specific ID
    test_file_id = "a5cf8037-77a6-49fc-8314-1ada9cb75ba7"
    file_content = b"Mock file content for testing"
    
    file_service = FileService()
    test_file = await file_service.create_file_record(
        db=test_db,
        filename="test_attachment.pdf",
        mime_type="application/pdf", 
        file_size=len(file_content),
        file_content=file_content,
        uploaded_by_id=test_user.id,
        organization_id=test_user.organization_id
    )
    
    # Override the file ID to match the test case
    test_file.id = UUID(test_file_id)
    await test_db.commit()
    
    # 2. Execute: POST request with exact payload
    payload = {
        "title": "Application Login Issue - Unable to Access Dashboard",
        "description": "Users are reporting inability to log into the application. After entering correct credentials, the page redirects to a blank screen instead of the dashboard. This appears to affect multiple users across different browsers. Steps to reproduce: 1. Navigate to login page 2. Enter valid credentials 3. Click login button 4. Observe blank page instead of dashboard.",
        "category": "technical",
        "priority": "high",
        "urgency": "high",
        "department": "Engineering",
        "assigned_to_id": None,
        "integration_id": str(jira_integration.id),
        "create_externally": True,
        "custom_fields": {
            "environment": "production",
            "browser_versions": "Chrome 118+, Firefox 119+",
            "affected_users": "~50 users"
        },
        "attachments": [{"file_id": test_file_id}]
    }
    
    headers = {"Authorization": f"Bearer {test_user.token}"}
    
    response = await client.post("/api/v1/tickets", json=payload, headers=headers)
    
    # 3. Assertions
    assert response.status_code == 201
    response_data = response.json()
    
    # Verify ticket creation
    assert response_data["title"] == payload["title"]
    assert response_data["external_ticket_id"] is not None
    assert response_data["external_ticket_url"] is not None
    
    # Verify attachment processing
    assert "attachments" in response_data
    assert len(response_data["attachments"]) == 1
    
    attachment = response_data["attachments"][0]
    assert attachment["file_id"] == test_file_id
    assert attachment["upload_status"] == "success"
    assert attachment["jira_attachment_id"] is not None
    
    # Verify integration result includes attachment summary
    integration_result = response_data["integration_result"]
    assert integration_result["success"] is True
    assert "attachment_summary" in integration_result["response"]
    
    summary = integration_result["response"]["attachment_summary"]
    assert summary["total_files"] == 1
    assert summary["successful_uploads"] == 1
    assert summary["failed_uploads"] == 0
    
    # 4. Verify in JIRA (if using real JIRA instance)
    if not MOCK_JIRA_API:
        jira_issue_key = response_data["external_ticket_id"]
        jira_attachments = await jira_integration.get_issue_attachments(jira_issue_key)
        assert len(jira_attachments) == 1
        assert jira_attachments[0]["filename"] == "test_attachment.pdf"
```

### Performance Tests (`app/integrations/jira/tests/test_jira_attachment_performance.py`)

#### Load and Stress Testing
```python
class TestJiraAttachmentPerformance:
    async def test_large_file_upload_memory_usage(self):
        """Test memory usage with 50MB+ files"""
        
    async def test_concurrent_attachment_uploads(self):
        """Test 10+ concurrent ticket creations with attachments"""
        
    async def test_attachment_processing_timeout(self):
        """Ensure attachment processing completes within 30 seconds"""
        
    async def test_bulk_file_processing(self):
        """Test ticket with 10+ attachments"""
```

### Docker Environment Tests

#### Pre-Implementation Validation
```bash
# 1. Clean environment startup
docker-compose down -v
docker-compose up -d

# 2. Health checks
curl http://localhost:8000/health  # Should return 200
curl http://localhost:8001/health  # MCP server health

# 3. Database connectivity  
docker-compose exec app poetry run alembic upgrade head

# 4. Run existing test suite
docker-compose exec app poetry run pytest tests/ -v --tb=short

# 5. Verify no Docker errors
docker-compose logs --tail=50  # Should show no ERROR level logs
```

### Test Data Requirements

#### File Test Fixtures
- **Small file**: 1KB text file
- **Medium file**: 1MB PDF document  
- **Large file**: 8MB image (near JIRA limit)
- **Invalid file**: Corrupted content
- **Deleted file**: File with status='deleted'
- **Cross-org file**: File from different organization

#### JIRA Integration Test Setup
- **Test JIRA project**: Dedicated test project key (e.g., "TEST")
- **API credentials**: Valid test environment credentials
- **Permission scenarios**: Various user permission levels

### Continuous Testing Requirements

#### Pre-Merge Validation
1. **Unit tests**: 100% pass rate required
2. **Integration tests**: All scenarios must pass
3. **Docker startup**: Clean startup with no errors
4. **Memory leaks**: No memory growth during attachment processing
5. **Log validation**: No ERROR level logs during normal operation

#### Post-Implementation Validation  
1. **End-to-end test**: Execute provided POST request scenario
2. **JIRA verification**: Manual verification of attachments in JIRA UI
3. **Performance baseline**: Establish performance benchmarks
4. **Error rate monitoring**: Monitor for any increase in error rates

## Security Considerations

### File Access Control
- Verify user owns or has access to files
- Validate organization boundaries
- Check file status (not deleted, processed)

### JIRA Security
- Use organization-specific JIRA credentials
- Respect JIRA project permissions
- Handle authentication failures gracefully

### Data Privacy
- Log file metadata only, not content
- Respect file retention policies  
- Support file deletion after external upload

## Monitoring & Metrics

### Key Metrics
- Attachment upload success rate
- Average attachment processing time
- File size distribution for uploads
- JIRA API error rates and types

### Alerting
- High attachment failure rates
- JIRA API authentication failures
- File access permission violations
- Performance degradation thresholds

## Success Criteria

1. **Functional Success**
   - Files attached to tickets appear in corresponding JIRA issues
   - All supported file types upload successfully
   - Error handling prevents ticket creation failures

2. **Performance Success**
   - Attachment processing completes within 30 seconds for typical files
   - System supports concurrent attachment uploads
   - Memory usage remains stable during large file processing

3. **Reliability Success**  
   - 95%+ attachment upload success rate
   - Graceful handling of all identified failure scenarios
   - Complete audit trail for troubleshooting

## Reference Test Case & API Usage

### Provided Test Case
This exact POST request must be supported and tested:

```http
POST /api/v1/tickets HTTP/1.1
Authorization: Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8
Content-Type: application/json
User-Agent: PostmanRuntime/7.46.1
Accept: */*
Cache-Control: no-cache
Host: localhost:8000

{
  "title": "Application Login Issue - Unable to Access Dashboard",
  "description": "Users are reporting inability to log into the application. After entering correct credentials, the page redirects to a blank screen instead of the dashboard. This appears to affect multiple users across different browsers. Steps to reproduce: 1. Navigate to login page 2. Enter valid credentials 3. Click login button 4. Observe blank page instead of dashboard.",
  "category": "technical",
  "priority": "high",
  "urgency": "high",
  "department": "Engineering",
  "assigned_to_id": null,
  "integration_id": "820703db-1835-47e2-b09c-6933b927bb8e",
  "create_externally": true,
  "custom_fields": {
    "environment": "production",
    "browser_versions": "Chrome 118+, Firefox 119+",
    "affected_users": "~50 users"
  },
  "attachments": [{"file_id": "a5cf8037-77a6-49fc-8314-1ada9cb75ba7"}]
}
```

### Expected Enhanced Response
The current response format will be enhanced with attachment details:

```json
{
  "created_at": "2025-09-17T23:35:17.501477Z",
  "updated_at": "2025-09-17T23:35:18.722335Z",
  "id": "9c9d1df3-4d3f-4d55-9278-063d6178c193",
  "title": "Application Login Issue - Unable to Access Dashboard",
  "category": "technical",
  "priority": "high",
  "urgency": "high",
  "status": "new",
  "department": "Engineering",
  "external_ticket_id": "TINT-3",
  "external_ticket_url": "https://shipwell.atlassian.net/browse/TINT-3",
  "attachments": [
    {
      "file_id": "a5cf8037-77a6-49fc-8314-1ada9cb75ba7",
      "filename": "uploaded_document.pdf",
      "upload_status": "success", 
      "jira_attachment_id": "10001",
      "error_message": null
    }
  ],
  "integration_result": {
    "success": true,
    "integration_id": "820703db-1835-47e2-b09c-6933b927bb8e",
    "external_ticket_id": "TINT-3",
    "external_ticket_url": "https://shipwell.atlassian.net/browse/TINT-3",
    "error_message": null,
    "response": {
      "key": "TINT-3",
      "id": "76383",
      "url": "https://shipwell.atlassian.net/browse/TINT-3",
      "self": "https://shipwell.atlassian.net/rest/api/3/issue/76383",
      "project_key": "TINT",
      "issue_type": "Bug",
      "summary": "Application Login Issue - Unable to Access Dashboard",
      "attachments": [
        {
          "file_id": "a5cf8037-77a6-49fc-8314-1ada9cb75ba7",
          "filename": "uploaded_document.pdf",
          "upload_status": "success",
          "jira_attachment_id": "10001"
        }
      ],
      "attachment_summary": {
        "total_files": 1,
        "successful_uploads": 1,
        "failed_uploads": 0
      }
    }
  }
}
```

### Implementation Validation Checklist

#### ✅ Must Verify:
1. **File ID Resolution**: `a5cf8037-77a6-49fc-8314-1ada9cb75ba7` resolves to valid file
2. **JIRA Issue Creation**: Issue `TINT-3` gets created in JIRA
3. **Attachment Upload**: File content uploaded as attachment to `TINT-3`
4. **Response Format**: All expected fields present in API response
5. **No Failures**: Ticket creation succeeds even if attachment fails
6. **Docker Stability**: No Docker service errors during operation
7. **Test Suite**: All existing tests continue to pass