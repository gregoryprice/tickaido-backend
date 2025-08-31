#!/usr/bin/env python3
"""
Customer Support Agent

Pydantic AI agent for comprehensive customer support ticket creation with MCP integration.
Handles user requests, file analysis, and ticket routing.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from app.services.ai_config_service import ai_config_service
from app.agents.prompts import format_customer_support_prompt
from mcp_client.client import mcp_client

logger = logging.getLogger(__name__)


class CustomerSupportContext(BaseModel):
    """Context for customer support operations"""
    user_input: str = Field(description="User's input/request")
    uploaded_files: List[str] = Field(default=[], description="List of uploaded file paths")
    conversation_history: List[Dict[str, Any]] = Field(default=[], description="Previous conversation")
    user_metadata: Dict[str, Any] = Field(default={}, description="User information and context")
    session_id: Optional[str] = Field(None, description="Session identifier")
    integration_preference: Optional[str] = Field(None, description="Preferred integration for routing")


class TicketCreationResult(BaseModel):
    """Structured output from customer support agent"""
    ticket_title: str = Field(description="Generated ticket title")
    ticket_description: str = Field(description="Detailed ticket description")
    category: str = Field(description="Issue category (technical, billing, etc.)")
    priority: str = Field(description="Priority level (low, medium, high, critical)")
    urgency: str = Field(description="Urgency level (low, medium, high, critical)")
    department: str = Field(description="Recommended department")
    confidence_score: float = Field(description="Confidence in analysis (0-1)", ge=0, le=1)
    recommended_integration: Optional[str] = Field(None, description="Suggested integration routing")
    file_analysis_summary: str = Field(default="", description="Summary of file analysis results")
    next_actions: List[str] = Field(default=[], description="Recommended next steps")
    knowledge_base_matches: List[Dict[str, Any]] = Field(default=[], description="Relevant KB articles")
    estimated_resolution_time: Optional[str] = Field(None, description="Estimated time to resolve")
    tags: List[str] = Field(default=[], description="Relevant tags for the ticket")


class CustomerSupportAgent:
    """
    Pydantic AI agent for customer support operations.
    Integrates with MCP server for tool access and file processing.
    """
    
    def __init__(self):
        """Initialize the customer support agent"""
        self.agent_type = "customer_support_agent"
        self.agent: Optional[Agent] = None
        self._initialized = False
    
    async def ensure_initialized(self):
        """Ensure the agent is initialized"""
        if not self._initialized:
            await self._initialize_agent()
            self._initialized = True
    
    async def _initialize_agent(self):
        """Initialize the Pydantic AI agent with MCP client"""
        try:
            # Get agent configuration
            agent_config = await ai_config_service.get_agent_config(self.agent_type)
            if not agent_config:
                logger.error(f"No configuration found for {self.agent_type}")
                return
            
            # Get MCP client
            mcp = mcp_client.get_mcp_client()
            if not mcp:
                logger.error("MCP client not available")
                return
            
            # Get system prompt
            system_prompt = agent_config.get("system_prompt", "")
            if not system_prompt:
                system_prompt = format_customer_support_prompt(
                    user_input="{user_input}",
                    uploaded_files="{uploaded_files}",
                    conversation_history="{conversation_history}",
                    user_metadata="{user_metadata}"
                )
            
            # Initialize Pydantic AI agent
            self.agent = Agent(
                model=f"{agent_config.get('model_provider', 'openai')}:{agent_config.get('model_name', 'gpt-4o-mini')}",
                output_type=TicketCreationResult,
                system_prompt=system_prompt,
                tools=[mcp] if mcp else []
            )
            
            logger.info(f"✅ Customer support agent initialized with {agent_config.get('model_provider')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize customer support agent: {e}")
    
    async def create_ticket_with_ai(
        self,
        context: CustomerSupportContext
    ) -> Optional[TicketCreationResult]:
        """
        Create a support ticket using AI analysis of user input and files.
        
        Args:
            context: Customer support context with user input and files
            
        Returns:
            Optional[TicketCreationResult]: Structured ticket creation result
        """
        try:
            # Ensure agent is initialized
            await self.ensure_initialized()
            if not self.agent:
                logger.error("Customer support agent not available")
                return None
            
            logger.info(f"🎫 Creating ticket for user request: {context.user_input[:100]}...")
            
            # Prepare the prompt context
            prompt_context = self._prepare_prompt_context(context)
            
            # Run the AI agent
            result = await self.agent.run(
                prompt_context,
                message_history=context.conversation_history
            )
            
            if result and result.data:
                logger.info(f"✅ Ticket created: {result.data.ticket_title}")
                return result.data
            else:
                logger.error("❌ No result from customer support agent")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating ticket with AI: {e}")
            return None
    
    def _prepare_prompt_context(self, context: CustomerSupportContext) -> str:
        """Prepare the prompt context for the AI agent"""
        
        # Format file information
        file_info = ""
        if context.uploaded_files:
            file_info = f"\nUploaded files: {', '.join(context.uploaded_files)}"
        
        # Format conversation history
        history_info = ""
        if context.conversation_history:
            history_info = f"\nConversation history: {len(context.conversation_history)} previous messages"
        
        # Format user metadata
        metadata_info = ""
        if context.user_metadata:
            metadata_info = f"\nUser context: {context.user_metadata}"
        
        # Prepare integration preference
        integration_info = ""
        if context.integration_preference:
            integration_info = f"\nPreferred integration: {context.integration_preference}"
        
        return f"""
