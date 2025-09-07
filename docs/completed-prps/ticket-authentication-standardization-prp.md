# Ticket API Authentication Standardization PRP

**Problem Resolution Proposal**  
**Document Version:** 1.0  
**Date:** 2025-09-03  
**Author:** AI Assistant  
**Status:** Proposed - Critical Security Standardization  

## Problem Statement

### Critical Security Gap Identified

The Ticket API endpoints (`/api/v1/tickets/*`) currently lack authentication requirements, creating a significant security vulnerability where unauthenticated users can access, create, modify, and delete tickets. This inconsistency with other protected endpoints (e.g., integrations) presents multiple risks:

**Current Authentication Status:**
- ❌ **Ticket API**: No authentication required (open access)
- ✅ **Integration API**: Proper JWT authentication enforced
- ✅ **User API**: Proper JWT authentication enforced
- ✅ **Agent API**: Proper JWT authentication enforced

### Security Risks

1. **Data Exposure**: Unauthenticated access to sensitive ticket information
2. **Unauthorized Operations**: Anonymous users can create, modify, or delete tickets
3. **Multi-tenant Violation**: No organization isolation for ticket data
4. **Compliance Issues**: Violates data privacy and access control requirements
5. **MCP Integration Impact**: Once standardized, MCP tools will need proper authentication

### Affected Endpoints

**Currently Unprotected Ticket Endpoints:**
```
GET    /api/v1/tickets/                 # List tickets
POST   /api/v1/tickets/                 # Create ticket  
POST   /api/v1/tickets/ai-create        # AI ticket creation
GET    /api/v1/tickets/{ticket_id}      # Get ticket details
PUT    /api/v1/tickets/{ticket_id}      # Full update ticket (replace all fields)
PATCH  /api/v1/tickets/{ticket_id}      # Partial update ticket (update specific fields)
DELETE /api/v1/tickets/{ticket_id}      # Delete ticket
GET    /api/v1/tickets/stats/overview   # Ticket statistics
```

**Endpoints to be Removed (Redundant Patterns):**
```
PATCH  /api/v1/tickets/{ticket_id}/status      # ❌ REMOVE - Use PATCH /api/v1/tickets/{ticket_id} with {"status": "new"}
PATCH  /api/v1/tickets/{ticket_id}/assign     # ❌ REMOVE - Use PATCH /api/v1/tickets/{ticket_id} with {"assigned_to_id": "uuid"}
```

**Note**: No backward compatibility needed - this is initial design phase implementation.

## Proposed Solution

### Authentication Standardization & API Consolidation Strategy

Implement consistent JWT-based authentication across all ticket endpoints while consolidating redundant endpoint patterns into a unified PATCH API design.

### Core Requirements

1. **JWT Authentication**: All ticket endpoints require valid JWT tokens
2. **Organization Isolation**: Users can only access tickets within their organization  
3. **Role-Based Access**: Support for different permission levels (admin, user, readonly)
4. **API Consolidation**: Remove redundant `/status` and `/assign` endpoints in favor of unified PATCH
5. **Flexible PATCH Operations**: Support partial updates for any combination of fields
6. **Test-Driven Implementation**: Each phase must pass all tests before proceeding to next phase
7. **MCP Integration Ready**: Prepare for authenticated MCP tool integration

## Implementation Plan

### 🚨 **Critical Implementation Requirements**

**Test-Driven Development Approach:**
1. **Phase Gate Requirement**: Each implementation phase MUST pass ALL tests before proceeding
2. **Test Suite Validation**: All existing tests must continue to pass after each change
3. **New Test Coverage**: Each new feature must have comprehensive test coverage
4. **Continuous Validation**: Run full test suite after every significant change
5. **Error Resolution**: Fix ALL test failures before moving to next phase

**Implementation Workflow:**
```bash
# Required workflow for each phase
1. Implement phase changes
2. Run full test suite: poetry run pytest -v
3. Fix any test failures
4. Verify 100% test pass rate
5. Commit phase changes
6. Move to next phase ONLY after all tests pass
```

### Phase 1: Authentication Infrastructure Updates

#### 1.1 Update Ticket API Dependencies
**File:** `app/api/v1/tickets.py`

**Current Pattern (Insecure):**
```python
async def list_tickets(
    pagination: PaginationParams = Depends(),
    search_params: TicketSearchParams = Depends(),
    sort_params: TicketSortParams = Depends(),
    db: AsyncSession = Depends(get_db_session)  # No authentication!
):
```

**New Pattern (Secure):**
```python
from app.dependencies import get_current_active_user
from app.models.user import User

async def list_tickets(
    pagination: PaginationParams = Depends(),
    search_params: TicketSearchParams = Depends(),
    sort_params: TicketSortParams = Depends(),
    current_user: User = Depends(get_current_active_user),  # Add authentication
    db: AsyncSession = Depends(get_db_session)
):
```

