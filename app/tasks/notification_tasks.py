#!/usr/bin/env python3
"""
Celery tasks for notifications and communications
"""

import asyncio
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone

from celery import current_app as celery_app
from celery.utils.log import get_task_logger
from sqlalchemy import select, and_

from app.database import get_db_session
from app.models.ticket import DBTicket
from app.models.user import DBUser
from app.services.ticket_service import TicketService
from app.services.user_service import UserService

# Get logger
logger = get_task_logger(__name__)


@celery_app.task(bind=True, retry_backoff=True, max_retries=3)
def send_email_notification(self, recipient_email: str, subject: str, body: str, template: str = None):
    """
    Send email notification
    
    Args:
        recipient_email: Email address to send to
        subject: Email subject
        body: Email body content
        template: Optional email template name
    """
    logger.info(f"Sending email to: {recipient_email}")
    
    try:
        result = asyncio.run(_send_email_async(recipient_email, subject, body, template))
        logger.info(f"Email sent to: {recipient_email}")
        return result
        
    except Exception as exc:
        logger.error(f"Email failed for: {recipient_email}, error: {str(exc)}")
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True, retry_backoff=True, max_retries=2)
def send_slack_notification(self, channel: str, message: str, attachments: List[Dict] = None):
    """
    Send Slack notification
    
    Args:
        channel: Slack channel or user ID
        message: Message content
        attachments: Optional message attachments
    """
    logger.info(f"Sending Slack message to: {channel}")
    
    try:
        result = asyncio.run(_send_slack_async(channel, message, attachments))
        logger.info(f"Slack message sent to: {channel}")
        return result
        
    except Exception as exc:
        logger.error(f"Slack notification failed for: {channel}, error: {str(exc)}")
        self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


@celery_app.task(bind=True, retry_backoff=True, max_retries=2)
def send_teams_notification(self, webhook_url: str, message: str, card_data: Dict = None):
    """
    Send Microsoft Teams notification
    
    Args:
        webhook_url: Teams webhook URL
        message: Message content
        card_data: Optional adaptive card data
    """
    logger.info(f"Sending Teams notification")
    
    try:
        result = asyncio.run(_send_teams_async(webhook_url, message, card_data))
        logger.info(f"Teams notification sent")
        return result
        
    except Exception as exc:
        logger.error(f"Teams notification failed, error: {str(exc)}")
        self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


