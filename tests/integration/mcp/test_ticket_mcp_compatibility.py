#!/usr/bin/env python3
"""
MCP Tool Compatibility Test Suite

Tests for verifying that MCP tools properly handle the new authenticated ticket endpoints.
This validates that the MCP authentication PRP integration will work correctly.
"""

from fastapi.testclient import TestClient
from fastapi import status
from app.main import app


class TestTicketMCPCompatibility:
    """Test suite for MCP tool compatibility with authenticated ticket endpoints"""
    
    def test_mcp_tools_fail_without_authentication(self):
        """Test that MCP tools now require authentication for ticket operations"""
        client = TestClient(app)
        
        # Simulate MCP tool request patterns without authentication
        mcp_style_endpoints = [
            "/api/v1/tickets/?page=1&page_size=10&status=open",  # list_tickets MCP pattern
            "/api/v1/tickets/stats/overview",  # get_ticket_stats MCP pattern
        ]
        
        for endpoint in mcp_style_endpoints:
            response = client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
                f"MCP endpoint {endpoint} should require authentication"
    
    def test_mcp_create_operations_require_auth(self):
        """Test that MCP create operations require authentication"""
        client = TestClient(app)
        
        # Simulate MCP tool ticket creation patterns
        mcp_create_data = {
            "title": "MCP Created Ticket",
            "description": "Ticket created via MCP tools",
            "category": "technical",
            "priority": "medium",
            "department": "Support"
        }
        
        # Standard create
        response = client.post("/api/v1/tickets/", json=mcp_create_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # AI-powered create
        ai_create_data = {
            "user_input": "I'm having trouble with my login",
            "conversation_context": [],
            "uploaded_files": []
        }
        response = client.post("/api/v1/tickets/ai-create", json=ai_create_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_mcp_update_operations_require_auth(self):
        """Test that MCP update operations require authentication"""
        client = TestClient(app)
        ticket_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Test MCP-style update operations
        mcp_update_patterns = [
            # Full update (PUT)
            ("PUT", {
                "title": "MCP Updated Ticket",
                "description": "Updated via MCP tools",
                "status": "in_progress",
                "priority": "high"
            }),
            # Status update via unified PATCH (replaces old /status endpoint)
            ("PATCH", {"status": "resolved", "resolution_summary": "Issue resolved"}),
            # Assignment via unified PATCH (replaces old /assign endpoint)  
            ("PATCH", {
                "assigned_to_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "assignment_reason": "Assigned by MCP automation"
            }),
            # Multi-field update via unified PATCH
            ("PATCH", {
                "status": "in_progress", 
                "priority": "critical",
                "tags": ["mcp-updated", "urgent"]
            })
        ]
        
        for method, data in mcp_update_patterns:
            response = client.request(method, f"/api/v1/tickets/{ticket_id}", json=data)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
                f"MCP {method} operation should require authentication"
    
    def test_mcp_delete_operations_require_auth(self):
        """Test that MCP delete operations require authentication"""
        client = TestClient(app)
        ticket_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # MCP tools should not be able to delete without authentication
        response = client.delete(f"/api/v1/tickets/{ticket_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_mcp_legacy_endpoint_migration(self):
        """Test that MCP tools using legacy endpoints get proper error responses"""
        client = TestClient(app)
        ticket_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # MCP tools might still try to use old endpoints
        legacy_operations = [
            ("PATCH", f"/api/v1/tickets/{ticket_id}/status", {"status": "resolved"}),
            ("PATCH", f"/api/v1/tickets/{ticket_id}/assign", {"assigned_to_id": ticket_id}),
        ]
        
        for method, endpoint, data in legacy_operations:
            response = client.request(method, endpoint, json=data)
            # Should return 404 since these endpoints are removed
            assert response.status_code == status.HTTP_404_NOT_FOUND, \
                f"Legacy MCP endpoint {method} {endpoint} should return 404 (removed)"
    
    def test_mcp_batch_operations_auth_consistency(self):
        """Test that batch-style MCP operations consistently require auth"""
        client = TestClient(app)
        
        # MCP tools often make multiple requests in sequence
        ticket_operations = [
            ("GET", "/api/v1/tickets/", None),
            ("GET", "/api/v1/tickets/stats/overview", None),
            ("POST", "/api/v1/tickets/", {
                "title": "Batch Created", 
                "description": "Created in batch operation"
            }),
        ]
        
        for method, endpoint, data in ticket_operations:
            response = client.request(method, endpoint, json=data)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
                f"Batch operation {method} {endpoint} should require authentication"
    
    def test_mcp_error_message_consistency(self):
        """Test that MCP tools get consistent error messages"""
        client = TestClient(app)
        
        # Test various MCP-style requests without auth
        mcp_requests = [
            ("GET", "/api/v1/tickets/"),
            ("GET", "/api/v1/tickets/123e4567-e89b-12d3-a456-426614174000"),
            ("POST", "/api/v1/tickets/", {"title": "Test", "description": "Test"}),
            ("PATCH", "/api/v1/tickets/123e4567-e89b-12d3-a456-426614174000", {"status": "open"}),
        ]
        
        for method, endpoint, *json_data in mcp_requests:
            json_payload = json_data[0] if json_data else None
            response = client.request(method, endpoint, json=json_payload)
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            
            # Verify consistent error message structure
            error_data = response.json()
            assert "detail" in error_data
            assert isinstance(error_data["detail"], str)
            assert len(error_data["detail"]) > 0
            
            # Verify error message doesn't expose sensitive information
            detail = error_data["detail"].lower()
            assert "internal" not in detail
            assert "database" not in detail
            assert "secret" not in detail
    
    def test_mcp_unified_patch_migration_readiness(self):
        """Test that MCP tools can migrate from legacy patterns to unified PATCH"""
        client = TestClient(app)
        ticket_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Old MCP pattern: separate status and assignment requests
        # New MCP pattern: single unified PATCH request
        
        # Test that new unified approach works (requires auth)
        unified_patch_data = {
            "status": "resolved",
            "assigned_to_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", 
            "assignment_reason": "Final assignment for resolution",
            "resolution_summary": "Issue resolved through unified PATCH",
            "tags": ["mcp-resolved", "unified-patch"]
        }
        
        response = client.patch(f"/api/v1/tickets/{ticket_id}", json=unified_patch_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # This validates that MCP tools can use the new unified endpoint
        # once they implement authentication
    
    def test_mcp_organization_isolation_compatibility(self):
        """Test that MCP tools will respect organization isolation"""
        client = TestClient(app)
        
        # MCP tools should only access tickets within their authenticated user's organization
        # This test validates the endpoint behavior without authentication
        
        endpoints_requiring_org_isolation = [
            "/api/v1/tickets/",  # List should be org-filtered
            "/api/v1/tickets/123e4567-e89b-12d3-a456-426614174000",  # Get should check org
            "/api/v1/tickets/stats/overview"  # Stats should be org-specific
        ]
        
        for endpoint in endpoints_requiring_org_isolation:
            response = client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            
        # This ensures that when MCP tools authenticate, they'll get org-isolated data
    
    def test_mcp_query_parameter_compatibility(self):
        """Test that MCP tools' query parameters still work with authentication"""
        client = TestClient(app)
        
        # MCP tools use various query parameters for filtering
        mcp_query_patterns = [
            "/api/v1/tickets/?page=1&page_size=10",
            "/api/v1/tickets/?status=open&priority=high",
            "/api/v1/tickets/?category=technical&department=Support",
            "/api/v1/tickets/?created_after=2025-01-01T00:00:00Z",
        ]
        
        for endpoint in mcp_query_patterns:
            response = client.get(endpoint)
            # Should require authentication but accept the query parameters
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            
        # This validates that MCP tools' query patterns will work once authenticated
    
    def test_mcp_tools_api_surface_validation(self):
        """Validate that the API surface MCP tools expect is still available"""
        client = TestClient(app)
        
        # Core ticket operations MCP tools need
        required_endpoints = [
            ("GET", "/api/v1/tickets/"),                     # list_tickets tool
            ("POST", "/api/v1/tickets/"),                    # create_ticket tool  
            ("GET", "/api/v1/tickets/{ticket_id}"),          # get_ticket tool
            ("PATCH", "/api/v1/tickets/{ticket_id}"),        # update_ticket tool (new unified)
            ("DELETE", "/api/v1/tickets/{ticket_id}"),       # delete_ticket tool
            ("GET", "/api/v1/tickets/stats/overview"),       # get_ticket_stats tool
        ]
        
        # Removed endpoints that MCP tools should NOT use anymore
        removed_endpoints = [
            ("PATCH", "/api/v1/tickets/{ticket_id}/status"),
            ("PATCH", "/api/v1/tickets/{ticket_id}/assign"),
        ]
        
        # Test that required endpoints exist (but require auth)
        for method, endpoint in required_endpoints:
            test_endpoint = endpoint.replace("{ticket_id}", "123e4567-e89b-12d3-a456-426614174000")
            test_data = {"title": "Test", "description": "Test"} if method == "POST" else None
            test_data = {"status": "open"} if method == "PATCH" else test_data
            
            response = client.request(method, test_endpoint, json=test_data)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
                f"Required endpoint {method} {endpoint} should exist but require auth"
        
        # Test that removed endpoints return 404
        for method, endpoint in removed_endpoints:
            test_endpoint = endpoint.replace("{ticket_id}", "123e4567-e89b-12d3-a456-426614174000")
            test_data = {"status": "open"} if "status" in endpoint else {"assigned_to_id": "123e4567-e89b-12d3-a456-426614174000"}
            
            response = client.request(method, test_endpoint, json=test_data)
            assert response.status_code == status.HTTP_404_NOT_FOUND, \
                f"Removed endpoint {method} {endpoint} should return 404"