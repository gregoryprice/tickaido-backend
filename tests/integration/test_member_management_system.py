#!/usr/bin/env python3
"""
Integration tests for Member Management System
Based on test scenarios from PRD
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.organization import Organization
from app.models.organization_invitation import (
    OrganizationInvitation, 
    OrganizationRole, 
    InvitationStatus
)
from app.services.member_management_service import MemberManagementService
from app.services.organization_discovery_service import OrganizationDiscoveryService
from app.services.user_service import UserService


@pytest.fixture
def member_service():
    """Member management service fixture"""
    return MemberManagementService()


@pytest.fixture
def discovery_service():
    """Organization discovery service fixture"""
    return OrganizationDiscoveryService()


@pytest.fixture
def user_service():
    """User service fixture"""
    return UserService()


class TestFirstUserRegistrationScenario:
    """Test Scenario 1: First User Registration (New Organization)"""
    
    async def test_first_user_registration_creates_admin(
        self,
        async_db: AsyncSession,
        member_service: MemberManagementService,
        discovery_service: OrganizationDiscoveryService
    ):
        """Test that first user becomes admin of new organization"""
        
        # Given: No organization exists for domain
        domain = "newcompany.com"
        organizations = await discovery_service.find_organizations_by_domain(async_db, domain)
        assert len(organizations) == 0
        
        # When: User registers and creates organization
        user_email = f"admin@{domain}"
        organization_name = "New Company Inc"
        
        # Create organization first
        org = Organization(
            name=organization_name,
            domain=domain,
            is_enabled=True
        )
        async_db.add(org)
        await async_db.commit()
        await async_db.refresh(org)
        
        # Create user as admin
        user = User(
            email=user_email,
            password_hash="hashed_password",
            full_name="Admin User",
            organization_id=org.id,
            organization_role=OrganizationRole.ADMIN,
            joined_organization_at=datetime.now(timezone.utc),
            is_active=True,
            is_verified=True
        )
        async_db.add(user)
        await async_db.commit()
        await async_db.refresh(user)
        
        # Then: User is admin, organization created
        assert user.organization_role == OrganizationRole.ADMIN
        assert user.organization_id == org.id
        assert user.is_organization_admin()
        assert org.domain == domain
        
        # Verify organization member count
        members, total = await member_service.get_organization_members(
            async_db, org.id
        )
        assert total == 1
        assert members[0].id == user.id
    
    def test_domain_extraction_from_email(self, discovery_service: OrganizationDiscoveryService):
        """Test email domain extraction logic"""
        test_cases = [
            ("user@example.com", "example.com"),
            ("test.user@subdomain.company.co.uk", "subdomain.company.co.uk"),
            ("admin@localhost", "localhost"),
        ]
        
        for email, expected_domain in test_cases:
            assert discovery_service.extract_domain_from_email(email) == expected_domain
    
    async def test_organization_domain_uniqueness_not_required(
        self,
        async_db: AsyncSession
    ):
        """Test that multiple organizations can have same domain"""
        
        # Given: Organization exists with domain
        domain = "example.com"
        org1 = Organization(name="Company A", domain=domain, is_enabled=True)
        async_db.add(org1)
        await async_db.commit()
        
        # When: Another organization created with same domain
        org2 = Organization(name="Company B", domain=domain, is_enabled=True)
        async_db.add(org2)
        await async_db.commit()
        
        # Then: Both organizations exist
        assert org1.id != org2.id
        assert org1.domain == org2.domain == domain


class TestSubsequentUserRegistrationScenario:
    """Test Scenario 2: Subsequent User Registration (Join Existing)"""
    
    async def test_subsequent_user_joins_as_member(
        self,
        async_db: AsyncSession,
        member_service: MemberManagementService
    ):
        """Test that subsequent users join as members"""
        
        # Given: Organization exists with admin
        org = Organization(
            name="Example Inc",
            domain="example.com",
            is_enabled=True
        )
        async_db.add(org)
        await async_db.commit()
        await async_db.refresh(org)
        
        admin_user = User(
            email="admin@example.com",
            password_hash="hashed",
            full_name="Admin User",
            organization_id=org.id,
            organization_role=OrganizationRole.ADMIN,
            joined_organization_at=datetime.now(timezone.utc),
            is_active=True,
            is_verified=True
        )
        async_db.add(admin_user)
        await async_db.commit()
        
        # When: New user registers with same domain
        member_user = User(
            email="member@example.com",
            password_hash="hashed",
            full_name="Member User",
            organization_id=org.id,
            organization_role=OrganizationRole.MEMBER,
            joined_organization_at=datetime.now(timezone.utc),
            is_active=True,
            is_verified=True
        )
        async_db.add(member_user)
        await async_db.commit()
        await async_db.refresh(member_user)
        
        # Then: User is member of existing organization
        assert member_user.organization_role == OrganizationRole.MEMBER
        assert member_user.organization_id == admin_user.organization_id
        
        # Verify organization member count
        members, total = await member_service.get_organization_members(
            async_db, org.id
        )
        assert total == 2
    
    async def test_domain_lookup_functionality(
        self,
        async_db: AsyncSession,
        discovery_service: OrganizationDiscoveryService
    ):
        """Test domain lookup works correctly"""
        
        # Given: Organization exists
        domain = "testdomain.com"
        org = Organization(
            name="Test Company",
            domain=domain,
            is_enabled=True
        )
        async_db.add(org)
        await async_db.commit()
        
        # When: Domain lookup performed
        org_data = await discovery_service.get_organization_by_domain(async_db, domain)
        
        # Then: Returns organization data
        assert org_data is not None
        assert org_data["domain"] == domain
        assert org_data["name"] == "Test Company"


class TestAdminPromotionScenario:
    """Test Scenario 3: Admin Promotes Member to Admin"""
    
    async def test_admin_promotes_member_to_admin(
        self,
        async_db: AsyncSession,
        member_service: MemberManagementService
    ):
        """Test admin can promote member to admin"""
        
        # Given: Organization with admin and member
        org = Organization(name="Example Inc", domain="example.com", is_enabled=True)
        async_db.add(org)
        await async_db.commit()
        await async_db.refresh(org)
        
        admin = User(
            email="admin@example.com",
            organization_id=org.id,
            organization_role=OrganizationRole.ADMIN,
            is_active=True
        )
        async_db.add(admin)
        
        member = User(
            email="member@example.com",
            organization_id=org.id,
            organization_role=OrganizationRole.MEMBER,
            is_active=True
        )
        async_db.add(member)
        await async_db.commit()
        await async_db.refresh(admin)
        await async_db.refresh(member)
        
        # When: Admin promotes member
        success = await member_service.update_member_role(
            db=async_db,
            organization_id=org.id,
            user_id=member.id,
            new_role=OrganizationRole.ADMIN,
            admin_user_id=admin.id
        )
        
        # Then: Member becomes admin
        assert success is True
        await async_db.refresh(member)
        assert member.organization_role == OrganizationRole.ADMIN
    
    async def test_multiple_admins_allowed(
        self,
        async_db: AsyncSession,
        member_service: MemberManagementService
    ):
        """Test organization can have multiple admins"""
        
        # Given: Organization with 2 users
        org = Organization(name="Example Inc", domain="example.com", is_enabled=True)
        async_db.add(org)
        await async_db.commit()
        
        admin1 = User(
            email="admin1@example.com",
            organization_id=org.id,
            organization_role=OrganizationRole.ADMIN,
            is_active=True
        )
        admin2 = User(
            email="admin2@example.com",
            organization_id=org.id,
            organization_role=OrganizationRole.ADMIN,
            is_active=True
        )
        async_db.add_all([admin1, admin2])
        await async_db.commit()
        
        # Then: Both users are admins
        assert admin1.organization_role == OrganizationRole.ADMIN
        assert admin2.organization_role == OrganizationRole.ADMIN
        assert admin1.is_organization_admin()
        assert admin2.is_organization_admin()
    
    async def test_member_cannot_promote_others(
        self,
        async_db: AsyncSession,
        member_service: MemberManagementService
    ):
        """Test member users cannot promote others"""
        
        # Given: Organization with admin and 2 members
        org = Organization(name="Example Inc", domain="example.com", is_enabled=True)
        async_db.add(org)
        await async_db.commit()
        
        admin = User(
            email="admin@example.com",
            organization_id=org.id,
            organization_role=OrganizationRole.ADMIN,
            is_active=True
        )
        member1 = User(
            email="member1@example.com",
            organization_id=org.id,
            organization_role=OrganizationRole.MEMBER,
            is_active=True
        )
        member2 = User(
            email="member2@example.com",
            organization_id=org.id,
            organization_role=OrganizationRole.MEMBER,
            is_active=True
        )
        async_db.add_all([admin, member1, member2])
        await async_db.commit()
        await async_db.refresh(member1)
        await async_db.refresh(member2)
        
        # When: Member tries to promote another member
        with pytest.raises(PermissionError):
            await member_service.update_member_role(
                db=async_db,
                organization_id=org.id,
                user_id=member2.id,
                new_role=OrganizationRole.ADMIN,
                admin_user_id=member1.id
            )
        
        # Then: Member2 role unchanged
        await async_db.refresh(member2)
        assert member2.organization_role == OrganizationRole.MEMBER


class TestSelfRoleChangePreventionScenario:
    """Test Scenario 4: Self-Role Change Prevention"""
    
    async def test_user_cannot_change_own_role(
        self,
        async_db: AsyncSession,
        member_service: MemberManagementService
    ):
        """Test users cannot modify their own role"""
        
        # Given: Admin user
        org = Organization(name="Example Inc", domain="example.com", is_enabled=True)
        async_db.add(org)
        await async_db.commit()
        
        admin = User(
            email="admin@example.com",
            organization_id=org.id,
            organization_role=OrganizationRole.ADMIN,
            is_active=True
        )
        async_db.add(admin)
        await async_db.commit()
        await async_db.refresh(admin)
        
        # When: Admin tries to change own role
        with pytest.raises(ValueError, match="cannot modify their own role"):
            await member_service.update_member_role(
                db=async_db,
                organization_id=org.id,
                user_id=admin.id,
                new_role=OrganizationRole.MEMBER,
                admin_user_id=admin.id
            )
        
        # Then: Role unchanged
        await async_db.refresh(admin)
        assert admin.organization_role == OrganizationRole.ADMIN


class TestMemberDeletionScenario:
    """Test Scenario 5: Member Deletion with Auto-Admin Promotion"""
    
    async def test_auto_admin_promotion_on_last_admin_deletion(
        self,
        async_db: AsyncSession,
        member_service: MemberManagementService
    ):
        """Test member becomes admin when last admin is deleted"""
        
        # Given: Organization with 1 admin, 1 member
        org = Organization(name="Example Inc", domain="example.com", is_enabled=True)
        async_db.add(org)
        await async_db.commit()
        
        admin = User(
            email="admin@example.com",
            organization_id=org.id,
            organization_role=OrganizationRole.ADMIN,
            joined_organization_at=datetime.now(timezone.utc) - timedelta(days=1),
            is_active=True
        )
        member = User(
            email="member@example.com",
            organization_id=org.id,
            organization_role=OrganizationRole.MEMBER,
            joined_organization_at=datetime.now(timezone.utc),
            is_active=True
        )
        async_db.add_all([admin, member])
        await async_db.commit()
        await async_db.refresh(admin)
        await async_db.refresh(member)
        
        # When: Admin is removed
        success = await member_service.remove_member(
            db=async_db,
            organization_id=org.id,
            user_id=admin.id,
            admin_user_id=admin.id
        )
        
        # Then: Member auto-promoted to admin
        assert success is True
        await async_db.refresh(member)
        assert member.organization_role == OrganizationRole.ADMIN
    
    async def test_normal_member_deletion(
        self,
        async_db: AsyncSession,
        member_service: MemberManagementService
    ):
        """Test normal member deletion doesn't trigger auto-promotion"""
        
        # Given: Organization with 1 admin, 2 members
        org = Organization(name="Example Inc", domain="example.com", is_enabled=True)
        async_db.add(org)
        await async_db.commit()
        
        admin = User(
            email="admin@example.com",
            organization_id=org.id,
            organization_role=OrganizationRole.ADMIN,
            is_active=True
        )
        member1 = User(
            email="member1@example.com",
            organization_id=org.id,
            organization_role=OrganizationRole.MEMBER,
            is_active=True
        )
        member2 = User(
            email="member2@example.com",
            organization_id=org.id,
            organization_role=OrganizationRole.MEMBER,
            is_active=True
        )
        async_db.add_all([admin, member1, member2])
        await async_db.commit()
        await async_db.refresh(admin)
        await async_db.refresh(member1)
        await async_db.refresh(member2)
        
        # When: Admin removes a member
        success = await member_service.remove_member(
            db=async_db,
            organization_id=org.id,
            user_id=member1.id,
            admin_user_id=admin.id
        )
        
        # Then: Normal deletion, admin stays admin
        assert success is True
        await async_db.refresh(admin)
        await async_db.refresh(member2)
        assert admin.organization_role == OrganizationRole.ADMIN
        assert member2.organization_role == OrganizationRole.MEMBER


