#!/usr/bin/env python3
"""
AI service for AI-powered operations
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.customer_support_agent import (
    customer_support_agent, 
    CustomerSupportContext,
    TicketCreationResult
)
from app.agents.categorization_agent import (
    categorization_agent,
    CategorizationContext, 
    CategoryAnalysisResult
)
from app.services.ticket_service import ticket_service

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered operations"""
    
    async def create_ticket_with_ai(
        self,
        db: AsyncSession,
        user_input: str,
        uploaded_files: List[UUID] = None,
        conversation_context: List[Dict[str, Any]] = None,
        user_preferences: Dict[str, Any] = None,
        integration_preference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a ticket using AI analysis of user input.
        
        Args:
            db: Database session
            user_input: User's natural language input
            uploaded_files: List of uploaded file IDs
            conversation_context: Previous conversation history
            user_preferences: User preferences
            integration_preference: Preferred integration
            
        Returns:
            Dictionary with ticket and AI analysis results
        """
        try:
            logger.info(f"Creating AI-powered ticket for input: {user_input[:100]}...")
            
            # Prepare context for AI agent
            context = CustomerSupportContext(
                user_input=user_input,
                uploaded_files=[str(file_id) for file_id in (uploaded_files or [])],
                conversation_history=conversation_context or [],
                user_metadata=user_preferences or {},
                integration_preference=integration_preference
            )
            
            # Use AI agent to create ticket
            ai_result = await customer_support_agent.create_ticket_with_ai(context)
            
            if not ai_result:
                raise ValueError("AI agent failed to create ticket")
            
            # Create actual ticket in database
            ticket_data = {
                "title": ai_result.ticket_title,
                "description": ai_result.ticket_description,
                "category": ai_result.category,
                "priority": ai_result.priority,
                "urgency": ai_result.urgency,
                "department": ai_result.department,
                "integration_routing": ai_result.recommended_integration,
                "ai_confidence_score": str(ai_result.confidence_score),
                "source_channel": "ai_agent",
                # TODO: Set created_by_id from authenticated user
            }
            
            # Add AI analysis metadata
            if hasattr(ai_result, 'file_analysis_summary') and ai_result.file_analysis_summary:
                ticket_data["ai_reasoning"] = f"File Analysis: {ai_result.file_analysis_summary}\n\nAI Reasoning: {ai_result.reasoning if hasattr(ai_result, 'reasoning') else 'N/A'}"
            
            # Create the ticket
            ticket = await ticket_service.create_ticket(db, ticket_data)
            
            # Prepare response
            result = {
                "ticket": ticket,
                "ai_analysis": {
                    "confidence_score": ai_result.confidence_score,
                    "reasoning": getattr(ai_result, 'reasoning', 'AI analysis completed'),
                    "tags": getattr(ai_result, 'tags', []),
                    "keywords": [],
                    "similar_patterns": [],
                    "sentiment": "neutral",
                    "business_impact": getattr(ai_result, 'business_impact', 'medium')
                },
                "confidence_score": ai_result.confidence_score,
                "suggested_actions": ai_result.next_actions,
                "file_analysis_summary": ai_result.file_analysis_summary
            }
            
            logger.info(f"Successfully created AI-powered ticket {ticket.id}")
            return result
            
        except Exception as e:
            logger.error(f"Error creating AI-powered ticket: {e}")
            raise
    
    async def categorize_ticket(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        force_reanalysis: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Categorize a ticket using AI.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            force_reanalysis: Force re-analysis
            
        Returns:
            Categorization results or None
        """
        try:
            # Get ticket
            ticket = await ticket_service.get_ticket(db, ticket_id)
            if not ticket:
                return None
            
            # Skip if already analyzed and not forcing
            if not force_reanalysis and ticket.ai_confidence_score:
                logger.info(f"Ticket {ticket_id} already has AI analysis")
                return {
                    "category": ticket.category.value,
                    "confidence_score": float(ticket.ai_confidence_score),
                    "reasoning": ticket.ai_reasoning or "Previously analyzed"
                }
            
            logger.info(f"Categorizing ticket {ticket_id} with AI")
            
            # Prepare context
            context = CategorizationContext(
                title=ticket.title,
                description=ticket.description,
                attachments=[],  # TODO: Add file paths
                user_context={},  # TODO: Add user context
                existing_category=ticket.category.value,
                department_preference=ticket.department
            )
            
            # Use AI agent for categorization
            analysis = await categorization_agent.categorize_ticket(context)
            
            if not analysis:
                logger.warning(f"AI categorization failed for ticket {ticket_id}")
                return None
            
            # Update ticket with AI analysis
            update_data = {
                "category": analysis.category,
                "subcategory": analysis.subcategory,
                "priority": analysis.priority,
                "urgency": analysis.urgency,
                "department": analysis.department,
                "ai_confidence_score": str(analysis.confidence_score),
                "ai_reasoning": analysis.reasoning,
                "ai_tags": analysis.tags,
                "ai_keywords": analysis.keywords_detected,
                "ai_similar_patterns": analysis.similar_patterns,
                "business_impact": analysis.business_impact,
                "customer_segment": analysis.customer_segment,
                "estimated_effort": analysis.estimated_effort
            }
            
            await ticket_service.update_ticket(db, ticket_id, update_data)
            
            result = {
                "category": analysis.category,
                "subcategory": analysis.subcategory,
                "priority": analysis.priority,
                "urgency": analysis.urgency,
                "department": analysis.department,
                "confidence_score": analysis.confidence_score,
                "reasoning": analysis.reasoning,
                "tags": analysis.tags,
                "keywords": analysis.keywords_detected,
                "similar_patterns": analysis.similar_patterns,
                "business_impact": analysis.business_impact,
                "customer_segment": analysis.customer_segment,
                "estimated_effort": analysis.estimated_effort
            }
            
            logger.info(f"Successfully categorized ticket {ticket_id} as {analysis.category}")
            return result
            
        except Exception as e:
            logger.error(f"Error categorizing ticket {ticket_id}: {e}")
            raise
    
    async def analyze_file_content(
        self,
        file_path: str,
        file_type: str,
        analysis_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze file content using AI.
        
        Args:
            file_path: Path to file
            file_type: Type of file
            analysis_options: Analysis options
            
        Returns:
            Analysis results
        """
        try:
            logger.info(f"Analyzing file content: {file_path}")
            
            # TODO: Implement file analysis using MCP tools
            # This would use the MCP server's analyze_file tool
            
            # For now, return mock analysis
            analysis = {
                "file_type": file_type,
                "analysis_type": "auto",
                "extracted_text": f"Mock extracted text from {file_path}",
                "confidence": 0.85,
                "summary": f"File analysis completed for {file_path}",
                "key_topics": ["support", "issue", "request"],
                "sentiment": "neutral",
                "language": "en"
            }
            
            logger.info(f"File analysis completed for {file_path}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            raise
    
    async def get_ai_suggestions(
        self,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Get AI suggestions for various contexts.
        
        Args:
            context: Context information
            
        Returns:
            List of suggestions
        """
        try:
            # TODO: Implement AI suggestions based on context
            suggestions = [
                "Consider escalating to technical team",
                "Check for similar resolved tickets", 
                "Request additional information from user",
                "Schedule follow-up in 24 hours"
            ]
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting AI suggestions: {e}")
            return []


# Global service instance
ai_service = AIService()