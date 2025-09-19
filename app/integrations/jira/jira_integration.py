#!/usr/bin/env python3
"""
JIRA Integration Service
Handles JIRA Cloud API v3 integration for ticket creation, attachments, and comments
"""

import logging
import time
from typing import Dict, Any, Optional, List
from uuid import UUID
import httpx

from ..base.integration_interface import IntegrationInterface
from ..base.integration_result import IntegrationTestResult, IntegrationTicketResult
from app.utils.http_debug_logger import log_http_request_response_pair

logger = logging.getLogger(__name__)


class JiraIntegration(IntegrationInterface):
    """
    JIRA-specific integration implementation for JIRA Cloud API v3.
    Handles authentication, connection testing, and issue management.
    """
    
    def __init__(self, base_url: str, email: str, api_token: str):
        """
        Initialize JIRA integration.
        
        Args:
            base_url: JIRA instance URL (e.g., https://company.atlassian.net)
            email: Email address for authentication (username)
            api_token: API token generated from Atlassian account settings
        """
        # CRITICAL: JIRA requires email as username, API token as password
        self.base_url = base_url.rstrip('/')
        self.auth = httpx.BasicAuth(email, api_token)
        self.email = email
        self.api_token = api_token
        self.client = httpx.AsyncClient(
            auth=self.auth,
            timeout=30.0,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        )
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.client.aclose()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test JIRA connection by calling /rest/api/3/myself endpoint.
        Implements IntegrationInterface.test_connection().
        
        Returns:
            Dict with standardized test result format
        """
        try:
            # PATTERN: Test endpoint that requires authentication
            start_time = time.time()
            url = f"{self.base_url}/rest/api/3/myself"
            
            response = await self.client.get(url)
            response.raise_for_status()
            user_info = response.json()
            
            # Debug log the request/response
            duration_ms = (time.time() - start_time) * 1000
            log_http_request_response_pair(
                method="GET",
                url=url,
                response=response,
                headers=dict(self.client.headers),
                duration_ms=duration_ms
            )
            
            logger.info(f"✅ JIRA connection successful for {self.email}")
            
            return IntegrationTestResult.success(
                message="Connection successful",
                details={
                    "user": user_info.get("displayName"),
                    "account_id": user_info.get("accountId"),
                    "email": user_info.get("emailAddress"),
                    "timezone": user_info.get("timeZone"),
                    "response_time_ms": int(response.elapsed.total_seconds() * 1000)
                }
            )
            
        except httpx.HTTPStatusError as e:
            error_msg = f"JIRA API error: {e.response.status_code}"
            logger.error(f"❌ JIRA connection failed: {error_msg}")
            
            # GOTCHA: JIRA returns specific error codes
            if e.response.status_code == 401:
                return IntegrationTestResult.failure("Invalid credentials - check email and API token")
            elif e.response.status_code == 403:
                return IntegrationTestResult.failure("Insufficient permissions - check API token permissions")
            elif e.response.status_code == 404:
                return IntegrationTestResult.failure("JIRA instance not found - check base URL")
            else:
                return IntegrationTestResult.failure(error_msg)
                
        except httpx.TimeoutException:
            logger.error("❌ JIRA connection timeout")
            return IntegrationTestResult.failure("Connection timeout - JIRA instance may be unreachable")
        except Exception as e:
            logger.error(f"❌ JIRA connection failed: {e}")
            return IntegrationTestResult.failure(f"Connection failed: {str(e)}")
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        """
        Get list of accessible JIRA projects.
        
        Returns:
            List of project dictionaries with key, name, and description
        """
        try:
            start_time = time.time()
            url = f"{self.base_url}/rest/api/3/project"
            
            response = await self.client.get(url)
            response.raise_for_status()
            projects = response.json()
            
            # Debug log the request/response
            duration_ms = (time.time() - start_time) * 1000
            log_http_request_response_pair(
                method="GET",
                url=url,
                response=response,
                headers=dict(self.client.headers),
                duration_ms=duration_ms
            )
            
            return [
                {
                    "key": project.get("key"),
                    "name": project.get("name"),
                    "description": project.get("description", ""),
                    "project_type": project.get("projectTypeKey"),
                    "lead": project.get("lead", {}).get("displayName")
                }
                for project in projects
            ]
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Failed to get JIRA projects: {e.response.status_code}")
            if e.response.status_code == 403:
                raise ValueError("Insufficient permissions to view projects")
            raise ValueError(f"Failed to get projects: {e.response.status_code}")
    
    async def get_issue_types(self, project_key: str) -> List[Dict[str, Any]]:
        """
        Get issue types for a specific project.
        
        Args:
            project_key: JIRA project key (e.g., "TEST")
            
        Returns:
            List of issue type dictionaries
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/rest/api/3/issue/createmeta",
                params={
                    "projectKeys": project_key,
                    "expand": "projects.issuetypes.fields"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("projects"):
                return []
            
            project = data["projects"][0]
            return [
                {
                    "id": issue_type.get("id"),
                    "name": issue_type.get("name"),
                    "description": issue_type.get("description", ""),
                    "subtask": issue_type.get("subtask", False)
                }
                for issue_type in project.get("issuetypes", [])
            ]
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Failed to get issue types for {project_key}: {e.response.status_code}")
            raise ValueError(f"Failed to get issue types: {e.response.status_code}")
    
    async def create_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create JIRA issue with required fields.
        
        Args:
            issue_data: Dictionary containing issue information:
                - project_key: JIRA project key (required)
                - issue_type: Issue type name or ID (required) 
                - summary: Issue title (required)
                - description: Issue description (optional)
                - priority: Priority name (optional)
                - assignee: Assignee email/account ID (optional)
                - labels: List of labels (optional)
                - custom_fields: Dict of custom field mappings (optional)
                
        Returns:
            Dict containing created issue information
            
        Raises:
            ValueError: If issue creation fails
        """
        try:
            # CRITICAL: JIRA requires specific field format
            payload = {
                "fields": {
                    "project": {"key": issue_data["project_key"]},
                    "issuetype": {"name": issue_data["issue_type"]},
                    "summary": issue_data["summary"],
                }
            }
            
            # Add optional fields - Description in ADF format for JIRA v3
            if "description" in issue_data and issue_data["description"]:
                description_text = str(issue_data["description"]).strip()
                if description_text:
                    # JIRA Cloud v3 uses Atlassian Document Format (ADF) for rich text
                    payload["fields"]["description"] = {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": description_text
                                    }
                                ]
                            }
                        ]
                    }
                else:
                    # Empty description - provide minimal ADF structure
                    payload["fields"]["description"] = {
                        "type": "doc",
                        "version": 1,
                        "content": []
                    }
            
            if "priority" in issue_data:
                payload["fields"]["priority"] = {"name": issue_data["priority"]}
            
            if "assignee" in issue_data and issue_data["assignee"]:
                # Try email first, fallback to account ID
                assignee_value = issue_data["assignee"]
                if "@" in assignee_value:
                    payload["fields"]["assignee"] = {"emailAddress": assignee_value}
                else:
                    payload["fields"]["assignee"] = {"accountId": assignee_value}
            
            if "labels" in issue_data and issue_data["labels"]:
                payload["fields"]["labels"] = issue_data["labels"]
            
            # Add custom fields if provided
            if "custom_fields" in issue_data:
                for field_id, field_value in issue_data["custom_fields"].items():
                    payload["fields"][field_id] = field_value
            
            logger.info(f"Creating JIRA issue in project {issue_data['project_key']}")
            logger.debug(f"JIRA payload: {payload}")
            
            start_time = time.time()
            url = f"{self.base_url}/rest/api/3/issue"
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Debug log the request/response
            duration_ms = (time.time() - start_time) * 1000
            log_http_request_response_pair(
                method="POST",
                url=url,
                response=response,
                headers=dict(self.client.headers),
                json_data=payload,
                duration_ms=duration_ms
            )
            
            issue_key = result["key"]
            issue_url = f"{self.base_url}/browse/{issue_key}"
            
            logger.info(f"✅ JIRA issue created: {issue_key}")
            
            return {
                "key": issue_key,
                "id": result["id"],
                "url": issue_url,
                "self": result["self"],
                "project_key": issue_data["project_key"],
                "issue_type": issue_data["issue_type"],
                "summary": issue_data["summary"]
            }
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Failed to create JIRA issue: {e.response.status_code}"
            logger.error(f"❌ {error_msg}")
            
            # Preserve the full error response for debugging
            error_response = {}
            try:
                error_response = e.response.json()
                if "errors" in error_response:
                    error_msg += f" - {error_response['errors']}"
                elif "errorMessages" in error_response:
                    error_msg += f" - {'; '.join(error_response['errorMessages'])}"
            except (ValueError, KeyError, AttributeError):
                # Ignore JSON parsing errors for error details
                pass
            
            # Create a ValueError that includes the response for upstream handling
            error = ValueError(error_msg)
            error.response = e.response
            error.error_details = error_response
            raise error
        except Exception as e:
            logger.error(f"❌ Failed to create JIRA issue: {e}")
            raise ValueError(f"Issue creation failed: {str(e)}")
    
    async def add_attachment(self, issue_key: str, file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        """
        Add attachment to JIRA issue with enhanced error handling and retry logic.
        
        Args:
            issue_key: JIRA issue key (e.g., "TEST-123")
            file_content: File content as bytes
            filename: Name of the file
            
        Returns:
            List of attachment dictionaries
            
        Raises:
            ValueError: For various attachment failure scenarios with specific error messages
        """
        import asyncio
        
        # Validate inputs
        if not file_content:
            raise ValueError("File content is empty or None")
        
        if not filename or not filename.strip():
            raise ValueError("Filename is required and cannot be empty")
        
        # Validate file size (JIRA default limit is typically 10MB)
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        if len(file_content) > max_size:
            size_mb = len(file_content) / (1024 * 1024)
            raise ValueError(f"File size ({size_mb:.1f}MB) exceeds JIRA attachment limit (10MB)")
        
        # Sanitize filename for JIRA
        safe_filename = filename.replace('/', '_').replace('\\', '_')[:255]
        
        # Retry configuration
        max_retries = 3
        base_delay = 1.0
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Uploading attachment {safe_filename} to {issue_key} (attempt {attempt + 1}/{max_retries})")
                
                # JIRA attachment API requires multipart/form-data
                # Based on official JIRA v3 API documentation:
                # curl --form 'file=@"myfile.txt"' -H 'X-Atlassian-Token: no-check'
                
                import mimetypes
                mime_type, _ = mimetypes.guess_type(safe_filename)
                if not mime_type:
                    # Default based on file extension
                    if safe_filename.lower().endswith('.png'):
                        mime_type = 'image/png'
                    elif safe_filename.lower().endswith('.jpg') or safe_filename.lower().endswith('.jpeg'):
                        mime_type = 'image/jpeg'
                    elif safe_filename.lower().endswith('.pdf'):
                        mime_type = 'application/pdf'
                    else:
                        mime_type = 'application/octet-stream'
                
                # Format files according to JIRA API requirements
                files = {
                    "file": (safe_filename, file_content, mime_type)
                }
                
                # Headers exactly as specified in JIRA v3 documentation
                headers = {
                    "Accept": "application/json",
                    "X-Atlassian-Token": "no-check"  # Required for CSRF protection
                }
                
                # Create a clean client without conflicting headers
                async with httpx.AsyncClient(
                    auth=self.auth,
                    timeout=60.0,
                    # No default headers that could conflict with multipart
                ) as upload_client:
                    
                    logger.debug(f"JIRA attachment request: POST {self.base_url}/rest/api/3/issue/{issue_key}/attachments")
                    logger.debug(f"Headers: {headers}")
                    logger.debug(f"File: {safe_filename} ({mime_type}, {len(file_content)} bytes)")
                    
                    # Use JIRA API v3 with proper multipart form data
                    response = await upload_client.post(
                        f"{self.base_url}/rest/api/3/issue/{issue_key}/attachments",
                        files=files,
                        headers=headers
                    )
                
                # Enhanced error handling based on status codes
                if response.status_code == 404:
                    raise ValueError(f"JIRA issue {issue_key} not found")
                elif response.status_code == 403:
                    raise ValueError("Permission denied - unable to add attachments to this JIRA issue")
                elif response.status_code == 413:
                    raise ValueError("File is too large for JIRA attachment limits")
                elif response.status_code == 415:
                    raise ValueError(f"File type not supported by JIRA (filename: {safe_filename})")
                elif response.status_code == 429:
                    # Rate limit - should retry
                    rate_limit_reset = response.headers.get("X-RateLimit-Reset")
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), 30)
                        logger.warning(f"Rate limited by JIRA API, retrying in {delay}s")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise ValueError("JIRA API rate limit exceeded")
                
                response.raise_for_status()
                attachments = response.json()
                
                if not attachments:
                    raise ValueError("JIRA returned empty response for attachment upload")
                
                logger.info(f"✅ Successfully uploaded attachment {safe_filename} to {issue_key}")
                
                # Return standardized attachment data
                return [
                    {
                        "id": attachment.get("id"),
                        "filename": attachment.get("filename"),
                        "size": attachment.get("size"),
                        "content_url": attachment.get("content"),
                        "thumbnail_url": attachment.get("thumbnail"),
                        "author": attachment.get("author", {}).get("displayName", "Unknown"),
                        "created": attachment.get("created")
                    }
                    for attachment in attachments
                ]
                
            except httpx.TimeoutException as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Timeout uploading to {issue_key}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"❌ Timeout after {max_retries} attempts uploading {safe_filename} to {issue_key}")
                    raise ValueError(f"Upload timeout after {max_retries} attempts")
                    
            except httpx.ConnectError as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Connection error to JIRA, retrying in {delay}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"❌ Connection failed after {max_retries} attempts")
                    raise ValueError("Unable to connect to JIRA service")
                    
            except httpx.HTTPStatusError as e:
                # For HTTP errors, check if we should retry
                if e.response.status_code in [500, 502, 503, 504] and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"JIRA server error {e.response.status_code}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    error_details = ""
                    try:
                        error_response = e.response.json()
                        if "errorMessages" in error_response:
                            error_details = f": {', '.join(error_response['errorMessages'])}"
                    except:
                        pass
                    
                    error_msg = f"JIRA API error {e.response.status_code}{error_details}"
                    logger.error(f"❌ {error_msg}")
                    raise ValueError(error_msg)
                    
            except ValueError:
                # Re-raise validation errors without retry
                raise
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Unexpected error uploading attachment, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"❌ Failed to upload attachment after {max_retries} attempts: {e}")
                    raise ValueError(f"Attachment upload failed: {str(e)}")
        
        # If we get here, all retries failed
        raise ValueError(f"Failed to upload attachment after {max_retries} attempts. Last error: {str(last_error)}")
    
    async def add_comment(self, issue_key: str, comment_text: str) -> Dict[str, Any]:
        """
        Add comment to JIRA issue.
        
        Args:
            issue_key: JIRA issue key (e.g., "TEST-123")
            comment_text: Comment text content
            
        Returns:
            Dict containing comment information
        """
        try:
            # JIRA Cloud uses ADF format for comments
            payload = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": str(comment_text)
                                }
                            ]
                        }
                    ]
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/comment",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"✅ Added comment to {issue_key}")
            
            return {
                "id": result.get("id"),
                "body": comment_text,
                "author": result.get("author", {}).get("displayName"),
                "created": result.get("created"),
                "updated": result.get("updated"),
                "self": result.get("self")
            }
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Failed to add comment to {issue_key}: {e.response.status_code}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"❌ Failed to add comment: {e}")
            raise ValueError(f"Comment failed: {str(e)}")
    
    async def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """
        Get JIRA issue details.
        
        Args:
            issue_key: JIRA issue key (e.g., "TEST-123")
            
        Returns:
            Dict containing issue details
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}",
                params={
                    "expand": "changelog,comments,attachments"
                }
            )
            response.raise_for_status()
            issue = response.json()
            
            fields = issue.get("fields", {})
            
            return {
                "key": issue.get("key"),
                "id": issue.get("id"),
                "url": f"{self.base_url}/browse/{issue.get('key')}",
                "summary": fields.get("summary"),
                "description": self._extract_text_from_adf(fields.get("description")),
                "status": fields.get("status", {}).get("name"),
                "priority": fields.get("priority", {}).get("name"),
                "assignee": fields.get("assignee", {}).get("displayName"),
                "reporter": fields.get("reporter", {}).get("displayName"),
                "created": fields.get("created"),
                "updated": fields.get("updated"),
                "project_key": fields.get("project", {}).get("key"),
                "issue_type": fields.get("issuetype", {}).get("name"),
                "labels": fields.get("labels", []),
                "comments_count": len(issue.get("fields", {}).get("comment", {}).get("comments", [])),
                "attachments_count": len(fields.get("attachment", []))
            }
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Issue {issue_key} not found")
            error_msg = f"Failed to get issue {issue_key}: {e.response.status_code}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"❌ Failed to get issue: {e}")
            raise ValueError(f"Get issue failed: {str(e)}")
    
    def _extract_text_from_adf(self, adf_content: Optional[Dict]) -> str:
        """
        Extract plain text from Atlassian Document Format (ADF).
        
        Args:
            adf_content: ADF document structure
            
        Returns:
            Plain text content
        """
        if not adf_content or not isinstance(adf_content, dict):
            return ""
        
        def extract_text(node):
            if isinstance(node, dict):
                if node.get("type") == "text":
                    return node.get("text", "")
                elif "content" in node:
                    return "".join(extract_text(child) for child in node["content"])
            elif isinstance(node, list):
                return "".join(extract_text(item) for item in node)
            return ""
        
        return extract_text(adf_content)
    
    async def validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate JIRA integration configuration.
        
        Args:
            config: Configuration dictionary with project_key, etc.
            
        Returns:
            Dict containing validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "projects": [],
            "issue_types": []
        }
        
        try:
            # Test connection first
            connection_result = await self.test_connection()
            results.update(connection_result)
            
            # Get available projects
            projects = await self.get_projects()
            results["projects"] = projects
            
            # Validate project key if provided
            if "project_key" in config:
                project_key = config["project_key"]
                project_exists = any(p["key"] == project_key for p in projects)
                
                if project_exists:
                    # Get issue types for the project
                    issue_types = await self.get_issue_types(project_key)
                    results["issue_types"] = issue_types
                    
                    # Validate issue type if provided
                    if "default_issue_type" in config:
                        issue_type = config["default_issue_type"]
                        issue_type_exists = any(
                            it["name"] == issue_type or it["id"] == issue_type 
                            for it in issue_types
                        )
                        
                        if not issue_type_exists:
                            results["errors"].append(f"Issue type '{issue_type}' not found in project {project_key}")
                            results["valid"] = False
                else:
                    results["errors"].append(f"Project '{project_key}' not found or not accessible")
                    results["valid"] = False
            
            return results
            
        except Exception as e:
            results["valid"] = False
            results["errors"].append(str(e))
            return results


    # Interface implementation methods
    
    async def test_authentication(self) -> Dict[str, Any]:
        """
        Test authentication credentials.
        For JIRA, this is the same as connection test.
        """
        return await self.test_connection()
    
    async def create_ticket(self, ticket_data: Dict[str, Any], is_test: bool = False) -> Dict[str, Any]:
        """Create a ticket in JIRA, optionally as a test"""
        try:
            # Prepare ticket data for JIRA API
            jira_issue_data = {
                "fields": {
                    "project": {"key": ticket_data.get("project_key")},
                    "summary": ticket_data.get("summary", "Test Ticket"),
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": ticket_data.get("description", "This is a test ticket created by the integration service.")
                                    }
                                ]
                            }
                        ]
                    },
                    "issuetype": {"name": ticket_data.get("issue_type", "Task")}
                }
            }

            async with self.client as client:
                response = await client.post("issue", json=jira_issue_data)
                response.raise_for_status()
                issue_data = response.json()

            # If it's a test, we don't need to return the full ticket data
            if is_test:
                return {"success": True, "message": "Test ticket created successfully.", "details": {"issue_key": issue_data["key"]}}

            return {"success": True, "ticket_id": issue_data["key"], "data": issue_data}

        except httpx.HTTPStatusError as e:
            error_message = f"Failed to create JIRA ticket: {e.response.text}"
            logger.error(error_message)
            return {"success": False, "message": error_message}
        except Exception as e:
            error_message = f"An unexpected error occurred while creating a JIRA ticket: {str(e)}"
            logger.error(error_message)
            return {"success": False, "message": error_message}
            
    async def test_permissions(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test required permissions for ticket creation.
        
        Args:
            test_data: Should contain 'project_key' for JIRA testing
        """
        try:
            project_key = test_data.get("project_key")
            if not project_key:
                return IntegrationTestResult.failure(
                    "No project_key provided for permissions test"
                )
            
            # Test project access
            projects = await self.get_projects()
            project_exists = any(p.get("key") == project_key for p in projects)
            
            if project_exists:
                return IntegrationTestResult.success(
                    f"Project '{project_key}' accessible",
                    details={"project_key": project_key, "can_create_issues": True}
                )
            else:
                return IntegrationTestResult.failure(
                    f"Project '{project_key}' not found or not accessible",
                    details={"project_key": project_key}
                )
                
        except Exception as e:
            return IntegrationTestResult.failure(
                f"Permissions test failed: {str(e)}",
                details={"error": str(e)}
            )
    
    async def create_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create ticket in JIRA.
        Implements IntegrationInterface.create_ticket().
        
        Args:
            ticket_data: Normalized ticket data with fields:
                - summary: Issue title (required)
                - description: Issue description (optional)
                - project_key: JIRA project key (required)
                - issue_type: Issue type name (required)
                - priority: Priority name (optional)
                - assignee: Assignee email (optional)
                - labels: List of labels (optional)
        """
        try:
            # Use the existing create_issue method which handles JIRA API specifics
            jira_result = await self.create_issue(ticket_data)
            
            return IntegrationTicketResult.success(
                external_ticket_id=jira_result["key"],
                external_ticket_url=jira_result["url"],
                details=jira_result
            )
            
        except Exception as e:
            # Get detailed error response if available
            error_details = {"error": str(e)}
            if hasattr(e, 'error_details'):
                error_details["jira_api_response"] = e.error_details
            elif hasattr(e, 'response') and hasattr(e.response, 'json'):
                try:
                    error_details["jira_api_response"] = e.response.json()
                except:
                    pass
            
            return IntegrationTicketResult.failure(
                error_message=f"JIRA ticket creation failed: {str(e)}",
                details=error_details
            )
    
    async def get_all_fields(self) -> List[Dict[str, Any]]:
        """
        Get all fields available in JIRA instance including custom fields.
        
        Returns:
            List of field dictionaries with id, name, type, and schema
        """
        try:
            response = await self.client.get(f"{self.base_url}/rest/api/3/field")
            response.raise_for_status()
            fields = response.json()
            
            result = []
            for field in fields:
                field_info = {
                    "id": field.get("id"),
                    "name": field.get("name"),
                    "type": field.get("schema", {}).get("type"),
                    "custom": field.get("custom", False),
                    "schema": field.get("schema", {}),
                    "description": field.get("description", "")
                }
                result.append(field_info)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get JIRA fields: {e}")
            raise ValueError(f"Failed to get fields: {str(e)}")
    
    async def get_custom_fields(self) -> List[Dict[str, Any]]:
        """
        Get only custom fields from JIRA instance.
        
        Returns:
            List of custom field dictionaries
        """
        all_fields = await self.get_all_fields()
        custom_fields = [f for f in all_fields if f["custom"] and "customfield_" in f["id"]]
        
        # Sort by field ID for easier reading
        custom_fields.sort(key=lambda x: x["id"])
        
        return custom_fields
    
    async def find_acceptance_criteria_field(self) -> Optional[Dict[str, Any]]:
        """
        Find acceptance criteria or test planning field in JIRA.
        
        Returns:
            Field info dict if found, None otherwise
        """
        custom_fields = await self.get_custom_fields()
        
        # Look for fields with acceptance/criteria/test in the name
        keywords = ["acceptance", "criteria", "test", "planning", "ac", "definition of done"]
        
        for field in custom_fields:
            field_name = field["name"].lower()
            if any(keyword in field_name for keyword in keywords):
                return field
        
        return None

    async def get_configuration_schema(self) -> Dict[str, Any]:
        """
        Get JIRA configuration schema.
        """
        return {
            "type": "object",
            "required": ["base_url", "email", "api_token", "project_key"],
            "properties": {
                "base_url": {
                    "type": "string",
                    "description": "JIRA instance URL (e.g., https://company.atlassian.net)"
                },
                "email": {
                    "type": "string",
                    "format": "email",
                    "description": "Email address for authentication"
                },
                "api_token": {
                    "type": "string",
                    "description": "API token from Atlassian account settings"
                },
                "project_key": {
                    "type": "string",
                    "description": "JIRA project key (e.g., PROJ)"
                },
                "default_issue_type": {
                    "type": "string",
                    "default": "Task",
                    "description": "Default issue type for created tickets"
                }
            }
        }
    
    @classmethod
    async def create_ticket_from_internal(
        cls,
        integration: "Integration",
        ticket_data: "Ticket",
        db: Optional["AsyncSession"] = None,
        user_id: Optional["UUID"] = None,
        attachment_file_ids: Optional[List["UUID"]] = None,
        organization_id: Optional["UUID"] = None,
        original_priority_provided: bool = True
    ) -> Dict[str, Any]:
        """
        Create JIRA ticket from internal ticket data with attachment support.
        This is the integration-specific logic moved from TicketService.
        
        Args:
            integration: Integration model instance
            ticket_data: Internal ticket model instance
            db: Database session for attachment processing
            user_id: User ID for access control
            attachment_file_ids: List of validated file IDs to attach to the ticket
            organization_id: Organization ID for access control
            original_priority_provided: Whether priority was explicitly provided
            
        Returns:
            Dict with standardized creation result including attachment information
        """
        try:
            # Get credentials
            credentials = integration.get_credentials()
            
            # Initialize JIRA integration
            async with cls(
                base_url=integration.base_url,
                email=credentials.get("email"),
                api_token=credentials.get("api_token")
            ) as jira:
                
                # Map internal ticket data to JIRA format with proper field mapping
                # TODO: Re-add priority_mapping when implementing custom field mapping
                # priority_mapping = {
                #     "low": "Low",
                #     "medium": "Medium", 
                #     "high": "High",
                #     "critical": "Critical"
                # }
                
                category_to_issue_type = {
                    "technical": "Bug",
                    "billing": "Task",
                    "feature_request": "Story", 
                    "bug": "Bug",
                    "general": "Task",
                    "integration": "Task",
                    "performance": "Bug",
                    "security": "Bug",
                    "user_access": "Task"
                }
                
                # Get project key from routing rules or fallback to credentials
                project_key = None
                if integration.routing_rules:
                    project_key = integration.routing_rules.get("default_project")
                if not project_key:
                    project_key = credentials.get("project_key", "SUPPORT")
                
                jira_data = {
                    "project_key": str(project_key),
                    "issue_type": str(category_to_issue_type.get(
                        ticket_data.category.value if ticket_data.category else "general", 
                        "Task"
                    )),
                    "summary": str(ticket_data.title),
                    "description": str(ticket_data.description or ""),
                    "labels": [
                        "source:ai-ticket-creator", 
                        f"category:{ticket_data.category.value if ticket_data.category else 'general'}"
                    ]
                }
                
                # TODO: Implement proper field mapping for priority based on JIRA custom fields
                # For now, skip priority to avoid "Field 'priority' cannot be set" errors
                # when priority is not on the project's create screen
                # if original_priority_provided and ticket_data.priority:
                #     jira_priority = priority_mapping.get(
                #         ticket_data.priority.value, 
                #         "Medium"
                #     )
                #     jira_data["priority"] = str(jira_priority)
                
                logger.debug(f"JIRA data before create_ticket: {jira_data}")
                
                # Create JIRA issue using the interface method
                result = await jira.create_ticket(jira_data)
                
                # Handle attachments if ticket creation succeeded and attachment file IDs are provided
                attachment_summary = None
                if result.get("success") and attachment_file_ids and db and user_id and organization_id:
                    try:
                        logger.info(f"Processing {len(attachment_file_ids)} file attachments for JIRA issue {result['details']['key']}")
                        
                        from .jira_attachment_service import JiraAttachmentService
                        
                        attachment_service = JiraAttachmentService()
                        attachment_summary = await attachment_service.upload_ticket_attachments(
                            db=db,
                            jira=jira,
                            issue_key=result["details"]["key"],
                            file_ids=attachment_file_ids,
                            user_id=user_id,
                            organization_id=organization_id
                        )
                        
                        logger.info(f"Processed {len(attachment_file_ids)} attachments for JIRA issue {result['details']['key']}: "
                                  f"{attachment_summary.successful_uploads} successful, {attachment_summary.failed_uploads} failed")
                    
                    except Exception as attachment_error:
                        logger.error(f"Failed to process attachments for JIRA issue {result.get('details', {}).get('key', 'unknown')}: {attachment_error}")
                        # Don't fail the entire ticket creation due to attachment errors
                
                # Add attachment information to the result if available
                if attachment_summary:
                    result["details"]["attachments"] = [r.to_dict() for r in attachment_summary.results]
                    result["details"]["attachment_summary"] = attachment_summary.to_dict()
                
                # Track integration usage
                integration.record_request(success=result.get("success", False))
                
                return result
                
        except Exception as e:
            # Get detailed error response if available
            error_details = {"error": str(e)}
            if hasattr(e, 'error_details'):
                error_details["jira_api_response"] = e.error_details
            elif hasattr(e, 'response') and hasattr(e.response, 'json'):
                try:
                    error_details["jira_api_response"] = e.response.json()
                except:
                    pass
            
            # Track failed request
            integration.record_request(success=False, error_message=str(e))
            return IntegrationTicketResult.failure(
                error_message=f"JIRA ticket creation failed: {str(e)}",
                details=error_details
            )


# Factory function for creating JIRA integrations
async def create_jira_integration(base_url: str, email: str, api_token: str) -> JiraIntegration:
    """
    Factory function to create and validate JIRA integration.
    
    Args:
        base_url: JIRA instance URL
        email: Email for authentication
        api_token: API token for authentication
        
    Returns:
        JiraIntegration instance
        
    Raises:
        ValueError: If connection fails
    """
    integration = JiraIntegration(base_url, email, api_token)
    
    # Test connection immediately
    await integration.test_connection()
    
    return integration