#!/usr/bin/env python3
"""
Celery tasks for AI-powered operations
"""

import asyncio
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime, timezone

from celery import current_app as celery_app
from celery.utils.log import get_task_logger

from app.database import get_db_session
from app.services.ai_service import AIService
from app.services.ticket_service import TicketService

# Get logger
logger = get_task_logger(__name__)


@celery_app.task(bind=True, retry_backoff=True, max_retries=3)
def create_ticket_with_ai(self, user_input: str, user_id: str, context: Dict[str, Any] = None):
    """
    Create ticket using AI analysis of user input
    
    Args:
        user_input: User's natural language description
        user_id: UUID of the user creating the ticket
        context: Additional context like uploaded files, conversation history
    """
    logger.info(f"Creating ticket with AI for user: {user_id}")
    
    try:
        result = asyncio.run(_create_ticket_with_ai_async(user_input, user_id, context))
        logger.info(f"AI ticket creation completed for user: {user_id}")
        return result
        
    except Exception as exc:
        logger.error(f"AI ticket creation failed for user: {user_id}, error: {str(exc)}")
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True, retry_backoff=True, max_retries=2)
def categorize_ticket(self, ticket_id: str):
    """
    Categorize ticket using AI analysis
    
    Args:
        ticket_id: UUID of the ticket to categorize
    """
    logger.info(f"Categorizing ticket: {ticket_id}")
    
    try:
        result = asyncio.run(_categorize_ticket_async(ticket_id))
        logger.info(f"Ticket categorization completed: {ticket_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Ticket categorization failed: {ticket_id}, error: {str(exc)}")
        self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


@celery_app.task(bind=True, retry_backoff=True, max_retries=2)
def suggest_ticket_resolution(self, ticket_id: str):
    """
    Generate AI-powered resolution suggestions for ticket
    
    Args:
        ticket_id: UUID of the ticket
    """
    logger.info(f"Generating resolution suggestions for ticket: {ticket_id}")
    
    try:
        result = asyncio.run(_suggest_resolution_async(ticket_id))
        logger.info(f"Resolution suggestions generated for ticket: {ticket_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Resolution suggestion failed for ticket: {ticket_id}, error: {str(exc)}")
        self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


