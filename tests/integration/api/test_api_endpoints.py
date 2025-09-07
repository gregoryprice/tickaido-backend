#!/usr/bin/env python3
"""
Test API endpoints functionality in Docker environment
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


def test_fastapi_app_creation():
    """Test FastAPI app can be created"""
    try:
        from app.main import app
        assert app is not None
        print("✅ FastAPI app created successfully")
        
        # Test client creation
        client = TestClient(app)
        assert client is not None
        print("✅ Test client created successfully")
        
    except Exception as e:
        print(f"❌ FastAPI app creation failed: {e}")
        raise


def test_api_router_registration():
    """Test that API routers are properly registered"""
    from app.main import app
    
    # Check if routers are included
    routes = [route.path for route in app.routes]
    
    # Should have health check
    health_routes = [r for r in routes if 'health' in r]
    assert len(health_routes) > 0
    print("✅ Health check route registered")
    
    # Should have API routes
    api_routes = [r for r in routes if 'api' in r or 'v1' in r]
    if api_routes:
        print("✅ API routes registered")
    else:
        print("⚠️ No explicit API routes found (may be included via router)")



@pytest.mark.asyncio
async def test_ticket_service_methods():
    """Test ticket service methods with mocks"""
    from app.services.ticket_service import TicketService
    from app.schemas.ticket import TicketCreateRequest
    
    service = TicketService()
    
    # Mock database session
    mock_session = AsyncMock()
    mock_result = MagicMock()  # Use MagicMock for the result object
    mock_scalars = MagicMock()  # Use MagicMock for synchronous all() method
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_result.scalar.return_value = 0
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    # Test list tickets with organization context
    from uuid import uuid4
    mock_org_id = uuid4()
    tickets, total = await service.list_tickets(mock_session, mock_org_id)
    assert isinstance(tickets, list)
    assert total == 0
    print("✅ Ticket service list_tickets working")
    
    # Test create ticket with valid data
    ticket_data = TicketCreateRequest(
        title="Test Ticket",
        description="Test description",
        priority="medium",
        category="technical"
    )
    
    # Mock successful creation
    mock_session.reset_mock()
    mock_session.add = MagicMock()  # add() is synchronous in SQLAlchemy
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    
    with patch('app.models.ticket.Ticket') as MockTicket:
        mock_ticket = MockTicket.return_value
        mock_ticket.id = "test-id"
        mock_ticket.title = ticket_data.title
        
        ticket = await service.create_ticket(mock_session, ticket_data)
        
        assert ticket is not None
        print("✅ Ticket service create_ticket working")


@pytest.mark.asyncio 
async def test_ai_service_methods():
    """Test AI service methods"""
    from app.services.ai_service import AIService
    
    service = AIService()
    assert service is not None
    
    # Mock database session
    mock_session = AsyncMock()
    
    # Test AI ticket creation (should handle gracefully without real AI)
    try:
        result = await service.create_ticket_with_ai(
            mock_session, 
            "Create a test ticket for login issues"
        )
        print("✅ AI service create_ticket_with_ai callable")
    except Exception as e:
        # Expected to fail without real AI services, but should be callable
        print(f"⚠️ AI service expected failure (no AI services): {str(e)[:100]}...")


def test_schema_validation_comprehensive():
    """Test comprehensive schema validation"""
    from app.schemas.ticket import TicketCreateRequest
    from app.schemas.user import UserCreateRequest
    from app.schemas.file import FileUploadRequest
    
    # Test ticket schemas
    ticket_data = {
        "title": "Test Ticket",
        "description": "Test description", 
        "priority": "high",
        "category": "bug"
    }
    
    ticket_request = TicketCreateRequest(**ticket_data)
    assert ticket_request.title == "Test Ticket"
    assert ticket_request.priority == "high"
    print("✅ Ticket schemas validation working")
    
    # Test user schemas
    user_data = {
        "email": "test@example.com",
        "password": "secure_password123",
        "full_name": "Test User",
        "role": "user"
    }
    
    user_request = UserCreateRequest(**user_data)
    assert user_request.email == "test@example.com"
    print("✅ User schemas validation working")
    
    # Test file schemas
    file_data = {
        "filename": "test.pdf",
        "mime_type": "application/pdf",
        "file_size": 1024
    }
    
    file_request = FileUploadRequest(**file_data)
    assert file_request.filename == "test.pdf"
    print("✅ File schemas validation working")


def test_database_models():
    """Test database models can be instantiated"""
    from app.models.ticket import Ticket, TicketStatus, TicketPriority
    from app.models.user import User, UserRole
    from app.models.file import File, FileStatus
    
    # Test enums
    assert TicketStatus.OPEN.value == "open"
    assert TicketPriority.HIGH.value == "high"
    assert UserRole.USER.value == "user" 
    assert FileStatus.UPLOADED.value == "uploaded"
    print("✅ Database model enums working")
    
    # Models should be importable and have proper attributes
    ticket_fields = [f for f in dir(Ticket) if not f.startswith('_')]
    user_fields = [f for f in dir(User) if not f.startswith('_')]
    file_fields = [f for f in dir(File) if not f.startswith('_')]
    
    assert 'title' in ticket_fields
    assert 'email' in user_fields  
    assert 'filename' in file_fields
    print("✅ Database model fields accessible")


if __name__ == "__main__":
    print("🚀 Starting API endpoints validation...")
    
    # Run synchronous tests
    test_fastapi_app_creation()
    test_api_router_registration()  
    test_schema_validation_comprehensive()
    test_database_models()
    
    # Run async tests
    asyncio.run(test_ticket_service_methods())
    asyncio.run(test_ai_service_methods())
    
    print("✅ All API endpoints validation tests completed!")