### SSO Registration and Login Plan (Google, Microsoft, GitHub)

This document describes how to add "Sign up / Sign in with Google, Microsoft, and GitHub" to the existing FastAPI backend and frontends/clients. It focuses on registration-on-first-login (Just-In-Time provisioning), linking future logins, and issuing our app’s JWTs upon successful OAuth/OIDC authentication.


## Goals
- Enable new users to register via SSO (Google, Microsoft, GitHub) from the Signup/Login page.
- Support existing users to log in via SSO using the same email.
- Create or link a `User` record with `external_auth_provider` and `external_auth_id`.
- Issue our existing JWT access/refresh tokens for session continuity.
- Keep local email/password auth working.


## Current State (in this repo)
- Local auth: implemented in `app/routers/auth.py` with `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me`.
- JWT token creation/verification: via `app/middleware/auth_middleware.py` (create_access_token/create_refresh_token, authenticate_user).
- `User` model already supports external auth:
  - `external_auth_provider`, `external_auth_id` fields in `app/models/user.py`.
- Settings: `app/config/settings.py` has generic config, but no provider-specific OAuth config yet.

This is a good baseline: we only need to add provider flows and endpoints to exchange provider tokens for our JWTs and to JIT-provision user records.


## Architectural Approach
- Use OAuth 2.0 / OpenID Connect flows with the provider’s hosted login.
- Frontend redirects user to provider’s authorization endpoint → provider prompts for consent → provider redirects back to our backend callback.
- Backend callback validates the authorization code (via provider SDK or direct HTTP), obtains ID token and user profile, then:
  1) Finds or creates a `User` by email.
  2) Stores `external_auth_provider` and `external_auth_id`.
  3) Issues our app’s JWT access/refresh tokens (same shape as local login).
- Return tokens to frontend (via JSON if SPA calls a callback endpoint, or via a frontend callback URL with a one-time code to exchange server-to-server).


## Libraries & Dependencies
Following RFC 9700 (January 2025) security requirements and best practices:

- **Authlib**: Industry-standard OAuth/OIDC library with PKCE support, OpenID Connect metadata discovery, and security validation
- **HTTPx**: Already installed - HTTP client for direct provider API calls
- **Itsdangerous**: Secure token/state generation (already available via FastAPI)
- **PyJWT**: JWT handling (already installed as `pyjwt`)

Add to Poetry:
```bash
poetry add authlib itsdangerous
```

**Security Rationale**: 
- Authlib provides RFC 9700 compliant PKCE implementation
- Built-in OpenID Connect metadata discovery prevents endpoint misconfiguration
- Automatic state/nonce validation prevents CSRF attacks
- Token signature validation prevents tampering


## Configuration
Add OAuth provider configurations to `Settings` in `app/config/settings.py`. Following RFC 9700 security requirements:

**Required Settings**:
```python
# OAuth2/OIDC Provider Settings (RFC 9700 Compliant)
# Google OAuth/OIDC
google_client_id: Optional[str] = Field(default=None, description="Google OAuth client ID")
google_client_secret: Optional[str] = Field(default=None, description="Google OAuth client secret")
google_redirect_uri: str = Field(default="http://localhost:8000/auth/callback/google", description="Google OAuth redirect URI")

# GitHub OAuth
github_client_id: Optional[str] = Field(default=None, description="GitHub OAuth client ID")
github_client_secret: Optional[str] = Field(default=None, description="GitHub OAuth client secret")
github_redirect_uri: str = Field(default="http://localhost:8000/auth/callback/github", description="GitHub OAuth redirect URI")

# Microsoft Azure AD/Entra ID
microsoft_client_id: Optional[str] = Field(default=None, description="Microsoft OAuth client ID")
microsoft_client_secret: Optional[str] = Field(default=None, description="Microsoft OAuth client secret")
microsoft_tenant: str = Field(default="common", description="Microsoft tenant (common/organizations/specific tenant ID)")
microsoft_redirect_uri: str = Field(default="http://localhost:8000/auth/callback/microsoft", description="Microsoft OAuth redirect URI")

# OAuth Security Settings
oauth_state_secret: str = Field(default="your-oauth-state-secret-change-in-production", description="Secret for OAuth state parameter encryption")
oauth_session_timeout: int = Field(default=600, description="OAuth session timeout in seconds (10 minutes)")
```

**Environment Variables** (.env):
```bash
# Google OAuth/OIDC Configuration
GOOGLE_CLIENT_ID=123456789-abcdefghijklmnopqrstuvwxyz.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abcdefghijklmnopqrstuvwxyz123456
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback/google

# GitHub OAuth Configuration  
GITHUB_CLIENT_ID=Iv1.a1b2c3d4e5f67890
GITHUB_CLIENT_SECRET=abcdef1234567890abcdef1234567890abcdef12
GITHUB_REDIRECT_URI=http://localhost:8000/auth/callback/github

# Microsoft OAuth Configuration
MICROSOFT_CLIENT_ID=12345678-1234-1234-1234-123456789abc
MICROSOFT_CLIENT_SECRET=abc123def456ghi789jkl012mno345pqr678stu
MICROSOFT_TENANT=common
MICROSOFT_REDIRECT_URI=http://localhost:8000/auth/callback/microsoft

# OAuth Security
OAUTH_STATE_SECRET=your-cryptographically-secure-256-bit-secret-key-here
OAUTH_SESSION_TIMEOUT=600
```

**Security Requirements**:
- All redirect URIs must use HTTPS in production
- State secret must be cryptographically random (256-bit minimum)
- Client secrets must be stored securely (use environment variables or secret manager)
- Session timeout prevents stale OAuth flows


## Database Model Notes & Identity Management

### Current Database Schema
`User` model supports external auth with no migration needed:
- `external_auth_provider`: Provider name (google, github, microsoft)  
- `external_auth_id`: Provider-specific user ID (stable across logins)
- `email`: Primary identity key for account linking
- Existing index on `external_auth_id` for performance

### Recommended Database Enhancement
Add composite unique constraint to prevent duplicate provider linkings:
```sql
ALTER TABLE users ADD CONSTRAINT unique_external_auth 
UNIQUE (external_auth_provider, external_auth_id);
```

## Identity Linking Strategy & Edge Cases

### Core Principles
1. **Email as Primary Identity**: Email address serves as the universal account identifier
2. **Provider Agnostic**: Users can link multiple SSO providers to same account  
3. **Security First**: All linking requires email verification to prevent account takeover
4. **User Choice**: Explicit consent for account linking vs. creating new accounts