#### 1.2 Complete Endpoint Updates

**All ticket endpoints need authentication dependency added:**

```python
# Import the authentication dependency
from app.dependencies import get_current_active_user

# List Tickets
@router.get("/", response_model=PaginatedResponse)
async def list_tickets(
    pagination: PaginationParams = Depends(),
    search_params: TicketSearchParams = Depends(),
    sort_params: TicketSortParams = Depends(),
    current_user: User = Depends(get_current_active_user),  # ADD THIS
    db: AsyncSession = Depends(get_db_session)
):

# Create Ticket
@router.post("/", response_model=TicketDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: TicketCreateRequest,
    current_user: User = Depends(get_current_active_user),  # ADD THIS
    db: AsyncSession = Depends(get_db_session)
):

# AI Create Ticket
@router.post("/ai-create", response_model=TicketAICreateResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket_with_ai(
    ai_request: TicketAICreateRequest,
    current_user: User = Depends(get_current_active_user),  # ADD THIS
    db: AsyncSession = Depends(get_db_session)
):

# Get Ticket
@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(
    ticket_id: UUID,
    include_ai_data: bool = Query(True, description="Include AI analysis data"),
    current_user: User = Depends(get_current_active_user),  # ADD THIS
    db: AsyncSession = Depends(get_db_session)
):

# Update Ticket
@router.put("/{ticket_id}", response_model=TicketDetailResponse)
async def update_ticket(
    ticket_id: UUID,
    update_data: TicketUpdateRequest,
    current_user: User = Depends(get_current_active_user),  # ADD THIS
    db: AsyncSession = Depends(get_db_session)
):

# Unified PATCH Ticket (replaces separate /status and /assign endpoints)
@router.patch("/{ticket_id}", response_model=TicketDetailResponse)
async def patch_ticket(
    ticket_id: UUID,
    patch_data: TicketPatchRequest,  # NEW: Flexible patch schema
    current_user: User = Depends(get_current_active_user),  # ADD THIS
    db: AsyncSession = Depends(get_db_session)
):

# Delete Ticket
@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: UUID,
    current_user: User = Depends(get_current_active_user),  # ADD THIS
    db: AsyncSession = Depends(get_db_session)
):

# Ticket Statistics
@router.get("/stats/overview", response_model=TicketStatsResponse)
async def get_ticket_stats(
    current_user: User = Depends(get_current_active_user),  # ADD THIS
    db: AsyncSession = Depends(get_db_session)
):
```

### Phase 1.5: API Consolidation - Unified PATCH Schema

#### 1.5.1 New Flexible Patch Request Schema
**File:** `app/schemas/ticket.py`

```python
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.models.ticket import TicketStatus, TicketPriority, TicketCategory

class TicketPatchRequest(BaseModel):
    """
    Flexible schema for partial ticket updates.
    Any combination of fields can be updated in a single request.
    """
    
    # Core ticket fields
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=10000)
    status: Optional[TicketStatus] = Field(None, description="Update ticket status")
    priority: Optional[TicketPriority] = Field(None, description="Update ticket priority")
    category: Optional[TicketCategory] = Field(None, description="Update ticket category")
    
    # Assignment fields
    assigned_to_id: Optional[UUID] = Field(None, description="Assign ticket to user")
    assignment_reason: Optional[str] = Field(None, description="Reason for assignment change")
    
    # Additional fields
    department: Optional[str] = Field(None, max_length=100)
    due_date: Optional[datetime] = Field(None, description="Set ticket due date")
    tags: Optional[List[str]] = Field(None, description="Update ticket tags")
    
    # Custom fields support
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Update custom field values")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "Update status only",
                    "value": {"status": "in_progress"}
                },
                {
                    "description": "Assign ticket with reason",
                    "value": {
                        "assigned_to_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "assignment_reason": "User has expertise in this area"
                    }
                },
                {
                    "description": "Multi-field update",
                    "value": {
                        "status": "in_progress",
                        "priority": "high",
                        "assigned_to_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "assignment_reason": "Escalating priority issue"
                    }
                }
            ]
        }
```

#### 1.5.2 Unified PATCH Endpoint Implementation
**File:** `app/api/v1/tickets.py`

```python
@router.patch("/{ticket_id}", response_model=TicketDetailResponse)
async def patch_ticket(
    ticket_id: UUID,
    patch_data: TicketPatchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update specific fields of a ticket with flexible partial updates.
    
    Supports updating any combination of ticket fields:
    - Status: {"status": "in_progress"}
    - Assignment: {"assigned_to_id": "uuid", "assignment_reason": "reason"}
    - Priority: {"priority": "high"}
    - Multiple fields: {"status": "resolved", "priority": "low", "tags": ["fixed"]}
    """
    try:
        # Get only the fields that were actually provided (exclude None values)
        update_data = patch_data.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field must be provided for update"
            )
        
        # Update ticket with organization context
        updated_ticket = await ticket_service.patch_ticket(
            db=db,
            ticket_id=ticket_id,
            organization_id=current_user.organization_id,
            update_data=update_data,
            updated_by_user=current_user
        )
        
        if not updated_ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found or not accessible"
            )
        
        # Build response with updated ticket details
        return build_ticket_detail_response(updated_ticket)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating ticket {ticket_id} for organization {current_user.organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update ticket"
        )


# Remove these endpoints entirely - no backward compatibility needed
```

