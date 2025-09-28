"""
Agent-specific tool filtering for MCP clients using PydanticAI's official filtering mechanism
"""
import logging
from typing import List
from pydantic_ai.mcp import MCPServerStreamableHTTP

logger = logging.getLogger(__name__)

def create_filtered_mcp_client(base_client: MCPServerStreamableHTTP, allowed_tools: List[str], agent_id: str):
    """Create a tool-filtered MCP client using PydanticAI's official filtering mechanism"""
    logger.info(f"[TOOL_FILTER] Creating official filtered toolset for agent {agent_id} with tools: {allowed_tools}")
    
    # Convert to set for faster lookups
    allowed_tools_set = set(allowed_tools)
    
    def tool_filter_func(ctx, tool_def):
        """Filter function for PydanticAI's filtered() method"""
        tool_name = tool_def.name
        is_allowed = tool_name in allowed_tools_set
        
        if is_allowed:
            logger.info(f"[TOOL_FILTER] ✅ Tool '{tool_name}' allowed for agent {agent_id}")
        else:
            logger.info(f"[TOOL_FILTER] ❌ Tool '{tool_name}' filtered out for agent {agent_id}")
        
        return is_allowed
    
    # Use PydanticAI's official filtering mechanism
    filtered_toolset = base_client.filtered(tool_filter_func)
    
    # Preserve authentication information from the base client
    if hasattr(base_client, 'get_principal'):
        # Store principal getter on filtered toolset for reference
        filtered_toolset.get_principal = base_client.get_principal
        filtered_toolset.is_authenticated = base_client.is_authenticated
        logger.debug(f"[TOOL_FILTER] ✅ Preserved authentication methods on filtered toolset")
    
    logger.info(f"[TOOL_FILTER] ✅ Created official PydanticAI filtered toolset for agent {agent_id} with {len(allowed_tools)} allowed tools")
    
    return filtered_toolset