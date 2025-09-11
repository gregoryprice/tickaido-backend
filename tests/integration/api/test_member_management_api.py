#!/usr/bin/env python3
"""
API Integration tests for Member Management endpoints
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User
from app.models.organization import Organization
from app.models.organization_invitation import (
    OrganizationInvitation,
    OrganizationRole,
    InvitationStatus
)


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
async def test_organization(async_db: AsyncSession):
    """Create test organization"""
    org = Organization(
        name="Test Organization",
        domain="test.com",
        is_enabled=True
    )
    async_db.add(org)
    await async_db.commit()
    await async_db.refresh(org)
    return org


@pytest.fixture
async def test_admin_user(async_db: AsyncSession, test_organization: Organization):
    """Create test admin user"""
    admin = User(
        email="admin@test.com",
        password_hash="hashed_password",
        full_name="Admin User",
        organization_id=test_organization.id,
        organization_role=OrganizationRole.ADMIN,
        is_active=True,
        is_verified=True
    )
    async_db.add(admin)
    await async_db.commit()
    await async_db.refresh(admin)
    return admin


@pytest.fixture
async def test_member_user(async_db: AsyncSession, test_organization: Organization):
    """Create test member user"""
    member = User(
        email="member@test.com",
        password_hash="hashed_password",
        full_name="Member User",
        organization_id=test_organization.id,
        organization_role=OrganizationRole.MEMBER,
        is_active=True,
        is_verified=True
    )
    async_db.add(member)
    await async_db.commit()
    await async_db.refresh(member)
    return member


@pytest.fixture
def admin_headers(test_admin_user: User):
    """Create auth headers for admin user"""
    # This would need to be implemented with actual JWT token generation
    # For now, we'll simulate authentication
    return {"Authorization": f"Bearer admin-token-{test_admin_user.id}"}


@pytest.fixture
def member_headers(test_member_user: User):
    """Create auth headers for member user"""
    return {"Authorization": f"Bearer member-token-{test_member_user.id}"}


class TestMemberListEndpoint:
    """Test GET /organizations/{org_id}/members endpoint"""
    
    def test_list_members_as_admin(
        self,
        client: TestClient,
        test_organization: Organization,
        test_admin_user: User,
        test_member_user: User,
        admin_headers: dict
    ):
        """Test listing organization members as admin"""
        
        response = client.get(
            f"/api/v1/organizations/{test_organization.id}/members",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return both admin and member
        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["total"] == 2
        
        # Verify member data structure
        members = data["data"]
        emails = [member["email"] for member in members]
        assert "admin@test.com" in emails
        assert "member@test.com" in emails
    
    def test_list_members_with_role_filter(
        self,
        client: TestClient,
        test_organization: Organization,
        admin_headers: dict
    ):
        """Test listing members with role filter"""
        
        response = client.get(
            f"/api/v1/organizations/{test_organization.id}/members?role=admin",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only return admin users
        members = data["data"]
        for member in members:
            assert member["organization_role"] == "admin"
    
    def test_list_members_pagination(
        self,
        client: TestClient,
        test_organization: Organization,
        admin_headers: dict
    ):
        """Test member listing pagination"""
        
        response = client.get(
            f"/api/v1/organizations/{test_organization.id}/members?page=1&limit=1",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return only 1 member
        assert len(data["data"]) <= 1
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 1
    
    def test_list_members_unauthorized_cross_org(
        self,
        client: TestClient,
        admin_headers: dict
    ):
        """Test unauthorized access to another organization's members"""
        
        other_org_id = uuid4()
        
        response = client.get(
            f"/api/v1/organizations/{other_org_id}/members",
            headers=admin_headers
        )
        
        assert response.status_code == 403
        assert "own organization" in response.json()["detail"]
    
    def test_list_members_no_auth(
        self,
        client: TestClient,
        test_organization: Organization
    ):
        """Test listing members without authentication"""
        
        response = client.get(
            f"/api/v1/organizations/{test_organization.id}/members"
        )
        
        assert response.status_code == 401