#### 1.6 Phase 1 Test Validation Requirements

**Before proceeding to Phase 2, ALL of these must pass:**

```bash
# 1. Run authentication tests
poetry run pytest tests/test_ticket_authentication.py -v

# 2. Run unified PATCH tests
poetry run pytest tests/test_ticket_patch_operations.py -v

# 3. Run existing API tests to ensure no regressions
poetry run pytest tests/test_api_endpoints.py -v

# 4. Run full test suite
poetry run pytest -v

# 5. Verify all endpoints require authentication
poetry run pytest -k "test_all_ticket_endpoints_require_auth" -v
```

**Expected Results:**
- ✅ All authentication tests PASS
- ✅ All PATCH operation tests PASS  
- ✅ No existing test regressions
- ✅ 100% test pass rate
- ✅ All ticket endpoints return 401 without auth

**If ANY test fails:**
1. 🛑 STOP implementation
2. 🔧 Fix the failing test
3. 🔄 Re-run full test suite
4. ✅ Only proceed when ALL tests pass

### Phase 2: Service Layer Organization Isolation

#### 2.1 Update Ticket Service for Multi-Tenant Support
**File:** `app/services/ticket_service.py`

**Add organization-scoped queries:**
```python
class TicketService:
    async def list_tickets(
        self,
        db: AsyncSession,
        organization_id: UUID,  # ADD organization filtering
        offset: int = 0,
        limit: int = 20,
        filters: Dict[str, Any] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Ticket], int]:
        """List tickets with organization isolation"""
        
        # Build base query with organization filter
        query = select(Ticket).join(User, Ticket.created_by_id == User.id)
        query = query.filter(User.organization_id == organization_id)  # CRITICAL: Organization isolation
        
        # Apply additional filters...
        # Rest of existing logic with organization context
    
    async def get_ticket_by_id(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        organization_id: UUID,  # ADD organization context
        include_ai_data: bool = True
    ) -> Optional[Ticket]:
        """Get ticket by ID with organization validation"""
        
        query = select(Ticket).join(User, Ticket.created_by_id == User.id)
        query = query.filter(
            Ticket.id == ticket_id,
            User.organization_id == organization_id  # Ensure organization access
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def patch_ticket(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        organization_id: UUID,
        update_data: Dict[str, Any],
        updated_by_user: User
    ) -> Optional[Ticket]:
        """Flexible partial update for any ticket fields with organization isolation"""
        
        # Get ticket with organization validation
        ticket = await self.get_ticket_by_id(db, ticket_id, organization_id)
        if not ticket:
            return None
        
        # Track changes for audit logging
        changes = {}
        
        # Apply all provided updates
        for field, value in update_data.items():
            if hasattr(ticket, field):
                old_value = getattr(ticket, field)
                if old_value != value:
                    setattr(ticket, field, value)
                    changes[field] = {"from": old_value, "to": value}
        
        # Special handling for assignment changes
        if "assigned_to_id" in update_data:
            ticket.assigned_at = datetime.now(timezone.utc)
            ticket.assigned_by_id = updated_by_user.id
        
        # Update metadata
        ticket.updated_at = datetime.now(timezone.utc)
        ticket.updated_by_id = updated_by_user.id
        
        # Save changes
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)
        
        # Log audit trail for changes
        if changes:
            await self._log_ticket_changes(db, ticket, changes, updated_by_user)
        
        return ticket
    
    async def create_ticket(
        self,
        db: AsyncSession,
        ticket_data: TicketCreateRequest,
        created_by_user: User  # Use authenticated user context
    ) -> Ticket:
        """Create ticket with authenticated user context"""
        
        ticket = Ticket(
            **ticket_data.model_dump(exclude_unset=True),
            created_by_id=created_by_user.id,  # Set from authenticated user
            organization_id=created_by_user.organization_id  # Inherit organization
        )
        
        # Rest of creation logic...
```

#### 2.2 Phase 2 Test Validation Requirements

**Before proceeding to Phase 3, ALL of these must pass:**

