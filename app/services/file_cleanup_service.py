#!/usr/bin/env python3
"""
File Cleanup Service for cascade deletion of attached files
"""

import logging
from typing import List, Set
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from app.models.file import File, FileStatus
from app.models.chat import Message
from app.models.ticket import Ticket

logger = logging.getLogger(__name__)


class FileCleanupService:
    """Service for cleaning up orphaned files when threads or tickets are deleted"""
    
    async def collect_thread_file_ids(
        self,
        db: AsyncSession,
        thread_id: UUID
    ) -> Set[UUID]:
        """
        Collect all file IDs referenced in messages of a thread.
        
        Args:
            db: Database session
            thread_id: Thread ID to collect file IDs from
            
        Returns:
            Set of file UUIDs referenced by the thread
        """
        try:
            # Get all messages in the thread that have attachments
            query = select(Message.attachments).where(
                and_(
                    Message.thread_id == thread_id,
                    Message.attachments.isnot(None)
                )
            )
            
            result = await db.execute(query)
            attachment_arrays = result.scalars().all()
            
            file_ids = set()
            for attachments in attachment_arrays:
                if attachments and isinstance(attachments, list):
                    for attachment in attachments:
                        if isinstance(attachment, dict) and 'file_id' in attachment:
                            try:
                                file_ids.add(UUID(attachment['file_id']))
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Invalid file_id in attachment: {attachment.get('file_id')}: {e}")
            
            logger.info(f"Collected {len(file_ids)} unique file IDs from thread {thread_id}")
            return file_ids
            
        except Exception as e:
            logger.error(f"Error collecting file IDs from thread {thread_id}: {e}")
            return set()
    
    async def collect_ticket_file_ids(
        self,
        db: AsyncSession,
        ticket_id: UUID
    ) -> Set[UUID]:
        """
        Collect all file IDs referenced by a ticket.
        
        Args:
            db: Database session
            ticket_id: Ticket ID to collect file IDs from
            
        Returns:
            Set of file UUIDs referenced by the ticket
        """
        try:
            # Get ticket attachments
            query = select(Ticket.attachments).where(Ticket.id == ticket_id)
            result = await db.execute(query)
            attachments = result.scalar_one_or_none()
            
            file_ids = set()
            if attachments and isinstance(attachments, list):
                for attachment in attachments:
                    if isinstance(attachment, dict) and 'file_id' in attachment:
                        try:
                            file_ids.add(UUID(attachment['file_id']))
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Invalid file_id in ticket attachment: {attachment.get('file_id')}: {e}")
            
            logger.info(f"Collected {len(file_ids)} unique file IDs from ticket {ticket_id}")
            return file_ids
            
        except Exception as e:
            logger.error(f"Error collecting file IDs from ticket {ticket_id}: {e}")
            return set()
    
    async def cascade_delete_thread_files(
        self,
        db: AsyncSession,
        thread_id: UUID,
        organization_id: UUID
    ) -> int:
        """
        Delete all files attached to messages in a thread.
        
        Args:
            db: Database session
            thread_id: Thread ID whose files should be deleted
            organization_id: Organization ID for security validation
            
        Returns:
            Number of files deleted
        """
        try:
            # Collect all file IDs from thread messages
            file_ids = await self.collect_thread_file_ids(db, thread_id)
            
            if not file_ids:
                logger.info(f"No files to delete for thread {thread_id}")
                return 0
            
            # Delete the files (organization validation included for security)
            deleted_count = await self._delete_files_by_ids(db, file_ids, organization_id)
            
            logger.info(f"Cascade deleted {deleted_count} files from thread {thread_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cascade deleting files for thread {thread_id}: {e}")
            return 0
    
    async def cascade_delete_ticket_files(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        organization_id: UUID
    ) -> int:
        """
        Delete all files attached to a ticket.
        
        Args:
            db: Database session
            ticket_id: Ticket ID whose files should be deleted
            organization_id: Organization ID for security validation
            
        Returns:
            Number of files deleted
        """
        try:
            # Collect all file IDs from ticket attachments
            file_ids = await self.collect_ticket_file_ids(db, ticket_id)
            
            if not file_ids:
                logger.info(f"No files to delete for ticket {ticket_id}")
                return 0
            
            # Delete the files (organization validation included for security)
            deleted_count = await self._delete_files_by_ids(db, file_ids, organization_id)
            
            logger.info(f"Cascade deleted {deleted_count} files from ticket {ticket_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cascade deleting files for ticket {ticket_id}: {e}")
            return 0
    
    async def _delete_files_by_ids(
        self,
        db: AsyncSession,
        file_ids: Set[UUID],
        organization_id: UUID
    ) -> int:
        """
        Delete files by their IDs with organization validation.
        
        Args:
            db: Database session
            file_ids: Set of file UUIDs to delete
            organization_id: Organization ID for security validation
            
        Returns:
            Number of files actually deleted
        """
        if not file_ids:
            return 0
        
        try:
            # First, get the files to validate organization and log what we're deleting
            query = select(File).where(
                and_(
                    File.id.in_(file_ids),
                    File.organization_id == organization_id,
                    File.is_deleted == False  # Don't delete already deleted files
                )
            )
            
            result = await db.execute(query)
            files_to_delete = result.scalars().all()
            
            if not files_to_delete:
                logger.warning(f"No valid files found for deletion from {len(file_ids)} requested IDs")
                return 0
            
            # Log what we're about to delete for audit purposes
            filenames = [f.filename for f in files_to_delete]
            logger.info(f"Deleting {len(files_to_delete)} files: {filenames}")
            
            # Perform soft delete by updating status
            file_ids_to_delete = [f.id for f in files_to_delete]
            
            # Option 1: Soft delete (recommended for audit trail)
            from sqlalchemy import update
            from datetime import datetime, timezone
            
            soft_delete_query = update(File).where(
                File.id.in_(file_ids_to_delete)
            ).values(
                status=FileStatus.DELETED,
                updated_at=datetime.now(timezone.utc)
            )
            
            result = await db.execute(soft_delete_query)
            deleted_count = result.rowcount
            
            # Option 2: Hard delete (uncomment if preferred)
            # hard_delete_query = delete(File).where(File.id.in_(file_ids_to_delete))
            # result = await db.execute(hard_delete_query)
            # deleted_count = result.rowcount
            
            await db.commit()
            
            logger.info(f"Successfully soft-deleted {deleted_count} files")
            return deleted_count
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting files by IDs: {e}")
            return 0
    
    async def cleanup_orphaned_files(
        self,
        db: AsyncSession,
        organization_id: UUID,
        dry_run: bool = True
    ) -> int:
        """
        Find and optionally delete files that are no longer referenced by any thread or ticket.
        This is a utility method for cleanup tasks.
        
        Args:
            db: Database session
            organization_id: Organization ID to limit cleanup scope
            dry_run: If True, only count orphaned files without deleting
            
        Returns:
            Number of orphaned files found (or deleted if not dry run)
        """
        try:
            # Get all file IDs in the organization
            all_files_query = select(File.id).where(
                and_(
                    File.organization_id == organization_id,
                    File.status != FileStatus.DELETED
                )
            )
            result = await db.execute(all_files_query)
            all_file_ids = set(result.scalars().all())
            
            if not all_file_ids:
                logger.info("No files found for orphan cleanup")
                return 0
            
            # Get all referenced file IDs from messages
            messages_query = select(Message.attachments).where(
                Message.attachments.isnot(None)
            )
            result = await db.execute(messages_query)
            message_attachments = result.scalars().all()
            
            referenced_file_ids = set()
            for attachments in message_attachments:
                if attachments and isinstance(attachments, list):
                    for attachment in attachments:
                        if isinstance(attachment, dict) and 'file_id' in attachment:
                            try:
                                referenced_file_ids.add(UUID(attachment['file_id']))
                            except (ValueError, TypeError):
                                pass  # Skip invalid UUIDs
            
            # Get all referenced file IDs from tickets
            tickets_query = select(Ticket.attachments).where(
                Ticket.attachments.isnot(None)
            )
            result = await db.execute(tickets_query)
            ticket_attachments = result.scalars().all()
            
            for attachments in ticket_attachments:
                if attachments and isinstance(attachments, list):
                    for attachment in attachments:
                        if isinstance(attachment, dict) and 'file_id' in attachment:
                            try:
                                referenced_file_ids.add(UUID(attachment['file_id']))
                            except (ValueError, TypeError):
                                pass  # Skip invalid UUIDs
            
            # Find orphaned files
            orphaned_file_ids = all_file_ids - referenced_file_ids
            
            logger.info(f"Found {len(orphaned_file_ids)} orphaned files out of {len(all_file_ids)} total")
            
            if dry_run or not orphaned_file_ids:
                return len(orphaned_file_ids)
            
            # Delete orphaned files
            deleted_count = await self._delete_files_by_ids(db, orphaned_file_ids, organization_id)
            logger.info(f"Cleaned up {deleted_count} orphaned files")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during orphaned file cleanup: {e}")
            return 0


# Global service instance
file_cleanup_service = FileCleanupService()