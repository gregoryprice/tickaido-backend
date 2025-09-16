#!/usr/bin/env python3
"""
Ticket service for business logic operations
"""

import logging
from typing import List, Tuple, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload

from app.models.ticket import Ticket, TicketStatus, TicketPriority
from app.models.user import User
from app.models.integration import Integration, IntegrationStatus

logger = logging.getLogger(__name__)


class TicketService:
    """Service for ticket operations"""
    
    async def list_tickets(
        self,
        db: AsyncSession,
        organization_id: UUID,
        offset: int = 0,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Ticket], int]:
        """
        List tickets with organization isolation, filtering, sorting, and pagination.
        
        Args:
            db: Database session
            organization_id: Organization ID for isolation
            offset: Pagination offset
            limit: Pagination limit
            filters: Filter criteria
            sort_by: Sort field
            sort_order: Sort direction
            
        Returns:
            Tuple of (tickets, total_count)
        """
        try:
            # Build query with organization isolation
            query = select(Ticket).join(User, Ticket.created_by_id == User.id).options(
                selectinload(Ticket.creator),
# selectinload(Ticket.files)  # Removed - files now via file_ids array
            ).filter(User.organization_id == organization_id)
            
            # Apply filters
            if filters:
                conditions = []
                
                # Search in title and description
                if search := filters.get('search'):
                    search_condition = or_(
                        Ticket.title.ilike(f'%{search}%'),
                        Ticket.description.ilike(f'%{search}%')
                    )
                    conditions.append(search_condition)
                
                # Status filter
                if status_list := filters.get('status'):
                    conditions.append(Ticket.status.in_(status_list))
                
                # Category filter
                if category_list := filters.get('category'):
                    conditions.append(Ticket.category.in_(category_list))
                
                # Priority filter
                if priority_list := filters.get('priority'):
                    conditions.append(Ticket.priority.in_(priority_list))
                
                # Department filter
                if department := filters.get('department'):
                    conditions.append(Ticket.department == department)
                
                # User filters
                if created_by_id := filters.get('created_by_id'):
                    conditions.append(Ticket.created_by_id == created_by_id)
                
                if assigned_to_id := filters.get('assigned_to_id'):
                    conditions.append(Ticket.assigned_to_id == assigned_to_id)
                
                # Date filters
                if created_after := filters.get('created_after'):
                    conditions.append(Ticket.created_at >= created_after)
                
                if created_before := filters.get('created_before'):
                    conditions.append(Ticket.created_at <= created_before)
                
                # Overdue filter
                if is_overdue := filters.get('is_overdue'):
                    now = datetime.now(timezone.utc)
                    if is_overdue:
                        conditions.append(
                            and_(
                                Ticket.sla_due_date.isnot(None),
                                Ticket.sla_due_date < now
                            )
                        )
                    else:
                        conditions.append(
                            or_(
                                Ticket.sla_due_date.is_(None),
                                Ticket.sla_due_date >= now
                            )
                        )
                
                if conditions:
                    query = query.where(and_(*conditions))
            
            # Exclude soft-deleted records
            query = query.where(Ticket.is_deleted == False)
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Apply sorting
            sort_column = getattr(Ticket, sort_by, Ticket.created_at)
            if sort_order.lower() == 'asc':
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            # Execute query
            result = await db.execute(query)
            tickets = result.scalars().all()
            
            logger.info(f"Listed {len(tickets)} tickets (total: {total})")
            return list(tickets), total
            
        except Exception as e:
            logger.error(f"Error listing tickets: {e}")
            raise
    
    async def create_ticket(
        self,
        db: AsyncSession,
        ticket_data: Dict[str, Any],
        created_by_id: Optional[UUID] = None
    ) -> Ticket:
        """
        Create a new ticket.
        
        Args:
            db: Database session
            ticket_data: Ticket data
            
        Returns:
            Created ticket
        """
        try:
            # Create ticket instance
            # Convert Pydantic model to dict if needed
            if hasattr(ticket_data, 'model_dump'):
                ticket_dict = ticket_data.model_dump(exclude_unset=True)
            else:
                ticket_dict = ticket_data.copy()  # Make copy to avoid modifying original
            
            # Remove fields from ticket_dict that are not Ticket model fields
            file_ids = ticket_dict.pop('file_ids', None)
            create_externally = ticket_dict.pop('create_externally', None)
            
            # Set created_by_id if provided
            if created_by_id:
                ticket_dict['created_by_id'] = created_by_id
            
            # Convert enum strings to proper enum instances and handle defaults
            if 'priority' in ticket_dict and ticket_dict['priority'] is not None:
                if isinstance(ticket_dict['priority'], str):
                    try:
                        ticket_dict['priority'] = TicketPriority(ticket_dict['priority'].lower())
                    except ValueError:
                        # If invalid priority, use default
                        ticket_dict['priority'] = TicketPriority.MEDIUM
                # else: priority is already a TicketPriority enum, keep it
            else:
                # Priority not provided or is None, set default for internal ticket only
                ticket_dict['priority'] = TicketPriority.MEDIUM
            
            if 'category' in ticket_dict and isinstance(ticket_dict['category'], str):
                from app.models.ticket import TicketCategory
                try:
                    ticket_dict['category'] = TicketCategory(ticket_dict['category'].lower())
                except ValueError:
                    # If invalid category, use default
                    ticket_dict['category'] = TicketCategory.GENERAL
            
            if 'status' in ticket_dict and isinstance(ticket_dict['status'], str):
                try:
                    ticket_dict['status'] = TicketStatus(ticket_dict['status'].lower())
                except ValueError:
                    # If invalid status, use default
                    ticket_dict['status'] = TicketStatus.NEW
            
            if 'urgency' in ticket_dict and isinstance(ticket_dict['urgency'], str):
                try:
                    ticket_dict['urgency'] = TicketPriority(ticket_dict['urgency'].lower())
                except ValueError:
                    # If invalid urgency, use default  
                    ticket_dict['urgency'] = TicketPriority.MEDIUM
            
            ticket = Ticket(**ticket_dict)
            
            # Set initial status
            ticket.status = TicketStatus.NEW
            ticket.last_activity_at = datetime.now(timezone.utc)
            
            # Add to database
            db.add(ticket)
            await db.commit()
            await db.refresh(ticket)
            
            # Load relationships
            query = select(Ticket).options(
                selectinload(Ticket.creator),
# selectinload(Ticket.files)  # Removed - files now via file_ids array
            ).where(Ticket.id == ticket.id)
            
            result = await db.execute(query)
            ticket = result.scalar_one()
            
            logger.info(f"Created ticket {ticket.id}: {ticket.title}")
            return ticket
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating ticket: {e}")
            raise
    
    async def create_ticket_with_integration(
        self,
        db: AsyncSession,
        ticket_data: Dict[str, Any],
        created_by_id: UUID
    ) -> Tuple[Ticket, Dict[str, Any]]:
        """
        Create ticket in database and optionally in one external integration.
        
        Args:
            db: Database session
            ticket_data: Ticket data including integration field
            created_by_id: ID of user creating ticket
            
        Returns:
            Tuple of (internal_ticket, integration_result)
        """
        # Extract integration fields
        integration_id = ticket_data.pop('integration_id', None)
        create_externally = ticket_data.pop('create_externally', True)
        
        # Track if priority was explicitly provided before defaults are applied
        original_priority_provided = 'priority' in ticket_data and ticket_data.get('priority') is not None
        
        # 1. Create internal ticket
        internal_ticket = await self.create_ticket(db, ticket_data, created_by_id)
        
        # 2. Handle external integration if specified
        integration_result = {
            "success": False,
            "integration_id": None,
            "external_ticket_id": None,
            "external_ticket_url": None,
            "error_message": None,
            "response": {}  # Full JSON response from integration
        }
        
        if integration_id and create_externally:
            # Get active integration by ID
            integration = await self._get_active_integration_by_id(
                db=db,
                integration_id=integration_id,
                user_id=created_by_id
            )
            
            if not integration or integration.status != IntegrationStatus.ACTIVE or not integration.enabled:
                # Rollback internal ticket creation
                await db.delete(internal_ticket)
                await db.commit()
                raise ValueError(f"Integration with ID '{integration_id}' not found, not active, or not enabled")
            
            # Create external ticket first - fail if this fails
            external_result = await self._create_external_ticket(
                integration=integration,
                ticket_data=internal_ticket,
                user_id=created_by_id,
                original_priority_provided=original_priority_provided
            )
            
            if not external_result.get("success"):
                # Rollback internal ticket creation if external creation fails
                await db.delete(internal_ticket)
                await db.commit()
                
                # Include the full error response in the exception
                error_details = external_result.get("details", {})
                error_msg = external_result.get("error_message", "External ticket creation failed")
                
                raise ValueError(f"External ticket creation failed: {error_msg}")
            
            # External creation succeeded - update integration result and internal ticket
            integration_result.update({
                "success": True,
                "integration_id": str(integration_id),
                "external_ticket_id": external_result["external_ticket_id"],
                "external_ticket_url": external_result["external_ticket_url"],
                "response": external_result["details"]
            })
            
            # Update internal ticket with external references
            internal_ticket.external_ticket_id = external_result["external_ticket_id"]
            internal_ticket.external_ticket_url = external_result["external_ticket_url"]
            internal_ticket.integration_id = integration_id
            
            await db.commit()
            
            logger.info(f"✅ Ticket created in integration {integration.name} ({integration_id}): {external_result['external_ticket_id']}")
        else:
            # No integration specified, just commit the internal ticket
            await db.commit()
        
        return internal_ticket, integration_result
    
    async def _get_active_integration_by_id(
        self,
        db: AsyncSession,
        integration_id: UUID,
        user_id: UUID
    ) -> Optional[Integration]:
        """
        Get active integration by ID for the user's organization.
        """
        from app.models.user import User
        
        # Get user to determine organization
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            return None
        
        # Query for integration by ID and organization
        query = select(Integration).where(
            and_(
                Integration.id == integration_id,
                Integration.status == IntegrationStatus.ACTIVE,
                Integration.enabled == True,
                Integration.is_deleted == False,
                Integration.organization_id == user.organization_id
            )
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _create_external_ticket(
        self,
        integration: Integration,
        ticket_data: Ticket,
        user_id: UUID,
        original_priority_provided: bool = True
    ) -> Dict[str, Any]:
        """
        Create ticket in external integration system using integration-specific methods.
        """
        try:
            # Use integration-specific factory methods
            if integration.platform_name == "jira":
                from .jira_integration import JiraIntegration
                return await JiraIntegration.create_ticket_from_internal(
                    integration, ticket_data, original_priority_provided=original_priority_provided
                )
            # elif integration.platform_name == "salesforce":
            #     from .salesforce_integration import SalesforceIntegration
            #     return await SalesforceIntegration.create_ticket_from_internal(integration, ticket_data)
            else:
                return {
                    "success": False,
                    "error_message": f"Integration platform '{integration.platform_name}' not supported for ticket creation",
                    "details": {}
                }
                
        except Exception as e:
            logger.error(f"External ticket creation failed: {e}")
            return {
                "success": False,
                "error_message": str(e),
                "details": {}
            }
    
    async def get_ticket(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        organization_id: UUID,
        include_ai_data: bool = True,
        include_internal: bool = False
    ) -> Optional[Ticket]:
        """
        Get a ticket by ID with organization validation.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            organization_id: Organization ID for isolation
            include_ai_data: Include AI analysis data
            include_internal: Include internal notes
            
        Returns:
            Ticket or None if not found or not accessible
        """
        try:
            query = select(Ticket).join(User, Ticket.created_by_id == User.id).options(
                selectinload(Ticket.creator),
# selectinload(Ticket.files)  # Removed - files now via file_ids array
            ).where(
                and_(
                    Ticket.id == ticket_id,
                    User.organization_id == organization_id,
                    Ticket.is_deleted == False
                )
            )
            
            result = await db.execute(query)
            ticket = result.scalar_one_or_none()
            
            if ticket:
                logger.info(f"Retrieved ticket {ticket_id} for organization {organization_id}")
            else:
                logger.warning(f"Ticket {ticket_id} not found or not accessible for organization {organization_id}")
            
            return ticket
            
        except Exception as e:
            logger.error(f"Error getting ticket {ticket_id} for organization {organization_id}: {e}")
            raise
    
    async def patch_ticket(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        organization_id: UUID,
        update_data: Dict[str, Any],
        updated_by_user: User
    ) -> Optional[Ticket]:
        """
        Flexible partial update for any ticket fields with organization isolation.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            organization_id: Organization ID for isolation
            update_data: Dictionary of fields to update
            updated_by_user: User performing the update
            
        Returns:
            Updated ticket or None if not found or not accessible
        """
        try:
            # Get ticket with organization validation
            ticket = await self.get_ticket(db, ticket_id, organization_id)
            if not ticket:
                return None
            
            # Track changes for audit logging
            changes = {}
            
            # Apply all provided updates
            for field, value in update_data.items():
                if hasattr(ticket, field):
                    old_value = getattr(ticket, field)
                    # Convert enum values for comparison
                    if hasattr(old_value, 'value'):
                        old_value = old_value.value
                    if hasattr(value, 'value'):
                        value = value.value
                        
                    if old_value != value:
                        setattr(ticket, field, value)
                        changes[field] = {"from": old_value, "to": value}
            
            # Special handling for assignment changes
            if "assigned_to_id" in update_data:
                ticket.assigned_at = datetime.now(timezone.utc)
                ticket.assigned_by_id = updated_by_user.id
            
            # Update metadata
            ticket.updated_at = datetime.now(timezone.utc)
            ticket.updated_by_id = updated_by_user.id
            
            # Save changes
            db.add(ticket)
            await db.commit()
            await db.refresh(ticket)
            
            # Log audit trail for changes
            if changes:
                logger.info(f"Ticket {ticket_id} updated by user {updated_by_user.id} in organization {organization_id}: {changes}")
            
            return ticket
            
        except Exception as e:
            logger.error(f"Error patching ticket {ticket_id} for organization {organization_id}: {e}")
            await db.rollback()
            raise
    
    async def update_ticket(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        organization_id: UUID,
        update_data: Dict[str, Any]
    ) -> Optional[Ticket]:
        """
        Update a ticket with organization isolation.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            organization_id: Organization ID for isolation
            update_data: Update data
            
        Returns:
            Updated ticket or None if not found or not accessible
        """
        try:
            ticket = await self.get_ticket(db, ticket_id, organization_id)
            if not ticket:
                return None
            
            # Update fields
            nullable_fields = {'assigned_to_id', 'department', 'resolution_summary', 'internal_notes', 'custom_fields'}
            
            for field, value in update_data.items():
                if hasattr(ticket, field):
                    # Allow None values for nullable fields
                    if value is not None or field in nullable_fields:
                        setattr(ticket, field, value)
            
            # Update activity timestamp
            ticket.last_activity_at = datetime.now(timezone.utc)
            
            await db.commit()
            await db.refresh(ticket)
            
            logger.info(f"Updated ticket {ticket_id}")
            return ticket
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating ticket {ticket_id}: {e}")
            raise
    
    async def update_ticket_status(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        organization_id: UUID,
        new_status: str,
        resolution_summary: Optional[str] = None,
        internal_notes: Optional[str] = None
    ) -> Optional[Ticket]:
        """
        Update ticket status with organization isolation and proper state transitions.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            organization_id: Organization ID for isolation
            new_status: New status
            resolution_summary: Resolution summary for resolved tickets
            internal_notes: Internal notes
            
        Returns:
            Updated ticket or None if not found or not accessible
        """
        try:
            ticket = await self.get_ticket(db, ticket_id, organization_id)
            if not ticket:
                return None
            
            # Validate status transition
            old_status = ticket.status
            new_status_enum = TicketStatus(new_status)
            
            # Update status with timestamp tracking
            ticket.update_status(new_status_enum)
            
            # Add resolution summary if provided
            if resolution_summary:
                ticket.resolution_summary = resolution_summary
            
            # Add internal notes if provided
            if internal_notes:
                if ticket.internal_notes:
                    ticket.internal_notes += f"\n\n{datetime.now().isoformat()}: {internal_notes}"
                else:
                    ticket.internal_notes = f"{datetime.now().isoformat()}: {internal_notes}"
            
            await db.commit()
            await db.refresh(ticket)
            
            logger.info(f"Updated ticket {ticket_id} status from {old_status} to {new_status}")
            return ticket
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating ticket status {ticket_id}: {e}")
            raise
    
    async def assign_ticket(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        organization_id: UUID,
        assigned_to_id: Optional[UUID],
        reason: Optional[str] = None
    ) -> Optional[Ticket]:
        """
        Assign or unassign a ticket with organization isolation.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            organization_id: Organization ID for isolation
            assigned_to_id: User ID to assign to (None to unassign)
            reason: Assignment reason
            
        Returns:
            Updated ticket or None if not found or not accessible
        """
        try:
            ticket = await self.get_ticket(db, ticket_id, organization_id)
            if not ticket:
                return None
            
            # Validate assignee exists if provided
            if assigned_to_id:
                user_query = select(User).where(
                    and_(
                        User.id == assigned_to_id,
                        User.is_active == True,
                        User.is_deleted == False
                    )
                )
                user_result = await db.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    raise ValueError(f"User {assigned_to_id} not found or inactive")
            
            # Update assignment
            old_assignee = ticket.assigned_to_id
            ticket.assigned_to_id = assigned_to_id
            ticket.last_activity_at = datetime.now(timezone.utc)
            
            # Add assignment note
            if reason:
                assignment_note = f"Assignment changed: {reason}"
                if ticket.internal_notes:
                    ticket.internal_notes += f"\n\n{datetime.now().isoformat()}: {assignment_note}"
                else:
                    ticket.internal_notes = f"{datetime.now().isoformat()}: {assignment_note}"
            
            await db.commit()
            await db.refresh(ticket)
            
            logger.info(f"Assigned ticket {ticket_id} from {old_assignee} to {assigned_to_id}")
            return ticket
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error assigning ticket {ticket_id}: {e}")
            raise
    
    async def delete_ticket(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        organization_id: UUID
    ) -> bool:
        """
        Soft delete a ticket with organization isolation.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            organization_id: Organization ID for isolation
            
        Returns:
            True if deleted, False if not found or not accessible
        """
        try:
            ticket = await self.get_ticket(db, ticket_id, organization_id)
            if not ticket:
                return False
            
            # Soft delete
            ticket.soft_delete()
            
            await db.commit()
            
            logger.info(f"Deleted ticket {ticket_id}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting ticket {ticket_id}: {e}")
            raise
    
    async def get_ticket_stats(
        self,
        db: AsyncSession,
        organization_id: UUID
    ) -> Dict[str, Any]:
        """
        Get ticket statistics with organization isolation.
        
        Args:
            db: Database session
            organization_id: Organization ID for isolation
            
        Returns:
            Organization-specific statistics dictionary
        """
        try:
            # Base organization filter - join with User table
            base_filter = lambda: and_(
                Ticket.is_deleted == False,
                Ticket.created_by_id == User.id,
                User.organization_id == organization_id
            )
            
            # Total tickets
            total_query = select(func.count(Ticket.id)).select_from(
                Ticket.__table__.join(User.__table__, Ticket.created_by_id == User.id)
            ).where(base_filter())
            total_result = await db.execute(total_query)
            total_tickets = total_result.scalar() or 0
            
            # Open tickets
            open_query = select(func.count(Ticket.id)).select_from(
                Ticket.__table__.join(User.__table__, Ticket.created_by_id == User.id)
            ).where(
                and_(
                    base_filter(),
                    Ticket.status.in_([TicketStatus.NEW, TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
                )
            )
            open_result = await db.execute(open_query)
            open_tickets = open_result.scalar() or 0
            
            # Resolved tickets
            resolved_query = select(func.count(Ticket.id)).select_from(
                Ticket.__table__.join(User.__table__, Ticket.created_by_id == User.id)
            ).where(
                and_(
                    base_filter(),
                    Ticket.status == TicketStatus.RESOLVED
                )
            )
            resolved_result = await db.execute(resolved_query)
            resolved_tickets = resolved_result.scalar() or 0
            
            # Overdue tickets
            now = datetime.now(timezone.utc)
            overdue_query = select(func.count(Ticket.id)).where(
                and_(
                    Ticket.is_deleted == False,
                    Ticket.sla_due_date.isnot(None),
                    Ticket.sla_due_date < now,
                    Ticket.status.in_([TicketStatus.NEW, TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
                )
            )
            overdue_result = await db.execute(overdue_query)
            overdue_tickets = overdue_result.scalar() or 0
            
            # High priority tickets
            high_priority_query = select(func.count(Ticket.id)).where(
                and_(
                    Ticket.is_deleted == False,
                    Ticket.priority.in_([TicketPriority.HIGH, TicketPriority.CRITICAL]),
                    Ticket.status.in_([TicketStatus.NEW, TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
                )
            )
            high_priority_result = await db.execute(high_priority_query)
            high_priority_tickets = high_priority_result.scalar() or 0
            
            # Category distribution
            category_query = select(
                Ticket.category,
                func.count(Ticket.id).label('count')
            ).where(
                Ticket.is_deleted == False
            ).group_by(Ticket.category)
            
            category_result = await db.execute(category_query)
            category_distribution = {
                str(row.category.value): row.count 
                for row in category_result
            }
            
            # Priority distribution
            priority_query = select(
                Ticket.priority,
                func.count(Ticket.id).label('count')
            ).where(
                Ticket.is_deleted == False
            ).group_by(Ticket.priority)
            
            priority_result = await db.execute(priority_query)
            priority_distribution = {
                str(row.priority.value): row.count 
                for row in priority_result
            }
            
            # Status distribution
            status_query = select(
                Ticket.status,
                func.count(Ticket.id).label('count')
            ).where(
                Ticket.is_deleted == False
            ).group_by(Ticket.status)
            
            status_result = await db.execute(status_query)
            status_distribution = {
                str(row.status.value): row.count 
                for row in status_result
            }
            
            stats = {
                "total_tickets": total_tickets,
                "open_tickets": open_tickets,
                "resolved_tickets": resolved_tickets,
                "overdue_tickets": overdue_tickets,
                "high_priority_tickets": high_priority_tickets,
                "avg_resolution_time_hours": None,  # TODO: Calculate from resolved tickets
                "avg_first_response_time_hours": None,  # TODO: Calculate from tickets with first response
                "satisfaction_score": None,  # TODO: Calculate from satisfaction ratings
                "category_distribution": category_distribution,
                "priority_distribution": priority_distribution,
                "status_distribution": status_distribution
            }
            
            logger.info(f"Generated ticket stats: {total_tickets} total, {open_tickets} open")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting ticket stats: {e}")
            raise


# Global service instance
ticket_service = TicketService()