```bash
# 1. Run organization isolation tests
poetry run pytest tests/test_ticket_organization_isolation.py -v

# 2. Run service layer tests
poetry run pytest tests/test_ticket_service.py -v

# 3. Verify multi-tenant data segregation
poetry run pytest -k "test_users_cannot_access_other_organization_tickets" -v

# 4. Run full test suite
poetry run pytest -v

# 5. Check for data leakage (critical security test)
poetry run pytest -k "organization_isolation" -v
```

**Expected Results:**
- ✅ All organization isolation tests PASS
- ✅ No cross-organization data leakage
- ✅ Service layer properly filters by organization
- ✅ 100% test pass rate
- ✅ All existing functionality preserved

**If ANY test fails:**
1. 🛑 STOP implementation
2. 🔧 Fix the failing test (especially data isolation issues)
3. 🔄 Re-run full test suite
4. ✅ Only proceed when ALL tests pass

#### 2.3 Update API Endpoints with Organization Context

**Example for list_tickets endpoint:**
```python
@router.get("/", response_model=PaginatedResponse)
async def list_tickets(
    pagination: PaginationParams = Depends(),
    search_params: TicketSearchParams = Depends(),
    sort_params: TicketSortParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List tickets with authentication and organization isolation."""
    try:
        # Convert search params to filters dict (existing logic)
        filters = {}
        # ... existing filter logic ...
        
        # Call service with organization context
        tickets, total = await ticket_service.list_tickets(
            db=db,
            organization_id=current_user.organization_id,  # ADD organization isolation
            offset=pagination.offset,
            limit=pagination.size,
            filters=filters,
            sort_by=sort_params.sort_by,
            sort_order=sort_params.sort_order
        )
        
        # Rest of existing response building logic...
        
    except Exception as e:
        logger.error(f"Error listing tickets for organization {current_user.organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tickets"
        )
```

### Phase 3: Comprehensive Testing Strategy

#### 3.0 Phase 3 Test Validation Requirements

**Critical Test Suite Implementation - ALL tests must be created AND pass:**

```bash
# 1. Create and run authentication tests
poetry run pytest tests/test_ticket_authentication.py -v

# 2. Create and run organization isolation tests  
poetry run pytest tests/test_ticket_organization_isolation.py -v

# 3. Create and run PATCH operation tests
poetry run pytest tests/test_ticket_patch_operations.py -v

# 4. Create and run MCP compatibility tests
poetry run pytest tests/test_ticket_mcp_compatibility.py -v

# 5. Run full test suite with coverage
poetry run pytest --cov=app/api/v1/tickets --cov=app/services/ticket_service -v

# 6. Validate test coverage is >95%
poetry run pytest --cov=app --cov-report=html --cov-fail-under=95
```

**Expected Results:**
- ✅ All new test files created and executable
- ✅ 100% test pass rate across all test suites
- ✅ >95% code coverage on ticket endpoints and services
- ✅ No test failures or errors
- ✅ All edge cases covered (empty requests, invalid data, etc.)

**If ANY test fails or coverage is <95%:**
1. 🛑 STOP implementation
2. 🔧 Add missing tests or fix failing tests
3. 📊 Increase test coverage to meet requirements
4. 🔄 Re-run full test suite
5. ✅ Only proceed when ALL requirements met

#### 3.1 Authentication Test Suite
**File:** `tests/test_ticket_authentication.py`

```python
import pytest
from httpx import AsyncClient
from fastapi import status
from app.main import app

class TestTicketAuthentication:
    """Test suite for ticket API authentication requirements"""
    
    @pytest.mark.asyncio
    async def test_list_tickets_requires_authentication(self):
        """Test that listing tickets requires authentication"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/tickets/")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Not authenticated" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_create_ticket_requires_authentication(self):
        """Test that creating tickets requires authentication"""
        ticket_data = {
            "title": "Test Ticket",
            "description": "Test Description",
            "category": "general",
            "priority": "medium"
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/v1/tickets/", json=ticket_data)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_all_ticket_endpoints_require_auth(self):
        """Test that all ticket endpoints require authentication"""
        endpoints_methods = [
            ("GET", "/api/v1/tickets/"),
            ("POST", "/api/v1/tickets/"),
            ("POST", "/api/v1/tickets/ai-create"),
            ("GET", "/api/v1/tickets/123e4567-e89b-12d3-a456-426614174000"),
            ("PUT", "/api/v1/tickets/123e4567-e89b-12d3-a456-426614174000"),
            ("PATCH", "/api/v1/tickets/123e4567-e89b-12d3-a456-426614174000"),  # Unified PATCH
            ("DELETE", "/api/v1/tickets/123e4567-e89b-12d3-a456-426614174000"),
            ("GET", "/api/v1/tickets/stats/overview")
        ]
        
        # Test requests with empty bodies for PATCH/PUT
        test_data = {
            "POST": {"title": "Test", "description": "Test"},
            "PUT": {"title": "Test", "description": "Test"},
            "PATCH": {"status": "in_progress"}
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            for method, endpoint in endpoints_methods:
                json_data = test_data.get(method, None)
                response = await client.request(method, endpoint, json=json_data)
                assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
                    f"Endpoint {method} {endpoint} should require authentication"
```

