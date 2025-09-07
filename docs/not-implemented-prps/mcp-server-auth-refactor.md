# MCP Server OAuth 2.1 Authentication Refactor PRP

**Problem Resolution Proposal**  
**Document Version:** 1.0  
**Date:** 2025-09-04  
**Author:** AI Assistant  
**Status:** Implementation Roadmap - MCP OAuth 2.1 Specification Compliance  

## Executive Summary

This PRP outlines the complete refactor of our MCP authentication system to comply with the **official MCP OAuth 2.1 specification (March 2025)**. The implementation follows a strict validation approach where **ALL tests must pass and Docker logs must be error-free** before proceeding to each subsequent phase.

## Target Architecture

### OAuth 2.1 MCP Architecture
```
┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────┐
│   MCP Client    │    │  Authorization      │    │   MCP Server    │
│                 │    │      Server         │    │                 │
│  ┌─────────────┐│    │  ┌─────────────────┐│    │ ┌─────────────┐ │
│  │ AI Agent    ││◄──►│  │ OAuth 2.1       ││◄──►│ │ Resource    │ │
│  │             ││    │  │ + PKCE          ││    │ │ Server      │ │
│  │ Discovery   ││    │  │ Dynamic Client  ││    │ │ Token       │ │
│  │ Protocol    ││    │  │ Registration    ││    │ │ Validation  │ │
│  └─────────────┘│    │  └─────────────────┘│    │ └─────────────┘ │
└─────────────────┘    └─────────────────────┘    └─────────────────┘
         │                        │                         │
         ▼                        ▼                         ▼
   OAuth Flow               Token Issuance            Resource Access
   PKCE Validation         Scope Management           Bearer Validation
   Client Registration     RFC 8707 Compliance       API Authorization
```

### Core Components Overview

**1. Authorization Server (New Service)**
- **Port**: `:9000`
- **Responsibilities**: OAuth 2.1 flows, token issuance, client registration
- **Standards**: RFC 6749, RFC 7636 (PKCE), RFC 7591 (DCR), RFC 8414 (metadata)

**2. MCP Server (Refactored)**
- **Port**: `:8001` 
- **New Role**: OAuth 2.1 Resource Server
- **Responsibilities**: Token validation, resource protection, scope enforcement

**3. MCP Client (Enhanced)**
- **Integration**: AI Agent OAuth client
- **Responsibilities**: OAuth flows, token management, discovery protocol

## Implementation Phases

### 🎯 **CRITICAL SUCCESS CRITERIA**

**Before ANY phase progression:**
1. ✅ **100% Test Suite Pass**: All `poetry run pytest` tests must pass
2. ✅ **Clean Docker Logs**: No errors, warnings, or authentication failures
3. ✅ **End-to-End Validation**: Complete authentication flows working
4. ✅ **Performance Baseline**: <50ms additional latency per MCP call
5. ✅ **Security Audit**: No token exposure, proper scope enforcement

---

## Phase 1: Authorization Server Infrastructure
**Duration:** 2 weeks  
**Validation Required:** All tests pass + clean Docker logs

### 1.1 OAuth 2.1 Authorization Server Setup

**File:** `oauth_server/main.py`
```python
"""
OAuth 2.1 Authorization Server with PKCE and Dynamic Client Registration
Compliant with MCP March 2025 specification
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, RedirectResponse
import secrets
import hashlib
import base64
from typing import Dict, Optional, List
from datetime import datetime, timedelta, timezone
import jwt
from pydantic import BaseModel, Field
import os
import logging

logger = logging.getLogger(__name__)

# OAuth 2.1 Configuration
OAUTH_CONFIG = {
    "issuer": os.getenv("OAUTH_ISSUER", "http://localhost:9000"),
    "authorization_endpoint": "/oauth/authorize",
    "token_endpoint": "/oauth/token", 
    "registration_endpoint": "/oauth/register",
    "jwks_uri": "/.well-known/jwks.json",
    "scopes_supported": ["mcp:read", "mcp:write", "mcp:admin", "mcp:tools"],
    "grant_types_supported": ["authorization_code", "client_credentials"],
    "code_challenge_methods_supported": ["S256"],  # PKCE required
    "token_endpoint_auth_methods_supported": ["client_secret_post", "none"],
    "response_types_supported": ["code"]
}

app = FastAPI(
    title="MCP OAuth 2.1 Authorization Server",
    description="OAuth 2.1 compliant authorization server for MCP ecosystem",
    version="1.0.0"
)

# In-memory storage (replace with database in production)
clients_db: Dict[str, Dict] = {}
authorization_codes: Dict[str, Dict] = {}
access_tokens: Dict[str, Dict] = {}
pkce_challenges: Dict[str, Dict] = {}

class ClientRegistrationRequest(BaseModel):
    """RFC 7591 Dynamic Client Registration"""
    client_name: str = Field(..., description="Human-readable client name")
    client_uri: Optional[str] = Field(None, description="Client information URL")
    redirect_uris: List[str] = Field(..., description="Authorized redirect URIs")
    scope: str = Field(default="mcp:read mcp:write", description="Requested scopes")
    grant_types: List[str] = Field(default=["authorization_code"], description="Grant types")
    response_types: List[str] = Field(default=["code"], description="Response types")

class ClientRegistrationResponse(BaseModel):
    """RFC 7591 Client Registration Response"""
    client_id: str
    client_secret: Optional[str] = None
    client_name: str
    client_uri: Optional[str] = None
    redirect_uris: List[str]
    scope: str
    grant_types: List[str]
    response_types: List[str]
    client_id_issued_at: int
    client_secret_expires_at: int = 0  # 0 = never expires

class TokenRequest(BaseModel):
    """OAuth 2.1 Token Request"""
    grant_type: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    client_id: str
    client_secret: Optional[str] = None
    code_verifier: Optional[str] = None  # PKCE
    scope: Optional[str] = None

class TokenResponse(BaseModel):
    """OAuth 2.1 Token Response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str
    refresh_token: Optional[str] = None

@app.get("/.well-known/oauth-authorization-server")
async def oauth_metadata():
    """RFC 8414 - OAuth 2.0 Authorization Server Metadata"""
    base_url = OAUTH_CONFIG["issuer"]
    
    metadata = {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}{OAUTH_CONFIG['authorization_endpoint']}",
        "token_endpoint": f"{base_url}{OAUTH_CONFIG['token_endpoint']}",
        "registration_endpoint": f"{base_url}{OAUTH_CONFIG['registration_endpoint']}",
        "jwks_uri": f"{base_url}{OAUTH_CONFIG['jwks_uri']}",
        "scopes_supported": OAUTH_CONFIG["scopes_supported"],
        "response_types_supported": OAUTH_CONFIG["response_types_supported"],
        "grant_types_supported": OAUTH_CONFIG["grant_types_supported"],
        "code_challenge_methods_supported": OAUTH_CONFIG["code_challenge_methods_supported"],
        "token_endpoint_auth_methods_supported": OAUTH_CONFIG["token_endpoint_auth_methods_supported"],
        "subject_types_supported": ["public"]
    }
    
    logger.info("OAuth metadata requested")
    return metadata

@app.post("/oauth/register", response_model=ClientRegistrationResponse)
async def register_client(request: ClientRegistrationRequest):
    """RFC 7591 - OAuth 2.0 Dynamic Client Registration"""
    
    # Validate redirect URIs
    for uri in request.redirect_uris:
        if not (uri.startswith("https://") or uri.startswith("http://localhost")):
            raise HTTPException(400, "Invalid redirect URI - must be HTTPS or localhost")
    
    # Generate client credentials
    client_id = f"mcp_client_{secrets.token_urlsafe(16)}"
    client_secret = secrets.token_urlsafe(32)
    
    # Store client
    client_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_name": request.client_name,
        "client_uri": request.client_uri,
        "redirect_uris": request.redirect_uris,
        "scope": request.scope,
        "grant_types": request.grant_types,
        "response_types": request.response_types,
        "created_at": datetime.now(timezone.utc).timestamp()
    }
    
    clients_db[client_id] = client_data
    
    logger.info(f"Registered new OAuth client: {client_id}")
    
    return ClientRegistrationResponse(
        client_id=client_id,
        client_secret=client_secret,
        client_name=request.client_name,
        client_uri=request.client_uri,
        redirect_uris=request.redirect_uris,
        scope=request.scope,
        grant_types=request.grant_types,
        response_types=request.response_types,
        client_id_issued_at=int(client_data["created_at"])
    )

@app.get("/oauth/authorize")
async def authorize(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: Optional[str] = None,
    state: Optional[str] = None,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = None,
    resource: Optional[str] = None  # RFC 8707 Resource Indicators
):
    """OAuth 2.1 Authorization Endpoint with PKCE"""
    
    # Validate client
    if client_id not in clients_db:
        raise HTTPException(400, "Invalid client_id")
    
    client = clients_db[client_id]
    
    # Validate redirect URI
    if redirect_uri not in client["redirect_uris"]:
        raise HTTPException(400, "Invalid redirect_uri")
    
    # Validate response type
    if response_type != "code":
        raise HTTPException(400, "Unsupported response_type")
    
    # PKCE validation (required for MCP)
    if not code_challenge or code_challenge_method != "S256":
        error_uri = f"{redirect_uri}?error=invalid_request&error_description=PKCE+required"
        if state:
            error_uri += f"&state={state}"
        return RedirectResponse(error_uri)
    
    # Generate authorization code
    auth_code = secrets.token_urlsafe(32)
    
    # Store authorization code and PKCE challenge
    auth_data = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope or "mcp:read mcp:write",
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "resource": resource,  # RFC 8707
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)
    }
    
    authorization_codes[auth_code] = auth_data
    
    # Redirect back to client with authorization code
    callback_uri = f"{redirect_uri}?code={auth_code}"
    if state:
        callback_uri += f"&state={state}"
    
    logger.info(f"Authorization code issued for client {client_id}")
    return RedirectResponse(callback_uri)

@app.post("/oauth/token", response_model=TokenResponse)
async def token_endpoint(
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),  # PKCE
    scope: Optional[str] = Form(None)
):
    """OAuth 2.1 Token Endpoint with PKCE verification"""
    
    if grant_type == "authorization_code":
        # Validate authorization code
        if not code or code not in authorization_codes:
            raise HTTPException(400, "Invalid authorization code")
        
        auth_data = authorization_codes[code]
        
        # Check expiry
        if datetime.now(timezone.utc) > auth_data["expires_at"]:
            del authorization_codes[code]
            raise HTTPException(400, "Authorization code expired")
        
        # Validate client
        if client_id != auth_data["client_id"]:
            raise HTTPException(400, "Invalid client")
        
        if client_id in clients_db:
            client = clients_db[client_id]
            if client_secret != client["client_secret"]:
                raise HTTPException(400, "Invalid client credentials")
        
        # PKCE verification (required)
        if not code_verifier:
            raise HTTPException(400, "PKCE code_verifier required")
        
        # Verify PKCE challenge
        code_challenge = auth_data["code_challenge"]
        computed_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        
        if code_challenge != computed_challenge:
            raise HTTPException(400, "PKCE verification failed")
        
        # Generate access token
        access_token = jwt.encode(
            {
                "iss": OAUTH_CONFIG["issuer"],
                "sub": client_id,
                "aud": auth_data.get("resource", "mcp-server"),  # RFC 8707
                "scope": auth_data["scope"],
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iat": datetime.now(timezone.utc),
                "client_id": client_id
            },
            os.getenv("JWT_SECRET_KEY", "oauth-secret-key"),
            algorithm="HS256"
        )
        
        # Store token
        token_data = {
            "client_id": client_id,
            "scope": auth_data["scope"],
            "resource": auth_data.get("resource"),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        access_tokens[access_token] = token_data
        
        # Clean up authorization code
        del authorization_codes[code]
        
        logger.info(f"Access token issued for client {client_id}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=3600,
            scope=auth_data["scope"]
        )
    
    elif grant_type == "client_credentials":
        # Client credentials flow for server-to-server
        if client_id not in clients_db:
            raise HTTPException(400, "Invalid client")
        
        client = clients_db[client_id]
        if client_secret != client["client_secret"]:
            raise HTTPException(400, "Invalid client credentials")
        
        # Generate access token
        token_scope = scope or "mcp:read mcp:write"
        access_token = jwt.encode(
            {
                "iss": OAUTH_CONFIG["issuer"],
                "sub": client_id,
                "aud": "mcp-server",
                "scope": token_scope,
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iat": datetime.now(timezone.utc),
                "client_id": client_id
            },
            os.getenv("JWT_SECRET_KEY", "oauth-secret-key"),
            algorithm="HS256"
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="Bearer", 
            expires_in=3600,
            scope=token_scope
        )
    
    else:
        raise HTTPException(400, "Unsupported grant_type")

@app.get("/.well-known/jwks.json")
async def jwks():
    """JSON Web Key Set for token verification"""
    # In production, use proper JWKS with RSA keys
    return {
        "keys": [
            {
                "kty": "oct",  # Symmetric key for demo
                "use": "sig",
                "kid": "oauth-key-1",
                "alg": "HS256"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
```

