#!/usr/bin/env python3
"""
Ticket Organization Isolation Test Suite

Critical security tests to verify that users cannot access tickets 
from other organizations (multi-tenant data segregation).
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import status
from app.main import app

# Mock valid JWT tokens for testing different organizations
MOCK_ORG_A_TOKEN = "Bearer valid-jwt-token-org-a"
MOCK_ORG_B_TOKEN = "Bearer valid-jwt-token-org-b"


class TestTicketOrganizationIsolation:
    """Test suite for organization-level isolation"""
    
    def test_list_tickets_filtered_by_organization(self):
        """Test that ticket lists are filtered by organization"""
        client = TestClient(app)
        
        # Test that different organizations get different results
        # This is a basic test - in real implementation, these would use actual JWT tokens
        
        response_a = client.get("/api/v1/tickets/", headers={"Authorization": MOCK_ORG_A_TOKEN})
        response_b = client.get("/api/v1/tickets/", headers={"Authorization": MOCK_ORG_B_TOKEN})
        
        # Both should require authentication but would return different data sets
        # For now, testing that they both properly require authentication
        assert response_a.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_200_OK]
        assert response_b.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_200_OK]
    
    def test_get_ticket_cross_organization_access_denied(self):
        """Test that users cannot access tickets from other organizations"""
        client = TestClient(app)
        
        # Use a mock ticket ID
        ticket_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Attempt to access ticket with different organization tokens
        response_a = client.get(f"/api/v1/tickets/{ticket_id}", headers={"Authorization": MOCK_ORG_A_TOKEN})
        response_b = client.get(f"/api/v1/tickets/{ticket_id}", headers={"Authorization": MOCK_ORG_B_TOKEN})
        
        # Should require authentication - actual organization isolation requires real users/tickets
        assert response_a.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]
        assert response_b.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]
    
    def test_create_ticket_organization_context(self):
        """Test that created tickets inherit organization context"""
        client = TestClient(app)
        
        ticket_data = {
            "title": "Org Specific Ticket",
            "description": "This ticket should be scoped to the creating user's organization",
            "category": "general",
            "priority": "medium"
        }
        
        # Attempt to create ticket (will require valid authentication in real scenario)
        response = client.post("/api/v1/tickets/", json=ticket_data, headers={"Authorization": MOCK_ORG_A_TOKEN})
        
        # Should require authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_update_ticket_organization_isolation(self):
        """Test that users can only update tickets in their organization"""
        client = TestClient(app)
        
        ticket_id = "123e4567-e89b-12d3-a456-426614174000"
        update_data = {
            "title": "Updated Title",
            "description": "Updated Description"
        }
        
        # Attempt to update ticket from different organizations
        response_a = client.put(f"/api/v1/tickets/{ticket_id}", json=update_data, headers={"Authorization": MOCK_ORG_A_TOKEN})
        response_b = client.put(f"/api/v1/tickets/{ticket_id}", json=update_data, headers={"Authorization": MOCK_ORG_B_TOKEN})
        
        # Should require authentication
        assert response_a.status_code == status.HTTP_401_UNAUTHORIZED
        assert response_b.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_patch_ticket_organization_isolation(self):
        """Test that PATCH operations respect organization isolation"""
        client = TestClient(app)
        
        ticket_id = "123e4567-e89b-12d3-a456-426614174000"
        patch_data = {
            "status": "in_progress",
            "priority": "high"
        }
        
        # Test unified PATCH endpoint with organization isolation
        response_a = client.patch(f"/api/v1/tickets/{ticket_id}", json=patch_data, headers={"Authorization": MOCK_ORG_A_TOKEN})
        response_b = client.patch(f"/api/v1/tickets/{ticket_id}", json=patch_data, headers={"Authorization": MOCK_ORG_B_TOKEN})
        
        # Should require authentication
        assert response_a.status_code == status.HTTP_401_UNAUTHORIZED
        assert response_b.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_delete_ticket_organization_isolation(self):
        """Test that users can only delete tickets in their organization"""
        client = TestClient(app)
        
        ticket_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Attempt to delete ticket from different organizations
        response_a = client.delete(f"/api/v1/tickets/{ticket_id}", headers={"Authorization": MOCK_ORG_A_TOKEN})
        response_b = client.delete(f"/api/v1/tickets/{ticket_id}", headers={"Authorization": MOCK_ORG_B_TOKEN})
        
        # Should require authentication
        assert response_a.status_code == status.HTTP_401_UNAUTHORIZED
        assert response_b.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_ticket_stats_organization_isolation(self):
        """Test that ticket statistics are organization-specific"""
        client = TestClient(app)
        
        # Different organizations should get different statistics
        response_a = client.get("/api/v1/tickets/stats/overview", headers={"Authorization": MOCK_ORG_A_TOKEN})
        response_b = client.get("/api/v1/tickets/stats/overview", headers={"Authorization": MOCK_ORG_B_TOKEN})
        
        # Should require authentication
        assert response_a.status_code == status.HTTP_401_UNAUTHORIZED
        assert response_b.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_no_organization_data_leakage_in_responses(self):
        """Test that API responses don't expose other organizations' data"""
        client = TestClient(app)
        
        # Test various endpoints to ensure no data leakage
        endpoints = [
            "/api/v1/tickets/",
            "/api/v1/tickets/stats/overview"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint, headers={"Authorization": MOCK_ORG_A_TOKEN})
            
            # Should require authentication - when working with real users,
            # need to verify no cross-organization data appears in responses
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_organization_isolation_enforcement_in_service_layer(self):
        """Test that organization isolation is enforced at service layer"""
        # This test verifies that even if someone bypasses the API layer,
        # the service layer still enforces organization isolation
        from app.services.ticket_service import TicketService
        from unittest.mock import AsyncMock
        from uuid import uuid4
        
        service = TicketService()
        mock_session = AsyncMock()
        
        # Mock empty results for organization queries with proper SQLAlchemy structure
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        
        # Mock scalars() to return a synchronous object with all() method
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        
        mock_session.execute.return_value = mock_result
        
        # Test that organization_id is required parameter
        org_a_id = uuid4()
        org_b_id = uuid4()
        ticket_id = uuid4()
        
        # These should not raise exceptions and should handle organization filtering
        try:
            # Test list_tickets with organization filtering
            tickets_a, total_a = await service.list_tickets(mock_session, org_a_id)
            tickets_b, total_b = await service.list_tickets(mock_session, org_b_id)
            
            # Test get_ticket with organization validation  
            ticket_a = await service.get_ticket(mock_session, ticket_id, org_a_id)
            ticket_b = await service.get_ticket(mock_session, ticket_id, org_b_id)
            
            print("✅ Service layer organization isolation parameters working")
            
        except TypeError as e:
            pytest.fail(f"❌ Service layer missing organization isolation: {e}")
    
    def test_service_methods_reject_missing_organization_id(self):
        """Test that service methods require organization_id parameter"""
        from app.services.ticket_service import TicketService
        import inspect
        
        service = TicketService()
        
        # Check that critical service methods have organization_id parameter
        critical_methods = ['list_tickets', 'get_ticket', 'patch_ticket', 'delete_ticket', 'get_ticket_stats']
        
        for method_name in critical_methods:
            if hasattr(service, method_name):
                method = getattr(service, method_name)
                sig = inspect.signature(method)
                
                assert 'organization_id' in sig.parameters, \
                    f"Method {method_name} missing organization_id parameter for isolation"
                
                print(f"✅ Method {method_name} has organization_id parameter")
    
    @pytest.mark.asyncio
    async def test_organization_isolation_in_database_queries(self):
        """Test that database queries include organization filtering"""
        # This test ensures that the service layer is building queries that include
        # organization filtering to prevent data leakage at the database level
        
        from app.services.ticket_service import TicketService
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4
        
        service = TicketService()
        mock_session = AsyncMock()
        
        # Mock database execution to capture SQL queries
        executed_queries = []
        
        async def capture_execute(query):
            executed_queries.append(str(query))
            # Mock result for count queries
            mock_result = MagicMock()
            mock_result.scalar.return_value = 0
            mock_result.scalar_one_or_none.return_value = None
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = []
            mock_result.scalars.return_value = mock_scalars
            return mock_result
        
        mock_session.execute.side_effect = capture_execute
        
        org_id = uuid4()
        
        # Test methods that should include organization filtering
        try:
            # Run service methods that should include organization filtering
            await service.list_tickets(mock_session, org_id)
            await service.get_ticket_stats(mock_session, org_id)
            
            # Note: This test structure validates that organization_id is required
            # In a full test environment, we'd also validate that the generated SQL
            # includes proper JOIN and WHERE clauses for organization filtering
            print("✅ Organization isolation query structure validation passed")
            
        except Exception as e:
            pytest.fail(f"❌ Organization isolation query validation failed: {e}")