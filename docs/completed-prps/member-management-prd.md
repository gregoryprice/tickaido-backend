# Member Management System - Product Requirements Document (PRD)

## Overview

This PRD outlines the implementation of a comprehensive member management system for the AI Ticket Creator platform. The system will enable organizations to manage user memberships, handle invitations, implement role-based access control, and provide intelligent organization matching during user registration.

## Problem Statement

Currently, the system has a basic user-organization relationship where users can belong to one organization. However, there's no robust member management system that handles:

1. **Member invitation and onboarding workflows**
2. **Role-based access control within organizations** 
3. **Organization discovery and matching during registration**
4. **Member transfer between organizations**
5. **Bulk member management operations**

## Goals

### Primary Goals
- Enable organizations to invite and manage members with specific roles
- Implement intelligent organization matching to reduce duplicate organizations
- Provide seamless member onboarding experience
- Support member role management and transfers
- Maintain security and data isolation between organizations

### Secondary Goals  
- Reduce administrative overhead for organization setup
- Improve user experience during registration
- Enable bulk operations for large organizations
- Provide audit trails for member management actions

## Success Metrics

- **Registration Accuracy**: 95% reduction in duplicate/misspelled organizations
- **Member Onboarding Time**: < 2 minutes from invitation to active membership
- **API Response Time**: < 500ms for all member management endpoints
- **User Satisfaction**: 90%+ satisfaction with invitation and onboarding flow

## Data Model Changes

### 1. Enhanced User Model

Update the existing `User` model to include organization membership fields:

```python
class OrganizationRole(enum.Enum):
    ADMIN = "admin"        # Full organization management  
    MEMBER = "member"      # Standard member access

# Add to existing User model:
class User(BaseModel):
    # ... existing fields ...
    
    # Organization membership (enhanced)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey('organizations.id'),
        nullable=True,  # Users can exist without organization during invitation
        index=True
    )
    
    organization_role = Column(
        SQLEnum(OrganizationRole),
        default=OrganizationRole.MEMBER,
        nullable=True,  # Null when not part of any organization
        comment="Role within the user's organization"
    )
    
    # Membership tracking
    invited_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=True,
        comment="User who invited this member"
    )
    
    invited_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When user was invited to organization"
    )
    
    joined_organization_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When user joined the organization"
    )
    
    # Enhanced relationships
    organization = relationship("Organization", back_populates="users")
    invited_by = relationship("User", remote_side="User.id")
```

### 2. Invitation System

Create `OrganizationInvitation` model:

```python
class InvitationStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted" 
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class OrganizationInvitation(BaseModel):
    __tablename__ = "organization_invitations"
    
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'))
    email = Column(String(255), nullable=False, index=True)
    role = Column(SQLEnum(OrganizationRole), default=OrganizationRole.MEMBER)
    
    invited_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    invitation_token = Column(String(255), unique=True, index=True)
    status = Column(SQLEnum(InvitationStatus), default=InvitationStatus.PENDING)
    
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 7 days default
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    organization = relationship("Organization")
    invited_by = relationship("User")
```

### 3. Model Updates

**User Model Changes:**
- Enhance existing `organization_id` with role and membership tracking fields
- Add `organization_role`, `invited_by_id`, `invited_at`, `joined_organization_at` columns
- Maintain one-to-many relationship (user belongs to one organization)

**Organization Model Changes:**
- Keep existing users relationship (one-to-many)
- Add member-related helper methods for role management
- Add methods to count admins vs members

## API Endpoints Specification

### 1. Organization Members Management

#### GET `/api/v1/organizations/{org_id}/members/`
**Purpose**: Get all members of an organization

**Query Parameters:**
- `role` (optional): Filter by role (admin, member)
- `active` (optional): Filter by active status (true/false)
- `page` (optional): Pagination page number
- `limit` (optional): Results per page (max 100)

**Response:**
```json
{
  "data": [
    {
      "id": "user-uuid",
      "email": "user@example.com",
      "full_name": "John Doe",
      "organization_role": "admin",
      "joined_organization_at": "2024-01-15T10:30:00Z",
      "invited_by": {
        "id": "inviter-uuid",
        "email": "admin@example.com",
        "full_name": "Admin User"
      },
      "is_active": true
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 25,
    "pages": 1
  }
}
```