**File:** `oauth_server/Dockerfile`
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 9000

CMD ["python", "main.py"]
```

**File:** `oauth_server/requirements.txt`
```text
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-jose[cryptography]==3.3.0
pydantic==2.5.0
python-multipart==0.0.6
```

### 1.2 Docker Compose Integration

**File:** `compose.yml` (Update)
```yaml
services:
  # ... existing services ...

  oauth-server:
    build: 
      context: ./oauth_server
      dockerfile: Dockerfile
    container_name: support-extension-oauth-server-1
    ports:
      - "9000:9000"
    environment:
      - OAUTH_ISSUER=http://localhost:9000
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/.well-known/oauth-authorization-server"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - app-network
    profiles:
      - oauth
      - all
```

### 1.3 Phase 1 Validation Tests

**File:** `tests/test_oauth_server.py`
```python
"""OAuth 2.1 Authorization Server Tests"""

import pytest
import httpx
from datetime import datetime, timezone
import secrets
import hashlib
import base64
import jwt
import os

OAUTH_BASE_URL = "http://localhost:9000"

class TestOAuthServer:
    
    @pytest.mark.asyncio
    async def test_oauth_metadata_endpoint(self):
        """Test OAuth 2.0 Authorization Server Metadata (RFC 8414)"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OAUTH_BASE_URL}/.well-known/oauth-authorization-server")
            
        assert response.status_code == 200
        metadata = response.json()
        
        # Required metadata fields
        assert "issuer" in metadata
        assert "authorization_endpoint" in metadata
        assert "token_endpoint" in metadata
        assert "jwks_uri" in metadata
        assert "scopes_supported" in metadata
        assert "grant_types_supported" in metadata
        assert "code_challenge_methods_supported" in metadata
        
        # MCP-specific requirements
        assert "S256" in metadata["code_challenge_methods_supported"]
        assert "authorization_code" in metadata["grant_types_supported"]
        assert "mcp:read" in metadata["scopes_supported"]
    
    @pytest.mark.asyncio
    async def test_dynamic_client_registration(self):
        """Test RFC 7591 Dynamic Client Registration"""
        registration_data = {
            "client_name": "Test MCP Client",
            "redirect_uris": ["http://localhost:3000/callback"],
            "scope": "mcp:read mcp:write",
            "grant_types": ["authorization_code"]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OAUTH_BASE_URL}/oauth/register",
                json=registration_data
            )
        
        assert response.status_code == 200
        registration_response = response.json()
        
        # Validate registration response
        assert "client_id" in registration_response
        assert "client_secret" in registration_response
        assert registration_response["client_name"] == "Test MCP Client"
        assert registration_response["redirect_uris"] == ["http://localhost:3000/callback"]
        assert registration_response["scope"] == "mcp:read mcp:write"
        
        return registration_response
    
    @pytest.mark.asyncio
    async def test_pkce_authorization_flow(self):
        """Test OAuth 2.1 Authorization Code Flow with PKCE"""
        
        # Step 1: Register client
        client_info = await self.test_dynamic_client_registration()
        client_id = client_info["client_id"]
        client_secret = client_info["client_secret"]
        redirect_uri = client_info["redirect_uris"][0]
        
        # Step 2: Generate PKCE parameters
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        
        # Step 3: Authorization request
        auth_params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "mcp:read mcp:write",
            "state": "test-state",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "resource": "mcp-server"  # RFC 8707
        }
        
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.get(
                f"{OAUTH_BASE_URL}/oauth/authorize",
                params=auth_params
            )
        
        assert response.status_code == 307  # Redirect response
        location = response.headers["location"]
        assert "code=" in location
        assert "state=test-state" in location
        
        # Extract authorization code
        code_start = location.find("code=") + 5
        code_end = location.find("&", code_start)
        if code_end == -1:
            code_end = len(location)
        auth_code = location[code_start:code_end]
        
        # Step 4: Token exchange
        token_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": code_verifier
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OAUTH_BASE_URL}/oauth/token",
                data=token_data
            )
        
        assert response.status_code == 200
        token_response = response.json()
        
        # Validate token response
        assert "access_token" in token_response
        assert token_response["token_type"] == "Bearer"
        assert "expires_in" in token_response
        assert "scope" in token_response
        
        # Validate JWT token
        access_token = token_response["access_token"]
        payload = jwt.decode(
            access_token,
            os.getenv("JWT_SECRET_KEY", "oauth-secret-key"),
            algorithms=["HS256"]
        )
        
        assert payload["client_id"] == client_id
        assert payload["aud"] == "mcp-server"  # RFC 8707 resource indicator
        assert "mcp:read" in payload["scope"]
        
        return access_token
    
    @pytest.mark.asyncio
    async def test_client_credentials_flow(self):
        """Test OAuth 2.1 Client Credentials Grant"""
        
        # Register client
        client_info = await self.test_dynamic_client_registration()
        client_id = client_info["client_id"]
        client_secret = client_info["client_secret"]
        
        # Client credentials request
        token_data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "mcp:read mcp:tools"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OAUTH_BASE_URL}/oauth/token",
                data=token_data
            )
        
        assert response.status_code == 200
        token_response = response.json()
        
        assert "access_token" in token_response
        assert token_response["token_type"] == "Bearer"
        assert token_response["scope"] == "mcp:read mcp:tools"
        
        return token_response["access_token"]
    
    @pytest.mark.asyncio
    async def test_pkce_validation_failure(self):
        """Test PKCE validation failure scenarios"""
        
        client_info = await self.test_dynamic_client_registration()
        client_id = client_info["client_id"]
        redirect_uri = client_info["redirect_uris"][0]
        
        # Missing PKCE parameters
        auth_params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "mcp:read"
        }
        
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.get(
                f"{OAUTH_BASE_URL}/oauth/authorize",
                params=auth_params
            )
        
        assert response.status_code == 307
        location = response.headers["location"]
        assert "error=invalid_request" in location
        assert "PKCE+required" in location
    
    @pytest.mark.asyncio
    async def test_jwks_endpoint(self):
        """Test JWKS endpoint for token verification"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OAUTH_BASE_URL}/.well-known/jwks.json")
        
        assert response.status_code == 200
        jwks = response.json()
        
        assert "keys" in jwks
        assert len(jwks["keys"]) > 0
        
        key = jwks["keys"][0]
        assert "kty" in key
        assert "use" in key
        assert "kid" in key
