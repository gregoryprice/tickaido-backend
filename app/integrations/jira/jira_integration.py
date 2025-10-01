#!/usr/bin/env python3
"""
JIRA Official Library Integration Service
Handles JIRA Cloud integration using the official jira Python library
Migration from custom httpx implementation to official jira>=3.10.5
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from jira import JIRA
from jira.exceptions import JIRAError

from ..base.integration_interface import IntegrationInterface
from ..base.integration_result import IntegrationTestResult, IntegrationTicketResult

logger = logging.getLogger(__name__)


class JiraIntegration(IntegrationInterface):
    """
    JIRA integration implementation using the official jira Python library.
    
    Uses the official jira>=3.10.5 library for enhanced functionality including
    rich text support, comment management, and improved attachment handling.
    """
    
    def __init__(self, base_url: str, email: str, api_token: str):
        """
        Initialize JIRA integration using official library.
        
        Args:
            base_url: JIRA instance URL (e.g., https://company.atlassian.net)
            email: Email address for authentication (username)
            api_token: API token generated from Atlassian account settings
        """
        # PRESERVE: Same constructor signature as current implementation
        self.base_url = base_url.rstrip('/')
        self.email = email
        self.api_token = api_token
        
        # Initialize official JIRA library with API v3 configuration
        self.jira = JIRA(
            server=self.base_url,
            basic_auth=(email, api_token),
            options={
                'timeout': 30,
                'verify': True,
                'server_has_json_encode_error_bug': False,
                'rest_api_version': '3',  # Force API v3 usage
                'agile_rest_api_version': '1.0'
            }
        )
        
        # Thread pool for async operations (jira library is sync)
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def close(self):
        """Close resources and thread pool"""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
    
    def _run_sync(self, func, *args, **kwargs):
        """
        Run synchronous JIRA operations in thread pool.
        
        Args:
            func: Synchronous function to run
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Awaitable that resolves to function result
        """
        if not self._executor:
            raise RuntimeError("Integration has been closed")
        
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(self._executor, func, *args, **kwargs)
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test JIRA connection using official library's current_user() method.
        Implements IntegrationInterface.test_connection().
        
        Returns:
            Dict with standardized test result format
        """
        try:
            start_time = time.time()
            
            # Use official library method (runs in thread pool for async compatibility)
            user_info = await self._run_sync(lambda: self.jira.myself())
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Log similar to original implementation
            logger.info(f"✅ JIRA connection successful for {self.email}")
            
            return IntegrationTestResult.success(
                message="Connection successful",
                details={
                    "user": user_info.get("displayName"),
                    "account_id": user_info.get("accountId"),
                    "email": user_info.get("emailAddress"),
                    "timezone": user_info.get("timeZone"),
                    "response_time_ms": int(duration_ms)
                }
            )
            
        except JIRAError as e:
            error_msg = f"JIRA API error: {e.status_code}"
            logger.error(f"❌ JIRA connection failed: {error_msg}")
            
            # PRESERVE: Same error code handling as original
            if e.status_code == 401:
                return IntegrationTestResult.failure("Invalid credentials - check email and API token")
            elif e.status_code == 403:
                return IntegrationTestResult.failure("Insufficient permissions - check API token permissions")
            elif e.status_code == 404:
                return IntegrationTestResult.failure("JIRA instance not found - check base URL")
            else:
                return IntegrationTestResult.failure(error_msg)
                
        except Exception as e:
            logger.error(f"❌ JIRA connection failed: {e}")
            return IntegrationTestResult.failure(f"Connection failed: {str(e)}")
    
    async def test_authentication(self) -> Dict[str, Any]:
        """
        Test authentication credentials.
        For JIRA, this is the same as connection test.
        """
        return await self.test_connection()
    
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
            
            # Test project access using official library
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
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        """
        Get list of accessible JIRA projects using official library.
        
        Returns:
            List of project dictionaries with key, name, and description
        """
        try:
            start_time = time.time()
            
            # Use official library method
            projects = await self._run_sync(lambda: self.jira.projects())
            
            duration_ms = (time.time() - start_time) * 1000
            logger.debug(f"Retrieved {len(projects)} projects in {duration_ms:.0f}ms")
            
            result = []
            for project in projects:
                project_info = {
                    "key": project.key,
                    "name": project.name,
                    "description": getattr(project, 'description', ''),
                    "project_type": getattr(project, 'projectTypeKey', None),
                    "lead": getattr(project.lead, 'displayName', None) if hasattr(project, 'lead') and project.lead else None
                }
                result.append(project_info)
            
            return result
            
        except JIRAError as e:
            logger.error(f"❌ Failed to get JIRA projects: {e.status_code}")
            if e.status_code == 403:
                raise ValueError("Insufficient permissions to view projects")
            raise ValueError(f"Failed to get projects: {e.status_code}")
        except Exception as e:
            logger.error(f"❌ Failed to get JIRA projects: {e}")
            raise ValueError(f"Failed to get projects: {str(e)}")
    
    async def get_issue_types(self, project_key: str) -> List[Dict[str, Any]]:
        """
        Get issue types for a specific project using official library.
        
        Args:
            project_key: JIRA project key (e.g., "TEST")
            
        Returns:
            List of issue type dictionaries
        """
        try:
            # Use official library method
            project = await self._run_sync(lambda: self.jira.project(project_key))
            issue_types = await self._run_sync(lambda: self.jira.issue_types())
            
            # Filter issue types available for this project
            project_issue_types = []
            for issue_type in issue_types:
                issue_type_info = {
                    "id": issue_type.id,
                    "name": issue_type.name,
                    "description": getattr(issue_type, 'description', ''),
                    "subtask": getattr(issue_type, 'subtask', False)
                }
                project_issue_types.append(issue_type_info)
            
            return project_issue_types
            
        except JIRAError as e:
            logger.error(f"❌ Failed to get issue types for {project_key}: {e.status_code}")
            raise ValueError(f"Failed to get issue types: {e.status_code}")
        except Exception as e:
            logger.error(f"❌ Failed to get issue types: {e}")
            raise ValueError(f"Failed to get issue types: {str(e)}")
    
    async def create_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create JIRA issue using official library with enhanced ADF support.
        
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
            # Build issue fields using official library patterns
            issue_fields = {
                'project': {'key': issue_data["project_key"]},
                'issuetype': {'name': issue_data["issue_type"]},
                'summary': issue_data["summary"],
            }
            
            # Enhanced ADF description support (preserve from original implementation)
            if "description" in issue_data and issue_data["description"]:
                description_text = str(issue_data["description"]).strip()
                if description_text:
                    # JIRA Cloud v3 uses Atlassian Document Format (ADF) for rich text
                    issue_fields["description"] = {
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
                    issue_fields["description"] = {
                        "type": "doc",
                        "version": 1,
                        "content": []
                    }
            
            # Add optional fields
            if "priority" in issue_data and issue_data["priority"]:
                issue_fields["priority"] = {"name": issue_data["priority"]}
            
            if "assignee" in issue_data and issue_data["assignee"]:
                # Try email first, fallback to account ID
                assignee_value = issue_data["assignee"]
                if "@" in assignee_value:
                    issue_fields["assignee"] = {"emailAddress": assignee_value}
                else:
                    issue_fields["assignee"] = {"accountId": assignee_value}
            
            if "labels" in issue_data and issue_data["labels"]:
                issue_fields["labels"] = issue_data["labels"]
            
            # Add custom fields if provided
            if "custom_fields" in issue_data:
                for field_id, field_value in issue_data["custom_fields"].items():
                    issue_fields[field_id] = field_value
            
            logger.info(f"Creating JIRA issue in project {issue_data['project_key']}")
            logger.debug(f"JIRA fields: {issue_fields}")
            
            start_time = time.time()
            
            # Use official library to create issue
            # The official jira library expects the fields directly, not wrapped in 'fields' key
            new_issue = await self._run_sync(
                lambda: self.jira.create_issue(**issue_fields)
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Log similar to original implementation
            logger.info(f"✅ JIRA issue created: {new_issue.key} in {duration_ms:.0f}ms")
            
            issue_url = f"{self.base_url}/browse/{new_issue.key}"
            
            return {
                "key": new_issue.key,
                "id": new_issue.id,
                "url": issue_url,
                "self": new_issue.self,
                "project_key": issue_data["project_key"],
                "issue_type": issue_data["issue_type"],
                "summary": issue_data["summary"]
            }
            
        except JIRAError as e:
            # Enhanced error logging to capture full JIRA error details
            logger.error(f"❌ JIRAError caught: status_code={getattr(e, 'status_code', 'unknown')}")
            logger.error(f"❌ JIRAError text: {getattr(e, 'text', 'no text')}")
            logger.error(f"❌ JIRAError url: {getattr(e, 'url', 'no url')}")
            logger.error(f"❌ JIRAError response: {getattr(e, 'response', 'no response')}")
            
            error_msg = f"Failed to create JIRA issue: {e.status_code}"
            
            # Try to extract detailed error information
            error_response = {}
            try:
                if hasattr(e, 'text') and e.text:
                    # The official library stores error details in e.text
                    import json
                    try:
                        error_response = json.loads(e.text)
                    except:
                        # If not JSON, use the text as-is
                        error_response = {"message": e.text}
                elif hasattr(e, 'response') and e.response:
                    error_response = e.response.json() if hasattr(e.response, 'json') else {"raw_response": str(e.response)}
                
                if "errors" in error_response:
                    error_msg += f" - {error_response['errors']}"
                elif "errorMessages" in error_response:
                    error_msg += f" - {'; '.join(error_response['errorMessages'])}"
                elif "message" in error_response:
                    error_msg += f" - {error_response['message']}"
                
                logger.error(f"❌ JIRA error details: {error_response}")
                
            except Exception as parse_error:
                logger.error(f"❌ Failed to parse JIRA error response: {parse_error}")
            
            # Create a ValueError that includes the response for upstream handling
            error = ValueError(error_msg)
            if hasattr(e, 'response'):
                error.response = e.response
            error.error_details = error_response
            raise error
        except Exception as e:
            logger.error(f"❌ Failed to create JIRA issue: {e}")
            raise ValueError(f"Issue creation failed: {str(e)}")
    
    async def add_attachment(self, issue_key: str, file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        """
        Add attachment to JIRA issue using official library with enhanced error handling.
        
        Args:
            issue_key: JIRA issue key (e.g., "TEST-123")
            file_content: File content as bytes
            filename: Name of the file
            
        Returns:
            List of attachment dictionaries
            
        Raises:
            ValueError: For various attachment failure scenarios with specific error messages
        """
        # Validate inputs (preserve from original)
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
        
        # Retry configuration (preserve from original)
        max_retries = 3
        base_delay = 1.0
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Uploading attachment {safe_filename} to {issue_key} (attempt {attempt + 1}/{max_retries})")
                
                start_time = time.time()
                
                # Create a file-like object from bytes content
                import io
                file_obj = io.BytesIO(file_content)
                file_obj.name = safe_filename  # Set name attribute for jira library
                
                # Use official library method
                attachments = await self._run_sync(
                    lambda: self.jira.add_attachment(issue=issue_key, attachment=file_obj, filename=safe_filename)
                )
                
                duration_ms = (time.time() - start_time) * 1000
                
                logger.info(f"✅ Successfully uploaded attachment {safe_filename} to {issue_key} in {duration_ms:.0f}ms")
                
                # Return standardized attachment data (similar to original format)
                if not attachments:
                    raise ValueError("JIRA returned empty response for attachment upload")
                
                # The official library returns attachment objects, convert to dict format
                result = []
                for attachment in attachments if isinstance(attachments, list) else [attachments]:
                    attachment_dict = {
                        "id": attachment.id,
                        "filename": attachment.filename,
                        "size": attachment.size,
                        "content_url": attachment.content if hasattr(attachment, 'content') else None,
                        "thumbnail_url": attachment.thumbnail if hasattr(attachment, 'thumbnail') else None,
                        "author": attachment.author.displayName if hasattr(attachment, 'author') and attachment.author else "Unknown",
                        "created": attachment.created if hasattr(attachment, 'created') else None
                    }
                    result.append(attachment_dict)
                
                return result
                
            except JIRAError as e:
                # Handle specific JIRA errors (preserve from original error handling)
                if e.status_code == 404:
                    raise ValueError(f"JIRA issue {issue_key} not found")
                elif e.status_code == 403:
                    raise ValueError("Permission denied - unable to add attachments to this JIRA issue")
                elif e.status_code == 413:
                    raise ValueError("File is too large for JIRA attachment limits")
                elif e.status_code == 415:
                    raise ValueError(f"File type not supported by JIRA (filename: {safe_filename})")
                elif e.status_code == 429:
                    # Rate limit - should retry
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), 30)
                        logger.warning(f"Rate limited by JIRA API, retrying in {delay}s")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise ValueError("JIRA API rate limit exceeded")
                
                # For other HTTP errors, check if we should retry
                if e.status_code in [500, 502, 503, 504] and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"JIRA server error {e.status_code}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    error_msg = f"JIRA API error {e.status_code}: {e.text}"
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
    
    async def add_comment(self, issue_key: str, comment_text: str = None, comment_markdown: str = None) -> Dict[str, Any]:
        """
        Add comment to JIRA issue using official library with markdown to ADF conversion.
        
        Args:
            issue_key: JIRA issue key (e.g., "TEST-123")
            comment_text: Plain text comment content (deprecated - use comment_markdown)
            comment_markdown: Markdown comment content (preferred)
            
        Returns:
            Dict containing comment information
        """
        try:
            # Convert markdown to ADF format for JIRA
            if comment_markdown:
                comment_body = self._markdown_to_adf(comment_markdown)
            elif comment_text:
                # Fallback for plain text
                comment_body = {
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
            else:
                raise ValueError("Either comment_text or comment_markdown must be provided")
            
            # Use official library method
            comment = await self._run_sync(
                lambda: self.jira.add_comment(issue_key, comment_body)
            )
            
            logger.info(f"✅ Added comment to {issue_key}")
            
            return {
                "id": comment.id,
                "body": comment_markdown or comment_text,
                "author": comment.author.displayName if hasattr(comment, 'author') and comment.author else "Unknown",
                "created": comment.created if hasattr(comment, 'created') else None,
                "updated": comment.updated if hasattr(comment, 'updated') else None,
                "self": comment.self if hasattr(comment, 'self') else None
            }
            
        except JIRAError as e:
            error_msg = f"Failed to add comment to {issue_key}: {e.status_code}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"❌ Failed to add comment: {e}")
            raise ValueError(f"Comment failed: {str(e)}")
    
    async def update_comment(self, issue_key: str, comment_id: str, comment_markdown: str) -> Dict[str, Any]:
        """
        Update an existing comment in JIRA issue.
        
        Args:
            issue_key: JIRA issue key (e.g., "TEST-123")
            comment_id: ID of the comment to update
            comment_markdown: Updated markdown comment content
            
        Returns:
            Dict containing updated comment information
        """
        try:
            # Convert markdown to ADF format for JIRA
            comment_body = self._markdown_to_adf(comment_markdown)
            
            # Use official library method
            updated_comment = await self._run_sync(
                lambda: self.jira.comment(issue_key, comment_id).update(body=comment_body)
            )
            
            logger.info(f"✅ Updated comment {comment_id} in {issue_key}")
            
            # Get the updated comment to return current data
            comment = await self._run_sync(
                lambda: self.jira.comment(issue_key, comment_id)
            )
            
            return {
                "id": comment.id,
                "body": comment_markdown,
                "author": comment.author.displayName if hasattr(comment, 'author') and comment.author else "Unknown",
                "created": comment.created if hasattr(comment, 'created') else None,
                "updated": comment.updated if hasattr(comment, 'updated') else None,
                "self": comment.self if hasattr(comment, 'self') else None
            }
            
        except JIRAError as e:
            error_msg = f"Failed to update comment {comment_id} in {issue_key}: {e.status_code}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"❌ Failed to update comment: {e}")
            raise ValueError(f"Comment update failed: {str(e)}")
    
    async def delete_comment(self, issue_key: str, comment_id: str) -> bool:
        """
        Delete a comment from JIRA issue.
        
        Args:
            issue_key: JIRA issue key (e.g., "TEST-123")
            comment_id: ID of the comment to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            # Use official library method
            await self._run_sync(
                lambda: self.jira.comment(issue_key, comment_id).delete()
            )
            
            logger.info(f"✅ Deleted comment {comment_id} from {issue_key}")
            return True
            
        except JIRAError as e:
            error_msg = f"Failed to delete comment {comment_id} from {issue_key}: {e.status_code}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"❌ Failed to delete comment: {e}")
            raise ValueError(f"Comment deletion failed: {str(e)}")
    
    def _markdown_to_adf(self, markdown_content: str) -> Dict[str, Any]:
        """
        Convert markdown to Atlassian Document Format (ADF) for JIRA.
        This is the JIRA-specific conversion logic.
        
        Args:
            markdown_content: Markdown formatted text
            
        Returns:
            ADF document structure
        """
        if not markdown_content or not markdown_content.strip():
            return {
                "type": "doc",
                "version": 1,
                "content": []
            }
        
        try:
            import re
            lines = markdown_content.strip().split('\n')
            adf_content = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Handle headers
                if line.startswith('#'):
                    level = len(line) - len(line.lstrip('#'))
                    level = min(level, 6)  # ADF supports h1-h6
                    text = line.lstrip('#').strip()
                    adf_content.append({
                        "type": "heading",
                        "attrs": {"level": level},
                        "content": [{"type": "text", "text": text}]
                    })
                else:
                    # Convert basic inline formatting for ADF
                    text_content = []
                    
                    # Basic regex patterns for markdown conversion
                    # TODO: Enhance this for more complex markdown features
                    parts = re.split(r'(\*\*.*?\*\*|\*.*?\*|`.*?`|\[.*?\]\(.*?\))', line)
                    
                    for part in parts:
                        if not part:
                            continue
                        elif part.startswith('**') and part.endswith('**'):
                            # Bold text
                            text_content.append({
                                "type": "text",
                                "text": part[2:-2],
                                "marks": [{"type": "strong"}]
                            })
                        elif part.startswith('*') and part.endswith('*'):
                            # Italic text
                            text_content.append({
                                "type": "text", 
                                "text": part[1:-1],
                                "marks": [{"type": "em"}]
                            })
                        elif part.startswith('`') and part.endswith('`'):
                            # Code text
                            text_content.append({
                                "type": "text",
                                "text": part[1:-1],
                                "marks": [{"type": "code"}]
                            })
                        elif '[' in part and '](' in part and part.endswith(')'):
                            # Link - basic extraction
                            link_match = re.match(r'\[([^\]]+)\]\(([^\)]+)\)', part)
                            if link_match:
                                text_content.append({
                                    "type": "text",
                                    "text": link_match.group(1),
                                    "marks": [{"type": "link", "attrs": {"href": link_match.group(2)}}]
                                })
                            else:
                                text_content.append({"type": "text", "text": part})
                        else:
                            # Plain text
                            text_content.append({"type": "text", "text": part})
                    
                    if text_content:
                        adf_content.append({
                            "type": "paragraph",
                            "content": text_content
                        })
            
            return {
                "type": "doc",
                "version": 1,
                "content": adf_content if adf_content else [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": markdown_content.strip()}]
                    }
                ]
            }
            
        except Exception:
            # Fallback to simple paragraph
            return {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text", 
                                "text": markdown_content.strip()
                            }
                        ]
                    }
                ]
            }
    
    async def update_issue(self, issue_key: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update JIRA issue using official library with change tracking.
        
        Args:
            issue_key: JIRA issue key (e.g., "TEST-123")
            update_data: Dictionary containing fields to update:
                - summary: Issue title (optional)
                - description: Issue description markdown (optional) 
                - priority: Priority name (optional)
                - assignee: Assignee email (optional)
                - status: Status name (optional)
                - labels: List of labels (optional)
                
        Returns:
            Dict containing update results and changes made
            
        Raises:
            ValueError: If update fails
        """
        try:
            changes_made = []
            start_time = time.time()
            
            # Get current issue to track changes
            current_issue = await self._run_sync(lambda: self.jira.issue(issue_key))
            
            # Build update fields
            update_fields = {}
            
            # Handle summary (title) update
            if "summary" in update_data and update_data["summary"]:
                new_summary = str(update_data["summary"]).strip()
                if new_summary != current_issue.fields.summary:
                    update_fields["summary"] = new_summary
                    changes_made.append(f"summary: '{current_issue.fields.summary}' → '{new_summary}'")
            
            # Handle description update with markdown → ADF conversion
            if "description" in update_data and update_data["description"] is not None:
                new_description_adf = self._markdown_to_adf(str(update_data["description"]))
                update_fields["description"] = new_description_adf
                changes_made.append(f"description: updated with markdown content")
            
            # Handle priority update
            if "priority" in update_data and update_data["priority"]:
                new_priority = str(update_data["priority"])
                current_priority = current_issue.fields.priority.name if current_issue.fields.priority else None
                if new_priority != current_priority:
                    update_fields["priority"] = {"name": new_priority}
                    changes_made.append(f"priority: '{current_priority}' → '{new_priority}'")
            
            # Handle assignee update
            if "assignee" in update_data:
                assignee_value = update_data["assignee"]
                if assignee_value:
                    if "@" in assignee_value:
                        update_fields["assignee"] = {"emailAddress": assignee_value}
                    else:
                        update_fields["assignee"] = {"accountId": assignee_value}
                    changes_made.append(f"assignee: assigned to '{assignee_value}'")
                else:
                    update_fields["assignee"] = None
                    changes_made.append("assignee: unassigned")
            
            # Handle labels update
            if "labels" in update_data:
                new_labels = update_data["labels"] or []
                current_labels = current_issue.fields.labels or []
                if set(new_labels) != set(current_labels):
                    update_fields["labels"] = new_labels
                    changes_made.append(f"labels: {current_labels} → {new_labels}")
            
            # Only update if there are actual changes
            if not update_fields:
                logger.info(f"No changes detected for JIRA issue {issue_key}")
                return {
                    "issue_key": issue_key,
                    "changes_made": [],
                    "message": "No changes detected"
                }
            
            logger.info(f"Updating JIRA issue {issue_key} with {len(update_fields)} field changes")
            logger.info(f"Changes: {'; '.join(changes_made)}")
            
            # Apply updates to JIRA using official library with field-level error handling
            successful_updates = {}
            failed_updates = {}
            
            # Try to update each field individually to handle field-specific restrictions
            for field_name, field_value in update_fields.items():
                try:
                    await self._run_sync(
                        lambda: current_issue.update(fields={field_name: field_value})
                    )
                    successful_updates[field_name] = field_value
                    logger.info(f"✅ Successfully updated {field_name} in JIRA {issue_key}")
                except JIRAError as field_error:
                    failed_updates[field_name] = f"{field_error.status_code}: {field_error.text}"
                    logger.warning(f"⚠️ Could not update {field_name} in JIRA {issue_key}: {field_error.text}")
                except Exception as field_error:
                    failed_updates[field_name] = str(field_error)
                    logger.warning(f"⚠️ Could not update {field_name} in JIRA {issue_key}: {field_error}")
            
            # Update changes_made to reflect what actually succeeded
            if successful_updates:
                changes_made = [f"✅ {field}" for field in successful_updates.keys()]
            if failed_updates:
                changes_made.extend([f"❌ {field} (blocked by JIRA)" for field in failed_updates.keys()])
            
            duration_ms = (time.time() - start_time) * 1000
            
            logger.info(f"✅ JIRA issue {issue_key} updated successfully in {duration_ms:.0f}ms")
            
            return {
                "issue_key": issue_key,
                "changes_made": changes_made,
                "successful_updates": list(successful_updates.keys()),
                "failed_updates": failed_updates,
                "duration_ms": int(duration_ms),
                "message": f"Updated {len(successful_updates)}/{len(update_fields)} fields successfully"
            }
            
        except JIRAError as e:
            error_msg = f"Failed to update JIRA issue {issue_key}: {e.status_code}"
            logger.error(f"❌ {error_msg}")
            
            # Enhanced error logging
            try:
                if hasattr(e, 'text') and e.text:
                    logger.error(f"❌ JIRA error details: {e.text}")
                    error_msg += f" - {e.text}"
            except Exception:
                pass
            
            raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"❌ Failed to update JIRA issue {issue_key}: {e}")
            raise ValueError(f"Issue update failed: {str(e)}")
    
    async def get_issue_changes(self, issue_key: str, since_timestamp: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get recent changes from JIRA issue for synchronization.
        
        Args:
            issue_key: JIRA issue key (e.g., "TEST-123") 
            since_timestamp: Only get changes since this timestamp
            
        Returns:
            List of change records from JIRA
        """
        try:
            # Get issue with changelog
            issue = await self._run_sync(
                lambda: self.jira.issue(issue_key, expand='changelog')
            )
            
            changes = []
            if hasattr(issue, 'changelog') and issue.changelog:
                for history in issue.changelog.histories:
                    change_time = datetime.fromisoformat(history.created.replace('Z', '+00:00'))
                    
                    # Filter by timestamp if provided
                    if since_timestamp and change_time <= since_timestamp:
                        continue
                    
                    for item in history.items:
                        changes.append({
                            "field": item.field,
                            "field_type": item.fieldtype,
                            "old_value": item.fromString,
                            "new_value": item.toString,
                            "author": history.author.displayName if history.author else "Unknown",
                            "created": change_time.isoformat(),
                            "change_id": history.id
                        })
            
            logger.info(f"Retrieved {len(changes)} changes for JIRA issue {issue_key}")
            return changes
            
        except JIRAError as e:
            logger.error(f"❌ Failed to get changes for {issue_key}: {e.status_code}")
            raise ValueError(f"Failed to get issue changes: {e.status_code}")
        except Exception as e:
            logger.error(f"❌ Failed to get changes for {issue_key}: {e}")
            raise ValueError(f"Failed to get issue changes: {str(e)}")
    
    async def create_ticket(self, ticket_data: Dict[str, Any], is_test: bool = False) -> Dict[str, Any]:
        """
        Create ticket in JIRA using official library.
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
            # Get detailed error response if available (preserve from original)
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
    
    async def get_configuration_schema(self) -> Dict[str, Any]:
        """
        Get JIRA configuration schema.
        Implements IntegrationInterface.get_configuration_schema().
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
        Create JIRA ticket from internal ticket data using official library.
        This preserves the integration-specific logic from the original implementation.
        
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
            
            # Initialize JIRA integration using official library
            async with cls(
                base_url=integration.base_url,
                email=credentials.get("email"),
                api_token=credentials.get("api_token")
            ) as jira:
                
                # PRESERVE: Same category-to-issue-type mapping as original
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
                # (same as original implementation)
                
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
            # Get detailed error response if available (preserve from original)
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


# Factory function for creating JIRA integrations (preserve from original)
async def create_jira_integration(base_url: str, email: str, api_token: str) -> JiraIntegration:
    """
    Factory function to create and validate JIRA integration using official library.
    
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
    connection_result = await integration.test_connection()
    if not connection_result.get("success"):
        raise ValueError(f"Connection failed: {connection_result.get('message')}")
    
    return integration