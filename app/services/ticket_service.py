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

from app.models.ticket import DBTicket, TicketStatus, TicketPriority, TicketCategory
from app.models.user import DBUser
from app.models.file import DBFile

logger = logging.getLogger(__name__)


class TicketService:
    """Service for ticket operations"""
    
    async def list_tickets(
        self,
        db: AsyncSession,
        offset: int = 0,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[DBTicket], int]:
        """
        List tickets with filtering, sorting, and pagination.
        
        Args:
            db: Database session
            offset: Pagination offset
            limit: Pagination limit
            filters: Filter criteria
            sort_by: Sort field
            sort_order: Sort direction
            
        Returns:
            Tuple of (tickets, total_count)
        """
        try:
            # Build query
            query = select(DBTicket).options(
                selectinload(DBTicket.creator),
                selectinload(DBTicket.assignee),
                selectinload(DBTicket.files)
            )
            
            # Apply filters
            if filters:
                conditions = []
                
                # Search in title and description
                if search := filters.get('search'):
                    search_condition = or_(
                        DBTicket.title.ilike(f'%{search}%'),
                        DBTicket.description.ilike(f'%{search}%')
                    )
                    conditions.append(search_condition)
                
                # Status filter
                if status_list := filters.get('status'):
                    conditions.append(DBTicket.status.in_(status_list))
                
                # Category filter
                if category_list := filters.get('category'):
                    conditions.append(DBTicket.category.in_(category_list))
                
                # Priority filter
                if priority_list := filters.get('priority'):
                    conditions.append(DBTicket.priority.in_(priority_list))
                
                # Department filter
                if department := filters.get('department'):
                    conditions.append(DBTicket.department == department)
                
                # User filters
                if created_by_id := filters.get('created_by_id'):
                    conditions.append(DBTicket.created_by_id == created_by_id)
                
                if assigned_to_id := filters.get('assigned_to_id'):
                    conditions.append(DBTicket.assigned_to_id == assigned_to_id)
                
                # Date filters
                if created_after := filters.get('created_after'):
                    conditions.append(DBTicket.created_at >= created_after)
                
                if created_before := filters.get('created_before'):
                    conditions.append(DBTicket.created_at <= created_before)
                
                # Overdue filter
                if is_overdue := filters.get('is_overdue'):
                    now = datetime.now(timezone.utc)
                    if is_overdue:
                        conditions.append(
                            and_(
                                DBTicket.sla_due_date.isnot(None),
                                DBTicket.sla_due_date < now
                            )
                        )
                    else:
                        conditions.append(
                            or_(
                                DBTicket.sla_due_date.is_(None),
                                DBTicket.sla_due_date >= now
                            )
                        )
                
                if conditions:
                    query = query.where(and_(*conditions))
            
            # Exclude soft-deleted records
            query = query.where(DBTicket.is_deleted == False)
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Apply sorting
            sort_column = getattr(DBTicket, sort_by, DBTicket.created_at)
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
        ticket_data: Dict[str, Any]
    ) -> DBTicket:
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
                ticket_dict = ticket_data
            ticket = DBTicket(**ticket_dict)
            
            # Set initial status
            ticket.status = TicketStatus.NEW
            ticket.last_activity_at = datetime.now(timezone.utc)
            
            # Add to database
            db.add(ticket)
            await db.commit()
            await db.refresh(ticket)
            
            # Load relationships
            query = select(DBTicket).options(
                selectinload(DBTicket.creator),
                selectinload(DBTicket.assignee),
                selectinload(DBTicket.files)
            ).where(DBTicket.id == ticket.id)
            
            result = await db.execute(query)
            ticket = result.scalar_one()
            
            logger.info(f"Created ticket {ticket.id}: {ticket.title}")
            return ticket
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating ticket: {e}")
            raise
    
    async def get_ticket(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        include_ai_data: bool = True,
        include_internal: bool = False
    ) -> Optional[DBTicket]:
        """
        Get a ticket by ID.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            include_ai_data: Include AI analysis data
            include_internal: Include internal notes
            
        Returns:
            Ticket or None if not found
        """
        try:
            query = select(DBTicket).options(
                selectinload(DBTicket.creator),
                selectinload(DBTicket.assignee),
                selectinload(DBTicket.files)
            ).where(
                and_(
                    DBTicket.id == ticket_id,
                    DBTicket.is_deleted == False
                )
            )
            
            result = await db.execute(query)
            ticket = result.scalar_one_or_none()
            
            if ticket:
                logger.info(f"Retrieved ticket {ticket_id}")
            else:
                logger.warning(f"Ticket {ticket_id} not found")
            
            return ticket
            
        except Exception as e:
            logger.error(f"Error getting ticket {ticket_id}: {e}")
            raise
    
    async def update_ticket(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        update_data: Dict[str, Any]
    ) -> Optional[DBTicket]:
        """
        Update a ticket.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            update_data: Update data
            
        Returns:
            Updated ticket or None if not found
        """
        try:
            ticket = await self.get_ticket(db, ticket_id)
            if not ticket:
                return None
            
            # Update fields
            for field, value in update_data.items():
                if hasattr(ticket, field) and value is not None:
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
        new_status: str,
        resolution_summary: Optional[str] = None,
        internal_notes: Optional[str] = None
    ) -> Optional[DBTicket]:
        """
        Update ticket status with proper state transitions.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            new_status: New status
            resolution_summary: Resolution summary for resolved tickets
            internal_notes: Internal notes
            
        Returns:
            Updated ticket or None if not found
        """
        try:
            ticket = await self.get_ticket(db, ticket_id)
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
        assigned_to_id: Optional[UUID],
        reason: Optional[str] = None
    ) -> Optional[DBTicket]:
        """
        Assign or unassign a ticket.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            assigned_to_id: User ID to assign to (None to unassign)
            reason: Assignment reason
            
        Returns:
            Updated ticket or None if not found
        """
        try:
            ticket = await self.get_ticket(db, ticket_id)
            if not ticket:
                return None
            
            # Validate assignee exists if provided
            if assigned_to_id:
                user_query = select(DBUser).where(
                    and_(
                        DBUser.id == assigned_to_id,
                        DBUser.is_active == True,
                        DBUser.is_deleted == False
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
        ticket_id: UUID
    ) -> bool:
        """
        Soft delete a ticket.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            ticket = await self.get_ticket(db, ticket_id)
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
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get ticket statistics.
        
        Args:
            db: Database session
            
        Returns:
            Statistics dictionary
        """
        try:
            # Total tickets
            total_query = select(func.count(DBTicket.id)).where(DBTicket.is_deleted == False)
            total_result = await db.execute(total_query)
            total_tickets = total_result.scalar() or 0
            
            # Open tickets
            open_query = select(func.count(DBTicket.id)).where(
                and_(
                    DBTicket.is_deleted == False,
                    DBTicket.status.in_([TicketStatus.NEW, TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
                )
            )
            open_result = await db.execute(open_query)
            open_tickets = open_result.scalar() or 0
            
            # Resolved tickets
            resolved_query = select(func.count(DBTicket.id)).where(
                and_(
                    DBTicket.is_deleted == False,
                    DBTicket.status == TicketStatus.RESOLVED
                )
            )
            resolved_result = await db.execute(resolved_query)
            resolved_tickets = resolved_result.scalar() or 0
            
            # Overdue tickets
            now = datetime.now(timezone.utc)
            overdue_query = select(func.count(DBTicket.id)).where(
                and_(
                    DBTicket.is_deleted == False,
                    DBTicket.sla_due_date.isnot(None),
                    DBTicket.sla_due_date < now,
                    DBTicket.status.in_([TicketStatus.NEW, TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
                )
            )
            overdue_result = await db.execute(overdue_query)
            overdue_tickets = overdue_result.scalar() or 0
            
            # High priority tickets
            high_priority_query = select(func.count(DBTicket.id)).where(
                and_(
                    DBTicket.is_deleted == False,
                    DBTicket.priority.in_([TicketPriority.HIGH, TicketPriority.CRITICAL]),
                    DBTicket.status.in_([TicketStatus.NEW, TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
                )
            )
            high_priority_result = await db.execute(high_priority_query)
            high_priority_tickets = high_priority_result.scalar() or 0
            
            # Category distribution
            category_query = select(
                DBTicket.category,
                func.count(DBTicket.id).label('count')
            ).where(
                DBTicket.is_deleted == False
            ).group_by(DBTicket.category)
            
            category_result = await db.execute(category_query)
            category_distribution = {
                str(row.category.value): row.count 
                for row in category_result
            }
            
            # Priority distribution
            priority_query = select(
                DBTicket.priority,
                func.count(DBTicket.id).label('count')
            ).where(
                DBTicket.is_deleted == False
            ).group_by(DBTicket.priority)
            
            priority_result = await db.execute(priority_query)
            priority_distribution = {
                str(row.priority.value): row.count 
                for row in priority_result
            }
            
            # Status distribution
            status_query = select(
                DBTicket.status,
                func.count(DBTicket.id).label('count')
            ).where(
                DBTicket.is_deleted == False
            ).group_by(DBTicket.status)
            
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