### Identity Linking Flow Matrix

| Scenario | User State | SSO Login Attempt | System Behavior | User Experience |
|----------|------------|-------------------|------------------|-----------------|
| **New User** | No account exists | First SSO login | Create new account with SSO | Automatic registration |
| **Existing SSO User** | Account with Provider A | Login with Provider A | Standard login | Seamless authentication |
| **Multi-Provider Link** | Account with Provider A | Login with Provider B (same email) | Link Provider B to existing account | Account consolidation |
| **Email Mismatch** | Account with email1@domain.com | SSO with email2@domain.com | Create separate account | Isolated accounts |
| **Unverified Email** | Local account, unverified email | SSO with same email | Upgrade account, mark verified | Email verification bypass |
| **Verified Email Conflict** | Local account, verified email | SSO with same email | Link SSO provider to account | Multi-auth account |

### Detailed Edge Case Handling

#### **Edge Case 1: Cross-Provider Email Conflicts**
**Scenario**: User creates account with Google (user@gmail.com), logs out, tries to login with GitHub (user@gmail.com)

**Best Practice Implementation**:
```python
async def handle_cross_provider_linking(db: AsyncSession, provider: str, profile: Dict) -> User:
    """Handle cross-provider account linking with security validation"""
    email = profile['email']
    external_id = profile['id']
    
    # Check if external auth already exists (prevent duplicate linking)
    existing_external = await db.execute(
        select(User).where(
            and_(
                User.external_auth_provider == provider,
                User.external_auth_id == external_id
            )
        )
    )
    if existing_external.scalar_one_or_none():
        return existing_external.scalar_one()  # Standard login
    
    # Look for existing user by email
    existing_user = await db.execute(select(User).where(User.email == email))
    user = existing_user.scalar_one_or_none()
    
    if user:
        # SECURITY CHECK: Verify email ownership via SSO provider
        if not profile.get('email_verified', False):
            raise SecurityError("Cannot link unverified email to existing account")
        
        # Link new provider to existing account
        if user.external_auth_provider:
            # Multi-provider account - store additional providers in metadata
            providers = user.preferences.get('linked_providers', []) if user.preferences else []
            providers.append({
                'provider': provider,
                'external_id': external_id,
                'linked_at': datetime.now(timezone.utc).isoformat()
            })
            user.preferences = {**(user.preferences or {}), 'linked_providers': providers}
        else:
            # First SSO link to local account
            user.external_auth_provider = provider
            user.external_auth_id = external_id
        
        user.is_verified = True  # SSO implies email verification
        await db.commit()
        return user
    
    # Create new account
    return await create_new_sso_user(db, provider, profile)
```

**User Experience**:
- ✅ **Success Message**: "Your GitHub account has been linked to your existing account"
- ✅ **Account Dashboard**: Shows all linked providers with unlink options
- ✅ **Security Audit**: Log all account linking events

#### **Edge Case 2: Provider Email Changes**
**Scenario**: User's email changes at provider level (e.g., GitHub email updated)

**Best Practice**: Use stable provider ID for identification, email for linking only
```python
def get_stable_provider_id(provider: str, token_data: Dict) -> str:
    """Extract stable user ID that doesn't change if email changes"""
    if provider == 'google':
        return token_data['sub']  # Google's stable subject ID
    elif provider == 'github':
        return str(token_data['id'])  # GitHub's numeric user ID
    elif provider == 'microsoft':
        return token_data['oid']  # Microsoft's object ID
```

#### **Edge Case 3: Account Takeover Prevention**
**Scenario**: Attacker with access to email tries to link malicious SSO provider

**Security Controls**:
1. **Email Verification Requirement**: Only verified emails from SSO providers can link
2. **Notification System**: Email notification on new provider linking
3. **Cooling Period**: 24-hour delay before new provider becomes active
4. **IP Geolocation**: Flag suspicious geographic changes

```python
async def validate_account_linking_security(user: User, provider: str, request: Request):
    """Enhanced security validation for account linking"""
    
    # Check for suspicious activity patterns
    recent_logins = await get_recent_login_attempts(user.id, hours=24)
    if len(recent_logins) > 10:  # Rate limiting
        raise SecurityError("Too many login attempts, account linking temporarily disabled")
    
    # Geolocation validation
    current_ip = get_client_ip(request)
    if await is_suspicious_location(user.id, current_ip):
        # Require additional verification
        await send_account_linking_notification(user.email, provider)
        await create_pending_link_verification(user.id, provider)
        raise PendingVerificationError("Additional verification required for account linking")
    
    return True
```

#### **Edge Case 4: Partial Account Data**
**Scenario**: SSO provider returns incomplete profile data

**Handling Strategy**:
```python
def normalize_sso_profile(provider: str, raw_profile: Dict) -> Dict:
    """Normalize profile data handling missing fields gracefully"""
    normalized = {
        'id': None,
        'email': None, 
        'name': None,
        'avatar_url': None,
        'email_verified': False
    }
    
    if provider == 'google':
        normalized.update({
            'id': raw_profile.get('sub'),
            'email': raw_profile.get('email'),
            'name': raw_profile.get('name') or raw_profile.get('given_name', '') + ' ' + raw_profile.get('family_name', ''),
            'avatar_url': raw_profile.get('picture'),
            'email_verified': raw_profile.get('email_verified', False)
        })
    # Validation
    if not normalized['id'] or not normalized['email']:
        raise ProfileDataError(f"Incomplete profile from {provider}: missing required fields")
    
    return normalized
```

### Multi-Provider Account Management

#### **User Dashboard Features**
- **Linked Accounts Section**: Show all connected SSO providers
- **Primary Login Method**: User can set preferred login method
- **Account Unlinking**: Allow users to remove SSO providers (with confirmation)
- **Security Timeline**: Show recent login methods and linking events

#### **Administrative Controls**
- **Provider Disable**: Admins can disable specific SSO providers temporarily
- **Forced Re-authentication**: Require users to re-verify linked accounts
- **Audit Logging**: Track all account linking/unlinking events

### Security Boundaries & Limitations

#### **What We DON'T Support**
1. **Automatic Account Merging**: Never merge accounts without explicit user consent
2. **Cross-Email Linking**: Different email addresses = separate accounts (security)
3. **Retroactive Provider Changes**: Can't change provider ID after initial linking
4. **Silent Account Takeover**: Always notify users of new provider links

