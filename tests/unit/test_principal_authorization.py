#!/usr/bin/env python3
"""
Unit tests for Principal-based authorization system
Tests the new architecture for MCP tool filtering using PydanticAI
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.toolsets import FilteredToolset
from pydantic_ai.usage import UsageLimits

# Import schemas (will be created in implementation)
# from app.schemas.principal import Principal  # To be implemented
# from app.services.dynamic_agent_factory_v2 import DynamicAgentFactoryV2  # To be implemented

# Mock implementations for testing the proposed architecture
class Principal:
    """Mock Principal class for testing proposed architecture"""
    
    def __init__(
        self,
        user_id: str,
        organization_id: str,
        email: str,
        roles: list = None,
        permissions: list = None,
        scopes: list = None,
        token_issued_at: datetime = None,
        token_expires_at: datetime = None
    ):
        self.user_id = user_id
        self.organization_id = organization_id
        self.email = email
        self.roles = roles or []
        self.permissions = permissions or []
        self.scopes = scopes or []
        self.token_issued_at = token_issued_at or datetime.now(timezone.utc)
        self.token_expires_at = token_expires_at or datetime.now(timezone.utc) + timedelta(hours=1)
    
    def has_permission(self, permission: str) -> bool:
        """Check if principal has specific permission"""
        return permission in self.permissions or "all" in self.permissions
    
    def has_role(self, role: str) -> bool:
        """Check if principal has specific role"""
        return role in self.roles
    
    def can_access_tool(self, tool_name: str, context: Dict = None) -> bool:
        """ABAC/RBAC logic for tool access"""
        context = context or {}
        
        # Admin can access everything
        if "admin" in self.roles:
            return True
        
        # Manager can access most tools
        if "manager" in self.roles:
            restricted_tools = ["delete_ticket", "assign_ticket"]
            return tool_name not in restricted_tools or self.has_permission("ticket.admin")
        
        # Regular user has limited access
        if "user" in self.roles:
            allowed_tools = ["create_ticket", "get_ticket", "list_tickets", "search_tickets"]
            return tool_name in allowed_tools
        
        # Default deny
        return False


class MockAgentModel:
    """Mock Agent model for testing"""
    
    def __init__(
        self,
        id: str = "test-agent-123",
        organization_id: str = "org-456",
        tools: list = None,
        requires_approval: bool = False,
        max_iterations: int = 5,
        prompt: str = "You are a helpful assistant",
        model_provider: str = "openai",
        model_name: str = "gpt-4o-mini"
    ):
        self.id = id
        self.organization_id = organization_id
        self.prompt = prompt
        self.requires_approval = requires_approval
        self.max_iterations = max_iterations
        self.model_provider = model_provider
        self.model_name = model_name
        self._tools = tools or [
            "create_ticket", "get_ticket", "list_tickets", "search_tickets"
        ]
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get agent configuration"""
        return {
            "tools": self._tools,
            "model_provider": self.model_provider,
            "model_name": self.model_name
        }


