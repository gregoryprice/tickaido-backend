#!/usr/bin/env python3
"""
Middleware package for AI Ticket Creator Backend
"""

from .auth_middleware import (
    auth_middleware,
    get_current_user,
    get_current_user_optional,
    require_permissions,
    websocket_auth,
    WebSocketAuthMiddleware,
    AuthMiddleware,
    AuthenticationError
)

from .rate_limiting import (
    rate_limiter,
    RateLimitMiddleware,
    create_rate_limit_dependency,
    RateLimitExceeded
)

__all__ = [
    'auth_middleware',
    'get_current_user', 
    'get_current_user_optional',
    'require_permissions',
    'websocket_auth',
    'WebSocketAuthMiddleware',
    'AuthMiddleware',
    'AuthenticationError',
    'rate_limiter',
    'RateLimitMiddleware', 
    'create_rate_limit_dependency',
    'RateLimitExceeded'
]