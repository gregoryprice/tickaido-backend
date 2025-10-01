# PRP: Jira Official Library Migration

**Feature**: Migration from custom Jira integration to official Python library  
**Date**: 2025-09-30  
**Status**: Ready for Implementation  
**Estimated Effort**: 8-12 days  

## Executive Summary

Migrate from custom Jira REST API implementation to the official [jira Python library](https://pypi.org/project/jira/) (v3.10.5+) to standardize integration, add rich text support, improve comment handling, and maintain seamless attachment functionality while preserving existing integration setup API.

## Context and Research Findings

### Current Implementation Analysis

**Files to Replace/Migrate:**
- `app/integrations/jira/jira_integration.py` (1,125 lines) - Custom httpx-based JIRA REST implementation
- `app/integrations/jira/jira_attachment_service.py` (251 lines) - Custom attachment handling  
- `app/integrations/jira/tests/test_jira_attachment_service.py` - Custom attachment tests

**Current Architecture Patterns (MUST PRESERVE):**
- Inherits from `IntegrationInterface` abstract base class (`app/integrations/base/integration_interface.py:11`)
- Implements required methods: `test_connection()`, `test_authentication()`, `test_permissions()`, `create_ticket()`, `get_configuration_schema()`, `close()`
- Uses standardized result classes: `IntegrationTestResult`, `IntegrationTicketResult` from `app/integrations/base/integration_result.py`
- Async context manager support with `__aenter__` and `__aexit__`
- Basic auth with email/API token pattern: `httpx.BasicAuth(email, api_token)` (`app/integrations/jira/jira_integration.py:37`)

**Current Features:**
- ✅ Basic auth with email/API token
- ✅ Issue creation with ADF (Atlassian Document Format) descriptions
- ✅ File attachment upload with retry logic and error handling
- ✅ Connection testing via `/rest/api/3/myself` endpoint
- ✅ Integration with local ticket model via `create_ticket_from_internal()`
- ❌ Limited rich text support (only basic ADF paragraph format)
- ❌ No comment management (only creation)
- ❌ No advanced ADF features (tables, code blocks, formatting)

### External Library Research

**Jira Python Library Details:**
- **Package**: `jira>=3.10.5,<4.0.0` from PyPI
- **Compatibility**: Requires Python >=3.10 (✅ Current project: >=3.12)
- **Documentation**: https://jira.readthedocs.io/en/latest/
- **Examples**: https://jira.readthedocs.io/en/latest/examples.html

**Key API Patterns from Official Library:**
```python
# Authentication (matches current pattern)
from jira import JIRA
jira = JIRA(server='https://instance.atlassian.net', basic_auth=('email', 'api_token'))

# Issue creation
new_issue = jira.create_issue(
    project='PROJ_key', 
    summary='New issue', 
    description='Issue details', 
    issuetype={'name': 'Bug'}
)

# Attachment handling  
jira.add_attachment(issue=issue, attachment='/path/to/file.txt')
with open('/path/to/file.txt', 'rb') as f:
    jira.add_attachment(issue=issue, attachment=f)

# Comment management
jira.add_comment('ISSUE-123', 'New comment')
jira.add_comment(issue, 'Comment', visibility={'type': 'role', 'value': 'Administrators'})
```

### Test Patterns Analysis

**Existing Test Structure (MUST FOLLOW):**
- Integration tests: `tests/integration/integrations/test_jira_integration_framework.py`
- Unit tests with pytest and asyncio: `@pytest.mark.asyncio`
- Mock patterns: `AsyncMock`, `MagicMock` for external dependencies
- Test validation: Interface implementation checks, schema validation
- Naming convention: `test_*.py` files with descriptive method names

## Implementation Plan

### Phase 1: Core Library Migration (3-5 days)

#### Task 1.1: Dependency Integration
```bash
# Add official library
poetry add "jira>=3.10.5,<4.0.0"

# Validate compatibility
poetry install
python -c "from jira import JIRA; print('✅ Import successful')"
```

#### Task 1.2: Create New Integration Class
**Target**: `app/integrations/jira/jira_official_integration.py`

**CRITICAL PATTERNS TO FOLLOW:**
```python
from jira import JIRA
from ..base.integration_interface import IntegrationInterface
from ..base.integration_result import IntegrationTestResult, IntegrationTicketResult

class JiraOfficialIntegration(IntegrationInterface):
    """Official Jira library integration implementation"""
    
    def __init__(self, base_url: str, email: str, api_token: str):
        # PRESERVE: Same constructor signature as current implementation
        self.base_url = base_url.rstrip('/')
        self.email = email
        self.api_token = api_token
        self.jira = JIRA(
            server=self.base_url,
            basic_auth=(email, api_token),
            options={'timeout': 30}
        )
    
    async def test_connection(self) -> Dict[str, Any]:
        # PRESERVE: Must return IntegrationTestResult format
        # Use: user = self.jira.current_user()
        return IntegrationTestResult.success(
            message="Connection successful",
            details={"user": user["displayName"], "account_id": user["accountId"]}
        )
    
    async def create_ticket(self, ticket_data: Dict[str, Any], is_test: bool = False) -> Dict[str, Any]:
        # PRESERVE: Must return IntegrationTicketResult format
        # Use: issue = self.jira.create_issue(fields=issue_dict)
        return IntegrationTicketResult.success(
            external_ticket_id=issue.key,
            external_ticket_url=f"{self.base_url}/browse/{issue.key}",
            details=issue.raw
        )
```

#### Task 1.3: Authentication Migration
- Replace `httpx.BasicAuth` with `basic_auth=(email, api_token)` parameter
- Preserve existing error handling patterns from `app/integrations/jira/jira_integration.py:69-108`
- Maintain response time logging using `app/utils/http_debug_logger.py`

#### Task 1.4: Issue Creation Enhancement
- Implement advanced ADF (Atlassian Document Format) support
- Support rich text elements: tables, code blocks, lists, formatted text
- Preserve existing category-to-issue-type mapping logic
- Maintain compatibility with `create_ticket_from_internal()` workflow

### Phase 2: Rich Text & Comments System (2-3 days)

#### Task 2.1: Database Schema Extension
**Target**: New Alembic migration file

```sql
-- New table for comment tracking (ADDITIVE - no data loss risk)
CREATE TABLE ticket_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    jira_comment_id TEXT,
    author_email TEXT NOT NULL,
    author_display_name TEXT,
    body JSONB NOT NULL,  -- ADF format
    is_internal BOOLEAN DEFAULT FALSE,
    INDEX idx_ticket_comments_ticket_id (ticket_id),
    INDEX idx_ticket_comments_jira_id (jira_comment_id)
);

-- Update tickets table for rich text support (ADDITIVE)
ALTER TABLE tickets 
ADD COLUMN description_adf JSONB,  -- Rich text ADF format
ADD COLUMN description_html TEXT;   -- Rendered HTML for display
```

#### Task 2.2: Comment API Implementation
**Target**: `app/api/v1/tickets.py` (extend existing endpoints)

```python
# New endpoints to add
@router.post("/{ticket_id}/comments")
async def create_comment(ticket_id: UUID, comment: CommentCreate) -> CommentResponse

@router.get("/{ticket_id}/comments") 
async def list_comments(ticket_id: UUID) -> List[CommentResponse]

@router.put("/{ticket_id}/comments/{comment_id}")
async def update_comment(ticket_id: UUID, comment_id: UUID, comment: CommentUpdate) -> CommentResponse

@router.delete("/{ticket_id}/comments/{comment_id}")
async def delete_comment(ticket_id: UUID, comment_id: UUID) -> Dict[str, str]
```

#### Task 2.3: Schema Updates
**Target**: `app/schemas/comment.py` (new file)

```python
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any

class CommentCreate(BaseModel):
    body: str | Dict[str, Any]  # Plain text or ADF
    is_internal: bool = False

class CommentResponse(BaseModel):
    id: UUID
    ticket_id: UUID  
    author_email: str
    author_display_name: Optional[str]
    body: Dict[str, Any]  # ADF format
    body_html: str  # Rendered HTML
    created_at: datetime
    updated_at: datetime
    jira_comment_id: Optional[str]
    is_internal: bool
```

### Phase 3: Enhanced Attachments (2-3 days)

#### Task 3.1: Attachment Migration
- Replace custom attachment logic with `jira.add_attachment(issue, attachment, filename)`
- Support file objects, file paths, and in-memory uploads
- Preserve existing retry logic and error handling patterns from `app/integrations/jira/jira_attachment_service.py:90-150`

#### Task 3.2: Metadata Enhancement  
- Store Jira attachment IDs in local database
- Track attachment status (uploaded, failed, deleted)
- Add attachment download capability using `jira.attachment()`

### Phase 4: Testing & Validation (2-3 days)

#### Task 4.1: Test Migration
**Target Files to Update:**
- `tests/integration/integrations/test_jira_integration_framework.py`
- `app/integrations/jira/tests/test_jira_attachment_service.py`
- New: `tests/integration/test_jira_comments.py`
- New: `tests/unit/test_jira_rich_text.py`

#### Task 4.2: Validation Gates (EXECUTABLE)
```bash
# Syntax and Style Validation
poetry run ruff check --fix app/
poetry run mypy app/

# Unit Tests  
poetry run pytest tests/unit/ -v

# Integration Tests
poetry run pytest tests/integration/integrations/test_jira_integration_framework.py -v

# Attachment Tests
poetry run pytest app/integrations/jira/tests/test_jira_attachment_service.py -v

# New Feature Tests
poetry run pytest tests/integration/test_jira_comments.py -v
poetry run pytest tests/unit/test_jira_rich_text.py -v

# Full Test Suite
poetry run pytest --cov=app --cov-report=html --cov-fail-under=95
```

## Technical Implementation Details

### Critical Dependencies
```toml
# Add to pyproject.toml [tool.poetry.dependencies]
jira = ">=3.10.5,<4.0.0"

# No conflicts expected with existing dependencies:
# - httpx (still used by other services)
# - fastapi (unchanged)  
# - sqlalchemy (unchanged)
# - pydantic (unchanged)
```

### Integration Interface Compliance

**MUST IMPLEMENT (from IntegrationInterface):**
1. `async def test_connection(self) -> Dict[str, Any]` - Use `jira.current_user()`
2. `async def test_authentication(self) -> Dict[str, Any]` - Use `jira.current_user()`  
3. `async def test_permissions(self, test_data: Dict) -> Dict[str, Any]` - Use `jira.create_meta()`
4. `async def create_ticket(self, ticket_data: Dict, is_test: bool = False) -> Dict[str, Any]` - Use `jira.create_issue()`
5. `async def get_configuration_schema(self) -> Dict[str, Any]` - Return JSON schema
6. `async def close(self)` - Clean up resources

### Error Handling Patterns (PRESERVE FROM CURRENT)

```python
# From app/integrations/jira/jira_integration.py:101-120
try:
    # Jira operation
    pass
except JIRAError as e:
    logger.error(f"JIRA API error: {e}")
    return IntegrationTestResult.failure(
        message=f"JIRA error: {e.text}",
        details={"status_code": e.status_code, "response": e.response.text}
    )
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return IntegrationTestResult.failure(
        message="Connection failed",
        details={"error": str(e)}
    )
```

## Risk Assessment & Mitigation

### High Risk - Authentication Compatibility 
**Risk**: Existing credentials must work unchanged  
**Mitigation**: Thorough testing with current test credentials before deployment
**Test**: Use existing integration endpoint `/api/v1/integrations/{id}/test`

### Medium Risk - API Backward Compatibility
**Risk**: Integration setup API must remain unchanged  
**Mitigation**: Preserve all existing method signatures, only change internal implementation
**Test**: Existing integration tests must pass without modification

### Low Risk - Performance Impact
**Risk**: Official library may have different performance characteristics  
**Mitigation**: Performance testing during migration, optimization if needed
**Test**: Response time benchmarks (current: issue creation ~2.5s, attachments ~25s)

## Success Criteria

### Functional Requirements ✅
- [ ] All existing integration tests pass unchanged
- [ ] Rich text support: tables, code blocks, formatted text in descriptions  
- [ ] Comment system: full CRUD operations with ADF support
- [ ] Enhanced attachments: improved metadata tracking and download
- [ ] API compatibility: existing integration setup endpoints unchanged

### Performance Requirements ✅  
- [ ] Issue creation ≤ 3 seconds (current: ~2.5s)
- [ ] Attachment upload ≤ 30 seconds (current: ~25s) 
- [ ] Comment operations ≤ 1 second

### Quality Requirements ✅
- [ ] Test coverage ≥95% on new functionality
- [ ] All validation gates pass (ruff, mypy, pytest)
- [ ] Comprehensive error handling for all failure scenarios
- [ ] Complete API documentation for new features

## Implementation Tasks Checklist

### Phase 1: Core Migration
- [ ] Add jira library dependency with `poetry add "jira>=3.10.5,<4.0.0"`
- [ ] Create `JiraOfficialIntegration` class inheriting from `IntegrationInterface`
- [ ] Implement authentication using `basic_auth=(email, api_token)`
- [ ] Migrate `test_connection()` to use `jira.current_user()`
- [ ] Migrate `create_ticket()` to use `jira.create_issue()`
- [ ] Preserve all error handling patterns and return formats
- [ ] Update imports and integration factory to use new class

### Phase 2: Rich Text & Comments  
- [ ] Create Alembic migration for `ticket_comments` table
- [ ] Implement ADF builder utility for complex rich text
- [ ] Add comment CRUD operations to Jira integration
- [ ] Create comment API endpoints in `app/api/v1/tickets.py`
- [ ] Add comment schemas in `app/schemas/comment.py`
- [ ] Implement comment synchronization from Jira to local DB

### Phase 3: Enhanced Attachments
- [ ] Migrate attachment upload to `jira.add_attachment()`
- [ ] Add attachment metadata tracking in local database
- [ ] Implement attachment download using `jira.attachment()`
- [ ] Add batch attachment operations support
- [ ] Integrate with existing file processing pipeline

### Phase 4: Testing & Validation
- [ ] Update existing integration tests for new implementation
- [ ] Create comment system tests
- [ ] Create rich text functionality tests  
- [ ] Run full validation gate: `ruff check --fix && mypy . && pytest --cov-fail-under=95`
- [ ] Performance benchmarking against current implementation
- [ ] End-to-end testing with real Jira instance

## Rollback Strategy

- **Low Risk**: Keep existing custom integration as backup during transition
- **Feature Flag**: Environment variable to switch between old/new implementation  
- **Data Safety**: New database schema is additive - no data loss risk
- **Quick Rollback**: Simply revert integration factory to use old class

## External Resources

- **Official Documentation**: https://jira.readthedocs.io/en/latest/
- **API Examples**: https://jira.readthedocs.io/en/latest/examples.html  
- **PyPI Package**: https://pypi.org/project/jira/
- **GitHub Repository**: https://github.com/pycontribs/jira
- **Atlassian Document Format (ADF)**: https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/

## Quality Score: 9/10

**Confidence Level**: High for one-pass implementation success

**Strengths**:
- Comprehensive codebase analysis with specific file references
- Detailed external library research with working examples
- Clear preservation of existing patterns and interfaces
- Executable validation gates with specific commands
- Additive database changes with no data loss risk
- Thorough error handling and rollback strategy

**Minor Risk**:
- ADF implementation complexity may require iteration for advanced features
- Performance optimization may be needed based on official library characteristics

This PRP provides complete context for successful one-pass implementation while maintaining backward compatibility and system reliability.