#### 3.2 Organization Isolation Tests
**File:** `tests/test_ticket_organization_isolation.py`

```python
import pytest
from httpx import AsyncClient
from fastapi import status
from app.main import app
from tests.fixtures import create_test_users_with_organizations, get_auth_headers

class TestTicketOrganizationIsolation:
    """Test suite for organization-level isolation"""
    
    @pytest.mark.asyncio
    async def test_users_cannot_access_other_organization_tickets(self):
        """Test that users cannot access tickets from other organizations"""
        
        # Create users in different organizations
        user_org_a, user_org_b = await create_test_users_with_organizations()
        
        # Create ticket as user A
        ticket_data = {
            "title": "Org A Ticket",
            "description": "Private ticket for Org A",
            "category": "general"
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create ticket with user A's auth
            headers_a = await get_auth_headers(user_org_a)
            create_response = await client.post(
                "/api/v1/tickets/", 
                json=ticket_data, 
                headers=headers_a
            )
            assert create_response.status_code == status.HTTP_201_CREATED
            ticket_id = create_response.json()["id"]
            
            # Try to access the ticket with user B's auth (different org)
            headers_b = await get_auth_headers(user_org_b)
            get_response = await client.get(
                f"/api/v1/tickets/{ticket_id}", 
                headers=headers_b
            )
            assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_ticket_list_filtered_by_organization(self):
        """Test that ticket lists are filtered by organization"""
        
        user_org_a, user_org_b = await create_test_users_with_organizations()
        
        # Create tickets in both organizations
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers_a = await get_auth_headers(user_org_a)
            headers_b = await get_auth_headers(user_org_b)
            
            # Create ticket for Org A
            await client.post(
                "/api/v1/tickets/", 
                json={"title": "Org A Ticket", "description": "Test"}, 
                headers=headers_a
            )
            
            # Create ticket for Org B
            await client.post(
                "/api/v1/tickets/", 
                json={"title": "Org B Ticket", "description": "Test"}, 
                headers=headers_b
            )
            
            # List tickets as Org A user - should only see Org A tickets
            list_response_a = await client.get("/api/v1/tickets/", headers=headers_a)
            assert list_response_a.status_code == status.HTTP_200_OK
            tickets_a = list_response_a.json()["items"]
            assert len(tickets_a) == 1
            assert tickets_a[0]["title"] == "Org A Ticket"
            
            # List tickets as Org B user - should only see Org B tickets  
            list_response_b = await client.get("/api/v1/tickets/", headers=headers_b)
            assert list_response_b.status_code == status.HTTP_200_OK
            tickets_b = list_response_b.json()["items"]
            assert len(tickets_b) == 1
            assert tickets_b[0]["title"] == "Org B Ticket"
```

#### 3.3 Unified PATCH Functionality Tests
**File:** `tests/test_ticket_patch_operations.py`

