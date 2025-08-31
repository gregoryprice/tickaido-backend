#!/usr/bin/env python3
"""
Rate Limiting Middleware for AI Ticket Creator Backend
Implements Redis-based rate limiting with flexible policies and user-specific limits
"""

import logging
import time
import hashlib
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import HTTPException, status, Request, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import redis.asyncio as redis

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration"""
    requests: int  # Number of requests allowed
    window: int    # Time window in seconds
    burst: int = 0 # Additional burst capacity (optional)


class RateLimitExceeded(HTTPException):
    """Rate limit exceeded exception"""
    def __init__(self, detail: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)} if retry_after else None
        )


class RateLimitMiddleware:
    """Redis-based rate limiting middleware with sliding window algorithm"""
    
    def __init__(self, redis_url: str = None):
        settings = get_settings()
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis_client: Optional[redis.Redis] = None
        
        # Default rate limit rules (relaxed for development and testing)
        self.default_rules = {
            # General API requests
            "default": RateLimitRule(requests=1000, window=3600),  # 1000 requests per hour
            "auth": RateLimitRule(requests=100, window=300),       # 100 auth requests per 5 minutes
            "file_upload": RateLimitRule(requests=50, window=300), # 50 file uploads per 5 minutes
            "websocket": RateLimitRule(requests=2000, window=3600), # 2000 WebSocket messages per hour
            "ai_requests": RateLimitRule(requests=200, window=3600), # 200 AI requests per hour
        }
        
        # Premium user multipliers
        self.premium_multipliers = {
            "basic": 1.0,
            "premium": 2.0,
            "enterprise": 5.0
        }
    
    async def get_redis_client(self) -> redis.Redis:
        """Get or create Redis client"""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30
            )
        return self.redis_client
    
    def get_client_identifier(self, request: Request) -> str:
        """Generate unique identifier for rate limiting"""
        # Try to get authenticated user ID first
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address with X-Forwarded-For support
        forwarded_ip = request.headers.get("X-Forwarded-For")
        if forwarded_ip:
            # Take the first IP in case of multiple proxies
            client_ip = forwarded_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"
    
    def get_rate_limit_key(self, identifier: str, rule_name: str) -> str:
        """Generate Redis key for rate limiting"""
        # Hash the identifier for privacy and consistent key length
        id_hash = hashlib.md5(identifier.encode()).hexdigest()[:16]
        return f"ratelimit:{rule_name}:{id_hash}"
    
    def get_rule_for_endpoint(self, request: Request) -> tuple[str, RateLimitRule]:
        """Determine which rate limiting rule to apply"""
        path = request.url.path.lower()
        method = request.method.upper()
        
        # Authentication endpoints
        if "/auth/" in path or "/login" in path or "/register" in path:
            return "auth", self.default_rules["auth"]
        
        # File upload endpoints
        if "/files" in path and method in ["POST", "PUT"]:
            return "file_upload", self.default_rules["file_upload"]
        
        # WebSocket connections (handled separately)
        if path.startswith("/ws"):
            return "websocket", self.default_rules["websocket"]
        
        # AI-related endpoints
        if "/ai/" in path or "/agents/" in path or "/chat" in path:
            return "ai_requests", self.default_rules["ai_requests"]
        
        # Default rule for all other endpoints
        return "default", self.default_rules["default"]
    
    def get_user_multiplier(self, request: Request) -> float:
        """Get rate limit multiplier based on user plan"""
        # Try to get user plan from request state (set by auth middleware)
        user_plan = getattr(request.state, 'user_plan', 'basic')
        return self.premium_multipliers.get(user_plan, 1.0)
    
    async def check_rate_limit(
        self, 
        identifier: str, 
        rule_name: str, 
        rule: RateLimitRule,
        multiplier: float = 1.0
    ) -> tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limits using sliding window"""
        try:
            redis_client = await self.get_redis_client()
            key = self.get_rate_limit_key(identifier, rule_name)
            
            # Apply multiplier to limits
            effective_limit = int(rule.requests * multiplier)
            window_size = rule.window
            
            # Current timestamp
            now = int(time.time())
            window_start = now - window_size
            
            # Use Redis pipeline for atomic operations
            async with redis_client.pipeline() as pipe:
                # Remove expired entries
                await pipe.zremrangebyscore(key, 0, window_start)
                
                # Count current requests in window
                await pipe.zcard(key)
                
                # Execute pipeline
                results = await pipe.execute()
                current_requests = results[1]
            
            # Check if limit exceeded
            if current_requests >= effective_limit:
                # Calculate retry after time
                async with redis_client.pipeline() as pipe:
                    await pipe.zrange(key, 0, 0, withscores=True)
                    oldest_requests = await pipe.execute()
                
                if oldest_requests[0]:
                    oldest_timestamp = int(oldest_requests[0][0][1])
                    retry_after = max(1, oldest_timestamp + window_size - now)
                else:
                    retry_after = window_size
                
                return False, {
                    "limit": effective_limit,
                    "remaining": 0,
                    "reset_time": now + retry_after,
                    "retry_after": retry_after
                }
            
            # Add current request
            async with redis_client.pipeline() as pipe:
                await pipe.zadd(key, {str(now): now})
                await pipe.expire(key, window_size + 10)  # Add buffer to TTL
                await pipe.execute()
            
            # Return success with rate limit info
            remaining = max(0, effective_limit - current_requests - 1)
            
            return True, {
                "limit": effective_limit,
                "remaining": remaining,
                "reset_time": now + window_size,
                "retry_after": None
            }
            
        except Exception as e:
            logger.error(f"❌ Rate limiting error for {identifier}: {e}")
            # Allow request to proceed on Redis errors (fail open)
            return True, {
                "limit": rule.requests,
                "remaining": rule.requests - 1,
                "reset_time": int(time.time()) + rule.window,
                "retry_after": None
            }
    
    async def process_request(self, request: Request) -> Optional[JSONResponse]:
        """Process rate limiting for incoming request"""
        try:
            # Get client identifier
            identifier = self.get_client_identifier(request)
            
            # Get rate limiting rule
            rule_name, rule = self.get_rule_for_endpoint(request)
            
            # Get user multiplier
            multiplier = self.get_user_multiplier(request)
            
            # Check rate limit
            allowed, info = await self.check_rate_limit(identifier, rule_name, rule, multiplier)
            
            # Add rate limiting headers to request state for later use
            request.state.rate_limit_info = info
            
            if not allowed:
                logger.warning(f"🚫 Rate limit exceeded for {identifier} on {rule_name}: "
                             f"{info['limit']} requests per {rule.window}s")
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Limit: {info['limit']} per {rule.window} seconds",
                        "limit": info["limit"],
                        "remaining": info["remaining"],
                        "reset_time": info["reset_time"],
                        "retry_after": info["retry_after"]
                    },
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": str(info["remaining"]),
                        "X-RateLimit-Reset": str(info["reset_time"]),
                        "Retry-After": str(info["retry_after"])
                    }
                )
            
            logger.debug(f"✅ Rate limit check passed for {identifier} on {rule_name}: "
                        f"{info['remaining']}/{info['limit']} remaining")
            
            return None  # Allow request to proceed
            
        except Exception as e:
            logger.error(f"❌ Rate limiting middleware error: {e}")
            # Allow request to proceed on errors (fail open)
            return None


class FastAPIRateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware wrapper for rate limiting"""
    
    def __init__(self, app, redis_url: str = None):
        super().__init__(app)
        self.rate_limiter = RateLimitMiddleware(redis_url)
    
    async def dispatch(self, request: Request, call_next):
        """Process rate limiting before request"""
        # Check rate limits
        rate_limit_response = await self.rate_limiter.process_request(request)
        if rate_limit_response:
            return rate_limit_response
        
        # Proceed with request
        response = await call_next(request)
        
        # Add rate limiting headers to response
        if hasattr(request.state, 'rate_limit_info'):
            info = request.state.rate_limit_info
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset_time"])
        
        return response


# Global rate limiting instance
rate_limiter = RateLimitMiddleware()


def create_rate_limit_dependency(rule_name: str, custom_rule: RateLimitRule = None):
    """Create a FastAPI dependency for endpoint-specific rate limiting"""
    
    async def rate_limit_dependency(request: Request):
        """Rate limiting dependency"""
        identifier = rate_limiter.get_client_identifier(request)
        rule = custom_rule or rate_limiter.default_rules.get(rule_name, rate_limiter.default_rules["default"])
        multiplier = rate_limiter.get_user_multiplier(request)
        
        allowed, info = await rate_limiter.check_rate_limit(identifier, rule_name, rule, multiplier)
        
        if not allowed:
            raise RateLimitExceeded(
                detail=f"Rate limit exceeded: {info['limit']} requests per {rule.window} seconds",
                retry_after=info["retry_after"]
            )
        
        return info
    
    return rate_limit_dependency


# Common rate limiting dependencies
auth_rate_limit = create_rate_limit_dependency("auth")
file_upload_rate_limit = create_rate_limit_dependency("file_upload")
ai_rate_limit = create_rate_limit_dependency("ai_requests")