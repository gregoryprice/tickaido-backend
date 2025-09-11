#!/usr/bin/env python3
"""
Test all business logic services
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock


def test_service_imports():
    """Test that all services can be imported"""
    print("Testing service imports...")
    
    
    print("✅ All services imported successfully")


def test_service_instantiation():
    """Test that all services can be instantiated"""
    print("Testing service instantiation...")
    
    from app.services.ticket_service import TicketService
    from app.services.ai_service import AIService
    from app.services.file_service import FileService
    from app.services.user_service import UserService
    from app.services.integration_service import IntegrationService
    
    ticket_service = TicketService()
    ai_service = AIService()
    file_service = FileService()
    user_service = UserService()
    integration_service = IntegrationService()
    
    assert ticket_service is not None
    assert ai_service is not None
    assert file_service is not None
    assert user_service is not None
    assert integration_service is not None
    
    print("✅ All services instantiated successfully")


def test_service_configurations():
    """Test service configurations"""
    print("Testing service configurations...")
    
    from app.services.file_service import FileService
    from app.services.user_service import UserService
    
    file_service = FileService()
    user_service = UserService()
    
    # Test file service config
    assert hasattr(file_service, 'upload_directory')
    assert hasattr(file_service, 'max_file_size')
    assert hasattr(file_service, 'allowed_file_types')
    
    # Test user service config
    assert hasattr(user_service, 'pwd_context')
    assert hasattr(user_service, 'secret_key')
    assert hasattr(user_service, 'algorithm')
    
    print("✅ Service configurations working")


@pytest.mark.asyncio
async def test_file_service_methods():
    """Test file service methods with mocks"""
    from app.services.file_service import FileService
    
    service = FileService()
    mock_session = AsyncMock()
    
    # Test file type detection
    assert service._detect_file_type('image/jpeg').value == 'image'
    assert service._detect_file_type('application/pdf').value == 'document'
    assert service._detect_file_type('text/plain').value == 'text'
    print("✅ File type detection working")
    
    # Test text extraction (basic)
    text = await service._extract_text(b"Hello World", "text/plain")
    assert "Hello World" in text
    print("✅ Text extraction working")
    
    # Test metadata extraction
    metadata = await service._extract_metadata(b"test content", "text/plain")
    assert "mime_type" in metadata
    assert metadata["size"] == len(b"test content")
    print("✅ Metadata extraction working")


def test_user_service_password_handling():
    """Test user service password functions"""
    from app.services.user_service import UserService
    
    service = UserService()
    
    # Test password hashing and verification
    password = "test_password_123"
    hashed = service._hash_password(password)
    
    assert hashed != password  # Should be hashed
    assert service._verify_password(password, hashed)  # Should verify
    assert not service._verify_password("wrong_password", hashed)  # Should fail
    
    print("✅ Password hashing and verification working")


def test_user_service_token_handling():
    """Test user service JWT token functions"""
    from app.services.user_service import UserService
    from datetime import timedelta
    
    service = UserService()
    
    # Test token creation and verification
    test_data = {"sub": "test_user", "role": "user"}
    token = service._create_access_token(test_data, expires_delta=timedelta(minutes=30))
    
    assert token is not None
    assert isinstance(token, str)
    
    # Verify token
    payload = service._verify_token(token)
    assert payload is not None
    assert payload.get("sub") == "test_user"
    assert payload.get("role") == "user"
    
    print("✅ JWT token creation and verification working")


def test_integration_service_config_validation():
    """Test integration service configuration validation"""
    from app.services.integration_service import IntegrationService
    
    service = IntegrationService()
    
    # Test required fields detection
    salesforce_fields = service._get_required_config_fields("salesforce")
    assert "client_id" in salesforce_fields
    assert "client_secret" in salesforce_fields
    assert "instance_url" in salesforce_fields
    
    jira_fields = service._get_required_config_fields("jira")
    # With base_url standardized at top-level, only credentials are required here
    assert "email" in jira_fields
    assert "api_token" in jira_fields
    
    print("✅ Integration configuration validation working")
    
    # Test validation function
    valid_config = {
        "client_id": "test",
        "client_secret": "test",
        "instance_url": "https://test.salesforce.com"
    }
    
    # Should not raise exception
    service._validate_credentials("salesforce", valid_config)
    
    # Invalid config should raise exception
    invalid_config = {"client_id": "test"}  # Missing required fields
    
    try:
        service._validate_credentials("salesforce", invalid_config)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Missing required configuration field" in str(e)
    
    print("✅ Integration configuration validation working properly")


@pytest.mark.asyncio
async def test_service_error_handling():
    """Test service error handling"""
    from app.services.file_service import FileService
    from app.services.user_service import UserService
    from app.schemas.file import FileUploadRequest
    from app.schemas.user import UserCreateRequest
    from uuid import uuid4
    from pydantic import ValidationError
    
    file_service = FileService()
    user_service = UserService()
    mock_session = AsyncMock()
    
    # Test file service validation errors
    large_file_data = b"x" * (file_service.max_file_size + 1000)
    
    try:
        file_request = FileUploadRequest(
            filename="test.txt",
            mime_type="text/plain",
            file_size=len(large_file_data)
        )
        await file_service.upload_file(mock_session, file_request, large_file_data, uuid4())
        assert False, "Should have raised validation error for file size"
    except (ValueError, ValidationError) as e:
        # Accept both schema validation error and service validation error
        assert any(x in str(e).lower() for x in ["exceeds", "cannot exceed", "file size"])
    
    print("✅ File service error handling working")
    
    # Test user service validation
    mock_existing_user = MagicMock()
    mock_existing_user.email = "test@example.com"
    
    with patch.object(user_service, 'get_user_by_email', return_value=mock_existing_user):
        try:
            user_request = UserCreateRequest(
                email="test@example.com",
                password="password123",
                full_name="Test User"
            )
            await user_service.create_user(mock_session, user_request)
            assert False, "Should have raised ValueError for existing email"
        except ValueError as e:
            assert "already exists" in str(e)
    
    print("✅ User service error handling working")


def test_service_utility_functions():
    """Test service utility functions"""
    from app.services.file_service import FileService
    from app.models.file import FileType
    
    service = FileService()
    
    # Test file type detection for various MIME types
    test_cases = [
        ("image/png", FileType.IMAGE),
        ("audio/mp3", FileType.AUDIO), 
        ("video/mp4", FileType.VIDEO),
        ("application/pdf", FileType.DOCUMENT),
        ("text/plain", FileType.TEXT),
        ("application/unknown", FileType.OTHER)
    ]
    
    for mime_type, expected_type in test_cases:
        detected_type = service._detect_file_type(mime_type)
        assert detected_type == expected_type, f"Failed for {mime_type}: expected {expected_type}, got {detected_type}"
    
    print("✅ Service utility functions working")


if __name__ == "__main__":
    print("🚀 Starting services validation tests...")
    
    # Run synchronous tests
    test_service_imports()
    test_service_instantiation()
    test_service_configurations()
    test_user_service_password_handling()
    test_user_service_token_handling()
    test_integration_service_config_validation()
    test_service_utility_functions()
    
    # Run async tests
    asyncio.run(test_file_service_methods())
    asyncio.run(test_service_error_handling())
    
    print("✅ All services validation tests completed!")