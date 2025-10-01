#!/usr/bin/env python3
"""
FileProcessingService - Process files and store unified context in JSON format
Coordinates DocumentParserService, OCRService, TranscriptionService, VisionAnalysisService, and AIAnalysisService
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File, FileStatus
from app.schemas.file import FileProcessingStatusResponse
from app.services.ai_analysis_service import AIAnalysisService
from app.services.document_parser_service import DocumentParserService
from app.services.file_service import FileService
from app.services.ocr_service import OCRService
from app.services.transcription_service import TranscriptionService
from app.services.vision_analysis_service import VisionAnalysisService

logger = logging.getLogger(__name__)


class FileProcessingService:
    """Process files and store unified context in JSON format"""
    
    def __init__(self):
        self.document_parser = DocumentParserService()  # Document structure parsing
        self.ocr_service = OCRService()                 # Text extraction from images
        self.transcription_service = TranscriptionService()   # Audio/video transcription
        self.vision_service = VisionAnalysisService()   # Computer vision analysis
        self.ai_service = AIAnalysisService()          # LLM-based content analysis
        self.file_service = FileService()              # File storage operations
    
    async def process_uploaded_file(self, db: AsyncSession, file_obj: File) -> None:
        """Process file and store extracted context in unified JSON format"""
        
        # Safety check: don't process soft-deleted files
        if file_obj.is_deleted:
            logger.warning(f"Skipping processing for soft-deleted file: {file_obj.id}")
            return
        
        # Safety check: don't process if already processing (idempotency)
        if file_obj.status == FileStatus.PROCESSING:
            logger.info(f"File {file_obj.id} is already being processed, skipping")
            return
            
        file_obj.start_processing()
        await db.commit()
        
        try:
            extracted_context = {}
            
            # Get file content from storage
            file_content = await self.file_service.get_file_content(db, file_obj.id)
            if not file_content:
                raise Exception("Unable to retrieve file content from storage")
            
            # Process based on file type
            logger.debug(f"DEBUG: File processing - MIME: {file_obj.mime_type}, is_text_file: {file_obj.is_text_file}")
            
            if file_obj.is_text_file or file_obj.mime_type == "application/pdf":
                logger.info("DEBUG: Using document processing path")
                document_data = await self._extract_document_content(file_obj, file_content)
                extracted_context["document"] = document_data
                file_obj.extraction_method = "document_parser"
            
            elif file_obj.is_image_file:
                logger.info("DEBUG: Using image processing path")
                image_data = await self._extract_image_content(file_obj, file_content)
                extracted_context["image"] = image_data
                file_obj.extraction_method = "vision_ocr"
            
            elif file_obj.is_media_file:
                logger.info("DEBUG: Using audio processing path")
                audio_data = await self._extract_audio_content(file_obj, file_content)
                extracted_context["audio"] = audio_data
                file_obj.extraction_method = "speech_transcription"
            
            # Validate and clean extracted context before storing
            cleaned_context = self._validate_and_clean_context(extracted_context)
            file_obj.extracted_context = cleaned_context
            
            # Generate AI summary from all extracted content
            all_text_content = self._extract_text_from_context(extracted_context)
            if all_text_content:
                file_obj.content_summary = await self.ai_service.generate_summary(
                    all_text_content,
                    max_length=500
                )
                
                # Detect language
                file_obj.language_detection = await self.ai_service.detect_language(
                    all_text_content
                )
            
            file_obj.complete_processing()
            logger.info(f"Successfully processed file {file_obj.id}")
            
        except Exception as e:
            logger.error(f"File processing failed for {file_obj.id}: {e}")
            file_obj.fail_processing(str(e)[:500])  # Limit error message length
        
        finally:
            await db.commit()
    
    async def _extract_document_content(self, file_obj: File, file_content: bytes) -> Dict[str, Any]:
        """Extract structured document content (AWS Textract style)"""
        
        logger.debug(f"DEBUG: _extract_document_content called with MIME: {file_obj.mime_type}")
        
        if file_obj.mime_type == "application/pdf":
            logger.debug("DEBUG: Calling document_parser.analyze_document for PDF")
            # Use document parser with structure detection
            result = await self.document_parser.analyze_document(
                file_content,
                features=["TEXT", "TABLES", "FORMS", "LAYOUT"]
            )
            logger.debug(f"DEBUG: Document parser returned result with {len(result.get('pages', []))} pages")
            
            # Check if PDF text extraction failed and fallback to OCR if needed
            pages_data = []
            for page in result["pages"]:
                page_data = {
                    "page_number": page["page_number"],
                    "text": page["text"],
                    "blocks": page["blocks"],  # Paragraphs, tables, forms
                    "confidence": page["confidence"]
                }
                
                # If text extraction failed (empty or contains PDF bytes), try OCR
                if not page_data["text"] or page_data["text"].startswith('%PDF'):
                    try:
                        # Convert PDF page to image and use OCR
                        import pymupdf
                        doc = pymupdf.open(stream=file_content, filetype="pdf")
                        pdf_page = doc[page["page_number"] - 1]  # Convert to 0-based index
                        
                        # Render page as image with 2x zoom for better OCR
                        matrix = pymupdf.Matrix(2, 2)
                        pix = pdf_page.get_pixmap(matrix=matrix)
                        img_data = pix.tobytes("png")
                        doc.close()
                        
                        # Use OCR service to extract text from the image
                        ocr_result = await self.ocr_service.extract_text_with_regions(img_data)
                        if ocr_result.get("full_text"):
                            page_data["text"] = ocr_result["full_text"]
                            page_data["confidence"] = ocr_result.get("total_confidence", 0.5)
                            # Update extraction method to indicate OCR was used
                            file_obj.extraction_method = "document_parser_ocr_fallback"
                        
                    except Exception as e:
                        # OCR failed too, leave as empty text
                        logger.warning(f"PDF text extraction and OCR fallback failed for page {page['page_number']}: {e}")
                
                pages_data.append(page_data)
            
            return {
                "pages": pages_data,
                "metadata": {
                    "total_pages": result["metadata"]["total_pages"],
                    "language": result["metadata"].get("language", "auto-detected"),
                    "document_type": result["metadata"]["document_type"]
                }
            }
        
        else:
            # Plain text or office documents
            text_content = await self.document_parser.extract_text(file_content)
            return {
                "pages": [
                    {
                        "page_number": 1,
                        "text": text_content,
                        "blocks": [{"type": "paragraph", "text": text_content, "confidence": 0.99}]
                    }
                ],
                "metadata": {
                    "total_pages": 1,
                    "language": "auto-detected",
                    "document_type": "text"
                }
            }
    
    async def _extract_image_content(self, file_obj: File, file_content: bytes) -> Dict[str, Any]:
        """Extract structured image content with OCR and vision analysis"""
        
        logger.info(f"DEBUG: _extract_image_content called with MIME: {file_obj.mime_type}")
        
        logger.info("DEBUG: Calling vision_service.analyze_image")
        # Vision analysis
        vision_result = await self.vision_service.analyze_image(
            file_content,
            features=["DESCRIPTION", "OBJECTS", "TEXT", "METADATA"]
        )
        logger.info(f"DEBUG: Vision analysis result: {vision_result}")
        
        logger.info("DEBUG: Calling ocr_service.extract_text_with_regions")
        # OCR extraction
        ocr_result = await self.ocr_service.extract_text_with_regions(file_content)
        
        logger.info(f"DEBUG: OCR analysis result: {ocr_result}")

        return {
            "description": vision_result.get("description", ""),
            "objects": vision_result.get("objects", []),
            "text_regions": [
                {
                    "text": region["text"],
                    "confidence": region["confidence"],
                    "geometry": region["geometry"]
                }
                for region in ocr_result.get("text_regions", [])
            ],
            "metadata": vision_result.get("metadata", {})
        }
    
    async def _extract_audio_content(self, file_obj: File, file_content: bytes) -> Dict[str, Any]:
        """Extract audio transcription and analysis"""
        
        # Transcription
        transcription_result = await self.transcription_service.transcribe_with_segments(
            file_content
        )
        
        # AI analysis of transcription
        if transcription_result["text"]:
            analysis = await self.ai_service.analyze_audio_content(
                transcription_result["text"]
            )
            
            return {
                "transcription": {
                    "text": transcription_result["text"],
                    "language": transcription_result["language"],
                    "confidence": transcription_result["confidence"],
                    "duration_seconds": transcription_result["duration"],
                    "segments": transcription_result["segments"]
                },
                "analysis": {
                    "sentiment": analysis["sentiment"],
                    "key_topics": analysis["key_topics"],
                    "urgency_level": analysis["urgency_level"]
                }
            }
        
        return {
            "transcription": {"text": "", "language": "unknown", "confidence": 0.0},
            "analysis": {}
        }
    
    def _extract_text_from_context(self, extracted_context: Dict[str, Any]) -> str:
        """Extract all text content from extracted_context JSON for AI summary"""
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
    
    def _validate_and_clean_context(self, extracted_context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean extracted context - simplified to trust PyMuPDF"""
        cleaned_context = {}
        
        for content_type, content_data in extracted_context.items():
            if content_type == "document" and isinstance(content_data, dict):
                cleaned_context[content_type] = self._clean_document_context(content_data)
            elif content_type == "image" and isinstance(content_data, dict):
                cleaned_context[content_type] = self._clean_image_context(content_data)
            elif content_type == "audio" and isinstance(content_data, dict):
                cleaned_context[content_type] = self._clean_audio_context(content_data)
            else:
                # Skip unknown content types or malformed data
                logger.warning(f"Skipping unknown content type: {content_type}")
        
        return cleaned_context
    
    def _clean_document_context(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean document context to ensure no raw bytes are present"""
        cleaned_doc = {
            "pages": [],
            "metadata": document_data.get("metadata", {})
        }
        
        for page in document_data.get("pages", []):
            if isinstance(page, dict):
                # Trust PyMuPDF to return clean UTF-8 text - no additional validation needed
                page_text = page.get("text", "")
                
                cleaned_page = {
                    "page_number": page.get("page_number", 1),
                    "text": page_text,
                    "blocks": page.get("blocks", []),
                    "confidence": page.get("confidence", 0.0)
                }
                cleaned_doc["pages"].append(cleaned_page)
        
        return cleaned_doc
    
    def _clean_image_context(self, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean image context data"""
        return {
            "description": str(image_data.get("description", "")),
            "objects": image_data.get("objects", []),
            "text_regions": image_data.get("text_regions", []),
            "metadata": image_data.get("metadata", {})
        }
    
    def _clean_audio_context(self, audio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean audio context data"""
        return {
            "transcription": audio_data.get("transcription", {}),
            "analysis": audio_data.get("analysis", {})
        }
    
    async def get_file_processing_status(self, db: AsyncSession, file_id: str) -> Optional[FileProcessingStatusResponse]:
        """Get processing status for a file"""
        file_obj = await self.file_service.get_file(db, file_id)
        
        if not file_obj:
            return None
        
        return FileProcessingStatusResponse(
            id=file_obj.id,
            filename=file_obj.filename,
            status=file_obj.status.value,
            extraction_method=file_obj.extraction_method,
            processing_started_at=file_obj.processing_started_at,
            processing_completed_at=file_obj.processing_completed_at,
            processing_error=file_obj.processing_error,
            has_content=file_obj.has_content,
            content_summary=file_obj.content_summary,
            language_detection=file_obj.language_detection
        )
    
    async def reprocess_file(self, db: AsyncSession, file_id: str) -> None:
        """Reprocess a file that failed or needs updated extraction"""
        file_obj = await self.file_service.get_file(db, file_id)
        
        if not file_obj:
            raise ValueError("File not found")
        
        # Reset processing status
        file_obj.status = FileStatus.UPLOADED
        file_obj.extracted_context = None
        file_obj.content_summary = None
        file_obj.processing_error = None
        file_obj.processing_attempts = 0
        
        # Reprocess
        await self.process_uploaded_file(db, file_obj)