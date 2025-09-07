#!/usr/bin/env python3
"""
Categorization Agent

Pydantic AI agent specialized in categorizing customer support tickets
with high accuracy and consistency.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.services.ai_config_service import ai_config_service
from app.agents.prompts import format_categorization_prompt
from mcp_client.client import mcp_client

logger = logging.getLogger(__name__)


class CategorizationContext(BaseModel):
    """Context for ticket categorization"""
    title: str = Field(description="Ticket title")
    description: str = Field(description="Ticket description") 
    attachments: List[str] = Field(default=[], description="Attachment file paths")
    user_context: Dict[str, Any] = Field(default={}, description="User context information")
    existing_category: Optional[str] = Field(None, description="Existing category if any")
    department_preference: Optional[str] = Field(None, description="Preferred department")


class CategoryAnalysisResult(BaseModel):
    """Structured output from categorization agent"""
    category: str = Field(description="Primary issue category")
    subcategory: Optional[str] = Field(None, description="Specific subcategory if applicable")
    priority: str = Field(description="Priority level (low, medium, high, critical)")
    urgency: str = Field(description="Urgency level (low, medium, high, critical)")
    department: str = Field(description="Recommended department")
    confidence_score: float = Field(description="Confidence in categorization (0-1)", ge=0, le=1)
    reasoning: str = Field(description="Explanation of categorization decision")
    tags: List[str] = Field(default=[], description="Relevant tags for the issue")
    estimated_effort: str = Field(description="Estimated effort (minimal, moderate, significant, major)")
    similar_patterns: List[str] = Field(default=[], description="Similar issue patterns identified")
    keywords_detected: List[str] = Field(default=[], description="Key terms that influenced categorization")
    business_impact: str = Field(description="Potential business impact (low, medium, high, critical)")
    customer_segment: Optional[str] = Field(None, description="Affected customer segment")


class CategorizationAgent:
    """
    Pydantic AI agent specialized in ticket categorization.
    Uses lower temperature for consistent categorization results.
    """
    
    def __init__(self):
        """Initialize the categorization agent"""
        self.agent_type = "categorization_agent"
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
                logger.warning("MCP client not available - categorization will work without tools")
            
            # Get system prompt
            system_prompt = agent_config.get("system_prompt", "")
            if not system_prompt:
                system_prompt = format_categorization_prompt(
                    title="{title}",
                    description="{description}",
                    attachments="{attachments}",
                    user_context="{user_context}"
                )
            
            # Initialize Pydantic AI agent with lower temperature for consistency
            self.agent = Agent(
                model=f"{agent_config.get('model_provider', 'openai')}:{agent_config.get('model_name', 'gpt-3.5-turbo')}",
                output_type=CategoryAnalysisResult,
                system_prompt=system_prompt,
                tools=[mcp] if mcp else []
            )
            
            logger.info(f"✅ Categorization agent initialized with {agent_config.get('model_provider')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize categorization agent: {e}")
    
    async def categorize_ticket(
        self,
        context: CategorizationContext
    ) -> Optional[CategoryAnalysisResult]:
        """
        Categorize a support ticket with detailed analysis.
        
        Args:
            context: Categorization context with ticket details
            
        Returns:
            Optional[CategoryAnalysisResult]: Structured categorization result
        """
        try:
            # Ensure agent is initialized
            await self.ensure_initialized()
            if not self.agent:
                logger.error("Categorization agent not available")
                return None
            
            logger.info(f"🏷️ Categorizing ticket: {context.title[:50]}...")
            
            # Prepare the prompt context
            prompt_context = self._prepare_prompt_context(context)
            
            # Run the AI agent
            result = await self.agent.run(prompt_context)
            
            if result and result.data:
                logger.info(f"✅ Categorized as: {result.data.category} ({result.data.confidence_score:.2f})")
                return result.data
            else:
                logger.error("❌ No result from categorization agent")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error categorizing ticket: {e}")
            return None
    
    def _prepare_prompt_context(self, context: CategorizationContext) -> str:
        """Prepare the prompt context for the categorization agent"""
        
        # Format attachment information
        attachment_info = ""
        if context.attachments:
            attachment_info = f"\nAttachments: {', '.join(context.attachments)}"
        
        # Format user context
        user_info = ""
        if context.user_context:
            user_info = f"\nUser Context: {context.user_context}"
        
        # Format existing category if provided
        existing_info = ""
        if context.existing_category:
            existing_info = f"\nCurrent Category: {context.existing_category}"
        
        return f"""
Please categorize this support ticket with detailed analysis:

Title: {context.title}

Description: {context.description}
{attachment_info}
{user_info}
{existing_info}

Analyze this ticket considering:

1. ISSUE TYPE CLASSIFICATION:
   - technical: System errors, performance, configuration issues
   - billing: Payment, subscription, invoicing problems  
   - feature_request: New features, enhancements, improvements
   - bug: Software defects, unexpected behavior, broken functionality
   - user_access: Login, permissions, account access issues
   - general: Questions, how-to requests, general inquiries

2. PRIORITY ASSESSMENT:
   - critical: System down, security breach, data loss, blocking all users
   - high: Significant impact, multiple users affected, urgent business need
   - medium: Moderate impact, some users affected, important but not urgent
   - low: Minor issues, cosmetic problems, nice-to-have improvements

3. URGENCY EVALUATION:
   - critical: Immediate response required, business-critical
   - high: Response needed within hours, important issue
   - medium: Response needed within 1-2 business days
   - low: Response can wait, no immediate impact

4. DEPARTMENT ROUTING:
   - engineering: Technical issues requiring development work
   - support: General support questions, user assistance
   - billing: Payment and subscription related issues  
   - sales: Pre-sales questions, demos, pricing inquiries
   - product: Feature requests, feedback, roadmap questions

5. BUSINESS IMPACT:
   - critical: Major revenue impact, customer churn risk
   - high: Significant business disruption, important customers affected
   - medium: Moderate business impact, operational issues
   - low: Minimal business impact, internal process issues

Provide detailed reasoning for your categorization decisions and include confidence scores.
"""
    
    async def bulk_categorize(
        self,
        tickets: List[CategorizationContext]
    ) -> List[Optional[CategoryAnalysisResult]]:
        """
        Categorize multiple tickets efficiently.
        
        Args:
            tickets: List of tickets to categorize
            
        Returns:
            List[Optional[CategoryAnalysisResult]]: Categorization results
        """
        try:
            results = []
            
            logger.info(f"🏷️ Bulk categorizing {len(tickets)} tickets...")
            
            for i, context in enumerate(tickets):
                try:
                    result = await self.categorize_ticket(context)
                    results.append(result)
                    logger.info(f"✅ Categorized ticket {i+1}/{len(tickets)}")
                    
                except Exception as e:
                    logger.error(f"❌ Error categorizing ticket {i+1}: {e}")
                    results.append(None)
            
            successful = len([r for r in results if r is not None])
            logger.info(f"✅ Bulk categorization complete: {successful}/{len(tickets)} successful")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in bulk categorization: {e}")
            return [None] * len(tickets)
    
    async def analyze_categorization_patterns(
        self,
        recent_tickets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze categorization patterns from recent tickets.
        
        Args:
            recent_tickets: List of recent tickets with categorization
            
        Returns:
            Dict[str, Any]: Pattern analysis results
        """
        try:
            if not recent_tickets:
                return {"error": "No tickets provided for analysis"}
            
            # Analyze patterns
            category_counts = {}
            priority_counts = {}
            department_counts = {}
            
            for ticket in recent_tickets:
                category = ticket.get("category", "unknown")
                priority = ticket.get("priority", "unknown")
                department = ticket.get("department", "unknown")
                
                category_counts[category] = category_counts.get(category, 0) + 1
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
                department_counts[department] = department_counts.get(department, 0) + 1
            
            total_tickets = len(recent_tickets)
            
            analysis = {
                "total_tickets_analyzed": total_tickets,
                "category_distribution": {
                    cat: {"count": count, "percentage": round(count/total_tickets*100, 1)}
                    for cat, count in category_counts.items()
                },
                "priority_distribution": {
                    pri: {"count": count, "percentage": round(count/total_tickets*100, 1)}
                    for pri, count in priority_counts.items()
                },
                "department_distribution": {
                    dept: {"count": count, "percentage": round(count/total_tickets*100, 1)}
                    for dept, count in department_counts.items()
                },
                "most_common_category": max(category_counts, key=category_counts.get),
                "most_common_priority": max(priority_counts, key=priority_counts.get),
                "most_common_department": max(department_counts, key=department_counts.get),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📊 Analyzed patterns from {total_tickets} tickets")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing categorization patterns: {e}")
            return {"error": str(e)}
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """
        Get the current status of the categorization agent.
        
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
                    "temperature": agent_config.get("temperature") if agent_config else "unknown",
                    "confidence_threshold": agent_config.get("confidence_threshold") if agent_config else "unknown"
                },
                "mcp_client": mcp_status,
                "specialization": "ticket_categorization",
                "supported_categories": [
                    "technical", "billing", "feature_request", 
                    "bug", "user_access", "general"
                ],
                "supported_priorities": ["low", "medium", "high", "critical"],
                "supported_departments": [
                    "engineering", "support", "billing", "sales", "product"
                ],
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting categorization agent status: {e}")
            return {
                "agent_type": self.agent_type,
                "error": str(e),
                "initialized": False
            }

# Global categorization agent instance
categorization_agent = CategorizationAgent()