#### **Data Consistency Rules**
1. **Email Precedence**: User's current email in our system takes precedence over SSO email
2. **Profile Sync Policy**: Only update profile data with explicit user permission  
3. **Avatar Priority**: Most recently used SSO provider avatar becomes default
4. **Name Conflicts**: Local name overrides SSO name unless user explicitly updates

### Privacy & Compliance Considerations

#### **Data Minimization**
- Only store essential SSO data (ID, email, name, avatar)
- Don't store SSO access tokens long-term
- Regular cleanup of unused linked provider data

#### **User Rights** 
- **Data Portability**: Export all linked account information
- **Right to Disconnect**: Remove SSO provider links at any time
- **Consent Management**: Clear consent for each provider linking action

#### **GDPR/Privacy Compliance**
- Clear privacy notice about multi-provider data handling
- Separate consent for each SSO provider
- Data retention policies for linked account metadata


## Backend Endpoints
We will add three pairs of endpoints per provider:
- `GET /auth/login/{provider}`: Redirect to provider authorization URL.
- `GET /auth/callback/{provider}`: Handle provider redirect, exchange code for tokens, identify user, issue our JWTs.

These will mirror across `google`, `github`, `microsoft`.

Behavior:
- On callback success:
  - Look up by `(external_auth_provider, external_auth_id)`; if found, use that user.
  - Else, look up by email; if found, link `external_auth_provider/id` to the existing user.
  - Else, create a new user with `email`, `full_name` (if available), set `is_verified=True`, `external_auth_provider`, `external_auth_id`, `password_hash=None`.
  - Issue access/refresh via `auth_middleware.create_access_token/refresh_token` with `sub` and `email`.
- On failure: return appropriate HTTP 4xx; if frontend flow is browser-based, redirect back with an error query param.

**RFC 9700 (2025) Security Requirements**:
- **MANDATORY PKCE**: All OAuth flows MUST use PKCE with S256 code challenge method (prevents code interception)
- **State parameter validation**: Cryptographically random, session-bound state prevents CSRF attacks
- **Nonce validation**: For OpenID Connect flows, prevents token replay attacks
- **ID token validation**: Verify signature, issuer, audience, expiration, and nonce claims
- **Authorization server support**: Verify provider supports PKCE and modern security features
- **Transaction binding**: Each OAuth flow must be bound to specific user session
- **Constant value detection**: Prevent reuse of static PKCE challenges or nonce values


## Provider Details

### Google (OIDC)
- Authorization Endpoint: `https://accounts.google.com/o/oauth2/v2/auth`
- Token Endpoint: `https://oauth2.googleapis.com/token`
- UserInfo Endpoint: `https://openidconnect.googleapis.com/v1/userinfo`
- Scopes: `openid email profile`
- ID token contains `sub` (stable subject), `email`, `email_verified`, `name`, `picture`.
- Use `sub` as `external_auth_id`; provider=`google`.

### GitHub (OAuth 2.0)
- Authorization Endpoint: `https://github.com/login/oauth/authorize`
- Token Endpoint: `https://github.com/login/oauth/access_token`
- User API: `https://api.github.com/user` and `https://api.github.com/user/emails`
- Scopes: `read:user user:email`
- Use `id` from `/user` as `external_auth_id`; provider=`github`.
- Emails may require additional call to `/user/emails` to fetch a primary verified email.

### Microsoft (OIDC - Entra ID)
- For multi-tenant use `tenant=common` or `organizations`.
- Authorization Endpoint: `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize`
- Token Endpoint: `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token`
- UserInfo: `https://graph.microsoft.com/oidc/userinfo` or decode ID token claims.
- Scopes: `openid email profile` (and optionally MS Graph if needed)
- Use `oid` (object id) from ID token as the stable `external_auth_id` (or `sub` per OIDC), provider=`microsoft`.


## Pseudocode: Callback Handler
```python
@router.get("/auth/callback/{provider}")
async def oauth_callback(provider: str, request: Request, db: AsyncSession = Depends(get_db_session)):
    # 1) Validate state, retrieve code
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    validate_state(state)

    # 2) Exchange code for tokens via provider endpoints
    id_info, profile = await exchange_and_fetch_profile(provider, code)
    email = extract_email(id_info, profile)
    external_id = extract_external_id(provider, id_info, profile)

    # 3) Find or create user
    user = await find_user_by_provider_id(db, provider, external_id)
    if not user:
        user = await find_user_by_email(db, email)
        if user:
            await link_user_provider(db, user, provider, external_id)
        else:
            user = await create_user_from_sso(db, email, profile, provider, external_id)

    # 4) Issue our JWTs
    token_data = {"sub": str(user.id), "email": user.email}
    access = auth_middleware.create_access_token(token_data)
    refresh = auth_middleware.create_refresh_token(token_data)

    # 5) Return/redirect with tokens
    return TokenResponse(access_token=access, refresh_token=refresh, token_type="bearer", expires_in=1800, user=...)
```


## Backend Implementation Steps (RFC 9700 Compliant)

### Step 1: Install Dependencies
```bash
poetry add authlib itsdangerous
```

### Step 2: Update Settings Configuration
Extend `app/config/settings.py` with OAuth provider settings (see Configuration section above).

### Step 3: Create OAuth Security Service
Create `app/services/oauth_security.py`:
```python
#!/usr/bin/env python3
"""
RFC 9700 compliant OAuth security service with PKCE, state, and nonce validation
"""
import secrets
import hashlib
import base64
from typing import Dict, Optional
from datetime import datetime, timedelta, timezone
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

class OAuthSecurityService:
    def __init__(self, secret_key: str, session_timeout: int = 600):
        self.serializer = URLSafeTimedSerializer(secret_key)
        self.session_timeout = session_timeout
    
    def generate_pkce_pair(self) -> Dict[str, str]:
        """Generate PKCE code verifier and challenge (S256 method)"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        return {
            "code_verifier": code_verifier,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
    
    def generate_state_token(self, session_data: Dict) -> str:
        """Generate cryptographically secure state token"""
        return self.serializer.dumps(session_data)
    
    def verify_state_token(self, state_token: str) -> Dict:
        """Verify and decode state token"""
        try:
            return self.serializer.loads(state_token, max_age=self.session_timeout)
        except (BadSignature, SignatureExpired) as e:
            raise ValueError(f"Invalid or expired state token: {e}")
    
    def generate_nonce(self) -> str:
        """Generate cryptographically random nonce for OpenID Connect"""
        return secrets.token_urlsafe(32)
```