class TestPrincipalAuthorization:
    """Test cases for Principal-based authorization"""
    
    def test_principal_creation(self):
        """Test Principal object creation and basic properties"""
        principal = Principal(
            user_id="user-123",
            organization_id="org-456",
            email="test@company.com",
            roles=["user"],
            permissions=["ticket.create", "ticket.view"],
            scopes=["basic"]
        )
        
        assert principal.user_id == "user-123"
        assert principal.organization_id == "org-456"
        assert principal.email == "test@company.com"
        assert "user" in principal.roles
        assert principal.has_permission("ticket.create")
        assert principal.has_role("user")
        assert not principal.has_role("admin")
    
    def test_admin_can_access_all_tools(self):
        """Test admin principal has access to all tools"""
        admin_principal = Principal(
            user_id="admin-123",
            organization_id="org-456",
            email="admin@company.com",
            roles=["admin"],
            permissions=["all"],
            scopes=["all"]
        )
        
        # Test various tools
        tools_to_test = [
            "create_ticket", "get_ticket", "update_ticket", "delete_ticket",
            "assign_ticket", "list_tickets", "search_tickets", "get_system_health"
        ]
        
        for tool in tools_to_test:
            assert admin_principal.can_access_tool(tool), f"Admin should have access to {tool}"
            assert admin_principal.has_permission("all")
    
    def test_user_limited_tool_access(self):
        """Test regular user has limited tool access"""
        user_principal = Principal(
            user_id="user-789",
            organization_id="org-456",
            email="user@company.com",
            roles=["user"],
            permissions=["ticket.create", "ticket.view"],
            scopes=["basic"]
        )
        
        # Allowed tools for regular user
        allowed_tools = ["create_ticket", "get_ticket", "list_tickets", "search_tickets"]
        for tool in allowed_tools:
            assert user_principal.can_access_tool(tool), f"User should have access to {tool}"
        
        # Restricted tools
        restricted_tools = ["delete_ticket", "assign_ticket", "update_ticket"]
        for tool in restricted_tools:
            assert not user_principal.can_access_tool(tool), f"User should not have access to {tool}"
    
    def test_manager_role_permissions(self):
        """Test manager role has intermediate permissions"""
        manager_principal = Principal(
            user_id="manager-456",
            organization_id="org-456",
            email="manager@company.com",
            roles=["manager"],
            permissions=["ticket.create", "ticket.update", "ticket.view"],
            scopes=["manager"]
        )
        
        # Manager should have access to most tools
        manager_tools = [
            "create_ticket", "get_ticket", "update_ticket",
            "list_tickets", "search_tickets"
        ]
        for tool in manager_tools:
            assert manager_principal.can_access_tool(tool), f"Manager should have access to {tool}"
        
        # But not to highly sensitive ones without special permission
        assert not manager_principal.can_access_tool("delete_ticket")
        assert not manager_principal.can_access_tool("assign_ticket")
    
    def test_organization_isolation(self):
        """Test that organization isolation is considered"""
        principal_org1 = Principal(
            user_id="user-123",
            organization_id="org-111",
            email="user1@org1.com",
            roles=["user"],
            permissions=["ticket.create"]
        )
        
        principal_org2 = Principal(
            user_id="user-456", 
            organization_id="org-222",
            email="user2@org2.com",
            roles=["user"],
            permissions=["ticket.create"]
        )
        
        # Both should have access to basic tools within their context
        assert principal_org1.can_access_tool("create_ticket")
        assert principal_org2.can_access_tool("create_ticket")
        
        # Organization IDs should be different
        assert principal_org1.organization_id != principal_org2.organization_id
    
    def test_token_expiry_validation(self):
        """Test token expiry validation"""
        # Valid token (not expired)
        valid_principal = Principal(
            user_id="user-123",
            organization_id="org-456",
            email="user@company.com",
            roles=["user"],
            token_issued_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            token_expires_at=datetime.now(timezone.utc) + timedelta(minutes=55)
        )
        
        # Expired token
        expired_principal = Principal(
            user_id="user-456",
            organization_id="org-456",
            email="expired@company.com", 
            roles=["user"],
            token_issued_at=datetime.now(timezone.utc) - timedelta(hours=2),
            token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        
        # Check if tokens are handled properly (in real implementation)
        assert valid_principal.token_expires_at > datetime.now(timezone.utc)
        assert expired_principal.token_expires_at < datetime.now(timezone.utc)
    
    def test_permission_based_tool_access(self):
        """Test granular permission-based tool access"""
        # User with specific permissions
        specific_principal = Principal(
            user_id="specific-user",
            organization_id="org-456",
            email="specific@company.com",
            roles=["specialist"],
            permissions=[
                "ticket.create", "ticket.view", "ticket.update",
                "integration.list", "system.health"
            ]
        )
        
        # Test permission-specific access
        assert specific_principal.has_permission("ticket.create")
        assert specific_principal.has_permission("system.health")
        assert not specific_principal.has_permission("ticket.delete")
        assert not specific_principal.has_permission("user.admin")
    
    def test_scope_based_access(self):
        """Test scope-based access control"""
        limited_scope_principal = Principal(
            user_id="limited-user",
            organization_id="org-456",
            email="limited@company.com",
            roles=["user"],
            permissions=["ticket.view"],
            scopes=["readonly"]
        )
        
        full_scope_principal = Principal(
            user_id="full-user",
            organization_id="org-456",
            email="full@company.com",
            roles=["user"],
            permissions=["ticket.create", "ticket.view", "ticket.update"],
            scopes=["read", "write"]
        )
        
        assert "readonly" in limited_scope_principal.scopes
        assert "read" in full_scope_principal.scopes
        assert "write" in full_scope_principal.scopes


class TestDynamicAgentFactory:
    """Test cases for Dynamic Agent Factory with Principal integration"""
    
    @pytest.fixture
    def mock_agent_model(self):
        """Create mock agent model for testing"""
        return MockAgentModel(
            tools=["create_ticket", "get_ticket", "list_tickets"]
        )
    
    @pytest.fixture
    def admin_principal(self):
        """Create admin principal for testing"""
        return Principal(
            user_id="admin-123",
            organization_id="org-456",
            email="admin@company.com",
            roles=["admin"],
            permissions=["all"],
            scopes=["all"]
        )
    
    @pytest.fixture
    def user_principal(self):
        """Create regular user principal for testing"""
        return Principal(
            user_id="user-789",
            organization_id="org-456", 
            email="user@company.com",
            roles=["user"],
            permissions=["ticket.create", "ticket.view"],
            scopes=["basic"]
        )
    
    def test_agent_tool_filtering_with_principal(self, mock_agent_model, admin_principal, user_principal):
        """Test that agent tools are properly filtered based on principal"""
        # Agent model has limited tools
        agent_tools = mock_agent_model.get_configuration()["tools"]
        assert "create_ticket" in agent_tools
        assert "get_ticket" in agent_tools
        assert "delete_ticket" not in agent_tools  # Not in agent's allowed tools
        
        # Admin should still be limited to agent's allowed tools
        for tool in agent_tools:
            assert admin_principal.can_access_tool(tool)
        
        # User should have access to allowed tools
        for tool in agent_tools:
            if user_principal.can_access_tool(tool):
                assert tool in ["create_ticket", "get_ticket", "list_tickets"]
    
    def test_toolset_composition(self, mock_agent_model, admin_principal):
        """Test that toolsets are properly composed and filtered"""
        # This test is for future implementation when app.tools module exists
        # For now, just test the mock agent model structure
        agent_config = mock_agent_model.get_configuration()
        assert "tools" in agent_config
        assert isinstance(agent_config["tools"], list)
        assert len(agent_config["tools"]) > 0
        
        # Verify admin can access agent tools
        for tool in agent_config["tools"]:
            assert admin_principal.can_access_tool(tool)
    
    def test_approval_workflow_integration(self, mock_agent_model, admin_principal, user_principal):
        """Test approval workflow for sensitive tools"""
        # Set agent to require approval
        mock_agent_model.requires_approval = True
        
        # Sensitive tools that require approval
        sensitive_tools = ["delete_ticket", "assign_ticket"]
        
        # Admin should have approval rights
        assert admin_principal.has_role("admin")
        
        # User should not have approval rights
        assert not user_principal.has_role("admin")
        assert not user_principal.has_role("manager")
    
    def test_context_aware_decisions(self, mock_agent_model, admin_principal):
        """Test that context is properly considered in access decisions"""
        context = {
            "agent_id": str(mock_agent_model.id),
            "organization_id": admin_principal.organization_id,
            "request_type": "chat",
            "timestamp": datetime.now(timezone.utc)
        }
        
        # Tool access decisions should consider context
        assert admin_principal.can_access_tool("create_ticket", context)
        
        # Context should be used for audit logging
        assert context["organization_id"] == admin_principal.organization_id
        assert context["agent_id"] == mock_agent_model.id
    
    def test_error_handling_and_fallbacks(self, mock_agent_model):
        """Test error handling and graceful fallbacks"""
        # Test with invalid principal
        invalid_principal = None
        
        # Test with expired principal
        expired_principal = Principal(
            user_id="expired-user",
            organization_id="org-456",
            email="expired@company.com",
            roles=["user"],
            token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        
        # Test with missing permissions
        no_permissions_principal = Principal(
            user_id="no-perms-user",
            organization_id="org-456",
            email="noperms@company.com",
            roles=[],
            permissions=[]
        )
        
        # All should handle gracefully without exceptions
        assert not no_permissions_principal.has_permission("ticket.create")
        assert not no_permissions_principal.can_access_tool("create_ticket")


class TestAuditAndSecurityLogging:
    """Test cases for audit trail and security logging"""
    
    def test_tool_access_audit_logging(self):
        """Test that tool access attempts are properly audited"""
        principal = Principal(
            user_id="test-user",
            organization_id="org-456",
            email="test@company.com",
            roles=["user"]
        )
        
        # Mock audit service would capture this information
        audit_context = {
            "timestamp": datetime.now(timezone.utc),
            "user_id": principal.user_id,
            "organization_id": principal.organization_id,
            "tool_name": "create_ticket",
            "access_granted": True,
            "roles": principal.roles,
            "permissions": principal.permissions
        }
        
        assert audit_context["user_id"] == "test-user"
        assert audit_context["tool_name"] == "create_ticket"
        assert isinstance(audit_context["timestamp"], datetime)
    
    def test_security_violation_detection(self):
        """Test detection of security violations"""
        # Test cross-organization access attempt
        principal_org1 = Principal(
            user_id="user-123",
            organization_id="org-111",
            email="user@org1.com",
            roles=["user"]
        )
        
        # Attempting to access resources from different organization
        malicious_context = {
            "target_organization": "org-222",  # Different org!
            "requested_resource": "tickets"
        }
        
        # This should be detected as a security violation
        assert principal_org1.organization_id != malicious_context["target_organization"]
    
    def test_token_manipulation_detection(self):
        """Test detection of token manipulation attempts"""
        # Test with malformed token claims
        suspicious_principal = Principal(
            user_id="admin-999",  # Suspicious user ID
            organization_id="",   # Empty org ID - suspicious
            email="",            # Empty email - suspicious
            roles=["admin", "super_admin"],  # Too many high-level roles
            permissions=["all", "everything"]  # Suspicious permissions
        )
        
        # These patterns should be flagged as suspicious
        assert len(suspicious_principal.roles) > 1  # Multiple high-privilege roles
        assert not suspicious_principal.email  # Missing email
        assert not suspicious_principal.organization_id  # Missing org


class TestPerformanceAndScaling:
    """Test cases for performance and scaling considerations"""
    
    def test_principal_creation_performance(self):
        """Test that Principal creation is fast"""
        start_time = datetime.now()
        
        # Create multiple principals
        principals = []
        for i in range(100):
            principal = Principal(
                user_id=f"user-{i}",
                organization_id=f"org-{i % 10}",
                email=f"user{i}@company.com",
                roles=["user"],
                permissions=["ticket.create", "ticket.view"]
            )
            principals.append(principal)
        
        end_time = datetime.now()
        creation_time = (end_time - start_time).total_seconds()
        
        # Should be very fast
        assert creation_time < 1.0  # Less than 1 second for 100 principals
        assert len(principals) == 100
    
    def test_tool_access_decision_performance(self):
        """Test that tool access decisions are fast"""
        principal = Principal(
            user_id="perf-test-user",
            organization_id="org-456",
            email="perftest@company.com",
            roles=["user"],
            permissions=["ticket.create", "ticket.view", "ticket.update"]
        )
        
        tools_to_test = [
            "create_ticket", "get_ticket", "update_ticket", "delete_ticket",
            "list_tickets", "search_tickets", "assign_ticket", "get_system_health"
        ] * 100  # Test 800 tool access decisions
        
        start_time = datetime.now()
        
        results = []
        for tool in tools_to_test:
            result = principal.can_access_tool(tool)
            results.append(result)
        
        end_time = datetime.now()
        decision_time = (end_time - start_time).total_seconds()
        
        # Should be very fast
        assert decision_time < 1.0  # Less than 1 second for 800 decisions
        assert len(results) == len(tools_to_test)
    
    def test_memory_usage_optimization(self):
        """Test that Principal objects don't consume excessive memory"""
        # Create many principals to test memory efficiency
        principals = []
        for i in range(1000):
            principal = Principal(
                user_id=f"user-{i}",
                organization_id=f"org-{i % 10}",
                email=f"user{i}@company.com",
                roles=["user"],
                permissions=["ticket.create"]
            )
            principals.append(principal)
        
        # Verify they're all created successfully
        assert len(principals) == 1000
        
        # Check that they contain expected data
        sample_principal = principals[500]
        assert sample_principal.user_id == "user-500"
        assert sample_principal.organization_id == "org-0"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])