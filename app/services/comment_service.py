#!/usr/bin/env python3
"""
Comment Service for ticket comment management with generic integration platform support
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.integration import Integration
from app.models.ticket import Ticket
from app.models.ticket_comment import TicketComment
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


class CommentService:
    """Service for managing ticket comments with generic integration platform support"""
    
    async def create_comment(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        author_email: str,
        body: str,
        author_display_name: Optional[str] = None,
        is_internal: bool = False,
        integration_id: Optional[UUID] = None,
        user: Optional[User] = None
    ) -> TicketComment:
        """
        Create a new comment on a ticket with optional integration synchronization.
        
        Args:
            db: Database session
            ticket_id: ID of the parent ticket
            author_email: Email of the comment author
            body: Comment content (supports text and markdown)
            author_display_name: Display name of the comment author
            is_internal: Whether comment is internal-only
            integration_id: Optional integration platform to sync with
            user: Current user (for permissions and validation)
            
        Returns:
            Created TicketComment instance
            
        Raises:
            ValueError: If ticket not found or user lacks permission
        """
        # Verify ticket exists and user has permission
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await db.execute(stmt)
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        # Check permissions - users can comment on tickets in their organization
        if user and ticket.organization_id != user.organization_id:
            raise ValueError("You don't have permission to comment on this ticket")
        
        # If integration_id is provided, validate it exists and user has access
        integration = None
        if integration_id:
            integration_stmt = select(Integration).where(
                and_(
                    Integration.id == integration_id,
                    Integration.deleted_at.is_(None)
                )
            )
            integration_result = await db.execute(integration_stmt)
            integration = integration_result.scalar_one_or_none()
            
            if not integration:
                raise ValueError(f"Integration {integration_id} not found or not available")
            
            # Check if user has access to this integration
            if user and integration.organization_id != user.organization_id:
                raise ValueError("You don't have permission to use this integration")
        
        # Create comment using factory method
        comment = TicketComment.create_from_content(
            ticket_id=ticket_id,
            author_email=author_email,
            content=body,
            author_display_name=author_display_name,
            is_internal=is_internal,
            integration_id=integration_id
        )
        
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        
        # Update ticket's last activity timestamp
        ticket.last_activity_at = datetime.now(timezone.utc)
        ticket.increment_communication()
        await db.commit()
        
        # If integration is specified, sync comment with external platform
        if integration:
            try:
                await self._sync_comment_with_integration(db, comment, integration)
            except Exception as sync_error:
                logger.error(f"Failed to sync comment {comment.id} with integration {integration.platform_name}: {sync_error}")
                # Don't fail the comment creation if sync fails
        
        logger.info(f"Created comment {comment.id} on ticket {ticket_id} by {author_email}" + 
                   (f" with {integration.platform_name} sync" if integration else ""))
        
        return comment
    
    async def _sync_comment_with_integration(
        self,
        db: AsyncSession,
        comment: TicketComment,
        integration: Integration
    ):
        """
        Synchronize comment with external integration platform.
        
        Args:
            db: Database session
            comment: TicketComment instance to sync
            integration: Integration platform to sync with
        """
        try:
            from app.services.integration_service import IntegrationService
            
            integration_service = IntegrationService()
            
            # Get the integration implementation
            integration_impl = integration_service._get_integration_implementation(integration)
            
            # Convert markdown to platform-specific format
            if integration.platform_name.lower() == "jira":
                # Create comment in JIRA - ADF conversion is handled within the integration layer
                external_comment = await integration_impl.add_comment(
                    issue_key=comment.ticket.external_ticket_id,
                    comment_markdown=comment.body
                )
                
                # Update comment with external sync information
                comment.sync_with_integration(
                    integration_data={"platform": "jira", "converted_to_adf": True},
                    external_comment_id=external_comment.get("id"),
                    integration_id=str(integration.id)
                )
                
            # Add support for other platforms here (ServiceNow, Zendesk, etc.)
            
            await db.commit()
            logger.info(f"Successfully synced comment {comment.id} with {integration.platform_name}")
            
        except Exception as e:
            logger.error(f"Failed to sync comment with {integration.platform_name}: {e}")
            raise
    
    async def list_comments(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        page: int = 1,
        per_page: int = 10,
        include_internal: bool = False,
        user: Optional[User] = None
    ) -> Tuple[List[TicketComment], int]:
        """
        List comments for a ticket with pagination.
        
        Args:
            db: Database session
            ticket_id: ID of the parent ticket
            page: Page number (1-based)
            per_page: Number of comments per page
            include_internal: Whether to include internal comments
            user: Current user (for permissions)
            
        Returns:
            Tuple of (comments list, total count)
            
        Raises:
            ValueError: If ticket not found or user lacks permission
        """
        # Verify ticket exists and user has permission
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await db.execute(stmt)
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        # Check permissions
        if user and ticket.organization_id != user.organization_id:
            raise ValueError("You don't have permission to view comments on this ticket")
        
        # Build query filters
        filters = [TicketComment.ticket_id == ticket_id, TicketComment.deleted_at.is_(None)]
        
        # Only include internal comments for admin users or if explicitly requested
        if not include_internal or (user and user.role != UserRole.ADMIN):
            filters.append(TicketComment.is_internal == False)
        
        # Count total comments
        count_stmt = select(func.count(TicketComment.id)).where(and_(*filters))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0
        
        # Get paginated comments with integration data
        offset = (page - 1) * per_page
        stmt = (
            select(TicketComment)
            .options(selectinload(TicketComment.integration))
            .where(and_(*filters))
            .order_by(TicketComment.created_at.asc())
            .offset(offset)
            .limit(per_page)
        )
        
        result = await db.execute(stmt)
        comments = result.scalars().all()
        
        logger.debug(f"Listed {len(comments)}/{total} comments for ticket {ticket_id}, page {page}")
        
        return list(comments), total
    
    async def get_comment(
        self,
        db: AsyncSession,
        comment_id: UUID,
        user: Optional[User] = None
    ) -> TicketComment:
        """
        Get a single comment by ID.
        
        Args:
            db: Database session
            comment_id: ID of the comment
            user: Current user (for permissions)
            
        Returns:
            TicketComment instance
            
        Raises:
            ValueError: If comment not found or user lacks permission
        """
        stmt = (
            select(TicketComment)
            .options(selectinload(TicketComment.ticket), selectinload(TicketComment.integration))
            .where(TicketComment.id == comment_id, TicketComment.deleted_at.is_(None))
        )
        result = await db.execute(stmt)
        comment = result.scalar_one_or_none()
        
        if not comment:
            raise ValueError(f"Comment {comment_id} not found")
        
        # Check permissions
        if user and comment.ticket.organization_id != user.organization_id:
            raise ValueError("You don't have permission to view this comment")
        
        # Check internal comment visibility
        if comment.is_internal and user and user.role != UserRole.ADMIN:
            raise ValueError("You don't have permission to view internal comments")
        
        return comment
    
    async def update_comment(
        self,
        db: AsyncSession,
        comment_id: UUID,
        body: Optional[str] = None,
        is_internal: Optional[bool] = None,
        user: Optional[User] = None
    ) -> TicketComment:
        """
        Update an existing comment.
        
        Args:
            db: Database session
            comment_id: ID of the comment to update
            body: New content (supports text and markdown)
            is_internal: New internal flag value
            user: Current user (for permissions)
            
        Returns:
            Updated TicketComment instance
            
        Raises:
            ValueError: If comment not found
            PermissionError: If user lacks permission to update
        """
        comment = await self.get_comment(db, comment_id, user)
        
        # Check if user can update this comment
        # Users can update their own comments, admins can update any comment
        if user:
            if user.role != UserRole.ADMIN and comment.author_email != user.email:
                raise PermissionError("You can only update your own comments")
        
        # Update fields if provided
        if body is not None:
            comment.update_content(body)
        
        if is_internal is not None:
            comment.is_internal = is_internal
        
        comment.updated_at = datetime.now(timezone.utc)
        
        # If comment is synchronized with an integration, update external platform
        if comment.integration:
            try:
                await self._update_external_comment(db, comment)
            except Exception as sync_error:
                logger.error(f"Failed to update external comment for {comment.id}: {sync_error}")
                # Don't fail the local update if external sync fails
        
        await db.commit()
        await db.refresh(comment)
        
        logger.info(f"Updated comment {comment_id} by {user.email if user else 'system'}")
        
        return comment
    
    async def _update_external_comment(
        self,
        db: AsyncSession,
        comment: TicketComment
    ):
        """
        Update comment in external integration platform.
        
        Args:
            db: Database session
            comment: TicketComment instance to update externally
        """
        if not comment.integration or not comment.external_comment_id:
            return
        
        try:
            from app.services.integration_service import IntegrationService
            
            integration_service = IntegrationService()
            integration_impl = integration_service._get_integration_implementation(comment.integration)
            
            # Get the ticket to get external_ticket_id
            if not comment.ticket.external_ticket_id:
                logger.warning(f"Cannot update external comment - ticket {comment.ticket_id} has no external_ticket_id")
                return
            
            # Platform-specific update logic
            if comment.integration.platform_name.lower() == "jira":
                # Update comment in JIRA
                await integration_impl.update_comment(
                    issue_key=comment.ticket.external_ticket_id,
                    comment_id=comment.external_comment_id,
                    comment_markdown=comment.body
                )
                
                # Update local sync status
                comment.sync_with_integration(
                    integration_data={"platform": "jira", "action": "updated"},
                    external_comment_id=comment.external_comment_id,
                    integration_id=str(comment.integration.id)
                )
                
                logger.info(f"✅ Updated external comment {comment.external_comment_id} in {comment.integration.platform_name}")
            
            # Add support for other platforms here (ServiceNow, Zendesk, etc.)
            else:
                logger.warning(f"External comment update not implemented for platform: {comment.integration.platform_name}")
            
        except Exception as e:
            logger.error(f"Failed to update external comment: {e}")
            raise
    
    async def delete_comment(
        self,
        db: AsyncSession,
        comment_id: UUID,
        user: Optional[User] = None
    ):
        """
        Delete a comment (soft delete) and synchronize with external integration if applicable.
        
        Args:
            db: Database session
            comment_id: ID of the comment to delete
            user: Current user (for permissions)
            
        Raises:
            ValueError: If comment not found
            PermissionError: If user lacks permission to delete
        """
        comment = await self.get_comment(db, comment_id, user)
        
        # Check if user can delete this comment
        # Users can delete their own comments, admins can delete any comment
        if user:
            if user.role != UserRole.ADMIN and comment.author_email != user.email:
                raise PermissionError("You can only delete your own comments")
        
        # If comment is synchronized with an integration, delete from external platform first
        if comment.integration and comment.external_comment_id:
            try:
                await self._delete_external_comment(db, comment)
            except Exception as sync_error:
                logger.error(f"Failed to delete external comment for {comment.id}: {sync_error}")
                # Don't fail the local delete if external sync fails
        
        # Soft delete the comment
        comment.soft_delete()
        await db.commit()
        
        logger.info(f"Deleted comment {comment_id} by {user.email if user else 'system'}")
    
    async def _delete_external_comment(
        self,
        db: AsyncSession,
        comment: TicketComment
    ):
        """
        Delete comment from external integration platform.
        
        Args:
            db: Database session
            comment: TicketComment instance to delete externally
        """
        if not comment.integration or not comment.external_comment_id:
            return
        
        try:
            from app.services.integration_service import IntegrationService
            
            integration_service = IntegrationService()
            integration_impl = integration_service._get_integration_implementation(comment.integration)
            
            # Get the ticket to get external_ticket_id
            if not comment.ticket.external_ticket_id:
                logger.warning(f"Cannot delete external comment - ticket {comment.ticket_id} has no external_ticket_id")
                return
            
            # Platform-specific delete logic
            if comment.integration.platform_name.lower() == "jira":
                # Delete comment from JIRA
                await integration_impl.delete_comment(
                    issue_key=comment.ticket.external_ticket_id,
                    comment_id=comment.external_comment_id
                )
                
                logger.info(f"✅ Deleted external comment {comment.external_comment_id} from {comment.integration.platform_name}")
            
            # Add support for other platforms here (ServiceNow, Zendesk, etc.)
            else:
                logger.warning(f"External comment deletion not implemented for platform: {comment.integration.platform_name}")
            
        except Exception as e:
            logger.error(f"Failed to delete external comment: {e}")
            raise
    
    async def get_ticket_comment_stats(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Get comment statistics for a ticket.
        
        Args:
            db: Database session
            ticket_id: ID of the parent ticket
            user: Current user (for permissions)
            
        Returns:
            Dictionary with comment statistics
        """
        # Build query filters
        filters = [TicketComment.ticket_id == ticket_id, TicketComment.deleted_at.is_(None)]
        
        # Only count non-internal comments for non-admin users
        if user and user.role != UserRole.ADMIN:
            filters.append(TicketComment.is_internal == False)
        
        # Total comments
        count_stmt = select(func.count(TicketComment.id)).where(and_(*filters))
        count_result = await db.execute(count_stmt)
        total_comments = count_result.scalar() or 0
        
        # Internal comments count (for admins)
        internal_count = 0
        if user and user.role == UserRole.ADMIN:
            internal_stmt = select(func.count(TicketComment.id)).where(
                and_(
                    TicketComment.ticket_id == ticket_id, 
                    TicketComment.is_internal == True,
                    TicketComment.deleted_at.is_(None)
                )
            )
            internal_result = await db.execute(internal_stmt)
            internal_count = internal_result.scalar() or 0
        
        # Synchronized comments count
        sync_stmt = select(func.count(TicketComment.id)).where(
            and_(
                TicketComment.ticket_id == ticket_id, 
                TicketComment.external_comment_id.isnot(None),
                TicketComment.deleted_at.is_(None)
            )
        )
        sync_result = await db.execute(sync_stmt)
        synchronized_count = sync_result.scalar() or 0
        
        # Comments by integration platform
        platform_stmt = (
            select(Integration.platform_name, func.count(TicketComment.id).label('count'))
            .select_from(TicketComment)
            .join(Integration, TicketComment.integration_id == Integration.id)
            .where(
                and_(
                    TicketComment.ticket_id == ticket_id,
                    TicketComment.deleted_at.is_(None),
                    TicketComment.integration_id.isnot(None)
                )
            )
            .group_by(Integration.platform_name)
        )
        platform_result = await db.execute(platform_stmt)
        platform_stats = {row.platform_name: row.count for row in platform_result}
        
        # Latest comment timestamp
        latest_stmt = select(func.max(TicketComment.created_at)).where(and_(*filters))
        latest_result = await db.execute(latest_stmt)
        latest_comment_at = latest_result.scalar()
        
        return {
            "total_comments": total_comments,
            "internal_comments": internal_count,
            "synchronized_comments": synchronized_count,
            "platform_stats": platform_stats,
            "latest_comment_at": latest_comment_at
        }


# Service instance
comment_service = CommentService()