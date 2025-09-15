# Clerk Frontend Integration Instructions

## Product Requirements Document (PRD)

**Version**: 1.0  
**Date**: September 2025  
**Author**: AI Ticket Creator Team  
**Status**: Implementation Ready

---

## Executive Summary

This document outlines how frontend applications (Web Dashboard, Chrome Extension, Mobile App) should integrate with the new Clerk-based authentication system and utilize the enhanced API endpoints with the unified webhook architecture.

### Key Frontend Changes
- **Authentication Flow**: Replace custom login with Clerk-managed authentication
- **API Access**: Support both Clerk session tokens and organization-scoped API tokens
- **Organization Context**: Handle single organization membership with proper data isolation
- **Token Management**: Provide UI for users to generate and manage API tokens
- **SSO Integration**: Support Google, Microsoft, and GitHub sign-in options
- **Unified Webhook Processing**: Single Clerk webhook endpoint handles all event types

---

## Authentication Architecture

### Authentication Methods

The frontend will support two authentication methods:

#### 1. **Interactive Authentication (Web/Mobile)**
- **Purpose**: Human users accessing the dashboard, Chrome extension, or mobile app
- **Method**: Clerk session tokens
- **Flow**: Clerk-managed SSO → Session token → API calls
- **Token Format**: Clerk-generated JWT tokens
- **Lifespan**: Session-based with automatic refresh

#### 2. **Programmatic Authentication (API)**
- **Purpose**: Automated scripts, CI/CD, integrations, Chrome extension background scripts
- **Method**: Organization-scoped API tokens
- **Flow**: User generates token in dashboard → Use in API calls
- **Token Format**: `ai_{environment}_{token}` (e.g., `ai_prod_AbCdEf123456...`)
- **Lifespan**: Long-lived (30 days to 1 year)

### API Request Examples

#### **Using Clerk Session Token (Interactive)**
```javascript
// Web dashboard or mobile app
const clerkToken = await clerk.session.getToken()

const response = await fetch('/api/v1/tickets', {
  headers: {
    'Authorization': `Bearer ${clerkToken}`,
    'Content-Type': 'application/json'
  }
})
```

#### **Using API Token (Programmatic)**
```javascript
// Chrome extension background script or automation
const apiToken = 'ai_prod_AbCdEf123456789...'

const response = await fetch('/api/v1/tickets', {
  headers: {
    'Authorization': `Bearer ${apiToken}`,
    'Content-Type': 'application/json'
  }
})
```

---

## User Authentication Workflows

### 1. **Initial User Registration/Login**

#### **New User Registration**
```
User Flow:
1. User visits signup page
2. Frontend shows Clerk authentication UI
3. User selects provider (Google/Microsoft/GitHub) or email/password
4. Clerk handles authentication and verification
5. User is redirected back to application
6. Backend automatically creates user record via unified webhook
7. Frontend receives Clerk session token
8. User is logged in and can access organization features
```

### 2. **Chrome Extension Authentication**