@celery_app.task(bind=True)
def analyze_sentiment_batch(self, ticket_ids: List[str]):
    """
    Analyze sentiment for multiple tickets in batch
    
    Args:
        ticket_ids: List of ticket UUIDs to analyze
    """
    logger.info(f"Analyzing sentiment for {len(ticket_ids)} tickets")
    
    try:
        result = asyncio.run(_analyze_sentiment_batch_async(ticket_ids))
        logger.info(f"Sentiment analysis completed for {len(ticket_ids)} tickets")
        return result
        
    except Exception as exc:
        logger.error(f"Batch sentiment analysis failed, error: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True)
def generate_ticket_summary(self, ticket_id: str):
    """
    Generate AI summary of ticket conversation
    
    Args:
        ticket_id: UUID of the ticket
    """
    logger.info(f"Generating summary for ticket: {ticket_id}")
    
    try:
        result = asyncio.run(_generate_summary_async(ticket_id))
        logger.info(f"Summary generated for ticket: {ticket_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Summary generation failed for ticket: {ticket_id}, error: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True)
def extract_entities_from_ticket(self, ticket_id: str):
    """
    Extract entities (people, places, products, etc.) from ticket content
    
    Args:
        ticket_id: UUID of the ticket
    """
    logger.info(f"Extracting entities from ticket: {ticket_id}")
    
    try:
        result = asyncio.run(_extract_entities_async(ticket_id))
        logger.info(f"Entity extraction completed for ticket: {ticket_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Entity extraction failed for ticket: {ticket_id}, error: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True)
def auto_assign_ticket(self, ticket_id: str):
    """
    Automatically assign ticket to appropriate agent based on AI analysis
    
    Args:
        ticket_id: UUID of the ticket
    """
    logger.info(f"Auto-assigning ticket: {ticket_id}")
    
    try:
        result = asyncio.run(_auto_assign_ticket_async(ticket_id))
        logger.info(f"Auto-assignment completed for ticket: {ticket_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Auto-assignment failed for ticket: {ticket_id}, error: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True)
def detect_duplicate_tickets(self, ticket_id: str):
    """
    Detect potential duplicate tickets using AI similarity analysis
    
    Args:
        ticket_id: UUID of the ticket to check for duplicates
    """
    logger.info(f"Detecting duplicates for ticket: {ticket_id}")
    
    try:
        result = asyncio.run(_detect_duplicates_async(ticket_id))
        logger.info(f"Duplicate detection completed for ticket: {ticket_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Duplicate detection failed for ticket: {ticket_id}, error: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True)
def generate_response_suggestions(self, ticket_id: str, agent_id: str):
    """
    Generate AI-powered response suggestions for agents
    
    Args:
        ticket_id: UUID of the ticket
        agent_id: UUID of the agent who needs suggestions
    """
    logger.info(f"Generating response suggestions for ticket: {ticket_id}, agent: {agent_id}")
    
    try:
        result = asyncio.run(_generate_response_suggestions_async(ticket_id, agent_id))
        logger.info(f"Response suggestions generated for ticket: {ticket_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Response suggestion failed for ticket: {ticket_id}, error: {str(exc)}")
        return {"error": str(exc)}


# Async helper functions
async def _create_ticket_with_ai_async(user_input: str, user_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create ticket with AI asynchronously"""
    async with get_db_session() as db:
        ai_service = AIService()
        
        # Extract uploaded file IDs from context
        uploaded_files = []
        if context and "uploaded_files" in context:
            uploaded_files = [UUID(file_id) for file_id in context["uploaded_files"]]
        
        # Extract conversation context
        conversation_context = []
        if context and "conversation" in context:
            conversation_context = context["conversation"]
        
        # Create ticket using AI
        result = await ai_service.create_ticket_with_ai(
            db,
            user_input,
            uploaded_files,
            conversation_context
        )
        
        return result


async def _categorize_ticket_async(ticket_id: str) -> Dict[str, Any]:
    """Categorize ticket asynchronously"""
    async with get_db_session() as db:
        ticket_service = TicketService()
        ai_service = AIService()
        
        # Get ticket
        db_ticket = await ticket_service.get_ticket(db, UUID(ticket_id))
        if not db_ticket:
            raise ValueError(f"Ticket not found: {ticket_id}")
        
        # Analyze and categorize
        category_result = await ai_service.categorize_ticket(
            db,
            UUID(ticket_id),
            db_ticket.title,
            db_ticket.description
        )
        
        return {
            "ticket_id": ticket_id,
            "category": category_result.get("category"),
            "confidence": category_result.get("confidence"),
            "reasoning": category_result.get("reasoning")
        }


async def _suggest_resolution_async(ticket_id: str) -> Dict[str, Any]:
    """Generate resolution suggestions asynchronously"""
    async with get_db_session() as db:
        ticket_service = TicketService()
        ai_service = AIService()
        
        # Get ticket with conversation history
        db_ticket = await ticket_service.get_ticket(db, UUID(ticket_id), include_messages=True)
        if not db_ticket:
            raise ValueError(f"Ticket not found: {ticket_id}")
        
        # Generate suggestions
        suggestions = await ai_service.suggest_resolution(
            db,
            UUID(ticket_id),
            db_ticket.title,
            db_ticket.description,
            getattr(db_ticket, 'messages', [])
        )
        
        return {
            "ticket_id": ticket_id,
            "suggestions": suggestions
        }


async def _analyze_sentiment_batch_async(ticket_ids: List[str]) -> Dict[str, Any]:
    """Analyze sentiment for multiple tickets"""
    async with get_db_session() as db:
        ticket_service = TicketService()
        results = []
        
        for ticket_id in ticket_ids:
            try:
                db_ticket = await ticket_service.get_ticket(db, UUID(ticket_id))
                if not db_ticket:
                    continue
                
                # Analyze sentiment (mock implementation)
                sentiment_score = 0.5  # TODO: Implement real sentiment analysis
                sentiment_label = "neutral"
                
                # Update ticket with sentiment
                if not db_ticket.ai_analysis:
                    db_ticket.ai_analysis = {}
                
                db_ticket.ai_analysis["sentiment"] = {
                    "score": sentiment_score,
                    "label": sentiment_label,
                    "analyzed_at": datetime.now(timezone.utc).isoformat()
                }
                
                results.append({
                    "ticket_id": ticket_id,
                    "sentiment": sentiment_label,
                    "score": sentiment_score
                })
                
            except Exception as e:
                logger.error(f"Failed to analyze sentiment for ticket {ticket_id}: {str(e)}")
                continue
        
        await db.commit()
        
        return {
            "analyzed": len(results),
            "results": results
        }


async def _generate_summary_async(ticket_id: str) -> Dict[str, Any]:
    """Generate ticket summary asynchronously"""
    async with get_db_session() as db:
        ticket_service = TicketService()
        
        # Get ticket with full context
        db_ticket = await ticket_service.get_ticket(db, UUID(ticket_id), include_messages=True)
        if not db_ticket:
            raise ValueError(f"Ticket not found: {ticket_id}")
        
        # Generate summary (mock implementation)
        summary = f"Summary for ticket: {db_ticket.title}"
        if hasattr(db_ticket, 'messages') and db_ticket.messages:
            summary += f" with {len(db_ticket.messages)} messages"
        
        # Update ticket with summary
        if not db_ticket.ai_analysis:
            db_ticket.ai_analysis = {}
        
        db_ticket.ai_analysis["summary"] = {
            "text": summary,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.commit()
        
        return {
            "ticket_id": ticket_id,
            "summary": summary
        }


async def _extract_entities_async(ticket_id: str) -> Dict[str, Any]:
    """Extract entities from ticket asynchronously"""
    async with get_db_session() as db:
        ticket_service = TicketService()
        
        # Get ticket
        db_ticket = await ticket_service.get_ticket(db, UUID(ticket_id))
        if not db_ticket:
            raise ValueError(f"Ticket not found: {ticket_id}")
        
        # Extract entities (mock implementation)
        entities = [
            {"type": "PRODUCT", "text": "Example Product", "confidence": 0.9},
            {"type": "PERSON", "text": "John Doe", "confidence": 0.8}
        ]
        
        # Update ticket with entities
        if not db_ticket.ai_analysis:
            db_ticket.ai_analysis = {}
        
        db_ticket.ai_analysis["entities"] = {
            "extracted": entities,
            "extracted_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.commit()
        
        return {
            "ticket_id": ticket_id,
            "entities": entities
        }


async def _auto_assign_ticket_async(ticket_id: str) -> Dict[str, Any]:
    """Auto-assign ticket asynchronously"""
    async with get_db_session() as db:
        ticket_service = TicketService()
        
        # Get ticket
        db_ticket = await ticket_service.get_ticket(db, UUID(ticket_id))
        if not db_ticket:
            raise ValueError(f"Ticket not found: {ticket_id}")
        
        # Auto-assign logic (mock implementation)
        # In a real implementation, this would analyze ticket content,
        # agent expertise, workload, etc.
        suggested_agent_id = None  # Would be determined by AI
        
        assignment_reason = "Auto-assigned based on category and agent availability"
        
        return {
            "ticket_id": ticket_id,
            "suggested_agent": suggested_agent_id,
            "reason": assignment_reason
        }


async def _detect_duplicates_async(ticket_id: str) -> Dict[str, Any]:
    """Detect duplicate tickets asynchronously"""
    async with get_db_session() as db:
        ticket_service = TicketService()
        
        # Get current ticket
        db_ticket = await ticket_service.get_ticket(db, UUID(ticket_id))
        if not db_ticket:
            raise ValueError(f"Ticket not found: {ticket_id}")
        
        # Find similar tickets (mock implementation)
        # In reality, this would use AI similarity matching
        similar_tickets = []
        
        return {
            "ticket_id": ticket_id,
            "duplicates_found": len(similar_tickets),
            "similar_tickets": similar_tickets
        }


async def _generate_response_suggestions_async(ticket_id: str, agent_id: str) -> Dict[str, Any]:
    """Generate response suggestions asynchronously"""
    async with get_db_session() as db:
        ticket_service = TicketService()
        
        # Get ticket with context
        db_ticket = await ticket_service.get_ticket(db, UUID(ticket_id), include_messages=True)
        if not db_ticket:
            raise ValueError(f"Ticket not found: {ticket_id}")
        
        # Generate suggestions (mock implementation)
        suggestions = [
            {
                "type": "empathy",
                "text": "I understand your frustration with this issue.",
                "confidence": 0.9
            },
            {
                "type": "solution",
                "text": "Let me help you resolve this step by step.",
                "confidence": 0.8
            },
            {
                "type": "followup",
                "text": "Is there anything else I can help you with?",
                "confidence": 0.7
            }
        ]
        
        return {
            "ticket_id": ticket_id,
            "agent_id": agent_id,
            "suggestions": suggestions
        }