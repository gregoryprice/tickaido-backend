#!/usr/bin/env python3
"""
Basic API tests to validate implementation
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Let's test the basic imports and app creation first
def test_basic_imports():
    """Test that we can import the main components"""
    try:
        from app.main import app
        from app.api.v1.tickets import router
        from app.services.ticket_service import ticket_service
        from app.services.ai_service import ai_service
        from app.models.ticket import DBTicket
        from app.schemas.ticket import TicketCreateRequest
        assert app is not None
        assert router is not None
        assert ticket_service is not None
        assert ai_service is not None
        print("✅ All basic imports successful")
    except Exception as e:
        pytest.fail(f"❌ Import failed: {e}")

def test_app_creation():
    """Test that FastAPI app can be created"""
    try:
        from app.main import app
        client = TestClient(app)
        
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        assert "AI Ticket Creator Backend API" in response.text
        print("✅ App creation and root endpoint test successful")
    except Exception as e:
        pytest.fail(f"❌ App creation failed: {e}")

def test_health_endpoint():
    """Test health check endpoint"""
    try:
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/health")
        # Health endpoint might fail due to database connection, but should at least return JSON
        assert response.headers.get("content-type", "").startswith("application/json")
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        print("✅ Health endpoint test successful")
    except Exception as e:
        pytest.fail(f"❌ Health endpoint failed: {e}")

def test_api_documentation():
    """Test that API documentation is available"""
    try:
        from app.main import app
        client = TestClient(app)
        
        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("application/json")
        
        schema = response.json()
        assert "info" in schema
        assert "paths" in schema
        assert schema["info"]["title"] == "AI Ticket Creator Backend API"
        print("✅ API documentation test successful")
    except Exception as e:
        pytest.fail(f"❌ API documentation failed: {e}")

def test_tickets_endpoint_structure():
    """Test tickets endpoint is properly registered"""
    try:
        from app.main import app
        client = TestClient(app)
        
        # Get OpenAPI schema to check if tickets endpoints are registered
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        paths = schema.get("paths", {})
        
        # Check if tickets endpoints are registered
        ticket_paths = [path for path in paths.keys() if "/tickets" in path]
        assert len(ticket_paths) > 0, "No ticket endpoints found in OpenAPI schema"
        
        print(f"✅ Found {len(ticket_paths)} ticket endpoints:")
        for path in ticket_paths:
            print(f"   - {path}")
            
    except Exception as e:
        pytest.fail(f"❌ Tickets endpoint structure test failed: {e}")

if __name__ == "__main__":
    print("🧪 Running basic API tests...")
    test_basic_imports()
    test_app_creation()
    test_health_endpoint()
    test_api_documentation() 
    test_tickets_endpoint_structure()
    print("🎉 All basic tests passed!")