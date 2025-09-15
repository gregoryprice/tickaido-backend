#!/usr/bin/env python3
"""
Clerk webhook handlers for real-time user and organization synchronization
"""

import logging
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db_session
from app.models.user import User
from app.models.organization import Organization
from app.models.organization_invitation import OrganizationRole
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/clerk", tags=["Clerk Webhooks"])


async def verify_webhook_signature(request: Request) -> bool:
    """Verify Clerk webhook signature using svix headers"""
    try:
        # Get webhook secret from settings
        settings = get_settings()
        webhook_secret = getattr(settings, 'clerk_webhook_secret', None)
        
        if not webhook_secret:
            logger.warning("CLERK_WEBHOOK_SECRET not configured - webhook signature verification disabled")
            return True  # Allow webhooks in development
        
        # Get Svix signature headers
        signature = request.headers.get('svix-signature')
        timestamp = request.headers.get('svix-timestamp') 
        
        if not signature or not timestamp:
            logger.warning("Missing webhook signature headers")
            return False
        
        # Get request body
        body = await request.body()
        
        # Verify signature (simplified - in production use proper Svix verification)
        expected_signature = hmac.new(
            webhook_secret.encode(),
            f"{timestamp}.{body.decode()}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Extract signature from header (format: v1,signature)
        sig_parts = signature.split(',')
        actual_signature = None
        for part in sig_parts:
            if part.startswith('v1='):
                actual_signature = part[3:]
                break
        
        if not actual_signature:
            return False
        
        return hmac.compare_digest(expected_signature, actual_signature)
        
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        return False


@router.post("/events")
async def handle_clerk_events(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Handle all Clerk events (user and organization events)"""
    
    # Verify webhook signature
    if not await verify_webhook_signature(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse webhook payload
    payload = await request.json()
    event_type = payload.get('type')
    event_data = payload.get('data')
    
    logger.info(f"Received Clerk webhook: {event_type}")
    
    try:
        # Route events based on type
        if event_type.startswith('user.'):
            await _handle_user_event(db, event_type, event_data)
        elif event_type.startswith('session.'):
            await _handle_session_event(db, event_type, event_data)
        elif event_type.startswith('organization.'):
            await _handle_organization_event(db, event_type, event_data)
        elif event_type.startswith('organizationMembership.'):
            await _handle_membership_event(db, event_type, event_data)
        elif event_type.startswith('organizationInvitation.'):
            await _handle_invitation_event(db, event_type, event_data)
        else:
            logger.info(f"Unhandled Clerk event type: {event_type}")
        
        return {"status": "success", "event_type": event_type}
    
    except Exception as e:
        logger.error(f"Clerk webhook processing failed for {event_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed for event: {event_type}"
        )


# Event routing functions
async def _handle_user_event(db: AsyncSession, event_type: str, user_data: Dict[str, Any]):
    """Route user events to appropriate handlers"""
    if event_type == 'user.created':
        await handle_user_created(db, user_data)
    elif event_type == 'user.updated':
        await handle_user_updated(db, user_data)
    elif event_type == 'user.deleted':
        await handle_user_deleted(db, user_data)
    else:
        logger.warning(f"Unhandled user event: {event_type}")


async def _handle_session_event(db: AsyncSession, event_type: str, session_data: Dict[str, Any]):
    """Route session events to appropriate handlers"""
    if event_type == 'session.created':
        await handle_session_created(db, session_data)
    elif event_type == 'session.ended':
        await handle_session_ended(db, session_data)
    else:
        logger.warning(f"Unhandled session event: {event_type}")


async def _handle_organization_event(db: AsyncSession, event_type: str, org_data: Dict[str, Any]):
    """Route organization events to appropriate handlers"""
    if event_type == 'organization.created':
        await handle_organization_created(db, org_data)
    elif event_type == 'organization.updated':
        await handle_organization_updated(db, org_data)
    elif event_type == 'organization.deleted':
        await handle_organization_deleted(db, org_data)
    else:
        logger.warning(f"Unhandled organization event: {event_type}")


async def _handle_membership_event(db: AsyncSession, event_type: str, membership_data: Dict[str, Any]):
    """Route membership events to appropriate handlers"""
    if event_type == 'organizationMembership.created':
        await handle_membership_created(db, membership_data)
    elif event_type == 'organizationMembership.updated':
        await handle_membership_updated(db, membership_data)
    elif event_type == 'organizationMembership.deleted':
        await handle_membership_deleted(db, membership_data)
    else:
        logger.warning(f"Unhandled membership event: {event_type}")


async def _handle_invitation_event(db: AsyncSession, event_type: str, invitation_data: Dict[str, Any]):
    """Route invitation events to appropriate handlers"""
    if event_type == 'organizationInvitation.created':
        await handle_invitation_created(db, invitation_data)
    elif event_type == 'organizationInvitation.accepted':
        await handle_invitation_accepted(db, invitation_data)
    elif event_type == 'organizationInvitation.revoked':
        await handle_invitation_revoked(db, invitation_data)
    else:
        logger.warning(f"Unhandled invitation event: {event_type}")


# User event handlers
async def handle_user_created(db: AsyncSession, user_data: Dict[str, Any]):
    """Handle user creation from Clerk"""
    
    clerk_id = user_data.get('id')
    email_addresses = user_data.get('email_addresses', [])
    email = email_addresses[0].get('email_address') if email_addresses else None
    
    if not email:
        logger.warning(f"User created webhook missing email: {clerk_id}")
        return
    
    # Check if user already exists
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    existing_user = result.scalar_one_or_none()
    
    if not existing_user:
        new_user = User(
            clerk_id=clerk_id,
            email=email,
            full_name=f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
            avatar_url=user_data.get('image_url'),
            is_verified=True,
            is_active=True,
            external_auth_provider='clerk',
            external_auth_id=clerk_id,
            password_hash=None
        )
        db.add(new_user)
        await db.commit()
        logger.info(f"Created user from Clerk webhook: {email}")


async def handle_user_updated(db: AsyncSession, user_data: Dict[str, Any]):
    """Handle user updates from Clerk"""
    
    clerk_id = user_data.get('id')
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    
    if user:
        # Update user data
        email_addresses = user_data.get('email_addresses', [])
        email = email_addresses[0].get('email_address') if email_addresses else user.email
        
        user.email = email
        user.full_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
        if user_data.get('image_url'):
            user.avatar_url = user_data.get('image_url')
        
        await db.commit()
        logger.info(f"Updated user from Clerk webhook: {email}")


async def handle_user_deleted(db: AsyncSession, user_data: Dict[str, Any]):
    """Handle user deletion from Clerk"""
    
    clerk_id = user_data.get('id')
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    
    if user:
        # Soft delete user
        user.is_active = False
        user.email = f"deleted-{user.id}@deleted.local"
        user.full_name = "Deleted User"
        
        await db.commit()
        logger.info(f"Soft deleted user from Clerk webhook: {clerk_id}")


async def handle_session_created(db: AsyncSession, session_data: Dict[str, Any]):
    """Handle session creation for audit logging"""
    user_id = session_data.get('user_id')
    logger.info(f"User session created: {user_id}")
    
    # Update user login tracking
    if user_id:
        result = await db.execute(select(User).where(User.clerk_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.record_login()
            await db.commit()


async def handle_session_ended(db: AsyncSession, session_data: Dict[str, Any]):
    """Handle session end for audit logging"""
    user_id = session_data.get('user_id')
    logger.info(f"User session ended: {user_id}")


# Organization event handlers
async def handle_organization_created(db: AsyncSession, org_data: Dict[str, Any]):
    """Sync organization creation from Clerk"""
    
    clerk_org_id = org_data.get('id')
    
    # Check if organization already exists
    result = await db.execute(
        select(Organization).where(Organization.clerk_organization_id == clerk_org_id)
    )
    existing_org = result.scalar_one_or_none()
    
    if not existing_org:
        new_org = Organization(
            clerk_organization_id=clerk_org_id,
            name=org_data.get('name'),
            display_name=org_data.get('name'),
            clerk_metadata=org_data,
            is_enabled=True
        )
        db.add(new_org)
        await db.commit()
        logger.info(f"Created organization from Clerk webhook: {org_data.get('name')}")


async def handle_organization_updated(db: AsyncSession, org_data: Dict[str, Any]):
    """Sync organization updates from Clerk"""
    
    clerk_org_id = org_data.get('id')
    result = await db.execute(
        select(Organization).where(Organization.clerk_organization_id == clerk_org_id)
    )
    org = result.scalar_one_or_none()
    
    if org:
        org.name = org_data.get('name', org.name)
        org.display_name = org_data.get('name', org.display_name)
        org.clerk_metadata = org_data
        
        await db.commit()
        logger.info(f"Updated organization from Clerk webhook: {org.name}")


async def handle_organization_deleted(db: AsyncSession, org_data: Dict[str, Any]):
    """Handle organization deletion from Clerk"""
    
    clerk_org_id = org_data.get('id')
    result = await db.execute(
        select(Organization).where(Organization.clerk_organization_id == clerk_org_id)
    )
    org = result.scalar_one_or_none()
    
    if org:
        org.is_enabled = False
        await db.commit()
        logger.info(f"Disabled organization from Clerk webhook: {org.name}")


async def handle_membership_created(db: AsyncSession, membership_data: Dict[str, Any]):
    """Sync organization membership creation from Clerk"""
    
    clerk_membership_id = membership_data.get('id')
    clerk_org_id = membership_data.get('organization', {}).get('id')
    clerk_user_id = membership_data.get('public_user_data', {}).get('user_id')
    role = membership_data.get('role', 'basic_member')
    
    # Map Clerk roles to our roles (simplified)
    role_mapping = {
        'admin': OrganizationRole.ADMIN,
        'basic_member': OrganizationRole.MEMBER
    }
    
    # Get local user and organization
    user_result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
    user = user_result.scalar_one_or_none()
    
    org_result = await db.execute(
        select(Organization).where(Organization.clerk_organization_id == clerk_org_id)
    )
    org = org_result.scalar_one_or_none()
    
    if user and org:
        # Update user's organization membership
        user.organization_id = org.id
        user.organization_role = role_mapping.get(role, OrganizationRole.MEMBER)
        user.joined_organization_at = datetime.now(timezone.utc)
        
        await db.commit()
        logger.info(f"Updated membership: {user.email} -> {org.name} as {role}")


async def handle_membership_updated(db: AsyncSession, membership_data: Dict[str, Any]):
    """Handle membership role updates from Clerk"""
    
    clerk_user_id = membership_data.get('public_user_data', {}).get('user_id')
    role = membership_data.get('role', 'basic_member')
    
    role_mapping = {
        'admin': OrganizationRole.ADMIN,
        'basic_member': OrganizationRole.MEMBER
    }
    
    # Update user role
    user_result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
    user = user_result.scalar_one_or_none()
    
    if user:
        user.organization_role = role_mapping.get(role, OrganizationRole.MEMBER)
        await db.commit()
        logger.info(f"Updated user role: {user.email} -> {role}")


async def handle_membership_deleted(db: AsyncSession, membership_data: Dict[str, Any]):
    """Handle membership removal from Clerk"""
    
    clerk_user_id = membership_data.get('public_user_data', {}).get('user_id')
    
    # Remove user from organization
    user_result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
    user = user_result.scalar_one_or_none()
    
    if user:
        user.leave_organization()
        await db.commit()
        logger.info(f"Removed user from organization: {user.email}")


# Invitation event handlers
async def handle_invitation_created(db: AsyncSession, invitation_data: Dict[str, Any]):
    """Handle invitation creation from Clerk"""
    logger.info(f"Organization invitation created: {invitation_data.get('email_address')}")


async def handle_invitation_accepted(db: AsyncSession, invitation_data: Dict[str, Any]):
    """Handle invitation acceptance from Clerk"""
    logger.info(f"Organization invitation accepted: {invitation_data.get('email_address')}")


async def handle_invitation_revoked(db: AsyncSession, invitation_data: Dict[str, Any]):
    """Handle invitation revocation from Clerk"""
    logger.info(f"Organization invitation revoked: {invitation_data.get('email_address')}")