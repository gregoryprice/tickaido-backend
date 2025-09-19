# PRP: Ticket Integration Information Refactor

## Overview

Refactor ticket API responses to standardize integration information handling across all ticket endpoints (POST, GET, UPDATE, LIST). Remove the `integration_routing` field and replace with comprehensive `integration_result` data to provide better visibility into external integration status.

## Problem Statement

Currently, ticket endpoints return inconsistent integration information:
- POST `/api/v1/tickets/` returns full `integration_result` object with detailed integration status
- GET `/api/v1/tickets/{ticket_id}` returns `integration_result: null` and separate `external_ticket_id`/`external_ticket_url` fields
- Different ticket endpoints use different response models, creating inconsistency
- `integration_routing` field exists but appears unused and should be removed

## Requirements

### 1. Data Model Standardization
- Remove `integration_routing` field from ticket model and all related code
- Ensure `integration_result` field is properly stored and retrieved from database
- All ticket endpoints (POST, GET, UPDATE, LIST) must return identical response structure

### 2. API Response Consistency
- POST `/api/v1/tickets/` - Continue returning full `integration_result` object standardize the Response model to use in the endpoints
- GET `/api/v1/tickets/{ticket_id}` - Return `integration_result` object instead of null
- UPDATE ticket endpoints - Return consistent `integration_result` data
- LIST tickets endpoint - Return consistent `integration_result` data for each ticket

### 3. Integration Result Structure
The `integration_result` object should contain:
```json
{
    "success": true,
    "integration_id": "820703db-1835-47e2-b09c-6933b927bb8e",
    "external_ticket_id": "TINT-12",
    "external_ticket_url": "https://shipwell.atlassian.net/browse/TINT-12",
    "error_message": null,
    "response": {
        "key": "TINT-12",
        "id": "76911",
        "url": "https://shipwell.atlassian.net/browse/TINT-12",
        "self": "https://shipwell.atlassian.net/rest/api/3/issue/76911",
        "project_key": "TINT",
        "issue_type": "Bug",
        "summary": "Application Login Issue - Unable to Access Dashboard",
        "attachments": [...],
        "attachment_summary": {
            "total_files": 1,
            "successful_uploads": 1,
            "failed_uploads": 0
        }
    }
}
```

## Implementation Plan

### Phase 1: Database Schema Updates
1. **Review current database schema**
   - Examine `tickets` table structure
   - Identify how `integration_result` is currently stored
   - Verify `integration_routing` field usage across codebase

2. **Database migration (if needed)**
   - Create migration to remove `integration_routing` column
   - Ensure `integration_result` JSON field properly stores complete integration data
   - Update any existing records with missing integration data

### Phase 2: Model and Schema Updates
1. **Update SQLAlchemy models**
   - Remove `integration_routing` from `Ticket` model in `app/models/ticket.py`
   - Ensure `integration_result` field properly handles JSON serialization/deserialization
   
2. **Update Pydantic schemas**
   - Remove `integration_routing` from all ticket response schemas in `app/schemas/ticket.py`
   - Ensure all ticket schemas (create, read, update, list) include `integration_result` field
   - Consolidate to single ticket response schema across all endpoints

### Phase 3: Service Layer Updates
1. **Update ticket service methods**
   - Modify `app/services/ticket_service.py` to handle `integration_result` storage/retrieval
   - Ensure integration data is properly preserved during ticket operations
   - Remove any `integration_routing` related logic

2. **Update integration services**
   - Review `app/services/jira_integration.py` and related integration services
   - Ensure integration result data is properly structured and stored

### Phase 4: API Endpoint Updates
1. **Update ticket API routes**
   - Modify `app/api/v1/tickets.py` endpoints:
     - POST `/api/v1/tickets/` - Ensure integration_result is stored
     - GET `/api/v1/tickets/{ticket_id}` - Return stored integration_result instead of null
     - PUT/PATCH ticket update endpoints - Return consistent integration_result
     - GET `/api/v1/tickets/` - Return integration_result for each ticket in list