Please analyze the following customer support request and create a comprehensive support ticket:

User Request: {context.user_input}
{file_info}
{history_info}
{metadata_info}
{integration_info}

Process this request step by step:
1. If there are uploaded files, use the analyze_file tool to extract relevant information
2. Search the knowledge base for existing solutions using search_knowledge_base
3. Categorize the issue using categorize_issue tool
4. Create a comprehensive ticket with all relevant information
5. Suggest appropriate routing and next actions

Ensure the ticket is well-structured, professional, and contains all necessary information for resolution.
"""
    
    async def analyze_files_for_context(
        self,
        file_paths: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze uploaded files to extract context for ticket creation.
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Dict[str, Any]: File analysis results
        """
        try:
            if not mcp_client.is_available():
                logger.warning("MCP client not available for file analysis")
                return {"error": "File analysis service unavailable"}
            
            analysis_results = {}
            
            for file_path in file_paths:
                try:
                    # Determine file type (this would be more sophisticated in practice)
                    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        file_type = 'image/png'
                    elif file_path.lower().endswith(('.mp3', '.wav', '.m4a')):
                        file_type = 'audio/mpeg'
                    elif file_path.lower().endswith(('.mp4', '.avi', '.mov')):
                        file_type = 'video/mp4'
                    else:
                        file_type = 'application/octet-stream'
                    
                    # This would call the MCP analyze_file tool
                    # For now, we'll simulate the result
                    analysis_results[file_path] = {
                        "file_type": file_type,
                        "analysis_type": "auto",
                        "extracted_text": f"Analyzed content from {file_path}",
                        "confidence": 0.85,
                        "summary": "File analysis completed successfully"
                    }
                    
                    logger.info(f"📄 Analyzed file: {file_path}")
                    
                except Exception as e:
                    logger.error(f"Error analyzing file {file_path}: {e}")
                    analysis_results[file_path] = {
                        "error": str(e)
                    }
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in file analysis: {e}")
            return {"error": str(e)}
    
    async def search_knowledge_base_for_context(
        self,
        query: str,
        category: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Search knowledge base for relevant articles.
        
        Args:
            query: Search query
            category: Optional category filter
            
        Returns:
            List[Dict[str, Any]]: Knowledge base search results
        """
        try:
            if not mcp_client.is_available():
                logger.warning("MCP client not available for knowledge base search")
                return []
            
            # This would call the MCP search_knowledge_base tool
            # For now, we'll simulate the results
            results = [
                {
                    "id": "kb-001",
                    "title": "Common Issues and Solutions",
                    "summary": "Guide to resolving common support issues",
                    "relevance_score": 0.85,
                    "category": category or "general",
                    "url": "/kb/common-issues"
                }
            ]
            
            logger.info(f"🔍 Found {len(results)} knowledge base matches for: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """
        Get the current status of the customer support agent.
        
        Returns:
            Dict[str, Any]: Agent status information
        """
        try:
            agent_config = await ai_config_service.get_agent_config(self.agent_type)
            mcp_status = mcp_client.get_connection_info()
            
            return {
                "agent_type": self.agent_type,
                "initialized": self.agent is not None,
                "configuration": {
                    "model_provider": agent_config.get("model_provider") if agent_config else "unknown",
                    "model_name": agent_config.get("model_name") if agent_config else "unknown",
                    "temperature": agent_config.get("temperature") if agent_config else "unknown"
                },
                "mcp_client": mcp_status,
                "tools_available": mcp_client.get_available_tools(),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting agent status: {e}")
            return {
                "agent_type": self.agent_type,
                "error": str(e),
                "initialized": False
            }

# Global customer support agent instance
customer_support_agent = CustomerSupportAgent()