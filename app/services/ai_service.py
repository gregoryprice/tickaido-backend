#!/usr/bin/env python3
"""
AI service for AI-powered operations
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.categorization_agent import CategorizationContext, categorization_agent

# Legacy import - now using organization-scoped agents
from app.schemas.ai_response import CustomerSupportContext
from app.services.ticket_service import ticket_service

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered operations"""
    
    async def create_ticket_with_ai(
        self,
        db: AsyncSession,
        current_user: Any,
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
            current_user: Authenticated user creating the ticket
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
            
            # TODO: Replace with organization-scoped agent
            # For now, return a basic result structure
            logger.warning("Using legacy AI service - should be replaced with organization-scoped agent")
            
            # Create basic AI result structure for ticket creation
            class BasicAIResult:
                def __init__(self, user_input: str):
                    self.ticket_title = f"Support Request: {user_input[:50]}"
                    self.ticket_description = user_input
                    self.category = "general"
                    self.priority = "medium"
                    self.urgency = "medium" 
                    self.department = "Support"
                    self.confidence_score = 0.8
                    self.recommended_integration = None
                    
            ai_result = BasicAIResult(user_input)
            
            if not ai_result:
                raise ValueError("AI agent failed to create ticket")
            
            # Create actual ticket in database
            # Convert AI result values to match database enum format (uppercase)
            def normalize_category(category: str) -> str:
                """Normalize category to match database enum values"""
                if not category:
                    return "GENERAL"
                
                category_upper = category.upper()
                # Map common AI responses to valid enum values
                category_mapping = {
                    "TECHNICAL SUPPORT": "TECHNICAL",
                    "TECHNICAL": "TECHNICAL", 
                    "BILLING": "BILLING",
                    "FEATURE REQUEST": "FEATURE_REQUEST",
                    "BUG": "BUG",
                    "USER ACCESS": "USER_ACCESS",
                    "GENERAL": "GENERAL",
                    "INTEGRATION": "INTEGRATION",
                    "PERFORMANCE": "PERFORMANCE",
                    "SECURITY": "SECURITY"
                }
                return category_mapping.get(category_upper, "GENERAL")
            
            ticket_data = {
                "title": ai_result.ticket_title,
                "description": ai_result.ticket_description,
                "category": normalize_category(ai_result.category),
                "priority": ai_result.priority.upper() if ai_result.priority else None,
                "urgency": ai_result.urgency.upper() if ai_result.urgency else None,
                "department": ai_result.department,
                "ai_confidence_score": str(ai_result.confidence_score),
                "source_channel": "ai_agent",
                "created_by_id": current_user.id  # Use authenticated user ID
            }
            
            # Add AI analysis metadata
            if hasattr(ai_result, 'file_analysis_summary') and ai_result.file_analysis_summary:
                ticket_data["ai_reasoning"] = f"File Analysis: {ai_result.file_analysis_summary}\n\nAI Reasoning: {ai_result.reasoning if hasattr(ai_result, 'reasoning') else 'N/A'}"
            
            # Create the ticket
            ticket = await ticket_service.create_ticket(db, ticket_data)
            
            # Prepare properly formatted response
            # Format user info for ticket response
            user_info = {
                "id": current_user.id,
                "email": getattr(current_user, 'email', 'unknown@example.com'),
                "full_name": getattr(current_user, 'full_name', 'Unknown User'),
                "display_name": getattr(current_user, 'full_name', getattr(current_user, 'email', 'Unknown User')),
                "avatar_url": None
            }
            
            # Format ticket data for response (convert DB model to dict)
            ticket_data_response = {
                "id": str(ticket.id),
                "title": ticket.title,
                "display_title": ticket.title[:100] + "..." if len(ticket.title) > 100 else ticket.title,
                "description": ticket.description,
                "category": ticket.category.value.lower() if ticket.category and hasattr(ticket.category, 'value') else (str(ticket.category).lower() if ticket.category else "general"),
                "subcategory": ticket.subcategory,
                "priority": ticket.priority.value.lower() if ticket.priority and hasattr(ticket.priority, 'value') else (str(ticket.priority).lower() if ticket.priority else "medium"), 
                "urgency": ticket.urgency.value.lower() if ticket.urgency and hasattr(ticket.urgency, 'value') else (str(ticket.urgency).lower() if ticket.urgency else "medium"),
                "status": ticket.status.value.lower() if hasattr(ticket.status, 'value') else str(ticket.status).lower(),
                "department": ticket.department,
                "source_channel": ticket.source_channel,
                "created_by": user_info,
                "assigned_to": None,  # No assignment for new AI tickets
                "resolution_summary": ticket.resolution_summary,
                "internal_notes": ticket.internal_notes,
                "custom_fields": {},
                "first_response_at": ticket.first_response_at,
                "resolved_at": ticket.resolved_at,
                "closed_at": ticket.closed_at,
                "last_activity_at": ticket.last_activity_at or ticket.created_at,
                "communication_count": ticket.communication_count or 0,
                "resolution_time_minutes": ticket.resolution_time_minutes,
                "resolution_time_hours": ticket.resolution_time_minutes / 60.0 if ticket.resolution_time_minutes else None,
                "sla_due_date": ticket.sla_due_date,
                "sla_breached": ticket.sla_breached or False,
                "created_at": ticket.created_at,
                "updated_at": ticket.updated_at,
                "can_be_closed": ticket.status.value.lower() not in ['closed', 'cancelled'] if hasattr(ticket.status, 'value') else True,
                # Computed fields required by schema
                "escalation_level": ticket.escalation_level or 0,
                "is_overdue": ticket.sla_due_date and ticket.sla_due_date < datetime.now(timezone.utc) if ticket.sla_due_date else False,
                "is_high_priority": ticket.priority.value.lower() in ['high', 'critical'] if ticket.priority and hasattr(ticket.priority, 'value') else False,
                "age_in_hours": (datetime.now(timezone.utc) - ticket.created_at).total_seconds() / 3600.0
            }
            
            # Format AI analysis
            ai_analysis = {
                "confidence_score": ai_result.confidence_score,
                "reasoning": getattr(ai_result, 'reasoning', 'AI analysis completed'),
                "tags": getattr(ai_result, 'tags', []),
                "keywords": [],
                "similar_patterns": [],
                "sentiment": "neutral", 
                "business_impact": getattr(ai_result, 'business_impact', 'medium')
            }
            
            # Final response structure
            result = {
                "ticket": ticket_data_response,
                "ai_analysis": ai_analysis,
                "confidence_score": ai_result.confidence_score,
                "suggested_actions": getattr(ai_result, 'next_actions', []),
                "file_analysis_summary": getattr(ai_result, 'file_analysis_summary', None)
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