### Step 4: Create OAuth Service with Provider Configurations
Create `app/services/oauth_service.py`:
```python
#!/usr/bin/env python3
"""
RFC 9700 compliant OAuth/OIDC service with Authlib integration
"""
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client import OAuthError
from starlette.requests import Request
from typing import Dict, Optional, Any
import httpx

from app.config.settings import get_settings
from app.services.oauth_security import OAuthSecurityService

class OAuthService:
    def __init__(self):
        self.settings = get_settings()
        self.oauth = OAuth()
        self.security = OAuthSecurityService(
            self.settings.oauth_state_secret,
            self.settings.oauth_session_timeout
        )
        self._register_providers()
    
    def _register_providers(self):
        """Register OAuth providers with RFC 9700 compliance"""
        # Google (OpenID Connect with auto-discovery)
        if self.settings.google_client_id:
            self.oauth.register(
                name='google',
                client_id=self.settings.google_client_id,
                client_secret=self.settings.google_client_secret,
                server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
                client_kwargs={'scope': 'openid email profile'},
                # PKCE enabled by default in Authlib 1.0+
                code_challenge_method='S256'
            )
        
        # GitHub (OAuth 2.0 - manual endpoints)
        if self.settings.github_client_id:
            self.oauth.register(
                name='github',
                client_id=self.settings.github_client_id,
                client_secret=self.settings.github_client_secret,
                api_base_url='https://api.github.com/',
                authorize_url='https://github.com/login/oauth/authorize',
                access_token_url='https://github.com/login/oauth/access_token',
                client_kwargs={'scope': 'read:user user:email'},
                code_challenge_method='S256'
            )
        
        # Microsoft (OpenID Connect with tenant support)
        if self.settings.microsoft_client_id:
            tenant = self.settings.microsoft_tenant
            self.oauth.register(
                name='microsoft',
                client_id=self.settings.microsoft_client_id,
                client_secret=self.settings.microsoft_client_secret,
                server_metadata_url=f'https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration',
                client_kwargs={'scope': 'openid email profile'},
                code_challenge_method='S256'
            )
```

### Step 5: Implement Authentication Routes
Create `app/routers/sso.py`:
```python
#!/usr/bin/env python3
"""
RFC 9700 compliant SSO authentication routes
"""
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Dict, Any

from app.database import get_db_session
from app.models.user import User
from app.schemas.user import TokenResponse, UserResponse
from app.services.oauth_service import OAuthService
from app.middleware.auth_middleware import auth_middleware
from app.middleware.rate_limiting import auth_rate_limit

router = APIRouter(prefix="/auth", tags=["SSO Authentication"])
oauth_service = OAuthService()

@router.get("/login/{provider}")
@auth_rate_limit
async def sso_login(provider: str, request: Request):
    """Initiate OAuth/OIDC login with RFC 9700 security"""
    if provider not in ['google', 'github', 'microsoft']:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    
    # Generate PKCE parameters
    pkce_data = oauth_service.security.generate_pkce_pair()
    
    # Generate secure state with session binding
    session_data = {
        'provider': provider,
        'code_verifier': pkce_data['code_verifier'],
        'nonce': oauth_service.security.generate_nonce(),
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    state = oauth_service.security.generate_state_token(session_data)
    
    # Build authorization URL with PKCE
    client = oauth_service.oauth.create_client(provider)
    redirect_uri = getattr(oauth_service.settings, f'{provider}_redirect_uri')
    
    return await client.authorize_redirect(
        request, 
        redirect_uri,
        state=state,
        code_challenge=pkce_data['code_challenge'],
        code_challenge_method='S256',
        nonce=session_data['nonce'] if provider != 'github' else None  # GitHub doesn't support nonce
    )
```

### Step 6: Implement Callback Handler with Security Validation
```python
@router.get("/callback/{provider}")
async def sso_callback(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Handle OAuth callback with comprehensive security validation"""
    try:
        # Extract parameters
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        error = request.query_params.get('error')
        
        if error:
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
        
        if not code or not state:
            raise HTTPException(status_code=400, detail="Missing required parameters")
        
        # Verify state and extract session data
        try:
            session_data = oauth_service.security.verify_state_token(state)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Validate session data
        if session_data['provider'] != provider:
            raise HTTPException(status_code=400, detail="Provider mismatch")
        
        # Exchange code for tokens using PKCE
        client = oauth_service.oauth.create_client(provider)
        token = await client.authorize_access_token(
            request,
            code_verifier=session_data['code_verifier']
        )
        
        # Get user profile and validate
        user_profile = await _get_user_profile(provider, client, token, session_data.get('nonce'))
        
        # Find or create user
        user = await _find_or_create_user(db, provider, user_profile)
        
        # Generate our application tokens
        token_data = {"sub": str(user.id), "email": user.email}
        access_token = auth_middleware.create_access_token(token_data)
        refresh_token = auth_middleware.create_refresh_token(token_data)
        
        # Build user response
        from app.routers.auth import build_user_response
        user_response = await build_user_response(user, db)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=1800,
            user=user_response
        )
    
    except OAuthError as e:
        logger.error(f"OAuth error during {provider} callback: {e}")
        raise HTTPException(status_code=400, detail="OAuth authentication failed")
    except Exception as e:
        logger.error(f"Unexpected error during {provider} callback: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")
```