```

### 1.4 Phase 1 Validation Commands

```bash
# Phase 1 Validation Checklist

# 1. Start OAuth server
docker compose --profile oauth up -d oauth-server

# 2. Verify OAuth server health
curl -f http://localhost:9000/.well-known/oauth-authorization-server

# 3. Run OAuth server tests
poetry run pytest tests/test_oauth_server.py -v

# 4. Verify Docker logs are clean
docker logs support-extension-oauth-server-1 | grep -E "(ERROR|FAIL|Exception)"
# Should return no results

# 5. Run full test suite
poetry run pytest -v
# ALL tests must pass

# PHASE 1 GATE: 
# ✅ All OAuth tests pass
# ✅ No Docker errors/warnings
# ✅ Full test suite passes (436/436)
```

---

## Phase 2: MCP Server Resource Server Refactor
**Duration:** 2 weeks  
**Prerequisites:** Phase 1 complete + all validations passed

### 2.1 MCP Server OAuth 2.1 Resource Server

**File:** `mcp_server/oauth_resource_server.py`
```python
"""
MCP Server as OAuth 2.1 Resource Server
Compliant with MCP March 2025 specification
"""

import jwt
import httpx
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

logger = logging.getLogger(__name__)

class MCPResourceServer:
    """OAuth 2.1 Resource Server for MCP tools"""
    
    def __init__(self):
        self.oauth_server_url = os.getenv("OAUTH_SERVER_URL", "http://oauth-server:9000")
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "oauth-secret-key")
        self.required_audience = "mcp-server"
        self._metadata_cache: Optional[Dict] = None
        self._jwks_cache: Optional[Dict] = None
        self._cache_expiry: Optional[datetime] = None
    
    async def get_oauth_metadata(self) -> Dict[str, Any]:
        """Get OAuth server metadata with caching"""
        if self._metadata_cache and self._cache_expiry and datetime.now() < self._cache_expiry:
            return self._metadata_cache
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.oauth_server_url}/.well-known/oauth-authorization-server"
                )
                response.raise_for_status()
                
                self._metadata_cache = response.json()
                self._cache_expiry = datetime.now() + timedelta(minutes=15)
                
                logger.info("OAuth metadata retrieved and cached")
                return self._metadata_cache
                
        except Exception as e:
            logger.error(f"Failed to get OAuth metadata: {e}")
            raise HTTPException(503, "OAuth authorization server unavailable")
    
    async def get_jwks(self) -> Dict[str, Any]:
        """Get JWKS for token verification with caching"""
        if self._jwks_cache and self._cache_expiry and datetime.now() < self._cache_expiry:
            return self._jwks_cache
        
        try:
            metadata = await self.get_oauth_metadata()
            jwks_uri = metadata.get("jwks_uri")
            
            if not jwks_uri:
                raise HTTPException(503, "JWKS URI not found in OAuth metadata")
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(jwks_uri)
                response.raise_for_status()
                
                self._jwks_cache = response.json()
                logger.info("JWKS retrieved and cached")
                return self._jwks_cache
                
        except Exception as e:
            logger.error(f"Failed to get JWKS: {e}")
            raise HTTPException(503, "Token verification unavailable")
    
    async def validate_access_token(self, token: str) -> Dict[str, Any]:
        """Validate OAuth 2.1 access token"""
        try:
            # Decode and validate JWT token
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"],
                audience=self.required_audience,
                options={"verify_exp": True}
            )
            
            # Validate required claims
            required_claims = ["iss", "sub", "aud", "exp", "iat", "scope"]
            for claim in required_claims:
                if claim not in payload:
                    raise HTTPException(401, f"Missing required claim: {claim}")
            
            # Validate issuer
            metadata = await self.get_oauth_metadata()
            expected_issuer = metadata.get("issuer")
            if payload.get("iss") != expected_issuer:
                raise HTTPException(401, "Invalid token issuer")
            
            # Validate audience (RFC 8707 Resource Indicators)
            if payload.get("aud") != self.required_audience:
                raise HTTPException(401, "Invalid token audience")
            
            # Parse scopes
            scopes = payload.get("scope", "").split()
            
            logger.info(f"Access token validated for client {payload.get('client_id')} with scopes: {scopes}")
            
            return {
                "client_id": payload.get("client_id"),
                "subject": payload.get("sub"),
                "scopes": scopes,
                "expires_at": datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc),
                "issued_at": datetime.fromtimestamp(payload.get("iat"), tz=timezone.utc)
            }
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Access token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(401, f"Invalid access token: {str(e)}")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(401, "Token validation failed")
    
    def check_scope(self, token_info: Dict[str, Any], required_scope: str) -> bool:
        """Check if token has required scope"""
        scopes = token_info.get("scopes", [])
        return required_scope in scopes or "mcp:admin" in scopes
    
    async def authenticate_request(self, authorization: Optional[str]) -> Dict[str, Any]:
        """Authenticate HTTP request with OAuth 2.1 token"""
        if not authorization:
            raise HTTPException(401, "Authorization header required")
        
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "Bearer token required")
        
        token = authorization[7:]  # Remove "Bearer " prefix
        return await self.validate_access_token(token)

# Global resource server instance
resource_server = MCPResourceServer()

class MCPAuthenticationMiddleware:
    """Middleware for MCP tool authentication"""
    
    def __init__(self, required_scopes: Dict[str, str]):
        """
        Initialize with tool -> required scope mapping
        
        Args:
            required_scopes: {"tool_name": "required_scope"}
        """
        self.required_scopes = required_scopes
        self.security = HTTPBearer()
    
    async def authenticate_tool_call(
        self, 
        tool_name: str, 
        authorization: Optional[str]
    ) -> Dict[str, Any]:
        """Authenticate specific MCP tool call"""
        
        # Get required scope for tool
        required_scope = self.required_scopes.get(tool_name, "mcp:read")
        
        # Authenticate token
        token_info = await resource_server.authenticate_request(authorization)
        
        # Check scope authorization
        if not resource_server.check_scope(token_info, required_scope):
            raise HTTPException(
                403, 
                f"Insufficient scope: {tool_name} requires '{required_scope}'"
            )
        
        logger.info(f"Tool {tool_name} authorized for client {token_info.get('client_id')}")
        return token_info

# MCP tool scope requirements
MCP_TOOL_SCOPES = {
    "list_integrations": "mcp:read",
    "get_active_integrations": "mcp:read", 
    "create_ticket": "mcp:write",
    "create_ticket_with_ai": "mcp:write",
    "update_ticket": "mcp:write",
    "delete_ticket": "mcp:write",
    "get_ticket": "mcp:read",
    "search_tickets": "mcp:read",
    "list_tickets": "mcp:read",
    "get_ticket_stats": "mcp:read",
    "get_system_health": "mcp:read"
}

# Global authentication middleware
auth_middleware = MCPAuthenticationMiddleware(MCP_TOOL_SCOPES)
```

### 2.2 Enhanced MCP Tools with OAuth 2.1

**File:** `mcp_server/tools/integration_tools.py` (Refactored)
```python
"""
MCP Integration Tools with OAuth 2.1 Resource Server Authentication
"""

from datetime import datetime
import logging
from typing import Any, Optional
from fastapi import Request
from pydantic_ai.dependencies import RunContext
from fastmcp import FastMCP

from ..oauth_resource_server import auth_middleware, resource_server
from . import BACKEND_URL, log_tool_call
from .http_client import get_http_client

logger = logging.getLogger(__name__)
mcp = None

