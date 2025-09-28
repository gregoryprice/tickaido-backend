#!/usr/bin/env python3
"""
Principal Injection Middleware for MCP Server

This middleware extracts Principal from JWT tokens in HTTP headers
and injects Principal context into tool arguments as _mcp_context.
"""

import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


class PrincipalInjectionMiddleware:
    """
    Middleware that extracts Principal from JWT tokens and injects context into MCP tools.
    
    This is the ONLY place where JWT tokens are handled in the MCP layer.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def process_tool_call(
        self, 
        tool_name: str, 
        args: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Process incoming tool call and inject Principal context.
        
        Args:
            tool_name: Name of the tool being called
            args: Tool arguments from client
            headers: HTTP headers from client request
            
        Returns:
            Updated args with _mcp_context injected
        """
        try:
            # Extract JWT from headers
            auth_header = headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                # No authentication - tools will handle gracefully
                self.logger.warning(f"No authentication for MCP tool: {tool_name}")
                return args
            
            jwt_token = auth_header[7:]  # Remove 'Bearer ' prefix
            
            # Extract Principal (this is the ONLY place JWT tokens are handled!)
            try:
                from app.database import get_db_session
                from app.services.principal_service import principal_service
                
                async with get_db_session() as db:
                    principal = await principal_service.extract_principal(
                        token=jwt_token,
                        db=db,
                        request_context={
                            'client_ip': headers.get('X-Forwarded-For'),
                            'user_agent': headers.get('User-Agent'),
                            'request_id': headers.get('X-Request-ID'),
                            'tool_name': tool_name
                        }
                    )
                    
                    # Inject Principal context into tool args
                    args['_mcp_context'] = {
                        'principal': principal.to_cache_dict(),
                        'metadata': {
                            'tool_name': tool_name,
                            'request_headers': {k: v for k, v in headers.items() if not k.startswith('Authorization')},
                            'timestamp': datetime.utcnow().isoformat()
                        }
                    }
                    
                    self.logger.info(
                        f"✅ Principal context injected for tool: {tool_name} (user: {principal.email}, org: {principal.organization_id})"
                    )
                    
                    return args
                    
            except Exception as e:
                self.logger.error(f"❌ Principal extraction failed for tool {tool_name}: {e}")
                # Return args without context - tools will handle missing context
                return args
                
        except Exception as e:
            self.logger.error(f"❌ Failed to process tool call {tool_name}: {e}")
            return args


# Global middleware instance
principal_injection_middleware = PrincipalInjectionMiddleware()