@celery_app.task(bind=True)
def notify_ticket_created(self, ticket_id: str):
    """
    Send notifications when a new ticket is created
    
    Args:
        ticket_id: UUID of the created ticket
    """
    logger.info(f"Sending ticket creation notifications for: {ticket_id}")
    
    try:
        result = asyncio.run(_notify_ticket_created_async(ticket_id))
        logger.info(f"Ticket creation notifications sent for: {ticket_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Ticket creation notifications failed for: {ticket_id}, error: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True)
def notify_ticket_updated(self, ticket_id: str, update_type: str, updated_by: str):
    """
    Send notifications when a ticket is updated
    
    Args:
        ticket_id: UUID of the updated ticket
        update_type: Type of update (status, assignment, comment, etc.)
        updated_by: UUID of user who made the update
    """
    logger.info(f"Sending ticket update notifications for: {ticket_id}, type: {update_type}")
    
    try:
        result = asyncio.run(_notify_ticket_updated_async(ticket_id, update_type, updated_by))
        logger.info(f"Ticket update notifications sent for: {ticket_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Ticket update notifications failed for: {ticket_id}, error: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True)
def notify_sla_breach(self, ticket_id: str, sla_type: str):
    """
    Send notifications for SLA breaches
    
    Args:
        ticket_id: UUID of the ticket
        sla_type: Type of SLA (response_time, resolution_time)
    """
    logger.info(f"Sending SLA breach notification for ticket: {ticket_id}, type: {sla_type}")
    
    try:
        result = asyncio.run(_notify_sla_breach_async(ticket_id, sla_type))
        logger.info(f"SLA breach notification sent for: {ticket_id}")
        return result
        
    except Exception as exc:
        logger.error(f"SLA breach notification failed for: {ticket_id}, error: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True)
def send_daily_digest(self, user_id: str):
    """
    Send daily digest email to user
    
    Args:
        user_id: UUID of the user
    """
    logger.info(f"Sending daily digest for user: {user_id}")
    
    try:
        result = asyncio.run(_send_daily_digest_async(user_id))
        logger.info(f"Daily digest sent for user: {user_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Daily digest failed for user: {user_id}, error: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True)
def send_bulk_notifications(self, notifications: List[Dict[str, Any]]):
    """
    Send multiple notifications in batch
    
    Args:
        notifications: List of notification configs
    """
    logger.info(f"Sending {len(notifications)} bulk notifications")
    
    try:
        result = asyncio.run(_send_bulk_notifications_async(notifications))
        logger.info(f"Bulk notifications completed: {result['sent']} sent, {result['failed']} failed")
        return result
        
    except Exception as exc:
        logger.error(f"Bulk notifications failed: {str(exc)}")
        return {"error": str(exc)}


@celery_app.task(bind=True)
def send_escalation_notice(self, ticket_id: str, escalation_level: int):
    """
    Send escalation notice for high priority tickets
    
    Args:
        ticket_id: UUID of the ticket
        escalation_level: Level of escalation (1-5)
    """
    logger.info(f"Sending escalation notice for ticket: {ticket_id}, level: {escalation_level}")
    
    try:
        result = asyncio.run(_send_escalation_notice_async(ticket_id, escalation_level))
        logger.info(f"Escalation notice sent for: {ticket_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Escalation notice failed for: {ticket_id}, error: {str(exc)}")
        return {"error": str(exc)}


# Async helper functions
async def _send_email_async(recipient_email: str, subject: str, body: str, template: str = None) -> Dict[str, Any]:
    """Send email asynchronously"""
    # TODO: Implement actual email sending using aiosmtplib or similar
    # This would involve:
    # 1. Loading email template if provided
    # 2. Rendering template with variables
    # 3. Sending via SMTP server
    
    return {
        "recipient": recipient_email,
        "subject": subject,
        "status": "sent",
        "sent_at": datetime.now(timezone.utc).isoformat()
    }


async def _send_slack_async(channel: str, message: str, attachments: List[Dict] = None) -> Dict[str, Any]:
    """Send Slack message asynchronously"""
    # TODO: Implement actual Slack API integration
    # This would use the Slack Web API to send messages
    
    return {
        "channel": channel,
        "message": message,
        "status": "sent",
        "sent_at": datetime.now(timezone.utc).isoformat()
    }


async def _send_teams_async(webhook_url: str, message: str, card_data: Dict = None) -> Dict[str, Any]:
    """Send Teams notification asynchronously"""
    # TODO: Implement actual Teams webhook integration
    # This would POST to the Teams webhook URL
    
    return {
        "webhook": webhook_url,
        "message": message,
        "status": "sent",
        "sent_at": datetime.now(timezone.utc).isoformat()
    }


async def _notify_ticket_created_async(ticket_id: str) -> Dict[str, Any]:
    """Send ticket creation notifications"""
    async with get_db_session() as db:
        ticket_service = TicketService()
        user_service = UserService()
        
        # Get ticket with creator info
        db_ticket = await ticket_service.get_ticket(db, UUID(ticket_id), include_user=True)
        if not db_ticket:
            raise ValueError(f"Ticket not found: {ticket_id}")
        
        notifications_sent = []
        
        # Notify ticket creator
        if hasattr(db_ticket, 'created_by_user') and db_ticket.created_by_user:
            creator_email = db_ticket.created_by_user.email
            subject = f"Ticket Created: {db_ticket.title}"
            body = f"Your ticket '{db_ticket.title}' has been created and assigned ID #{db_ticket.id}."
            
            # Queue email notification
            send_email_notification.delay(creator_email, subject, body, "ticket_created")
            notifications_sent.append({"type": "email", "recipient": creator_email})
        
        # Notify assigned agent (if any)
        if db_ticket.assigned_to:
            assigned_user = await user_service.get_user(db, db_ticket.assigned_to)
            if assigned_user:
                subject = f"Ticket Assigned: {db_ticket.title}"
                body = f"You have been assigned ticket '{db_ticket.title}' (ID: #{db_ticket.id})."
                
                send_email_notification.delay(assigned_user.email, subject, body, "ticket_assigned")
                notifications_sent.append({"type": "email", "recipient": assigned_user.email})
        
        # TODO: Send Slack/Teams notifications based on configuration
        
        return {
            "ticket_id": ticket_id,
            "notifications_sent": len(notifications_sent),
            "details": notifications_sent
        }


async def _notify_ticket_updated_async(ticket_id: str, update_type: str, updated_by: str) -> Dict[str, Any]:
    """Send ticket update notifications"""
    async with get_db_session() as db:
        ticket_service = TicketService()
        user_service = UserService()
        
        # Get ticket and updater info
        db_ticket = await ticket_service.get_ticket(db, UUID(ticket_id), include_user=True)
        if not db_ticket:
            raise ValueError(f"Ticket not found: {ticket_id}")
        
        updater = await user_service.get_user(db, UUID(updated_by))
        if not updater:
            raise ValueError(f"User not found: {updated_by}")
        
        notifications_sent = []
        
        # Notify ticket creator (if different from updater)
        if (hasattr(db_ticket, 'created_by_user') and 
            db_ticket.created_by_user and 
            str(db_ticket.created_by) != updated_by):
            
            creator_email = db_ticket.created_by_user.email
            subject = f"Ticket Updated: {db_ticket.title}"
            body = f"Your ticket '{db_ticket.title}' has been updated by {updater.full_name}."
            
            send_email_notification.delay(creator_email, subject, body, "ticket_updated")
            notifications_sent.append({"type": "email", "recipient": creator_email})
        
        # Notify assigned agent (if different from updater)
        if db_ticket.assigned_to and str(db_ticket.assigned_to) != updated_by:
            assigned_user = await user_service.get_user(db, db_ticket.assigned_to)
            if assigned_user:
                subject = f"Assigned Ticket Updated: {db_ticket.title}"
                body = f"Ticket '{db_ticket.title}' assigned to you has been updated."
                
                send_email_notification.delay(assigned_user.email, subject, body, "ticket_updated")
                notifications_sent.append({"type": "email", "recipient": assigned_user.email})
        
        return {
            "ticket_id": ticket_id,
            "update_type": update_type,
            "notifications_sent": len(notifications_sent),
            "details": notifications_sent
        }


async def _notify_sla_breach_async(ticket_id: str, sla_type: str) -> Dict[str, Any]:
    """Send SLA breach notifications"""
    async with get_db_session() as db:
        ticket_service = TicketService()
        user_service = UserService()
        
        # Get ticket
        db_ticket = await ticket_service.get_ticket(db, UUID(ticket_id), include_user=True)
        if not db_ticket:
            raise ValueError(f"Ticket not found: {ticket_id}")
        
        notifications_sent = []
        
        # Notify assigned agent
        if db_ticket.assigned_to:
            assigned_user = await user_service.get_user(db, db_ticket.assigned_to)
            if assigned_user:
                subject = f"SLA BREACH: {db_ticket.title}"
                body = f"Ticket '{db_ticket.title}' has breached {sla_type} SLA. Immediate attention required."
                
                send_email_notification.delay(assigned_user.email, subject, body, "sla_breach")
                notifications_sent.append({"type": "email", "recipient": assigned_user.email})
        
        # TODO: Notify managers/escalation contacts
        
        return {
            "ticket_id": ticket_id,
            "sla_type": sla_type,
            "notifications_sent": len(notifications_sent),
            "details": notifications_sent
        }


async def _send_daily_digest_async(user_id: str) -> Dict[str, Any]:
    """Send daily digest to user"""
    async with get_db_session() as db:
        user_service = UserService()
        ticket_service = TicketService()
        
        # Get user
        db_user = await user_service.get_user(db, UUID(user_id))
        if not db_user:
            raise ValueError(f"User not found: {user_id}")
        
        # Get user's ticket statistics
        user_stats = await user_service.get_user_stats(db, UUID(user_id))
        
        # Create digest content
        subject = "Daily Ticket Digest"
        body = f"Hello {db_user.full_name},\n\nHere's your daily ticket summary:\n"
        body += f"Total tickets: {user_stats.get('total_tickets', 0)}\n"
        
        # Send digest
        send_email_notification.delay(db_user.email, subject, body, "daily_digest")
        
        return {
            "user_id": user_id,
            "digest_sent": True,
            "sent_at": datetime.now(timezone.utc).isoformat()
        }


async def _send_bulk_notifications_async(notifications: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Send bulk notifications"""
    sent_count = 0
    failed_count = 0
    
    for notification in notifications:
        try:
            notification_type = notification.get("type", "email")
            
            if notification_type == "email":
                send_email_notification.delay(
                    notification["recipient"],
                    notification["subject"],
                    notification["body"],
                    notification.get("template")
                )
            elif notification_type == "slack":
                send_slack_notification.delay(
                    notification["channel"],
                    notification["message"],
                    notification.get("attachments")
                )
            elif notification_type == "teams":
                send_teams_notification.delay(
                    notification["webhook_url"],
                    notification["message"],
                    notification.get("card_data")
                )
            
            sent_count += 1
            
        except Exception as e:
            logger.error(f"Failed to queue notification: {str(e)}")
            failed_count += 1
            continue
    
    return {
        "total": len(notifications),
        "sent": sent_count,
        "failed": failed_count
    }


async def _send_escalation_notice_async(ticket_id: str, escalation_level: int) -> Dict[str, Any]:
    """Send escalation notice"""
    async with get_db_session() as db:
        ticket_service = TicketService()
        
        # Get ticket
        db_ticket = await ticket_service.get_ticket(db, UUID(ticket_id), include_user=True)
        if not db_ticket:
            raise ValueError(f"Ticket not found: {ticket_id}")
        
        # TODO: Determine escalation recipients based on level and configuration
        escalation_recipients = ["manager@example.com"]  # Would be configuration-driven
        
        notifications_sent = []
        
        for recipient in escalation_recipients:
            subject = f"ESCALATION LEVEL {escalation_level}: {db_ticket.title}"
            body = f"Ticket '{db_ticket.title}' has been escalated to level {escalation_level}."
            
            send_email_notification.delay(recipient, subject, body, "escalation_notice")
            notifications_sent.append({"type": "email", "recipient": recipient})
        
        return {
            "ticket_id": ticket_id,
            "escalation_level": escalation_level,
            "notifications_sent": len(notifications_sent),
            "details": notifications_sent
        }