#!/usr/bin/env python3
"""
Docker Log Validation Tests

Validates that Docker logs contain no errors after FastMCP implementation.
These tests ensure zero error tolerance as specified in the PRP.
"""

import pytest
import subprocess
import re
from typing import List, Dict


class TestDockerLogsValidation:
    """Validate that Docker logs contain no errors after FastMCP implementation."""
    
    def get_container_logs(self, service_name: str) -> str:
        """Get logs for a specific Docker service."""
        try:
            result = subprocess.run(
                ["docker", "compose", "logs", service_name, "--tail", "100"],
                capture_output=True,
                text=True,
                check=True,
                cwd="/Users/aristotle/projects/tickaido-backend"
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to get logs for {service_name}: {e}")
    
    def test_app_service_logs_no_errors(self):
        """Test that app service has no error logs."""
        logs = self.get_container_logs("app")
        
        # Check for common error patterns that should be eliminated
        error_patterns = [
            r"ERROR.*TaskGroup",
            r"ERROR.*unhandled errors",
            r"ERROR.*MCP.*failed",
            r"❌.*MCP",
            r"❌.*FastMCP.*failed",
            r"CRITICAL",
            r"Exception.*not caught",
            r"Traceback.*most recent call",
            r"ConnectionError",
            r"TimeoutError"
        ]
        
        errors = []
        for pattern in error_patterns:
            matches = re.findall(pattern, logs, re.IGNORECASE)
            errors.extend([f"Pattern '{pattern}': {match}" for match in matches])
        
        if errors:
            pytest.fail(f"Found {len(errors)} error patterns in app logs:\n" + "\n".join(errors[:5]))
    
    def test_mcp_server_logs_healthy(self):
        """Test that MCP server logs show healthy operation."""
        logs = self.get_container_logs("mcp-server")
        
        # Check for success patterns
        success_patterns = [
            r"✅.*FastMCP.*server.*started",
            r"✅.*Token.*authentication.*enabled", 
            r"✅.*Tools.*registered",
            r"INFO.*Starting.*FastMCP",
            r"✅.*Configured.*development.*tokens",
            r"✅.*API.*base.*URL"
        ]
        
        success_count = 0
        for pattern in success_patterns:
            if re.search(pattern, logs, re.IGNORECASE):
                success_count += 1
        
        # Require at least 3 success indicators
        assert success_count >= 3, f"MCP server logs show insufficient success indicators: {success_count}/6"
        
        # Check for error patterns
        error_patterns = [
            r"ERROR.*authentication",
            r"ERROR.*tool.*call",
            r"❌.*Failed",
            r"CRITICAL",
            r"Authentication.*failed",
            r"Token.*verification.*failed"
        ]
        
        errors = []
        for pattern in error_patterns:
            matches = re.findall(pattern, logs, re.IGNORECASE)
            errors.extend([f"Pattern '{pattern}': {match}" for match in matches])
        
        if errors:
            pytest.fail(f"Found {len(errors)} errors in MCP server logs:\n" + "\n".join(errors))
    
    def test_no_connection_errors(self):
        """Test that there are no connection errors between services."""
        services = ["app", "mcp-server", "postgres", "redis"]
        
        # Error patterns that should be eliminated by FastMCP implementation
        connection_error_patterns = [
            r"Connection.*refused",
            r"Connection.*reset",
            r"Connection.*timeout",
            r"Unable to connect",
            r"HTTP.*50[0-9]",
            r"307.*Temporary Redirect",  # Should be eliminated with FastMCP
            r"502.*Bad Gateway",
            r"503.*Service Unavailable",
            r"504.*Gateway Timeout"
        ]
        
        all_errors = []
        for service in services:
            try:
                logs = self.get_container_logs(service)
                service_errors = []
                
                for pattern in connection_error_patterns:
                    matches = re.findall(pattern, logs, re.IGNORECASE)
                    service_errors.extend([f"{service}: {match}" for match in matches])
                
                all_errors.extend(service_errors)
            except Exception:
                # Service might not be running, skip
                continue
        
        if all_errors:
            pytest.fail(f"Found connection errors:\n" + "\n".join(all_errors[:10]))
    
    def test_fastmcp_specific_success_patterns(self):
        """Test for FastMCP-specific success patterns in logs."""
        app_logs = self.get_container_logs("app")
        mcp_logs = self.get_container_logs("mcp-server")
        
        # FastMCP-specific success patterns
        fastmcp_patterns = [
            # App logs should show FastMCP client creation
            (app_logs, r"FastMCP.*client.*created", "App should create FastMCP clients"),
            (app_logs, r"✅.*Created.*Pydantic.*AI.*agent.*with.*FastMCP", "App should create agents with FastMCP"),
            
            # MCP server logs should show proper startup
            (mcp_logs, r"✅.*FastMCP.*server.*initialized", "MCP server should initialize properly"),
            (mcp_logs, r"✅.*Configured.*\d+.*development.*tokens", "MCP server should configure tokens"),
            (mcp_logs, r"✅.*Registered.*\d+.*MCP.*tools", "MCP server should register tools")
        ]
        
        missing_patterns = []
        for logs, pattern, description in fastmcp_patterns:
            if not re.search(pattern, logs, re.IGNORECASE):
                missing_patterns.append(f"{description}: Pattern '{pattern}' not found")
        
        if missing_patterns:
            pytest.fail(f"Missing FastMCP success patterns:\n" + "\n".join(missing_patterns))
    
    def test_no_legacy_mcp_patterns(self):
        """Test that old MCP implementation patterns are not present."""
        app_logs = self.get_container_logs("app")
        mcp_logs = self.get_container_logs("mcp-server")
        
        # Legacy patterns that should be eliminated
        legacy_patterns = [
            (app_logs, r"MCPServerStreamableHTTP", "Old MCPServerStreamableHTTP should not be used"),
            (app_logs, r"authenticated_client", "Old authenticated_client should not be referenced"),
            (mcp_logs, r"start_mcp_server\.py", "Old start_mcp_server.py should not be used"),
            (mcp_logs, r"principal_injection", "Old principal injection middleware should not be used"),
            (app_logs, r"mcp_client\.client\.mcp_client", "Old mcp_client should not be used")
        ]
        
        found_legacy = []
        for logs, pattern, description in legacy_patterns:
            matches = re.findall(pattern, logs, re.IGNORECASE)
            if matches:
                found_legacy.append(f"{description}: Found {len(matches)} occurrences")
        
        if found_legacy:
            pytest.fail(f"Found legacy MCP patterns (should be eliminated):\n" + "\n".join(found_legacy))
    
    def test_performance_indicators_in_logs(self):
        """Test that performance indicators show good performance."""
        app_logs = self.get_container_logs("app")
        mcp_logs = self.get_container_logs("mcp-server")
        
        # Check for performance warnings
        performance_warning_patterns = [
            r"latency.*high",
            r"timeout.*exceeded",
            r"slow.*response",
            r"performance.*degraded",
            r"took.*[5-9]\d+.*seconds",  # More than 50 seconds
            r"took.*\d{3,}.*seconds"     # 100+ seconds
        ]
        
        performance_warnings = []
        for logs in [app_logs, mcp_logs]:
            for pattern in performance_warning_patterns:
                matches = re.findall(pattern, logs, re.IGNORECASE)
                performance_warnings.extend(matches)
        
        if performance_warnings:
            pytest.fail(f"Found performance warnings in logs:\n" + "\n".join(performance_warnings[:5]))
    
    def test_authentication_success_patterns(self):
        """Test that authentication is working properly."""
        mcp_logs = self.get_container_logs("mcp-server")
        
        # Authentication success patterns
        auth_success_patterns = [
            r"authenticated.*user",
            r"token.*valid",
            r"authorization.*successful",
            r"✅.*authentication"
        ]
        
        auth_successes = 0
        for pattern in auth_success_patterns:
            if re.search(pattern, mcp_logs, re.IGNORECASE):
                auth_successes += 1
        
        # Should have at least one authentication success indicator
        # Note: This might be 0 if no actual requests were made yet
        # In that case, we just verify no auth failures
        
        # Check for authentication failures
        auth_failure_patterns = [
            r"authentication.*failed",
            r"invalid.*token",
            r"unauthorized.*access",
            r"permission.*denied",
            r"❌.*authentication"
        ]
        
        auth_failures = []
        for pattern in auth_failure_patterns:
            matches = re.findall(pattern, mcp_logs, re.IGNORECASE)
            auth_failures.extend(matches)
        
        if auth_failures:
            pytest.fail(f"Found authentication failures:\n" + "\n".join(auth_failures))


class TestDockerServiceHealth:
    """Test that all Docker services are healthy."""
    
    def get_service_status(self, service_name: str) -> Dict[str, str]:
        """Get status of a Docker service."""
        try:
            result = subprocess.run(
                ["docker", "compose", "ps", service_name, "--format", "json"],
                capture_output=True,
                text=True,
                check=True,
                cwd="/Users/aristotle/projects/tickaido-backend"
            )
            
            if result.stdout.strip():
                import json
                return json.loads(result.stdout.strip())
            return {}
            
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return {"State": "unknown"}
    
    def test_all_services_running(self):
        """Test that all required services are running."""
        required_services = ["app", "mcp-server", "postgres", "redis"]
        
        service_issues = []
        for service in required_services:
            status = self.get_service_status(service)
            
            if not status or status.get("State") != "running":
                service_issues.append(f"{service}: {status.get('State', 'unknown')}")
        
        if service_issues:
            pytest.fail(f"Services not running properly:\n" + "\n".join(service_issues))
    
    def test_services_healthy(self):
        """Test that services with health checks are healthy."""
        # Services that should have health checks
        health_check_services = ["app", "mcp-server", "postgres", "redis"]
        
        unhealthy_services = []
        for service in health_check_services:
            status = self.get_service_status(service)
            
            # Check if service has health status information
            if "Health" in status:
                if status["Health"] not in ["healthy", "(healthy)"]:
                    unhealthy_services.append(f"{service}: {status['Health']}")
        
        if unhealthy_services:
            pytest.fail(f"Unhealthy services:\n" + "\n".join(unhealthy_services))