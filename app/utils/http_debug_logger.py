#!/usr/bin/env python3
"""
HTTP Debug Logger Utility

A comprehensive debug logging utility for HTTP requests and responses.
Provides pretty-printed JSON bodies and sanitized headers for debugging
HTTP communication with 3rd party APIs (Jira, AI providers, etc.).
"""

import json
import logging
import time
from typing import Dict, Any, Optional, Union
import httpx

logger = logging.getLogger(__name__)


class HTTPDebugLogger:
    """
    Debug logger for HTTP requests and responses.
    
    Features:
    - Pretty-printed JSON request/response bodies
    - Sanitized headers (removes sensitive data)
    - Request timing information
    - Configurable log levels
    - Support for both httpx.Request/Response and dict objects
    """
    
    def __init__(self, enabled: bool = True, log_level: int = logging.DEBUG):
        """
        Initialize HTTP debug logger.
        
        Args:
            enabled: Whether debug logging is enabled
            log_level: Log level to use for debug messages
        """
        self.enabled = enabled
        self.log_level = log_level
        self._sensitive_headers = {
            'authorization', 'cookie', 'set-cookie', 'api-key', 'x-api-key',
            'api_key', 'access_token', 'refresh_token', 'bearer', 'token'
        }
        self._sensitive_params = {
            'api_key', 'access_token', 'refresh_token', 'password', 'secret',
            'token', 'key', 'auth'
        }
    
    def sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Sanitize headers to remove/mask sensitive information.
        
        Args:
            headers: Raw headers dictionary
            
        Returns:
            Sanitized headers dictionary
        """
        sanitized = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self._sensitive_headers):
                if key_lower == 'authorization' and value.lower().startswith('bearer '):
                    # Show first 8 and last 4 characters of bearer token
                    token = value[7:]  # Remove 'Bearer ' prefix
                    if len(token) > 12:
                        sanitized[key] = f"Bearer {token[:8]}...{token[-4:]}"
                    else:
                        sanitized[key] = "Bearer [REDACTED]"
                elif key_lower == 'authorization' and value.lower().startswith('basic '):
                    sanitized[key] = "Basic [REDACTED]"
                else:
                    sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized
    
    def sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize URL parameters or form data to remove sensitive information.
        
        Args:
            params: Raw parameters dictionary
            
        Returns:
            Sanitized parameters dictionary
        """
        if not params:
            return params
            
        sanitized = {}
        for key, value in params.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self._sensitive_params):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized
    
    def pretty_format_json(self, data: Any, max_length: int = 2000) -> str:
        """
        Pretty format JSON data with length limiting.
        
        Args:
            data: Data to format (dict, list, str, etc.)
            max_length: Maximum length for formatted output
            
        Returns:
            Pretty formatted JSON string
        """
        if data is None:
            return "null"
        
        try:
            # If it's already a string, try to parse it as JSON first
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except (json.JSONDecodeError, ValueError):
                    # Not JSON, return as-is but truncated
                    if len(data) > max_length:
                        return f"{data[:max_length]}... (truncated)"
                    return data
            
            # Pretty format the JSON
            formatted = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
            
            # Truncate if too long
            if len(formatted) > max_length:
                return f"{formatted[:max_length]}... (truncated)"
                
            return formatted
            
        except (TypeError, ValueError) as e:
            # Fallback for non-serializable objects
            str_repr = str(data)
            if len(str_repr) > max_length:
                return f"{str_repr[:max_length]}... (truncated)"
            return str_repr
    
    def log_request(
        self, 
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Any] = None,
        data: Optional[Any] = None,
        request_id: Optional[str] = None
    ) -> str:
        """
        Log HTTP request details.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            params: URL parameters
            json_data: JSON request body
            data: Form data or raw body
            request_id: Optional request ID for correlation
            
        Returns:
            Request ID for correlation with response
        """
        if not self.enabled:
            return request_id or f"req_{int(time.time() * 1000)}"
        
        if not request_id:
            request_id = f"req_{int(time.time() * 1000)}"
        
        # Create log message
        log_lines = [
            "=" * 80,
            f"🔍 HTTP REQUEST [{request_id}]",
            f"Method: {method.upper()}",
            f"URL: {url}",
        ]
        
        # Add headers
        if headers:
            sanitized_headers = self.sanitize_headers(headers)
            log_lines.append("Headers:")
            for key, value in sanitized_headers.items():
                log_lines.append(f"  {key}: {value}")
        
        # Add URL parameters
        if params:
            sanitized_params = self.sanitize_params(params)
            log_lines.append("URL Parameters:")
            log_lines.append(f"  {self.pretty_format_json(sanitized_params, 500)}")
        
        # Add JSON body
        if json_data is not None:
            log_lines.append("JSON Body:")
            log_lines.append(self.pretty_format_json(json_data))
        
        # Add form data or raw body
        if data is not None and json_data is None:
            if isinstance(data, dict):
                sanitized_data = self.sanitize_params(data)
                log_lines.append("Form Data:")
                log_lines.append(f"  {self.pretty_format_json(sanitized_data, 1000)}")
            else:
                data_str = str(data)
                if len(data_str) > 1000:
                    data_str = f"{data_str[:1000]}... (truncated)"
                log_lines.append(f"Body: {data_str}")
        
        log_lines.append("=" * 80)
        
        logger.log(self.log_level, "\n".join(log_lines))
        return request_id
    
    def log_response(
        self,
        response: Union[httpx.Response, Dict[str, Any]],
        request_id: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> None:
        """
        Log HTTP response details.
        
        Args:
            response: HTTP response object or response dict
            request_id: Request ID for correlation
            duration_ms: Request duration in milliseconds
        """
        if not self.enabled:
            return
        
        if not request_id:
            request_id = f"resp_{int(time.time() * 1000)}"
        
        # Extract response data
        if isinstance(response, httpx.Response):
            status_code = response.status_code
            headers = dict(response.headers)
            try:
                response_json = response.json()
            except Exception:
                try:
                    response_json = response.text
                except Exception:
                    response_json = f"<Binary content, {len(response.content)} bytes>"
        else:
            # Handle dict response (for custom response objects)
            status_code = response.get('status_code', 'Unknown')
            headers = response.get('headers', {})
            response_json = response.get('body', response.get('data', response))
        
        # Create log message
        log_lines = [
            "=" * 80,
            f"📡 HTTP RESPONSE [{request_id}]",
            f"Status: {status_code}",
        ]
        
        if duration_ms is not None:
            log_lines.append(f"Duration: {duration_ms:.2f}ms")
        
        # Add response headers (sanitized)
        if headers:
            sanitized_headers = self.sanitize_headers(headers)
            log_lines.append("Headers:")
            for key, value in sanitized_headers.items():
                log_lines.append(f"  {key}: {value}")
        
        # Add response body
        log_lines.append("Response Body:")
        log_lines.append(self.pretty_format_json(response_json))
        log_lines.append("=" * 80)
        
        logger.log(self.log_level, "\n".join(log_lines))
    
    def log_request_response_pair(
        self,
        method: str,
        url: str,
        response: Union[httpx.Response, Dict[str, Any]],
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Any] = None,
        data: Optional[Any] = None,
        duration_ms: Optional[float] = None
    ) -> None:
        """
        Log both request and response in a single call.
        
        Args:
            method: HTTP method
            url: Request URL
            response: HTTP response
            headers: Request headers
            params: URL parameters
            json_data: JSON request body
            data: Form data or raw body
            duration_ms: Request duration in milliseconds
        """
        request_id = self.log_request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json_data=json_data,
            data=data
        )
        self.log_response(
            response=response,
            request_id=request_id,
            duration_ms=duration_ms
        )


