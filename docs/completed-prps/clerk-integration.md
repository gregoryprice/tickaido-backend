# Clerk.com Integration for User & Identity Management

## Product Requirements Document (PRD)
---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Business Goals & Requirements](#business-goals--requirements)
3. [Technical Architecture](#technical-architecture)
4. [Provider Setup (Google, Microsoft, GitHub)](#provider-setup)
5. [Implementation Plan](#implementation-plan)
6. [Migration Strategy](#migration-strategy)
7. [Testing & Validation](#testing--validation)
8. [Security & Compliance](#security--compliance)
9. [Cost Analysis](#cost-analysis)
10. [Timeline & Milestones](#timeline--milestones)

---

## Executive Summary

This document outlines the integration of [Clerk.com](https://clerk.com) as the primary user authentication and identity management solution for the AI Ticket Creator Backend. Clerk will replace the current custom SSO implementation and provide enterprise-grade authentication with support for multiple identity providers (Google, Microsoft Entra ID, GitHub).

### Key Benefits
- **Reduced Development Time**: Eliminate 2-3 weeks of custom SSO development and ongoing maintenance
- **Enterprise Security**: SOC 2 Type II compliant, GDPR/CCPA ready
- **Rich User Experience**: Pre-built UI components, passwordless authentication, MFA
- **Scalability**: Built to handle enterprise-scale authentication requirements
- **Compliance**: Built-in security features meet enterprise compliance requirements

### Integration Scope
- Replace custom authentication system with Clerk
- Integrate Google, Microsoft Entra ID, and GitHub SSO providers
- Maintain existing JWT-based API authentication
- Preserve user data and account relationships
- Add advanced security features (MFA, session management, security events)

---

## Business Goals & Requirements

### Primary Goals
1. **Accelerate Time-to-Market**: Reduce authentication development time by 80%
2. **Enhance Security Posture**: Implement enterprise-grade security controls
3. **Improve User Experience**: Provide seamless SSO across multiple providers
4. **Reduce Maintenance Overhead**: Outsource identity management complexity
5. **Enable Advanced Features**: Support MFA, passwordless auth, and advanced session management

### Functional Requirements

#### User Authentication
- [x] **Multi-Provider SSO**: Google, Microsoft Entra ID, GitHub
- [x] **Email/Password Authentication**: Traditional signup/signin
- [x] **Passwordless Authentication**: Email magic links, SMS OTP
- [x] **Multi-Factor Authentication**: TOTP, SMS, email verification
- [x] **Social Login**: Additional providers (LinkedIn, Apple) if needed

#### User Management
- [x] **User Profiles**: Profile management with custom fields
- [x] **Account Linking**: Link multiple providers to single account
- [x] **User Roles & Permissions**: Integration with existing RBAC system
- [x] **Organization Management**: Multi-tenant organization support with Clerk Organizations API
- [x] **User Invitation System**: Invite users to organizations with role-based access
- [x] **Single Organization Membership**: Users belong to one organization at a time
- [x] **Organization-Scoped Permissions**: Role-based permissions within the user's organization
- [x] **Tenant Isolation**: Complete data isolation between organizations

#### Security & Compliance
- [x] **Session Management**: Advanced session controls and monitoring
- [x] **Security Events**: Audit logging and suspicious activity detection
- [x] **Data Privacy**: GDPR/CCPA compliance features
- [x] **Rate Limiting**: Built-in protection against abuse
- [x] **Device Management**: Track and manage user devices

### Technical Requirements

#### Integration Requirements
- [x] **FastAPI Integration**: Seamless integration with existing FastAPI app
- [x] **JWT Compatibility**: Maintain existing JWT-based API authentication
- [x] **Database Integration**: Sync user data with existing PostgreSQL database
- [x] **Webhook Support**: Real-time user event synchronization
- [x] **Custom Claims**: Support for custom user metadata

#### Performance Requirements
- [x] **Response Time**: < 200ms for authentication requests
- [x] **Availability**: 99.9% uptime SLA
- [x] **Scalability**: Support for 10,000+ concurrent users
- [x] **CDN Integration**: Global edge network for fast authentication

---

## Technical Architecture

### Current State vs. Future State

| Component | Current State | Future State with Clerk |
|-----------|---------------|------------------------|
| **Authentication** | Custom FastAPI auth | Clerk-managed authentication |
| **SSO Providers** | Custom OAuth implementation | Clerk-managed OAuth flows |
| **User Database** | PostgreSQL with custom schema | PostgreSQL + Clerk user sync |
| **Session Management** | JWT tokens only | Clerk sessions + JWT API tokens |
| **User Profile** | Custom user model | Clerk user + custom metadata sync |
| **Security Features** | Basic rate limiting | Enterprise security suite |

### Multi-Tenant Organization Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Applications                    │
├─────────────────────────────────────────────────────────────┤
│  • Chrome Extension    • Web Dashboard    • Mobile App     │
│  • Role-Based UI       • Organization Context              │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   Clerk Authentication                     │
├─────────────────────────────────────────────────────────────┤
│  • User Authentication      • Single Organization Support  │
│  • Organization Management  • Role-Based Access Control    │
│  • Organization Invitations • Permission Management        │
│  • Tenant-Scoped Sessions  • API Token Generation         │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                FastAPI Backend (Enhanced)                  │
├─────────────────────────────────────────────────────────────┤
│  • Organization Context Middleware  • Tenant Data Isolation│
│  • Role & Permission Validation     • API Token Validation │
│  • Organization Webhook Handlers    • Permission Caching   │
│  • Multi-Tenant API Routes         • Audit Trail per Org  │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              PostgreSQL Database (Multi-Tenant)            │
├─────────────────────────────────────────────────────────────┤
│  • Organization-Scoped Data    • Single-Org User Records   │
│  • Tenant-Isolated Tickets     • Role/Permission Matrix   │
│  • Organization Memberships    • Audit Logs per Tenant    │
│  • Resource Access Controls    • API Token Management     │
└─────────────────────────────────────────────────────────────┘
```

### Organization Data Flow

1. **User Login**: User authenticates via Clerk within their assigned organization
2. **Organization Context**: Backend automatically determines user's organization membership
3. **Permission Check**: Every API request validates user permissions within their organization
4. **Data Isolation**: All queries filtered by organization_id for tenant isolation
5. **API Token Access**: Users can generate organization-scoped API tokens for programmatic access

---

## API Token Authentication with Clerk Integration

### Overview
The Clerk integration maintains support for API tokens while adding organization context and enhanced security. Users can generate organization-scoped API tokens for programmatic access to the AI Ticket Creator API.

### API Token Architecture

#### Token Types
1. **User Session Tokens**: Short-lived tokens from Clerk for web/mobile apps
2. **API Access Tokens**: Long-lived tokens for programmatic API access
3. **Organization-Scoped Tokens**: API tokens that include organization context

#### Token Generation Flow
```python
# API Token Generation Endpoint
@router.post("/api-tokens", response_model=APITokenResponse)
async def generate_api_token(
    token_request: APITokenGenerationRequest,
    context: OrganizationContext = Depends(get_organization_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Generate organization-scoped API token for programmatic access"""
    
    # Check permission to generate API tokens
    if not context.has_permission("api:generate"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to generate API tokens"
        )
    
    # Generate secure API token
    api_token = secrets.token_urlsafe(32)
    api_token_hash = auth_service.get_password_hash(api_token)
    
    # Store token with organization context
    token_record = APIToken(
        user_id=context.user.id,
        organization_id=context.organization.id,
        token_hash=api_token_hash,
        name=token_request.name,
        permissions=token_request.permissions or context.permissions,
        expires_at=datetime.now(timezone.utc) + timedelta(days=token_request.expires_days or 365),
        last_used_at=None,
        is_active=True
    )
    
    db.add(token_record)
    await db.commit()
    
    return APITokenResponse(
        token=f"att_{api_token}",  # "AI Ticket Token" prefix
        id=token_record.id,
        name=token_record.name,
        permissions=token_record.permissions,
        expires_at=token_record.expires_at,
        organization_id=context.organization.id,
        organization_name=context.organization.name
    )
```

### API Token Usage

#### Authentication Headers
Users authenticate API requests using the generated API token:

```bash
# Using curl with API token
curl -X GET "https://api.tickaido.com/api/v1/tickets" \
  -H "Authorization: Bearer ai_prod_AbCdEf123456789..." \
  -H "Content-Type: application/json"

# Using Python requests
import requests

headers = {
    'Authorization': 'Bearer ai_prod_AbCdEf123456789...',
    'Content-Type': 'application/json'
}

response = requests.get(
    'https://api.tickaido.com/api/v1/tickets',
    headers=headers
)
```

#### API Token Validation Middleware
```python
# Authentication middleware supporting both Clerk and API tokens
class AuthMiddleware:
    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Optional[User]:
        """Authenticate request using Clerk token or API token"""
        
        if not credentials:
            return None
        
        token = credentials.credentials
        
        # Check if it's an API token (starts with "ai_")
        if token.startswith("ai_"):
            return await self._validate_api_token(token, request)
        else:
            # Standard Clerk token validation
            return await self._validate_clerk_token(token, request)
    
    async def _validate_api_token(self, token: str, request: Request) -> Optional[User]:
        """Validate API token and return user with organization context"""
        
        # Extract token without environment prefix
        # Format: ai_prod_token, ai_stag_token, ai_dev_token
        parts = token.split('_', 2)
        if len(parts) != 3 or parts[0] != 'ai':
            raise HTTPException(400, "Invalid token format")
        
        env_prefix, raw_token = parts[1], parts[2]
        
        async with get_db_session() as db:
            # Find token by hash
            token_hash = auth_service.get_password_hash(raw_token)
            
            result = await db.execute(
                select(APIToken, User, Organization)
                .join(User, APIToken.user_id == User.id)
                .join(Organization, APIToken.organization_id == Organization.id)
                .where(
                    and_(
                        APIToken.token_hash == token_hash,
                        APIToken.is_active == True,
                        APIToken.expires_at > datetime.now(timezone.utc),
                        User.is_active == True,
                        Organization.is_active == True
                    )
                )
            )
            
            token_data = result.first()
            if not token_data:
                return None
            
            api_token, user, organization = token_data
            
            # Update last used timestamp
            api_token.last_used_at = datetime.now(timezone.utc)
            await db.commit()
            
            # Set organization context in request
            request.state.organization_context = OrganizationContext(
                organization=organization,
                membership=None,  # API tokens don't need membership
                user=user,
                permissions=api_token.permissions
            )
            
            return user
```

### API Token Management

#### Token Dashboard UI
Users can manage their API tokens through a dedicated dashboard:

```jsx
// API Token Management Component
function APITokenDashboard() {
  const [tokens, setTokens] = useState([])
  const [isGenerating, setIsGenerating] = useState(false)

  const generateToken = async (tokenData) => {
    setIsGenerating(true)
    try {
      const response = await authenticatedFetch('/api/v1/api-tokens', {
        method: 'POST',
        body: JSON.stringify(tokenData)
      })
      const newToken = await response.json()
      
      // Show token to user (only displayed once)
      setTokens([...tokens, newToken])
      
      // Display token securely to user
      alert(`Your API token: ${newToken.token}\nSave this token securely - it won't be shown again!`)
      
    } finally {
      setIsGenerating(false)
    }
  }

  const revokeToken = async (tokenId) => {
    await authenticatedFetch(`/api/v1/api-tokens/${tokenId}`, {
      method: 'DELETE'
    })
    setTokens(tokens.filter(t => t.token_id !== tokenId))
  }

  return (
    <div className="api-token-dashboard">
      <h2>API Tokens</h2>
      <p>Generate tokens for programmatic access to the AI Ticket Creator API</p>
      
      <div className="token-generation">
        <h3>Generate New Token</h3>
        <form onSubmit={(e) => {
          e.preventDefault()
          const formData = new FormData(e.target)
          generateToken({
            name: formData.get('name'),
            permissions: ['api:read', 'api:write'], // Based on user role
            expires_days: parseInt(formData.get('expires_days'))
          })
        }}>
          <input name="name" placeholder="Token name" required />
          <select name="expires_days" defaultValue="365">
            <option value="30">30 days</option>
            <option value="90">90 days</option>
            <option value="365">1 year</option>
          </select>
          <button type="submit" disabled={isGenerating}>
            Generate Token
          </button>
        </form>
      </div>

      <div className="token-list">
        <h3>Active Tokens</h3>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Created</th>
              <th>Last Used</th>
              <th>Expires</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {tokens.map(token => (
              <tr key={token.token_id}>
                <td>{token.name}</td>
                <td>{formatDate(token.created_at)}</td>
                <td>{token.last_used_at ? formatDate(token.last_used_at) : 'Never'}</td>
                <td>{formatDate(token.expires_at)}</td>
                <td>
                  <button 
                    onClick={() => revokeToken(token.token_id)}
                    className="revoke-btn"
                  >
                    Revoke
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

### API Token Security Features

#### Organization-Scoped Permissions
- ✅ **Automatic Organization Context**: API tokens inherit user's organization membership
- ✅ **Permission Inheritance**: Tokens respect user's role-based permissions within the organization
- ✅ **Data Isolation**: API requests automatically filtered by organization_id
- ✅ **Custom Permissions**: Users can create tokens with subset of their permissions

#### Security Controls
- ✅ **Environment-Specific Prefixing**: `ai_prod_`, `ai_stag_`, `ai_dev_` prefixes identify environment and application
- ✅ **Secure Storage**: Only token hash stored in database, not raw token
- ✅ **Expiration Management**: Configurable token expiration (30 days to 1 year)
- ✅ **Usage Tracking**: Last used timestamp for security monitoring
- ✅ **Revocation**: Instant token revocation capability
- ✅ **Rate Limiting**: API tokens subject to same rate limiting as user sessions

#### Example API Usage Patterns

**Create a Ticket**:
```bash
curl -X POST "https://api.tickaido.com/api/v1/tickets" \
  -H "Authorization: Bearer ai_prod_AbCdEf123456789..." \
  -H "Content-Type: application/json" \
  -d '{
    "title": "API Integration Issue",
    "description": "Authentication failing for API requests",
    "priority": "high",
    "category": "technical"
  }'
```

**List Organization Tickets**:
```bash
curl -X GET "https://api.tickaido.com/api/v1/tickets?status=open" \
  -H "Authorization: Bearer ai_stag_AbCdEf123456789..."
```

**Get User Profile**:
```bash
curl -X GET "https://api.tickaido.com/api/v1/users/me" \
  -H "Authorization: Bearer ai_dev_AbCdEf123456789..."
```

**Environment-Specific Token Examples**:
- **Production**: `ai_prod_AbCdEf123456789...`
- **Staging**: `ai_stag_AbCdEf123456789...`  
- **Development**: `ai_dev_AbCdEf123456789...`

### How Users Get API Tokens

#### Current Implementation vs. New Implementation

**Current System**:
```python
# Current API key generation in user model
class User(BaseModel):
    api_key_hash = Column(String(255), nullable=True, unique=True, index=True)
    api_key_created_at = Column(DateTime(timezone=True), nullable=True)
    api_key_last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    def generate_api_key(self):
        """Generate API key for user"""
        import secrets
        api_key = secrets.token_urlsafe(32)
        self.api_key_hash = hash_password(api_key)
        self.api_key_created_at = datetime.now(timezone.utc)
        return f"aip_{api_key}"  # Old prefix - will be removed
```

**New Clerk-Based System**:
```python
# New API token model with organization context
class APIToken(BaseModel):
    __tablename__ = "api_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)
    
    name = Column(String(255), nullable=False)  # User-friendly name
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    permissions = Column(JSON, nullable=True)  # Scoped permissions
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="api_tokens")
    organization = relationship("Organization")
```

#### User API Token Generation Process

**Step 1: User Interface**
Users access API token generation through their dashboard:

```jsx
// New API Token Generation UI
function GenerateAPIToken() {
  const { user, organization } = useOrganizationContext()
  
  const [tokenForm, setTokenForm] = useState({
    name: '',
    permissions: [],
    expires_days: 365
  })
  
  const availablePermissions = getUserAvailablePermissions(user.role)
  
  return (
    <div className="generate-api-token">
      <h3>Generate API Token</h3>
      <p>Organization: <strong>{organization.name}</strong></p>
      
      <form onSubmit={handleGenerateToken}>
        <div>
          <label>Token Name</label>
          <input 
            type="text" 
            placeholder="e.g., 'Production Integration', 'CI/CD Pipeline'"
            value={tokenForm.name}
            onChange={(e) => setTokenForm({...tokenForm, name: e.target.value})}
            required 
          />
          <small>Choose a descriptive name to identify this token</small>
        </div>
        
        <div>
          <label>Permissions</label>
          <div className="permission-checkboxes">
            {availablePermissions.map(permission => (
              <label key={permission}>
                <input 
                  type="checkbox" 
                  value={permission}
                  checked={tokenForm.permissions.includes(permission)}
                  onChange={handlePermissionChange}
                />
                {permission}
              </label>
            ))}
          </div>
          <small>Token will have subset of your current permissions</small>
        </div>
        
        <div>
          <label>Expiration</label>
          <select 
            value={tokenForm.expires_days}
            onChange={(e) => setTokenForm({...tokenForm, expires_days: parseInt(e.target.value)})}
          >
            <option value="30">30 days</option>
            <option value="90">90 days</option>
            <option value="365">1 year</option>
          </select>
        </div>
        
        <button type="submit">Generate Token</button>
      </form>
    </div>
  )
}
```

**Step 2: Backend Token Generation**
```python
# API endpoint for token generation
@router.post("/api-tokens", response_model=APITokenResponse)
async def generate_api_token(
    token_request: APITokenGenerationRequest,
    context: OrganizationContext = Depends(get_organization_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Generate organization-scoped API token"""
    
    # Validation: Check if user can generate API tokens
    if not context.has_permission("api:generate"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to generate API tokens"
        )
    
    # Validation: Check token limits per user
    existing_tokens_count = await db.scalar(
        select(func.count(APIToken.id)).where(
            and_(
                APIToken.user_id == context.user.id,
                APIToken.is_active == True
            )
        )
    )
    
    if existing_tokens_count >= 10:  # Max 10 active tokens per user
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of API tokens reached (10). Please revoke unused tokens."
        )
    
    # Validation: Ensure requested permissions are subset of user permissions
    user_permissions = set(context.permissions.keys() if isinstance(context.permissions, dict) 
                          else context._get_role_permissions())
    requested_permissions = set(token_request.permissions or [])
    
    if not requested_permissions.issubset(user_permissions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested permissions exceed user's current permissions"
        )
    
    # Generate secure token
    raw_token = secrets.token_urlsafe(32)
    token_hash = auth_service.get_password_hash(raw_token)
    
    # Create token record
    api_token = APIToken(
        user_id=context.user.id,
        organization_id=context.organization.id,
        name=token_request.name,
        token_hash=token_hash,
        permissions=token_request.permissions or list(user_permissions),
        expires_at=datetime.now(timezone.utc) + timedelta(days=token_request.expires_days),
        is_active=True
    )
    
    db.add(api_token)
    await db.commit()
    await db.refresh(api_token)
    
    # Log token generation for audit
    logger.info(f"API token generated: user={context.user.email}, org={context.organization.name}, name={token_request.name}")
    
    return APITokenResponse(
        token=f"ai_{settings.environment[:4]}_{raw_token}",  # Environment-prefixed token
        id=api_token.id,
        name=api_token.name,
        permissions=api_token.permissions,
        created_at=api_token.created_at,
        expires_at=api_token.expires_at,
        organization_id=context.organization.id,
        organization_name=context.organization.name,
        warning="Save this token securely - it will not be displayed again!"
    )
```

**Step 3: Token Display and Security Warning**
```jsx
// Token display component (shown only once)
function TokenGenerated({ tokenResponse, onClose }) {
  const [copied, setCopied] = useState(false)
  
  const copyToken = async () => {
    await navigator.clipboard.writeText(tokenResponse.token)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  
  return (
    <div className="token-generated-modal">
      <div className="modal-content">
        <h3>🔑 API Token Generated Successfully</h3>
        
        <div className="token-display">
          <label>Your API Token:</label>
          <div className="token-box">
            <code>{tokenResponse.token}</code>
            <button onClick={copyToken}>
              {copied ? '✓ Copied' : 'Copy'}
            </button>
          </div>
        </div>
        
        <div className="security-warning">
          <h4>⚠️ Important Security Information</h4>
          <ul>
            <li>This token will <strong>not be displayed again</strong></li>
            <li>Store it securely in your password manager or secrets vault</li>
            <li>Never share this token or commit it to version control</li>
            <li>Token is scoped to organization: <strong>{tokenResponse.organization_name}</strong></li>
            <li>Token expires: <strong>{formatDate(tokenResponse.expires_at)}</strong></li>
          </ul>
        </div>
        
        <div className="usage-example">
          <h4>Usage Example</h4>
          <pre><code>{`curl -X GET "https://api.tickaido.com/api/v1/tickets" \\
  -H "Authorization: Bearer ${tokenResponse.token}" \\
  -H "Content-Type: application/json"`}</code></pre>
        </div>
        
        <button onClick={onClose} className="primary">
          I've Saved My Token Securely
        </button>
      </div>
    </div>
  )
}
```

### Required Implementation Changes

#### 1. Database Schema Updates
```sql
-- Remove old API key fields from users table
ALTER TABLE users DROP COLUMN api_key_hash;
ALTER TABLE users DROP COLUMN api_key_created_at;
ALTER TABLE users DROP COLUMN api_key_last_used_at;
ALTER TABLE users DROP COLUMN rate_limit_override;

-- Create new API tokens table
CREATE TABLE api_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    permissions JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    last_used_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    CONSTRAINT api_tokens_user_name_unique UNIQUE(user_id, name)
);

CREATE INDEX idx_api_tokens_hash ON api_tokens(token_hash);
CREATE INDEX idx_api_tokens_user ON api_tokens(user_id);
CREATE INDEX idx_api_tokens_org ON api_tokens(organization_id);
```

#### 2. Authentication Middleware Changes
```python
# Remove old API key validation logic
# OLD: Check user.api_key_hash field
# NEW: Query api_tokens table with organization context

async def authenticate_api_request(token: str) -> Optional[User]:
    """NEW: Enhanced API token authentication with organization context"""
    
    if not token.startswith("ai_"):
        raise HTTPException(400, "Invalid token format")
    
    # Parse environment-specific token format: ai_env_token
    parts = token.split('_', 2)
    if len(parts) != 3 or parts[0] != 'ai':
        raise HTTPException(400, "Invalid token format")
    
    env_prefix, raw_token = parts[1], parts[2]
    
    # Validate environment matches current environment
    from app.config.settings import get_settings
    settings = get_settings()
    expected_env = settings.environment[:4]  # prod, stag, dev
    if env_prefix != expected_env:
        raise HTTPException(400, f"Token environment mismatch: expected {expected_env}, got {env_prefix}")
    
    async with get_db_session() as db:
        result = await db.execute(
            select(APIToken, User, Organization)
            .join(User, APIToken.user_id == User.id)
            .join(Organization, APIToken.organization_id == Organization.id)
            .where(
                and_(
                    APIToken.token_hash == hash_token(raw_token),
                    APIToken.is_active == True,
                    APIToken.expires_at > datetime.now(timezone.utc),
                    User.is_active == True,
                    Organization.is_active == True
                )
            )
        )
        
        token_data = result.first()
        if not token_data:
            return None
        
        api_token, user, organization = token_data
        
        # Update usage tracking
        api_token.last_used_at = datetime.now(timezone.utc)
        await db.commit()
        
        # Set organization context for request
        request.state.api_token = api_token
        request.state.organization_context = OrganizationContext(
            organization=organization,
            user=user,
            permissions=api_token.permissions
        )
        
        return user
```

#### 3. User Model Updates
```python
# Add API token relationship to User model
class User(BaseModel):
    # Remove old API key fields:
    # api_key_hash = Column(...)  # REMOVE
    # api_key_created_at = Column(...)  # REMOVE
    # api_key_last_used_at = Column(...)  # REMOVE
    
    # Add new relationship
    api_tokens = relationship("APIToken", back_populates="user", cascade="all, delete-orphan")
    
    # Remove old methods:
    # def generate_api_key(self):  # REMOVE
    # def update_api_key_usage(self):  # REMOVE
    
    # Add new method
    def can_generate_api_token(self) -> bool:
        """Check if user can generate API tokens"""
        return self.has_permission("api:generate")
```

#### 4. API Documentation Updates
```yaml
# Update OpenAPI spec for new authentication
paths:
  /api/v1/tickets:
    get:
      security:
        - Auth: []         # Web/mobile authentication via Clerk
        - APIToken: []     # API token authentication
      # ...

components:
  securitySchemes:
    Auth:
      type: http
      scheme: bearer
      description: "Authentication token (Clerk session or API token)"
    APIToken:
      type: http
      scheme: bearer  
      description: "Organization-scoped API token (format: ai_env_...)"
      example: "ai_prod_AbCdEf123456789..."
```

### User Journey: Getting an API Token

1. **Login to Dashboard**: User authenticates via Clerk (Google/Microsoft/GitHub SSO)
2. **Navigate to API Section**: User goes to Settings → API Tokens
3. **Generate Token**: User fills out form (name, permissions, expiration)
4. **Receive Token**: System displays token once with security warnings
5. **Use Token**: User copies token and uses in API requests with `Authorization: Bearer ai_env_...`
6. **Manage Tokens**: User can view, rename, or revoke tokens in dashboard

This eliminates the current simple API key system and replaces it with a more sophisticated, organization-aware token system that integrates seamlessly with Clerk authentication.

---

## Organization & Tenant Management Strategy

### Clerk Organizations Overview

Clerk's Organizations feature provides native multi-tenant support, allowing secure organization isolation with role-based permissions. Each user belongs to a single organization, ensuring clear data boundaries and simplified permission management.

### Organization Architecture Design

#### Multi-Tenant Data Model
```python
# Enhanced User-Organization Relationship
class OrganizationMembership(BaseModel):
    """Junction table for user-organization relationships with roles"""
    __tablename__ = "organization_memberships"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)
    
    # Clerk-specific fields
    clerk_organization_id = Column(String(255), nullable=False, index=True)
    clerk_membership_id = Column(String(255), unique=True, nullable=False)
    
    # Role and permissions
    role = Column(SQLEnum(OrganizationRole), nullable=False)
    permissions = Column(JSON, nullable=True, comment="Custom permissions JSON")
    
    # Membership metadata
    joined_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    invited_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    status = Column(String(50), default='active')  # active, suspended, pending
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('user_id', 'organization_id', name='unique_user_org'),
        UniqueConstraint('clerk_membership_id', name='unique_clerk_membership'),
    )

class Organization(BaseModel):
    """Enhanced organization model with Clerk integration"""
    __tablename__ = "organizations"
    
    # Existing fields...
    clerk_organization_id = Column(String(255), unique=True, nullable=True, index=True)
    
    # Organization settings
    settings = Column(JSON, nullable=True, comment="Organization-specific settings")
    billing_plan = Column(String(50), default='free')
    max_users = Column(Integer, default=10)
    
    # Clerk organization metadata sync
    clerk_metadata = Column(JSON, nullable=True, comment="Synced Clerk organization data")
```

#### Permission Matrix (Simplified)

| Role | Permissions | Description |
|------|-------------|-------------|
| **Admin** | All permissions (`*`) | Full access to all organization features and data |
| **Member** | All permissions (`*`) | Full access to all organization features and data |

**Rationale**: Simplified permission model with two roles:
- **Admin**: Organization administrators who can manage members and settings
- **Member**: Regular users with full access to organizational features
- Both roles have complete access since the application uses organization-level isolation for security

#### Organization Context Middleware

```python
# app/middleware/organization_middleware.py
#!/usr/bin/env python3
"""
Organization context middleware for multi-tenant request handling
"""

import logging
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db_session
from app.models.user import User
from app.models.organization import Organization, OrganizationMembership
from app.middleware.clerk_middleware import get_current_user

logger = logging.getLogger(__name__)

class OrganizationContext:
    """Container for organization context information"""
    def __init__(
        self, 
        organization: Organization,
        membership: OrganizationMembership,
        user: User
    ):
        self.organization = organization
        self.membership = membership
        self.user = user
        self.role = membership.role
        self.permissions = membership.permissions or {}
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission in this organization"""
        # Owner has all permissions
        if self.role == OrganizationRole.OWNER:
            return True
        
        # Check role-based permissions
        role_permissions = self._get_role_permissions()
        if permission in role_permissions:
            return True
        
        # Check custom permissions
        return self.permissions.get(permission, False)
    
    def _get_role_permissions(self) -> list[str]:
        """Get permissions for current role"""
        permissions_map = {
            OrganizationRole.ADMIN: ["*"],  # All permissions
            OrganizationRole.MEMBER: ["*"]  # All permissions
        }
        return permissions_map.get(self.role, ["*"])  # Default to all permissions

class OrganizationMiddleware:
    """Middleware to handle organization context for requests"""
    
    async def __call__(
        self,
        request: Request,
        user: User = Depends(get_current_user)
    ) -> Optional[OrganizationContext]:
        """Extract and validate organization context"""
        
        # Get organization ID from header, query param, or path
        org_id = (
            request.headers.get("X-Organization-ID") or
            request.query_params.get("org_id") or
            request.path_params.get("org_id")
        )
        
        if not org_id:
            # For endpoints that don't require organization context
            return None
        
        async with get_db_session() as db:
            # Get organization membership
            result = await db.execute(
                select(OrganizationMembership, Organization).join(Organization).where(
                    and_(
                        OrganizationMembership.user_id == user.id,
                        OrganizationMembership.organization_id == org_id,
                        OrganizationMembership.status == 'active'
                    )
                )
            )
            membership_org = result.first()
            
            if not membership_org:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User does not have access to this organization"
                )
            
            membership, organization = membership_org
            return OrganizationContext(organization, membership, user)

# Global middleware instance
org_middleware = OrganizationMiddleware()

async def get_organization_context(
    context: OrganizationContext = Depends(org_middleware)
) -> OrganizationContext:
    """Dependency to get organization context (required)"""
    if not context:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )
    return context

async def get_organization_context_optional(
    context: Optional[OrganizationContext] = Depends(org_middleware)
) -> Optional[OrganizationContext]:
    """Dependency to get organization context (optional)"""
    return context
```

### Clerk Organizations API Integration

#### Step 1: Clerk Organization Service
```python
# app/services/clerk_organization_service.py
#!/usr/bin/env python3
"""
Clerk Organizations API integration service
"""

import logging
from typing import Optional, Dict, Any, List
from clerk_sdk import Clerk

from app.services.clerk_service import clerk_service

logger = logging.getLogger(__name__)

class ClerkOrganizationService:
    """Service for Clerk Organizations API integration"""
    
    def __init__(self):
        self.client = clerk_service.client
    
    async def create_organization(
        self,
        name: str,
        slug: str,
        created_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Create organization in Clerk"""
        try:
            org = self.client.organizations.create(
                name=name,
                slug=slug,
                created_by=created_by,
                private_metadata=metadata or {}
            )
            return self._format_organization_data(org)
        except Exception as e:
            logger.error(f"Failed to create organization: {e}")
            return None
    
    async def get_organization(self, org_id: str) -> Optional[Dict[str, Any]]:
        """Get organization by ID from Clerk"""
        try:
            org = self.client.organizations.get(org_id)
            return self._format_organization_data(org)
        except Exception as e:
            logger.error(f"Failed to get organization {org_id}: {e}")
            return None
    
    async def update_organization(
        self,
        org_id: str,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update organization in Clerk"""
        try:
            update_data = {}
            if name:
                update_data['name'] = name
            if slug:
                update_data['slug'] = slug
            if metadata:
                update_data['private_metadata'] = metadata
            
            self.client.organizations.update(org_id, **update_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update organization {org_id}: {e}")
            return False
    
    async def add_member(
        self,
        org_id: str,
        user_id: str,
        role: str = "basic_member"
    ) -> Optional[Dict[str, Any]]:
        """Add user to organization with role"""
        try:
            membership = self.client.organization_memberships.create(
                organization_id=org_id,
                user_id=user_id,
                role=role
            )
            return self._format_membership_data(membership)
        except Exception as e:
            logger.error(f"Failed to add member to organization: {e}")
            return None
    
    async def update_member_role(
        self,
        membership_id: str,
        role: str
    ) -> bool:
        """Update member role in organization"""
        try:
            self.client.organization_memberships.update(
                membership_id,
                role=role
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update member role: {e}")
            return False
    
    async def remove_member(self, membership_id: str) -> bool:
        """Remove member from organization"""
        try:
            self.client.organization_memberships.delete(membership_id)
            return True
        except Exception as e:
            logger.error(f"Failed to remove member: {e}")
            return False
    
    async def list_members(self, org_id: str) -> List[Dict[str, Any]]:
        """List all members of organization"""
        try:
            memberships = self.client.organization_memberships.list(
                organization_id=org_id
            )
            return [self._format_membership_data(m) for m in memberships]
        except Exception as e:
            logger.error(f"Failed to list members: {e}")
            return []
    
    async def create_invitation(
        self,
        org_id: str,
        email: str,
        role: str = "basic_member",
        inviter_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create organization invitation"""
        try:
            invitation = self.client.organization_invitations.create(
                organization_id=org_id,
                email_address=email,
                role=role,
                inviter_id=inviter_id
            )
            return self._format_invitation_data(invitation)
        except Exception as e:
            logger.error(f"Failed to create invitation: {e}")
            return None
    
    def _format_organization_data(self, org) -> Dict[str, Any]:
        """Format Clerk organization data"""
        return {
            'clerk_id': org.id,
            'name': org.name,
            'slug': org.slug,
            'image_url': org.image_url,
            'created_at': org.created_at,
            'updated_at': org.updated_at,
            'members_count': org.members_count,
            'private_metadata': org.private_metadata or {},
            'public_metadata': org.public_metadata or {}
        }
    
    def _format_membership_data(self, membership) -> Dict[str, Any]:
        """Format Clerk membership data"""
        return {
            'clerk_id': membership.id,
            'organization_id': membership.organization.id,
            'user_id': membership.public_user_data.user_id,
            'role': membership.role,
            'created_at': membership.created_at,
            'updated_at': membership.updated_at
        }
    
    def _format_invitation_data(self, invitation) -> Dict[str, Any]:
        """Format Clerk invitation data"""
        return {
            'clerk_id': invitation.id,
            'organization_id': invitation.organization.id,
            'email': invitation.email_address,
            'role': invitation.role,
            'status': invitation.status,
            'created_at': invitation.created_at,
            'expires_at': invitation.expires_at
        }

# Global service instance
clerk_org_service = ClerkOrganizationService()
```

---

## Provider Setup (Google, Microsoft, GitHub)

### Google OAuth Setup

#### Step 1: Google Cloud Console Configuration
1. **Navigate to Google Cloud Console**
   - Go to [console.cloud.google.com](https://console.cloud.google.com)
   - Select or create a project

2. **Enable Google+ API**
   ```bash
   # Enable the API
   gcloud services enable plus.googleapis.com
   gcloud services enable oauth2.googleapis.com
   ```

3. **Create OAuth 2.0 Credentials**
   - Navigate to **APIs & Services → Credentials**
   - Click **Create Credentials → OAuth 2.0 Client IDs**
   - Select **Web application**
   - Configure settings:
     ```
     Name: AI Ticket Creator - Clerk Integration
     Authorized JavaScript origins:
     - https://accounts.clerk.com
     - https://your-domain.com
     
     Authorized redirect URIs:
     - https://accounts.clerk.com/v1/oauth_callback
     - https://clerk.your-domain.com/v1/oauth_callback
     ```

4. **Configure OAuth Consent Screen**
   - Select **External** user type
   - Fill required fields:
     ```
     App name: AI Ticket Creator
     User support email: support@your-domain.com
     Developer contact: dev@your-domain.com
     ```
   - Add scopes:
     - `openid`
     - `email` 
     - `profile`
   - Add test users during development

#### Step 2: Clerk Configuration
1. **Add Google Provider in Clerk Dashboard**
   - Navigate to **User & Authentication → Social Connections**
   - Enable **Google**
   - Enter credentials:
     ```
     Client ID: [From Google Cloud Console]
     Client Secret: [From Google Cloud Console]
     ```

2. **Configure Provider Settings**
   ```javascript
   // Clerk configuration
   {
     "google": {
       "clientId": "123456789-abcd.apps.googleusercontent.com",
       "scopes": ["openid", "email", "profile"],
       "redirectUrl": "https://accounts.clerk.com/v1/oauth_callback",
       "strategy": "oauth_google"
     }
   }
   ```

### Microsoft Entra ID (Azure AD) Setup

#### Step 1: Azure Portal Configuration
1. **Register Application**
   - Navigate to [portal.azure.com](https://portal.azure.com)
   - Go to **Azure Active Directory → App registrations**
   - Click **New registration**
   - Configure:
     ```
     Name: AI Ticket Creator Clerk Integration
     Supported account types: 
       - Accounts in any organizational directory (Any Azure AD directory - Multitenant)
       - Personal Microsoft accounts (e.g. Skype, Xbox)
     Redirect URI: https://accounts.clerk.com/v1/oauth_callback
     ```

2. **Configure Authentication**
   - Navigate to **Authentication** section
   - Add platform → **Web**
   - Add redirect URIs:
     ```
     https://accounts.clerk.com/v1/oauth_callback
     https://clerk.your-domain.com/v1/oauth_callback
     ```
   - Enable **ID tokens** and **Access tokens**

3. **Configure API Permissions**
   - Navigate to **API permissions**
   - Add permissions:
     ```
     Microsoft Graph:
     - openid (Sign users in)
     - email (View users' email address)  
     - profile (View users' basic profile)
     - User.Read (Read user profile)
     ```

4. **Generate Client Secret**
   - Navigate to **Certificates & secrets**
   - Click **New client secret**
   - Description: `Clerk Integration Secret`
   - Expires: `24 months`
   - **Copy the secret value immediately**

#### Step 2: Clerk Configuration
1. **Add Microsoft Provider**
   - Navigate to **User & Authentication → Social Connections**
   - Enable **Microsoft**
   - Configure:
     ```
     Client ID: [Application (client) ID from Azure]
     Client Secret: [Secret value from Azure]
     Tenant ID: common (for multi-tenant) or specific tenant ID
     ```

2. **Advanced Configuration**
   ```javascript
   {
     "microsoft": {
       "clientId": "12345678-1234-1234-1234-123456789abc",
       "tenantId": "common",
       "scopes": ["openid", "email", "profile"],
       "redirectUrl": "https://accounts.clerk.com/v1/oauth_callback",
       "strategy": "oauth_microsoft"
     }
   }
   ```

### GitHub OAuth Setup

#### Step 1: GitHub Application Configuration
1. **Create OAuth App**
   - Navigate to [github.com/settings/developers](https://github.com/settings/developers)
   - Click **New OAuth App**
   - Configure:
     ```
     Application name: AI Ticket Creator
     Homepage URL: https://your-domain.com
     Authorization callback URL: https://accounts.clerk.com/v1/oauth_callback
     Application description: AI-powered ticket management system
     ```

2. **Generate Client Secret**
   - Click **Generate a new client secret**
   - **Copy both Client ID and Client Secret**

3. **Configure Application Settings**
   - Enable **Request user authorization (OAuth) during installation**
   - Set **User authorization callback URL**:
     ```
     https://accounts.clerk.com/v1/oauth_callback
     ```

#### Step 2: Clerk Configuration
1. **Add GitHub Provider**
   - Navigate to **User & Authentication → Social Connections**
   - Enable **GitHub**
   - Configure:
     ```
     Client ID: [Client ID from GitHub]
     Client Secret: [Client Secret from GitHub]
     ```

2. **Scope Configuration**
   ```javascript
   {
     "github": {
       "clientId": "Iv1.a1b2c3d4e5f67890",
       "scopes": ["read:user", "user:email"],
       "redirectUrl": "https://accounts.clerk.com/v1/oauth_callback",
       "strategy": "oauth_github"
     }
   }
   ```

### Provider Testing Matrix

| Provider | Test Account | Expected Scopes | Profile Data |
|----------|--------------|-----------------|--------------|
| **Google** | test@gmail.com | `openid email profile` | `sub`, `email`, `name`, `picture` |
| **Microsoft** | test@outlook.com | `openid email profile` | `oid`, `email`, `name` |
| **GitHub** | github-user | `read:user user:email` | `id`, `login`, `email`, `name`, `avatar_url` |

---

## Implementation Plan

### Phase 1: Clerk Account & Provider Setup (Week 1)

#### Step 1.1: Create Clerk Account & Application
**Configuration Task - No Coding Required**

**Steps:**
1. Navigate to [clerk.com](https://clerk.com)
2. Click "Get started for free" or "Sign up"
3. Create account with your work email
4. Complete onboarding flow
5. Choose "Pro" plan for production features
6. Create new application:
   - Application name: `AI Ticket Creator`
   - Application type: `Web application`
   - Framework: `Other` (we'll configure manually)

**Validation:**
- [ ] Clerk dashboard accessible at [dashboard.clerk.com](https://dashboard.clerk.com)
- [ ] Application shows up in applications list
- [ ] Application ID and keys are visible in API Keys section

**Expected Outcome:**
```
Application created successfully
- Application ID: app_xxxxxxxxxxxx
- Publishable Key: pk_test_xxxxxxxxxxxx
- Secret Key: sk_test_xxxxxxxxxxxx (keep secure)
```

---

#### Step 1.2: Configure Google OAuth Provider
**Configuration Task - No Coding Required**

**Google Cloud Console Setup:**

**Steps:**
1. Navigate to [console.cloud.google.com](https://console.cloud.google.com)
2. Select existing project or create new project:
   - Project name: `AI Ticket Creator`
   - Project ID: `ai-ticket-creator-[your-suffix]`
3. Enable APIs:
   - Go to "APIs & Services" → "Library"
   - Search "Google+ API" → Enable
   - Search "OAuth2 API" → Enable
4. Create OAuth consent screen:
   - Go to "APIs & Services" → "OAuth consent screen"
   - User Type: `External`
   - App name: `AI Ticket Creator`
   - User support email: `your-email@domain.com`
   - App logo: Upload your app logo (optional)
   - App domain: `https://your-domain.com`
   - Authorized domains: Add `clerk.com` and your domain
   - Developer contact: `your-email@domain.com`
   - Scopes: Add `openid`, `email`, `profile`
   - Test users: Add your email and team emails
5. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth 2.0 Client IDs"
   - Application type: `Web application`
   - Name: `AI Ticket Creator - Clerk Integration`
   - Authorized JavaScript origins:
     - `https://accounts.clerk.com`
     - `https://your-domain.com` (your actual domain)
   - Authorized redirect URIs:
     - `https://accounts.clerk.com/v1/oauth_callback`
   - Click "Create"
   - **Copy Client ID and Client Secret immediately**

**Clerk Configuration:**
1. In Clerk Dashboard → "User & Authentication" → "Social Connections"
2. Enable "Google"
3. Enter credentials:
   - Client ID: `[from Google Console]`
   - Client Secret: `[from Google Console]`
4. Save configuration

**Validation:**
- [ ] Google OAuth app appears in Google Cloud Console credentials
- [ ] OAuth consent screen configured and shows correct information
- [ ] Clerk dashboard shows Google as "Configured" with green checkmark
- [ ] Test authentication:
  1. Open Clerk's preview URL (found in dashboard)
  2. Click "Sign in with Google"
  3. Should redirect to Google login
  4. After login, should redirect back to Clerk successfully

**Troubleshooting:**
- If redirect fails: Check redirect URIs match exactly
- If consent screen errors: Ensure all required fields completed
- If permission errors: Verify APIs are enabled

---

#### Step 1.3: Configure Microsoft Entra ID Provider
**Configuration Task - No Coding Required**

**Azure Portal Setup:**

**Steps:**
1. Navigate to [portal.azure.com](https://portal.azure.com)
2. Go to "Azure Active Directory" → "App registrations"
3. Click "New registration"
   - Name: `AI Ticket Creator`
   - Supported account types: `Accounts in any organizational directory and personal Microsoft accounts`
   - Redirect URI: `Web` → `https://accounts.clerk.com/v1/oauth_callback`
4. Click "Register"
5. Note the Application (client) ID and Directory (tenant) ID
6. Go to "Authentication" section:
   - Add additional redirect URI: `https://your-domain.com/auth/callback` (if needed)
   - Enable "ID tokens" and "Access tokens"
   - Save changes
7. Go to "API permissions":
   - Click "Add a permission"
   - Select "Microsoft Graph"
   - Select "Delegated permissions"
   - Add: `openid`, `email`, `profile`, `User.Read`
   - Click "Add permissions"
   - Click "Grant admin consent" (if you have admin rights)
8. Go to "Certificates & secrets":
   - Click "New client secret"
   - Description: `Clerk Integration`
   - Expires: `24 months`
   - Click "Add"
   - **Copy the secret VALUE immediately (not the ID)**

**Clerk Configuration:**
1. In Clerk Dashboard → "User & Authentication" → "Social Connections"
2. Enable "Microsoft"
3. Enter credentials:
   - Client ID: `[Application (client) ID from Azure]`
   - Client Secret: `[Secret VALUE from Azure]`
   - Tenant ID: `common` (for multi-tenant) or specific tenant ID
4. Save configuration

**Validation:**
- [ ] App registration visible in Azure AD
- [ ] Client secret created and copied
- [ ] API permissions configured and consented
- [ ] Clerk dashboard shows Microsoft as "Configured"
- [ ] Test authentication:
  1. Open Clerk's preview URL
  2. Click "Sign in with Microsoft"
  3. Should redirect to Microsoft login
  4. After login, should redirect back successfully

**Troubleshooting:**
- If tenant errors: Use "common" for multi-tenant access
- If permission errors: Ensure admin consent granted
- If redirect fails: Check redirect URIs in Authentication section

---

#### Step 1.4: Configure GitHub OAuth Provider
**Configuration Task - No Coding Required**

**GitHub Setup:**

**Steps:**
1. Navigate to [github.com/settings/developers](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill out application details:
   - Application name: `AI Ticket Creator`
   - Homepage URL: `https://your-domain.com`
   - Application description: `AI-powered ticket management system with smart categorization and automated responses`
   - Authorization callback URL: `https://accounts.clerk.com/v1/oauth_callback`
4. Click "Register application"
5. Note the Client ID
6. Click "Generate a new client secret"
7. **Copy the Client Secret immediately**
8. Optional: Upload application logo
9. Optional: Enable "Request user authorization (OAuth) during installation"

**Clerk Configuration:**
1. In Clerk Dashboard → "User & Authentication" → "Social Connections"
2. Enable "GitHub"
3. Enter credentials:
   - Client ID: `[from GitHub OAuth App]`
   - Client Secret: `[from GitHub OAuth App]`
4. Save configuration

**Validation:**
- [ ] GitHub OAuth app visible in your Developer Settings
- [ ] Client ID and secret configured correctly
- [ ] Callback URL matches exactly: `https://accounts.clerk.com/v1/oauth_callback`
- [ ] Clerk dashboard shows GitHub as "Configured"
- [ ] Test authentication:
  1. Open Clerk's preview URL
  2. Click "Sign in with GitHub"
  3. Should redirect to GitHub authorization page
  4. After authorization, should redirect back successfully

**Troubleshooting:**
- If callback errors: Verify callback URL is exactly `https://accounts.clerk.com/v1/oauth_callback`
- If scope errors: GitHub automatically includes `read:user` and `user:email`

---

#### Step 1.5: Configure Clerk Organizations Feature
**Configuration Task - No Coding Required**

**Steps:**
1. In Clerk Dashboard, go to "Organizations"
2. Enable Organizations feature:
   - Toggle "Enable organizations" to ON
   - Organization name requirements: `Minimum 2 characters`
   - Organization slug requirements: `Auto-generate from name`
   - Enable "Allow users to create organizations"
   - Enable "Allow users to leave organizations"
3. Configure roles:
   - Keep default roles: `admin`, `basic_member`  
   - Add custom role if needed: `guest_member`
4. Configure permissions:
   - `admin`: All permissions
   - `basic_member`: Standard member permissions
   - `guest_member`: Read-only permissions (if added)
5. Save settings

**Validation:**
- [ ] Organizations toggle is enabled
- [ ] Role configuration shows admin and basic_member
- [ ] Test organization creation:
  1. Use Clerk's preview to create test user
  2. Create test organization through Clerk UI
  3. Verify organization appears in Clerk dashboard

---

#### Step 1.6: Install Dependencies
**Coding Task**

**Backend Dependencies:**
```bash
# Navigate to project root
cd /Users/aristotle/projects/tickaido-backend

# Install required packages
poetry add clerk-sdk-python itsdangerous

# Verify installation
poetry show clerk-sdk-python
poetry show itsdangerous
```

**Environment Configuration:**
```bash
# Add to .env file
echo "# Clerk Configuration" >> .env
echo "CLERK_SECRET_KEY=sk_test_YOUR_SECRET_KEY_HERE" >> .env
echo "CLERK_PUBLISHABLE_KEY=pk_test_YOUR_PUBLISHABLE_KEY_HERE" >> .env
echo "CLERK_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET_HERE" >> .env

# OAuth Security
echo "OAUTH_STATE_SECRET=your-cryptographically-secure-256-bit-secret-key-here" >> .env
echo "OAUTH_SESSION_TIMEOUT=600" >> .env
```

**Validation:**
```bash
# Test imports
python -c "import clerk_sdk; print('✅ Clerk SDK installed')"
python -c "import itsdangerous; print('✅ itsdangerous installed')"

# Verify environment variables
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
required_vars = ['CLERK_SECRET_KEY', 'CLERK_PUBLISHABLE_KEY']
for var in required_vars:
    if os.getenv(var):
        print(f'✅ {var} configured')
    else:
        print(f'❌ {var} missing')
"
```

**Expected Output:**
```
✅ Clerk SDK installed
✅ itsdangerous installed
✅ CLERK_SECRET_KEY configured
✅ CLERK_PUBLISHABLE_KEY configured
```

---

#### Step 1.7: Basic Clerk Connection Test
**Coding Task**

**Create Test Script:**
```python
# test_clerk_connection.py
#!/usr/bin/env python3
"""Test basic connection to Clerk API"""

import os
import asyncio
from dotenv import load_dotenv
from clerk_sdk import Clerk

async def test_clerk_connection():
    """Test basic Clerk API connectivity"""
    load_dotenv()
    
    # Initialize Clerk client
    secret_key = os.getenv('CLERK_SECRET_KEY')
    if not secret_key:
        print("❌ CLERK_SECRET_KEY not found in environment")
        return False
    
    client = Clerk(api_key=secret_key)
    
    try:
        # Test API connectivity by listing users (should work even if empty)
        users = client.users.list(limit=1)
        print(f"✅ Clerk API connection successful")
        print(f"   API response received (found {len(users)} users)")
        return True
        
    except Exception as e:
        print(f"❌ Clerk API connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_clerk_connection())
    exit(0 if success else 1)
```

**Run Test:**
```bash
# Create and run test
python test_clerk_connection.py
```

**Validation:**
- [ ] Script runs without import errors
- [ ] Clerk API connection succeeds
- [ ] No authentication errors

**Expected Output:**
```
✅ Clerk API connection successful
   API response received (found 0 users)
```

**Troubleshooting:**
- If import errors: Check `poetry install` completed successfully
- If auth errors: Verify `CLERK_SECRET_KEY` is correct and starts with `sk_`
- If network errors: Check internet connection and firewall settings

---

### Phase 1 Completion Checklist

**Configuration Validation:**
- [ ] Clerk account created and accessible
- [ ] Google OAuth configured and tested
- [ ] Microsoft OAuth configured and tested  
- [ ] GitHub OAuth configured and tested
- [ ] Clerk Organizations feature enabled
- [ ] All provider test logins successful

**Technical Validation:**
- [ ] Dependencies installed successfully
- [ ] Environment variables configured
- [ ] Clerk API connection test passes
- [ ] No import or runtime errors

**Documentation:**
- [ ] All OAuth app credentials saved securely
- [ ] Environment variables documented
- [ ] Provider callback URLs recorded

**🚫 STOP: Do not proceed to Phase 2 until all Phase 1 items are completed and validated.**

---

## Phase 2: Backend Integration (Week 2-3)

#### Step 2.1: Create Clerk Service
**Coding Task**

**Create Service File:**
```bash
# Ensure services directory exists
mkdir -p app/services
```

**Implementation:**
Create `app/services/clerk_service.py`:
```python
#!/usr/bin/env python3
"""
Clerk integration service for user authentication and management
"""

import os
import logging
from typing import Optional, Dict, Any, List
from clerk_sdk import Clerk

logger = logging.getLogger(__name__)

class ClerkService:
    """Service for Clerk authentication integration"""
    
    def __init__(self):
        self.client = Clerk(api_key=os.getenv('CLERK_SECRET_KEY'))
        self.webhook_secret = os.getenv('CLERK_WEBHOOK_SECRET')
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify Clerk session token and return user data"""
        try:
            # Verify the session token
            session = self.client.sessions.verify_token(token)
            if not session:
                return None
            
            # Get user data
            user = self.client.users.get(session.user_id)
            return {
                'user_id': user.id,
                'email': user.email_addresses[0].email_address,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'image_url': user.image_url,
                'external_accounts': user.external_accounts,
                'created_at': user.created_at,
                'updated_at': user.updated_at
            }
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Clerk user ID"""
        try:
            user = self.client.users.get(user_id)
            return self._format_user_data(user)
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    async def update_user_metadata(self, user_id: str, metadata: Dict[str, Any]) -> bool:
        """Update user metadata in Clerk"""
        try:
            self.client.users.update(user_id, private_metadata=metadata)
            return True
        except Exception as e:
            logger.error(f"Failed to update user metadata: {e}")
            return False
    
    async def list_users(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List users from Clerk"""
        try:
            users = self.client.users.list(limit=limit, offset=offset)
            return [self._format_user_data(user) for user in users]
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return []
    
    def _format_user_data(self, user) -> Dict[str, Any]:
        """Format Clerk user data for application use"""
        return {
            'clerk_id': user.id,
            'email': user.email_addresses[0].email_address if user.email_addresses else None,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': f"{user.first_name} {user.last_name}".strip(),
            'image_url': user.image_url,
            'phone_number': user.phone_numbers[0].phone_number if user.phone_numbers else None,
            'external_accounts': [
                {
                    'provider': account.provider,
                    'external_id': account.external_id,
                    'email': account.email_address
                }
                for account in user.external_accounts
            ],
            'created_at': user.created_at,
            'updated_at': user.updated_at,
            'last_sign_in_at': user.last_sign_in_at,
            'private_metadata': user.private_metadata or {},
            'public_metadata': user.public_metadata or {}
        }

# Global service instance
clerk_service = ClerkService()
```

**Validation:**
Create test script `test_clerk_service.py`:
```python
#!/usr/bin/env python3
"""Test Clerk service functionality"""

import asyncio
import os
from dotenv import load_dotenv
from app.services.clerk_service import clerk_service

async def test_clerk_service():
    """Test basic Clerk service functionality"""
    load_dotenv()
    
    print("Testing Clerk Service...")
    
    # Test 1: Service initialization
    try:
        service = clerk_service
        print("✅ Clerk service initialized successfully")
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return False
    
    # Test 2: List users (should work even if empty)
    try:
        users = await service.list_users(limit=1)
        print(f"✅ User listing successful (found {len(users)} users)")
    except Exception as e:
        print(f"❌ User listing failed: {e}")
        return False
    
    # Test 3: Invalid token handling
    try:
        result = await service.verify_token("invalid_token")
        if result is None:
            print("✅ Invalid token properly rejected")
        else:
            print("❌ Invalid token incorrectly accepted")
            return False
    except Exception as e:
        print(f"❌ Token verification error handling failed: {e}")
        return False
    
    print("✅ All Clerk service tests passed")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_clerk_service())
    exit(0 if success else 1)
```

**Run Validation:**
```bash
# Test the service
python test_clerk_service.py

# Expected output:
# ✅ Clerk service initialized successfully
# ✅ User listing successful (found 0 users)
# ✅ Invalid token properly rejected
# ✅ All Clerk service tests passed
```

**Checklist:**
- [ ] Service file created without syntax errors
- [ ] Service initializes successfully
- [ ] Can connect to Clerk API
- [ ] Error handling works correctly
- [ ] All tests pass

---

#### Step 2.2: Create Database Migration for Clerk Integration
**Coding Task**

**Create Migration:**
```bash
# Generate migration for Clerk fields
poetry run alembic revision --autogenerate -m "Add Clerk integration fields to users and organizations"

# The migration should include:
# - clerk_id field on users table
# - clerk_organization_id field on organizations table  
# - New api_tokens table
# - Remove old API key fields from users
```

**Migration File Content:**
The generated migration should look like this:
```python
# migrations/versions/xxx_add_clerk_integration_fields.py
"""Add Clerk integration fields to users and organizations

Revision ID: xxx
Create Date: 2025-xx-xx
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Add clerk_id to users table
    op.add_column('users', sa.Column('clerk_id', sa.String(255), nullable=True))
    op.create_index('ix_users_clerk_id', 'users', ['clerk_id'])
    op.create_unique_constraint('unique_users_clerk_id', 'users', ['clerk_id'])
    
    # Add clerk_organization_id to organizations table
    op.add_column('organizations', sa.Column('clerk_organization_id', sa.String(255), nullable=True))
    op.create_index('ix_organizations_clerk_id', 'organizations', ['clerk_organization_id'])
    op.create_unique_constraint('unique_orgs_clerk_id', 'organizations', ['clerk_organization_id'])
    
    # Create api_tokens table
    op.create_table('api_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False),
        sa.Column('permissions', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True)
    )
    
    # Create indexes
    op.create_index('ix_api_tokens_hash', 'api_tokens', ['token_hash'])
    op.create_index('ix_api_tokens_user', 'api_tokens', ['user_id'])
    op.create_index('ix_api_tokens_org', 'api_tokens', ['organization_id'])
    op.create_unique_constraint('unique_token_hash', 'api_tokens', ['token_hash'])
    
    # Remove old API key fields from users (optional - can be done later)
    # op.drop_column('users', 'api_key_hash')
    # op.drop_column('users', 'api_key_created_at')
    # op.drop_column('users', 'api_key_last_used_at')

def downgrade():
    # Reverse the changes
    op.drop_table('api_tokens')
    op.drop_column('organizations', 'clerk_organization_id')
    op.drop_column('users', 'clerk_id')
```

**Apply Migration:**
```bash
# Apply the migration
poetry run alembic upgrade head

# Verify migration applied
poetry run alembic current

# Check database schema
poetry run python -c "
from app.database import engine
from sqlalchemy import text
import asyncio

async def check_schema():
    async with engine.begin() as conn:
        result = await conn.execute(text(\"\"\"
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'clerk_id'
        \"\"\"))
        if result.rowcount > 0:
            print('✅ clerk_id column added to users table')
        else:
            print('❌ clerk_id column missing')

asyncio.run(check_schema())
"
```

**Validation:**
- [ ] Migration file generated successfully
- [ ] Migration applies without errors
- [ ] `clerk_id` column exists in `users` table
- [ ] `clerk_organization_id` column exists in `organizations` table
- [ ] `api_tokens` table created with correct schema
- [ ] All indexes and constraints created

**Expected Output:**
```
✅ clerk_id column added to users table
✅ clerk_organization_id column added to organizations table
✅ api_tokens table created successfully
```

---

#### Step 2.3: Create Enhanced Authentication Middleware
**Coding Task**

**Implementation:**
Create `app/middleware/enhanced_auth_middleware.py`:

#### Step 3: Create Clerk Middleware
Create `app/middleware/clerk_middleware.py`:
```python
#!/usr/bin/env python3
"""
Clerk authentication middleware for FastAPI
"""

import logging
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.clerk_service import clerk_service
from app.models.user import User
from app.database import get_db_session

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

class ClerkAuthMiddleware:
    """Clerk authentication middleware"""
    
    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Optional[User]:
        """Authenticate request using Clerk token"""
        
        if not credentials:
            return None
        
        # Extract token
        token = credentials.credentials
        
        # Verify with Clerk
        clerk_user = await clerk_service.verify_token(token)
        if not clerk_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        # Get or create local user record
        async with get_db_session() as db:
            user = await self._sync_local_user(db, clerk_user)
            return user
    
    async def _sync_local_user(self, db, clerk_user: dict) -> User:
        """Sync Clerk user data with local database"""
        from sqlalchemy import select
        
        # Look for existing user by Clerk ID or email
        result = await db.execute(
            select(User).where(
                (User.clerk_id == clerk_user['user_id']) |
                (User.email == clerk_user['email'])
            )
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Update existing user
            user.clerk_id = clerk_user['user_id']
            user.email = clerk_user['email']
            user.full_name = f"{clerk_user.get('first_name', '')} {clerk_user.get('last_name', '')}".strip()
            user.avatar_url = clerk_user.get('image_url')
            user.is_verified = True  # Clerk handles verification
        else:
            # Create new user
            user = User(
                clerk_id=clerk_user['user_id'],
                email=clerk_user['email'],
                full_name=f"{clerk_user.get('first_name', '')} {clerk_user.get('last_name', '')}".strip(),
                avatar_url=clerk_user.get('image_url'),
                is_verified=True,
                is_active=True,
                external_auth_provider='clerk',
                external_auth_id=clerk_user['user_id']
            )
            db.add(user)
        
        await db.commit()
        await db.refresh(user)
        return user

# Global middleware instance
clerk_auth = ClerkAuthMiddleware()

async def get_current_user(
    user: User = Depends(clerk_auth)
) -> User:
    """Dependency to get current authenticated user"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user

async def get_current_user_optional(
    user: Optional[User] = Depends(clerk_auth)
) -> Optional[User]:
    """Dependency to get current user (optional)"""
    return user
```

#### Step 4: Update User Model
Add Clerk ID field to `app/models/user.py`:
```python
# Add to User model
clerk_id = Column(
    String(255),
    unique=True,
    nullable=True,
    index=True,
    comment="Clerk user ID"
)
```

#### Step 5: Create Database Migration
```bash
poetry run alembic revision --autogenerate -m "Add clerk_id to users table"
poetry run alembic upgrade head
```

### Phase 3: Webhook Integration (Week 2)

#### Step 1: Create Webhook Handler
Create `app/routers/clerk_webhooks.py`:
```python
#!/usr/bin/env python3
"""
Clerk webhook handlers for real-time user synchronization
"""

import logging
import hmac
import hashlib
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.user import User
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/clerk", tags=["Clerk Webhooks"])
settings = get_settings()

async def verify_webhook_signature(request: Request) -> bool:
    """Verify Clerk webhook signature"""
    signature = request.headers.get('svix-signature')
    timestamp = request.headers.get('svix-timestamp') 
    
    if not signature or not timestamp:
        return False
    
    body = await request.body()
    expected_signature = hmac.new(
        settings.clerk_webhook_secret.encode(),
        f"{timestamp}.{body.decode()}".encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature.split(',')[1].split('=')[1], expected_signature)

@router.post("/user-events")
async def handle_user_events(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Handle Clerk user events (created, updated, deleted)"""
    
    # Verify webhook signature
    if not await verify_webhook_signature(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse webhook payload
    payload = await request.json()
    event_type = payload.get('type')
    user_data = payload.get('data')
    
    logger.info(f"Received Clerk webhook: {event_type}")
    
    try:
        if event_type == 'user.created':
            await handle_user_created(db, user_data)
        elif event_type == 'user.updated':
            await handle_user_updated(db, user_data)
        elif event_type == 'user.deleted':
            await handle_user_deleted(db, user_data)
        elif event_type == 'session.created':
            await handle_session_created(db, user_data)
        elif event_type == 'session.ended':
            await handle_session_ended(db, user_data)
        
        return {"status": "success"}
    
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )

async def handle_user_created(db: AsyncSession, user_data: Dict[str, Any]):
    """Handle user creation from Clerk"""
    from sqlalchemy import select
    
    clerk_id = user_data.get('id')
    email = user_data.get('email_addresses', [{}])[0].get('email_address')
    
    # Check if user already exists
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    existing_user = result.scalar_one_or_none()
    
    if not existing_user:
        new_user = User(
            clerk_id=clerk_id,
            email=email,
            full_name=f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
            avatar_url=user_data.get('image_url'),
            is_verified=True,
            is_active=True,
            external_auth_provider='clerk',
            external_auth_id=clerk_id
        )
        db.add(new_user)
        await db.commit()
        logger.info(f"Created user from Clerk webhook: {email}")

async def handle_user_updated(db: AsyncSession, user_data: Dict[str, Any]):
    """Handle user updates from Clerk"""
    from sqlalchemy import select
    
    clerk_id = user_data.get('id')
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    
    if user:
        # Update user data
        email = user_data.get('email_addresses', [{}])[0].get('email_address')
        user.email = email
        user.full_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
        user.avatar_url = user_data.get('image_url')
        
        await db.commit()
        logger.info(f"Updated user from Clerk webhook: {email}")

async def handle_user_deleted(db: AsyncSession, user_data: Dict[str, Any]):
    """Handle user deletion from Clerk"""
    from sqlalchemy import select
    
    clerk_id = user_data.get('id')
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    
    if user:
        # Soft delete or anonymize user
        user.is_active = False
        user.email = f"deleted-{user.id}@example.com"
        user.full_name = "Deleted User"
        
        await db.commit()
        logger.info(f"Soft deleted user from Clerk webhook: {clerk_id}")

async def handle_session_created(db: AsyncSession, session_data: Dict[str, Any]):
    """Handle session creation for audit logging"""
    logger.info(f"User session created: {session_data.get('user_id')}")
    # Implement audit logging here

async def handle_session_ended(db: AsyncSession, session_data: Dict[str, Any]):
    """Handle session end for audit logging"""
    logger.info(f"User session ended: {session_data.get('user_id')}")
    # Implement audit logging here
```

#### Step 2: Organization Webhook Handlers
Add organization webhook handling to `app/routers/clerk_webhooks.py`:
```python
@router.post("/organization-events")
async def handle_organization_events(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Handle Clerk organization events"""
    
    # Verify webhook signature
    if not await verify_webhook_signature(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    payload = await request.json()
    event_type = payload.get('type')
    data = payload.get('data')
    
    logger.info(f"Received Clerk organization webhook: {event_type}")
    
    try:
        if event_type == 'organization.created':
            await handle_organization_created(db, data)
        elif event_type == 'organization.updated':
            await handle_organization_updated(db, data)
        elif event_type == 'organization.deleted':
            await handle_organization_deleted(db, data)
        elif event_type == 'organizationMembership.created':
            await handle_membership_created(db, data)
        elif event_type == 'organizationMembership.updated':
            await handle_membership_updated(db, data)
        elif event_type == 'organizationMembership.deleted':
            await handle_membership_deleted(db, data)
        elif event_type == 'organizationInvitation.created':
            await handle_invitation_created(db, data)
        elif event_type == 'organizationInvitation.accepted':
            await handle_invitation_accepted(db, data)
        elif event_type == 'organizationInvitation.revoked':
            await handle_invitation_revoked(db, data)
        
        return {"status": "success"}
    
    except Exception as e:
        logger.error(f"Organization webhook processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )

async def handle_organization_created(db: AsyncSession, org_data: Dict[str, Any]):
    """Sync organization creation from Clerk"""
    from sqlalchemy import select
    from app.models.organization import Organization
    
    clerk_org_id = org_data.get('id')
    
    # Check if organization already exists
    result = await db.execute(
        select(Organization).where(Organization.clerk_organization_id == clerk_org_id)
    )
    existing_org = result.scalar_one_or_none()
    
    if not existing_org:
        new_org = Organization(
            clerk_organization_id=clerk_org_id,
            name=org_data.get('name'),
            slug=org_data.get('slug'),
            description=f"Organization synced from Clerk: {org_data.get('name')}",
            clerk_metadata=org_data
        )
        db.add(new_org)
        await db.commit()
        logger.info(f"Created organization from Clerk webhook: {org_data.get('name')}")

async def handle_membership_created(db: AsyncSession, membership_data: Dict[str, Any]):
    """Sync organization membership creation from Clerk"""
    from sqlalchemy import select
    from app.models.user import User
    from app.models.organization import Organization, OrganizationMembership
    
    clerk_membership_id = membership_data.get('id')
    clerk_org_id = membership_data.get('organization', {}).get('id')
    clerk_user_id = membership_data.get('public_user_data', {}).get('user_id')
    role = membership_data.get('role', 'basic_member')
    
    # Map Clerk roles to our roles (simplified)
    role_mapping = {
        'admin': OrganizationRole.ADMIN,
        'basic_member': OrganizationRole.MEMBER
    }
    
    # Get local user and organization
    user_result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
    user = user_result.scalar_one_or_none()
    
    org_result = await db.execute(
        select(Organization).where(Organization.clerk_organization_id == clerk_org_id)
    )
    org = org_result.scalar_one_or_none()
    
    if user and org:
        # Create membership
        membership = OrganizationMembership(
            user_id=user.id,
            organization_id=org.id,
            clerk_organization_id=clerk_org_id,
            clerk_membership_id=clerk_membership_id,
            role=role_mapping.get(role, OrganizationRole.MEMBER),
            status='active'
        )
        db.add(membership)
        await db.commit()
        logger.info(f"Created membership: {user.email} -> {org.name} as {role}")
```

#### Step 3: Organization API Routes
Create `app/routers/organizations.py`:
```python
#!/usr/bin/env python3
"""
Organization management API routes with Clerk integration
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db_session
from app.models.organization import Organization, OrganizationMembership
from app.models.user import User
from app.schemas.organization import (
    OrganizationResponse, OrganizationCreateRequest, OrganizationUpdateRequest,
    OrganizationMemberResponse, OrganizationInviteRequest
)
from app.middleware.clerk_middleware import get_current_user
from app.middleware.organization_middleware import get_organization_context, OrganizationContext
from app.services.clerk_organization_service import clerk_org_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations", tags=["Organization Management"])

@router.get("/", response_model=List[OrganizationResponse])
async def list_user_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List all organizations the current user belongs to"""
    
    result = await db.execute(
        select(Organization, OrganizationMembership)
        .join(OrganizationMembership)
        .where(
            and_(
                OrganizationMembership.user_id == current_user.id,
                OrganizationMembership.status == 'active'
            )
        )
    )
    
    organizations = []
    for org, membership in result.all():
        org_data = OrganizationResponse.from_orm(org)
        org_data.user_role = membership.role
        org_data.user_permissions = membership.permissions
        organizations.append(org_data)
    
    return organizations

@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new organization"""
    
    # Create organization in Clerk first
    clerk_org = await clerk_org_service.create_organization(
        name=org_data.name,
        slug=org_data.slug or org_data.name.lower().replace(' ', '-'),
        created_by=current_user.clerk_id,
        metadata={
            'created_by_user_id': str(current_user.id),
            'billing_plan': org_data.billing_plan or 'free'
        }
    )
    
    if not clerk_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create organization in Clerk"
        )
    
    # Create local organization record
    new_org = Organization(
        name=org_data.name,
        slug=org_data.slug or org_data.name.lower().replace(' ', '-'),
        description=org_data.description,
        clerk_organization_id=clerk_org['clerk_id'],
        settings=org_data.settings or {},
        billing_plan=org_data.billing_plan or 'free',
        clerk_metadata=clerk_org
    )
    
    db.add(new_org)
    await db.commit()
    await db.refresh(new_org)
    
    # Add creator as owner
    membership = OrganizationMembership(
        user_id=current_user.id,
        organization_id=new_org.id,
        clerk_organization_id=clerk_org['clerk_id'],
        role=OrganizationRole.OWNER,
        status='active'
    )
    
    # Add member to Clerk organization
    clerk_membership = await clerk_org_service.add_member(
        org_id=clerk_org['clerk_id'],
        user_id=current_user.clerk_id,
        role='admin'  # Owner maps to admin in Clerk
    )
    
    if clerk_membership:
        membership.clerk_membership_id = clerk_membership['clerk_id']
    
    db.add(membership)
    await db.commit()
    
    logger.info(f"Created organization: {new_org.name} by {current_user.email}")
    
    response = OrganizationResponse.from_orm(new_org)
    response.user_role = OrganizationRole.OWNER
    response.member_count = 1
    
    return response

@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    context: OrganizationContext = Depends(get_organization_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Get organization details"""
    
    # Verify access through middleware
    if context.organization.id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    # Get member count
    result = await db.execute(
        select(func.count(OrganizationMembership.id)).where(
            and_(
                OrganizationMembership.organization_id == org_id,
                OrganizationMembership.status == 'active'
            )
        )
    )
    member_count = result.scalar() or 0
    
    response = OrganizationResponse.from_orm(context.organization)
    response.user_role = context.role
    response.user_permissions = context.permissions
    response.member_count = member_count
    
    return response

@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: UUID,
    update_data: OrganizationUpdateRequest,
    context: OrganizationContext = Depends(get_organization_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Update organization details"""
    
    # Check permissions
    if not context.has_permission("settings:update"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update organization"
        )
    
    org = context.organization
    
    # Update in Clerk
    if update_data.name or update_data.slug:
        await clerk_org_service.update_organization(
            org_id=org.clerk_organization_id,
            name=update_data.name,
            slug=update_data.slug
        )
    
    # Update local record
    if update_data.name:
        org.name = update_data.name
    if update_data.description:
        org.description = update_data.description
    if update_data.slug:
        org.slug = update_data.slug
    if update_data.settings:
        org.settings = {**(org.settings or {}), **update_data.settings}
    
    await db.commit()
    
    response = OrganizationResponse.from_orm(org)
    response.user_role = context.role
    
    return response

@router.get("/{org_id}/members", response_model=List[OrganizationMemberResponse])
async def list_organization_members(
    org_id: UUID,
    context: OrganizationContext = Depends(get_organization_context),
    db: AsyncSession = Depends(get_db_session)
):
    """List organization members"""
    
    # Check permissions
    if not context.has_permission("users:read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view members"
        )
    
    result = await db.execute(
        select(User, OrganizationMembership).join(OrganizationMembership).where(
            and_(
                OrganizationMembership.organization_id == org_id,
                OrganizationMembership.status == 'active'
            )
        )
    )
    
    members = []
    for user, membership in result.all():
        member = OrganizationMemberResponse(
            user_id=user.id,
            clerk_id=user.clerk_id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            role=membership.role,
            joined_at=membership.joined_at,
            last_active_at=user.last_login_at,
            status=membership.status
        )
        members.append(member)
    
    return members

@router.post("/{org_id}/invitations", status_code=status.HTTP_201_CREATED)
async def invite_user_to_organization(
    org_id: UUID,
    invite_data: OrganizationInviteRequest,
    context: OrganizationContext = Depends(get_organization_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Invite user to organization"""
    
    # Check permissions
    if not context.has_permission("users:invite"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to invite users"
        )
    
    # Map our roles to Clerk roles (simplified)
    clerk_role_mapping = {
        OrganizationRole.ADMIN: 'admin',
        OrganizationRole.MEMBER: 'basic_member'
    }
    
    # Create invitation in Clerk
    invitation = await clerk_org_service.create_invitation(
        org_id=context.organization.clerk_organization_id,
        email=invite_data.email,
        role=clerk_role_mapping.get(invite_data.role, 'basic_member'),
        inviter_id=context.user.clerk_id
    )
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create invitation"
        )
    
    logger.info(f"User {context.user.email} invited {invite_data.email} to {context.organization.name}")
    
    return {
        "message": f"Invitation sent to {invite_data.email}",
        "invitation_id": invitation['clerk_id'],
        "expires_at": invitation['expires_at']
    }
```

#### Step 4: Register Organization Routes
Update `app/main.py`:
```python
from app.routers import clerk_webhooks, organizations

# Add to router registration
app.include_router(clerk_webhooks.router, prefix="/api/v1/webhooks")
app.include_router(organizations.router, prefix="/api/v1")
```

#### Step 5: Configure Webhooks in Clerk Dashboard
1. Navigate to **Webhooks** in Clerk dashboard
2. Add single unified endpoint:
   - **Local Development**: `http://localhost:8000/api/v1/webhooks/clerk/events`
   - **Production**: `https://api.tickaido.com/api/v1/webhooks/clerk/events`
3. Select all events (single endpoint handles both user and organization events):
   **User Events**:
   - `user.created`
   - `user.updated`
   - `user.deleted`
   - `session.created`
   - `session.ended`
   
   **Organization Events**:
   - `organization.created`
   - `organization.updated`
   - `organization.deleted`
   - `organizationMembership.created`
   - `organizationMembership.updated`
   - `organizationMembership.deleted`
   - `organizationInvitation.created`
   - `organizationInvitation.accepted`
   - `organizationInvitation.revoked`
4. Copy webhook secret to environment variables as `CLERK_WEBHOOK_SECRET`

### Phase 4: Frontend Integration (Week 3)

#### Step 1: Frontend Authentication Setup
For React/Next.js frontend:
```jsx
// app/layout.js or _app.js
import { ClerkProvider } from '@clerk/nextjs'

export default function RootLayout({ children }) {
  return (
    <ClerkProvider
      publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}
      appearance={{
        theme: {
          primaryColor: "#your-brand-color"
        }
      }}
    >
      {children}
    </ClerkProvider>
  )
}
```

```jsx
// components/AuthButton.jsx
import { SignInButton, SignUpButton, UserButton, useUser } from '@clerk/nextjs'

export default function AuthButton() {
  const { isSignedIn, user } = useUser()

  if (isSignedIn) {
    return (
      <div className="flex items-center space-x-4">
        <span>Welcome, {user.firstName}!</span>
        <UserButton />
      </div>
    )
  }

  return (
    <div className="space-x-2">
      <SignInButton mode="modal">
        <button className="btn btn-primary">Sign In</button>
      </SignInButton>
      <SignUpButton mode="modal">
        <button className="btn btn-outline">Sign Up</button>
      </SignUpButton>
    </div>
  )
}
```

#### Step 2: API Authentication
```javascript
// utils/api.js
import { useAuth } from '@clerk/nextjs'

export function useAuthenticatedAPI() {
  const { getToken } = useAuth()

  const authenticatedFetch = async (url, options = {}) => {
    const token = await getToken()
    
    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    })
  }

  return { authenticatedFetch }
}
```

### Phase 5: Testing & Validation (Week 3)

#### Step 1: Unit Tests
Create `tests/test_clerk_integration.py`:
```python
import pytest
from unittest.mock import Mock, patch
from app.services.clerk_service import clerk_service
from app.middleware.clerk_middleware import clerk_auth

class TestClerkIntegration:
    @pytest.mark.asyncio
    async def test_verify_token_success(self):
        """Test successful token verification"""
        with patch.object(clerk_service, 'client') as mock_client:
            # Mock Clerk response
            mock_session = Mock()
            mock_session.user_id = 'user_123'
            mock_client.sessions.verify_token.return_value = mock_session
            
            mock_user = Mock()
            mock_user.id = 'user_123'
            mock_user.email_addresses = [Mock(email_address='test@example.com')]
            mock_user.first_name = 'Test'
            mock_user.last_name = 'User'
            mock_client.users.get.return_value = mock_user
            
            result = await clerk_service.verify_token('valid_token')
            
            assert result is not None
            assert result['user_id'] == 'user_123'
            assert result['email'] == 'test@example.com'
    
    @pytest.mark.asyncio
    async def test_verify_token_invalid(self):
        """Test invalid token handling"""
        with patch.object(clerk_service, 'client') as mock_client:
            mock_client.sessions.verify_token.return_value = None
            
            result = await clerk_service.verify_token('invalid_token')
            
            assert result is None
    
    @pytest.mark.asyncio 
    async def test_webhook_user_created(self):
        """Test webhook user creation"""
        from app.routers.clerk_webhooks import handle_user_created
        
        user_data = {
            'id': 'user_456',
            'email_addresses': [{'email_address': 'webhook@example.com'}],
            'first_name': 'Webhook',
            'last_name': 'User',
            'image_url': 'https://example.com/avatar.jpg'
        }
        
        # Mock database session
        mock_db = Mock()
        await handle_user_created(mock_db, user_data)
        
        # Verify user creation
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
```

#### Step 2: Integration Tests
```python
class TestClerkAPIIntegration:
    @pytest.mark.asyncio
    async def test_protected_endpoint_with_valid_token(self):
        """Test API access with valid Clerk token"""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        with patch('app.middleware.clerk_middleware.clerk_service.verify_token') as mock_verify:
            mock_verify.return_value = {
                'user_id': 'user_123',
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
            
            response = client.get(
                '/api/v1/users/me',
                headers={'Authorization': 'Bearer valid_clerk_token'}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['email'] == 'test@example.com'
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self):
        """Test API access without authentication"""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        response = client.get('/api/v1/users/me')
        
        assert response.status_code == 401
```

#### Step 3: End-to-End Tests
```python
@pytest.mark.e2e
class TestClerkE2E:
    def test_google_sso_flow(self):
        """Test complete Google SSO authentication flow"""
        # This would use Playwright/Selenium for browser automation
        # 1. Navigate to login page
        # 2. Click "Sign in with Google"
        # 3. Complete Google OAuth flow
        # 4. Verify user is authenticated in application
        # 5. Verify user record created in database
        pass
    
    def test_microsoft_sso_flow(self):
        """Test complete Microsoft SSO authentication flow"""
        pass
    
    def test_github_sso_flow(self):
        """Test complete GitHub SSO authentication flow"""
        pass
```

---

## Migration Strategy

### Pre-Migration Assessment

#### Current User Analysis
```sql
-- Analyze current user authentication methods
SELECT 
    COUNT(*) as total_users,
    COUNT(CASE WHEN password_hash IS NOT NULL THEN 1 END) as local_auth_users,
    COUNT(CASE WHEN external_auth_provider IS NOT NULL THEN 1 END) as sso_users,
    COUNT(CASE WHEN external_auth_provider = 'google' THEN 1 END) as google_users,
    COUNT(CASE WHEN external_auth_provider = 'github' THEN 1 END) as github_users
FROM users 
WHERE is_active = true;
```

### Migration Phases

#### Phase 1: Parallel Authentication (2 weeks)
1. **Deploy Clerk Integration**: Run Clerk alongside existing auth
2. **User Choice**: Allow users to link Clerk accounts or continue with existing auth
3. **Data Sync**: Ensure user data stays synchronized between systems
4. **Testing**: Validate all authentication flows work correctly

#### Phase 2: User Migration (4 weeks)  
1. **Migration Communications**: Notify users about upcoming changes
2. **Assisted Migration**: Provide migration tools and support
3. **Incentives**: Offer enhanced features for users who migrate
4. **Support**: Provide comprehensive user support during transition

#### Phase 3: Legacy Deprecation (2 weeks)
1. **Final Migration Push**: Final communications and migration assistance  
2. **Legacy Shutdown**: Disable old authentication system
3. **Cleanup**: Remove legacy authentication code and database fields
4. **Monitoring**: Monitor system stability post-migration

### Migration Scripts

### Organization Migration Strategy

#### Pre-Migration Organization Analysis
```sql
-- Analyze current organization structure
SELECT 
    COUNT(*) as total_orgs,
    AVG(user_count) as avg_users_per_org,
    MAX(user_count) as max_users_per_org,
    COUNT(CASE WHEN user_count > 50 THEN 1 END) as large_orgs
FROM (
    SELECT 
        o.id,
        o.name,
        COUNT(DISTINCT om.user_id) as user_count
    FROM organizations o
    LEFT JOIN organization_memberships om ON o.id = om.organization_id
    WHERE o.is_active = true AND om.status = 'active'
    GROUP BY o.id, o.name
) org_stats;
```

#### Organization Migration Phases

##### Phase 1: Clerk Organization Setup (1 week)
1. **Create Organizations in Clerk**: Migrate organization records to Clerk Organizations
2. **Setup Organization Webhooks**: Configure webhook handlers for organization events  
3. **Test Organization Creation**: Validate organization creation and webhook sync
4. **Permission Mapping**: Test role and permission mapping between systems

##### Phase 2: Organization Membership Migration (2 weeks)
1. **Migrate Organization Owners**: Start with organization owners and admins
2. **Batch Member Migration**: Migrate members in batches per organization
3. **Role Assignment Validation**: Verify roles are correctly assigned in Clerk
4. **Cross-Organization Access**: Test users with multiple organization memberships

##### Phase 3: Data Isolation Validation (1 week)
1. **Tenant Data Verification**: Ensure data isolation between organizations
2. **Permission Testing**: Validate organization-scoped permissions  
3. **API Access Control**: Test organization context middleware
4. **Security Audit**: Comprehensive security review of multi-tenant setup

### Organization & User Migration Scripts

#### Organization Migration Script
```python
#!/usr/bin/env python3
"""
Script to migrate existing organizations and users to Clerk with multi-tenant support
"""

import asyncio
import logging
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db_session
from app.models.user import User
from app.models.organization import Organization, OrganizationMembership
from app.services.clerk_service import clerk_service
from app.services.clerk_organization_service import clerk_org_service

logger = logging.getLogger(__name__)

async def migrate_organizations_to_clerk():
    """Migrate organizations and memberships to Clerk"""
    
    async with get_db_session() as db:
        # Get all active organizations
        result = await db.execute(
            select(Organization).where(
                (Organization.is_active == True) & 
                (Organization.clerk_organization_id.is_(None))
            )
        )
        organizations = result.scalars().all()
        
        logger.info(f"Found {len(organizations)} organizations to migrate")
        
        for org in organizations:
            try:
                # Find organization owner/admin to use as creator
                owner_result = await db.execute(
                    select(User, OrganizationMembership)
                    .join(OrganizationMembership)
                    .where(
                        and_(
                            OrganizationMembership.organization_id == org.id,
                            OrganizationMembership.role.in_([
                                OrganizationRole.OWNER, 
                                OrganizationRole.ADMIN
                            ]),
                            OrganizationMembership.status == 'active'
                        )
                    )
                    .order_by(OrganizationMembership.joined_at.asc())
                )
                owner_data = owner_result.first()
                
                if not owner_data:
                    logger.warning(f"No owner found for organization {org.name}, skipping")
                    continue
                
                owner_user, owner_membership = owner_data
                
                # Ensure owner has Clerk account
                if not owner_user.clerk_id:
                    logger.warning(f"Owner {owner_user.email} not migrated to Clerk yet, skipping org {org.name}")
                    continue
                
                # Create organization in Clerk
                clerk_org = await clerk_org_service.create_organization(
                    name=org.name,
                    slug=org.slug or org.name.lower().replace(' ', '-'),
                    created_by=owner_user.clerk_id,
                    metadata={
                        'original_org_id': str(org.id),
                        'migrated_at': datetime.now().isoformat(),
                        'billing_plan': getattr(org, 'billing_plan', 'free'),
                        'settings': org.settings or {}
                    }
                )
                
                if clerk_org:
                    # Update local organization record
                    org.clerk_organization_id = clerk_org['clerk_id']
                    org.clerk_metadata = clerk_org
                    await db.commit()
                    
                    # Migrate all organization members
                    await migrate_organization_members(db, org, clerk_org['clerk_id'])
                    
                    logger.info(f"Successfully migrated organization: {org.name}")
                else:
                    logger.error(f"Failed to create Clerk organization: {org.name}")
                    
            except Exception as e:
                logger.error(f"Migration error for organization {org.name}: {e}")
                continue
        
        logger.info("Organization migration completed")

async def migrate_organization_members(
    db: AsyncSession, 
    organization: Organization, 
    clerk_org_id: str
):
    """Migrate all members of an organization to Clerk"""
    
    # Get all active members
    result = await db.execute(
        select(User, OrganizationMembership)
        .join(OrganizationMembership)
        .where(
            and_(
                OrganizationMembership.organization_id == organization.id,
                OrganizationMembership.status == 'active',
                User.is_active == True
            )
        )
    )
    members = result.all()
    
    # Role mapping for Clerk (simplified)
    role_mapping = {
        OrganizationRole.ADMIN: 'admin',
        OrganizationRole.MEMBER: 'basic_member'
    }
    
    for user, membership in members:
        try:
            if not user.clerk_id:
                logger.warning(f"User {user.email} not migrated to Clerk yet, skipping membership")
                continue
            
            # Add member to Clerk organization
            clerk_membership = await clerk_org_service.add_member(
                org_id=clerk_org_id,
                user_id=user.clerk_id,
                role=role_mapping.get(membership.role, 'basic_member')
            )
            
            if clerk_membership:
                # Update local membership record
                membership.clerk_organization_id = clerk_org_id
                membership.clerk_membership_id = clerk_membership['clerk_id']
                await db.commit()
                
                logger.info(f"Added {user.email} to {organization.name} as {membership.role}")
            else:
                logger.error(f"Failed to add {user.email} to Clerk organization {organization.name}")
                
        except Exception as e:
            logger.error(f"Error migrating member {user.email} to {organization.name}: {e}")
            continue

async def validate_organization_migration():
    """Validate organization migration completed successfully"""
    
    async with get_db_session() as db:
        # Check for organizations without Clerk ID
        result = await db.execute(
            select(Organization).where(
                (Organization.is_active == True) & 
                (Organization.clerk_organization_id.is_(None))
            )
        )
        unmigrated_orgs = result.scalars().all()
        
        if unmigrated_orgs:
            logger.warning(f"{len(unmigrated_orgs)} organizations not migrated to Clerk:")
            for org in unmigrated_orgs:
                logger.warning(f"  - {org.name} (ID: {org.id})")
        else:
            logger.info("All organizations successfully migrated to Clerk")
        
        # Check for memberships without Clerk ID
        result = await db.execute(
            select(OrganizationMembership, Organization, User)
            .join(Organization)
            .join(User)
            .where(
                and_(
                    OrganizationMembership.status == 'active',
                    Organization.is_active == True,
                    User.is_active == True,
                    OrganizationMembership.clerk_membership_id.is_(None)
                )
            )
        )
        unmigrated_memberships = result.all()
        
        if unmigrated_memberships:
            logger.warning(f"{len(unmigrated_memberships)} memberships not migrated:")
            for membership, org, user in unmigrated_memberships:
                logger.warning(f"  - {user.email} in {org.name}")
        else:
            logger.info("All memberships successfully migrated to Clerk")

#### User Data Migration Script (Enhanced for Organizations)
```python
#!/usr/bin/env python3
"""
Script to migrate existing users to Clerk with organization context
"""

import asyncio
import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db_session
from app.models.user import User
from app.services.clerk_service import clerk_service

logger = logging.getLogger(__name__)

async def migrate_users_to_clerk():
    """Migrate existing users to Clerk"""
    
    async with get_db_session() as db:
        # Get all active users without Clerk ID
        result = await db.execute(
            select(User).where(
                (User.is_active == True) & 
                (User.clerk_id.is_(None))
            )
        )
        users = result.scalars().all()
        
        logger.info(f"Found {len(users)} users to migrate")
        
        for user in users:
            try:
                # Create user in Clerk
                clerk_user = await create_clerk_user(user)
                
                if clerk_user:
                    # Update local user record
                    user.clerk_id = clerk_user['id']
                    await db.commit()
                    
                    # Send migration notification email
                    await send_migration_notification(user.email)
                    
                    logger.info(f"Migrated user: {user.email}")
                else:
                    logger.error(f"Failed to migrate user: {user.email}")
                    
            except Exception as e:
                logger.error(f"Migration error for {user.email}: {e}")
                continue
        
        logger.info("User migration completed")

async def create_clerk_user(user: User) -> dict:
    """Create user in Clerk system"""
    try:
        # Create user with email and password reset requirement
        clerk_user_data = {
            'email_address': [user.email],
            'first_name': user.full_name.split(' ')[0] if user.full_name else '',
            'last_name': ' '.join(user.full_name.split(' ')[1:]) if user.full_name else '',
            'private_metadata': {
                'legacy_user_id': str(user.id),
                'migrated_at': datetime.now().isoformat(),
                'original_auth_provider': user.external_auth_provider
            }
        }
        
        # Skip password for SSO users
        if not user.external_auth_provider:
            clerk_user_data['skip_password_checks'] = True
            clerk_user_data['password_digest'] = user.password_hash
        
        # Create in Clerk
        clerk_user = clerk_service.client.users.create(**clerk_user_data)
        return clerk_user
        
    except Exception as e:
        logger.error(f"Failed to create Clerk user: {e}")
        return None

async def send_migration_notification(email: str):
    """Send email notification about migration"""
    # Implementation depends on your email service
    logger.info(f"Migration notification sent to: {email}")

if __name__ == "__main__":
    asyncio.run(migrate_users_to_clerk())
```

### Rollback Plan

#### Emergency Rollback Procedure
1. **Immediate Actions** (< 30 minutes):
   - Switch traffic back to legacy authentication
   - Disable Clerk webhook endpoints
   - Monitor system health metrics

2. **Data Consistency** (< 2 hours):
   - Sync any user changes back to legacy system
   - Verify data integrity
   - Update user notification systems

3. **Post-Rollback Analysis** (< 24 hours):
   - Analyze root cause of rollback
   - Document lessons learned
   - Plan corrective actions for re-migration

---

## Security & Compliance

### Security Features

#### Clerk Built-in Security
- ✅ **Multi-Factor Authentication**: TOTP, SMS, Email
- ✅ **Session Management**: Advanced session controls and monitoring  
- ✅ **Device Management**: Track and manage user devices
- ✅ **Rate Limiting**: Built-in protection against brute force attacks
- ✅ **Suspicious Activity Detection**: AI-powered fraud detection
- ✅ **Audit Logging**: Comprehensive security event logging

#### Application-Level Security
- ✅ **API Rate Limiting**: Maintain existing FastAPI rate limiting
- ✅ **Input Validation**: Validate all user inputs and API requests
- ✅ **SQL Injection Prevention**: Use parameterized queries
- ✅ **CORS Protection**: Configure appropriate CORS policies
- ✅ **Data Encryption**: Encrypt sensitive data at rest and in transit

### Compliance Features

#### GDPR Compliance
- ✅ **Data Minimization**: Only collect necessary user data
- ✅ **Right to Access**: Users can export their data
- ✅ **Right to Rectification**: Users can update their information
- ✅ **Right to Erasure**: Users can delete their accounts
- ✅ **Data Portability**: Export user data in standard formats
- ✅ **Consent Management**: Clear consent for data processing

#### SOC 2 Compliance
- ✅ **Security Controls**: Clerk is SOC 2 Type II certified
- ✅ **Availability**: 99.9% uptime SLA
- ✅ **Processing Integrity**: Data integrity guarantees
- ✅ **Confidentiality**: Data encryption and access controls
- ✅ **Privacy**: Privacy controls and data protection

### Security Monitoring

#### Metrics to Monitor
```python
# Security monitoring metrics
SECURITY_METRICS = {
    'authentication_failures': 'Counter of failed login attempts',
    'suspicious_activity_alerts': 'Alerts for unusual user behavior',
    'session_anomalies': 'Unusual session patterns',
    'api_rate_limit_hits': 'API rate limiting triggers',
    'webhook_failures': 'Failed Clerk webhook deliveries'
}
```

#### Alerting Rules
```yaml
# Example alerting configuration
alerts:
  - name: "High Authentication Failures"
    condition: "authentication_failures > 100 in 5 minutes"
    action: "Alert security team and temporarily block IPs"
  
  - name: "Webhook Delivery Failures"  
    condition: "webhook_failures > 10 in 1 hour"
    action: "Alert engineering team and investigate sync issues"
  
  - name: "Suspicious Activity Spike"
    condition: "suspicious_activity_alerts > 5 in 10 minutes"
    action: "Alert security team and enable enhanced monitoring"
```

---

## Cost Analysis

### Clerk Pricing Analysis

#### Estimated Monthly Costs
| User Tier | Monthly Active Users | Clerk Plan | Monthly Cost | Annual Cost |
|-----------|---------------------|------------|--------------|-------------|
| **Starter** | 0 - 10,000 | Pro | $25/month | $300/year |
| **Growth** | 10,001 - 100,000 | Pro + overages | $25 + $0.02/MAU | $300 + $240/year |
| **Enterprise** | 100,000+ | Enterprise | Custom pricing | $12,000+/year |

#### Cost Comparison: Build vs. Buy

| Factor | Custom SSO Build | Clerk Integration | Difference |
|--------|------------------|-------------------|------------|
| **Initial Development** | $50,000 - $80,000 | $5,000 - $10,000 | **Save $45,000 - $70,000** |
| **Ongoing Maintenance** | $30,000/year | $300 - $3,000/year | **Save $27,000 - $29,700/year** |
| **Security Compliance** | $20,000/year | Included | **Save $20,000/year** |
| **Time to Market** | 8-12 weeks | 2-3 weeks | **Save 6-9 weeks** |
| **Feature Richness** | Basic features | Enterprise features | **Additional value** |

#### ROI Analysis (3 Years)
```
Custom Build Total Cost: $170,000 - $260,000
Clerk Integration Total Cost: $6,200 - $19,000
Total Savings: $150,800 - $241,000

Break-even Point: Immediate (Week 1)
3-Year ROI: 800% - 3,900%
```

### Hidden Costs Avoided

#### Development Complexity
- OAuth provider maintenance and updates
- Security vulnerability patches and updates  
- Compliance certification and auditing
- Multi-browser and device compatibility testing
- Customer support for authentication issues

#### Operational Overhead
- 24/7 monitoring and incident response
- Security team oversight and management
- Legal review for compliance requirements
- Documentation and training materials
- User onboarding and migration support

---

## Timeline & Milestones

### Project Timeline (8 weeks total with Organizations)

```mermaid
gantt
    title Clerk Integration Timeline with Multi-Tenant Organizations
    dateFormat  YYYY-MM-DD
    section Setup Phase
    Clerk Account & Provider Setup    :setup1, 2025-01-13, 5d
    Environment Configuration         :setup2, after setup1, 2d
    
    section Backend Integration
    Install Dependencies             :backend1, after setup2, 1d
    Clerk Service Implementation     :backend2, after backend1, 3d
    User Middleware Integration      :backend3, after backend2, 2d
    Organization Service Integration :backend4, after backend3, 3d
    Organization Middleware         :backend5, after backend4, 2d
    Webhook Implementation          :backend6, after backend5, 3d
    
    section Frontend Integration
    Frontend Authentication Setup   :frontend1, after backend4, 3d
    Organization Context UI         :frontend2, after frontend1, 3d
    Multi-Tenant API Integration    :frontend3, after frontend2, 3d
    Organization Management UI      :frontend4, after frontend3, 2d
    
    section Testing & Migration
    Unit & Integration Testing     :test1, after backend6, 4d
    Organization Migration Scripts :migrate1, after test1, 3d
    User Migration Scripts        :migrate2, after migrate1, 2d
    Production Deployment         :deploy1, after migrate2, 2d
    Organization Migration        :migrate3, after deploy1, 5d
    User Migration Execution      :migrate4, after migrate3, 7d
    Data Isolation Validation    :validate1, after migrate4, 3d
    
    section Finalization
    Legacy System Deprecation    :final1, after validate1, 3d
    Documentation & Training      :final2, after final1, 2d
```

### Key Milestones (Updated for Organizations)

#### Week 1: Foundation Setup ✅
- **Day 1-2**: Clerk account creation and provider configuration
- **Day 3-5**: Google, Microsoft, GitHub OAuth app setup
- **Day 6-7**: Environment configuration and initial testing

**Success Criteria**:
- [ ] All OAuth providers configured and tested
- [ ] Clerk dashboard properly configured with Organizations enabled
- [ ] Development environment setup complete

#### Week 2-3: Backend Integration 🔄
- **Day 8-10**: Clerk SDK integration and basic authentication service
- **Day 11-12**: User authentication middleware implementation
- **Day 13-15**: Clerk Organizations API integration
- **Day 16-17**: Organization context middleware
- **Day 18-21**: Comprehensive webhook handlers (users + organizations)

**Success Criteria**:
- [ ] Clerk authentication working in backend
- [ ] Organization management functional
- [ ] Multi-tenant context middleware working
- [ ] All webhook events handled properly
- [ ] Permission system integrated with organizations

#### Week 4-5: Frontend Integration 🔄
- **Day 22-24**: Frontend Clerk SDK integration
- **Day 25-27**: Organization switcher and context UI
- **Day 28-30**: Multi-tenant API integration
- **Day 31-33**: Organization management dashboard
- **Day 34-35**: Role-based UI components

**Success Criteria**:
- [ ] Frontend authentication flows working
- [ ] Organization switching seamless
- [ ] All SSO providers accessible from UI
- [ ] Organization management features functional
- [ ] Role-based UI properly implemented

#### Week 6: Testing & Quality Assurance 📋
- **Day 36-39**: Comprehensive testing (unit, integration, E2E, multi-tenant)
- **Day 40-41**: Performance and security testing with tenant isolation
- **Day 42**: Bug fixes and optimizations

**Success Criteria**:
- [ ] All tests passing (>95% coverage)
- [ ] Multi-tenant data isolation verified
- [ ] Performance benchmarks met
- [ ] Security audit completed including tenant security

#### Week 7: Migration Preparation 🚀
- **Day 43-45**: Organization migration scripts and validation
- **Day 46-47**: User migration scripts with organization context
- **Day 48-49**: Production deployment and configuration

**Success Criteria**:
- [ ] Production system deployed successfully
- [ ] Organization migration tools tested and validated
- [ ] User migration tools tested with multi-tenant support
- [ ] Both auth systems running in parallel

#### Week 8: Organization & User Migration 🎯
- **Day 50-54**: Organization migration execution
- **Day 55-61**: User migration with organization membership
- **Day 62-64**: Data isolation validation and security audit

**Success Criteria**:
- [ ] >95% of organizations migrated successfully
- [ ] >95% of users migrated with correct organization memberships
- [ ] All user permissions validated within organizations
- [ ] Data isolation confirmed between organizations
- [ ] Legacy system retired securely

### Organization-Specific Validation Checklist

#### Multi-Tenant Security Validation
- [ ] **Data Isolation**: Users can only access data from their organizations
- [ ] **Permission Enforcement**: Role-based permissions work within organization context  
- [ ] **Cross-Organization Prevention**: No data leakage between organizations
- [ ] **API Security**: Organization context properly enforced in all API endpoints
- [ ] **Database Queries**: All queries properly filtered by organization_id

#### Organization Management Features
- [ ] **Organization Creation**: Users can create new organizations
- [ ] **Member Invitations**: Organization admins can invite users with roles
- [ ] **Role Management**: Organization roles properly assigned and enforced
- [ ] **Single Organization Access**: Users access only their assigned organization
- [ ] **Settings Isolation**: Organization settings are properly isolated

#### Migration Validation
- [ ] **Organization Data Integrity**: All organization data migrated correctly
- [ ] **Membership Preservation**: User-organization relationships maintained
- [ ] **Role Assignment**: User roles properly mapped from old to new system
- [ ] **Permission Continuity**: User permissions unchanged post-migration
- [ ] **Audit Trail**: Complete audit trail of migration activities

### Risk Mitigation Timeline

#### High-Risk Items (Weeks 1-2)
- **OAuth Provider Configuration**: Allocate extra time for provider-specific requirements
- **Webhook Reliability**: Implement comprehensive error handling and retry logic
- **Database Migration**: Test migration scripts extensively before production

#### Medium-Risk Items (Weeks 3-4)
- **Frontend Integration Complexity**: Plan for cross-browser compatibility testing
- **Performance Impact**: Monitor and optimize authentication flow performance
- **User Experience**: Conduct user testing and gather feedback early

#### Low-Risk Items (Weeks 5-6)
- **Documentation**: Ensure comprehensive documentation for maintenance
- **Training**: Provide adequate training for support team
- **Monitoring**: Set up proper monitoring and alerting for production

---

## Appendix

### Additional Resources

#### Clerk Documentation
- [Clerk Getting Started Guide](https://clerk.com/docs)
- [FastAPI Integration Guide](https://clerk.com/docs/integrations/fastapi)
- [Webhook Events Reference](https://clerk.com/docs/webhooks/overview)
- [Social Connections Setup](https://clerk.com/docs/authentication/social-connections)

#### Provider Documentation
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Microsoft Identity Platform](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- [GitHub OAuth Apps](https://docs.github.com/en/developers/apps/building-oauth-apps)

#### Security Best Practices
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OAuth 2.0 Security Best Practices (RFC 9700)](https://datatracker.ietf.org/doc/rfc9700/)
- [OpenID Connect Security Considerations](https://openid.net/specs/openid-connect-core-1_0.html#Security)