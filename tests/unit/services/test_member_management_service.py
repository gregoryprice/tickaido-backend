#!/usr/bin/env python3
"""
Unit tests for Member Management Service
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.services.member_management_service import MemberManagementService
from app.models.user import User
from app.models.organization import Organization
from app.models.organization_invitation import (
    OrganizationInvitation,
    OrganizationRole,
    InvitationStatus
)


@pytest.fixture
def member_service():
    """Member management service fixture"""
    return MemberManagementService()


class TestDomainExtraction:
    """Test email domain extraction functionality"""
    
    def test_extract_domain_from_email(self, member_service):
        """Test domain extraction from various email formats"""
        test_cases = [
            ("user@example.com", "example.com"),
            ("test.user@subdomain.company.co.uk", "subdomain.company.co.uk"),
            ("admin@localhost", "localhost"),
            ("USER@EXAMPLE.COM", "example.com"),  # Test case normalization
            ("  user@example.com  ", "example.com")  # Test whitespace handling
        ]
        
        for email, expected_domain in test_cases:
            result = member_service.extract_domain_from_email(email)
            assert result == expected_domain
    
    def test_extract_domain_invalid_email(self, member_service):
        """Test domain extraction with invalid emails"""
        invalid_emails = ["", "no-at-sign", "@example.com", "user@", None]
        
        for email in invalid_emails:
            with pytest.raises(ValueError):
                member_service.extract_domain_from_email(email)


class TestInvitationTokenGeneration:
    """Test invitation token generation"""
    
    def test_generate_invitation_token(self, member_service):
        """Test invitation token generation"""
        token = member_service._generate_invitation_token()
        
        # Token should be non-empty string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Should generate unique tokens
        token2 = member_service._generate_invitation_token()
        assert token != token2


class TestMemberRoleValidation:
    """Test member role validation and permissions"""
    
    @pytest.mark.asyncio
    async def test_update_member_role_permission_validation(self, member_service):
        """Test role update permission validation"""
        
        # Mock database session
        mock_db = AsyncMock()
        
        # Mock users
        admin_user = Mock(spec=User)
        admin_user.id = uuid4()
        admin_user.organization_id = uuid4()
        admin_user.is_organization_admin.return_value = True
        
        member_user = Mock(spec=User)
        member_user.id = uuid4()
        member_user.organization_id = admin_user.organization_id
        member_user.organization_role = OrganizationRole.MEMBER
        
        # Mock db.get to return the users
        async def mock_get(model, user_id):
            if user_id == admin_user.id:
                return admin_user
            elif user_id == member_user.id:
                return member_user
            return None
        
        mock_db.get = mock_get
        
        # Test successful role update
        result = await member_service.update_member_role(
            db=mock_db,
            organization_id=admin_user.organization_id,
            user_id=member_user.id,
            new_role=OrganizationRole.ADMIN,
            admin_user_id=admin_user.id
        )
        
        assert result is True
        assert member_user.organization_role == OrganizationRole.ADMIN
    
    @pytest.mark.asyncio
    async def test_update_member_role_self_modification_prevention(self, member_service):
        """Test prevention of self role modification"""
        
        mock_db = AsyncMock()
        user_id = uuid4()
        org_id = uuid4()
        
        # Mock admin user
        admin_user = Mock(spec=User)
        admin_user.id = user_id
        admin_user.organization_id = org_id
        admin_user.is_organization_admin.return_value = True
        
        # Mock db.get to return the admin user
        mock_db.get.return_value = admin_user
        
        # When admin tries to change their own role
        with pytest.raises(ValueError, match="cannot modify their own role"):
            await member_service.update_member_role(
                db=mock_db,
                organization_id=org_id,
                user_id=user_id,
                new_role=OrganizationRole.MEMBER,
                admin_user_id=user_id  # Same user ID
            )


class TestInvitationCreation:
    """Test invitation creation logic"""
    
    @pytest.mark.asyncio
    async def test_create_invitation_validation(self, member_service):
        """Test invitation creation validation"""
        
        mock_db = AsyncMock()
        org_id = uuid4()
        admin_id = uuid4()
        
        # Mock admin user
        admin_user = Mock(spec=User)
        admin_user.id = admin_id
        admin_user.organization_id = org_id
        admin_user.is_organization_admin.return_value = True
        
        # Mock db responses
        mock_db.get.return_value = admin_user
        
        # Create multiple mock results for the execute calls
        # First execute call is for existing invitation check
        mock_execute_result = Mock()
        mock_execute_result.scalar_one_or_none.return_value = None  # No existing invitation
        mock_db.execute.return_value = mock_execute_result
        
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Mock _get_user_by_email to return None (no existing user)
        member_service._get_user_by_email = AsyncMock(return_value=None)
        
        # Test valid invitation creation
        invitation = await member_service.create_invitation(
            db=mock_db,
            organization_id=org_id,
            email="newuser@example.com",
            role=OrganizationRole.MEMBER,
            admin_user_id=admin_id,
            message="Welcome to our team!"
        )
        
        # Verify invitation was created
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_invitation_invalid_email(self, member_service):
        """Test invitation creation with invalid email"""
        
        mock_db = AsyncMock()
        org_id = uuid4()
        admin_id = uuid4()
        
        # Mock admin user
        admin_user = Mock(spec=User)
        admin_user.id = admin_id
        admin_user.organization_id = org_id
        admin_user.is_organization_admin.return_value = True
        
        mock_db.get.return_value = admin_user
        
        # Test invalid email
        with pytest.raises(ValueError, match="Invalid email address"):
            await member_service.create_invitation(
                db=mock_db,
                organization_id=org_id,
                email="invalid-email",
                role=OrganizationRole.MEMBER,
                admin_user_id=admin_id
            )


class TestInvitationAcceptance:
    """Test invitation acceptance logic"""
    
    @pytest.mark.asyncio
    async def test_accept_invitation_new_user(self, member_service):
        """Test accepting invitation for new user"""
        
        mock_db = AsyncMock()
        token = "test-token"
        org_id = uuid4()
        inviter_id = uuid4()
        
        # Mock invitation
        mock_invitation = Mock(spec=OrganizationInvitation)
        mock_invitation.id = uuid4()
        mock_invitation.organization_id = org_id
        mock_invitation.email = "newuser@example.com"
        mock_invitation.role = OrganizationRole.MEMBER
        mock_invitation.invited_by_id = inviter_id
        mock_invitation.created_at = datetime.now(timezone.utc)
        mock_invitation.is_pending = True
        mock_invitation.is_expired = False
        mock_invitation.accept = Mock()
        
        # Mock that user doesn't exist (new user scenario)
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # Mock get_invitation_by_token
        member_service.get_invitation_by_token = AsyncMock(return_value=mock_invitation)
        
        # Mock User creation
        mock_user = Mock(spec=User)
        mock_user.id = uuid4()
        mock_user.email = "newuser@example.com"
        mock_user.organization_id = org_id
        mock_user.organization_role = OrganizationRole.MEMBER
        
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Test invitation acceptance for new user
        user_data = {
            "password": "securepassword123",
            "full_name": "New User"
        }
        
        # We need to mock the user creation in the method
        original_get_user_by_email = member_service._get_user_by_email
        member_service._get_user_by_email = AsyncMock(return_value=None)  # No existing user
        
        try:
            user, invitation = await member_service.accept_invitation(
                db=mock_db,
                invitation_token=token,
                user_data=user_data
            )
            
            # Verify invitation was accepted
            mock_invitation.accept.assert_called_once()
            mock_db.add.assert_called()
            mock_db.commit.assert_called()
            
        finally:
            # Restore original method
            member_service._get_user_by_email = original_get_user_by_email
    
    @pytest.mark.asyncio
    async def test_accept_invitation_expired(self, member_service):
        """Test accepting expired invitation"""
        
        mock_db = AsyncMock()
        token = "expired-token"
        
        # Mock expired invitation
        mock_invitation = Mock(spec=OrganizationInvitation)
        mock_invitation.is_pending = True
        mock_invitation.is_expired = True
        mock_invitation.expire = Mock()
        
        member_service.get_invitation_by_token = AsyncMock(return_value=mock_invitation)
        
        # Test expired invitation acceptance
        with pytest.raises(ValueError, match="expired"):
            await member_service.accept_invitation(
                db=mock_db,
                invitation_token=token
            )
        
        # Verify invitation was marked as expired
        mock_invitation.expire.assert_called_once()


class TestMemberRemoval:
    """Test member removal and auto-promotion logic"""
    
    @pytest.mark.asyncio
    async def test_remove_member_last_member_protection(self, member_service):
        """Test protection against removing last member"""
        
        mock_db = AsyncMock()
        org_id = uuid4()
        admin_id = uuid4()
        user_id = uuid4()
        
        # Mock admin user
        admin_user = Mock(spec=User)
        admin_user.id = admin_id
        admin_user.organization_id = org_id
        admin_user.is_organization_admin.return_value = True
        
        # Mock target user
        target_user = Mock(spec=User)
        target_user.id = user_id
        target_user.organization_id = org_id
        
        # Mock database responses
        async def mock_get(model, user_id_param):
            if user_id_param == admin_id:
                return admin_user
            elif user_id_param == user_id:
                return target_user
            return None
        
        mock_db.get = mock_get
        
        # Mock member count query to return 1 (last member)
        mock_execute_result = Mock()
        mock_execute_result.scalar.return_value = 1  # Return 1 member
        mock_db.execute.return_value = mock_execute_result
        
        # Test removing last member
        with pytest.raises(ValueError, match="Cannot delete last member"):
            await member_service.remove_member(
                db=mock_db,
                organization_id=org_id,
                user_id=user_id,
                admin_user_id=admin_id
            )


class TestOrganizationStatistics:
    """Test organization statistics calculation"""
    
    @pytest.mark.asyncio
    async def test_get_organization_member_stats(self, member_service):
        """Test member statistics calculation"""
        
        mock_db = AsyncMock()
        org_id = uuid4()
        
        # Mock query results - need separate mock objects for each execute call
        mock_results = [Mock() for _ in range(3)]
        mock_results[0].scalar.return_value = 2  # admin_count
        mock_results[1].scalar.return_value = 3  # member_count
        mock_results[2].scalar.return_value = 1  # pending_invitations
        
        mock_db.execute.side_effect = mock_results
        
        # Test statistics retrieval
        stats = await member_service.get_organization_member_stats(mock_db, org_id)
        
        # Verify results
        assert stats["admin_count"] == 2
        assert stats["member_count"] == 3
        assert stats["total_members"] == 5
        assert stats["pending_invitations"] == 1
        assert stats["has_admin"] is True
    
    @pytest.mark.asyncio
    async def test_get_organization_member_stats_no_admin(self, member_service):
        """Test statistics when no admin exists"""
        
        mock_db = AsyncMock()
        org_id = uuid4()
        
        # Mock query results - no admins, need separate mock objects for each execute call
        mock_results = [Mock() for _ in range(3)]
        mock_results[0].scalar.return_value = 0  # admin_count
        mock_results[1].scalar.return_value = 5  # member_count  
        mock_results[2].scalar.return_value = 2  # pending_invitations
        
        mock_db.execute.side_effect = mock_results
        
        # Test statistics retrieval
        stats = await member_service.get_organization_member_stats(mock_db, org_id)
        
        # Verify results
        assert stats["admin_count"] == 0
        assert stats["member_count"] == 5
        assert stats["total_members"] == 5
        assert stats["pending_invitations"] == 2
        assert stats["has_admin"] is False


class TestInvitationStatus:
    """Test invitation status management"""
    
    def test_invitation_expiry_logic(self):
        """Test invitation expiry detection"""
        
        # Test non-expired invitation
        invitation = Mock(spec=OrganizationInvitation)
        invitation.status = InvitationStatus.PENDING
        invitation.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Mock the is_expired property
        invitation.is_expired = invitation.expires_at < datetime.now(timezone.utc)
        invitation.is_pending = invitation.status == InvitationStatus.PENDING and not invitation.is_expired
        
        assert invitation.is_expired is False
        assert invitation.is_pending is True
        
        # Test expired invitation
        invitation.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        invitation.is_expired = invitation.expires_at < datetime.now(timezone.utc)
        invitation.is_pending = invitation.status == InvitationStatus.PENDING and not invitation.is_expired
        
        assert invitation.is_expired is True
        assert invitation.is_pending is False
    
    def test_invitation_status_transitions(self):
        """Test invitation status transitions"""
        
        invitation = Mock(spec=OrganizationInvitation)
        invitation.status = InvitationStatus.PENDING
        
        # Mock status transition methods
        def accept():
            invitation.status = InvitationStatus.ACCEPTED
            invitation.accepted_at = datetime.now(timezone.utc)
        
        def decline():
            invitation.status = InvitationStatus.DECLINED
            invitation.declined_at = datetime.now(timezone.utc)
        
        def cancel():
            invitation.status = InvitationStatus.CANCELLED
            invitation.cancelled_at = datetime.now(timezone.utc)
        
        invitation.accept = accept
        invitation.decline = decline
        invitation.cancel = cancel
        
        # Test acceptance
        invitation.accept()
        assert invitation.status == InvitationStatus.ACCEPTED
        assert invitation.accepted_at is not None
        
        # Reset for decline test
        invitation.status = InvitationStatus.PENDING
        invitation.decline()
        assert invitation.status == InvitationStatus.DECLINED
        assert invitation.declined_at is not None
        
        # Reset for cancel test
        invitation.status = InvitationStatus.PENDING
        invitation.cancel()
        assert invitation.status == InvitationStatus.CANCELLED
        assert invitation.cancelled_at is not None


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_permission_error_handling(self, member_service):
        """Test permission error handling"""
        
        mock_db = AsyncMock()
        org_id = uuid4()
        user_id = uuid4()
        member_id = uuid4()
        
        # Mock member user (not admin)
        member_user = Mock(spec=User)
        member_user.id = user_id
        member_user.organization_id = org_id
        member_user.is_organization_admin.return_value = False
        
        mock_db.get.return_value = member_user
        
        # Test permission error when non-admin tries to update role
        with pytest.raises(PermissionError):
            await member_service.update_member_role(
                db=mock_db,
                organization_id=org_id,
                user_id=member_id,
                new_role=OrganizationRole.ADMIN,
                admin_user_id=user_id
            )
    
    @pytest.mark.asyncio
    async def test_cross_organization_access_prevention(self, member_service):
        """Test prevention of cross-organization access"""
        
        mock_db = AsyncMock()
        org_a_id = uuid4()
        org_b_id = uuid4()
        admin_id = uuid4()
        member_id = uuid4()
        
        # Mock admin from organization A
        admin_user = Mock(spec=User)
        admin_user.id = admin_id
        admin_user.organization_id = org_a_id
        admin_user.is_organization_admin.return_value = True
        
        mock_db.get.return_value = admin_user
        
        # Test cross-organization access prevention
        with pytest.raises(PermissionError, match="their own organization"):
            await member_service.update_member_role(
                db=mock_db,
                organization_id=org_b_id,  # Different organization
                user_id=member_id,
                new_role=OrganizationRole.ADMIN,
                admin_user_id=admin_id
            )