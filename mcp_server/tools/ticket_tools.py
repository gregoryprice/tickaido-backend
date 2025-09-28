#!/usr/bin/env python3
"""
Principal-based MCP Tools with Direct Database Access

These tools receive Principal context from FastAPI via MCP Client and access
the database directly. NO HTTP calls back to the API.
"""

import json
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, or_

from app.database import get_db_session
from app.schemas.principal import Principal
from app.models.ticket import Ticket, TicketStatus, TicketPriority, TicketCategory
from app.models.user import User

logger = logging.getLogger(__name__)


def register_all_ticket_tools(mcp):
    """Register all ticket tools that receive context from FastAPI"""
    
    @mcp.tool()
    async def create_ticket(
        title: str,
        description: str,
        category: str = "general",
        priority: str = "medium",
        urgency: str = "medium",
        department: str = "",
        assigned_to_id: str = "",
        integration: str = "",
        create_externally: str = "false",
        custom_fields: str = "{}",
        file_ids: str = "",
        _mcp_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create ticket with Principal-based authorization.
        
        Principal context is injected by MCP Server middleware from FastAPI.
        """
        start_time = datetime.now()
        
        try:
            # Extract Principal from MCP context injected by middleware
            if not _mcp_context or 'principal' not in _mcp_context:
                return json.dumps({
                    "error": "Principal context required", 
                    "message": "MCP tools require Principal context from FastAPI"
                })
            
            principal_data = _mcp_context['principal']
            principal = Principal.from_dict(principal_data) if isinstance(principal_data, dict) else principal_data
            
            # Validate permission
            if not principal.can_access_tool("create_ticket"):
                return json.dumps({
                    "error": "Permission denied", 
                    "message": f"User {principal.email} not authorized to create tickets"
                })
            
            # Validate inputs
            if not title or not title.strip():
                return json.dumps({"error": "Title is required"})
            if not description or not description.strip():
                return json.dumps({"error": "Description is required"})
            
            # Direct database access (NO HTTP calls)
            async with get_db_session() as db:
                # Create ticket with organization isolation
                ticket = Ticket(
                    title=title.strip(),
                    description=description.strip(),
                    category=TicketCategory(category) if category in [c.value for c in TicketCategory] else TicketCategory.GENERAL,
                    priority=TicketPriority(priority) if priority in [p.value for p in TicketPriority] else TicketPriority.MEDIUM,
                    urgency=TicketPriority(urgency) if urgency in [p.value for p in TicketPriority] else TicketPriority.MEDIUM,
                    status=TicketStatus.OPEN,
                    created_by_id=principal.user_id,
                    organization_id=principal.organization_id,  # Organization isolation
                    department=department if department else None,
                )
                
                # Validate assigned_to_id if provided
                if assigned_to_id:
                    try:
                        result = await db.execute(
                            select(User).where(
                                and_(
                                    User.id == assigned_to_id,
                                    User.organization_id == principal.organization_id,
                                    User.is_active == True
                                )
                            )
                        )
                        if result.scalar_one_or_none():
                            ticket.assigned_to_id = assigned_to_id
                    except:
                        pass  # Invalid assigned_to_id, ignore
                
                db.add(ticket)
                await db.flush()
                await db.commit()
                
                result = {
                    "success": True,
                    "ticket_id": str(ticket.id),
                    "title": ticket.title,
                    "category": ticket.category.value,
                    "priority": ticket.priority.value,
                    "status": ticket.status.value,
                    "created_at": ticket.created_at.isoformat(),
                    "organization_id": str(ticket.organization_id),
                    "created_by_id": str(ticket.created_by_id)
                }
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(f"✅ Principal MCP: Created ticket {ticket.id} for {principal.email} in {execution_time:.2f}ms")
                
                return json.dumps(result, indent=2)
        
        except Exception as e:
            logger.error(f"❌ Principal MCP create_ticket failed: {e}")
            return json.dumps({"error": "Tool execution failed", "message": str(e)})
    
    @mcp.tool()
    async def list_tickets(
        page: int = 1,
        page_size: int = 10,
        status: str = "",
        category: str = "",
        priority: str = "",
        _mcp_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        List tickets with Principal-based authorization.
        """
        start_time = datetime.now()
        
        logger.info(f"🔍 [TRACE] Step 6: MCP_TOOL list_tickets - TOOL CALLED")
        logger.info(f"🔍 [TRACE] Parameters: page={page}, page_size={page_size}, status='{status}', category='{category}', priority='{priority}'")
        logger.info(f"🔍 [TRACE] _mcp_context present: {_mcp_context is not None}")
        
        if _mcp_context:
            logger.info(f"🔍 [TRACE] _mcp_context keys: {list(_mcp_context.keys())}")
            if 'principal' in _mcp_context:
                principal_data = _mcp_context['principal']
                if isinstance(principal_data, dict):
                    logger.info(f"🔍 [TRACE] Principal data: user_id={principal_data.get('user_id')}, email={principal_data.get('email')}, org={principal_data.get('organization_id')}")
                else:
                    logger.info(f"🔍 [TRACE] Principal object: {type(principal_data)}")
        
        try:
            # Extract Principal from MCP context
            if not _mcp_context or 'principal' not in _mcp_context:
                logger.warning(f"🔍 [TRACE] Step 6: MCP_TOOL - NO Principal context available")
                return json.dumps({
                    "error": "Principal context required",
                    "message": "MCP tools require Principal context from FastAPI"
                })
            
            principal_data = _mcp_context['principal']
            principal = Principal.from_dict(principal_data) if isinstance(principal_data, dict) else principal_data
            
            # Validate permission
            if not principal.can_access_tool("list_tickets"):
                return json.dumps({
                    "error": "Permission denied",
                    "message": f"User {principal.email} not authorized to list tickets"
                })
            
            # Direct database access (NO HTTP calls)
            async with get_db_session() as db:
                # Build query with organization isolation
                query = select(Ticket).where(
                    and_(
                        Ticket.organization_id == principal.organization_id,
                        Ticket.is_deleted == False
                    )
                )
                
                # Apply filters
                if status:
                    try:
                        query = query.where(Ticket.status == TicketStatus(status))
                    except ValueError:
                        pass
                
                if category:
                    try:
                        query = query.where(Ticket.category == TicketCategory(category))
                    except ValueError:
                        pass
                
                if priority:
                    try:
                        query = query.where(Ticket.priority == TicketPriority(priority))
                    except ValueError:
                        pass
                
                # Apply pagination
                page_size = min(50, max(1, page_size))
                offset = (page - 1) * page_size
                query = query.order_by(desc(Ticket.created_at)).offset(offset).limit(page_size)
                
                # Execute query
                result = await db.execute(query)
                tickets = result.scalars().all()
                
                # Format response
                ticket_list = []
                for ticket in tickets:
                    ticket_list.append({
                        "ticket_id": str(ticket.id),
                        "title": ticket.title,
                        "category": ticket.category.value,
                        "priority": ticket.priority.value,
                        "status": ticket.status.value,
                        "created_at": ticket.created_at.isoformat()
                    })
                
                response = {
                    "success": True,
                    "tickets": ticket_list,
                    "page": page,
                    "page_size": page_size,
                    "total_returned": len(ticket_list),
                    "organization_id": principal.organization_id
                }
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(f"🔍 [TRACE] Step 7: MCP_TOOL - Successfully listed {len(ticket_list)} tickets for {principal.email} in {execution_time:.2f}ms")
                logger.info(f"🔍 [TRACE] Step 8: MCP_TOOL - Returning results to MCP Server")
                
                return json.dumps(response, indent=2)
        
        except Exception as e:
            logger.error(f"❌ Principal MCP list_tickets failed: {e}")
            return json.dumps({"error": "Tool execution failed", "message": str(e)})
    
    @mcp.tool()
    async def search_tickets(
        query: str = "",
        status: str = "",
        category: str = "",
        priority: str = "",
        page: int = 1,
        page_size: int = 10,
        _mcp_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Search tickets with Principal-based authorization.
        """
        start_time = datetime.now()
        
        try:
            # Extract Principal from MCP context
            if not _mcp_context or 'principal' not in _mcp_context:
                return json.dumps({
                    "error": "Principal context required",
                    "message": "MCP tools require Principal context from FastAPI"
                })
            
            principal_data = _mcp_context['principal']
            principal = Principal.from_dict(principal_data) if isinstance(principal_data, dict) else principal_data
            
            # Validate permission
            if not principal.can_access_tool("search_tickets"):
                return json.dumps({
                    "error": "Permission denied",
                    "message": f"User {principal.email} not authorized to search tickets"
                })
            
            # Direct database access (NO HTTP calls)
            async with get_db_session() as db:
                # Build search query with organization isolation
                search_query = select(Ticket).where(
                    and_(
                        Ticket.organization_id == principal.organization_id,
                        Ticket.is_deleted == False
                    )
                )
                
                # Add search conditions
                if query:
                    search_query = search_query.where(
                        or_(
                            Ticket.title.ilike(f"%{query}%"),
                            Ticket.description.ilike(f"%{query}%")
                        )
                    )
                
                # Apply filters
                if status:
                    try:
                        search_query = search_query.where(Ticket.status == TicketStatus(status))
                    except ValueError:
                        pass
                
                if category:
                    try:
                        search_query = search_query.where(Ticket.category == TicketCategory(category))
                    except ValueError:
                        pass
                
                if priority:
                    try:
                        search_query = search_query.where(Ticket.priority == TicketPriority(priority))
                    except ValueError:
                        pass
                
                # Apply pagination
                page_size = min(50, max(1, page_size))
                offset = (page - 1) * page_size
                search_query = search_query.order_by(desc(Ticket.created_at)).offset(offset).limit(page_size)
                
                # Execute search
                result = await db.execute(search_query)
                tickets = result.scalars().all()
                
                # Format results
                search_results = []
                for ticket in tickets:
                    search_results.append({
                        "ticket_id": str(ticket.id),
                        "title": ticket.title,
                        "description": ticket.description[:200] + "..." if len(ticket.description) > 200 else ticket.description,
                        "category": ticket.category.value,
                        "priority": ticket.priority.value,
                        "status": ticket.status.value,
                        "created_at": ticket.created_at.isoformat()
                    })
                
                response = {
                    "success": True,
                    "query": query,
                    "results": search_results,
                    "page": page,
                    "page_size": page_size,
                    "result_count": len(search_results),
                    "organization_id": principal.organization_id
                }
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(f"✅ Principal MCP: Search found {len(search_results)} tickets for {principal.email} in {execution_time:.2f}ms")
                
                return json.dumps(response, indent=2)
        
        except Exception as e:
            logger.error(f"❌ Principal MCP search_tickets failed: {e}")
            return json.dumps({"error": "Tool execution failed", "message": str(e)})
    
    @mcp.tool()
    async def get_ticket(
        ticket_id: str,
        _mcp_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get ticket with Principal-based authorization.
        """
        start_time = datetime.now()
        
        try:
            # Extract Principal from MCP context
            if not _mcp_context or 'principal' not in _mcp_context:
                return json.dumps({
                    "error": "Principal context required",
                    "message": "MCP tools require Principal context from FastAPI"
                })
            
            principal_data = _mcp_context['principal']
            principal = Principal.from_dict(principal_data) if isinstance(principal_data, dict) else principal_data
            
            # Validate permission
            if not principal.can_access_tool("get_ticket"):
                return json.dumps({
                    "error": "Permission denied",
                    "message": f"User {principal.email} not authorized to get tickets"
                })
            
            # Direct database access (NO HTTP calls)
            async with get_db_session() as db:
                # Get ticket with organization isolation
                result = await db.execute(
                    select(Ticket).where(
                        and_(
                            Ticket.id == ticket_id,
                            Ticket.organization_id == principal.organization_id,
                            Ticket.is_deleted == False
                        )
                    )
                )
                
                ticket = result.scalar_one_or_none()
                if not ticket:
                    return json.dumps({
                        "error": "Ticket not found",
                        "message": f"Ticket {ticket_id} not found or not accessible"
                    })
                
                response = {
                    "success": True,
                    "ticket": {
                        "ticket_id": str(ticket.id),
                        "title": ticket.title,
                        "description": ticket.description,
                        "category": ticket.category.value,
                        "priority": ticket.priority.value,
                        "status": ticket.status.value,
                        "created_at": ticket.created_at.isoformat(),
                        "created_by_id": str(ticket.created_by_id),
                        "organization_id": str(ticket.organization_id)
                    }
                }
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(f"✅ Principal MCP: Retrieved ticket {ticket_id} for {principal.email} in {execution_time:.2f}ms")
                
                return json.dumps(response, indent=2)
        
        except Exception as e:
            logger.error(f"❌ Principal MCP get_ticket failed: {e}")
            return json.dumps({"error": "Tool execution failed", "message": str(e)})
    
    logger.info("✅ Principal-based MCP tools registered (NO HTTP calls)")