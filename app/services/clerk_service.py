#!/usr/bin/env python3
"""
Clerk integration service for user authentication and management
"""

import logging
import os
from typing import Any, Dict, List, Optional

from clerk_backend_api import Clerk

logger = logging.getLogger(__name__)


class ClerkService:
    """Service for Clerk authentication integration"""
    
    def __init__(self):
        self.api_key = os.getenv('CLERK_SECRET_KEY')
        self.webhook_secret = os.getenv('CLERK_WEBHOOK_SECRET')
        
        if self.api_key:
            self.client = Clerk(bearer_auth=self.api_key)
        else:
            self.client = None
            logger.warning("CLERK_SECRET_KEY not found - Clerk functionality will be disabled")
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify Clerk session token and return user data"""
        logger.debug("Attempting to verify Clerk token")
        
        if not self.client:
            logger.error("Clerk client not initialized - missing CLERK_SECRET_KEY")
            return None
            
        try:
            # Use the official authenticate_request method as per SDK documentation
            import httpx
            from clerk_backend_api.security.types import AuthenticateRequestOptions
            
            logger.debug("Creating httpx request for Clerk authentication")
            
            # Create a mock request with the Bearer token
            request = httpx.Request("GET", "http://localhost", headers={
                "Authorization": f"Bearer {token}"
            })
            
            # Use authenticate_request with proper options
            logger.debug("Calling Clerk authenticate_request")
            request_state = self.client.authenticate_request(
                request,
                AuthenticateRequestOptions()  # Try without authorized_parties first
            )
            
            logger.debug(f"Clerk request state: is_signed_in={request_state.is_signed_in}")
            
            if not request_state.is_signed_in:
                logger.warning("Clerk authentication failed - user not signed in")
                return None
            
            # Debug: Check what attributes are available
            logger.debug(f"RequestState attributes: {dir(request_state)}")
            
            # Try to get user ID and extract organization info from payload
            user_id = None
            org_info = {}
            for attr in ['user_id', 'sub', 'user', 'payload']:
                if hasattr(request_state, attr):
                    attr_value = getattr(request_state, attr)
                    logger.debug(f"RequestState.{attr} = {attr_value}")
                    if attr == 'user_id' or attr == 'sub':
                        user_id = attr_value
                    elif attr == 'payload' and isinstance(attr_value, dict):
                        user_id = attr_value.get('sub')
                        # Extract organization information from JWT payload
                        # Clerk stores org info in the 'o' field
                        if 'o' in attr_value and isinstance(attr_value['o'], dict):
                            org_data = attr_value['o']
                            org_info = {
                                'org_id': org_data.get('id'),
                                'org_slug': org_data.get('slg'),  # 'slg' is the Clerk field for slug
                                'org_role': org_data.get('rol')   # 'rol' is the Clerk field for role
                            }
                            logger.debug(f"Extracted organization info from 'o' field: {org_info}")
                        # Also check for legacy format (direct fields)
                        elif 'org_id' in attr_value:
                            org_info = {
                                'org_id': attr_value.get('org_id'),
                                'org_slug': attr_value.get('org_slug'),
                                'org_role': attr_value.get('org_role')
                            }
                            logger.debug(f"Extracted organization info from legacy format: {org_info}")
            
            if not user_id:
                logger.error("Could not extract user_id from request state")
                return None
            
            # Get user data from the user_id
            logger.debug(f"Getting user data for user_id: {user_id}")
            user = self.client.users.get(user_id=user_id)
            logger.debug("Successfully retrieved user data from Clerk API")
            
            formatted_user = self._format_user_data(user, org_info)
            logger.debug(f"Formatted user data: {formatted_user}")
            
            return formatted_user
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Clerk user ID"""
        if not self.client:
            return None
            
        try:
            user = self.client.users.get(user_id=user_id)
            return self._format_user_data(user)
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    async def update_user_metadata(self, user_id: str, metadata: Dict[str, Any]) -> bool:
        """Update user metadata in Clerk"""
        if not self.client:
            return False
            
        try:
            self.client.users.update(user_id, private_metadata=metadata)
            return True
        except Exception as e:
            logger.error(f"Failed to update user metadata: {e}")
            return False
    
    async def list_users(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List users from Clerk"""
        if not self.client:
            return []
            
        try:
            response = self.client.users.list(limit=limit, offset=offset)
            return [self._format_user_data(user) for user in response.data]
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return []
    
    def _format_user_data(self, user, org_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format Clerk user data for application use"""
        # Extract primary email address
        primary_email = None
        if hasattr(user, 'email_addresses') and user.email_addresses:
            primary_email = user.email_addresses[0].email_address
        
        # Extract phone number
        phone_number = None
        if hasattr(user, 'phone_numbers') and user.phone_numbers:
            phone_number = user.phone_numbers[0].phone_number
        
        # Format external accounts
        external_accounts = []
        if hasattr(user, 'external_accounts') and user.external_accounts:
            for account in user.external_accounts:
                external_accounts.append({
                    'provider': account.provider if hasattr(account, 'provider') else 'unknown',
                    'external_id': account.external_id if hasattr(account, 'external_id') else None,
                    'email': account.email_address if hasattr(account, 'email_address') else None
                })
        
        formatted_data = {
            'clerk_id': user.id,
            'email': primary_email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip(),
            'image_url': user.image_url,
            'phone_number': phone_number,
            'external_accounts': external_accounts,
            'created_at': user.created_at,
            'updated_at': user.updated_at,
            'last_sign_in_at': getattr(user, 'last_sign_in_at', None),
            'private_metadata': getattr(user, 'private_metadata', {}) or {},
            'public_metadata': getattr(user, 'public_metadata', {}) or {}
        }
        
        # Add organization information if available
        if org_info:
            formatted_data.update({
                'org_id': org_info.get('org_id'),
                'org_slug': org_info.get('org_slug'),
                'org_role': org_info.get('org_role')
            })
        
        return formatted_data


# Global service instance
clerk_service = ClerkService()