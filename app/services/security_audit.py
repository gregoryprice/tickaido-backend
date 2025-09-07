#!/usr/bin/env python3
"""
Security audit logging for MCP authentication

This module provides comprehensive audit logging for MCP authentication events,
enabling security monitoring, forensic analysis, and compliance reporting.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

# Dedicated security logger for audit events
security_logger = logging.getLogger("security.mcp_auth")

# Ensure security logger has appropriate formatting
if not security_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - SECURITY - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    security_logger.addHandler(handler)
    security_logger.setLevel(logging.INFO)


class MCPSecurityAudit:
    """Audit logging for MCP authentication events"""
    
    @staticmethod
    def log_mcp_auth_attempt(
        user_id: str,
        tool_name: str,
        has_token: bool,
        success: bool,
        error_reason: Optional[str] = None,
        conversation_id: Optional[str] = None,
        token_expires_at: Optional[datetime] = None
    ):
        """Log MCP tool authentication attempt"""
        event_data = {
            "event_type": "mcp_auth_attempt",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "tool_name": tool_name,
            "has_token": has_token,
            "success": success,
            "error_reason": error_reason,
            "conversation_id": conversation_id,
            "token_expires_at": token_expires_at.isoformat() if token_expires_at else None
        }
        
        if success:
            security_logger.info(f"MCP_AUTH_SUCCESS: {event_data}")
        else:
            security_logger.warning(f"MCP_AUTH_FAILURE: {event_data}")
    
    @staticmethod
    def log_token_propagation(
        user_id: str,
        conversation_id: str,
        token_expires_at: Optional[datetime],
        auth_provider_type: str = "jwt"
    ):
        """Log successful token propagation to MCP context"""
        event_data = {
            "event_type": "token_propagation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "conversation_id": conversation_id,
            "token_expires_at": token_expires_at.isoformat() if token_expires_at else None,
            "auth_provider_type": auth_provider_type
        }
        
        security_logger.info(f"MCP_TOKEN_PROPAGATION: {event_data}")
    
    @staticmethod
    def log_token_validation_failure(
        user_id: Optional[str],
        failure_reason: str,
        token_hash: Optional[str] = None
    ):
        """Log token validation failure"""
        event_data = {
            "event_type": "token_validation_failure",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id or "unknown",
            "failure_reason": failure_reason,
            "token_hash": token_hash  # Safe to log hash for correlation
        }
        
        security_logger.warning(f"MCP_TOKEN_VALIDATION_FAILURE: {event_data}")
    
    @staticmethod
    def log_permission_check(
        user_id: str,
        permission: str,
        granted: bool,
        tool_name: Optional[str] = None
    ):
        """Log permission check result"""
        event_data = {
            "event_type": "permission_check",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "permission": permission,
            "granted": granted,
            "tool_name": tool_name
        }
        
        if granted:
            security_logger.debug(f"MCP_PERMISSION_GRANTED: {event_data}")
        else:
            security_logger.warning(f"MCP_PERMISSION_DENIED: {event_data}")
    
    @staticmethod
    def log_tool_execution(
        user_id: str,
        tool_name: str,
        execution_time_ms: float,
        success: bool,
        authenticated: bool,
        http_status: Optional[int] = None
    ):
        """Log MCP tool execution with security context"""
        event_data = {
            "event_type": "tool_execution",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "tool_name": tool_name,
            "execution_time_ms": execution_time_ms,
            "success": success,
            "authenticated": authenticated,
            "http_status": http_status
        }
        
        if success:
            security_logger.info(f"MCP_TOOL_SUCCESS: {event_data}")
        else:
            security_logger.warning(f"MCP_TOOL_FAILURE: {event_data}")
    
    @staticmethod
    def log_circuit_breaker_event(
        backend_url: str,
        event_type: str,  # "opened", "closed", "half-open"
        failure_count: int,
        last_failure_reason: Optional[str] = None
    ):
        """Log circuit breaker state changes"""
        event_data = {
            "event_type": "circuit_breaker_event",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "backend_url": backend_url,
            "circuit_event": event_type,
            "failure_count": failure_count,
            "last_failure_reason": last_failure_reason
        }
        
        if event_type == "opened":
            security_logger.error(f"MCP_CIRCUIT_BREAKER_OPENED: {event_data}")
        elif event_type == "closed":
            security_logger.info(f"MCP_CIRCUIT_BREAKER_CLOSED: {event_data}")
        else:
            security_logger.warning(f"MCP_CIRCUIT_BREAKER_HALF_OPEN: {event_data}")
    
    @staticmethod
    def log_suspicious_activity(
        user_id: Optional[str],
        activity_type: str,
        details: Dict[str, Any],
        severity: str = "medium"  # low, medium, high, critical
    ):
        """Log suspicious activity for security monitoring"""
        event_data = {
            "event_type": "suspicious_activity",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id or "unknown",
            "activity_type": activity_type,
            "severity": severity,
            "details": details
        }
        
        if severity in ["high", "critical"]:
            security_logger.error(f"MCP_SUSPICIOUS_ACTIVITY: {event_data}")
        else:
            security_logger.warning(f"MCP_SUSPICIOUS_ACTIVITY: {event_data}")


# Global audit instance
mcp_security_audit = MCPSecurityAudit()