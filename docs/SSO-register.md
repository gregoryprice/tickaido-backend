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


## Libraries
- Prefer using Authlib for FastAPI: `authlib` supports OAuth/OIDC with Google, GitHub, Microsoft.
- Alternatively, roll your own with `httpx` and provider endpoints; Authlib reduces boilerplate and handles edge cases.

Add to Poetry:
```bash
poetry add authlib httpx
```


## Configuration
Add the following fields to `Settings` in `app/config/settings.py` (keeping env-var driven):
- Google: `google_client_id`, `google_client_secret`, `google_redirect_uri`
- GitHub: `github_client_id`, `github_client_secret`, `github_redirect_uri`
- Microsoft (Entra ID common tenant for multi-tenant or your tenant): `ms_client_id`, `ms_client_secret`, `ms_tenant`, `ms_redirect_uri`

Example env vars (.env):
```bash
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback/google

GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GITHUB_REDIRECT_URI=http://localhost:8000/auth/callback/github

MS_CLIENT_ID=...
MS_CLIENT_SECRET=...
MS_TENANT=common
MS_REDIRECT_URI=http://localhost:8000/auth/callback/microsoft
```

Update `Settings` class accordingly and expose through `get_settings()`.


## Database Model Notes
`User` already supports external auth; no migration needed. Ensure a unique constraint pairing `(external_auth_provider, external_auth_id)` implicitly by logic (we already have `external_auth_id` indexed). If you want strict DB-level uniqueness, add a composite unique constraint in a future migration.


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

Security considerations:
- Always validate `state` parameter for CSRF protection.
- Use PKCE for public SPA initiations or keep the code exchange on backend with a confidential client.
- For Microsoft and Google, validate the ID token issuer and audience; Authlib can perform this, or validate JWT claims manually.


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


## Backend Implementation Steps
1) Install libs:
```bash
poetry add authlib httpx
```

2) Extend `Settings` with provider secrets and redirect URIs.

3) Create `app/services/oauth_service.py`:
   - Initialize Authlib OAuth registry.
   - Register `google`, `github`, `microsoft` clients with client_id/secret and endpoints.
   - Helpers to build authorization URLs and exchange codes, fetch userinfo.

4) Add new routes in `app/routers/auth.py` or a new `app/routers/sso.py`:
   - `GET /auth/login/{provider}`: builds `state` (store in server-side session/Redis) and returns redirect URL.
   - `GET /auth/callback/{provider}`: performs code exchange and JIT user create/link, then returns our JWTs.
   - Reuse existing response models `TokenResponse`, `UserResponse`.

5) User linking/creation logic:
   - If user exists by `(provider, external_id)`: use it.
   - Else if exists by `email`: link it by setting `external_auth_provider` and `external_auth_id`.
   - Else create new `User` (set `is_verified=True`, `password_hash=None`, `full_name` from profile, `avatar_url` if available).

6) CORS and Redirects:
   - Ensure `settings.cors_origins` includes your frontend origins.
   - If using a browser redirect flow, either:
     - Return JSON directly if frontend calls callback via XHR, or
     - Redirect to a frontend `/#/auth/callback?code=...` and let frontend call `/auth/token/exchange` to get our JWTs.

7) Security:
   - Verify `state` to mitigate CSRF.
   - Validate ID token (issuer, audience) for OIDC providers.
   - Use HTTPS in production and set exact redirect URIs at provider consoles.

8) Provider Console Setup
   - Google Cloud Console → OAuth consent screen, create Web app credentials, add redirect URI.
   - GitHub Developer Settings → OAuth Apps, add callback URL.
   - Microsoft Entra ID → App registrations, add redirect URI, expose `email`/`profile` scopes.


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


## Testing
- Create test scripts under a temp folder per workspace rules (e.g., `/project-tests`) to validate:
  - Redirect URL building with `state` present
  - Callback validation for missing/invalid `state` or `code`
  - JIT user creation and linking behavior
  - Token issuance response shape equals `/auth/login` response


## Rollout Plan
- Stage behind feature flags per environment.
- Start with Google (simplest OIDC), then GitHub, then Microsoft.
- Add admin visibility of linked providers on user profile.


## Maintenance
- Rotate client secrets regularly; prefer using secret manager.
- Monitor provider deprecations and OIDC metadata changes.
- Log audit events on SSO logins and linking.