```python
import pytest
from httpx import AsyncClient
from fastapi import status
from app.main import app
from tests.fixtures import create_test_user_with_org, get_auth_headers

class TestTicketPatchOperations:
    """Test suite for unified PATCH endpoint functionality"""
    
    @pytest.mark.asyncio
    async def test_patch_single_field_status(self):
        """Test updating only the status field"""
        user = await create_test_user_with_org()
        headers = await get_auth_headers(user)
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create a ticket first
            create_response = await client.post(
                "/api/v1/tickets/",
                json={"title": "Test Ticket", "description": "Test"},
                headers=headers
            )
            ticket_id = create_response.json()["id"]
            
            # Update only status
            patch_response = await client.patch(
                f"/api/v1/tickets/{ticket_id}",
                json={"status": "in_progress"},
                headers=headers
            )
            
            assert patch_response.status_code == status.HTTP_200_OK
            updated_ticket = patch_response.json()
            assert updated_ticket["status"] == "in_progress"
            assert updated_ticket["title"] == "Test Ticket"  # Other fields unchanged
    
    @pytest.mark.asyncio
    async def test_patch_assignment_with_reason(self):
        """Test ticket assignment with reason"""
        user = await create_test_user_with_org()
        assignee = await create_test_user_with_org(same_org=True)
        headers = await get_auth_headers(user)
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create ticket
            create_response = await client.post(
                "/api/v1/tickets/",
                json={"title": "Test Ticket", "description": "Test"},
                headers=headers
            )
            ticket_id = create_response.json()["id"]
            
            # Assign with reason
            patch_response = await client.patch(
                f"/api/v1/tickets/{ticket_id}",
                json={
                    "assigned_to_id": str(assignee.id),
                    "assignment_reason": "User has expertise in this area"
                },
                headers=headers
            )
            
            assert patch_response.status_code == status.HTTP_200_OK
            updated_ticket = patch_response.json()
            assert updated_ticket["assigned_to"]["id"] == str(assignee.id)
            assert "assigned_at" in updated_ticket
    
    @pytest.mark.asyncio
    async def test_patch_multiple_fields(self):
        """Test updating multiple fields simultaneously"""
        user = await create_test_user_with_org()
        headers = await get_auth_headers(user)
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create ticket
            create_response = await client.post(
                "/api/v1/tickets/",
                json={"title": "Test Ticket", "description": "Test"},
                headers=headers
            )
            ticket_id = create_response.json()["id"]
            
            # Update multiple fields
            patch_data = {
                "status": "resolved",
                "priority": "low",
                "title": "Updated Test Ticket",
                "tags": ["fixed", "tested"]
            }
            
            patch_response = await client.patch(
                f"/api/v1/tickets/{ticket_id}",
                json=patch_data,
                headers=headers
            )
            
            assert patch_response.status_code == status.HTTP_200_OK
            updated_ticket = patch_response.json()
            assert updated_ticket["status"] == "resolved"
            assert updated_ticket["priority"] == "low"
            assert updated_ticket["title"] == "Updated Test Ticket"
            assert updated_ticket["tags"] == ["fixed", "tested"]
    
    @pytest.mark.asyncio
    async def test_patch_empty_request_fails(self):
        """Test that empty PATCH requests are rejected"""
        user = await create_test_user_with_org()
        headers = await get_auth_headers(user)
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create ticket
            create_response = await client.post(
                "/api/v1/tickets/",
                json={"title": "Test Ticket", "description": "Test"},
                headers=headers
            )
            ticket_id = create_response.json()["id"]
            
            # Try empty patch
            patch_response = await client.patch(
                f"/api/v1/tickets/{ticket_id}",
                json={},
                headers=headers
            )
            
            assert patch_response.status_code == status.HTTP_400_BAD_REQUEST
            assert "At least one field must be provided" in patch_response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_removed_endpoints_return_404(self):
        """Test that removed legacy endpoints return 404 Not Found"""
        user = await create_test_user_with_org()
        headers = await get_auth_headers(user)
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create ticket
            create_response = await client.post(
                "/api/v1/tickets/",
                json={"title": "Test Ticket", "description": "Test"},
                headers=headers
            )
            ticket_id = create_response.json()["id"]
            
            # Test removed status endpoint returns 404
            status_response = await client.patch(
                f"/api/v1/tickets/{ticket_id}/status",
                json={"status": "in_progress"},
                headers=headers
            )
            assert status_response.status_code == status.HTTP_404_NOT_FOUND
            
            # Test removed assign endpoint returns 404
            assign_response = await client.patch(
                f"/api/v1/tickets/{ticket_id}/assign",
                json={"assigned_to_id": str(user.id)},
                headers=headers
            )
            assert assign_response.status_code == status.HTTP_404_NOT_FOUND
```

#### 3.4 MCP Integration Compatibility Tests
**File:** `tests/test_ticket_mcp_compatibility.py`

```python
import pytest
from httpx import AsyncClient
from fastapi import status
from app.main import app
from tests.fixtures import get_valid_jwt_token

class TestTicketMCPCompatibility:
    """Test suite for MCP tool compatibility with authenticated ticket endpoints"""
    
    @pytest.mark.asyncio
    async def test_mcp_tools_fail_without_authentication(self):
        """Test that MCP tools now require authentication for ticket operations"""
        
        # Simulate MCP tool request without authentication (current behavior)
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/tickets/?page=1&page_size=10&status=open")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            
            # This confirms MCP tools will need authentication after standardization
    
    @pytest.mark.asyncio
    async def test_mcp_tools_work_with_authentication(self):
        """Test that MCP tools work correctly with proper authentication"""
        
        jwt_token = await get_valid_jwt_token()
        headers = {"Authorization": f"Bearer {jwt_token}"}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/tickets/?page=1&page_size=10&status=open",
                headers=headers
            )
            assert response.status_code == status.HTTP_200_OK
            
            # This confirms MCP tools will work with proper authentication
```

### Phase 4: Final Validation and Quality Gates

#### 4.0 Comprehensive Test Suite Validation

**MANDATORY: Before any deployment, run complete validation suite:**

