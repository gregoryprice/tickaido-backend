#!/usr/bin/env python3
"""
Simple tests to validate basic functionality without database
"""

import os
import pytest

# Set minimal environment variables for testing
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://test:test@localhost:5432/test'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'

def test_models_import():
    """Test that we can import database models"""
    try:
        from app.models.base import BaseModel
        from app.models.user import User, UserRole
        from app.models.ticket import Ticket, TicketStatus
        
        assert BaseModel is not None
        assert User is not None
        assert UserRole is not None
        assert Ticket is not None
        assert TicketStatus is not None
        print("✅ All model imports successful")
    except Exception as e:
        pytest.fail(f"❌ Model import failed: {e}")

def test_schemas_import():
    """Test that we can import schemas"""
    try:
        from app.schemas.user import UserCreateRequest
        from app.schemas.ticket import TicketCreateRequest
        from app.schemas.file import FileUploadRequest
        
        assert UserCreateRequest is not None
        assert TicketCreateRequest is not None
        assert FileUploadRequest is not None
        print("✅ All schema imports successful")
    except Exception as e:
        pytest.fail(f"❌ Schema import failed: {e}")

def test_services_import():
    """Test that we can import services"""
    try:
        from app.services.ticket_service import ticket_service
        from app.services.ai_service import ai_service
        
        assert ticket_service is not None
        assert ai_service is not None
        print("✅ All service imports successful")
    except Exception as e:
        pytest.fail(f"❌ Service import failed: {e}")

def test_agents_import():
    """Test that we can import AI agents and new dynamic agent architecture"""
    try:
        # Test new dynamic agent components
        from app.services.dynamic_agent_factory import dynamic_agent_factory
        from app.services.agent_task_service import agent_task_service
        from app.agents.categorization_agent import categorization_agent, CategorizationContext
        from app.schemas.ai_response import CustomerSupportContext
        from mcp_client.client import mcp_client
        
        # Test that components exist
        assert dynamic_agent_factory is not None
        assert agent_task_service is not None
        assert categorization_agent is not None
        assert CustomerSupportContext is not None
        assert CategorizationContext is not None
        assert mcp_client is not None
        
        print("✅ All AI agent components import successfully (new dynamic agent architecture)")
    except Exception as e:
        pytest.fail(f"❌ AI agent component import failed: {e}")

def test_fastapi_app_import():
    """Test that we can import the FastAPI app (without starting it)"""
    try:
        from app.main import app
        
        # Check that it's a FastAPI instance
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)
        assert app.title == "AI Ticket Creator Backend API"
        print("✅ FastAPI app import successful")
    except Exception as e:
        pytest.fail(f"❌ FastAPI app import failed: {e}")

def test_enum_values():
    """Test that enums have expected values"""
    try:
        from app.models.user import UserRole
        from app.models.ticket import TicketStatus, TicketPriority
        
        # Test UserRole values
        assert UserRole.ADMIN.value == "ADMIN"
        assert UserRole.MEMBER.value == "MEMBER"
        
        # Test TicketStatus values
        assert TicketStatus.NEW.value == "new"
        assert TicketStatus.RESOLVED.value == "resolved"
        
        # Test TicketPriority values
        assert TicketPriority.LOW.value == "low"
        assert TicketPriority.CRITICAL.value == "critical"
        
        print("✅ All enum values correct")
    except Exception as e:
        pytest.fail(f"❌ Enum values test failed: {e}")

def test_schema_validation():
    """Test that schemas can be instantiated"""
    try:
        from app.schemas.ticket import TicketCreateRequest
        from app.schemas.user import UserCreateRequest
        
        # Test ticket schema
        ticket_data = {
            "title": "Test ticket",
            "description": "Test description",
            "category": "technical",
            "priority": "medium"
        }
        ticket_schema = TicketCreateRequest(**ticket_data)
        assert ticket_schema.title == "Test ticket"
        
        # Test user schema
        user_data = {
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "test123456"  # Must be at least 8 characters
        }
        user_schema = UserCreateRequest(**user_data)
        assert user_schema.email == "test@example.com"
        
        print("✅ Schema validation successful")
    except Exception as e:
        pytest.fail(f"❌ Schema validation failed: {e}")

if __name__ == "__main__":
    print("🧪 Running simple tests...")
    test_models_import()
    test_schemas_import()
    test_services_import()
    test_agents_import()
    test_fastapi_app_import()
    test_enum_values()
    test_schema_validation()
    print("🎉 All simple tests passed!")