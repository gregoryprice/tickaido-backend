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
        from app.models.user import DBUser, UserRole
        from app.models.ticket import DBTicket, TicketStatus
        from app.models.file import DBFile, FileStatus
        from app.models.integration import DBIntegration, IntegrationType
        from app.models.ai_agent_config import DBAIAgentConfig, AIAgentType
        
        assert BaseModel is not None
        assert DBUser is not None
        assert UserRole is not None
        assert DBTicket is not None
        assert TicketStatus is not None
        print("✅ All model imports successful")
    except Exception as e:
        pytest.fail(f"❌ Model import failed: {e}")

def test_schemas_import():
    """Test that we can import schemas"""
    try:
        from app.schemas.user import UserCreateRequest, UserListResponse
        from app.schemas.ticket import TicketCreateRequest, TicketDetailResponse
        from app.schemas.file import FileUploadRequest, FileListResponse
        from app.schemas.integration import IntegrationCreateRequest, IntegrationListResponse
        from app.schemas.ai_config import AIAgentConfigCreateRequest, AIAgentConfigListResponse
        
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
    """Test that we can import AI agents"""
    try:
        from app.agents.customer_support_agent import customer_support_agent, CustomerSupportContext
        from app.agents.categorization_agent import categorization_agent, CategorizationContext
        
        assert customer_support_agent is not None
        assert categorization_agent is not None
        assert CustomerSupportContext is not None
        assert CategorizationContext is not None
        print("✅ All AI agent imports successful")
    except Exception as e:
        pytest.fail(f"❌ AI agent import failed: {e}")

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
        from app.models.ticket import TicketStatus, TicketPriority, TicketCategory
        from app.models.file import FileStatus, FileType
        
        # Test UserRole values
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.USER.value == "user"
        
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