#### **Background Script Authentication**
```javascript
// Chrome extension background.js
class ApiClient {
  constructor() {
    this.apiToken = null
    this.baseUrl = 'https://api.tickaido.com'
  }
  
  async setApiToken(token) {
    // Validate token format
    if (!token.startsWith('ai_')) {
      throw new Error('Invalid API token format')
    }
    
    this.apiToken = token
    // Store securely in extension storage
    await chrome.storage.secure.set({ apiToken: token })
  }
  
  async makeAuthenticatedRequest(endpoint, options = {}) {
    if (!this.apiToken) {
      throw new Error('API token not configured')
    }
    
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.apiToken}`,
        'Content-Type': 'application/json',
        ...options.headers
      }
    })
    
    if (response.status === 401) {
      // Token expired or invalid - notify user
      this.handleAuthenticationError()
    }
    
    return response
  }
}
```

---

## API Token Management

### Token Generation Workflow

#### **User Journey for API Token Creation**
```
Frontend Workflow:
1. User navigates to Settings → API Tokens
2. User clicks "Generate New Token"
3. Frontend shows token generation form:
   - Token name (required)
   - Permissions (defaults to user's permissions)
   - Expiration (dropdown: 30/90/365 days)
4. User submits form
5. Frontend calls token generation API
6. Backend returns token (shown only once)
7. Frontend displays token with security warnings
8. User copies token and confirms they've saved it
9. Frontend redirects to token list (token value no longer available)
```

#### **Token Generation API**
```http
POST /api/v1/api-tokens
Content-Type: application/json
Authorization: Bearer {clerk_session_token}

{
  "name": "Production Integration",
  "permissions": ["*"],
  "expires_days": 365
}
```

**Response:**
```json
{
  "token": "ai_prod_AbCdEf123456789...",
  "id": "token-uuid",
  "name": "Production Integration",
  "permissions": ["*"],
  "expires_at": "2026-09-13T16:30:00Z",
  "organization_id": "org-uuid",
  "organization_name": "Acme Corporation",
  "warning": "Save this token securely - it will not be displayed again!"
}
```

---

## API Endpoint Reference

### Authentication Endpoints

| Method | Endpoint | Purpose | Token Type |
|--------|----------|---------|------------|
| `GET` | `/api/v1/users/me` | Get current user info | Clerk Session |
| `POST` | `/api/v1/api-tokens` | Generate API token | Clerk Session |
| `GET` | `/api/v1/api-tokens` | List user's tokens | Clerk Session |
| `DELETE` | `/api/v1/api-tokens/{id}` | Revoke API token | Clerk Session |

### Organization Endpoints

| Method | Endpoint | Purpose | Token Type |
|--------|----------|---------|------------|
| `GET` | `/api/v1/organizations/{id}` | Get org details | Both |
| `GET` | `/api/v1/organizations/{id}/members` | List members | Both |
| `POST` | `/api/v1/organizations/{id}/invitations` | Invite member | Clerk Session |

### Business Endpoints

| Method | Endpoint | Purpose | Token Type |
|--------|----------|---------|------------|
| `GET` | `/api/v1/tickets` | List org tickets | Both |
| `POST` | `/api/v1/tickets` | Create ticket | Both |
| `GET` | `/api/v1/tickets/{id}` | Get ticket details | Both |
| `PUT` | `/api/v1/tickets/{id}` | Update ticket | Both |

### Webhook Endpoint (Backend Only)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/webhooks/clerk/events` | Unified webhook for all Clerk events |

**Webhook Configuration URLs**:
- **Local Development**: `http://localhost:8000/api/v1/webhooks/clerk/events`
- **Production**: `https://api.tickaido.com/api/v1/webhooks/clerk/events`

**Supported Event Types**:
- **User Events**: `user.created`, `user.updated`, `user.deleted`
- **Session Events**: `session.created`, `session.ended`
- **Organization Events**: `organization.created`, `organization.updated`, `organization.deleted`
- **Membership Events**: `organizationMembership.created`, `organizationMembership.updated`, `organizationMembership.deleted`
- **Invitation Events**: `organizationInvitation.created`, `organizationInvitation.accepted`, `organizationInvitation.revoked`

---

## Error Handling & Security

### Authentication Error Handling

#### **Common Error Scenarios**
1. **Invalid/Expired Clerk Session**
   - **Detection**: 401 response from API
   - **Frontend Action**: Redirect to Clerk login
   - **User Message**: "Your session has expired. Please sign in again."

2. **Invalid/Expired API Token**
   - **Detection**: 401 response with API token
   - **Frontend Action**: Show token configuration error
   - **User Message**: "API token is invalid or expired. Please generate a new token."

3. **Organization Access Denied**
   - **Detection**: 403 response
   - **Frontend Action**: Show access denied message
   - **User Message**: "You don't have access to this organization's data."

#### **Error Response Handling**
```javascript
const handleApiResponse = async (response) => {
  if (response.status === 401) {
    // Authentication required
    if (isUsingClerkToken) {
      await clerk.redirectToSignIn()
    } else {
      showApiTokenConfigurationError()
    }
  } else if (response.status === 403) {
    // Permission denied
    showAccessDeniedError()
  } else if (response.status === 429) {
    // Rate limited
    showRateLimitError()
  }
  
  return response
}
```

---

## Frontend Environment Configuration

### Development Environment
```javascript
// Frontend config for development
const config = {
  clerkPublishableKey: 'pk_test_...',
  apiBaseUrl: 'http://localhost:8000/api/v1',
  webhookUrl: 'http://localhost:8000/api/v1/webhooks/clerk/events',
  environment: 'development'
}

// API tokens will use ai_dev_ prefix
```

### Production Environment
```javascript
// Frontend config for production
const config = {
  clerkPublishableKey: 'pk_live_...',
  apiBaseUrl: 'https://api.tickaido.com/api/v1',
  webhookUrl: 'https://api.tickaido.com/api/v1/webhooks/clerk/events',
  environment: 'production'
}

// API tokens will use ai_prod_ prefix
```

---

## Implementation Checklist

### Phase 1: Authentication Setup

#### **Web Dashboard**
- [ ] Replace custom login forms with Clerk authentication components
- [ ] Implement Clerk session token storage and refresh
- [ ] Update all API calls to use Clerk session tokens
- [ ] Add organization context display in UI header
- [ ] Implement logout functionality with Clerk.signOut()

#### **Chrome Extension**
- [ ] Configure API token storage in extension settings
- [ ] Update background scripts to use API tokens with `ai_env_` format
- [ ] Implement token validation and error handling
- [ ] Add token configuration UI in extension options
- [ ] Test cross-origin API calls with proper headers

### Phase 2: Organization Integration

#### **Organization Context**
- [ ] Display current organization in all frontend interfaces
- [ ] Update data filtering to respect organization boundaries
- [ ] Implement organization-specific settings UI
- [ ] Add organization member management interface
- [ ] Test data isolation between organizations

### Phase 3: API Token Management

#### **Token Generation**
- [ ] Create API token generation form with environment-aware naming
- [ ] Implement one-time token display with security warnings
- [ ] Add token usage examples with correct `ai_env_` format
- [ ] Implement token name validation and uniqueness checking
- [ ] Test token generation workflow end-to-end

### Phase 4: Testing & Validation

#### **Authentication Testing**
- [ ] Test all SSO provider flows (Google, Microsoft, GitHub)
- [ ] Validate session refresh and token renewal
- [ ] Test environment-specific API token functionality
- [ ] Verify error handling for invalid tokens
- [ ] Test unified webhook event processing

---

*This document provides high-level frontend integration guidance for the Clerk authentication system with unified webhook processing.*