#### POST `/api/v1/organizations/{org_id}/members/invite`
**Purpose**: Invite new members to organization

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "role": "member",
  "send_email": true
}
```

**Response:**
```json
{
  "invitation_id": "invitation-uuid",
  "email": "newuser@example.com",
  "role": "member",
  "invitation_url": "https://app.example.com/invitations/accept/token-here",
  "expires_at": "2024-01-22T10:30:00Z"
}
```

#### PUT `/api/v1/organizations/{org_id}/members/{user_id}/role`
**Purpose**: Update member role (Admin only, cannot change own role)

**Request Body:**
```json
{
  "organization_role": "admin"
}
```

**Validation:**
- Only Admin users can call this endpoint
- Cannot change own role (prevents accidental lockout)
- Target user must belong to the same organization

#### DELETE `/api/v1/organizations/{org_id}/members/{user_id}`
**Purpose**: Remove member from organization

**Business Rules:**
- Cannot delete user if they are the only member (must delete organization instead)
- If user being deleted is Admin and only one member remains, remaining member becomes Admin
- Admin users required to remove members

#### DELETE `/api/v1/users/{user_id}`
**Purpose**: Delete user account entirely

**Business Rules:**
- If user is only member of organization, must provide `delete_organization=true` parameter
- If user is Admin and other members exist, one remaining member is auto-promoted to Admin
- Soft delete with audit trail

### 2. Organization Discovery

#### GET `/api/v1/organizations/by-domain/{domain}`
**Purpose**: Find organization by email domain (for registration matching)

**Authentication**: None required (public endpoint for registration flow)

**Rate Limiting**: 100 requests per IP per hour

**Path Parameters:**
- `domain`: Email domain to search for (e.g., "example.com")

**Response:**
```json
{
  "organization": {
    "id": "org-uuid",
    "name": "Example Inc.",
    "domain": "example.com", 
    "member_count": 25,
    "display_name": "Example Inc."
  }
}
```

**Status Codes:**
- `200`: Organization found
- `404`: No organization with this domain
- `429`: Rate limit exceeded (too many requests from IP)

#### GET `/api/v1/organizations/directory`
**Purpose**: Get list of all active organizations (admin only)

**Query Parameters:**
- `page`, `limit`: Pagination
- `search`: Filter by name/domain

### 3. Member Transfer

#### PUT `/api/v1/users/{user_id}/organization`
**Purpose**: Transfer user to different organization

**Request Body:**
```json
{
  "organization_id": "new-org-uuid",
  "organization_role": "member",
  "reason": "Organization restructure"
}
```

### 4. Invitation Management

#### GET `/api/v1/invitations/{token}`
**Purpose**: Get invitation details (public endpoint)

#### POST `/api/v1/invitations/{token}/accept`
**Purpose**: Accept invitation and create/link user account

**Request Body:**
```json
{
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

#### POST `/api/v1/invitations/{token}/decline`
**Purpose**: Decline invitation

#### GET `/api/v1/organizations/{org_id}/invitations`
**Purpose**: List pending invitations for organization

#### DELETE `/api/v1/organizations/{org_id}/invitations/{invitation_id}`
**Purpose**: Cancel pending invitation

## Enhanced Registration Flow

### Domain-Based Organization Matching

The system uses email domains as the primary method for organization discovery:

1. **Extract Domain**: Extract domain from user's email address (e.g., `user@example.com` → `example.com`)
2. **Domain Match**: Check if any organization has this domain in their `domain` field
3. **Present Options**: If match found, present user with choice to join existing organization or create new one
4. **No Fuzzy Matching**: No name-based searching or fuzzy matching - only exact domain matches

### Registration Workflows

#### Workflow 1: First User (New Organization)
1. User registers with email `admin@example.com`
2. System checks for existing organizations with domain `example.com`
3. No match found → User creates new organization
4. User automatically becomes **Admin** of new organization
5. Organization's `domain` field set to `example.com`

#### Workflow 2: Subsequent Users (Join Existing)
1. User registers with email `user@example.com` 
2. System finds existing organization with domain `example.com`
3. Frontend presents options:
   - "Join Example Inc. organization" 
   - "Create new organization"
4. If user chooses to join → User becomes **Member** of existing organization
5. If user chooses new org → Creates separate organization (duplicate domains allowed)

#### Workflow 3: Admin Management
- New users joining existing organization default to **Member** role
- Only **Admin** users can promote Members to Admin
- Multiple Admins are allowed per organization
- **Self-Role Restriction**: Users cannot change their own role (prevents accidental lockout)

## Validation Requirements

### Input Validation
- **Email Format**: RFC 5322 compliant email validation
- **Organization Names**: 3-255 characters, no special characters except spaces, hyphens, apostrophes
- **Role Validation**: Must be valid OrganizationRole enum value
- **UUID Validation**: All ID parameters must be valid UUIDs

### Business Logic Validation
- **Duplicate Invitations**: Prevent multiple pending invitations for same email/organization
- **Self-Invitation**: Users cannot invite themselves
- **Role Permissions**: Only admins can modify user roles or invite members
- **Self-Role Change**: Users cannot change their own role (prevents lockout)
- **Last Admin Protection**: Cannot delete or demote the last admin if they're the only member
- **Organization Limits**: Respect plan-based member limits
- **Active Organization**: Can only invite to active/enabled organizations
- **Single Organization Constraint**: Users can only belong to one organization at a time
- **Domain Matching**: Organization matching only by exact domain match, no fuzzy search

### Security Validation
- **Authorization**: Users can only manage members for organizations they have admin access to
- **Invitation Tokens**: Secure random tokens with expiration (7 days)
- **Rate Limiting**: 
  - Domain lookup endpoint: 100 requests/hour per IP (unauthenticated)
  - Invitation endpoints: 20 requests/hour per organization
  - Member management endpoints: 100 requests/hour per user
- **CSRF Protection**: All state-changing endpoints require CSRF tokens
- **Public Endpoint Security**: Domain lookup endpoint has no sensitive data exposure

## Security Considerations

### Access Control
- **Organization Admins**: Can invite members, change roles (except own), remove members
- **Members**: Can view other members in same organization, cannot manage memberships
- **Cross-Organization Isolation**: Users cannot access members of other organizations
- **Self-Management Restriction**: Users cannot modify their own role (prevents accidental lockout)
- **Last Member Protection**: Cannot delete sole remaining member without deleting organization
- **Auto-Admin Promotion**: If last admin is removed, remaining member auto-promoted to admin
- **System Admins**: Can perform any operation (audit logging required)

### Data Protection
- **Invitation Tokens**: Single-use, time-limited, cryptographically secure
- **Audit Logging**: Log all membership changes with user, timestamp, action
- **Data Minimization**: Only return necessary member information
- **Soft Deletes**: Maintain membership history for audit purposes

### Privacy Considerations
- **Email Privacy**: Don't expose member emails to non-admin users
- **Member Directory**: Optional feature that organizations can disable
- **Invitation Privacy**: Invitation details only visible to inviter and invitee

## Error Handling

### HTTP Status Codes
- **200**: Success with data
- **201**: Resource created successfully
- **400**: Invalid request data
- **401**: Authentication required
- **403**: Insufficient permissions
- **404**: Resource not found
- **409**: Conflict (duplicate invitation, etc.)
- **422**: Validation error
- **429**: Rate limit exceeded
- **500**: Internal server error

### Error Response Format
```json
{
  "error": {
    "code": "INVALID_ROLE",
    "message": "Invalid role specified for organization member",
    "details": {
      "field": "role",
      "allowed_values": ["admin", "member"]
    }
  }
}
```

## Comprehensive Testing Strategy

### Step-by-Step Test Scenarios

#### Scenario 1: First User Registration (New Organization)

**Test Steps:**
1. User registers with email `admin@newcompany.com`
2. System extracts domain `newcompany.com`
3. Domain lookup finds no existing organization
4. User creates organization "New Company Inc"
5. User automatically assigned Admin role

**Required PyTests:**

```python
def test_first_user_registration_creates_admin():
    """Test that first user becomes admin of new organization"""
    # Given: No organization exists for domain
    assert Organization.query.filter_by(domain="newcompany.com").first() is None
    
    # When: User registers and creates organization
    user_data = {"email": "admin@newcompany.com", "password": "secure123"}
    org_data = {"name": "New Company Inc", "domain": "newcompany.com"}
    
    user = create_user_and_organization(user_data, org_data)
    
    # Then: User is admin, organization created
    assert user.organization_role == OrganizationRole.ADMIN
    assert user.organization.domain == "newcompany.com"
    assert user.organization.users.count() == 1

def test_domain_extraction_from_email():
    """Test email domain extraction logic"""
    # Test cases
    test_cases = [
        ("user@example.com", "example.com"),
        ("test.user@subdomain.company.co.uk", "subdomain.company.co.uk"),
        ("admin@localhost", "localhost"),
    ]
    
    for email, expected_domain in test_cases:
        assert extract_domain_from_email(email) == expected_domain

def test_organization_domain_uniqueness_not_required():
    """Test that multiple organizations can have same domain"""
    # Given: Organization exists with domain
    org1 = create_organization("Company A", "example.com")
    
    # When: Another organization created with same domain
    org2 = create_organization("Company B", "example.com")
    
    # Then: Both organizations exist
    assert org1.id != org2.id
    assert org1.domain == org2.domain == "example.com"
```

#### Scenario 2: Subsequent User Registration (Join Existing)

**Test Steps:**
1. User registers with email `member@newcompany.com`
2. System finds existing organization with domain `newcompany.com`
3. Frontend presents join/create options
4. User chooses to join existing organization
5. User assigned Member role

**Required PyTests:**

```python
def test_subsequent_user_joins_as_member():
    """Test that subsequent users join as members"""
    # Given: Organization exists with admin
    admin_user = create_user_with_organization("admin@example.com", "Example Inc")
    
    # When: New user registers with same domain
    member_data = {"email": "member@example.com", "password": "secure123"}
    member_user = create_user_join_organization(member_data, admin_user.organization_id)
    
    # Then: User is member of existing organization
    assert member_user.organization_role == OrganizationRole.MEMBER
    assert member_user.organization_id == admin_user.organization_id
    assert member_user.organization.users.count() == 2

def test_domain_lookup_endpoint_unauthenticated():
    """Test domain lookup works without authentication"""
    # Given: Organization exists
    org = create_organization("Test Company", "testdomain.com")
    
    # When: Unauthenticated request to domain endpoint
    response = client.get("/api/v1/organizations/by-domain/testdomain.com")
    
    # Then: Returns organization data
    assert response.status_code == 200
    data = response.json()
    assert data["organization"]["domain"] == "testdomain.com"
    assert data["organization"]["name"] == "Test Company"

def test_domain_lookup_rate_limiting():
    """Test rate limiting on domain lookup endpoint"""
    # When: Make 101 requests from same IP
    for i in range(101):
        response = client.get("/api/v1/organizations/by-domain/test.com")
        if i < 100:
            assert response.status_code in [200, 404]  # Normal responses
    
    # Then: 101st request should be rate limited
    assert response.status_code == 429
```

#### Scenario 3: Admin Promotes Member to Admin

**Test Steps:**
1. Admin user calls PUT `/api/v1/organizations/{org_id}/members/{user_id}/role`
2. System validates admin permissions
3. System validates target user belongs to same organization
4. System validates admin is not changing own role
5. Member promoted to Admin role

**Required PyTests:**

```python
def test_admin_promotes_member_to_admin():
    """Test admin can promote member to admin"""
    # Given: Organization with admin and member
    admin = create_user_with_organization("admin@example.com", "Example Inc")
    member = create_user_join_organization({"email": "member@example.com"}, admin.organization_id)
    
    # When: Admin promotes member
    response = client.put(
        f"/api/v1/organizations/{admin.organization_id}/members/{member.id}/role",
        json={"organization_role": "admin"},
        headers=auth_headers(admin)
    )
    
    # Then: Member becomes admin
    assert response.status_code == 200
    member.refresh_from_db()
    assert member.organization_role == OrganizationRole.ADMIN

def test_multiple_admins_allowed():
    """Test organization can have multiple admins"""
    # Given: Organization with 2 admins
    admin1 = create_user_with_organization("admin1@example.com", "Example Inc")
    admin2 = create_user_join_organization({"email": "admin2@example.com"}, admin1.organization_id)
    promote_user_to_admin(admin2, admin1.organization_id)
    
    # Then: Both users are admins
    assert admin1.organization_role == OrganizationRole.ADMIN
    assert admin2.organization_role == OrganizationRole.ADMIN
    
    # And: Both can perform admin operations
    member = create_user_join_organization({"email": "member@example.com"}, admin1.organization_id)
    assert can_manage_members(admin1, admin1.organization_id)
    assert can_manage_members(admin2, admin1.organization_id)

def test_member_cannot_promote_others():
    """Test member users cannot promote others"""
    # Given: Organization with admin and 2 members
    admin = create_user_with_organization("admin@example.com", "Example Inc")
    member1 = create_user_join_organization({"email": "member1@example.com"}, admin.organization_id)
    member2 = create_user_join_organization({"email": "member2@example.com"}, admin.organization_id)
    
    # When: Member tries to promote another member
    response = client.put(
        f"/api/v1/organizations/{admin.organization_id}/members/{member2.id}/role",
        json={"organization_role": "admin"},
        headers=auth_headers(member1)
    )
    
    # Then: Request denied
    assert response.status_code == 403
    member2.refresh_from_db()
    assert member2.organization_role == OrganizationRole.MEMBER
```

#### Scenario 4: Self-Role Change Prevention

**Test Steps:**
1. Admin user attempts to change own role
2. System validates request is for different user
3. System blocks self-modification
4. Returns 403 Forbidden

**Required PyTests:**

```python
def test_user_cannot_change_own_role():
    """Test users cannot modify their own role"""
    # Given: Admin user
    admin = create_user_with_organization("admin@example.com", "Example Inc")
    
    # When: Admin tries to change own role
    response = client.put(
        f"/api/v1/organizations/{admin.organization_id}/members/{admin.id}/role",
        json={"organization_role": "member"},
        headers=auth_headers(admin)
    )
    
    # Then: Request blocked
    assert response.status_code == 403
    assert "cannot modify own role" in response.json()["error"]["message"]
    
    # And: Role unchanged
    admin.refresh_from_db()
    assert admin.organization_role == OrganizationRole.ADMIN

def test_admin_cannot_demote_self():
    """Test admin cannot accidentally demote themselves"""
    # Given: Organization with 2 admins
    admin1 = create_user_with_organization("admin1@example.com", "Example Inc")
    admin2 = create_user_join_organization({"email": "admin2@example.com"}, admin1.organization_id)
    promote_user_to_admin(admin2, admin1.organization_id)
    
    # When: Admin1 tries to demote self
    response = client.put(
        f"/api/v1/organizations/{admin1.organization_id}/members/{admin1.id}/role",
        json={"organization_role": "member"},
        headers=auth_headers(admin1)
    )
    
    # Then: Blocked and both remain admins
    assert response.status_code == 403
    assert admin1.organization_role == OrganizationRole.ADMIN
    assert admin2.organization_role == OrganizationRole.ADMIN
```

#### Scenario 5: Member Deletion with Auto-Admin Promotion

**Test Steps:**
1. Admin deletes another admin (2 users remaining: 1 admin, 1 member)
2. System validates deletion permissions
3. User deleted successfully
4. Remaining member automatically promoted to Admin

**Required PyTests:**

```python
def test_auto_admin_promotion_on_last_admin_deletion():
    """Test member becomes admin when last admin is deleted"""
    # Given: Organization with 1 admin, 1 member
    admin = create_user_with_organization("admin@example.com", "Example Inc")
    member = create_user_join_organization({"email": "member@example.com"}, admin.organization_id)
    
    # When: Admin is deleted
    response = client.delete(
        f"/api/v1/organizations/{admin.organization_id}/members/{admin.id}",
        headers=auth_headers(admin)  # Admin can delete themselves in this case
    )
    
    # Then: Member auto-promoted to admin
    assert response.status_code == 200
    member.refresh_from_db()
    assert member.organization_role == OrganizationRole.ADMIN
    assert member.organization.users.count() == 1

def test_normal_member_deletion():
    """Test normal member deletion doesn't trigger auto-promotion"""
    # Given: Organization with 1 admin, 2 members
    admin = create_user_with_organization("admin@example.com", "Example Inc")
    member1 = create_user_join_organization({"email": "member1@example.com"}, admin.organization_id)
    member2 = create_user_join_organization({"email": "member2@example.com"}, admin.organization_id)
    
    # When: Admin deletes a member
    response = client.delete(
        f"/api/v1/organizations/{admin.organization_id}/members/{member1.id}",
        headers=auth_headers(admin)
    )
    
    # Then: Normal deletion, admin stays admin
    assert response.status_code == 200
    admin.refresh_from_db()
    member2.refresh_from_db()
    assert admin.organization_role == OrganizationRole.ADMIN
    assert member2.organization_role == OrganizationRole.MEMBER
    assert admin.organization.users.count() == 2

def test_auto_promotion_with_multiple_members():
    """Test auto-promotion chooses oldest member when multiple exist"""
    # Given: Organization with 1 admin, 2 members (member1 created first)
    admin = create_user_with_organization("admin@example.com", "Example Inc")
    member1 = create_user_join_organization({"email": "member1@example.com"}, admin.organization_id)
    time.sleep(0.1)  # Ensure different timestamps
    member2 = create_user_join_organization({"email": "member2@example.com"}, admin.organization_id)
    
    # When: Admin deleted
    delete_user(admin)
    
    # Then: Oldest member (member1) becomes admin
    member1.refresh_from_db()
    member2.refresh_from_db()
    assert member1.organization_role == OrganizationRole.ADMIN
    assert member2.organization_role == OrganizationRole.MEMBER
```

#### Scenario 6: Last Member Deletion Protection

**Test Steps:**
1. Attempt to delete sole remaining user
2. System validates user count
3. Deletion blocked without organization deletion flag
4. Returns 400 Bad Request with message

**Required PyTests:**

```python
def test_cannot_delete_last_member_without_org_deletion():
    """Test cannot delete sole organization member"""
    # Given: Organization with only 1 member
    admin = create_user_with_organization("admin@example.com", "Example Inc")
    
    # When: Try to delete last member without org deletion flag
    response = client.delete(
        f"/api/v1/organizations/{admin.organization_id}/members/{admin.id}",
        headers=auth_headers(admin)
    )
    
    # Then: Deletion blocked
    assert response.status_code == 400
    assert "cannot delete last member" in response.json()["error"]["message"]
    
    # And: User and organization still exist
    admin.refresh_from_db()
    assert admin.organization_role == OrganizationRole.ADMIN
    assert admin.organization.users.count() == 1

def test_delete_last_member_with_organization_deletion():
    """Test can delete last member with organization deletion flag"""
    # Given: Organization with only 1 member
    admin = create_user_with_organization("admin@example.com", "Example Inc")
    org_id = admin.organization_id
    
    # When: Delete last member with organization deletion
    response = client.delete(
        f"/api/v1/users/{admin.id}",
        json={"delete_organization": True},
        headers=auth_headers(admin)
    )
    
    # Then: Both user and organization deleted
    assert response.status_code == 200
    assert User.query.get(admin.id) is None
    assert Organization.query.get(org_id) is None

def test_user_deletion_endpoint_validation():
    """Test user deletion endpoint with various scenarios"""
    # Scenario 1: Delete user who is not last member
    admin = create_user_with_organization("admin@example.com", "Example Inc")
    member = create_user_join_organization({"email": "member@example.com"}, admin.organization_id)
    
    response = client.delete(f"/api/v1/users/{member.id}", headers=auth_headers(admin))
    assert response.status_code == 200
    
    # Scenario 2: Delete user who is last member without flag
    response = client.delete(f"/api/v1/users/{admin.id}", headers=auth_headers(admin))
    assert response.status_code == 400
    assert "delete_organization" in response.json()["error"]["message"]
    
    # Scenario 3: Delete user who is last member with flag
    response = client.delete(
        f"/api/v1/users/{admin.id}",
        json={"delete_organization": True},
        headers=auth_headers(admin)
    )
    assert response.status_code == 200
```

#### Scenario 7: Cross-Organization Access Prevention

**Test Steps:**
1. User from Organization A attempts to manage members of Organization B
2. System validates user's organization membership
3. Access denied with 403 Forbidden

**Required PyTests:**

```python
def test_cross_organization_access_denied():
    """Test users cannot access other organizations"""
    # Given: Two separate organizations
    admin_a = create_user_with_organization("admin@companya.com", "Company A")
    admin_b = create_user_with_organization("admin@companyb.com", "Company B")
    member_b = create_user_join_organization({"email": "member@companyb.com"}, admin_b.organization_id)
    
    # When: Admin A tries to manage Company B's members
    response = client.put(
        f"/api/v1/organizations/{admin_b.organization_id}/members/{member_b.id}/role",
        json={"organization_role": "admin"},
        headers=auth_headers(admin_a)
    )
    
    # Then: Access denied
    assert response.status_code == 403
    
    # When: Admin A tries to view Company B's members
    response = client.get(
        f"/api/v1/organizations/{admin_b.organization_id}/members/",
        headers=auth_headers(admin_a)
    )
    
    # Then: Access denied
    assert response.status_code == 403

def test_organization_isolation():
    """Test complete organization isolation"""
    # Given: Users in different organizations
    org_a_admin = create_user_with_organization("admin@orga.com", "Org A")
    org_b_admin = create_user_with_organization("admin@orgb.com", "Org B")
    
    # Test: Cannot view other org's data
    endpoints_to_test = [
        f"/api/v1/organizations/{org_b.organization_id}/members/",
        f"/api/v1/organizations/{org_b.organization_id}/invitations",
    ]
    
    for endpoint in endpoints_to_test:
        response = client.get(endpoint, headers=auth_headers(org_a_admin))
        assert response.status_code == 403
```

### Performance and Load Tests

```python
def test_domain_lookup_performance():
    """Test domain lookup performance under load"""
    # Given: 1000 organizations with different domains
    orgs = [create_organization(f"Company {i}", f"company{i}.com") for i in range(1000)]
    
    # When: Perform 1000 concurrent domain lookups
    import concurrent.futures
    import time
    
    def lookup_domain(domain):
        start = time.time()
        response = client.get(f"/api/v1/organizations/by-domain/{domain}")
        duration = time.time() - start
        return response.status_code, duration
    
    domains = [f"company{i}.com" for i in range(1000)]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(lookup_domain, domains))
    
    # Then: All lookups successful and fast
    for status_code, duration in results:
        assert status_code == 200
        assert duration < 0.2  # Under 200ms

def test_large_organization_member_list_performance():
    """Test member listing performance for large organizations"""
    # Given: Organization with 10,000 members
    admin = create_user_with_organization("admin@bigcorp.com", "Big Corp")
    
    # Create members in batches for performance
    for batch in range(100):  # 100 batches of 100 members
        members = []
        for i in range(100):
            member_data = {
                "email": f"member{batch*100+i}@bigcorp.com",
                "organization_id": admin.organization_id,
                "organization_role": OrganizationRole.MEMBER
            }
            members.append(User(**member_data))
        User.bulk_create(members)
    
    # When: Request member list
    start_time = time.time()
    response = client.get(
        f"/api/v1/organizations/{admin.organization_id}/members/",
        headers=auth_headers(admin)
    )
    duration = time.time() - start_time
    
    # Then: Response fast and paginated
    assert response.status_code == 200
    assert duration < 1.0  # Under 1 second
    assert len(response.json()["data"]) <= 50  # Paginated results
```

### Validation Edge Cases

```python
def test_email_domain_edge_cases():
    """Test domain extraction with edge cases"""
    edge_cases = [
        ("user@sub.domain.co.uk", "sub.domain.co.uk"),
        ("test+tag@company.com", "company.com"),
        ("user.name@company-name.org", "company-name.org"),
        ("admin@localhost", "localhost"),
        ("service@ip-192-168-1-1.internal", "ip-192-168-1-1.internal"),
    ]
    
    for email, expected_domain in edge_cases:
        extracted = extract_domain_from_email(email)
        assert extracted == expected_domain, f"Failed for {email}"

def test_rate_limiting_edge_cases():
    """Test rate limiting with edge cases"""
    # Test: Rate limit resets after time window
    for i in range(100):
        response = client.get("/api/v1/organizations/by-domain/test.com")
        assert response.status_code in [200, 404]
    
    # Should be rate limited now
    response = client.get("/api/v1/organizations/by-domain/test.com")
    assert response.status_code == 429
    
    # Fast forward time and test reset (mock time.time() if needed)
    # After 1 hour, rate limit should reset
    
def test_concurrent_admin_operations():
    """Test concurrent admin operations don't cause race conditions"""
    # Given: Organization with admin and member
    admin = create_user_with_organization("admin@test.com", "Test Corp")
    member = create_user_join_organization({"email": "member@test.com"}, admin.organization_id)
    
    # When: Multiple concurrent operations
    import threading
    results = []
    
    def promote_member():
        response = client.put(
            f"/api/v1/organizations/{admin.organization_id}/members/{member.id}/role",
            json={"organization_role": "admin"},
            headers=auth_headers(admin)
        )
        results.append(response.status_code)
    
    def delete_member():
        response = client.delete(
            f"/api/v1/organizations/{admin.organization_id}/members/{member.id}",
            headers=auth_headers(admin)
        )
        results.append(response.status_code)
    
    # Start both operations simultaneously
    threads = [threading.Thread(target=promote_member), threading.Thread(target=delete_member)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Then: Exactly one should succeed
    success_count = sum(1 for code in results if code in [200, 201])
    assert success_count == 1
```

## Frontend Requirements & User Journeys

### User Roles and Permissions

#### Organization Admin
- View all organization members with details (name, email, role, join date)
- Invite new members via email with role assignment
- Change member roles (promote/demote) except own role
- Remove members from organization
- View and manage pending invitations
- Cancel pending invitations

#### Organization Member  
- View other members in same organization (limited details)
- Cannot manage memberships or invitations
- Cannot change roles

### Core User Journeys

#### Journey 1: Admin Invites New Member

**User Story**: As an organization admin, I want to invite a new team member so they can access our tickets and collaborate.

**Steps**:
1. Admin navigates to Team/Members section
2. Admin clicks "Invite Member" button
3. System shows invite modal with email and role fields
4. Admin enters email address and selects role (Member/Admin)
5. Admin clicks "Send Invitation"
6. System validates email and sends invitation
7. System shows success message with invitation details
8. Invitee receives email with invitation link

**API Endpoints**:
```
POST /api/v1/organizations/{org_id}/members/invite
```

**Request**:
```json
{
  "email": "newuser@example.com",
  "role": "member",
  "send_email": true
}
```

**Response**:
```json
{
  "invitation_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "newuser@example.com",
  "role": "member",
  "invitation_url": "https://app.example.com/invitations/accept/abc123token",
  "expires_at": "2024-01-22T10:30:00Z"
}
```

#### Journey 2: User Accepts Invitation

**User Story**: As an invited user, I want to accept my team invitation so I can join my organization and start using the platform.

**Steps**:
1. User clicks invitation link in email
2. System loads invitation details page
3. System displays organization info, role, and inviter details  
4. User sees form to enter full name and password
5. User fills form and clicks "Accept Invitation"
6. System validates data and creates user account
7. System adds user to organization with specified role
8. User is redirected to dashboard as active member

**API Endpoints**:
```
GET /api/v1/invitations/{token}
POST /api/v1/invitations/{token}/accept
```

**Get Invitation Request**:
```
GET /api/v1/invitations/abc123token
```

**Get Invitation Response**:
```json
{
  "invitation_id": "550e8400-e29b-41d4-a716-446655440000",
  "organization": {
    "id": "org-uuid",
    "name": "Example Inc.",
    "display_name": "Example Inc.",
    "domain": "example.com",
    "member_count": 25
  },
  "email": "newuser@example.com",
  "role": "member",
  "status": "pending",
  "expires_at": "2024-01-22T10:30:00Z",
  "invited_by": {
    "id": "inviter-uuid",
    "email": "admin@example.com",
    "full_name": "Admin User"
  }
}
```

**Accept Invitation Request**:
```json
{
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Accept Invitation Response**:
```json
{
  "user": {
    "id": "user-uuid",
    "email": "newuser@example.com",
    "full_name": "John Doe",
    "organization_id": "org-uuid",
    "organization_role": "member",
    "joined_organization_at": "2024-01-15T14:30:00Z"
  },
  "access_token": "jwt-token-here",
  "refresh_token": "refresh-token-here"
}
```

#### Journey 3: Enhanced Registration with Organization Discovery

**User Story**: As a new user registering, I want the system to find my existing organization so I don't create a duplicate organization.

**Steps**:
1. User visits registration page and enters email
2. System extracts domain from email (e.g., user@example.com → example.com)
3. System automatically searches for existing organizations with that domain
4. If organization found: System shows option to join existing organization
5. If no organization found: System proceeds with new organization creation
6. User chooses to join existing or create new organization
7. System completes registration with appropriate organization assignment

**API Endpoints**:
```
GET /api/v1/organizations/by-domain/{domain}
```

**Domain Lookup Request**:
```
GET /api/v1/organizations/by-domain/example.com
```

**Domain Lookup Response (Found)**:
```json
{
  "organization": {
    "id": "org-uuid",
    "name": "Example Inc.",
    "domain": "example.com", 
    "member_count": 25,
    "display_name": "Example Inc."
  }
}
```

**Domain Lookup Response (Not Found)**:
```json
HTTP 404 Not Found
{
  "error": {
    "code": "ORGANIZATION_NOT_FOUND",
    "message": "No organization found for domain example.com"
  }
}
```

#### Journey 4: Admin Manages Member Roles

**User Story**: As an organization admin, I want to promote a member to admin or demote an admin to member so I can manage team permissions appropriately.

**Steps**:
1. Admin views member list in Team/Members section
2. Admin clicks actions menu for target member
3. System shows role management options (Promote to Admin/Demote to Member)
4. Admin selects desired role change
5. System shows confirmation dialog with role change details
6. Admin confirms the change
7. System updates member role and refreshes member list
8. System shows success notification

**API Endpoints**:
```
GET /api/v1/organizations/{org_id}/members/
PUT /api/v1/organizations/{org_id}/members/{user_id}/role
```

**Get Members Request**:
```
GET /api/v1/organizations/org-uuid/members/?page=1&limit=50
```

**Get Members Response**:
```json
{
  "data": [
    {
      "id": "user-uuid",
      "email": "user@example.com",
      "full_name": "John Doe",
      "organization_role": "admin",
      "joined_organization_at": "2024-01-15T10:30:00Z",
      "invited_by": {
        "id": "inviter-uuid",
        "email": "admin@example.com",
        "full_name": "Admin User"
      },
      "is_active": true
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 25,
    "pages": 1
  }
}
```

**Update Role Request**:
```json
{
  "organization_role": "admin"
}
```

**Update Role Response**:
```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "organization_role": "admin",
  "joined_organization_at": "2024-01-15T10:30:00Z"
}
```

#### Journey 5: Admin Removes Member

**User Story**: As an organization admin, I want to remove a member from my organization so I can manage team access appropriately.

**Steps**:
1. Admin views member list in Team/Members section
2. Admin clicks actions menu for target member
3. System shows "Remove Member" option
4. Admin clicks "Remove Member"
5. System shows confirmation dialog with member details and consequences
6. Admin confirms removal
7. System removes member from organization
8. System refreshes member list and shows success notification
9. If removed member was last admin, system auto-promotes another member

**API Endpoints**:
```
DELETE /api/v1/organizations/{org_id}/members/{user_id}
```

**Remove Member Request**:
```
DELETE /api/v1/organizations/org-uuid/members/user-uuid
```

**Remove Member Response**:
```json
{
  "success": true,
  "message": "Member removed successfully",
  "auto_promoted_admin": {
    "user_id": "promoted-user-uuid",
    "full_name": "Jane Smith",
    "email": "jane@example.com"
  }
}
```

#### Journey 6: Invitation Management

**User Story**: As an organization admin, I want to view and manage pending invitations so I can track who has been invited and cancel expired invitations.

**Steps**:
1. Admin navigates to Team/Members section
2. Admin clicks "Pending Invitations" tab
3. System displays list of pending invitations with details
4. Admin can see invitation status, expiry date, and invited role
5. Admin can cancel pending invitations if needed
6. Admin can resend invitations that are about to expire

**API Endpoints**:
```
GET /api/v1/organizations/{org_id}/invitations
DELETE /api/v1/organizations/{org_id}/invitations/{invitation_id}
```

**Get Invitations Request**:
```
GET /api/v1/organizations/org-uuid/invitations
```

**Get Invitations Response**:
```json
{
  "data": [
    {
      "id": "invitation-uuid",
      "email": "pending@example.com",
      "role": "member",
      "status": "pending",
      "invited_by": {
        "id": "admin-uuid",
        "full_name": "Admin User",
        "email": "admin@example.com"
      },
      "created_at": "2024-01-15T10:30:00Z",
      "expires_at": "2024-01-22T10:30:00Z"
    }
  ]
}
```

**Cancel Invitation Request**:
```
DELETE /api/v1/organizations/org-uuid/invitations/invitation-uuid
```

**Cancel Invitation Response**:
```json
{
  "success": true,
  "message": "Invitation cancelled successfully"
}
```

### Frontend UI Requirements

#### Member Management Dashboard
- **Main View**: Tabbed interface with "Active Members" and "Pending Invitations"
- **Member List**: Table with columns for Name, Email, Role, Join Date, Invited By
- **Actions**: Role-based action menus (admin users see more options)
- **Invite Button**: Prominent "Invite Member" button for admins
- **Search/Filter**: Filter members by role, search by name/email

#### Invitation Modal
- **Email Field**: Email input with validation
- **Role Selector**: Dropdown with Member/Admin options
- **Send Button**: Submit button with loading state
- **Validation**: Real-time email validation and duplicate checking

#### Organization Discovery (Registration)
- **Email Input**: Standard email field in registration form
- **Discovery Results**: Card showing found organization with join option
- **Choice Interface**: Clear buttons for "Join [Org Name]" vs "Create New Organization"
- **Organization Info**: Display org name, domain, member count when found

#### Invitation Accept Page
- **Invitation Details**: Organization info, role badge, inviter name
- **User Form**: Full name and password fields
- **Accept/Decline**: Clear action buttons
- **Expiry Warning**: Clear indication of invitation expiry date

### Validation Requirements

#### Client-Side Validation
- **Email Format**: RFC 5322 compliant email validation
- **Password Strength**: Minimum 8 characters, complexity requirements
- **Full Name**: Minimum 2 characters, no special characters except spaces/hyphens
- **Role Selection**: Must be valid enum value

#### Business Rule Validation
- **Self-Role Modification**: Users cannot change their own role
- **Last Admin Protection**: Cannot demote/remove last admin without replacement
- **Duplicate Invitations**: Cannot invite same email twice to same organization
- **Active Organization**: Can only invite to active organizations
- **Permission Checks**: Only admins can manage members/invitations

### Error Handling

#### User-Friendly Error Messages
```json
{
  "DUPLICATE_INVITATION": "This email has already been invited to your organization.",
  "INVALID_EMAIL_DOMAIN": "Email domain does not match your organization.",
  "CANNOT_MODIFY_OWN_ROLE": "You cannot change your own role. Ask another admin for help.",
  "LAST_ADMIN_PROTECTION": "Cannot remove the last admin. Promote another member first.",
  "INVITATION_EXPIRED": "This invitation has expired. Please request a new one.",
  "INSUFFICIENT_PERMISSIONS": "You don't have permission to perform this action.",
  "ORGANIZATION_LIMIT_REACHED": "Your organization has reached its member limit.",
  "USER_ALREADY_MEMBER": "This user is already a member of your organization."
}
```

#### HTTP Status Codes
- **200**: Success with data
- **201**: Resource created successfully  
- **400**: Invalid request data or business rule violation
- **401**: Authentication required
- **403**: Insufficient permissions
- **404**: Resource not found (organization, invitation, user)
- **409**: Conflict (duplicate invitation, etc.)
- **422**: Validation error
- **429**: Rate limit exceeded (domain lookup)

### Real-time Updates

#### WebSocket Events
```json
{
  "type": "MEMBER_INVITED",
  "organizationId": "org-uuid",
  "data": {
    "invitationId": "invitation-uuid",
    "email": "newuser@example.com",
    "role": "member"
  }
}

{
  "type": "MEMBER_JOINED", 
  "organizationId": "org-uuid",
  "data": {
    "userId": "user-uuid",
    "fullName": "John Doe",
    "email": "john@example.com"
  }
}

{
  "type": "MEMBER_ROLE_CHANGED",
  "organizationId": "org-uuid", 
  "data": {
    "userId": "user-uuid",
    "oldRole": "member",
    "newRole": "admin"
  }
}

{
  "type": "MEMBER_REMOVED",
  "organizationId": "org-uuid",
  "data": {
    "userId": "user-uuid",
    "autoPromotedAdmin": "promoted-user-uuid"
  }
}
```

## Implementation Phases

### Phase 1: Core Data Models (Week 1-2)
- Enhance User model with organization role and membership tracking fields
- Create OrganizationInvitation model
- Database migrations for new columns
- Update existing User/Organization relationship logic

### Phase 2: Basic Member Management (Week 3-4)
- Implement member CRUD operations
- Basic invitation creation and acceptance
- Member role management

### Phase 3: Domain-Based Organization Discovery (Week 5-6)
- Domain-based organization lookup endpoint
- Enhanced registration flow with domain matching
- Auto-admin promotion logic for first users

### Phase 4: Advanced Security and Protection (Week 7-8)
- Self-role modification prevention
- Last member deletion protection  
- Auto-admin promotion on member deletion
- Advanced validation and security
- Audit logging and monitoring

### Phase 5: Frontend Integration (Week 9-10)
- Complete frontend implementation following user journeys
- Real-time WebSocket integration
- Comprehensive testing and polish

## Dependencies

### External Libraries
- **celery**: For background email sending
- **jinja2**: For email templates
- **validators**: For email domain validation

### Infrastructure
- **Email Service**: SMTP or service like SendGrid for invitation emails
- **Monitoring**: Track registration flows and admin management actions
- **Caching**: Redis for domain-based organization lookups

## Rollback Plan

1. **Database Rollback**: Prepared down-migrations for all schema changes
2. **Feature Flags**: All new endpoints behind feature flags
3. **API Versioning**: New endpoints in separate version namespace
4. **Data Migration**: Reversible data migration scripts
5. **Monitoring**: Comprehensive error tracking for quick issue identification

## Post-Launch Monitoring

### Key Metrics
- **Registration Success Rate**: Target >95% successful domain matching
- **Admin Auto-Promotion Accuracy**: Target 100% success rate
- **API Error Rates**: Target <1%
- **Response Times**: Target <200ms for domain lookups

### Alerts
- Failed admin auto-promotions
- Blocked last-member deletions (may indicate user confusion)
- Self-role modification attempts (security monitoring)
- Domain lookup failures
- Unusual role change patterns