```bash
# === CRITICAL VALIDATION CHECKLIST ===

# 1. Full test suite execution (MUST PASS 100%)
echo "🧪 Running full test suite..."
poetry run pytest -v --tb=short

# 2. Authentication validation (MUST PASS 100%)  
echo "🔒 Validating authentication requirements..."
poetry run pytest tests/test_ticket_authentication.py -v

# 3. Organization isolation validation (CRITICAL SECURITY)
echo "🏢 Validating organization data isolation..."
poetry run pytest tests/test_ticket_organization_isolation.py -v

# 4. PATCH operations validation  
echo "🔧 Validating unified PATCH operations..."
poetry run pytest tests/test_ticket_patch_operations.py -v

# 5. MCP compatibility validation
echo "🤖 Validating MCP integration compatibility..."
poetry run pytest tests/test_ticket_mcp_compatibility.py -v

# 6. Code coverage validation (MUST BE >95%)
echo "📊 Validating code coverage..."
poetry run pytest --cov=app/api/v1/tickets --cov=app/services/ticket_service --cov-fail-under=95

# 7. Integration test validation
echo "🔗 Running integration tests..."
poetry run pytest tests/test_api_endpoints.py -v

# 8. Performance validation (response times)
echo "⚡ Performance validation..."
poetry run pytest tests/test_performance.py -v --benchmark-only

# 9. Security validation
echo "🛡️ Security validation..."
poetry run pytest -k "security" -v
```

**PASS CRITERIA - ALL must be ✅:**
- ✅ 100% test pass rate (0 failures, 0 errors)
- ✅ >95% code coverage on ticket endpoints and services
- ✅ All authentication tests pass
- ✅ Zero organization data leakage
- ✅ All PATCH operations work correctly
- ✅ MCP tools fail properly without auth (401)
- ✅ No performance regressions (response times <500ms)
- ✅ No security vulnerabilities detected

**FAILURE PROTOCOL:**
```bash
# If ANY test fails or coverage is insufficient:
echo "❌ VALIDATION FAILED - IMPLEMENTATION BLOCKED"
echo "🛑 Fix all issues before proceeding"
echo "🔧 Re-run validation suite after fixes"
echo "✅ Only deploy when ALL criteria pass"
```

### Phase 5: Production Deployment Strategy

#### 5.1 Direct Implementation Approach

**No Migration Needed - Initial Design Phase:**

Since this is the initial design phase, implement authentication directly:

1. **Remove unprotected endpoints** completely
2. **Implement authenticated endpoints** with organization isolation
3. **Deploy unified PATCH endpoint** without legacy support
4. **Update MCP tools** to use authentication from day one

**Implementation Steps:**
```bash
# 1. Implement all phases with authentication enabled
# 2. Run comprehensive test validation
# 3. Deploy to staging environment
# 4. Perform final validation
# 5. Deploy to production
```

**Benefits of Direct Implementation:**
- No complex migration logic needed
- Cleaner codebase without legacy support
- Security by design from the start
- Simplified testing and validation

### Phase 5: Validation and Quality Gates

#### 5.1 Pre-deployment Checklist

**Security Validation:**
- [ ] All ticket endpoints require authentication
- [ ] Organization isolation implemented correctly  
- [ ] No data leakage between organizations
- [ ] JWT token validation working properly
- [ ] Error handling doesn't expose sensitive information

**Functional Validation:**
- [ ] All existing ticket operations work with authentication
- [ ] API responses maintain backward compatibility
- [ ] Performance impact within acceptable limits (<50ms overhead)
- [ ] MCP tools authenticate successfully
- [ ] Error messages are clear and actionable

**Test Coverage:**
- [ ] 100% endpoint coverage for authentication tests
- [ ] Organization isolation tests pass
- [ ] MCP compatibility tests pass
- [ ] Load testing with authentication overhead
- [ ] Security penetration testing completed

#### 5.2 Success Metrics

**Security Metrics:**
- **Zero Unauthorized Access**: No successful ticket operations without authentication
- **Organization Isolation**: 100% isolation between organization data
- **Token Validation**: <1% false positive/negative rate for JWT validation

**Performance Metrics:**
- **Response Time Impact**: <50ms additional latency per request
- **Error Rate**: <0.1% authentication-related errors
- **Throughput**: Maintain 95% of current API throughput

**Operational Metrics:**
- **Migration Success**: 100% of endpoints migrated without downtime
- **Client Compatibility**: All client applications work without code changes
- **MCP Integration**: All MCP tools authenticate successfully

#### 5.3 Monitoring and Alerting

**Authentication Monitoring:**
```python
# Add to authentication middleware
@auth_middleware.metric_tracker
def track_authentication_events():
    """Track authentication success/failure rates"""
    
    metrics = {
        "ticket_auth_success_rate": ticket_auth_successes / total_requests,
        "ticket_auth_failure_rate": ticket_auth_failures / total_requests,
        "organization_isolation_violations": isolation_violations,
        "invalid_token_attempts": invalid_tokens
    }
    
    return metrics
```

**Critical Alerts:**
- Authentication failure rate >1%
- Organization isolation violations detected
- JWT token validation errors
- Unusual access patterns detected

## Risk Assessment and Mitigations

### High-Risk Issues