class TestLastMemberDeletionProtection:
    """Test Scenario 6: Last Member Deletion Protection"""
    
    async def test_cannot_delete_last_member_without_org_deletion(
        self,
        async_db: AsyncSession,
        member_service: MemberManagementService
    ):
        """Test cannot delete sole organization member"""
        
        # Given: Organization with only 1 member
        org = Organization(name="Example Inc", domain="example.com", is_enabled=True)
        async_db.add(org)
        await async_db.commit()
        
        admin = User(
            email="admin@example.com",
            organization_id=org.id,
            organization_role=OrganizationRole.ADMIN,
            is_active=True
        )
        async_db.add(admin)
        await async_db.commit()
        await async_db.refresh(admin)
        
        # When: Try to delete last member
        with pytest.raises(ValueError, match="Cannot delete last member"):
            await member_service.remove_member(
                db=async_db,
                organization_id=org.id,
                user_id=admin.id,
                admin_user_id=admin.id
            )
        
        # Then: User and organization still exist
        await async_db.refresh(admin)
        assert admin.organization_role == OrganizationRole.ADMIN
        assert admin.organization_id == org.id


class TestCrossOrganizationAccessPrevention:
    """Test Scenario 7: Cross-Organization Access Prevention"""
    
    async def test_cross_organization_access_denied(
        self,
        async_db: AsyncSession,
        member_service: MemberManagementService
    ):
        """Test users cannot access other organizations"""
        
        # Given: Two separate organizations
        org_a = Organization(name="Company A", domain="companya.com", is_enabled=True)
        org_b = Organization(name="Company B", domain="companyb.com", is_enabled=True)
        async_db.add_all([org_a, org_b])
        await async_db.commit()
        
        admin_a = User(
            email="admin@companya.com",
            organization_id=org_a.id,
            organization_role=OrganizationRole.ADMIN,
            is_active=True
        )
        admin_b = User(
            email="admin@companyb.com",
            organization_id=org_b.id,
            organization_role=OrganizationRole.ADMIN,
            is_active=True
        )
        member_b = User(
            email="member@companyb.com",
            organization_id=org_b.id,
            organization_role=OrganizationRole.MEMBER,
            is_active=True
        )
        async_db.add_all([admin_a, admin_b, member_b])
        await async_db.commit()
        await async_db.refresh(admin_a)
        await async_db.refresh(member_b)
        
        # When: Admin A tries to manage Company B's members
        with pytest.raises(PermissionError, match="their own organization"):
            await member_service.update_member_role(
                db=async_db,
                organization_id=org_b.id,
                user_id=member_b.id,
                new_role=OrganizationRole.ADMIN,
                admin_user_id=admin_a.id
            )
    
    async def test_organization_isolation(
        self,
        async_db: AsyncSession,
        member_service: MemberManagementService
    ):
        """Test complete organization isolation"""
        
        # Given: Users in different organizations
        org_a = Organization(name="Org A", domain="orga.com", is_enabled=True)
        org_b = Organization(name="Org B", domain="orgb.com", is_enabled=True)
        async_db.add_all([org_a, org_b])
        await async_db.commit()
        
        admin_a = User(
            email="admin@orga.com",
            organization_id=org_a.id,
            organization_role=OrganizationRole.ADMIN,
            is_active=True
        )
        admin_b = User(
            email="admin@orgb.com",
            organization_id=org_b.id,
            organization_role=OrganizationRole.ADMIN,
            is_active=True
        )
        async_db.add_all([admin_a, admin_b])
        await async_db.commit()
        
        # Test: Cannot view other org's members
        members_a, total_a = await member_service.get_organization_members(
            async_db, org_a.id
        )
        members_b, total_b = await member_service.get_organization_members(
            async_db, org_b.id
        )
        
        # Each org only sees its own members
        assert total_a == 1
        assert members_a[0].email == "admin@orga.com"
        assert total_b == 1  
        assert members_b[0].email == "admin@orgb.com"