### Step 7: User Profile and Account Management
```python
async def _get_user_profile(provider: str, client, token: Dict, nonce: Optional[str]) -> Dict[str, Any]:
    """Get user profile with provider-specific handling and security validation"""
    if provider == 'google':
        # Validate ID token for OpenID Connect
        user_info = token.get('userinfo')
        if not user_info:
            user_info = await client.userinfo(token=token)
        
        # Validate nonce if present
        if nonce and user_info.get('nonce') != nonce:
            raise ValueError("Nonce validation failed")
        
        return {
            'id': user_info['sub'],
            'email': user_info['email'],
            'name': user_info.get('name'),
            'avatar_url': user_info.get('picture'),
            'email_verified': user_info.get('email_verified', False)
        }
    
    elif provider == 'github':
        # GitHub requires separate API calls
        async with httpx.AsyncClient() as http:
            headers = {'Authorization': f"Bearer {token['access_token']}"}
            
            # Get user profile
            user_resp = await http.get('https://api.github.com/user', headers=headers)
            user_data = user_resp.json()
            
            # Get verified email
            emails_resp = await http.get('https://api.github.com/user/emails', headers=headers)
            emails = emails_resp.json()
            primary_email = next((e for e in emails if e['primary'] and e['verified']), None)
            
            if not primary_email:
                raise ValueError("No verified email found")
            
            return {
                'id': str(user_data['id']),
                'email': primary_email['email'],
                'name': user_data.get('name') or user_data.get('login'),
                'avatar_url': user_data.get('avatar_url'),
                'email_verified': True
            }
    
    elif provider == 'microsoft':
        # Microsoft OpenID Connect
        user_info = token.get('userinfo')
        if not user_info:
            user_info = await client.userinfo(token=token)
        
        # Validate nonce
        if nonce and user_info.get('nonce') != nonce:
            raise ValueError("Nonce validation failed")
        
        return {
            'id': user_info['oid'],  # Use object ID as stable identifier
            'email': user_info['email'],
            'name': user_info.get('name'),
            'avatar_url': None,  # Microsoft Graph API required for avatar
            'email_verified': True  # Microsoft emails are pre-verified
        }

async def _find_or_create_user(db: AsyncSession, provider: str, profile: Dict[str, Any]) -> User:
    """Find existing user or create new one with multi-provider support and security validation"""
    external_id = profile['id']
    email = profile['email']
    email_verified = profile.get('email_verified', False)
    
    # Security validation: Only accept verified emails
    if not email_verified:
        raise HTTPException(
            status_code=400, 
            detail=f"Email not verified by {provider}. Please verify your email with the provider first."
        )
    
    # First, try to find by external auth ID (existing SSO user)
    result = await db.execute(
        select(User).where(
            and_(
                User.external_auth_provider == provider,
                User.external_auth_id == external_id
            )
        )
    )
    user = result.scalar_one_or_none()
    
    if user:
        # Existing SSO user - standard login
        user.record_login()
        await db.commit()
        return user
    
    # Look for existing user by email (potential account linking)
    result = await db.execute(select(User).where(User.email == email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        # Account linking scenario
        if existing_user.external_auth_provider:
            # Multi-provider linking
            await _link_additional_provider(db, existing_user, provider, external_id)
        else:
            # First SSO link to local account
            existing_user.external_auth_provider = provider
            existing_user.external_auth_id = external_id
        
        existing_user.is_verified = True  # SSO implies verified email
        existing_user.record_login()
        
        # Send security notification
        await _send_account_linking_notification(existing_user.email, provider)
        
        await db.commit()
        return existing_user
    
    # Create new user (JIT provisioning)
    new_user = User(
        email=email,
        full_name=profile.get('name'),
        is_verified=True,  # SSO accounts are pre-verified
        is_active=True,
        external_auth_provider=provider,
        external_auth_id=external_id,
        password_hash=None,  # No local password for SSO users
        avatar_url=profile.get('avatar_url'),
        preferences={'sso_providers': [provider]}  # Track SSO providers
    )
    
    new_user.record_login()
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user

async def _link_additional_provider(db: AsyncSession, user: User, provider: str, external_id: str):
    """Link additional SSO provider to existing multi-provider account"""
    
    # Get existing linked providers
    preferences = user.preferences or {}
    linked_providers = preferences.get('linked_providers', [])
    
    # Check if provider already linked
    existing_link = next((p for p in linked_providers if p['provider'] == provider), None)
    if existing_link:
        # Update external_id if changed
        existing_link['external_id'] = external_id
        existing_link['last_login'] = datetime.now(timezone.utc).isoformat()
    else:
        # Add new provider
        linked_providers.append({
            'provider': provider,
            'external_id': external_id,
            'linked_at': datetime.now(timezone.utc).isoformat(),
            'last_login': datetime.now(timezone.utc).isoformat()
        })
    
    # Update user preferences
    preferences['linked_providers'] = linked_providers
    user.preferences = preferences
    
    # Log security event
    logger.info(f"User {user.id} linked additional SSO provider: {provider}")

async def _send_account_linking_notification(email: str, provider: str):
    """Send email notification when new SSO provider is linked"""
    # Implementation would use your email service
    logger.info(f"Account linking notification sent to {email} for provider {provider}")
    # In production: send actual email notification
    pass

async def _validate_provider_linking_security(user: User, provider: str, request: Request) -> bool:
    """Enhanced security validation for provider linking"""
    
    # Rate limiting check
    recent_links = user.preferences.get('recent_provider_links', []) if user.preferences else []
    recent_count = len([link for link in recent_links 
                       if datetime.fromisoformat(link['timestamp']) > 
                       datetime.now(timezone.utc) - timedelta(hours=24)])
    
    if recent_count >= 3:  # Max 3 new provider links per day
        raise HTTPException(
            status_code=429,
            detail="Too many provider linking attempts. Please try again later."
        )
    
    return True
```

### Step 8: Update Main Router Registration
Add to `app/main.py`:
```python
from app.routers import sso
app.include_router(sso.router, prefix="/api/v1")
```

### Step 9: Provider Console Setup (Security-Focused)
**Google Cloud Console**:
- Create OAuth 2.0 credentials (Web application type)
- Add authorized redirect URI: `https://yourdomain.com/api/v1/auth/callback/google`
- Configure OAuth consent screen with required scopes: `openid`, `email`, `profile`
- Enable PKCE support (automatically enabled for public clients)

**GitHub Developer Settings**:
- Create OAuth App with Authorization callback URL: `https://yourdomain.com/api/v1/auth/callback/github`
- Request scopes: `read:user`, `user:email`
- Enable PKCE (GitHub supports PKCE as of 2024)

**Microsoft Entra ID**:
- Register application with redirect URI: `https://yourdomain.com/api/v1/auth/callback/microsoft`
- Configure API permissions: `openid`, `email`, `profile`
- Set tenant to `common` for multi-tenant or specific tenant ID
- PKCE is enabled by default for public clients

### Step 10: CORS and Security Headers
Update CORS settings in `app/main.py` to include OAuth callback origins.


## Minimal Code Sketches

Router endpoints (skeleton):
```python
# app/routers/sso.py
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_session
from app.middleware.auth_middleware import auth_middleware
from app.schemas.user import TokenResponse, UserResponse
from app.services.oauth_service import oauth_client, build_authorize_redirect, fetch_user_profile

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/login/{provider}")
async def oauth_login(provider: str, request: Request):
    return await build_authorize_redirect(provider, request)

@router.get("/callback/{provider}")
async def oauth_callback(provider: str, request: Request, db: AsyncSession = Depends(get_db_session)):
    profile = await fetch_user_profile(provider, request)
    # ... lookup/link/create user, then issue tokens ...
    return TokenResponse(...)
```

