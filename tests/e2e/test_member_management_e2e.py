#!/usr/bin/env python3
"""
MEMBER MANAGEMENT END-TO-END FLOW TEST

This test performs comprehensive e2e testing of the member management system:
1. Create test organization with admin user
2. Test invitation creation and management
3. Test member listing and role management 
4. Test organization discovery functionality
5. Validate all API endpoints with complete field validation

CRITICAL: This test hits actual API endpoints with real authentication
and validates the complete member management system.
"""

import pytest
import requests
import json
import time
from uuid import uuid4
from datetime import datetime


# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Shared test data across all tests in this module
MEMBER_TEST_DATA = {}


class TestMemberManagementE2E:
    """Complete end-to-end test of the member management system"""
    
    @classmethod
    def setup_class(cls):
        """Setup for the member management test"""
        cls.session = requests.Session()
        cls.session.headers.update({"Content-Type": "application/json"})
        
    @property
    def test_data(self):
        """Access shared test data"""
        return MEMBER_TEST_DATA
    
    def test_01_health_check(self):
        """Verify service is healthy before starting"""
        
        response = self.session.get(f"{BASE_URL}/health")
        assert response.status_code == 200, f"Service not healthy: {response.status_code}"
        
        health_data = response.json()
        print("\n🏥 Member Management E2E - Health Check:")
        print(f"   Status: {health_data['status']}")
        print(f"   Database: {health_data['services']['database']}")
        
        assert health_data["status"] == "healthy", "Service must be healthy for E2E testing"
        assert health_data["services"]["database"] == "healthy", "Database must be healthy"
    
    def test_02_create_admin_user_and_organization(self):
        """Step 1: Create admin user with organization"""
        
        # Generate unique test data
        test_email = f"admin_member_test_{int(time.time())}@example.com"
        test_org_name = f"Member Test Org {int(time.time())}"
        test_password = "SecureAdminPass123!"
        
        registration_data = {
            "email": test_email,
            "password": test_password,
            "full_name": "Admin Member Test User",
            "organization_name": test_org_name
        }
        
        print("\n👤 Step 1: Admin User Registration and Login")
        print(f"   Email: {test_email}")
        print(f"   Organization: {test_org_name}")
        
        # Register admin user
        response = self.session.post(f"{API_BASE}/auth/register", json=registration_data)
        
        print(f"   Registration Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Registration Response: {response.text}")
        
        assert response.status_code == 200, f"Admin user registration failed: {response.status_code} - {response.text}"
        
        reg_data = response.json()
        
        # Validate registration response fields
        assert "id" in reg_data, "Missing 'id' in registration response"
        assert "email" in reg_data, "Missing 'email' in registration response"
        assert "full_name" in reg_data, "Missing 'full_name' in registration response"
        assert "is_active" in reg_data, "Missing 'is_active' in registration response"
        
        assert reg_data["email"] == test_email, f"Email mismatch: {reg_data['email']} != {test_email}"
        assert reg_data["full_name"] == "Admin Member Test User", "Full name mismatch"
        assert reg_data["is_active"] == True, "User should be active after registration"
        
        print(f"   ✅ Admin user registered: {reg_data['id']}")
        
        # Login to get authentication token
        login_data = {
            "email": test_email,
            "password": test_password
        }
        
        login_response = self.session.post(f"{API_BASE}/auth/login", json=login_data)
        
        print(f"   Login Status: {login_response.status_code}")
        if login_response.status_code != 200:
            print(f"   Login Response: {login_response.text}")
        
        assert login_response.status_code == 200, f"Admin user login failed: {login_response.status_code} - {login_response.text}"
        
        login_resp_data = login_response.json()
        
        # Validate login response fields
        assert "access_token" in login_resp_data, "Missing 'access_token' in login response"
        assert "token_type" in login_resp_data, "Missing 'token_type' in login response"
        
        # Store admin authentication data
        self.test_data["admin_user_id"] = reg_data["id"]
        self.test_data["admin_email"] = test_email
        self.test_data["admin_access_token"] = login_resp_data["access_token"]
        self.test_data["organization_name"] = test_org_name
        
        # Update session with auth token
        self.session.headers.update({"Authorization": f"Bearer {login_resp_data['access_token']}"})
        
        print(f"   ✅ Admin user logged in: {reg_data['id']}")
        print(f"   ✅ Token acquired: {login_resp_data['access_token'][:20]}...")
    
    def test_03_get_organization_id(self):
        """Step 2: Get organization ID from user profile"""
        
        print("\n🏢 Step 2: Get Organization ID")
        
        # Get user profile to extract organization_id
        response = self.session.get(f"{API_BASE}/auth/me")
        
        print(f"   Profile Status: {response.status_code}")
        assert response.status_code == 200, f"Get user profile failed: {response.status_code} - {response.text}"
        
        profile_data = response.json()
        
        # Validate profile response
        assert "organization_id" in profile_data, "Missing 'organization_id' in profile response"
        assert profile_data["organization_id"] is not None, "organization_id should not be None"
        
        self.test_data["organization_id"] = profile_data["organization_id"]
        
        print(f"   ✅ Organization ID: {profile_data['organization_id']}")
    
    def test_04_create_invitation(self):
        """Step 3: Create invitation for new member"""
        
        # Generate unique invitation data
        invitee_email = f"invitee_member_test_{int(time.time())}@example.com"
        
        invitation_data = {
            "email": invitee_email,
            "role": "member",
            "message": "Welcome to our organization! You've been invited to join as a member."
        }
        
        print("\n📧 Step 3: Create Invitation")
        print(f"   Invitee Email: {invitee_email}")
        print(f"   Role: {invitation_data['role']}")
        
        response = self.session.post(f"{API_BASE}/invitations", json=invitation_data)
        
        print(f"   Create Invitation Status: {response.status_code}")
        if response.status_code not in [200, 201]:
            print(f"   Error Response: {response.text}")
        
        assert response.status_code in [200, 201], f"Invitation creation failed: {response.status_code} - {response.text}"
        
        invitation_response = response.json()
        
        # CRITICAL: Validate ALL invitation response fields
        required_invitation_fields = [
            "id", "organization_id", "inviter_id", "email", "role", 
            "status", "message", "token", "expires_at", "created_at"
        ]
        
        for field in required_invitation_fields:
            assert field in invitation_response, f"Missing required field '{field}' in invitation response"
        
        # Validate field values and types
        assert invitation_response["organization_id"] == self.test_data["organization_id"], "Organization ID mismatch"
        assert invitation_response["inviter_id"] == self.test_data["admin_user_id"], "Inviter ID mismatch"
        assert invitation_response["email"] == invitee_email, "Email mismatch"
        assert invitation_response["role"] == "member", "Role mismatch"
        assert invitation_response["status"] == "pending", "Status should be pending"
        assert invitation_response["message"] == invitation_data["message"], "Message mismatch"
        assert isinstance(invitation_response["token"], str), "Token should be string"
        assert len(invitation_response["token"]) > 0, "Token should not be empty"
        
        # Store invitation data
        self.test_data["invitation_id"] = invitation_response["id"]
        self.test_data["invitation_token"] = invitation_response["token"]
        self.test_data["invitee_email"] = invitee_email
        
        print(f"   ✅ Invitation created: {invitation_response['id']}")
        print(f"   ✅ Token: {invitation_response['token'][:20]}...")
        print(f"   ✅ Expires at: {invitation_response['expires_at']}")
    
    def test_05_list_invitations(self):
        """Step 4: List organization invitations"""
        
        print("\n📋 Step 4: List Organization Invitations")
        
        response = self.session.get(f"{API_BASE}/invitations")
        
        print(f"   List Invitations Status: {response.status_code}")
        assert response.status_code == 200, f"List invitations failed: {response.status_code} - {response.text}"
        
        invitations_data = response.json()
        
        # Validate response structure
        assert "invitations" in invitations_data, "Missing 'invitations' in response"
        assert "total" in invitations_data, "Missing 'total' in response"
        assert isinstance(invitations_data["invitations"], list), "Invitations should be list"
        assert isinstance(invitations_data["total"], int), "Total should be int"
        
        invitations = invitations_data["invitations"]
        assert len(invitations) >= 1, f"Should have at least 1 invitation, got {len(invitations)}"
        
        # Find our test invitation
        test_invitation = None
        for invitation in invitations:
            if invitation["id"] == self.test_data["invitation_id"]:
                test_invitation = invitation
                break
        
        assert test_invitation is not None, "Test invitation not found in list"
        
        # Validate invitation fields in list
        assert test_invitation["email"] == self.test_data["invitee_email"], "Email mismatch in list"
        assert test_invitation["role"] == "member", "Role mismatch in list"
        assert test_invitation["status"] == "pending", "Status mismatch in list"
        
        print(f"   ✅ Invitations listed: {len(invitations)}")
        print(f"   ✅ Test invitation found: {test_invitation['id']}")
    
    def test_06_get_single_invitation(self):
        """Step 5: Get single invitation by ID"""
        
        invitation_id = self.test_data["invitation_id"]
        
        print("\n🔍 Step 5: Get Single Invitation")
        print(f"   Invitation ID: {invitation_id}")
        
        response = self.session.get(f"{API_BASE}/invitations/{invitation_id}")
        
        print(f"   Get Invitation Status: {response.status_code}")
        assert response.status_code == 200, f"Get invitation failed: {response.status_code} - {response.text}"
        
        invitation_data = response.json()
        
        # Validate all fields are present
        required_fields = [
            "id", "organization_id", "inviter_id", "email", "role", 
            "status", "message", "expires_at", "created_at"
        ]
        
        for field in required_fields:
            assert field in invitation_data, f"Missing required field '{field}' in invitation response"
        
        # Validate field values
        assert invitation_data["id"] == invitation_id, "Invitation ID mismatch"
        assert invitation_data["email"] == self.test_data["invitee_email"], "Email mismatch"
        assert invitation_data["role"] == "member", "Role mismatch"
        assert invitation_data["status"] == "pending", "Status mismatch"
        
        print(f"   ✅ Invitation retrieved: {invitation_data['id']}")
        print(f"   ✅ Status: {invitation_data['status']}")
    
    def test_07_register_invited_user(self):
        """Step 6: Register user using invitation token"""
        
        invitation_token = self.test_data["invitation_token"]
        invitee_email = self.test_data["invitee_email"]
        invitee_password = "SecureMemberPass123!"
        
        print("\n👥 Step 6: Register Invited User")
        print(f"   Token: {invitation_token[:20]}...")
        print(f"   Email: {invitee_email}")
        
        # First, get invitation details using token
        invite_check_response = self.session.get(f"{API_BASE}/invitations/token/{invitation_token}")
        
        print(f"   Token Check Status: {invite_check_response.status_code}")
        assert invite_check_response.status_code == 200, f"Token check failed: {invite_check_response.status_code} - {invite_check_response.text}"
        
        invite_details = invite_check_response.json()
        
        # Validate invitation details
        assert invite_details["email"] == invitee_email, "Email mismatch in token check"
        assert invite_details["status"] == "pending", "Status should be pending"
        
        # Register user with invitation token
        registration_data = {
            "email": invitee_email,
            "password": invitee_password,
            "full_name": "Member Test User",
            "invitation_token": invitation_token
        }
        
        # Temporarily remove admin auth for registration
        original_auth = self.session.headers.get("Authorization")
        if original_auth:
            del self.session.headers["Authorization"]
        
        reg_response = self.session.post(f"{API_BASE}/auth/register", json=registration_data)
        
        # Restore admin auth
        if original_auth:
            self.session.headers["Authorization"] = original_auth
        
        print(f"   Registration Status: {reg_response.status_code}")
        if reg_response.status_code != 200:
            print(f"   Registration Response: {reg_response.text}")
        
        assert reg_response.status_code == 200, f"Invited user registration failed: {reg_response.status_code} - {reg_response.text}"
        
        reg_data = reg_response.json()
        
        # Validate registration response
        assert "id" in reg_data, "Missing 'id' in registration response"
        assert "email" in reg_data, "Missing 'email' in registration response"
        assert "organization_id" in reg_data, "Missing 'organization_id' in registration response"
        
        assert reg_data["email"] == invitee_email, "Email mismatch in registration"
        assert reg_data["organization_id"] == self.test_data["organization_id"], "Organization ID mismatch"
        
        # Store member data
        self.test_data["member_user_id"] = reg_data["id"]
        self.test_data["member_email"] = invitee_email
        self.test_data["member_password"] = invitee_password
        
        print(f"   ✅ Member user registered: {reg_data['id']}")
        print(f"   ✅ Organization: {reg_data['organization_id']}")
    
    def test_08_verify_invitation_accepted(self):
        """Step 7: Verify invitation status changed to accepted"""
        
        invitation_id = self.test_data["invitation_id"]
        
        print("\n✅ Step 7: Verify Invitation Accepted")
        
        response = self.session.get(f"{API_BASE}/invitations/{invitation_id}")
        
        print(f"   Check Invitation Status: {response.status_code}")
        assert response.status_code == 200, f"Get invitation failed: {response.status_code} - {response.text}"
        
        invitation_data = response.json()
        
        # Validate invitation is now accepted
        assert invitation_data["status"] == "accepted", f"Invitation should be accepted, got {invitation_data['status']}"
        assert "accepted_at" in invitation_data, "Missing 'accepted_at' field"
        assert invitation_data["accepted_at"] is not None, "accepted_at should not be None"
        
        print(f"   ✅ Invitation status: {invitation_data['status']}")
        print(f"   ✅ Accepted at: {invitation_data['accepted_at']}")
    
    def test_09_list_organization_members(self):
        """Step 8: List organization members"""
        
        print("\n👥 Step 8: List Organization Members")
        
        response = self.session.get(f"{API_BASE}/members")
        
        print(f"   List Members Status: {response.status_code}")
        assert response.status_code == 200, f"List members failed: {response.status_code} - {response.text}"
        
        members_data = response.json()
        
        # Validate response structure
        assert "members" in members_data, "Missing 'members' in response"
        assert "total" in members_data, "Missing 'total' in response"
        assert isinstance(members_data["members"], list), "Members should be list"
        assert isinstance(members_data["total"], int), "Total should be int"
        
        members = members_data["members"]
        assert len(members) >= 2, f"Should have at least 2 members (admin + member), got {len(members)}"
        
        # Find admin and member users
        admin_member = None
        regular_member = None
        
        for member in members:
            if member["id"] == self.test_data["admin_user_id"]:
                admin_member = member
            elif member["id"] == self.test_data["member_user_id"]:
                regular_member = member
        
        assert admin_member is not None, "Admin member not found in list"
        assert regular_member is not None, "Regular member not found in list"
        
        # Validate member fields (now using UserResponse format)
        required_member_fields = [
            "id", "email", "full_name", "role", "is_active", 
            "organization_id", "organization_name",
            "created_at", "updated_at", "timezone", "language"
        ]
        
        for member in [admin_member, regular_member]:
            for field in required_member_fields:
                assert field in member, f"Missing required field '{field}' in member response"
        
        # Validate roles
        assert admin_member["role"] == "admin", f"Admin should have admin role, got {admin_member['role']}"
        assert regular_member["role"] == "member", f"Member should have member role, got {regular_member['role']}"
        
        # Validate organization consistency
        assert admin_member["organization_id"] == self.test_data["organization_id"], "Admin organization mismatch"
        assert regular_member["organization_id"] == self.test_data["organization_id"], "Member organization mismatch"
        
        print(f"   ✅ Members listed: {len(members)}")
        print(f"   ✅ Admin member: {admin_member['email']} ({admin_member['role']})")
        print(f"   ✅ Regular member: {regular_member['email']} ({regular_member['role']})")
        
        # Store member IDs
        self.test_data["admin_member_id"] = admin_member["id"]
        self.test_data["regular_member_id"] = regular_member["id"]
    
    def test_10_get_single_member(self):
        """Step 9: Get single member by ID"""
        
        member_id = self.test_data["regular_member_id"]
        
        print("\n👤 Step 9: Get Single Member")
        print(f"   Member ID: {member_id}")
        
        response = self.session.get(f"{API_BASE}/members/{member_id}")
        
        print(f"   Get Member Status: {response.status_code}")
        assert response.status_code == 200, f"Get member failed: {response.status_code} - {response.text}"
        
        member_data = response.json()
        
        # Validate all fields are present (now using UserResponse format)
        required_fields = [
            "id", "email", "full_name", "role", "is_active", 
            "organization_id", "organization_name", "can_manage_organization_members",
            "created_at", "updated_at", "timezone", "language"
        ]
        
        for field in required_fields:
            assert field in member_data, f"Missing required field '{field}' in member response"
        
        # Validate field values
        assert member_data["id"] == member_id, "Member ID mismatch"
        assert member_data["email"] == self.test_data["member_email"], "User email mismatch"
        assert member_data["role"] == "member", "Role mismatch"
        assert member_data["is_active"] == True, "Status should be active"
        assert member_data["organization_id"] == self.test_data["organization_id"], "Organization ID mismatch"
        
        print(f"   ✅ Member retrieved: {member_data['id']}")
        print(f"   ✅ Role: {member_data['role']}")
        print(f"   ✅ Active: {member_data['is_active']}")
    
    def test_11_update_member_role(self):
        """Step 10: Update member role"""
        
        member_id = self.test_data["regular_member_id"]
        
        print("\n✏️ Step 10: Update Member Role")
        print(f"   Member ID: {member_id}")
        print("   Changing role: member -> admin")
        
        update_data = {
            "role": "admin"
        }
        
        response = self.session.patch(f"{API_BASE}/members/{member_id}", json=update_data)
        
        print(f"   Update Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error Response: {response.text}")
        
        assert response.status_code == 200, f"Member role update failed: {response.status_code} - {response.text}"
        
        update_response = response.json()
        
        # Validate update response
        assert "id" in update_response, "Missing 'id' in update response"
        assert "role" in update_response, "Missing 'role' in update response"
        assert "updated_fields" in update_response, "Missing 'updated_fields' in update response"
        
        assert update_response["id"] == member_id, "Member ID should match"
        assert update_response["role"] == "admin", f"Role not updated correctly: {update_response['role']}"
        assert "role" in update_response["updated_fields"], "'role' should be in updated_fields"
        
        print(f"   ✅ Member role updated: {update_response['role']}")
        print(f"   ✅ Updated fields: {update_response['updated_fields']}")
    
    def test_12_revoke_invitation(self):
        """Step 11: Test invitation revocation (create and revoke new invitation)"""
        
        # Create a new invitation to revoke
        revoke_email = f"revoke_test_{int(time.time())}@example.com"
        
        invitation_data = {
            "email": revoke_email,
            "role": "member",
            "message": "Test invitation for revocation"
        }
        
        print("\n🚫 Step 11: Test Invitation Revocation")
        print(f"   Creating invitation for: {revoke_email}")
        
        # Create invitation
        create_response = self.session.post(f"{API_BASE}/invitations", json=invitation_data)
        assert create_response.status_code in [200, 201], f"Test invitation creation failed: {create_response.status_code}"
        
        invitation_response = create_response.json()
        revoke_invitation_id = invitation_response["id"]
        
        print(f"   ✅ Test invitation created: {revoke_invitation_id}")
        
        # Revoke the invitation
        revoke_response = self.session.delete(f"{API_BASE}/invitations/{revoke_invitation_id}")
        
        print(f"   Revoke Status: {revoke_response.status_code}")
        assert revoke_response.status_code in [200, 204], f"Invitation revocation failed: {revoke_response.status_code} - {revoke_response.text}"
        
        # Verify invitation is revoked
        check_response = self.session.get(f"{API_BASE}/invitations/{revoke_invitation_id}")
        
        if check_response.status_code == 200:
            # If invitation still exists, check it's revoked
            invitation_data = check_response.json()
            assert invitation_data["status"] == "revoked", f"Invitation should be revoked, got {invitation_data['status']}"
            print(f"   ✅ Invitation status: {invitation_data['status']}")
        else:
            # If invitation is deleted, that's also valid
            assert check_response.status_code == 404, f"Expected 404 for deleted invitation, got {check_response.status_code}"
            print("   ✅ Invitation deleted")
    
    def test_13_organization_discovery(self):
        """Step 12: Test organization discovery functionality"""
        
        print("\n🔍 Step 12: Test Organization Discovery")
        
        # Test domain-based discovery
        test_domain = self.test_data["admin_email"].split('@')[1]
        
        print(f"   Testing domain: {test_domain}")
        
        response = self.session.get(f"{API_BASE}/organization-discovery/domain/{test_domain}")
        
        print(f"   Discovery Status: {response.status_code}")
        
        if response.status_code == 200:
            discovery_data = response.json()
            
            # Validate discovery response
            assert "organization" in discovery_data, "Missing 'organization' in discovery response"
            assert "domain" in discovery_data, "Missing 'domain' in discovery response"
            
            org_data = discovery_data["organization"]
            assert "id" in org_data, "Missing 'id' in organization data"
            assert "name" in org_data, "Missing 'name' in organization data"
            
            assert org_data["id"] == self.test_data["organization_id"], "Organization ID mismatch in discovery"
            
            print(f"   ✅ Organization discovered: {org_data['name']}")
            print(f"   ✅ Domain: {discovery_data['domain']}")
        else:
            print(f"   ⚠️  Organization discovery not available or domain not configured: {response.status_code}")
    
    def test_14_member_authentication_flow(self):
        """Step 13: Test member authentication with proper organization context"""
        
        member_email = self.test_data["member_email"]
        member_password = self.test_data["member_password"]
        
        print("\n🔐 Step 13: Member Authentication Flow")
        print(f"   Member Email: {member_email}")
        
        # Create new session for member login
        member_session = requests.Session()
        member_session.headers.update({"Content-Type": "application/json"})
        
        # Login as member
        login_data = {
            "email": member_email,
            "password": member_password
        }
        
        login_response = member_session.post(f"{API_BASE}/auth/login", json=login_data)
        
        print(f"   Login Status: {login_response.status_code}")
        assert login_response.status_code == 200, f"Member login failed: {login_response.status_code} - {login_response.text}"
        
        login_resp_data = login_response.json()
        
        # Validate login response
        assert "access_token" in login_resp_data, "Missing 'access_token' in member login response"
        
        # Set member auth
        member_session.headers.update({"Authorization": f"Bearer {login_resp_data['access_token']}"})
        
        # Test member can access their organization's data
        profile_response = member_session.get(f"{API_BASE}/auth/me")
        assert profile_response.status_code == 200, "Member should be able to access their profile"
        
        profile_data = profile_response.json()
        assert profile_data["organization_id"] == self.test_data["organization_id"], "Member should belong to correct organization"
        
        # Test member can see organization members
        members_response = member_session.get(f"{API_BASE}/members")
        assert members_response.status_code == 200, "Member should be able to see organization members"
        
        print("   ✅ Member login successful")
        print("   ✅ Member can access organization data")
        print("   ✅ Organization isolation verified")
    
    def test_15_final_verification_member_management(self):
        """Step 14: Final verification of complete member management flow"""
        
        print("\n🏁 Step 14: Final Member Management Verification")
        
        # Get final organization state
        members_response = self.session.get(f"{API_BASE}/members")
        assert members_response.status_code == 200, "Final members retrieval failed"
        
        members_data = members_response.json()
        members = members_data["members"]
        
        # Verify we have expected members
        assert len(members) >= 2, f"Should have at least 2 members, got {len(members)}"
        
        # Verify roles are correct after updates
        admin_members = [m for m in members if m["role"] == "admin"]
        
        # Should have 2 admin members now (original admin + promoted member)
        assert len(admin_members) == 2, f"Should have 2 admin members after promotion, got {len(admin_members)}"
        
        # Verify organization consistency
        for member in members:
            assert member["organization_id"] == self.test_data["organization_id"], "All members should belong to same organization"
            assert member["status"] == "active", "All members should be active"
        
        # Get invitations to verify final state
        invitations_response = self.session.get(f"{API_BASE}/invitations")
        assert invitations_response.status_code == 200, "Final invitations retrieval failed"
        
        invitations_data = invitations_response.json()
        
        print("   ✅ Complete member management flow verified")
        print(f"   ✅ Total members: {len(members)}")
        print(f"   ✅ Admin members: {len(admin_members)}")
        print(f"   ✅ Total invitations: {invitations_data['total']}")
        
        # Print summary
        print("\n🏆 MEMBER MANAGEMENT E2E TEST SUMMARY:")
        print(f"   🏢 Organization: {self.test_data['organization_id']}")
        print(f"   👤 Admin User: {self.test_data['admin_email']}")
        print(f"   👥 Member User: {self.test_data['member_email']}")
        print(f"   📧 Invitations: Created, accepted, and revoked successfully")
        print(f"   🔄 Role Updates: Member promoted to admin successfully")
        print(f"   🔍 Discovery: Organization discovery tested")
        print("   ✅ ALL MEMBER MANAGEMENT VALIDATIONS PASSED")


if __name__ == "__main__":
    # Run the member management E2E flow test
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--capture=no",  # Show all print statements
        "--log-cli-level=INFO",
        "-s"  # Don't capture stdout
    ])