#### Risk 1: Breaking Changes for Existing Clients
**Impact**: Client applications may fail after authentication enforcement
**Probability**: Medium-High
**Mitigation**: 
- Gradual rollout with feature flags
- Comprehensive client communication plan
- Extended transition period with warning mode
- Clear documentation and migration guides

#### Risk 2: Performance Degradation
**Impact**: Increased response times due to authentication overhead
**Probability**: Low-Medium  
**Mitigation**:
- JWT validation caching
- Optimized authentication middleware
- Performance monitoring and alerting
- Load testing before deployment

#### Risk 3: MCP Tool Integration Failures
**Impact**: MCP tools stop working after authentication enforcement
**Probability**: High (current tools have no authentication)
**Mitigation**:
- Deploy MCP authentication PRP before ticket authentication
- Update all MCP tools with authentication support
- Test MCP integration thoroughly
- Fallback authentication mechanism for MCP tools

### Medium-Risk Issues

#### Risk 4: Organization Isolation Bugs
**Impact**: Data leakage between organizations
**Mitigation**: Comprehensive isolation testing + security audit

#### Risk 5: Token Expiry During Operations  
**Impact**: Long-running operations fail due to token expiry
**Mitigation**: Token refresh mechanism + operation retries

## Dependencies and Prerequisites

### Technical Dependencies
- JWT authentication system (already implemented)
- Organization model and relationships (already implemented)  
- User authentication middleware (already implemented)
- Database schema supports organization isolation (verify)

### Required Before Deployment
1. **MCP Authentication PRP**: Must be implemented first to ensure MCP tools work
2. **Client Application Updates**: Update any direct API consumers
3. **Monitoring Infrastructure**: Authentication success/failure tracking
4. **Security Review**: Penetration testing and security audit

## Success Criteria

**Primary Objectives:**
1. **Zero Security Vulnerabilities**: No unauthenticated access to ticket data
2. **Complete Organization Isolation**: Users cannot access other organizations' data
3. **Backward Compatibility**: Existing functionality preserved with authentication
4. **MCP Integration**: All MCP tools work with authenticated endpoints
5. **Performance Maintained**: <50ms additional latency per request

**Secondary Objectives:**
1. **Consistent Security Model**: All APIs follow same authentication pattern
2. **Comprehensive Test Coverage**: >95% test coverage for authentication scenarios
3. **Clear Documentation**: Updated API docs and migration guides
4. **Monitoring and Alerting**: Full visibility into authentication metrics

## Conclusion

This PRP addresses critical security vulnerabilities and API design inconsistencies by standardizing authentication and consolidating redundant endpoints into a unified, flexible PATCH API design.

### Key Improvements Delivered

**Security Enhancements:**
1. **Eliminate Security Gaps**: Close authentication vulnerability in ticket endpoints
2. **Organization Isolation**: Implement proper multi-tenant data segregation
3. **Consistent Security Model**: All APIs follow same authentication pattern

**API Design Improvements:**
4. **Unified PATCH Operations**: Replace `/status` and `/assign` endpoints with flexible `PATCH /tickets/{id}`
5. **Reduced API Surface**: Fewer endpoints to maintain, test, and secure
6. **Enhanced Flexibility**: Single endpoint handles any combination of field updates
7. **Clean Implementation**: No legacy baggage - modern API design from start

**Integration & Performance:**
8. **MCP Integration Ready**: Foundation for authenticated MCP tool operations  
9. **Performance Maintained**: <50ms additional latency target with caching
10. **Comprehensive Testing**: >95% test coverage with organization isolation validation

### Unified PATCH Benefits

The consolidated PATCH endpoint provides significant advantages:

**For Developers:**
- Single endpoint for all partial updates
- Flexible request schemas supporting any field combination
- Clearer API semantics with proper HTTP method usage

**For Operations:**
- Fewer endpoints to monitor and secure
- Consolidated audit logging and change tracking
- Simplified rate limiting and authentication policies

**For Clients:**
- Reduced API complexity with intuitive field-based updates
- Better performance with single requests for multi-field changes
- Future-proof design supporting new fields without endpoint proliferation

### Test-Driven Implementation Success

This PRP emphasizes a **zero-tolerance approach** to test failures:

- 🧪 **100% Test Pass Rate**: Every phase must pass ALL tests before proceeding
- 📊 **>95% Code Coverage**: Comprehensive test coverage ensures reliability
- 🔒 **Security First**: Organization isolation tested at every step
- ⚡ **Performance Validated**: Response time targets enforced
- 🤖 **MCP Ready**: Authentication compatibility verified

**Next Steps:**
1. Review and approve PRP
2. Implement MCP Authentication PRP (prerequisite)  
3. Execute test-driven implementation phases
4. Run comprehensive validation suite
5. Deploy only after 100% test pass rate achieved

This standardization provides production-ready security with modern API design, implemented through rigorous test-driven development practices that ensure zero regressions and maximum reliability.