Service (skeleton):
```python
# app/services/oauth_service.py
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from app.config.settings import get_settings

settings = get_settings()
oauth = OAuth()

oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# Similar register for github (manual endpoints) and microsoft (tenant-based metadata)

async def build_authorize_redirect(provider: str, request: Request):
    client = oauth.create_client(provider)
    return await client.authorize_redirect(request, settings.google_redirect_uri if provider=="google" else ...)

async def fetch_user_profile(provider: str, request: Request):
    client = oauth.create_client(provider)
    token = await client.authorize_access_token(request)
    if provider == "google":
        userinfo = await client.userinfo(token=token)
        return {"email": userinfo.get("email"), "name": userinfo.get("name"), "id": userinfo.get("sub"), "avatar": userinfo.get("picture")}
    # github and microsoft similarly
```


## Frontend UX Flow
- Signup/Login page shows buttons: "Continue with Google", "Continue with Microsoft", "Continue with GitHub".
- Button hits `GET /auth/login/{provider}` → browser redirects to provider.
- After consent, provider redirects back to `/auth/callback/{provider}`.
- Backend responds with tokens JSON or redirects to frontend final page with a code to exchange.


## Comprehensive Testing & Validation Plan

### Test Categories

#### 1. Security Tests (CRITICAL - Must Pass)
**File**: `tests/test_sso_security.py`

```python
import pytest
from app.services.oauth_security import OAuthSecurityService
from app.services.oauth_service import OAuthService

@pytest.fixture
def oauth_security():
    return OAuthSecurityService("test-secret-key", 600)

class TestOAuthSecurity:
    def test_pkce_generation_s256_method(self, oauth_security):
        """Test PKCE pair generation uses S256 method"""
        pkce = oauth_security.generate_pkce_pair()
        assert pkce["code_challenge_method"] == "S256"
        assert len(pkce["code_verifier"]) >= 43  # RFC 7636 minimum
        assert len(pkce["code_challenge"]) >= 43
    
    def test_state_token_uniqueness(self, oauth_security):
        """Test state tokens are unique and session-bound"""
        state1 = oauth_security.generate_state_token({"provider": "google"})
        state2 = oauth_security.generate_state_token({"provider": "google"})
        assert state1 != state2
    
    def test_state_token_expiration(self, oauth_security):
        """Test state token expiration prevents replay attacks"""
        import time
        short_timeout_service = OAuthSecurityService("test-key", 1)
        state = short_timeout_service.generate_state_token({"test": "data"})
        time.sleep(2)
        with pytest.raises(ValueError, match="expired"):
            short_timeout_service.verify_state_token(state)
    
    def test_nonce_entropy(self, oauth_security):
        """Test nonce has sufficient entropy"""
        nonce1 = oauth_security.generate_nonce()
        nonce2 = oauth_security.generate_nonce()
        assert nonce1 != nonce2
        assert len(nonce1) >= 32  # Sufficient entropy
```

#### 2. OAuth Flow Integration Tests
**File**: `tests/test_sso_integration.py`

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

client = TestClient(app)

class TestOAuthFlows:
    @pytest.mark.asyncio
    async def test_google_login_initiation(self):
        """Test Google OAuth initiation with PKCE"""
        response = client.get("/api/v1/auth/login/google")
        assert response.status_code == 302  # Redirect to Google
        location = response.headers["location"]
        assert "accounts.google.com" in location
        assert "code_challenge=" in location
        assert "code_challenge_method=S256" in location
        assert "state=" in location
        assert "nonce=" in location
    
    @pytest.mark.asyncio 
    async def test_github_login_initiation(self):
        """Test GitHub OAuth initiation with PKCE"""
        response = client.get("/api/v1/auth/login/github")
        assert response.status_code == 302
        location = response.headers["location"]
        assert "github.com/login/oauth/authorize" in location
        assert "code_challenge=" in location
        assert "state=" in location
    
    @pytest.mark.asyncio
    async def test_invalid_provider_rejection(self):
        """Test rejection of unsupported providers"""
        response = client.get("/api/v1/auth/login/invalid")
        assert response.status_code == 400
        assert "Unsupported provider" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_callback_missing_parameters(self):
        """Test callback validation with missing parameters"""
        # Missing code
        response = client.get("/api/v1/auth/callback/google?state=test")
        assert response.status_code == 400
        
        # Missing state  
        response = client.get("/api/v1/auth/callback/google?code=test")
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_callback_invalid_state(self):
        """Test callback rejects invalid state tokens"""
        response = client.get("/api/v1/auth/callback/google?code=test&state=invalid")
        assert response.status_code == 400
        assert "Invalid or expired state token" in response.json()["detail"]
