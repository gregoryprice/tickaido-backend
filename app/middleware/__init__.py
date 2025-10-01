#!/usr/bin/env python3
"""
Middleware package for AI Ticket Creator Backend
"""

from .auth_middleware import (
    AuthenticationError,
    AuthMiddleware,
    WebSocketAuthMiddleware,
    auth_middleware,
    get_current_user,
    get_current_user_optional,
    require_permissions,
    websocket_auth,
)
from .rate_limiting import (
    RateLimitExceeded,
    RateLimitMiddleware,
    create_rate_limit_dependency,
    rate_limiter,
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