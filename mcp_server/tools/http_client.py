#!/usr/bin/env python3
"""
High-performance authenticated HTTP client with connection pooling

This module provides a high-performance HTTP client for MCP tools with:
- Connection pooling for efficient resource usage
- Circuit breaker pattern for resilience
- Authentication header support
- HTTP/2 support for better performance
- Singleton pattern for optimal resource management
"""

import httpx
import asyncio
import logging
import time
from typing import Optional, Dict, Any, ClassVar

# Import the debug logger
try:
    from app.utils.http_debug_logger import log_http_request_response_pair
except ImportError:
    # Fallback if running outside main app context
    def log_http_request_response_pair(*args, **kwargs):
        pass

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker pattern for HTTP client resilience"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        elif self.state == "open":
            if self.last_failure_time and time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                return True
            return False
        else:  # half-open
            return True
    
    def record_success(self):
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class AuthenticatedHTTPClient:
    """HTTP client with connection pooling and circuit breaker for MCP tools"""
    
    _instances: ClassVar[Dict[str, 'AuthenticatedHTTPClient']] = {}
    _lock: ClassVar[Optional[asyncio.Lock]] = None
    
    def __init__(self, backend_url: str, max_connections: int = 100):
        self.backend_url = backend_url
        self._client: Optional[httpx.AsyncClient] = None
        self._max_connections = max_connections
        self._circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create connection-pooled HTTP client"""
        if not self._client or self._client.is_closed:
            limits = httpx.Limits(
                max_keepalive_connections=self._max_connections,
                max_connections=self._max_connections,
                keepalive_expiry=30.0
            )
            timeout = httpx.Timeout(30.0, connect=5.0)
            
            self._client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                follow_redirects=True,
                http2=True  # Enable HTTP/2 for better performance
            )
            logger.debug(f"Created new HTTP client for {self.backend_url}")
        return self._client
        
    async def make_request(
        self, 
        method: str, 
        endpoint: str,
        auth_headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> httpx.Response:
        """Make authenticated HTTP request with circuit breaker protection"""
        
        if not self._circuit_breaker.can_execute():
            raise httpx.HTTPError("Circuit breaker open - service unavailable")
        
        headers = {}
        if auth_headers:
            headers.update(auth_headers)
            # Sanitize Authorization header for logging
            auth_header = auth_headers.get('Authorization', '')
            if auth_header.startswith('Bearer ') and len(auth_header) > 15:
                sanitized_token = f"Bearer {auth_header[7:15]}...{auth_header[-4:]}"
                logger.debug(f"Authenticated request: {method} {endpoint} (token: {sanitized_token})")
            else:
                logger.debug(f"Authenticated request: {method} {endpoint}")
        else:
            logger.debug(f"Unauthenticated request: {method} {endpoint}")
        
        try:
            client = await self._get_client()
            start_time = time.time()
            url = f"{self.backend_url}{endpoint}"
            
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=timeout
            )
            
            # Debug log the request/response
            duration_ms = (time.time() - start_time) * 1000
            log_http_request_response_pair(
                method=method,
                url=url,
                response=response,
                headers=headers,
                params=params,
                json_data=json_data,
                duration_ms=duration_ms
            )
            
            self._circuit_breaker.record_success()
            return response
            
        except Exception as e:
            self._circuit_breaker.record_failure()
            logger.error(f"HTTP request failed: {method} {endpoint} - {e}")
            raise
    
    async def close(self):
        """Close HTTP client and cleanup connections"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug(f"Closed HTTP client for {self.backend_url}")
    
    @classmethod
    async def get_instance(cls, backend_url: str) -> 'AuthenticatedHTTPClient':
        """Get singleton instance for URL with connection pooling"""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
            
        async with cls._lock:
            if backend_url not in cls._instances:
                cls._instances[backend_url] = cls(backend_url)
                logger.debug(f"Created new HTTP client instance for {backend_url}")
            return cls._instances[backend_url]
    
    @classmethod
    async def cleanup_all(cls):
        """Close all client instances"""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
            
        async with cls._lock:
            for instance in cls._instances.values():
                await instance.close()
            cls._instances.clear()
            logger.debug("Closed all HTTP client instances")


# Global HTTP client instance - will be initialized by MCP tools
_global_http_client: Optional[AuthenticatedHTTPClient] = None

async def get_http_client(backend_url: str = "http://app:8000") -> AuthenticatedHTTPClient:
    """Get global HTTP client instance"""
    return await AuthenticatedHTTPClient.get_instance(backend_url)


async def cleanup_http_clients():
    """Cleanup all HTTP clients"""
    await AuthenticatedHTTPClient.cleanup_all()