```

#### 3. User Management Tests
**File**: `tests/test_sso_users.py`

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.routers.sso import _find_or_create_user, _link_additional_provider
from fastapi import HTTPException

class TestSSOUserManagement:
    @pytest.mark.asyncio
    async def test_jit_user_creation(self, db_session: AsyncSession):
        """Test Just-In-Time user provisioning"""
        profile = {
            'id': 'google_123456',
            'email': 'newuser@example.com',
            'name': 'New User',
            'avatar_url': 'https://example.com/avatar.jpg',
            'email_verified': True
        }
        
        user = await _find_or_create_user(db_session, 'google', profile)
        
        assert user.email == 'newuser@example.com'
        assert user.external_auth_provider == 'google'
        assert user.external_auth_id == 'google_123456'
        assert user.is_verified is True
        assert user.password_hash is None
        assert user.avatar_url == 'https://example.com/avatar.jpg'
        assert user.preferences['sso_providers'] == ['google']
    
    @pytest.mark.asyncio
    async def test_existing_user_linking(self, db_session: AsyncSession):
        """Test linking SSO to existing email account"""
        # Create existing user
        existing_user = User(
            email='existing@example.com',
            password_hash='hashed_password',
            is_verified=False
        )
        db_session.add(existing_user)
        await db_session.commit()
        
        profile = {
            'id': 'google_789012',
            'email': 'existing@example.com',
            'name': 'Existing User',
            'email_verified': True
        }
        
        user = await _find_or_create_user(db_session, 'google', profile)
        
        assert user.id == existing_user.id  # Same user
        assert user.external_auth_provider == 'google'
        assert user.external_auth_id == 'google_789012'
        assert user.is_verified is True  # Updated to verified
        assert user.password_hash == 'hashed_password'  # Kept existing password
    
    @pytest.mark.asyncio
    async def test_multi_provider_linking(self, db_session: AsyncSession):
        """Test linking multiple SSO providers to same account"""
        # Create user with Google
        google_profile = {
            'id': 'google_123',
            'email': 'user@example.com',
            'name': 'Test User',
            'email_verified': True
        }
        user = await _find_or_create_user(db_session, 'google', google_profile)
        initial_user_id = user.id
        
        # Link GitHub to same email
        github_profile = {
            'id': 'github_456',
            'email': 'user@example.com',
            'name': 'Test User',
            'email_verified': True
        }
        linked_user = await _find_or_create_user(db_session, 'github', github_profile)
        
        # Should be same user
        assert linked_user.id == initial_user_id
        assert 'linked_providers' in linked_user.preferences
        assert len(linked_user.preferences['linked_providers']) == 1
        assert linked_user.preferences['linked_providers'][0]['provider'] == 'github'
        assert linked_user.preferences['linked_providers'][0]['external_id'] == 'github_456'
    
    @pytest.mark.asyncio
    async def test_unverified_email_rejection(self, db_session: AsyncSession):
        """Test rejection of unverified emails for security"""
        profile = {
            'id': 'google_123',
            'email': 'unverified@example.com',
            'name': 'Unverified User',
            'email_verified': False  # NOT verified
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await _find_or_create_user(db_session, 'google', profile)
        
        assert exc_info.value.status_code == 400
        assert "Email not verified" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_cross_provider_email_conflict(self, db_session: AsyncSession):
        """Test the specific edge case: user creates account with Provider A, then tries Provider B with same email"""
        
        # Step 1: User creates account with Google
        google_profile = {
            'id': 'google_original123',
            'email': 'user@example.com',
            'name': 'Original User',
            'email_verified': True
        }
        original_user = await _find_or_create_user(db_session, 'google', google_profile)
        original_login_count = int(original_user.login_count)
        
        # Step 2: Same email tries to login with GitHub (simulating logout -> different provider)
        github_profile = {
            'id': 'github_different456',
            'email': 'user@example.com',  # SAME EMAIL
            'name': 'Same Email User',
            'email_verified': True
        }
        
        # Should link to existing account, not create new one
        linked_user = await _find_or_create_user(db_session, 'github', github_profile)
        
        # Validation: Same user account
        assert linked_user.id == original_user.id
        assert int(linked_user.login_count) == original_login_count + 1
        
        # Validation: Multi-provider data stored
        assert 'linked_providers' in linked_user.preferences
        linked_providers = linked_user.preferences['linked_providers']
        github_provider = next((p for p in linked_providers if p['provider'] == 'github'), None)
        assert github_provider is not None
        assert github_provider['external_id'] == 'github_different456'
        
        # Validation: Security notification should be sent
        # (In real implementation, this would check notification system)
    
    @pytest.mark.asyncio
    async def test_different_emails_create_separate_accounts(self, db_session: AsyncSession):
        """Test that different emails create separate accounts (security boundary)"""
        # User 1 with email1
        profile1 = {
            'id': 'google_user1',
            'email': 'user1@example.com',
            'name': 'User One',
            'email_verified': True
        }
        user1 = await _find_or_create_user(db_session, 'google', profile1)
        
        # User 2 with different email (should be separate account)
        profile2 = {
            'id': 'google_user2',
            'email': 'user2@example.com',  # DIFFERENT EMAIL
            'name': 'User Two', 
            'email_verified': True
        }
        user2 = await _find_or_create_user(db_session, 'google', profile2)
        
        # Should be different users
        assert user1.id != user2.id
        assert user1.email != user2.email
        assert user1.external_auth_id != user2.external_auth_id
    
    @pytest.mark.asyncio
    async def test_sso_user_login_tracking(self, db_session: AsyncSession):
        """Test login tracking for SSO users"""
        profile = {
            'id': 'test123',
            'email': 'test@example.com',
            'email_verified': True
        }
        user = await _find_or_create_user(db_session, 'google', profile)
        
        initial_login_count = int(user.login_count)
        initial_login_time = user.last_login_at
        
        # Login again
        user = await _find_or_create_user(db_session, 'google', profile)
        
        assert int(user.login_count) == initial_login_count + 1
        assert user.last_login_at > initial_login_time
    
    @pytest.mark.asyncio
    async def test_provider_id_stability(self, db_session: AsyncSession):
        """Test that provider changes don't break user identification"""
        # Initial login
        profile = {
            'id': 'stable_id_123',
            'email': 'user@example.com',
            'name': 'Original Name',
            'email_verified': True
        }
        user = await _find_or_create_user(db_session, 'google', profile)
        original_id = user.id
        
        # Same provider ID but different email (provider email change)
        updated_profile = {
            'id': 'stable_id_123',  # SAME stable ID
            'email': 'newemail@example.com',  # Different email
            'name': 'Updated Name',
            'email_verified': True
        }
        
        # Should find same user by provider ID, not create new account
        same_user = await _find_or_create_user(db_session, 'google', updated_profile)
        assert same_user.id == original_id
        assert same_user.external_auth_id == 'stable_id_123'
        # Email should NOT be updated automatically for security
        assert same_user.email == 'user@example.com'  # Original email preserved
```

#### 4. Provider-Specific Tests
**File**: `tests/test_sso_providers.py`