class TestInvitationSystem:
    """Test invitation system functionality"""
    
    async def test_invitation_creation_and_acceptance(
        self,
        async_db: AsyncSession,
        member_service: MemberManagementService
    ):
        """Test invitation creation and acceptance flow"""
        
        # Given: Organization with admin
        org = Organization(name="Test Org", domain="test.com", is_enabled=True)
        async_db.add(org)
        await async_db.commit()
        
        admin = User(
            email="admin@test.com",
            organization_id=org.id,
            organization_role=OrganizationRole.ADMIN,
            is_active=True
        )
        async_db.add(admin)
        await async_db.commit()
        await async_db.refresh(admin)
        
        # When: Admin creates invitation
        invitation = await member_service.create_invitation(
            db=async_db,
            organization_id=org.id,
            email="newuser@test.com",
            role=OrganizationRole.MEMBER,
            admin_user_id=admin.id,
            message="Welcome to our team!"
        )
        
        # Then: Invitation created successfully
        assert invitation.email == "newuser@test.com"
        assert invitation.role == OrganizationRole.MEMBER
        assert invitation.status == InvitationStatus.PENDING
        assert invitation.is_pending is True
        assert invitation.invited_by_id == admin.id
        
        # When: Invitation accepted
        user_data = {
            "password": "securepassword123",
            "full_name": "New User"
        }
        user, accepted_invitation = await member_service.accept_invitation(
            db=async_db,
            invitation_token=invitation.invitation_token,
            user_data=user_data
        )
        
        # Then: User created and joined organization
        assert user.email == "newuser@test.com"
        assert user.organization_id == org.id
        assert user.organization_role == OrganizationRole.MEMBER
        assert accepted_invitation.status == InvitationStatus.ACCEPTED
    
    async def test_invitation_expiration(
        self,
        async_db: AsyncSession,
        member_service: MemberManagementService
    ):
        """Test invitation expiration logic"""
        
        # Given: Organization with admin
        org = Organization(name="Test Org", domain="test.com", is_enabled=True)
        async_db.add(org)
        await async_db.commit()
        
        admin = User(
            email="admin@test.com",
            organization_id=org.id,
            organization_role=OrganizationRole.ADMIN,
            is_active=True
        )
        async_db.add(admin)
        await async_db.commit()
        
        # Create expired invitation
        invitation = OrganizationInvitation(
            organization_id=org.id,
            email="expired@test.com",
            role=OrganizationRole.MEMBER,
            invited_by_id=admin.id,
            invitation_token="expired-token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Already expired
            status=InvitationStatus.PENDING
        )
        async_db.add(invitation)
        await async_db.commit()
        
        # Then: Invitation should be marked as expired
        assert invitation.is_expired is True
        assert invitation.is_pending is False


