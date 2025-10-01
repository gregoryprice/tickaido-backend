#!/usr/bin/env python3
"""
TicketAttachmentService - Process attachments using ticket.file_ids array
Implements the new file association pattern from PRP specification
"""

import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File
from app.models.ticket import Ticket
from app.models.user import User
from app.services.ai_analysis_service import AIAnalysisService
from app.services.file_processing_service import FileProcessingService
from app.services.file_service import FileService

logger = logging.getLogger(__name__)


class TicketAttachmentService:
    """Process attachments using ticket.file_ids array"""
    
    def __init__(self):
        self.file_service = FileService()
        self.file_processor = FileProcessingService()
        self.ai_service = AIAnalysisService()
    
    async def create_ticket_with_files(
        self,
        db: AsyncSession,
        ticket_data: dict,
        file_ids: List[UUID],
        user: User
    ) -> Ticket:
        """Create ticket with file attachments using file_ids array"""
        
        # Validate all files exist and belong to user's organization
        validated_files = []
        for file_id in file_ids:
            file_obj = await self.file_service.get_file(db, file_id)
            if not file_obj or file_obj.organization_id != user.organization_id:
                raise ValueError(f"File {file_id} not found or not accessible")
            validated_files.append(file_obj)
        
        # Create ticket with attachments array (correct field name)
        from app.services.ticket_service import TicketService
        ticket_service = TicketService()
        
        # Format file_ids as attachments array for the ticket model
        ticket_data["attachments"] = [{"file_id": str(fid)} for fid in file_ids]
        ticket = await ticket_service.create_ticket(
            db=db,
            ticket_data=ticket_data,
            created_by_id=user.id,
            organization_id=user.organization_id
        )
        
        # Process files for AI enhancement
        attachment_context = []
        for file_obj in validated_files:
            # Ensure file is processed
            if file_obj.status.value == "uploaded":
                await self.file_processor.process_uploaded_file(db, file_obj)
            
            # Extract context for ticket analysis
            if file_obj.extracted_context:
                text_content = self._extract_text_from_context(file_obj.extracted_context)
                attachment_context.append({
                    "filename": file_obj.filename,
                    "content": text_content,
                    "type": file_obj.file_type.value,
                    "summary": file_obj.content_summary
                })
        
        # Enhance ticket with file context
        if attachment_context:
            enhanced_analysis = await self.ai_service.analyze_ticket_with_attachments(
                title=ticket.title,
                description=ticket.description,
                attachments=attachment_context
            )
            
            # Update ticket with enhanced analysis
            if enhanced_analysis.confidence > 0.7:
                ticket.category = enhanced_analysis.suggested_category
                ticket.priority = enhanced_analysis.suggested_priority
                ticket.ai_confidence_score = str(enhanced_analysis.confidence)
                ticket.ai_reasoning = enhanced_analysis.reasoning
        
        await db.commit()
        return ticket
    
    async def add_files_to_ticket(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        new_file_ids: List[UUID],
        user: User
    ) -> Ticket:
        """Add files to existing ticket via file_ids array"""
        
        # Get ticket
        stmt = select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.organization_id == user.organization_id
        )
        result = await db.execute(stmt)
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            raise ValueError("Ticket not found")
        
        # Validate new files
        for file_id in new_file_ids:
            file_obj = await self.file_service.get_file(db, file_id)
            if not file_obj or file_obj.organization_id != user.organization_id:
                raise ValueError(f"File {file_id} not accessible")
        
        # Update ticket attachments array
        current_attachments = ticket.attachments or []
        # Extract current file_ids
        current_file_ids = [att.get("file_id") for att in current_attachments if isinstance(att, dict) and att.get("file_id")]
        # Add new file IDs
        new_file_strs = [str(fid) for fid in new_file_ids]
        all_file_ids = list(set(current_file_ids + new_file_strs))
        # Update attachments array
        ticket.attachments = [{"file_id": fid} for fid in all_file_ids]
        
        await db.commit()
        return ticket
    
    async def get_ticket_files(self, db: AsyncSession, ticket_id: UUID) -> List[File]:
        """Get all files associated with a ticket"""
        
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await db.execute(stmt)
        ticket = result.scalar_one_or_none()
        
        if not ticket or not ticket.attachments:
            return []
        
        files = []
        # Extract file IDs from attachments array
        for attachment in ticket.attachments:
            if not isinstance(attachment, dict) or "file_id" not in attachment:
                continue
            file_id_str = attachment["file_id"]
            try:
                file_id = UUID(file_id_str)
                file_obj = await self.file_service.get_file(db, file_id)
                if file_obj and not file_obj.is_deleted:
                    files.append(file_obj)
            except ValueError:
                # Skip invalid UUIDs
                logger.warning(f"Invalid file ID in ticket {ticket_id}: {file_id_str}")
                continue
        
        return files
    
    async def remove_file_from_ticket(
        self,
        db: AsyncSession,
        ticket_id: UUID,
        file_id: UUID,
        user: User
    ) -> Ticket:
        """Remove a file from ticket's file_ids array"""
        
        # Get ticket
        stmt = select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.organization_id == user.organization_id
        )
        result = await db.execute(stmt)
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            raise ValueError("Ticket not found")
        
        if not ticket.attachments:
            return ticket
        
        # Remove file ID from attachments array
        file_id_str = str(file_id)
        updated_attachments = [att for att in ticket.attachments 
                             if not (isinstance(att, dict) and att.get("file_id") == file_id_str)]
        ticket.attachments = updated_attachments
        
        await db.commit()
        return ticket
    
    def _extract_text_from_context(self, extracted_context: Dict[str, Any]) -> str:
        """Extract all text content from extracted_context JSON"""
        text_parts = []
        
        # Document text
        if "document" in extracted_context:
            doc = extracted_context["document"]
            for page in doc.get("pages", []):
                page_text = page.get("text", "")
                if page_text:
                    text_parts.append(page_text)
        
        # Image text (OCR results)
        if "image" in extracted_context:
            img = extracted_context["image"]
            
            # Image description
            if img.get("description"):
                text_parts.append(f"Image shows: {img['description']}")
            
            # Text found in image
            text_regions = img.get("text_regions", [])
            if text_regions:
                image_text = " ".join([region.get("text", "") for region in text_regions])
                if image_text:
                    text_parts.append(f"Text in image: {image_text}")
        
        # Audio transcription
        if "audio" in extracted_context:
            audio = extracted_context["audio"]
            transcription_text = audio.get("transcription", {}).get("text", "")
            if transcription_text:
                text_parts.append(f"Audio content: {transcription_text}")
        
        return "\n\n".join(text_parts)