```python
import pytest
from unittest.mock import patch, AsyncMock
import httpx
from app.routers.sso import _get_user_profile

class TestProviderIntegrations:
    @pytest.mark.asyncio
    async def test_google_profile_extraction(self):
        """Test Google OpenID Connect profile extraction"""
        mock_token = {
            'userinfo': {
                'sub': 'google_123456789',
                'email': 'user@gmail.com', 
                'email_verified': True,
                'name': 'Test User',
                'picture': 'https://lh3.googleusercontent.com/photo.jpg',
                'nonce': 'test_nonce_123'
            }
        }
        
        profile = await _get_user_profile('google', None, mock_token, 'test_nonce_123')
        
        assert profile['id'] == 'google_123456789'
        assert profile['email'] == 'user@gmail.com'
        assert profile['email_verified'] is True
        assert profile['name'] == 'Test User'
    
    @pytest.mark.asyncio
    async def test_google_nonce_validation_failure(self):
        """Test Google nonce validation prevents replay attacks"""
        mock_token = {
            'userinfo': {'sub': '123', 'email': 'user@gmail.com', 'nonce': 'wrong_nonce'}
        }
        
        with pytest.raises(ValueError, match="Nonce validation failed"):
            await _get_user_profile('google', None, mock_token, 'correct_nonce')
    
    @pytest.mark.asyncio
    async def test_github_profile_extraction(self):
        """Test GitHub OAuth profile extraction"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock()
            
            # Mock user profile response
            mock_user_resp = AsyncMock()
            mock_user_resp.json.return_value = {
                'id': 12345678,
                'login': 'testuser',
                'name': 'Test User',
                'avatar_url': 'https://github.com/avatar.jpg'
            }
            
            # Mock emails response
            mock_emails_resp = AsyncMock()
            mock_emails_resp.json.return_value = [
                {'email': 'user@example.com', 'primary': True, 'verified': True},
                {'email': 'alt@example.com', 'primary': False, 'verified': True}
            ]
            
            mock_client.return_value.__aenter__.return_value.get.side_effect = [
                mock_user_resp, mock_emails_resp
            ]
            
            mock_token = {'access_token': 'github_token_123'}
            profile = await _get_user_profile('github', None, mock_token, None)
            
            assert profile['id'] == '12345678'
            assert profile['email'] == 'user@example.com'  # Primary verified email
            assert profile['name'] == 'Test User'
    
    @pytest.mark.asyncio
    async def test_github_no_verified_email_error(self):
        """Test GitHub profile extraction fails without verified email"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock()
            
            mock_user_resp = AsyncMock()
            mock_user_resp.json.return_value = {'id': 123, 'login': 'user'}
            
            mock_emails_resp = AsyncMock()
            mock_emails_resp.json.return_value = [
                {'email': 'unverified@example.com', 'primary': True, 'verified': False}
            ]
            
            mock_client.return_value.__aenter__.return_value.get.side_effect = [
                mock_user_resp, mock_emails_resp
            ]
            
            with pytest.raises(ValueError, match="No verified email found"):
                await _get_user_profile('github', None, {'access_token': 'token'}, None)
```

#### 5. End-to-End Tests
**File**: `tests/test_sso_e2e.py`

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

class TestSSOEndToEnd:
    """End-to-end SSO flow testing"""
    
    @pytest.mark.asyncio
    async def test_complete_google_flow(self):
        """Test complete Google SSO flow from initiation to token"""
        client = TestClient(app)
        
        # Step 1: Initiate login
        response = client.get("/api/v1/auth/login/google")
        assert response.status_code == 302
        
        # Extract state from redirect URL
        location = response.headers["location"]
        state = location.split("state=")[1].split("&")[0]
        
        # Step 2: Mock successful callback with valid token exchange
        with patch('app.services.oauth_service.OAuthService') as mock_service:
            mock_oauth = AsyncMock()
            mock_service.return_value = mock_oauth
            
            # Mock token exchange
            mock_oauth.oauth.create_client.return_value.authorize_access_token = AsyncMock(
                return_value={
                    'userinfo': {
                        'sub': 'google_test_123',
                        'email': 'test@example.com',
                        'email_verified': True,
                        'name': 'Test User',
                        'nonce': 'mock_nonce'
                    }
                }
            )
            
            # Mock state verification
            mock_oauth.security.verify_state_token = AsyncMock(
                return_value={
                    'provider': 'google',
                    'code_verifier': 'mock_verifier',
                    'nonce': 'mock_nonce'
                }
            )
            
            response = client.get(f"/api/v1/auth/callback/google?code=mock_code&state={state}")
            
            assert response.status_code == 200
            data = response.json()
            assert 'access_token' in data
            assert 'refresh_token' in data
            assert data['token_type'] == 'bearer'
            assert 'user' in data
```

### Manual Testing Checklist

#### Pre-Implementation Validation
- [ ] **Dependencies installed**: `poetry add authlib itsdangerous`
- [ ] **Settings updated**: OAuth provider configurations added to `app/config/settings.py`
- [ ] **Environment variables**: All required OAuth secrets configured
- [ ] **Database ready**: User model supports external auth fields
- [ ] **Router registered**: SSO router included in main app

#### Security Validation (MANDATORY)
- [ ] **PKCE Implementation**: All providers use S256 code challenge method
- [ ] **State Parameter**: Cryptographically random, session-bound, expires after 10 minutes
- [ ] **Nonce Validation**: OpenID Connect flows validate nonce parameter
- [ ] **Token Signature**: ID tokens verified against provider public keys  
- [ ] **Provider Endpoints**: Using official provider discovery URLs
- [ ] **HTTPS Enforcement**: Production redirects use HTTPS only
- [ ] **CSRF Protection**: State parameter prevents cross-site request forgery
- [ ] **Session Binding**: OAuth flows bound to specific user sessions

#### Provider Testing
- [ ] **Google OAuth**: Login initiation redirects to accounts.google.com
- [ ] **Google Callback**: Successful authentication returns valid tokens
- [ ] **GitHub OAuth**: Login redirects to github.com/login/oauth/authorize  
- [ ] **GitHub Callback**: Profile and email extraction works correctly
- [ ] **Microsoft OAuth**: Tenant-aware redirection to login.microsoftonline.com
- [ ] **Microsoft Callback**: Azure AD profile extraction successful

#### User Management Testing  
- [ ] **JIT Provisioning**: New users created automatically on first login
- [ ] **Account Linking**: Existing email accounts link to SSO provider
- [ ] **Login Tracking**: SSO logins update last_login_at and login_count
- [ ] **Profile Sync**: User profile updated with provider information
- [ ] **Email Verification**: SSO users marked as verified automatically

#### Error Handling
- [ ] **Invalid Provider**: Unsupported providers return 400 error
- [ ] **Missing Parameters**: Callback validates required code/state parameters
- [ ] **Expired State**: Old state tokens rejected with appropriate error
- [ ] **Provider Errors**: OAuth errors handled gracefully
- [ ] **Network Failures**: Timeout/connection errors handled properly

#### Integration Testing
- [ ] **Token Compatibility**: SSO tokens work with existing protected endpoints
- [ ] **User Response Format**: SSO user responses match local auth format
- [ ] **CORS Configuration**: Frontend origins can access SSO endpoints
- [ ] **Rate Limiting**: SSO endpoints respect rate limiting rules
- [ ] **Database Constraints**: No unique constraint violations on user creation


## Rollout Plan
- Stage behind feature flags per environment.
- Start with Google (simplest OIDC), then GitHub, then Microsoft.
- Add admin visibility of linked providers on user profile.


## Maintenance
- Rotate client secrets regularly; prefer using secret manager.
- Monitor provider deprecations and OIDC metadata changes.
- Log audit events on SSO logins and linking.