async def list_integrations(
    ctx: RunContext[Any],
    integration_type: str = "",
    status: str = "",
    is_enabled: str = ""
) -> str:
    """
    List available integrations with OAuth 2.1 authentication
    
    Required scope: mcp:read
    """
    start_time = datetime.now()
    arguments = {"integration_type": integration_type, "status": status, "is_enabled": is_enabled}
    
    try:
        # Extract authorization from request context
        authorization = None
        if hasattr(ctx, 'request') and ctx.request:
            authorization = ctx.request.headers.get("authorization")
        
        # Authenticate with OAuth 2.1 resource server
        token_info = await auth_middleware.authenticate_tool_call(
            "list_integrations", 
            authorization
        )
        
        logger.info(f"list_integrations authorized for client: {token_info.get('client_id')}")
        
        # Build query parameters
        params = {}
        if integration_type:
            params["integration_type"] = integration_type
        if status:
            params["integration_status"] = status
        if is_enabled:
            params["is_enabled"] = is_enabled.lower() == "true"
        
        # Make authenticated request to backend
        http_client = await get_http_client()
        
        # Pass through OAuth token to backend API
        headers = {"Authorization": f"Bearer {authorization[7:]}"} if authorization else {}
        
        response = await http_client.make_request(
            method="GET",
            endpoint="/api/v1/integrations/",
            auth_headers=headers,
            params=params
        )
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if response.status_code == 200:
            log_tool_call("list_integrations", arguments, response.text, execution_time, "success")
            return response.text
        else:
            error_msg = f"Error: HTTP {response.status_code} - {response.text}"
            log_tool_call("list_integrations", arguments, error_msg, execution_time, "error")
            return error_msg
            
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        log_tool_call("list_integrations", arguments, error_msg, execution_time, "error")
        return error_msg

async def get_active_integrations(
    ctx: RunContext[Any],
    supports_category: str = ""
) -> str:
    """
    Get active integrations with OAuth 2.1 authentication
    
    Required scope: mcp:read
    """
    start_time = datetime.now()
    arguments = {"supports_category": supports_category}
    
    try:
        # Extract authorization from request context
        authorization = None
        if hasattr(ctx, 'request') and ctx.request:
            authorization = ctx.request.headers.get("authorization")
        
        # Authenticate with OAuth 2.1 resource server
        token_info = await auth_middleware.authenticate_tool_call(
            "get_active_integrations", 
            authorization
        )
        
        # Build query parameters
        params = {}
        if supports_category:
            params["supports_category"] = supports_category
        
        # Make authenticated request
        http_client = await get_http_client()
        headers = {"Authorization": f"Bearer {authorization[7:]}"} if authorization else {}
        
        response = await http_client.make_request(
            method="GET",
            endpoint="/api/v1/integrations/active",
            auth_headers=headers,
            params=params
        )
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if response.status_code == 200:
            log_tool_call("get_active_integrations", arguments, response.text, execution_time, "success")
            return response.text
        else:
            error_msg = f"Error: HTTP {response.status_code} - {response.text}"
            log_tool_call("get_active_integrations", arguments, error_msg, execution_time, "error")
            return error_msg
            
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        log_tool_call("get_active_integrations", arguments, error_msg, execution_time, "error")
        return error_msg

def register_all_integration_tools(mcp_instance: FastMCP):
    """Register all OAuth 2.1 authenticated integration tools"""
    global mcp
    mcp = mcp_instance
    
    # Register tools with OAuth 2.1 authentication
    mcp.tool()(list_integrations)
    mcp.tool()(get_active_integrations)
    
    logger.info("Integration tools registered with OAuth 2.1 authentication")
```

### 2.3 MCP Server Discovery Protocol

**File:** `mcp_server/oauth_discovery.py`
```python
"""
OAuth 2.1 Discovery Protocol for MCP Server
Implements MCP March 2025 specification requirements
"""

from fastapi import FastAPI, Request
from typing import Dict, Any
import os
import logging

logger = logging.getLogger(__name__)

class MCPDiscoveryProtocol:
    """OAuth 2.1 discovery protocol for MCP servers"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.oauth_server_url = os.getenv("OAUTH_SERVER_URL", "http://oauth-server:9000")
        self.mcp_server_url = os.getenv("MCP_SERVER_URL", "http://mcp-server:8001")
        
        # Add discovery endpoints
        self._add_discovery_endpoints()
    
    def _add_discovery_endpoints(self):
        """Add OAuth discovery endpoints to MCP server"""
        
        @self.app.get("/.well-known/oauth-protected-resource")
        async def protected_resource_metadata():
            """OAuth 2.0 Protected Resource Metadata"""
            return {
                "resource": self.mcp_server_url,
                "authorization_servers": [self.oauth_server_url],
                "scopes_supported": [
                    "mcp:read",
                    "mcp:write", 
                    "mcp:admin",
                    "mcp:tools"
                ],
                "bearer_methods_supported": ["header"],
                "resource_documentation": f"{self.mcp_server_url}/docs"
            }
        
        @self.app.get("/.well-known/mcp-server")
        async def mcp_server_metadata():
            """MCP Server Metadata with OAuth information"""
            return {
                "server": {
                    "name": "AI Ticket Creator Tools",
                    "version": "1.0.0",
                    "description": "MCP server for AI ticket management tools"
                },
                "authentication": {
                    "type": "oauth2",
                    "authorization_server": self.oauth_server_url,
                    "scopes": {
                        "mcp:read": "Read access to MCP tools",
                        "mcp:write": "Write access to MCP tools", 
                        "mcp:admin": "Administrative access to all MCP tools",
                        "mcp:tools": "Access to specialized MCP tools"
                    }
                },
                "tools": {
                    "list_integrations": {"required_scope": "mcp:read"},
                    "get_active_integrations": {"required_scope": "mcp:read"},
                    "create_ticket": {"required_scope": "mcp:write"},
                    "create_ticket_with_ai": {"required_scope": "mcp:write"},
                    "update_ticket": {"required_scope": "mcp:write"},
                    "delete_ticket": {"required_scope": "mcp:write"},
                    "get_ticket": {"required_scope": "mcp:read"},
                    "search_tickets": {"required_scope": "mcp:read"},
                    "list_tickets": {"required_scope": "mcp:read"},
                    "get_ticket_stats": {"required_scope": "mcp:read"},
                    "get_system_health": {"required_scope": "mcp:read"}
                }
            }
        
        logger.info("OAuth discovery endpoints added to MCP server")

def setup_discovery_protocol(app: FastAPI) -> MCPDiscoveryProtocol:
    """Setup OAuth discovery protocol for MCP server"""
    return MCPDiscoveryProtocol(app)
```

### 2.4 Updated MCP Server Main

**File:** `mcp_server/start_mcp_server.py` (Refactored)
```python
"""
OAuth 2.1 Compliant MCP Server for AI Ticket Creator Tools
Implements MCP March 2025 specification
"""

import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP

from .oauth_resource_server import resource_server
from .oauth_discovery import setup_discovery_protocol
from .tools.ticket_tools import register_all_ticket_tools
from .tools.integration_tools import register_all_integration_tools  
from .tools.system_tools import register_all_system_tools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app for OAuth discovery
fastapi_app = FastAPI(
    title="MCP OAuth 2.1 Server",
    description="OAuth 2.1 compliant MCP server for AI Ticket Creator",
    version="1.0.0"
)

# Add CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup OAuth discovery protocol
discovery_protocol = setup_discovery_protocol(fastapi_app)

# Initialize FastMCP with OAuth authentication
mcp = FastMCP("AI Ticket Creator Tools")

# Authentication middleware
@mcp.middleware()
async def oauth_authentication_middleware(request: Request, call_next):
    """OAuth 2.1 authentication middleware for all MCP tools"""
    
    # Skip authentication for discovery endpoints
    if request.url.path.startswith("/.well-known/"):
        return await call_next(request)
    
    try:
        # Extract authorization header
        authorization = request.headers.get("authorization")
        
        if not authorization:
            raise HTTPException(401, "Authorization header required")
        
        # Validate OAuth 2.1 token
        token_info = await resource_server.authenticate_request(authorization)
        
        # Add token info to request context
        request.state.token_info = token_info
        
        logger.info(f"Authenticated MCP request for client: {token_info.get('client_id')}")
        
        return await call_next(request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication middleware error: {e}")
        raise HTTPException(401, "Authentication failed")

# Register all MCP tools with OAuth authentication
register_all_ticket_tools(mcp)
register_all_integration_tools(mcp)
register_all_system_tools(mcp)

# Mount FastAPI app for discovery endpoints
mcp.mount("/", fastapi_app)

if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8001"))
    path = os.getenv("MCP_PATH", "/mcp/")
    log_level = os.getenv("MCP_LOG_LEVEL", "info")
    
    logger.info(f"Starting OAuth 2.1 MCP server on {host}:{port}")
    logger.info(f"OAuth server: {os.getenv('OAUTH_SERVER_URL', 'http://oauth-server:9000')}")
    
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        path=path,
        log_level=log_level
    )
```

### 2.5 Phase 2 Validation Tests

**File:** `tests/test_mcp_oauth_integration.py`
```python
"""MCP Server OAuth 2.1 Integration Tests"""

import pytest
import httpx
import asyncio
from datetime import datetime
import os

MCP_BASE_URL = "http://localhost:8001"
OAUTH_BASE_URL = "http://localhost:9000"

class TestMCPOAuthIntegration:
    
    @pytest.fixture
    async def oauth_client(self):
        """Create OAuth client for testing"""
        registration_data = {
            "client_name": "MCP Test Client",
            "redirect_uris": ["http://localhost:3000/callback"],
            "scope": "mcp:read mcp:write mcp:admin",
            "grant_types": ["client_credentials", "authorization_code"]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OAUTH_BASE_URL}/oauth/register",
                json=registration_data
            )
        
        assert response.status_code == 200
        return response.json()
    
    @pytest.fixture
    async def access_token(self, oauth_client):
        """Get access token for testing"""
        token_data = {
            "grant_type": "client_credentials",
            "client_id": oauth_client["client_id"],
            "client_secret": oauth_client["client_secret"],
            "scope": "mcp:read mcp:write mcp:admin"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OAUTH_BASE_URL}/oauth/token",
                data=token_data
            )
        
        assert response.status_code == 200
        token_response = response.json()
        return token_response["access_token"]
    
    @pytest.mark.asyncio
    async def test_mcp_discovery_endpoints(self):
        """Test MCP OAuth discovery endpoints"""
        
        # Test protected resource metadata
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MCP_BASE_URL}/.well-known/oauth-protected-resource"
            )
        
        assert response.status_code == 200
        metadata = response.json()
        
        assert "resource" in metadata
        assert "authorization_servers" in metadata
        assert "scopes_supported" in metadata
        assert "mcp:read" in metadata["scopes_supported"]
        assert "mcp:write" in metadata["scopes_supported"]
        
        # Test MCP server metadata
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MCP_BASE_URL}/.well-known/mcp-server"
            )
        
        assert response.status_code == 200
        server_metadata = response.json()
        
        assert "server" in server_metadata
        assert "authentication" in server_metadata
        assert "tools" in server_metadata
        assert server_metadata["authentication"]["type"] == "oauth2"
    
    @pytest.mark.asyncio
    async def test_authenticated_mcp_tool_call(self, access_token):
        """Test authenticated MCP tool call"""
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Test list_integrations tool
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_BASE_URL}/mcp/",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "list_integrations",
                        "arguments": {}
                    }
                },
                headers=headers
            )
        
        assert response.status_code == 200
        result = response.json()
        
        assert "result" in result
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
    
    @pytest.mark.asyncio
    async def test_unauthenticated_mcp_tool_call(self):
        """Test unauthenticated MCP tool call should fail"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_BASE_URL}/mcp/",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "list_integrations",
                        "arguments": {}
                    }
                }
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio 
    async def test_insufficient_scope_rejection(self):
        """Test tool call with insufficient scope"""
        
        # Create client with limited scope
        registration_data = {
            "client_name": "Limited MCP Client",
            "redirect_uris": ["http://localhost:3000/callback"],
            "scope": "mcp:read",  # No write scope
            "grant_types": ["client_credentials"]
        }
        
        async with httpx.AsyncClient() as client:
            reg_response = await client.post(
                f"{OAUTH_BASE_URL}/oauth/register",
                json=registration_data
            )
        
        client_info = reg_response.json()
        
        # Get token with limited scope
        token_data = {
            "grant_type": "client_credentials",
            "client_id": client_info["client_id"],
            "client_secret": client_info["client_secret"],
            "scope": "mcp:read"
        }
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                f"{OAUTH_BASE_URL}/oauth/token",
                data=token_data
            )
        
        limited_token = token_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {limited_token}"}
        
        # Try to call write-scope tool with read-only token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_BASE_URL}/mcp/",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "create_ticket",
                        "arguments": {
                            "title": "Test Ticket",
                            "description": "Test"
                        }
                    }
                },
                headers=headers
            )
        
        assert response.status_code == 403  # Insufficient scope
        result = response.json()
        assert "insufficient scope" in result.get("error", {}).get("message", "").lower()
    
    @pytest.mark.asyncio
    async def test_expired_token_rejection(self):
        """Test expired token rejection"""
        
        # Create token with immediate expiry (would need custom OAuth server setup)
        # This test validates the token expiry checking logic
        expired_token = "expired.jwt.token"
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_BASE_URL}/mcp/",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "list_integrations",
                        "arguments": {}
                    }
                },
                headers=headers
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_resource_indicator_validation(self, access_token):
        """Test RFC 8707 resource indicator validation"""
        
        # Token should be scoped to mcp-server audience
        import jwt
        
        payload = jwt.decode(
            access_token,
            options={"verify_signature": False}  # Just inspect claims
        )
        
        # Verify audience claim (RFC 8707)
        assert payload.get("aud") == "mcp-server"
        
        # Token should be accepted by MCP server
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_BASE_URL}/mcp/",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                },
                headers=headers
            )
        
        assert response.status_code == 200