# Global debug logger instance
http_debug_logger = HTTPDebugLogger()


def enable_http_debug_logging(enabled: bool = True, log_level: int = logging.DEBUG) -> None:
    """
    Enable or disable HTTP debug logging globally.
    
    Args:
        enabled: Whether to enable debug logging
        log_level: Log level to use for debug messages
    """
    global http_debug_logger
    http_debug_logger.enabled = enabled
    http_debug_logger.log_level = log_level
    
    if enabled:
        logger.info(f"✅ HTTP debug logging enabled at level {logging.getLevelName(log_level)}")
    else:
        logger.info("❌ HTTP debug logging disabled")


def log_http_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Any] = None,
    data: Optional[Any] = None,
    request_id: Optional[str] = None
) -> str:
    """
    Convenience function to log HTTP request.
    
    Returns:
        Request ID for correlation with response
    """
    return http_debug_logger.log_request(
        method=method,
        url=url,
        headers=headers,
        params=params,
        json_data=json_data,
        data=data,
        request_id=request_id
    )


def log_http_response(
    response: Union[httpx.Response, Dict[str, Any]],
    request_id: Optional[str] = None,
    duration_ms: Optional[float] = None
) -> None:
    """
    Convenience function to log HTTP response.
    """
    http_debug_logger.log_response(
        response=response,
        request_id=request_id,
        duration_ms=duration_ms
    )


def log_http_request_response_pair(
    method: str,
    url: str,
    response: Union[httpx.Response, Dict[str, Any]],
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Any] = None,
    data: Optional[Any] = None,
    duration_ms: Optional[float] = None
) -> None:
    """
    Convenience function to log both request and response.
    """
    http_debug_logger.log_request_response_pair(
        method=method,
        url=url,
        response=response,
        headers=headers,
        params=params,
        json_data=json_data,
        data=data,
        duration_ms=duration_ms
    )