class TestOrganizationMemberStatistics:
    """Test organization member statistics"""
    
    async def test_get_organization_member_stats(
        self,
        async_db: AsyncSession,
        member_service: MemberManagementService
    ):
        """Test organization member statistics calculation"""
        
        # Given: Organization with mixed members
        org = Organization(name="Test Org", domain="test.com", is_enabled=True)
        async_db.add(org)
        await async_db.commit()
        
        # Create 2 admins and 3 members
        users = [
            User(email="admin1@test.com", organization_id=org.id, organization_role=OrganizationRole.ADMIN, is_active=True),
            User(email="admin2@test.com", organization_id=org.id, organization_role=OrganizationRole.ADMIN, is_active=True),
            User(email="member1@test.com", organization_id=org.id, organization_role=OrganizationRole.MEMBER, is_active=True),
            User(email="member2@test.com", organization_id=org.id, organization_role=OrganizationRole.MEMBER, is_active=True),
            User(email="member3@test.com", organization_id=org.id, organization_role=OrganizationRole.MEMBER, is_active=True),
        ]
        async_db.add_all(users)
        await async_db.commit()
        
        # Create pending invitation
        invitation = OrganizationInvitation(
            organization_id=org.id,
            email="pending@test.com",
            role=OrganizationRole.MEMBER,
            invited_by_id=users[0].id,
            invitation_token="pending-token",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            status=InvitationStatus.PENDING
        )
        async_db.add(invitation)
        await async_db.commit()
        
        # When: Get member statistics
        stats = await member_service.get_organization_member_stats(async_db, org.id)
        
        # Then: Statistics are correct
        assert stats["total_members"] == 5
        assert stats["admin_count"] == 2
        assert stats["member_count"] == 3
        assert stats["pending_invitations"] == 1
        assert stats["has_admin"] is True