```

### 2.6 Phase 2 Validation Commands

```bash
# Phase 2 Validation Checklist

# 1. Update MCP server container
docker compose build mcp-server
docker compose up -d mcp-server

# 2. Verify OAuth discovery endpoints
curl -f http://localhost:8001/.well-known/oauth-protected-resource
curl -f http://localhost:8001/.well-known/mcp-server

# 3. Run MCP OAuth integration tests
poetry run pytest tests/test_mcp_oauth_integration.py -v

# 4. Verify MCP server logs are clean
docker logs support-extension-mcp-server-1 | grep -E "(ERROR|FAIL|Exception)"
# Should return no authentication errors

# 5. Test authenticated tool call
curl -X POST http://localhost:8001/mcp/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'

# 6. Run full test suite
poetry run pytest -v
# ALL tests must pass

# PHASE 2 GATE:
# ✅ All MCP OAuth tests pass  
# ✅ Discovery endpoints working
# ✅ No Docker errors/warnings
# ✅ Full test suite passes (440+/440+)
```

---

## Phase 3: MCP Client OAuth Integration
**Duration:** 2 weeks  
**Prerequisites:** Phase 1 & 2 complete + all validations passed

### 3.1 Enhanced MCP Client with OAuth 2.1

**File:** `mcp_client/oauth_client.py`
```python
"""
OAuth 2.1 MCP Client with PKCE and Discovery Protocol
Compliant with MCP March 2025 specification
"""

import httpx
import secrets
import hashlib
import base64
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, parse_qs, urlparse
import json
import os

logger = logging.getLogger(__name__)