class TestMemberInviteEndpoint:
    """Test POST /organizations/{org_id}/members/invite endpoint"""
    
    def test_invite_member_as_admin(
        self,
        client: TestClient,
        test_organization: Organization,
        admin_headers: dict
    ):
        """Test inviting member as admin"""
        
        invite_data = {
            "email": "newmember@test.com",
            "role": "member",
            "send_email": True,
            "message": "Welcome to our team!"
        }
        
        response = client.post(
            f"/api/v1/organizations/{test_organization.id}/members/invite",
            json=invite_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == "newmember@test.com"
        assert data["role"] == "member"
        assert "invitation_id" in data
        assert "invitation_url" in data
        assert "expires_at" in data
    
    def test_invite_member_as_non_admin(
        self,
        client: TestClient,
        test_organization: Organization,
        member_headers: dict
    ):
        """Test inviting member as non-admin (should fail)"""
        
        invite_data = {
            "email": "newmember@test.com",
            "role": "member"
        }
        
        response = client.post(
            f"/api/v1/organizations/{test_organization.id}/members/invite",
            json=invite_data,
            headers=member_headers
        )
        
        assert response.status_code == 403
    
    def test_invite_member_invalid_email(
        self,
        client: TestClient,
        test_organization: Organization,
        admin_headers: dict
    ):
        """Test inviting with invalid email"""
        
        invite_data = {
            "email": "invalid-email",
            "role": "member"
        }
        
        response = client.post(
            f"/api/v1/organizations/{test_organization.id}/members/invite",
            json=invite_data,
            headers=admin_headers
        )
        
        assert response.status_code == 400
    
    def test_invite_duplicate_email(
        self,
        client: TestClient,
        test_organization: Organization,
        test_member_user: User,
        admin_headers: dict
    ):
        """Test inviting existing member"""
        
        invite_data = {
            "email": test_member_user.email,
            "role": "member"
        }
        
        response = client.post(
            f"/api/v1/organizations/{test_organization.id}/members/invite",
            json=invite_data,
            headers=admin_headers
        )
        
        assert response.status_code == 400
        assert "already a member" in response.json()["detail"]


class TestMemberRoleUpdateEndpoint:
    """Test PUT /organizations/{org_id}/members/{user_id}/role endpoint"""
    
    def test_update_member_role_as_admin(
        self,
        client: TestClient,
        test_organization: Organization,
        test_member_user: User,
        admin_headers: dict
    ):
        """Test updating member role as admin"""
        
        role_data = {
            "organization_role": "admin"
        }
        
        response = client.put(
            f"/api/v1/organizations/{test_organization.id}/members/{test_member_user.id}/role",
            json=role_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        assert "role updated successfully" in response.json()["message"]
    
    def test_update_own_role_prevention(
        self,
        client: TestClient,
        test_organization: Organization,
        test_admin_user: User,
        admin_headers: dict
    ):
        """Test prevention of self-role modification"""
        
        role_data = {
            "organization_role": "member"
        }
        
        response = client.put(
            f"/api/v1/organizations/{test_organization.id}/members/{test_admin_user.id}/role",
            json=role_data,
            headers=admin_headers
        )
        
        assert response.status_code == 400
        assert "own role" in response.json()["detail"]
    
    def test_update_role_as_member(
        self,
        client: TestClient,
        test_organization: Organization,
        test_admin_user: User,
        member_headers: dict
    ):
        """Test updating role as non-admin (should fail)"""
        
        role_data = {
            "organization_role": "admin"
        }
        
        response = client.put(
            f"/api/v1/organizations/{test_organization.id}/members/{test_admin_user.id}/role",
            json=role_data,
            headers=member_headers
        )
        
        assert response.status_code == 403


class TestMemberRemovalEndpoint:
    """Test DELETE /organizations/{org_id}/members/{user_id} endpoint"""
    
    async def test_remove_member_as_admin(
        self,
        client: TestClient,
        async_db: AsyncSession,
        test_organization: Organization,
        admin_headers: dict
    ):
        """Test removing member as admin"""
        
        # Create additional member to remove
        extra_member = User(
            email="extra@test.com",
            organization_id=test_organization.id,
            organization_role=OrganizationRole.MEMBER,
            is_active=True
        )
        async_db.add(extra_member)
        await async_db.commit()
        await async_db.refresh(extra_member)
        
        response = client.delete(
            f"/api/v1/organizations/{test_organization.id}/members/{extra_member.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        assert "removed from organization successfully" in response.json()["message"]
    
    def test_remove_last_member_protection(
        self,
        client: TestClient,
        test_organization: Organization,
        test_admin_user: User,
        admin_headers: dict
    ):
        """Test protection against removing last member"""
        
        response = client.delete(
            f"/api/v1/organizations/{test_organization.id}/members/{test_admin_user.id}",
            headers=admin_headers
        )
        
        # Should be protected if this is the only member
        assert response.status_code == 400
        assert "last member" in response.json()["detail"]


class TestMemberStatsEndpoint:
    """Test GET /organizations/{org_id}/members/stats endpoint"""
    
    def test_get_member_stats(
        self,
        client: TestClient,
        test_organization: Organization,
        admin_headers: dict
    ):
        """Test getting organization member statistics"""
        
        response = client.get(
            f"/api/v1/organizations/{test_organization.id}/members/stats",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify stats structure
        expected_fields = [
            "total_members",
            "admin_count", 
            "member_count",
            "pending_invitations",
            "has_admin"
        ]
        
        for field in expected_fields:
            assert field in data
            assert isinstance(data[field], (int, bool))
    
    def test_get_stats_unauthorized(
        self,
        client: TestClient,
        test_organization: Organization,
        member_headers: dict
    ):
        """Test getting stats with member permissions (should work)"""
        
        response = client.get(
            f"/api/v1/organizations/{test_organization.id}/members/stats",
            headers=member_headers
        )
        
        assert response.status_code == 200


class TestOrganizationDiscoveryEndpoint:
    """Test organization discovery endpoints"""
    
    async def test_get_organization_by_domain(
        self,
        client: TestClient,
        async_db: AsyncSession,
        test_organization: Organization
    ):
        """Test public organization discovery by domain"""
        
        response = client.get(f"/api/v1/organizations/by-domain/{test_organization.domain}")
        
        if test_organization.domain:
            assert response.status_code == 200
            data = response.json()
            assert data["organization"]["domain"] == test_organization.domain
            assert data["organization"]["name"] == test_organization.name
        else:
            assert response.status_code == 404
    
    def test_get_organization_by_invalid_domain(
        self,
        client: TestClient
    ):
        """Test organization discovery with invalid domain"""
        
        response = client.get("/api/v1/organizations/by-domain/nonexistent.com")
        
        assert response.status_code == 404
        assert "No organization found" in response.json()["detail"]
    
    def test_get_organization_directory_as_admin(
        self,
        client: TestClient,
        admin_headers: dict
    ):
        """Test organization directory access as admin"""
        
        response = client.get(
            "/api/v1/organizations/directory",
            headers=admin_headers
        )
        
        # This would depend on user having system admin rights
        assert response.status_code in [200, 403]
    
    def test_registration_options(
        self,
        client: TestClient
    ):
        """Test registration options endpoint"""
        
        options_data = {
            "email": "test@example.com"
        }
        
        response = client.post(
            "/api/v1/organizations/registration-options",
            json=options_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = ["suggested_action", "options", "message"]
        for field in expected_fields:
            assert field in data


class TestRegistrationDomainInference:
    """Tests for registration inferring/setting organization domain"""

    def test_registration_creates_org_with_inferred_domain(self, client: TestClient):
        """Registration should create an org with domain inferred from email."""
        unique_part = str(uuid4())[:8]
        email_domain = f"infer-{unique_part}.com"
        registration_data = {
            "email": f"user@{email_domain}",
            "full_name": "Infer Domain User",
            "password": "StrongPass123"
        }

        reg_response = client.post("/api/v1/auth/register", json=registration_data)
        assert reg_response.status_code == 200

        # Organization discovery should now find the org by domain
        org_response = client.get(f"/api/v1/organizations/by-domain/{email_domain}")
        assert org_response.status_code == 200
        data = org_response.json()
        assert data["organization"]["domain"] == email_domain

    async def test_registration_sets_domain_on_existing_org_with_null_domain(
        self,
        client: TestClient,
        async_db: AsyncSession
    ):
        """If an existing org has null domain, registration sets it (first-writer-wins)."""
        # Prepare an existing org without a domain
        org_name = f"Acme {str(uuid4())[:8]}"
        existing_org = Organization(name=org_name, domain=None, is_enabled=True)
        async_db.add(existing_org)
        await async_db.commit()
        await async_db.refresh(existing_org)

        # Register a user providing the same organization name, with a specific email domain
        email_domain = "acme-example.com"
        registration_data = {
            "email": f"owner@{email_domain}",
            "full_name": "Acme Owner",
            "password": "StrongPass123",
            "organization_name": org_name
        }

        reg_response = client.post("/api/v1/auth/register", json=registration_data)
        assert reg_response.status_code == 200

        # The existing organization's domain should now be set and discoverable
        org_response = client.get(f"/api/v1/organizations/by-domain/{email_domain}")
        assert org_response.status_code == 200
        data = org_response.json()
        assert data["organization"]["domain"] == email_domain
        assert data["organization"]["id"] == str(existing_org.id)


class TestInvitationEndpoints:
    """Test invitation management endpoints"""
    
    async def test_get_invitation_details(
        self,
        client: TestClient,
        async_db: AsyncSession,
        test_organization: Organization,
        test_admin_user: User
    ):
        """Test getting invitation details by token"""
        
        # Create test invitation
        invitation = OrganizationInvitation(
            organization_id=test_organization.id,
            email="invited@test.com",
            role=OrganizationRole.MEMBER,
            invited_by_id=test_admin_user.id,
            invitation_token="test-token-123",
            expires_at=datetime.now(timezone.utc).replace(microsecond=0) + timezone.utc.localize(datetime.now()).utctimetuple()[6:],
            status=InvitationStatus.PENDING
        )
        async_db.add(invitation)
        await async_db.commit()
        
        response = client.get(f"/api/v1/invitations/{invitation.invitation_token}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == "invited@test.com"
        assert data["role"] == "member"
        assert data["status"] == "pending"
    
    def test_get_invitation_invalid_token(
        self,
        client: TestClient
    ):
        """Test getting invitation with invalid token"""
        
        response = client.get("/api/v1/invitations/invalid-token")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_accept_invitation_missing_data(
        self,
        client: TestClient
    ):
        """Test accepting invitation with missing user data"""
        
        accept_data = {}
        
        response = client.post(
            "/api/v1/invitations/test-token/accept",
            json=accept_data
        )
        
        # Should fail because invitation doesn't exist
        assert response.status_code in [400, 404]
    
    def test_decline_invitation(
        self,
        client: TestClient
    ):
        """Test declining invitation"""
        
        response = client.post("/api/v1/invitations/test-token/decline")
        
        # Should fail because invitation doesn't exist
        assert response.status_code in [400, 404]
    
    def test_list_organization_invitations(
        self,
        client: TestClient,
        test_organization: Organization,
        admin_headers: dict
    ):
        """Test listing organization invitations"""
        
        response = client.get(
            f"/api/v1/organizations/{test_organization.id}/invitations",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "data" in data
        assert "pagination" in data
    
    def test_cancel_invitation(
        self,
        client: TestClient,
        test_organization: Organization,
        admin_headers: dict
    ):
        """Test cancelling invitation"""
        
        invitation_id = uuid4()
        
        response = client.delete(
            f"/api/v1/organizations/{test_organization.id}/invitations/{invitation_id}",
            headers=admin_headers
        )
        
        # Should fail because invitation doesn't exist
        assert response.status_code in [400, 404]


class TestInputValidation:
    """Test input validation on endpoints"""
    
    def test_invalid_uuid_parameters(
        self,
        client: TestClient,
        admin_headers: dict
    ):
        """Test endpoints with invalid UUID parameters"""
        
        # Invalid organization ID
        response = client.get(
            "/api/v1/organizations/invalid-uuid/members",
            headers=admin_headers
        )
        assert response.status_code == 422
        
        # Invalid user ID
        response = client.put(
            f"/api/v1/organizations/{uuid4()}/members/invalid-uuid/role",
            json={"organization_role": "admin"},
            headers=admin_headers
        )
        assert response.status_code == 422
    
    def test_missing_required_fields(
        self,
        client: TestClient,
        test_organization: Organization,
        admin_headers: dict
    ):
        """Test endpoints with missing required fields"""
        
        # Missing email in invite request
        response = client.post(
            f"/api/v1/organizations/{test_organization.id}/members/invite",
            json={"role": "member"},
            headers=admin_headers
        )
        assert response.status_code == 422
        
        # Missing role in role update
        response = client.put(
            f"/api/v1/organizations/{test_organization.id}/members/{uuid4()}/role",
            json={},
            headers=admin_headers
        )
        assert response.status_code == 422
    
    def test_invalid_enum_values(
        self,
        client: TestClient,
        test_organization: Organization,
        admin_headers: dict
    ):
        """Test endpoints with invalid enum values"""
        
        # Invalid role
        response = client.post(
            f"/api/v1/organizations/{test_organization.id}/members/invite",
            json={"email": "test@example.com", "role": "invalid_role"},
            headers=admin_headers
        )
        assert response.status_code == 422
        
        # Invalid role in update
        response = client.put(
            f"/api/v1/organizations/{test_organization.id}/members/{uuid4()}/role",
            json={"organization_role": "super_admin"},
            headers=admin_headers
        )
        assert response.status_code == 422