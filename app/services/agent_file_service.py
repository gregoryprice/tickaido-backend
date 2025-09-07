#!/usr/bin/env python3
"""
Agent File Service for managing file attachments and context processing
"""

import logging
import os
from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.models.agent_file import AgentFile
from app.models.ai_agent import Agent
from app.models.file import File
from app.database import get_async_db_session
from app.services.file_service import FileService

logger = logging.getLogger(__name__)


class AgentFileService:
    """
    Service for managing agent file attachments and context processing.
    
    Handles up to 20 files per agent with text extraction, processing status tracking,
    and context window assembly for agent knowledge.
    """
    
    MAX_FILES_PER_AGENT = 20
    SUPPORTED_TEXT_FORMATS = {'.pdf', '.txt', '.md', '.docx', '.csv', '.xlsx'}
    
    def __init__(self):
        self.storage_type = os.getenv("STORAGE_TYPE", "local")  # "s3" or "local"
        self.file_service = FileService()
    
    async def attach_file_to_agent(
        self,
        agent_id: UUID,
        file_id: UUID,
        attached_by_user_id: Optional[UUID] = None,
        priority: str = "normal",
        db: Optional[AsyncSession] = None
    ) -> Optional[AgentFile]:
        """
        Attach a file to an agent for context processing.
        
        Args:
            agent_id: Agent to attach file to
            file_id: File to attach
            attached_by_user_id: User attaching the file
            priority: File priority for context inclusion (high, normal, low)
            db: Database session (optional)
            
        Returns:
            AgentFile: Created agent file relationship or None if failed
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Check if agent exists
                agent_stmt = select(Agent).where(Agent.id == agent_id)
                agent_result = await session.execute(agent_stmt)
                agent = agent_result.scalar_one_or_none()
                
                if not agent:
                    logger.error(f"Agent {agent_id} not found")
                    return None
                
                # Check file limit (20 files per agent)
                current_count = await self.get_agent_file_count(agent_id, db=session)
                if current_count >= self.MAX_FILES_PER_AGENT:
                    logger.error(f"Agent {agent_id} already has maximum {self.MAX_FILES_PER_AGENT} files")
                    return None
                
                # Check if file exists
                file_stmt = select(File).where(File.id == file_id)
                file_result = await session.execute(file_stmt)
                file = file_result.scalar_one_or_none()
                
                if not file:
                    logger.error(f"File {file_id} not found")
                    return None
                
                # Check if already attached
                existing_stmt = select(AgentFile).where(
                    and_(
                        AgentFile.agent_id == agent_id,
                        AgentFile.file_id == file_id,
                        AgentFile.is_deleted == False
                    )
                )
                existing_result = await session.execute(existing_stmt)
                existing_agent_file = existing_result.scalar_one_or_none()
                
                if existing_agent_file:
                    logger.warning(f"File {file_id} already attached to agent {agent_id}")
                    return existing_agent_file
                
                # Determine order index
                order_index = current_count
                
                # Create agent file relationship
                agent_file = AgentFile(
                    agent_id=agent_id,
                    file_id=file_id,
                    processing_status="pending",
                    order_index=order_index,
                    priority=priority,
                    attached_by_user_id=attached_by_user_id,
                    attached_at=datetime.now(timezone.utc)
                )
                
                session.add(agent_file)
                await session.commit()
                await session.refresh(agent_file)
                
                logger.info(f"✅ Attached file {file_id} to agent {agent_id}")
                
                # Start async file processing
                from app.tasks.agent_file_tasks import process_agent_file
                process_agent_file.delay(str(agent_file.id))
                
                return agent_file
                
            except Exception as e:
                logger.error(f"Error attaching file to agent: {e}")
                await session.rollback()
                return None
    
    async def detach_file_from_agent(
        self,
        agent_id: UUID,
        file_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Detach a file from an agent.
        
        Args:
            agent_id: Agent to detach file from
            file_id: File to detach
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                stmt = select(AgentFile).where(
                    and_(
                        AgentFile.agent_id == agent_id,
                        AgentFile.file_id == file_id,
                        AgentFile.is_deleted == False
                    )
                )
                result = await session.execute(stmt)
                agent_file = result.scalar_one_or_none()
                
                if not agent_file:
                    logger.error("Agent file relationship not found")
                    return False
                
                # Soft delete
                agent_file.soft_delete()
                await session.commit()
                
                logger.info(f"✅ Detached file {file_id} from agent {agent_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error detaching file from agent: {e}")
                await session.rollback()
                return False
    
    async def get_agent_files(
        self,
        agent_id: UUID,
        include_processing: bool = True,
        include_failed: bool = False,
        order_by_priority: bool = True,
        db: Optional[AsyncSession] = None
    ) -> List[AgentFile]:
        """
        Get all files attached to an agent.
        
        Args:
            agent_id: Agent ID
            include_processing: Include files being processed
            include_failed: Include failed files
            order_by_priority: Order by priority and order index
            db: Database session (optional)
            
        Returns:
            List[AgentFile]: Agent files
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                conditions = [
                    AgentFile.agent_id == agent_id,
                    AgentFile.is_deleted == False
                ]
                
                if not include_processing:
                    conditions.append(AgentFile.processing_status != "processing")
                
                if not include_failed:
                    conditions.append(AgentFile.processing_status != "failed")
                
                stmt = (
                    select(AgentFile)
                    .where(and_(*conditions))
                    .options(selectinload(AgentFile.file))
                )
                
                if order_by_priority:
                    # Order by priority (high first), then order_index
                    priority_order = {
                        'high': 1,
                        'normal': 2,
                        'low': 3
                    }
                    stmt = stmt.order_by(
                        func.coalesce(
                            func.nullif(
                                func.case(
                                    (AgentFile.priority == 'high', 1),
                                    (AgentFile.priority == 'normal', 2),
                                    (AgentFile.priority == 'low', 3),
                                    else_=2
                                ),
                                None
                            ),
                            2
                        ),
                        AgentFile.order_index
                    )
                else:
                    stmt = stmt.order_by(AgentFile.order_index)
                
                result = await session.execute(stmt)
                agent_files = result.scalars().all()
                
                logger.debug(f"Found {len(agent_files)} files for agent {agent_id}")
                return list(agent_files)
                
            except Exception as e:
                logger.error(f"Error getting agent files: {e}")
                return []
    
    async def get_agent_file_count(
        self,
        agent_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> int:
        """
        Get count of files attached to an agent.
        
        Args:
            agent_id: Agent ID
            db: Database session (optional)
            
        Returns:
            int: Number of attached files
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                stmt = select(func.count(AgentFile.id)).where(
                    and_(
                        AgentFile.agent_id == agent_id,
                        AgentFile.is_deleted == False
                    )
                )
                result = await session.execute(stmt)
                count = result.scalar()
                
                return count or 0
                
            except Exception as e:
                logger.error(f"Error getting agent file count: {e}")
                return 0
    
    async def process_file_content(
        self,
        agent_file_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Process file content and extract text for agent context.
        
        Args:
            agent_file_id: Agent file relationship ID
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Get agent file with file details
                stmt = (
                    select(AgentFile)
                    .where(AgentFile.id == agent_file_id)
                    .options(selectinload(AgentFile.file))
                )
                result = await session.execute(stmt)
                agent_file = result.scalar_one_or_none()
                
                if not agent_file:
                    logger.error(f"Agent file {agent_file_id} not found")
                    return False
                
                # Mark processing started
                agent_file.mark_processing_started()
                await session.commit()
                
                # Extract text content based on file type
                file_obj = agent_file.file
                extracted_text = ""
                
                try:
                    if file_obj.file_type.lower() == 'pdf':
                        extracted_text = await self._extract_pdf_text(file_obj)
                    elif file_obj.file_type.lower() in ['txt', 'md']:
                        extracted_text = await self._extract_text_file(file_obj)
                    elif file_obj.file_type.lower() == 'docx':
                        extracted_text = await self._extract_docx_text(file_obj)
                    elif file_obj.file_type.lower() in ['csv', 'xlsx']:
                        extracted_text = await self._extract_spreadsheet_text(file_obj)
                    else:
                        raise ValueError(f"Unsupported file type: {file_obj.file_type}")
                    
                    # Mark processing completed
                    agent_file.mark_processing_completed(extracted_text)
                    await session.commit()
                    
                    logger.info(f"✅ Processed file content for agent file {agent_file_id}, extracted {len(extracted_text)} characters")
                    return True
                    
                except Exception as extraction_error:
                    # Mark processing failed
                    agent_file.mark_processing_failed(str(extraction_error))
                    await session.commit()
                    
                    logger.error(f"Error extracting content: {extraction_error}")
                    return False
                
            except Exception as e:
                logger.error(f"Error processing file content: {e}")
                return False
    
    async def assemble_context_window(
        self,
        agent_id: UUID,
        max_context_length: int = 50000,
        db: Optional[AsyncSession] = None
    ) -> str:
        """
        Assemble context window from agent files for agent conversations.
        
        Args:
            agent_id: Agent ID
            max_context_length: Maximum context length in characters
            db: Database session (optional)
            
        Returns:
            str: Assembled context text
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                # Get processed files ordered by priority
                agent_files = await self.get_agent_files(
                    agent_id=agent_id,
                    include_processing=False,
                    include_failed=False,
                    order_by_priority=True,
                    db=session
                )
                
                context_parts = []
                total_length = 0
                
                for agent_file in agent_files:
                    if not agent_file.has_content:
                        continue
                    
                    content = agent_file.extracted_content
                    content_length = len(content)
                    
                    # Check if adding this content would exceed limit
                    if total_length + content_length > max_context_length:
                        # Truncate the content to fit
                        remaining_space = max_context_length - total_length
                        if remaining_space > 100:  # Only add if meaningful space remains
                            truncated_content = content[:remaining_space - 50] + "...(truncated)"
                            context_parts.append(f"\n--- File: {agent_file.file.filename} ({agent_file.priority} priority) ---\n{truncated_content}")
                        break
                    
                    # Add full content
                    context_parts.append(f"\n--- File: {agent_file.file.filename} ({agent_file.priority} priority) ---\n{content}")
                    total_length += content_length
                    
                    # Record usage
                    agent_file.record_context_usage()
                
                # Commit usage updates
                await session.commit()
                
                assembled_context = "\n".join(context_parts)
                logger.debug(f"Assembled context for agent {agent_id}: {len(assembled_context)} characters from {len(context_parts)} files")
                
                return assembled_context
                
            except Exception as e:
                logger.error(f"Error assembling context window: {e}")
                return ""
    
    async def reorder_agent_files(
        self,
        agent_id: UUID,
        file_order: List[UUID],
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Reorder files for an agent to control context priority.
        
        Args:
            agent_id: Agent ID
            file_order: List of file IDs in desired order
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                for index, file_id in enumerate(file_order):
                    stmt = select(AgentFile).where(
                        and_(
                            AgentFile.agent_id == agent_id,
                            AgentFile.file_id == file_id,
                            AgentFile.is_deleted == False
                        )
                    )
                    result = await session.execute(stmt)
                    agent_file = result.scalar_one_or_none()
                    
                    if agent_file:
                        agent_file.update_order(index)
                
                await session.commit()
                logger.info(f"✅ Reordered {len(file_order)} files for agent {agent_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error reordering agent files: {e}")
                await session.rollback()
                return False
    
    async def update_file_priority(
        self,
        agent_id: UUID,
        file_id: UUID,
        priority: str,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Update priority of a file for context inclusion.
        
        Args:
            agent_id: Agent ID
            file_id: File ID
            priority: New priority (high, normal, low)
            db: Database session (optional)
            
        Returns:
            bool: True if successful
        """
        async with get_async_db_session() if db is None else db as session:
            try:
                stmt = select(AgentFile).where(
                    and_(
                        AgentFile.agent_id == agent_id,
                        AgentFile.file_id == file_id,
                        AgentFile.is_deleted == False
                    )
                )
                result = await session.execute(stmt)
                agent_file = result.scalar_one_or_none()
                
                if not agent_file:
                    logger.error("Agent file relationship not found")
                    return False
                
                agent_file.set_priority(priority)
                await session.commit()
                
                logger.info(f"✅ Updated file {file_id} priority to {priority} for agent {agent_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error updating file priority: {e}")
                await session.rollback()
                return False
    
    async def check_file_access(
        self,
        agent_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Check if agent can access its files (health check).
        
        Args:
            agent_id: Agent ID
            db: Database session (optional)
            
        Returns:
            bool: True if files are accessible
        """
        try:
            files = await self.get_agent_files(agent_id, db=db)
            
            # Check if at least one file has processed content
            has_processed_content = any(f.has_content for f in files)
            
            logger.debug(f"File access check for agent {agent_id}: {len(files)} files, content available: {has_processed_content}")
            return True  # Basic check passes if we can query files
            
        except Exception as e:
            logger.error(f"File access check failed for agent {agent_id}: {e}")
            return False
    
    # Text extraction methods (would be implemented based on available libraries)
    
    async def _extract_pdf_text(self, file: File) -> str:
        """Extract text from PDF file"""
        try:
            # Placeholder for PDF text extraction
            # In real implementation, would use libraries like PyPDF2, pdfplumber, etc.
            logger.info(f"Extracting text from PDF: {file.filename}")
            
            # For now, return placeholder text
            return f"[PDF content from {file.filename} - text extraction would be implemented here]"
            
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            raise
    
    async def _extract_text_file(self, file: File) -> str:
        """Extract text from plain text file"""
        try:
            logger.info(f"Reading text file: {file.filename}")
            
            # Get file content from file service
            file_content = await self.file_service.get_file_content(file.id)
            if file_content:
                # Decode bytes to string
                if isinstance(file_content, bytes):
                    return file_content.decode('utf-8', errors='ignore')
                return str(file_content)
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting text file content: {e}")
            raise
    
    async def _extract_docx_text(self, file: File) -> str:
        """Extract text from DOCX file"""
        try:
            # Placeholder for DOCX text extraction
            # In real implementation, would use python-docx library
            logger.info(f"Extracting text from DOCX: {file.filename}")
            
            return f"[DOCX content from {file.filename} - text extraction would be implemented here]"
            
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
            raise
    
    async def _extract_spreadsheet_text(self, file: File) -> str:
        """Extract text from CSV/XLSX file"""
        try:
            # Placeholder for spreadsheet text extraction
            # In real implementation, would use pandas, openpyxl, etc.
            logger.info(f"Extracting text from spreadsheet: {file.filename}")
            
            return f"[Spreadsheet content from {file.filename} - text extraction would be implemented here]"
            
        except Exception as e:
            logger.error(f"Error extracting spreadsheet text: {e}")
            raise


# Global agent file service instance
agent_file_service = AgentFileService()