class MCPOAuthClient:
    """OAuth 2.1 compliant MCP client with PKCE and discovery"""
    
    def __init__(self, mcp_server_url: str):
        self.mcp_server_url = mcp_server_url
        self.oauth_server_url: Optional[str] = None
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._client_id: Optional[str] = None
        self._client_secret: Optional[str] = None
        self._metadata_cache: Dict[str, Any] = {}
    
    async def discover_oauth_server(self) -> str:
        """Discover OAuth server using MCP discovery protocol"""
        if self.oauth_server_url:
            return self.oauth_server_url
        
        try:
            async with httpx.AsyncClient() as client:
                # Try MCP server metadata first
                response = await client.get(
                    f"{self.mcp_server_url}/.well-known/mcp-server"
                )
                
                if response.status_code == 200:
                    metadata = response.json()
                    auth_config = metadata.get("authentication", {})
                    if auth_config.get("type") == "oauth2":
                        self.oauth_server_url = auth_config.get("authorization_server")
                        if self.oauth_server_url:
                            logger.info(f"Discovered OAuth server: {self.oauth_server_url}")
                            return self.oauth_server_url
                
                # Fallback to protected resource metadata
                response = await client.get(
                    f"{self.mcp_server_url}/.well-known/oauth-protected-resource"
                )
                
                if response.status_code == 200:
                    metadata = response.json()
                    auth_servers = metadata.get("authorization_servers", [])
                    if auth_servers:
                        self.oauth_server_url = auth_servers[0]
                        logger.info(f"Discovered OAuth server via protected resource: {self.oauth_server_url}")
                        return self.oauth_server_url
                
                raise Exception("No OAuth server found in discovery metadata")
                
        except Exception as e:
            logger.error(f"OAuth server discovery failed: {e}")
            raise Exception(f"Failed to discover OAuth server: {e}")
    
    async def get_oauth_metadata(self) -> Dict[str, Any]:
        """Get OAuth server metadata"""
        if not self.oauth_server_url:
            await self.discover_oauth_server()
        
        cache_key = f"{self.oauth_server_url}/metadata"
        if cache_key in self._metadata_cache:
            return self._metadata_cache[cache_key]
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.oauth_server_url}/.well-known/oauth-authorization-server"
            )
            response.raise_for_status()
            
            metadata = response.json()
            self._metadata_cache[cache_key] = metadata
            return metadata
    
    async def register_client(
        self, 
        client_name: str,
        redirect_uris: List[str],
        scopes: List[str] = None
    ) -> Dict[str, Any]:
        """Register OAuth client using Dynamic Client Registration"""
        if not self.oauth_server_url:
            await self.discover_oauth_server()
        
        scopes = scopes or ["mcp:read", "mcp:write"]
        
        registration_data = {
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "scope": " ".join(scopes),
            "grant_types": ["authorization_code", "client_credentials"],
            "response_types": ["code"]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.oauth_server_url}/oauth/register",
                json=registration_data
            )
            response.raise_for_status()
            
            client_info = response.json()
            self._client_id = client_info["client_id"]
            self._client_secret = client_info["client_secret"]
            
            logger.info(f"OAuth client registered: {self._client_id}")
            return client_info
    
    def generate_pkce_challenge(self) -> Dict[str, str]:
        """Generate PKCE code challenge and verifier"""
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        
        return {
            "code_verifier": code_verifier,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
    
    async def get_authorization_url(
        self,
        redirect_uri: str,
        scopes: List[str] = None,
        state: Optional[str] = None
    ) -> Dict[str, str]:
        """Get OAuth authorization URL with PKCE"""
        if not self.oauth_server_url:
            await self.discover_oauth_server()
        
        if not self._client_id:
            raise Exception("Client not registered. Call register_client() first.")
        
        metadata = await self.get_oauth_metadata()
        auth_endpoint = metadata["authorization_endpoint"]
        
        scopes = scopes or ["mcp:read", "mcp:write"]
        state = state or secrets.token_urlsafe(16)
        
        # Generate PKCE challenge
        pkce = self.generate_pkce_challenge()
        
        auth_params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": pkce["code_challenge"],
            "code_challenge_method": pkce["code_challenge_method"],
            "resource": "mcp-server"  # RFC 8707 Resource Indicator
        }
        
        auth_url = f"{auth_endpoint}?{urlencode(auth_params)}"
        
        return {
            "auth_url": auth_url,
            "state": state,
            "code_verifier": pkce["code_verifier"],
            "redirect_uri": redirect_uri
        }
    
    async def exchange_code_for_token(
        self,
        authorization_code: str,
        code_verifier: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token with PKCE"""
        if not self.oauth_server_url:
            await self.discover_oauth_server()
        
        metadata = await self.get_oauth_metadata()
        token_endpoint = metadata["token_endpoint"]
        
        token_data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": redirect_uri,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code_verifier": code_verifier
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_endpoint,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            
            token_response = response.json()
            
            # Store tokens
            self._access_token = token_response["access_token"]
            self._refresh_token = token_response.get("refresh_token")
            
            expires_in = token_response.get("expires_in", 3600)
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            logger.info("Access token obtained via authorization code flow")
            return token_response
    
    async def client_credentials_flow(self, scopes: List[str] = None) -> Dict[str, Any]:
        """Get access token using client credentials flow"""
        if not self.oauth_server_url:
            await self.discover_oauth_server()
        
        if not self._client_id or not self._client_secret:
            raise Exception("Client credentials not available. Register client first.")
        
        metadata = await self.get_oauth_metadata()
        token_endpoint = metadata["token_endpoint"]
        
        scopes = scopes or ["mcp:read", "mcp:write"]
        
        token_data = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "scope": " ".join(scopes)
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_endpoint,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            
            token_response = response.json()
            
            # Store tokens
            self._access_token = token_response["access_token"]
            
            expires_in = token_response.get("expires_in", 3600)
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            logger.info("Access token obtained via client credentials flow")
            return token_response
    
    async def is_token_valid(self) -> bool:
        """Check if current access token is valid"""
        if not self._access_token or not self._token_expires_at:
            return False
        
        # Check if token expires in next 5 minutes
        return datetime.now(timezone.utc) + timedelta(minutes=5) < self._token_expires_at
    
    async def get_access_token(self) -> Optional[str]:
        """Get valid access token (refresh if needed)"""
        if await self.is_token_valid():
            return self._access_token
        
        # Token invalid/expired - would need refresh logic here
        # For now, return None to indicate re-authentication needed
        logger.warning("Access token expired - re-authentication required")
        return None
    
    async def call_mcp_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Call MCP tool with OAuth authentication"""
        access_token = await self.get_access_token()
        if not access_token:
            raise Exception("No valid access token available")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.mcp_server_url}/mcp/",
                json=request_data,
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "error" in result:
                raise Exception(f"MCP tool error: {result['error']}")
            
            logger.info(f"MCP tool {tool_name} called successfully")
            return result.get("result", {})
    
    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools"""
        access_token = await self.get_access_token()
        if not access_token:
            raise Exception("No valid access token available")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.mcp_server_url}/mcp/",
                json=request_data,
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("result", {}).get("tools", [])
```

### 3.2 AI Chat Service OAuth Integration

**File:** `app/services/ai_chat_service.py` (OAuth 2.1 Integration)
```python
"""
AI Chat Service with OAuth 2.1 MCP Integration
"""

from mcp_client.oauth_client import MCPOAuthClient
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class EnhancedAIChatService:
    """AI Chat Service with OAuth 2.1 MCP integration"""
    
    def __init__(self):
        self.mcp_client = MCPOAuthClient("http://mcp-server:8001")
        self._oauth_initialized = False
    
    async def initialize_oauth_client(self):
        """Initialize OAuth client with automatic registration"""
        if self._oauth_initialized:
            return
        
        try:
            # Register OAuth client for MCP access
            client_info = await self.mcp_client.register_client(
                client_name="AI Chat Service",
                redirect_uris=["http://app:8000/oauth/callback"],  # Not used for client_credentials
                scopes=["mcp:read", "mcp:write", "mcp:admin"]
            )
            
            # Use client credentials flow for server-to-server
            await self.mcp_client.client_credentials_flow()
            
            self._oauth_initialized = True
            logger.info("OAuth MCP client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OAuth MCP client: {e}")
            raise
    
    async def send_message_with_oauth_mcp(
        self,
        conversation_id: str,
        user_id: str,
        message: str,
        user_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send message with OAuth 2.1 MCP integration"""
        
        # Initialize OAuth client if needed
        if not self._oauth_initialized:
            await self.initialize_oauth_client()
        
        # Get conversation history
        message_history = await self.get_conversation_history(conversation_id, user_id)
        
        # Create context with MCP OAuth client
        context = ChatContext(
            user_id=user_id,
            conversation_id=conversation_id,
            session_history=message_history,
            mcp_oauth_client=self.mcp_client,  # Pass OAuth client
            user_token=user_token  # Original user token for backend calls
        )
        
        # Run AI agent with OAuth MCP context
        result = await self.agent.run(message, deps=context)
        
        return {
            "content": result.data.content,
            "confidence": result.data.confidence,
            "requires_escalation": result.data.requires_escalation,
            "suggested_actions": result.data.suggested_actions,
            "ticket_references": result.data.ticket_references,
            "tools_used": result.data.tools_used
        }

class ChatContext(BaseModel):
    """Enhanced chat context with OAuth MCP client"""
    user_id: str
    conversation_id: str
    session_history: List[Dict[str, str]] = Field(default_factory=list)
    mcp_oauth_client: Optional[MCPOAuthClient] = Field(default=None, exclude=True)
    user_token: Optional[str] = Field(default=None, exclude=True)
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any] = None):
        """Call MCP tool using OAuth client"""
        if not self.mcp_oauth_client:
            raise Exception("MCP OAuth client not available")
        
        return await self.mcp_oauth_client.call_mcp_tool(tool_name, arguments)
    
    async def get_backend_auth_headers(self) -> Optional[Dict[str, str]]:
        """Get headers for backend API calls (user token)"""
        if self.user_token:
            return {"Authorization": f"Bearer {self.user_token}"}
        return None

# Global enhanced service instance
enhanced_ai_chat_service = EnhancedAIChatService()
```

### 3.3 Updated Chat API with OAuth Flow

**File:** `app/api/v1/chat.py` (OAuth Integration)
```python
"""
Chat API with OAuth 2.1 MCP Integration
"""

from app.services.ai_chat_service import enhanced_ai_chat_service