2. **Response model consolidation**
   - Use single response model across all ticket endpoints
   - Remove separate response models that create inconsistencies

### Phase 5: Code Cleanup
1. **Remove integration_routing references**
   - Search entire codebase for `integration_routing` usage
   - Remove from models, schemas, services, and any other references
   - Clean up any unused imports or helper functions

2. **Update related services**
   - Update any background tasks that handle integration data
   - Update WebSocket handlers if they send ticket data
   - Review MCP server integration if it handles ticket data

## Testing Strategy

### Unit Tests
1. **Model tests**
   - Test ticket model without `integration_routing` field
   - Test `integration_result` JSON serialization/deserialization
   - Test ticket creation/retrieval with integration data

2. **Service tests**
   - Test ticket service methods return consistent integration data
   - Test integration services properly store result data
   - Test ticket operations preserve integration information

3. **Schema validation tests**
   - Test all ticket endpoints return same response structure
   - Test integration_result field validation
   - Test removal of integration_routing from responses

### Integration Tests
1. **API endpoint tests**
   - Test POST ticket returns integration_result
   - Test GET ticket returns stored integration_result (not null)
   - Test UPDATE ticket preserves and returns integration_result
   - Test LIST tickets returns integration_result for each ticket
   - Test consistency across all endpoints

2. **Database integration tests**
   - Test integration_result data persistence
   - Test ticket queries properly retrieve integration data
   - Test migration removes integration_routing successfully

### End-to-End Tests
1. **Full ticket lifecycle**
   - Create ticket with integration → verify integration_result stored
   - Retrieve ticket → verify integration_result returned consistently
   - Update ticket → verify integration_result preserved
   - List tickets → verify integration_result included

2. **Integration workflow tests**
   - Test ticket creation with Jira integration
   - Verify integration_result contains complete integration information
   - Test error scenarios and integration_result error handling

## Validation Criteria

### Functional Requirements
- [ ] `integration_routing` field completely removed from codebase
- [ ] `integration_result` properly stored and retrieved from database
- [ ] All ticket endpoints (POST, GET, UPDATE, LIST) return identical response structure
- [ ] Integration data includes complete information (success status, IDs, URLs, response details)

### Technical Requirements
- [ ] Single ticket response schema used across all endpoints
- [ ] Database migration successfully removes integration_routing
- [ ] All existing tests updated and passing
- [ ] No breaking changes to external API consumers (except removal of integration_routing)

### Performance Requirements
- [ ] No performance degradation in ticket operations
- [ ] Integration_result data retrieval is efficient
- [ ] Database queries optimized for new structure

## Risks and Considerations

### Risks
1. **Data Loss**: Existing integration_routing data might be lost during migration
2. **API Breaking Changes**: External consumers might depend on integration_routing field
3. **Performance Impact**: Storing larger integration_result objects might affect query performance

### Mitigations
1. **Data Migration**: Carefully migrate any existing integration_routing data to integration_result format
2. **Backward Compatibility**: Document breaking change and provide migration guide for API consumers
3. **Performance Testing**: Benchmark database operations with new structure before deployment

### Dependencies
- Database migration must be carefully planned and tested
- Integration services (Jira, etc.) must continue working with new structure
- Background tasks handling ticket integration must be updated

## Deployment Strategy

### Pre-deployment
1. Run all tests in staging environment
2. Verify database migration works correctly
3. Test integration workflows end-to-end

### Deployment
1. Run database migration during maintenance window
2. Deploy application with updated code
3. Monitor integration workflows for issues

### Post-deployment
1. Verify all ticket endpoints return consistent data
2. Monitor API error rates and performance metrics
3. Validate integration workflows working correctly

## Success Metrics

- All ticket API endpoints return consistent response structure
- Integration_result data properly persists and retrieves
- No integration workflow failures after deployment
- API response times remain within acceptable limits
- Zero data loss during migration process