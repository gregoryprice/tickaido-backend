#!/usr/bin/env python3
"""
Ticket API Authentication Test Suite

Tests for verifying that all ticket endpoints require proper JWT authentication
and that legacy endpoints have been properly removed.
"""

from fastapi.testclient import TestClient
from fastapi import status
from app.main import app


class TestTicketAuthentication:
    """Test suite for ticket API authentication requirements"""
    
    def test_list_tickets_requires_authentication(self):
        """Test that listing tickets requires authentication"""
        client = TestClient(app)
        response = client.get("/api/v1/tickets/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication required" in response.json()["detail"]
    
    def test_create_ticket_requires_authentication(self):
        """Test that creating tickets requires authentication"""
        ticket_data = {
            "title": "Test Ticket",
            "description": "Test Description",
            "category": "general",
            "priority": "medium"
        }
        
        client = TestClient(app)
        response = client.post("/api/v1/tickets/", json=ticket_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_ai_create_ticket_requires_authentication(self):
        """Test that AI ticket creation requires authentication"""
        ai_request = {
            "user_input": "I need help with my login",
            "conversation_context": [],
            "uploaded_files": [],
            "user_preferences": {}
        }
        
        client = TestClient(app)
        response = client.post("/api/v1/tickets/ai-create", json=ai_request)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_ticket_requires_authentication(self):
        """Test that retrieving a specific ticket requires authentication"""
        ticket_id = "123e4567-e89b-12d3-a456-426614174000"
        
        client = TestClient(app)
        response = client.get(f"/api/v1/tickets/{ticket_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_update_ticket_requires_authentication(self):
        """Test that updating tickets (PUT) requires authentication"""
        ticket_id = "123e4567-e89b-12d3-a456-426614174000"
        update_data = {
            "title": "Updated Title",
            "description": "Updated Description"
        }
        
        client = TestClient(app)
        response = client.put(f"/api/v1/tickets/{ticket_id}", json=update_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_patch_ticket_requires_authentication(self):
        """Test that patching tickets requires authentication"""
        ticket_id = "123e4567-e89b-12d3-a456-426614174000"
        patch_data = {"status": "in_progress"}
        
        client = TestClient(app)
        response = client.patch(f"/api/v1/tickets/{ticket_id}", json=patch_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_delete_ticket_requires_authentication(self):
        """Test that deleting tickets requires authentication"""
        ticket_id = "123e4567-e89b-12d3-a456-426614174000"
        
        client = TestClient(app)
        response = client.delete(f"/api/v1/tickets/{ticket_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_ticket_stats_requires_authentication(self):
        """Test that ticket statistics require authentication"""
        client = TestClient(app)
        response = client.get("/api/v1/tickets/stats/overview")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_all_ticket_endpoints_require_auth(self):
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
        
        # Test requests with appropriate bodies for methods that require them
        test_data = {
            "POST": {"title": "Test", "description": "Test"},
            "PUT": {"title": "Test", "description": "Test"},
            "PATCH": {"status": "in_progress"}
        }
        
        client = TestClient(app)
        for method, endpoint in endpoints_methods:
            json_data = test_data.get(method, None)
            response = client.request(method, endpoint, json=json_data)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
                f"Endpoint {method} {endpoint} should require authentication"
    
    def test_removed_legacy_endpoints_return_404(self):
        """Test that removed legacy endpoints return 404 Not Found"""
        legacy_endpoints = [
            ("PATCH", "/api/v1/tickets/123e4567-e89b-12d3-a456-426614174000/status"),
            ("PATCH", "/api/v1/tickets/123e4567-e89b-12d3-a456-426614174000/assign")
        ]
        
        test_data = {
            "PATCH": {"status": "in_progress", "assigned_to_id": "123e4567-e89b-12d3-a456-426614174000"}
        }
        
        client = TestClient(app)
        for method, endpoint in legacy_endpoints:
            json_data = test_data.get(method, {})
            response = client.request(method, endpoint, json=json_data)
            assert response.status_code == status.HTTP_404_NOT_FOUND, \
                f"Legacy endpoint {method} {endpoint} should return 404 (removed)"
    
    def test_authentication_error_messages(self):
        """Test that authentication error messages are clear and consistent"""
        client = TestClient(app)
        response = client.get("/api/v1/tickets/")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        error_detail = response.json()["detail"]
        assert error_detail is not None
        assert len(error_detail) > 0
        # Should not expose sensitive information
        assert "token" not in error_detail.lower()
        assert "jwt" not in error_detail.lower()
    
    def test_invalid_token_format_rejection(self):
        """Test that invalid token formats are properly rejected"""
        invalid_tokens = [
            "invalid-token",
            "Bearer",
            "Bearer ",
            "Bearer invalid-jwt-token",
            ""
        ]
        
        client = TestClient(app)
        for invalid_token in invalid_tokens:
            headers = {"Authorization": invalid_token} if invalid_token else {}
            response = client.get("/api/v1/tickets/", headers=headers)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
                f"Invalid token '{invalid_token}' should be rejected"
    
    def test_missing_authorization_header(self):
        """Test that requests without Authorization header are rejected"""
        endpoints = [
            "/api/v1/tickets/",
            "/api/v1/tickets/stats/overview"
        ]
        
        client = TestClient(app)
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            # Verify no authorization header leaks sensitive info
            assert "Authorization" not in str(response.headers)