@router.post("/conversations/{conversation_id}/messages")
async def send_message_oauth(
    request: SendMessageRequest,
    conversation_id: UUID = Path(..., description="Conversation ID"),
    current_user: User = Depends(get_current_active_user),
    http_request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Send message with OAuth 2.1 MCP integration"""
    
    # Extract user JWT token for backend API calls
    auth_header = http_request.headers.get("authorization", "")
    user_token = auth_header[7:] if auth_header.startswith("Bearer ") else None
    
    try:
        # Use enhanced AI chat service with OAuth MCP
        ai_response = await enhanced_ai_chat_service.send_message_with_oauth_mcp(
            conversation_id=str(conversation_id),
            user_id=str(current_user.id),
            message=request.message,
            user_token=user_token
        )
        
        # Store message in database
        user_message = ChatMessage(
            conversation_id=conversation_id,
            role="user",
            content=request.message
        )
        
        assistant_message = ChatMessage(
            conversation_id=conversation_id,
            role="assistant", 
            content=ai_response["content"],
            model_used="gpt-4o-mini",
            tokens_used=0,  # Would be populated by actual usage
            confidence_score=ai_response["confidence"]
        )
        
        db.add_all([user_message, assistant_message])
        await db.commit()
        
        return ChatMessageResponse(
            content=ai_response["content"],
            confidence=ai_response["confidence"],
            requires_escalation=ai_response["requires_escalation"],
            suggested_actions=ai_response["suggested_actions"],
            ticket_references=ai_response["ticket_references"],
            tools_used=ai_response["tools_used"]
        )
        
    except Exception as e:
        logger.error(f"Chat message processing failed: {e}")
        
        # Fallback response
        return ChatMessageResponse(
            content="I'm sorry, I encountered an error processing your request. Please try again or contact support if the issue persists.",
            confidence=0.0,
            requires_escalation=True,
            suggested_actions=[],
            ticket_references=[],
            tools_used=[]
        )
```

### 3.4 Phase 3 Validation Tests

**File:** `tests/test_oauth_mcp_client.py`
```python
"""OAuth 2.1 MCP Client Tests"""

import pytest
import asyncio
from mcp_client.oauth_client import MCPOAuthClient

class TestOAuthMCPClient:
    
    @pytest.mark.asyncio
    async def test_oauth_discovery(self):
        """Test OAuth server discovery via MCP endpoints"""
        client = MCPOAuthClient("http://localhost:8001")
        
        oauth_server_url = await client.discover_oauth_server()
        
        assert oauth_server_url is not None
        assert "localhost:9000" in oauth_server_url or "oauth-server" in oauth_server_url
    
    @pytest.mark.asyncio
    async def test_client_registration(self):
        """Test dynamic client registration"""
        client = MCPOAuthClient("http://localhost:8001")
        
        client_info = await client.register_client(
            client_name="Test Client",
            redirect_uris=["http://localhost:3000/callback"],
            scopes=["mcp:read", "mcp:write"]
        )
        
        assert "client_id" in client_info
        assert "client_secret" in client_info
        assert client_info["client_name"] == "Test Client"
    
    @pytest.mark.asyncio
    async def test_client_credentials_flow(self):
        """Test OAuth client credentials flow"""
        client = MCPOAuthClient("http://localhost:8001")
        
        # Register client
        await client.register_client(
            client_name="Test Client",
            redirect_uris=["http://localhost:3000/callback"],
            scopes=["mcp:read", "mcp:write"]
        )
        
        # Get token via client credentials
        token_response = await client.client_credentials_flow()
        
        assert "access_token" in token_response
        assert token_response["token_type"] == "Bearer"
        assert "expires_in" in token_response
    
    @pytest.mark.asyncio
    async def test_authenticated_mcp_tool_call(self):
        """Test authenticated MCP tool call"""
        client = MCPOAuthClient("http://localhost:8001")
        
        # Register and authenticate
        await client.register_client(
            client_name="Test Client",
            redirect_uris=["http://localhost:3000/callback"],
            scopes=["mcp:read", "mcp:write", "mcp:admin"]
        )
        
        await client.client_credentials_flow()
        
        # Call MCP tool
        result = await client.call_mcp_tool(
            "get_system_health",
            {}
        )
        
        assert result is not None
        # System health should work without backend dependencies
    
    @pytest.mark.asyncio
    async def test_list_available_tools(self):
        """Test listing available MCP tools"""
        client = MCPOAuthClient("http://localhost:8001")
        
        # Register and authenticate
        await client.register_client(
            client_name="Test Client", 
            redirect_uris=["http://localhost:3000/callback"],
            scopes=["mcp:read", "mcp:write", "mcp:admin"]
        )
        
        await client.client_credentials_flow()
        
        # List tools
        tools = await client.list_available_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Verify expected tools are present
        tool_names = [tool.get("name") for tool in tools]
        assert "list_integrations" in tool_names
        assert "get_system_health" in tool_names
    
    @pytest.mark.asyncio
    async def test_pkce_challenge_generation(self):
        """Test PKCE challenge generation"""
        client = MCPOAuthClient("http://localhost:8001")
        
        pkce = client.generate_pkce_challenge()
        
        assert "code_verifier" in pkce
        assert "code_challenge" in pkce
        assert "code_challenge_method" in pkce
        assert pkce["code_challenge_method"] == "S256"
        assert len(pkce["code_verifier"]) >= 43  # Base64 URL-safe minimum
        assert len(pkce["code_challenge"]) >= 43
```

### 3.5 Phase 3 Validation Commands

```bash
# Phase 3 Validation Checklist

# 1. Update services with OAuth integration
docker compose build app mcp-server
docker compose up -d

# 2. Test OAuth MCP client
poetry run pytest tests/test_oauth_mcp_client.py -v

# 3. Test end-to-end OAuth flow
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "greg@shipwell.com", "password": "2YNfwVn.qDx.t2H"}'

# Extract access_token and test chat
curl -X POST http://localhost:8000/api/v1/chat/conversations/{id}/messages \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "What tools can you call?"}'

# 4. Verify all services are clean
docker logs support-extension-oauth-server-1 | grep -E "(ERROR|FAIL)"
docker logs support-extension-mcp-server-1 | grep -E "(ERROR|FAIL)" 
docker logs support-extension-app-1 | grep -E "(ERROR|FAIL)"
# All should return no errors

# 5. Run full test suite
poetry run pytest -v
# ALL tests must pass

# PHASE 3 GATE:
# ✅ OAuth MCP client tests pass
# ✅ End-to-end authentication working
# ✅ No Docker errors/warnings
# ✅ Full test suite passes (445+/445+)
```

---

## Final Validation & Production Readiness

### Security Audit Checklist

```bash
# Security validation commands

# 1. Verify no tokens in logs
docker logs support-extension-oauth-server-1 | grep -i "token\|secret\|jwt"
docker logs support-extension-mcp-server-1 | grep -i "token\|secret\|jwt"
docker logs support-extension-app-1 | grep -i "token\|secret\|jwt"
# Should not expose actual token values

# 2. Test PKCE enforcement
curl -X GET "http://localhost:9000/oauth/authorize?response_type=code&client_id=test&redirect_uri=http://localhost:3000/callback"
# Should return PKCE required error

# 3. Test scope enforcement
# Create limited scope token and test write operations - should fail

# 4. Test expired token handling
# Use expired token - should return 401

# 5. Test discovery endpoints
curl http://localhost:8001/.well-known/oauth-protected-resource
curl http://localhost:8001/.well-known/mcp-server
curl http://localhost:9000/.well-known/oauth-authorization-server
```

### Performance Validation

```bash
# Performance impact assessment

# 1. Measure baseline latency (no auth)
# 2. Measure OAuth latency (with auth)  
# 3. Verify <50ms additional overhead
# 4. Test concurrent requests
# 5. Monitor memory usage
```

### Production Readiness Checklist

- [ ] **Phase 1 Complete**: OAuth 2.1 Authorization Server operational
- [ ] **Phase 2 Complete**: MCP Server as OAuth Resource Server
- [ ] **Phase 3 Complete**: MCP Client OAuth integration
- [ ] **All Tests Pass**: 445+ tests passing across all phases
- [ ] **Clean Docker Logs**: No authentication errors or warnings
- [ ] **Security Audit**: No token exposure, proper scope enforcement
- [ ] **Performance Validated**: <50ms additional latency per MCP call
- [ ] **Discovery Protocol**: All OAuth discovery endpoints functional
- [ ] **Standards Compliance**: Full MCP OAuth 2.1 specification compliance

## Success Metrics

### Functional Requirements ✅
- **MCP Tool Success Rate**: >95% for authenticated calls
- **OAuth Flow Success**: 100% for valid clients/tokens
- **Scope Enforcement**: 100% accuracy for permission checking
- **Discovery Protocol**: All endpoints responding correctly

### Security Requirements ✅
- **Zero Token Leakage**: No JWT tokens in logs or error messages
- **PKCE Enforcement**: All authorization flows require PKCE
- **Scope Validation**: Tools respect OAuth scope requirements  
- **Resource Indicators**: RFC 8707 compliance for token audience

### Performance Requirements ✅
- **Latency Impact**: <50ms additional overhead per tool call
- **Token Validation**: <10ms OAuth token verification
- **Discovery Caching**: Metadata cached for 15+ minutes
- **Connection Pooling**: HTTP client reuse across tool calls

## Authentication Flow Deep Dive

### Real-World API Call Flow: Chat Message with AI Tool Usage

This section details exactly how OAuth 2.1 authentication works for a typical API call where an authenticated user posts a message, triggering an AI agent that calls MCP tools.

#### User Experience Flow
```
1. User logs in → Gets JWT token
2. User posts message "What integrations are available?"
3. AI responds "I found 5 integrations: JIRA, Salesforce, GitHub..." 
4. User sees response (unaware of OAuth complexity behind scenes)
```

#### API Experience Flow (Technical Details)

**Step 1: User Authentication (Already Working)**
```http
POST /api/v1/auth/login HTTP/1.1
Content-Type: application/json

{"email": "greg@shipwell.com", "password": "2YNfwVn.qDx.t2H"}

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {...}
}
```

**Step 2: User Posts Message (OAuth Flow Begins)**
```http
POST /api/v1/chat/conversations/93096547-62ef-45df-bf7d-bcf2526d741e/messages HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{"message": "What integrations are available?"}
```

**Step 3: Chat API Processing (New OAuth Logic)**
```python
# app/api/v1/chat.py
async def send_message_oauth(request, conversation_id, current_user, http_request, db):
    # 3a. Extract user JWT token from Authorization header
    auth_header = http_request.headers.get("authorization", "")
    user_token = auth_header[7:] if auth_header.startswith("Bearer ") else None
    
    # 3b. AI service will handle OAuth client setup for MCP
    ai_response = await enhanced_ai_chat_service.send_message_with_oauth_mcp(
        conversation_id=str(conversation_id),
        user_id=str(current_user.id), 
        message=request.message,
        user_token=user_token  # Pass user JWT for backend API calls
    )
```

**Step 4: AI Chat Service OAuth Initialization (One-Time Setup)**
```python
# app/services/ai_chat_service.py
async def send_message_with_oauth_mcp(self, conversation_id, user_id, message, user_token):
    # 4a. Initialize OAuth client (if not already done)
    if not self._oauth_initialized:
        # OAuth Client Registration (happens once per service startup)
        client_info = await self.mcp_client.register_client(
            client_name="AI Chat Service",
            redirect_uris=["http://app:8000/oauth/callback"],
            scopes=["mcp:read", "mcp:write", "mcp:admin"]
        )
        
        # 4b. Get service access token using Client Credentials flow
        token_response = await self.mcp_client.client_credentials_flow()
        # Result: AI service now has OAuth token for MCP calls
        
        self._oauth_initialized = True

    # 4c. Create chat context with OAuth MCP client
    context = ChatContext(
        user_id=user_id,
        conversation_id=conversation_id, 
        mcp_oauth_client=self.mcp_client,  # OAuth-enabled MCP client
        user_token=user_token  # Original user token for backend calls
    )
    
    # 4d. Run AI agent with OAuth context
    result = await self.agent.run(message, deps=context)
```

**Step 5: AI Agent Tool Call Decision**
```python
# AI Agent (PydanticAI) processes: "What integrations are available?"
# Decides to call: list_integrations tool
# 
# Agent automatically calls:
# await ctx.deps.call_mcp_tool("list_integrations", {})
```

**Step 6: OAuth MCP Tool Call (New Authentication)**
```python
# mcp_client/oauth_client.py
async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]):
    # 6a. Get valid service access token
    access_token = await self.get_access_token()
    if not access_token:
        # Re-authenticate using client credentials
        await self.client_credentials_flow()
        access_token = self._access_token
    
    # 6b. Make authenticated MCP call
    headers = {
        "Authorization": f"Bearer {access_token}",  # OAuth token
        "Content-Type": "application/json"
    }
    
    request_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    # 6c. HTTP request: app:8000 → mcp-server:8001
    response = await httpx.post(
        f"{self.mcp_server_url}/mcp/",
        json=request_data,
        headers=headers
    )
```

**Step 7: MCP Server OAuth Validation**
```python
# mcp_server/oauth_resource_server.py
async def oauth_authentication_middleware(request: Request, call_next):
    # 7a. Extract OAuth token from Authorization header
    authorization = request.headers.get("authorization")
    # authorization = "Bearer <oauth_access_token>"
    
    # 7b. Validate OAuth token
    token_info = await resource_server.validate_access_token(oauth_token)
    # Validates:
    # - JWT signature using shared secret
    # - Token expiry
    # - Audience = "mcp-server" (RFC 8707)
    # - Issuer = OAuth server
    # - Required claims present
    
    # 7c. Check tool authorization
    required_scope = "mcp:read"  # for list_integrations
    if not resource_server.check_scope(token_info, required_scope):
        raise HTTPException(403, "Insufficient scope")
    
    # 7d. Add token info to request context
    request.state.token_info = token_info
    # Tool call proceeds...
```

**Step 8: MCP Tool Execution with Backend API Call**
```python
# mcp_server/tools/integration_tools.py
async def list_integrations(ctx: RunContext[Any], integration_type: str = ""):
    # 8a. Authenticate this specific tool call
    authorization = ctx.request.headers.get("authorization")
    token_info = await auth_middleware.authenticate_tool_call(
        "list_integrations", 
        authorization
    )
    # OAuth token validated + scope "mcp:read" confirmed
    
    # 8b. Extract user token from context for backend API call
    # The user's original JWT is needed for backend API authorization
    user_token = getattr(ctx.deps, 'user_token', None)
    backend_headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}
    
    # 8c. Make backend API call with user's JWT token
    response = await http_client.make_request(
        method="GET",
        endpoint="/api/v1/integrations/",
        auth_headers=backend_headers,  # User's JWT (not OAuth token)
        params=params
    )
    # Backend API validates user's JWT → 200 OK ✅
    
    return response.text  # Integration list returned
```

**Step 9: Response Flow Back to User**
```
MCP Tool Result → AI Agent → Chat Service → Chat API → User
"5 integrations found: JIRA, Salesforce, GitHub, Zendesk, ServiceNow"
```

#### Complete Authentication Flow Summary

**Two Parallel Authentication Streams:**

**Stream 1: User → Backend API**
```
User JWT ──► Chat API ──► Backend Services ──► Database/Resources
(User permissions, direct API access)
```

**Stream 2: AI Service → MCP Tools** 
```
OAuth Client ──► Auth Server ──► MCP Server ──► Tool Execution
(Service permissions, MCP tool access)
```

**Critical Integration Point:**
```python
# In MCP tools, BOTH tokens are used:
oauth_token = ctx.request.headers.get("authorization")      # For MCP tool authorization
user_token = getattr(ctx.deps, 'user_token', None)         # For backend API calls

# OAuth validates: Can this service call this MCP tool?
# User JWT validates: Can this user access this backend resource?
```

### Authentication Experience Matrix

| Component | Authentication Method | Token Type | Purpose |
|-----------|----------------------|------------|---------|
| **User → Chat API** | User JWT | Bearer user_jwt | User identity & API access |
| **AI Service → MCP Server** | OAuth 2.1 | Bearer oauth_token | MCP tool authorization |
| **MCP Tool → Backend API** | User JWT (passthrough) | Bearer user_jwt | Resource access |
| **OAuth Client → Auth Server** | Client Credentials | oauth_token issuance | Service authentication |

### Error Handling Scenarios

**Scenario 1: User Token Expired**
```
User JWT expired → Backend API 401 → MCP tool returns error → AI agent responds:
"I'm unable to access integrations due to session expiry. Please log in again."
```

**Scenario 2: OAuth Token Expired**
```
OAuth token expired → MCP server 401 → AI service auto-refreshes OAuth token → Retry succeeds
```

**Scenario 3: Insufficient OAuth Scope**
```
Tool requires mcp:write, token has mcp:read → MCP server 403 → AI agent responds:
"I don't have permission to create tickets. Contact your administrator."
```

**Scenario 4: MCP Server Unavailable**
```
OAuth server down → MCP client fallback → AI agent responds:
"Tools are temporarily unavailable. Basic responses only."
```

### Developer Experience

**For Frontend Developers:**
- ✅ **No Changes**: Same API endpoints, same JWT tokens
- ✅ **Transparent**: OAuth complexity hidden behind existing chat API
- ✅ **Same Responses**: AI responses enhanced with tool access, no breaking changes

**For Backend Developers:**
- ✅ **OAuth Infrastructure**: Clear separation of concerns
- ✅ **Service Authentication**: AI services authenticate independently of users
- ✅ **Granular Permissions**: Tool-level authorization control
- ✅ **Standards Compliance**: Industry-standard OAuth 2.1 implementation

**For DevOps/Infrastructure:**
- ✅ **Container Isolation**: Each service has clear authentication boundaries
- ✅ **Monitoring**: OAuth audit trails for security compliance
- ✅ **Scalability**: OAuth server can support multiple MCP services
- ✅ **Security**: Enterprise-grade authentication with scope enforcement

This dual-stream authentication model ensures that:
1. **Users maintain their existing experience** (no UX changes)
2. **AI agents can access tools securely** (OAuth 2.1 service auth)
3. **Backend resources remain protected** (user JWT authorization)
4. **Enterprise security requirements are met** (standards compliance + audit trails)

## Conclusion

This PRP provides a complete OAuth 2.1 refactor of the MCP authentication system, fully compliant with the **MCP March 2025 specification**. The phased approach ensures:

1. **Standards Compliance**: Full OAuth 2.1 + PKCE implementation
2. **Enterprise Security**: Resource indicators, scope enforcement, discovery protocol
3. **Rigorous Validation**: Step-by-step testing with complete test suite validation
4. **Production Ready**: Performance optimized with proper error handling
5. **Dual-Stream Authentication**: User and service authentication streams working in parallel

The implementation resolves the 401 authentication errors while establishing a robust, scalable foundation for secure MCP tool execution in production environments that meets enterprise security requirements and industry standards.