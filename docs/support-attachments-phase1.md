# Support Attachments Feature - Phase 1 Implementation

## Executive Summary

This document defines Phase 1 of the comprehensive file attachment system for the Tickaido Backend API. Phase 1 focuses on core file upload, storage, content extraction, and basic integration with tickets and agent conversations - without advanced security scanning features.

## Phase 1 Scope

### ✅ Included in Phase 1
- **Core Files API**: Upload, download, delete, metadata endpoints
- **Basic File Validation**: MIME type, file size, organization scoping
- **Content Extraction**: Text, image analysis, audio transcription stored in structured JSON
- **Ticket Integration**: File attachments during creation/editing with AI enhancement
- **Thread/Chat Integration**: File sharing in agent conversations
- **Organization Scoping**: Multi-tenant file isolation
- **External Integration Support**: Jira/ServiceNow attachment sync
- **Basic Storage Management**: Local and S3 storage backends

### ❌ Deferred to Phase 2
- **Advanced Security**: Malware scanning, virus detection, quarantine system
- **Public File Sharing**: `is_public` flag and public access controls
- **Advanced Analytics**: Download tracking, access logging, usage metrics
- **File Quality Scoring**: Automated quality assessment
- **Tag Management**: User-defined file tagging system

## Technical Requirements

### 1. Files API Router (`app/api/v1/files.py`)

#### Core Endpoints
```python
POST   /api/v1/files/upload          # Upload single file
GET    /api/v1/files/{file_id}       # Get file metadata
GET    /api/v1/files/{file_id}/content # Download file content
DELETE /api/v1/files/{file_id}       # Delete file
GET    /api/v1/files                 # List user's files
```

#### Request/Response Schemas

**FileUploadRequest**:
```python
class FileUploadRequest(BaseSchema):
    file: UploadFile = Field(description="File to upload")
    description: Optional[str] = Field(None, max_length=500)
```

**FileUploadResponse**:
```python
class FileUploadResponse(BaseResponse):
    file_id: UUID
    filename: str
    file_size: int
    mime_type: str
    file_type: FileType
    status: FileStatus
    download_url: Optional[str] = Field(None, description="Temporary download URL")
    processing_required: bool = Field(description="Whether file needs AI processing")
```

#### File Association Workflow

Files are uploaded independently and then associated with tickets, threads, or other objects through separate API calls:

**Step 1: Upload File**
```http
POST /api/v1/files/upload
Content-Type: multipart/form-data

{
  "file": <binary_data>,
  "description": "Screenshot of login error"
}

Response: {
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "login_error.png",
  "status": "uploaded"
}
```

**Step 2: Associate with Ticket**
```http
POST /api/v1/tickets/{ticket_id}/attachments
Content-Type: application/json

{
  "file_ids": ["550e8400-e29b-41d4-a716-446655440000"]
}
```

**Step 3: Associate with Thread**
```http
POST /api/v1/agents/{agent_id}/threads/{thread_id}/messages
Content-Type: application/json

{
  "content": "Here's a screenshot of the error I'm seeing",
  "file_ids": ["550e8400-e29b-41d4-a716-446655440000"]
}
```

This separation allows:
- **Flexible file reuse** across multiple tickets/threads
- **Independent file processing** without blocking other operations
- **Better error handling** for upload vs association failures
- **Cleaner API design** with single-responsibility endpoints

### 2. Updated File Model & Database Storage

The Phase 1 file model removes the `ticket_id` foreign key relationship and uses a simplified structure:

#### Database Schema

```sql
CREATE TABLE files (
    -- Base Model Fields
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    
    -- File Identification
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL UNIQUE,  -- Storage key/path
    mime_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(64) NOT NULL UNIQUE,   -- SHA-256 hash for deduplication
    file_type file_type_enum NOT NULL DEFAULT 'other',
    
    -- Processing Status
    status file_status_enum NOT NULL DEFAULT 'uploaded',
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    processing_error TEXT,
    processing_attempts INTEGER DEFAULT 0,
    processing_time_seconds INTEGER,
    
    -- Relationships (No ticket_id - handled by ticket.file_ids array)
    uploaded_by_id UUID REFERENCES users(id) NOT NULL,
    organization_id UUID REFERENCES organizations(id) NOT NULL,
    
    -- AI Analysis Results - Simplified Structure
    ai_analysis_version VARCHAR(20),
    ai_confidence_score VARCHAR(10),
    
    -- Unified Content Extraction (NEW APPROACH)
    extracted_context JSON,  -- Unified JSON structure for all content types
    extraction_method VARCHAR(50),  -- Method used for extraction
    
    -- AI-Generated Summary
    content_summary TEXT,  -- AI-generated summary of file content
    
    -- Language Detection
    language_detection VARCHAR(10),
    
    -- Lifecycle Management
    retention_policy VARCHAR(50),
    expires_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,
    
    -- Indexes for performance
    INDEX idx_files_organization_id (organization_id),
    INDEX idx_files_uploaded_by_id (uploaded_by_id),
    INDEX idx_files_status (status),
    INDEX idx_files_file_type (file_type),
    INDEX idx_files_created_at (created_at),
    INDEX idx_files_expires_at (expires_at),
    INDEX idx_files_extracted_context (extracted_context) -- GIN index for JSON search
);
```

#### Extracted Context JSON Structure

The `extracted_context` field stores all content extraction results in a structured JSON format:

```json
{
  "document": {
    "pages": [
      {
        "page_number": 1,
        "text": "Full text content of page 1...",
        "blocks": [
          {
            "type": "paragraph",
            "text": "This is a paragraph...",
            "confidence": 0.95,
            "geometry": {
              "bounding_box": {"left": 0.1, "top": 0.2, "width": 0.8, "height": 0.1}
            }
          },
          {
            "type": "table",
            "rows": [
              {"cells": ["Header 1", "Header 2"]},
              {"cells": ["Cell 1", "Cell 2"]}
            ],
            "confidence": 0.9
          }
        ]
      }
    ],
    "metadata": {
      "total_pages": 1,
      "language": "en",
      "creation_date": "2024-01-01T00:00:00Z"
    }
  },
  "image": {
    "description": "Screenshot showing a login error message",
    "objects": [
      {"name": "error_dialog", "confidence": 0.95},
      {"name": "login_button", "confidence": 0.88}
    ],
    "text_regions": [
      {
        "text": "Error: Invalid credentials",
        "confidence": 0.92,
        "geometry": {"x": 100, "y": 200, "width": 300, "height": 50}
      }
    ],
    "exif": {
      "camera": "iPhone 15 Pro",
      "timestamp": "2024-01-01T12:00:00Z",
      "resolution": "1920x1080"
    }
  },
  "audio": {
    "transcription": {
      "text": "Hello, I'm having trouble logging into the application...",
      "language": "en-US",
      "confidence": 0.94,
      "duration_seconds": 45,
      "segments": [
        {
          "start": 0.0,
          "end": 5.2,
          "text": "Hello, I'm having trouble",
          "confidence": 0.96
        }
      ]
    },
    "analysis": {
      "sentiment": "frustrated",
      "key_topics": ["login", "authentication", "error"],
      "urgency_level": "medium"
    }
  }
}
```

### 3. Required Services Definition

Before implementing the content extraction pipeline, we need to define the core services:

#### DocumentParserService
**Purpose**: Extract structured content from documents (PDFs, Word, Excel, etc.) similar to AWS Textract

**Complete Implementation**: 
```python
class DocumentParserService:
    """Document structure parsing with layout detection"""
    
    def __init__(self):
        self.pdf_parser = PyMuPDFParser()       # PyMuPDF/fitz for PDF parsing
        self.office_parser = PythonDocxParser() # python-docx, openpyxl for Office docs
        self.layout_detector = LayoutAnalyzer() # Custom layout detection
        self.settings = get_settings()
        
    async def analyze_document(self, content: bytes, features: List[str]) -> Dict[str, Any]:
        """
        Analyze document with specified features (TEXT, TABLES, FORMS, LAYOUT)
        
        Args:
            content: Raw document bytes
            features: List of analysis features to perform
            
        Returns:
            Structured document analysis with pages, blocks, and metadata
        """
        mime_type = self._detect_mime_type(content)
        
        if mime_type == "application/pdf":
            return await self._analyze_pdf(content, features)
        elif mime_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            return await self._analyze_word_doc(content, features)
        elif mime_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            return await self._analyze_excel_doc(content, features)
        else:
            raise ValueError(f"Unsupported document type: {mime_type}")
    
    async def _analyze_pdf(self, content: bytes, features: List[str]) -> Dict[str, Any]:
        """Analyze PDF document with structure detection"""
        import fitz  # PyMuPDF
        
        doc = fitz.open(stream=content, filetype="pdf")
        pages = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_data = {
                "page_number": page_num + 1,
                "text": "",
                "blocks": [],
                "confidence": 0.95
            }
            
            if "TEXT" in features:
                page_data["text"] = page.get_text()
            
            if "LAYOUT" in features:
                # Get text blocks with positioning
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if "lines" in block:  # Text block
                        block_text = ""
                        for line in block["lines"]:
                            for span in line["spans"]:
                                block_text += span["text"]
                        
                        page_data["blocks"].append({
                            "type": "paragraph",
                            "text": block_text,
                            "confidence": 0.95,
                            "geometry": {
                                "bounding_box": {
                                    "left": block["bbox"][0] / page.rect.width,
                                    "top": block["bbox"][1] / page.rect.height,
                                    "width": (block["bbox"][2] - block["bbox"][0]) / page.rect.width,
                                    "height": (block["bbox"][3] - block["bbox"][1]) / page.rect.height
                                }
                            }
                        })
            
            if "TABLES" in features:
                # Extract tables using layout analysis
                tables = await self._extract_pdf_tables(page)
                page_data["blocks"].extend(tables)
            
            pages.append(page_data)
        
        doc.close()
        
        return {
            "pages": pages,
            "metadata": {
                "total_pages": len(pages),
                "document_type": "pdf",
                "language": "auto-detected"
            }
        }
    
    async def _analyze_word_doc(self, content: bytes, features: List[str]) -> Dict[str, Any]:
        """Analyze Word document"""
        from docx import Document
        from io import BytesIO
        
        doc = Document(BytesIO(content))
        
        page_data = {
            "page_number": 1,
            "text": "",
            "blocks": [],
            "confidence": 0.98
        }
        
        if "TEXT" in features:
            full_text = []
            for paragraph in doc.paragraphs:
                full_text.append(paragraph.text)
            page_data["text"] = "\n".join(full_text)
        
        if "LAYOUT" in features:
            for para in doc.paragraphs:
                if para.text.strip():
                    page_data["blocks"].append({
                        "type": "paragraph",
                        "text": para.text,
                        "confidence": 0.98
                    })
        
        if "TABLES" in features:
            for table in doc.tables:
                rows = []
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    rows.append({"cells": cells})
                
                page_data["blocks"].append({
                    "type": "table",
                    "rows": rows,
                    "confidence": 0.95
                })
        
        return {
            "pages": [page_data],
            "metadata": {
                "total_pages": 1,
                "document_type": "word",
                "language": "auto-detected"
            }
        }
    
    async def extract_text(self, content: bytes) -> str:
        """Simple text extraction without structure"""
        analysis = await self.analyze_document(content, ["TEXT"])
        return "\n".join([page["text"] for page in analysis["pages"]])
    
    def _detect_mime_type(self, content: bytes) -> str:
        """Detect document MIME type from content"""
        import magic
        return magic.from_buffer(content, mime=True)
```

**Required Dependencies:**
- `PyMuPDF` (fitz): PDF parsing and text extraction
- `python-docx`: Word document parsing
- `openpyxl`: Excel document parsing  
- `python-magic`: MIME type detection
- `tabula-py`: Advanced table extraction (optional)

**Testing Requirements:**
```python
class TestDocumentParserService:
    """Comprehensive tests for DocumentParserService"""
    
    @pytest.fixture
    def parser_service(self):
        return DocumentParserService()
    
    @pytest.mark.asyncio
    async def test_pdf_text_extraction(self, parser_service):
        """REQUIRED TEST: PDF text extraction must work"""
        with open("test_files/sample.pdf", "rb") as f:
            content = f.read()
        
        result = await parser_service.analyze_document(content, ["TEXT"])
        
        assert len(result["pages"]) > 0
        assert result["pages"][0]["text"] != ""
        assert result["metadata"]["total_pages"] > 0
        assert result["metadata"]["document_type"] == "pdf"
    
    @pytest.mark.asyncio  
    async def test_word_document_parsing(self, parser_service):
        """REQUIRED TEST: Word document parsing must work"""
        with open("test_files/sample.docx", "rb") as f:
            content = f.read()
        
        result = await parser_service.analyze_document(content, ["TEXT", "LAYOUT"])
        
        assert len(result["pages"]) > 0
        assert result["pages"][0]["text"] != ""
        assert len(result["pages"][0]["blocks"]) > 0
        assert result["metadata"]["document_type"] == "word"
    
    @pytest.mark.asyncio
    async def test_table_extraction(self, parser_service):
        """REQUIRED TEST: Table extraction from documents"""
        with open("test_files/document_with_table.pdf", "rb") as f:
            content = f.read()
        
        result = await parser_service.analyze_document(content, ["TABLES"])
        
        # Must find at least one table
        table_blocks = [b for b in result["pages"][0]["blocks"] if b["type"] == "table"]
        assert len(table_blocks) > 0
        assert "rows" in table_blocks[0]
        assert len(table_blocks[0]["rows"]) > 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, parser_service):
        """REQUIRED TEST: Error handling for corrupted files"""
        corrupted_content = b"This is not a PDF file"
        
        with pytest.raises(ValueError):
            await parser_service.analyze_document(corrupted_content, ["TEXT"])
    
    @pytest.mark.asyncio
    async def test_large_document_performance(self, parser_service):
        """REQUIRED TEST: Performance with large documents"""
        with open("test_files/large_document.pdf", "rb") as f:
            content = f.read()
        
        start_time = time.time()
        result = await parser_service.analyze_document(content, ["TEXT"])
        processing_time = time.time() - start_time
        
        # Must process within 30 seconds
        assert processing_time < 30.0
        assert len(result["pages"]) > 0

# VALIDATION GATE: DocumentParserService tests must ALL PASS before proceeding
```

#### OCRService  
**Purpose**: Extract text from images using Optical Character Recognition

**Complete Implementation**:
```python
class OCRService:
    """Text extraction from images using OCR"""
    
    def __init__(self):
        self.settings = get_settings()
        # Primary: Tesseract (free, local)
        # Fallback: Google Vision API (paid, cloud)
        
    async def extract_text_with_regions(self, image_content: bytes) -> Dict[str, Any]:
        """
        Extract text with bounding boxes and confidence scores
        
        Args:
            image_content: Raw image bytes
            
        Returns:
            Dictionary with text regions, bounding boxes, and confidence scores
        """
        try:
            # Try Tesseract first (free, local)
            return await self._extract_with_tesseract(image_content)
        except Exception as e:
            logger.warning(f"Tesseract OCR failed: {e}, falling back to Google Vision")
            # Fallback to Google Vision API if available
            if hasattr(self.settings, 'google_vision_api_key') and self.settings.google_vision_api_key:
                return await self._extract_with_google_vision(image_content)
            else:
                raise Exception("OCR extraction failed and no fallback available")
    
    async def _extract_with_tesseract(self, image_content: bytes) -> Dict[str, Any]:
        """Extract text using Tesseract OCR"""
        import pytesseract
        from PIL import Image
        from io import BytesIO
        
        # Load image
        image = Image.open(BytesIO(image_content))
        
        # Extract text with detailed data
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        # Process OCR results
        text_regions = []
        full_text = []
        
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 30:  # Confidence threshold
                text = data['text'][i].strip()
                if text:
                    text_regions.append({
                        "text": text,
                        "confidence": float(data['conf'][i]) / 100.0,
                        "geometry": {
                            "x": data['left'][i],
                            "y": data['top'][i], 
                            "width": data['width'][i],
                            "height": data['height'][i]
                        },
                        "block_num": data['block_num'][i],
                        "line_num": data['line_num'][i],
                        "word_num": data['word_num'][i]
                    })
                    full_text.append(text)
        
        return {
            "text_regions": text_regions,
            "full_text": " ".join(full_text),
            "method": "tesseract",
            "total_confidence": sum([r["confidence"] for r in text_regions]) / max(len(text_regions), 1)
        }
    
    async def _extract_with_google_vision(self, image_content: bytes) -> Dict[str, Any]:
        """Extract text using Google Vision API"""
        from google.cloud import vision
        
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_content)
        
        # Detect text
        response = client.text_detection(image=image)
        texts = response.text_annotations
        
        if response.error.message:
            raise Exception(f"Google Vision API error: {response.error.message}")
        
        text_regions = []
        full_text = ""
        
        if texts:
            full_text = texts[0].description  # First annotation is full text
            
            # Process individual text regions
            for text in texts[1:]:  # Skip first (full text)
                vertices = text.bounding_poly.vertices
                
                # Calculate bounding box
                x_coords = [v.x for v in vertices]
                y_coords = [v.y for v in vertices]
                
                text_regions.append({
                    "text": text.description,
                    "confidence": 0.95,  # Google Vision doesn't provide confidence per word
                    "geometry": {
                        "x": min(x_coords),
                        "y": min(y_coords),
                        "width": max(x_coords) - min(x_coords),
                        "height": max(y_coords) - min(y_coords)
                    }
                })
        
        return {
            "text_regions": text_regions,
            "full_text": full_text,
            "method": "google_vision",
            "total_confidence": 0.95
        }
    
    async def extract_text_from_image(self, image_content: bytes) -> str:
        """Simple text extraction from image"""
        result = await self.extract_text_with_regions(image_content)
        return result["full_text"]
```

**Required Dependencies:**
- `pytesseract`: Python wrapper for Tesseract OCR engine
- `Pillow` (PIL): Image processing library  
- `tesseract`: System installation of Tesseract OCR engine
- `google-cloud-vision`: Google Vision API client (optional)

**System Requirements:**
```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-spa

# macOS  
brew install tesseract

# Additional language packs as needed
```

**Testing Requirements:**
```python
class TestOCRService:
    """Comprehensive tests for OCRService"""
    
    @pytest.fixture
    def ocr_service(self):
        return OCRService()
    
    @pytest.mark.asyncio
    async def test_clear_text_image_extraction(self, ocr_service):
        """REQUIRED TEST: Clear text extraction from high-quality image"""
        with open("test_files/clear_text_image.png", "rb") as f:
            image_content = f.read()
        
        result = await ocr_service.extract_text_with_regions(image_content)
        
        assert len(result["text_regions"]) > 0
        assert result["full_text"] != ""
        assert result["total_confidence"] > 0.7
        assert result["method"] in ["tesseract", "google_vision"]
    
    @pytest.mark.asyncio
    async def test_screenshot_text_extraction(self, ocr_service):
        """REQUIRED TEST: Text extraction from screenshot"""
        with open("test_files/error_screenshot.png", "rb") as f:
            image_content = f.read()
        
        result = await ocr_service.extract_text_with_regions(image_content)
        
        # Should extract error messages from screenshots
        assert result["full_text"] != ""
        assert len(result["text_regions"]) > 0
        
        # Check for common error text
        text_lower = result["full_text"].lower()
        error_terms = ["error", "failed", "invalid", "warning", "exception"]
        assert any(term in text_lower for term in error_terms)
    
    @pytest.mark.asyncio
    async def test_geometric_accuracy(self, ocr_service):
        """REQUIRED TEST: Bounding box accuracy"""
        with open("test_files/structured_text.png", "rb") as f:
            image_content = f.read()
        
        result = await ocr_service.extract_text_with_regions(image_content)
        
        # Validate bounding box data
        for region in result["text_regions"]:
            assert "geometry" in region
            geo = region["geometry"] 
            assert geo["x"] >= 0
            assert geo["y"] >= 0
            assert geo["width"] > 0
            assert geo["height"] > 0
            assert region["confidence"] >= 0.3  # Minimum confidence threshold
    
    @pytest.mark.asyncio
    async def test_multilingual_text(self, ocr_service):
        """REQUIRED TEST: Multilingual text extraction"""
        with open("test_files/spanish_text.png", "rb") as f:
            image_content = f.read()
        
        result = await ocr_service.extract_text_from_image(image_content)
        
        # Should extract Spanish text
        assert result != ""
        assert len(result) > 10  # Reasonable text length
    
    @pytest.mark.asyncio
    async def test_low_quality_image_handling(self, ocr_service):
        """REQUIRED TEST: Handling of low-quality/blurry images"""
        with open("test_files/blurry_text.png", "rb") as f:
            image_content = f.read()
        
        # Should not crash, may have low confidence
        result = await ocr_service.extract_text_with_regions(image_content)
        
        assert "text_regions" in result
        assert "full_text" in result
        assert "total_confidence" in result
        # May have low confidence but shouldn't crash
    
    @pytest.mark.asyncio
    async def test_no_text_image(self, ocr_service):
        """REQUIRED TEST: Images with no text"""
        with open("test_files/landscape_photo.jpg", "rb") as f:
            image_content = f.read()
        
        result = await ocr_service.extract_text_from_image(image_content)
        
        # Should return empty string or minimal false positives
        assert len(result.strip()) < 50  # Allow for minor OCR noise
    
    @pytest.mark.asyncio
    async def test_performance_requirements(self, ocr_service):
        """REQUIRED TEST: OCR performance within acceptable limits"""
        with open("test_files/typical_screenshot.png", "rb") as f:
            image_content = f.read()
        
        start_time = time.time()
        result = await ocr_service.extract_text_from_image(image_content)
        processing_time = time.time() - start_time
        
        # Must complete within 15 seconds for typical image
        assert processing_time < 15.0
        assert result is not None

# VALIDATION GATE: OCRService tests must ALL PASS before proceeding
```

#### WhisperService
**Purpose**: Transcribe audio and video files using OpenAI Whisper

**Complete Implementation**:
```python
class WhisperService:
    """Audio/video transcription using OpenAI Whisper"""
    
    def __init__(self):
        self.settings = get_settings()
        self.ai_config = load_ai_config()
        
        # Model selection from config
        model_size = self.ai_config.get("transcription", {}).get("model", "base")
        self.whisper_model = None  # Lazy loaded
        self.model_size = model_size
        
    def _load_model(self):
        """Lazy load Whisper model to save memory"""
        if self.whisper_model is None:
            import whisper
            self.whisper_model = whisper.load_model(self.model_size)
        return self.whisper_model
    
    async def transcribe_with_segments(self, audio_content: bytes) -> Dict[str, Any]:
        """
        Transcribe audio with timestamp segments
        
        Args:
            audio_content: Raw audio bytes
            
        Returns:
            Dictionary with full transcription, segments, and metadata
        """
        # Save temporary audio file
        temp_path = await self._save_temp_audio(audio_content)
        
        try:
            model = self._load_model()
            
            # Transcribe with word-level timestamps
            result = model.transcribe(
                temp_path,
                task="transcribe",
                word_timestamps=True,
                verbose=False
            )
            
            # Process segments
            segments = []
            for segment in result.get("segments", []):
                segments.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip(),
                    "confidence": segment.get("avg_logprob", -0.5)  # Whisper uses log probability
                })
            
            # Calculate overall confidence (convert log prob to 0-1 scale)
            avg_logprob = result.get("avg_logprob", -1.0)
            confidence = max(0.0, min(1.0, (avg_logprob + 3.0) / 3.0))  # Normalize -3 to 0 → 0 to 1
            
            return {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "confidence": confidence,
                "duration": len(segments[-1]["end"]) if segments else 0.0,
                "segments": segments,
                "method": "whisper_local"
            }
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    async def _save_temp_audio(self, audio_content: bytes) -> str:
        """Save audio content to temporary file"""
        import tempfile
        import uuid
        
        # Create temp file with unique name
        temp_dir = tempfile.gettempdir()
        temp_filename = f"whisper_temp_{uuid.uuid4().hex}.wav"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        # Convert to WAV format if needed using ffmpeg
        await self._convert_to_wav(audio_content, temp_path)
        
        return temp_path
    
    async def _convert_to_wav(self, audio_content: bytes, output_path: str):
        """Convert audio to WAV format using ffmpeg"""
        import subprocess
        import tempfile
        
        # Save original file
        with tempfile.NamedTemporaryFile(delete=False) as temp_input:
            temp_input.write(audio_content)
            temp_input_path = temp_input.name
        
        try:
            # Convert to WAV using ffmpeg
            subprocess.run([
                "ffmpeg", "-i", temp_input_path,
                "-acodec", "pcm_s16le",
                "-ar", "16000",  # Whisper prefers 16kHz
                "-ac", "1",      # Mono
                output_path
            ], check=True, capture_output=True)
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Audio conversion failed: {e}")
        finally:
            os.unlink(temp_input_path)
    
    async def transcribe_audio(self, audio_content: bytes, language: str = "auto") -> TranscriptionResult:
        """Basic transcription without segments"""
        result = await self.transcribe_with_segments(audio_content)
        
        return TranscriptionResult(
            text=result["text"],
            language=result["language"],
            confidence=result["confidence"],
            duration=result["duration"],
            method=result["method"]
        )

@dataclass
class TranscriptionResult:
    text: str
    language: str
    confidence: float
    duration: float
    method: str
```

**Required Dependencies:**
- `openai-whisper`: OpenAI Whisper transcription model
- `ffmpeg`: Audio/video conversion tool (system installation)
- `torch`: PyTorch for model inference
- `torchaudio`: Audio processing for PyTorch

**System Requirements:**
```bash
# Install ffmpeg
sudo apt install ffmpeg  # Ubuntu/Debian
brew install ffmpeg      # macOS

# Python packages
pip install openai-whisper torch torchaudio
```

**Testing Requirements:**
```python
class TestWhisperService:
    """Comprehensive tests for WhisperService"""
    
    @pytest.fixture
    def whisper_service(self):
        return WhisperService()
    
    @pytest.mark.asyncio
    async def test_clear_speech_transcription(self, whisper_service):
        """REQUIRED TEST: Clear speech transcription"""
        with open("test_files/clear_speech.mp3", "rb") as f:
            audio_content = f.read()
        
        result = await whisper_service.transcribe_with_segments(audio_content)
        
        assert result["text"] != ""
        assert len(result["text"]) > 10
        assert result["confidence"] > 0.6
        assert result["language"] in ["en", "es", "fr", "de"]  # Common languages
        assert len(result["segments"]) > 0
        assert result["duration"] > 0
    
    @pytest.mark.asyncio
    async def test_multilingual_transcription(self, whisper_service):
        """REQUIRED TEST: Non-English language transcription"""
        with open("test_files/spanish_speech.mp3", "rb") as f:
            audio_content = f.read()
        
        result = await whisper_service.transcribe_audio(audio_content)
        
        assert result.text != ""
        assert result.language == "es" or "spanish" in result.text.lower()
        assert result.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_segment_accuracy(self, whisper_service):
        """REQUIRED TEST: Timestamp segment accuracy"""
        with open("test_files/structured_speech.wav", "rb") as f:
            audio_content = f.read()
        
        result = await whisper_service.transcribe_with_segments(audio_content)
        
        # Validate segment structure
        for segment in result["segments"]:
            assert "start" in segment
            assert "end" in segment  
            assert "text" in segment
            assert segment["end"] > segment["start"]
            assert len(segment["text"].strip()) > 0
            assert 0.0 <= segment["confidence"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_video_audio_extraction(self, whisper_service):
        """REQUIRED TEST: Audio extraction from video files"""
        with open("test_files/sample_video.mp4", "rb") as f:
            video_content = f.read()
        
        result = await whisper_service.transcribe_audio(video_content)
        
        # Should extract audio and transcribe
        assert result.text != ""
        assert result.method == "whisper_local"
    
    @pytest.mark.asyncio
    async def test_low_quality_audio_handling(self, whisper_service):
        """REQUIRED TEST: Low quality/noisy audio handling"""
        with open("test_files/noisy_audio.mp3", "rb") as f:
            audio_content = f.read()
        
        # Should not crash, may have low confidence
        result = await whisper_service.transcribe_audio(audio_content)
        
        assert result.text is not None  # May be empty for very noisy audio
        assert 0.0 <= result.confidence <= 1.0
        assert result.duration >= 0
    
    @pytest.mark.asyncio
    async def test_performance_requirements(self, whisper_service):
        """REQUIRED TEST: Transcription performance"""
        with open("test_files/60_second_audio.mp3", "rb") as f:
            audio_content = f.read()
        
        start_time = time.time()
        result = await whisper_service.transcribe_audio(audio_content)
        processing_time = time.time() - start_time
        
        # Should process at reasonable speed (allow 2x real-time for base model)
        assert processing_time < 120.0  # 2 minutes for 1 minute of audio
        assert result.text != ""
    
    @pytest.mark.asyncio
    async def test_format_support(self, whisper_service):
        """REQUIRED TEST: Multiple audio format support"""
        formats = ["test_audio.mp3", "test_audio.wav", "test_audio.m4a", "test_audio.ogg"]
        
        for format_file in formats:
            if os.path.exists(f"test_files/{format_file}"):
                with open(f"test_files/{format_file}", "rb") as f:
                    audio_content = f.read()
                
                result = await whisper_service.transcribe_audio(audio_content)
                
                assert result.text is not None
                assert result.method == "whisper_local"

# VALIDATION GATE: WhisperService tests must ALL PASS before proceeding
```

#### VisionAnalysisService
**Purpose**: Analyze images using computer vision and AI models

**Complete Implementation**:
```python
class VisionAnalysisService:
    """Computer vision analysis using AI models"""
    
    def __init__(self):
        self.settings = get_settings()
        self.ai_config = load_ai_config()
        # Uses ai_config.yaml to determine which vision API to use
        self.vision_client = self._initialize_vision_client()
    
    def _initialize_vision_client(self):
        """Initialize vision client based on ai_config.yaml"""
        ai_config = self.ai_config
        primary_provider = ai_config.get("vision", {}).get("primary_provider", "openai")
        
        if primary_provider == "openai":
            return OpenAIVisionClient(
                api_key=self.settings.openai_api_key,
                model=ai_config.get("vision", {}).get("openai", {}).get("model", "gpt-4-vision-preview")
            )
        elif primary_provider == "google":
            return GoogleVisionClient(
                api_key=self.settings.google_vision_api_key,
                model=ai_config.get("vision", {}).get("google", {}).get("model", "gemini-pro-vision")
            )
        elif primary_provider == "claude":
            return ClaudeVisionClient(
                api_key=self.settings.anthropic_api_key,
                model=ai_config.get("vision", {}).get("anthropic", {}).get("model", "claude-3-opus")
            )
        else:
            raise ValueError(f"Unsupported vision provider: {primary_provider}")
    
    async def analyze_image(self, image_content: bytes, features: List[str]) -> Dict[str, Any]:
        """
        Analyze image with specified features (DESCRIPTION, OBJECTS, TEXT, METADATA)
        
        Args:
            image_content: Raw image bytes
            features: List of analysis features to perform
            
        Returns:
            Dictionary with analysis results based on requested features
        """
        import base64
        from PIL import Image
        from io import BytesIO
        
        # Encode image for API
        image_b64 = base64.b64encode(image_content).decode('utf-8')
        
        # Get image metadata
        image = Image.open(BytesIO(image_content))
        metadata = {
            "width": image.width,
            "height": image.height,
            "format": image.format,
            "mode": image.mode,
            "size_bytes": len(image_content)
        }
        
        analysis_result = {
            "metadata": metadata,
            "method": f"vision_{self.ai_config.get('vision', {}).get('primary_provider', 'unknown')}"
        }
        
        # Build analysis prompt based on requested features
        prompt_parts = []
        
        if "DESCRIPTION" in features:
            prompt_parts.append(
                "Provide a detailed description of this image, focusing on any technical elements, "
                "user interface components, error messages, or diagrams that would be relevant for technical support."
            )
        
        if "OBJECTS" in features:
            prompt_parts.append(
                "Identify and list all objects, UI elements, buttons, dialogs, forms, and interactive "
                "components visible in this image. Focus on technical and interface elements."
            )
        
        if "TEXT" in features:
            prompt_parts.append(
                "Extract and transcribe any text visible in the image, including error messages, "
                "labels, button text, menu items, and any other readable text content."
            )
        
        if not prompt_parts:
            prompt_parts.append("Analyze this image and provide a general technical description.")
        
        full_prompt = " ".join(prompt_parts)
        
        # Call vision API
        vision_response = await self._call_vision_api(image_b64, full_prompt)
        
        # Parse response based on requested features
        if "DESCRIPTION" in features:
            analysis_result["description"] = vision_response
        
        if "OBJECTS" in features:
            # Extract object mentions from response
            objects = self._extract_objects_from_response(vision_response)
            analysis_result["objects"] = objects
        
        if "TEXT" in features:
            # Extract text mentions from response  
            extracted_text = self._extract_text_from_response(vision_response)
            analysis_result["extracted_text"] = extracted_text
        
        # Overall confidence (vision models typically don't provide this, so estimate)
        analysis_result["confidence"] = 0.85 if len(vision_response) > 20 else 0.6
        
        return analysis_result
    
    async def _call_vision_api(self, image_b64: str, prompt: str) -> str:
        """Call the configured vision API"""
        provider = self.ai_config.get("vision", {}).get("primary_provider", "openai")
        
        if provider == "openai":
            return await self._call_openai_vision(image_b64, prompt)
        elif provider == "google":
            return await self._call_google_vision(image_b64, prompt)
        elif provider == "claude":
            return await self._call_claude_vision(image_b64, prompt)
        else:
            raise ValueError(f"Unknown vision provider: {provider}")
    
    async def _call_openai_vision(self, image_b64: str, prompt: str) -> str:
        """Call OpenAI Vision API"""
        import openai
        
        client = openai.AsyncOpenAI(api_key=self.settings.openai_api_key)
        
        response = await client.chat.completions.create(
            model=self.ai_config.get("vision", {}).get("openai", {}).get("model", "gpt-4-vision-preview"),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    
    async def _call_claude_vision(self, image_b64: str, prompt: str) -> str:
        """Call Claude Vision API"""
        import anthropic
        
        client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        
        response = await client.messages.create(
            model=self.ai_config.get("vision", {}).get("anthropic", {}).get("model", "claude-3-opus-20240229"),
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64
                            }
                        }
                    ]
                }
            ]
        )
        
        return response.content[0].text
    
    def _extract_objects_from_response(self, response: str) -> List[str]:
        """Extract object/UI element mentions from vision response"""
        import re
        
        # Common UI/technical objects to look for
        ui_objects = [
            "button", "dialog", "window", "menu", "form", "input", "field", "text box",
            "dropdown", "checkbox", "radio button", "tab", "panel", "toolbar", "header",
            "footer", "sidebar", "navigation", "search box", "login", "error message",
            "warning", "notification", "popup", "modal", "alert"
        ]
        
        found_objects = []
        response_lower = response.lower()
        
        for obj in ui_objects:
            if obj in response_lower:
                found_objects.append(obj)
        
        return list(set(found_objects))  # Remove duplicates
    
    def _extract_text_from_response(self, response: str) -> str:
        """Extract mentioned text content from vision response"""
        import re
        
        # Look for quoted text or "text reads" patterns
        quoted_text = re.findall(r'"([^"]*)"', response)
        text_reads = re.findall(r'text reads?[:\s]+"([^"]*)"', response, re.IGNORECASE)
        says_patterns = re.findall(r'says?[:\s]+"([^"]*)"', response, re.IGNORECASE)
        
        all_text = quoted_text + text_reads + says_patterns
        return " | ".join(all_text) if all_text else ""
    
    async def detect_objects(self, image_content: bytes) -> List[str]:
        """Detect objects in image"""
        result = await self.analyze_image(image_content, ["OBJECTS"])
        return result.get("objects", [])
```

**Required Dependencies:**
- `openai`: OpenAI API client
- `anthropic`: Anthropic Claude API client  
- `google-cloud-aiplatform`: Google AI Platform client
- `Pillow` (PIL): Image processing
- `base64`: Image encoding (built-in)

**Testing Requirements:**
```python
class TestVisionAnalysisService:
    """Comprehensive tests for VisionAnalysisService"""
    
    @pytest.fixture
    def vision_service(self):
        return VisionAnalysisService()
    
    @pytest.mark.asyncio
    async def test_screenshot_analysis(self, vision_service):
        """REQUIRED TEST: Screenshot analysis with UI elements"""
        with open("test_files/login_screenshot.png", "rb") as f:
            image_content = f.read()
        
        result = await vision_service.analyze_image(
            image_content, 
            ["DESCRIPTION", "OBJECTS", "TEXT"]
        )
        
        assert "description" in result
        assert len(result["description"]) > 50
        assert "objects" in result
        assert len(result["objects"]) > 0
        assert result["confidence"] > 0.6
        
        # Should detect common UI elements
        ui_elements = ["button", "dialog", "form", "input", "field"]
        assert any(element in result["objects"] for element in ui_elements)
    
    @pytest.mark.asyncio
    async def test_error_message_detection(self, vision_service):
        """REQUIRED TEST: Error message detection in screenshots"""
        with open("test_files/error_dialog.png", "rb") as f:
            image_content = f.read()
        
        result = await vision_service.analyze_image(image_content, ["DESCRIPTION", "TEXT"])
        
        # Should identify error-related content
        description_lower = result["description"].lower()
        error_terms = ["error", "failed", "invalid", "warning", "exception", "problem"]
        assert any(term in description_lower for term in error_terms)
        
        # Should extract error text
        if result.get("extracted_text"):
            text_lower = result["extracted_text"].lower()
            assert any(term in text_lower for term in error_terms)
    
    @pytest.mark.asyncio
    async def test_diagram_analysis(self, vision_service):
        """REQUIRED TEST: Technical diagram analysis"""
        with open("test_files/system_diagram.png", "rb") as f:
            image_content = f.read()
        
        result = await vision_service.analyze_image(image_content, ["DESCRIPTION"])
        
        # Should provide technical description
        assert len(result["description"]) > 100
        assert result["confidence"] > 0.5
        
        # Should identify technical elements
        description_lower = result["description"].lower()
        tech_terms = ["diagram", "system", "component", "connection", "flow", "architecture"]
        assert any(term in description_lower for term in tech_terms)
    
    @pytest.mark.asyncio
    async def test_metadata_extraction(self, vision_service):
        """REQUIRED TEST: Image metadata extraction"""
        with open("test_files/sample_image.jpg", "rb") as f:
            image_content = f.read()
        
        result = await vision_service.analyze_image(image_content, ["DESCRIPTION"])
        
        assert "metadata" in result
        metadata = result["metadata"]
        assert metadata["width"] > 0
        assert metadata["height"] > 0
        assert metadata["size_bytes"] > 0
        assert metadata["format"] in ["JPEG", "PNG", "GIF", "BMP", "WEBP"]
    
    @pytest.mark.asyncio
    async def test_provider_fallback(self, vision_service):
        """REQUIRED TEST: Provider fallback handling"""
        # This test checks that the service handles API failures gracefully
        with open("test_files/simple_image.png", "rb") as f:
            image_content = f.read()
        
        # Should handle API errors without crashing
        try:
            result = await vision_service.analyze_image(image_content, ["DESCRIPTION"])
            # If successful, validate result
            assert "description" in result
            assert result["confidence"] >= 0
        except Exception as e:
            # Should be a specific API error, not a crash
            assert "API" in str(e) or "client" in str(e) or "auth" in str(e)
    
    @pytest.mark.asyncio
    async def test_performance_requirements(self, vision_service):
        """REQUIRED TEST: Vision analysis performance"""
        with open("test_files/high_res_screenshot.png", "rb") as f:
            image_content = f.read()
        
        start_time = time.time()
        result = await vision_service.analyze_image(image_content, ["DESCRIPTION"])
        processing_time = time.time() - start_time
        
        # Should complete within 30 seconds for high-res image
        assert processing_time < 30.0
        assert result["description"] != ""

# VALIDATION GATE: VisionAnalysisService tests must ALL PASS before proceeding
```

#### AIService
**Purpose**: LLM-based content analysis using the existing ai_config.yaml configuration

**Complete Implementation**:
```python
class AIService:
    """LLM-based content analysis using ai_config.yaml providers"""
    
    def __init__(self):
        self.settings = get_settings()
        self.ai_config = load_ai_config()  # From app/config/ai_config.yaml
        self.llm_client = self._initialize_llm_client()
    
    def _initialize_llm_client(self):
        """Initialize LLM client based on ai_config.yaml settings"""
        # Use existing AI configuration for consistency with other services
        content_config = self.ai_config.get("content_analysis", {})
        primary_provider = content_config.get("primary_provider", "openai")
        
        if primary_provider == "openai":
            return OpenAIClient(
                api_key=self.settings.openai_api_key,
                model=content_config.get("openai", {}).get("model", "gpt-4"),
                max_tokens=content_config.get("openai", {}).get("max_tokens", 2000)
            )
        elif primary_provider == "google":
            return GoogleGeminiClient(
                api_key=self.settings.gemini_api_key,
                model=content_config.get("google", {}).get("model", "gemini-pro"),
                max_tokens=content_config.get("google", {}).get("max_tokens", 2048)
            )
        elif primary_provider == "anthropic":
            return ClaudeClient(
                api_key=self.settings.anthropic_api_key,
                model=content_config.get("anthropic", {}).get("model", "claude-3-sonnet"),
                max_tokens=content_config.get("anthropic", {}).get("max_tokens", 2000)
            )
        else:
            raise ValueError(f"Unsupported AI provider: {primary_provider}")
    
    async def generate_summary(self, content: str, max_length: int = 500) -> str:
        """Generate content summary"""
        if not content or len(content.strip()) < 10:
            return "No content to summarize"
        
        # Truncate very long content to avoid token limits
        if len(content) > 8000:
            content = content[:8000] + "... [truncated]"
        
        prompt = f"""
        Summarize the following content in {max_length} characters or less. 
        Focus on the main topics, key information, and any technical details relevant for support.
        
        Content:
        {content}
        
        Summary:
        """
        
        try:
            summary = await self.llm_client.generate(prompt)
            # Ensure summary doesn't exceed max length
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."
            return summary.strip()
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"Summary generation failed: {str(e)[:100]}"
    
    async def detect_language(self, content: str) -> str:
        """Detect content language"""
        if not content or len(content.strip()) < 5:
            return "unknown"
        
        # Simple language detection using first 500 characters
        sample_text = content[:500]
        
        prompt = f"""
        Detect the primary language of this text. Respond with only the ISO 639-1 language code (e.g., "en", "es", "fr", "de", "it", "pt", "ja", "zh", "ko", "ar").
        
        Text: {sample_text}
        
        Language code:
        """
        
        try:
            response = await self.llm_client.generate(prompt)
            # Extract just the language code
            lang_code = response.strip().lower()[:2]
            
            # Validate it's a reasonable language code
            common_languages = ["en", "es", "fr", "de", "it", "pt", "ja", "zh", "ko", "ar", "ru", "hi"]
            if lang_code in common_languages:
                return lang_code
            else:
                return "en"  # Default to English if detection fails
        except Exception:
            return "en"  # Default fallback
    
    async def analyze_audio_content(self, transcription: str) -> Dict[str, Any]:
        """Analyze transcribed audio for sentiment and topics"""
        if not transcription or len(transcription.strip()) < 10:
            return {
                "sentiment": "neutral",
                "key_topics": [],
                "urgency_level": "low",
                "confidence": 0.0
            }
        
        prompt = f"""
        Analyze the following audio transcription for customer support purposes.
        
        Provide analysis in this exact JSON format:
        {{
            "sentiment": "positive|neutral|negative|frustrated|angry",
            "key_topics": ["topic1", "topic2", "topic3"],
            "urgency_level": "low|medium|high|critical",
            "confidence": 0.85
        }}
        
        Transcription: {transcription}
        
        Analysis:
        """
        
        try:
            response = await self.llm_client.generate(prompt)
            # Parse JSON response
            import json
            analysis = json.loads(response.strip())
            
            # Validate required fields
            required_fields = ["sentiment", "key_topics", "urgency_level", "confidence"]
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = "unknown" if field != "confidence" else 0.0
            
            return analysis
            
        except Exception as e:
            logger.error(f"Audio content analysis failed: {e}")
            return {
                "sentiment": "neutral",
                "key_topics": ["analysis_failed"],
                "urgency_level": "medium",
                "confidence": 0.0
            }
    
    async def analyze_ticket_with_attachments(
        self, 
        title: str, 
        description: str, 
        attachments: List[Dict[str, Any]]
    ) -> TicketAnalysisResult:
        """Analyze ticket with file context for enhanced categorization"""
        
        # Build comprehensive context
        full_context = f"Title: {title}\n\nDescription: {description}\n\n"
        
        if attachments:
            full_context += "Attachments:\n"
            for i, attachment in enumerate(attachments, 1):
                full_context += f"{i}. {attachment['filename']} ({attachment['type']})\n"
                if attachment.get('content'):
                    # Include first 1000 chars of content
                    content_preview = attachment['content'][:1000]
                    full_context += f"   Content: {content_preview}\n"
                if attachment.get('summary'):
                    full_context += f"   Summary: {attachment['summary']}\n"
                full_context += "\n"
        
        prompt = f"""
        Analyze this support ticket with its attachments and provide enhanced categorization.
        
        Respond in this exact JSON format:
        {{
            "suggested_category": "technical|billing|feature_request|bug|user_access|general|integration|performance|security",
            "suggested_priority": "low|medium|high|critical",
            "suggested_subcategory": "specific subcategory",
            "suggested_department": "department name",
            "confidence": 0.85,
            "reasoning": "Explanation of categorization decisions",
            "keywords": ["keyword1", "keyword2", "keyword3"],
            "tags": ["tag1", "tag2"]
        }}
        
        Ticket Context:
        {full_context}
        
        Analysis:
        """
        
        try:
            response = await self.llm_client.generate(prompt)
            import json
            analysis = json.loads(response.strip())
            
            return TicketAnalysisResult(
                suggested_category=analysis.get("suggested_category", "general"),
                suggested_priority=analysis.get("suggested_priority", "medium"),
                suggested_subcategory=analysis.get("suggested_subcategory"),
                suggested_department=analysis.get("suggested_department"),
                confidence=float(analysis.get("confidence", 0.5)),
                reasoning=analysis.get("reasoning", ""),
                keywords=analysis.get("keywords", []),
                tags=analysis.get("tags", [])
            )
            
        except Exception as e:
            logger.error(f"Ticket analysis failed: {e}")
            return TicketAnalysisResult(
                suggested_category="general",
                suggested_priority="medium",
                confidence=0.0,
                reasoning=f"Analysis failed: {str(e)}"
            )

@dataclass
class TicketAnalysisResult:
    suggested_category: str
    suggested_priority: str
    suggested_subcategory: Optional[str] = None
    suggested_department: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""
    keywords: List[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.tags is None:
            self.tags = []
```

**Testing Requirements:**
```python
class TestAIService:
    """Comprehensive tests for AIService"""
    
    @pytest.fixture
    def ai_service(self):
        return AIService()
    
    @pytest.mark.asyncio
    async def test_content_summarization(self, ai_service):
        """REQUIRED TEST: Content summarization accuracy"""
        long_content = """
        This is a detailed technical document explaining the authentication system.
        It covers OAuth 2.0 implementation, API key management, and security best practices.
        The document includes code examples, configuration details, and troubleshooting steps.
        """ * 10  # Make it longer
        
        summary = await ai_service.generate_summary(long_content, max_length=200)
        
        assert len(summary) <= 200
        assert len(summary) > 20
        assert "authentication" in summary.lower()
        assert summary != long_content  # Should be different from original
    
    @pytest.mark.asyncio
    async def test_language_detection(self, ai_service):
        """REQUIRED TEST: Language detection accuracy"""
        test_cases = [
            ("Hello, how are you today?", "en"),
            ("Hola, ¿cómo estás hoy?", "es"),
            ("Bonjour, comment allez-vous?", "fr"),
            ("Guten Tag, wie geht es Ihnen?", "de")
        ]
        
        for text, expected_lang in test_cases:
            detected_lang = await ai_service.detect_language(text)
            assert detected_lang == expected_lang or detected_lang == "en"  # Allow fallback to English
    
    @pytest.mark.asyncio
    async def test_audio_content_analysis(self, ai_service):
        """REQUIRED TEST: Audio transcription analysis"""
        transcription = "I'm really frustrated with this login issue. It keeps saying invalid credentials but I know my password is correct. This is urgent because I need to access my account for an important meeting."
        
        analysis = await ai_service.analyze_audio_content(transcription)
        
        assert "sentiment" in analysis
        assert analysis["sentiment"] in ["negative", "frustrated", "angry"]
        assert "key_topics" in analysis
        assert len(analysis["key_topics"]) > 0
        assert "login" in str(analysis["key_topics"]).lower()
        assert "urgency_level" in analysis
        assert analysis["urgency_level"] in ["low", "medium", "high", "critical"]
        assert analysis["confidence"] > 0.5
    
    @pytest.mark.asyncio
    async def test_ticket_analysis_with_attachments(self, ai_service):
        """REQUIRED TEST: Ticket categorization with file context"""
        title = "Cannot login to application"
        description = "Getting error when trying to log in"
        attachments = [
            {
                "filename": "error_screenshot.png",
                "content": "Error dialog showing: Invalid credentials. Please check username and password.",
                "type": "image",
                "summary": "Screenshot of login error dialog"
            }
        ]
        
        result = await ai_service.analyze_ticket_with_attachments(title, description, attachments)
        
        assert result.suggested_category in ["technical", "user_access", "bug"]
        assert result.suggested_priority in ["low", "medium", "high", "critical"]
        assert result.confidence > 0.5
        assert len(result.reasoning) > 20
        assert len(result.keywords) > 0
        assert "login" in [kw.lower() for kw in result.keywords]
    
    @pytest.mark.asyncio
    async def test_provider_fallback(self, ai_service):
        """REQUIRED TEST: AI provider fallback functionality"""
        content = "This is a test document for summarization."
        
        # Should handle provider failures gracefully
        try:
            summary = await ai_service.generate_summary(content)
            assert len(summary) > 0
            assert summary != content
        except Exception as e:
            # Should be a specific API error, not a general crash
            assert "API" in str(e) or "client" in str(e) or "auth" in str(e)
    
    @pytest.mark.asyncio
    async def test_edge_cases(self, ai_service):
        """REQUIRED TEST: Edge case handling"""
        
        # Empty content
        empty_summary = await ai_service.generate_summary("")
        assert empty_summary == "No content to summarize"
        
        # Very short content
        short_summary = await ai_service.generate_summary("Hi")
        assert len(short_summary) > 0
        
        # Unknown language
        unknown_lang = await ai_service.detect_language("###$$$***")
        assert unknown_lang == "en"  # Should fallback to English
    
    @pytest.mark.asyncio
    async def test_performance_requirements(self, ai_service):
        """REQUIRED TEST: AI service performance"""
        content = "This is a medium-length document for testing AI response times. " * 50
        
        start_time = time.time()
        summary = await ai_service.generate_summary(content)
        processing_time = time.time() - start_time
        
        # Should complete within 10 seconds
        assert processing_time < 10.0
        assert len(summary) > 0

# VALIDATION GATE: AIService tests must ALL PASS before proceeding
```

#### AI Configuration Integration
The services integrate with the existing `app/config/ai_config.yaml`:

```yaml
# Example ai_config.yaml additions for file processing
content_analysis:
  primary_provider: "openai"
  fallback_provider: "google"
  openai:
    model: "gpt-4"
    max_tokens: 2000
  google:
    model: "gemini-pro"
    max_tokens: 2048

vision:
  primary_provider: "openai"
  fallback_provider: "google"
  openai:
    model: "gpt-4-vision-preview"
  google:
    model: "gemini-pro-vision"
    
transcription:
  provider: "whisper"
  model: "base"  # or "small", "medium", "large"
  language: "auto"
```

### 4. Content Extraction Pipeline

#### Updated File Processing Service

```python
class FileProcessingService:
    """Process files and store unified context in JSON format"""
    
    def __init__(self):
        self.document_parser = DocumentParserService()  # Document structure parsing
        self.ocr_service = OCRService()                 # Text extraction from images
        self.transcription_service = WhisperService()   # Audio/video transcription
        self.vision_service = VisionAnalysisService()   # Computer vision analysis
        self.ai_service = AIService()                   # LLM-based content analysis
    
    async def process_uploaded_file(self, file_obj: File) -> None:
        """Process file and store extracted context in unified JSON format"""
        
        file_obj.start_processing()
        await db.commit()
        
        try:
            extracted_context = {}
            
            # Process based on file type
            if file_obj.is_text_file or file_obj.mime_type == "application/pdf":
                document_data = await self._extract_document_content(file_obj)
                extracted_context["document"] = document_data
                file_obj.extraction_method = "document_parser"
            
            elif file_obj.is_image_file:
                image_data = await self._extract_image_content(file_obj)
                extracted_context["image"] = image_data
                file_obj.extraction_method = "vision_ocr"
            
            elif file_obj.is_media_file:
                audio_data = await self._extract_audio_content(file_obj)
                extracted_context["audio"] = audio_data
                file_obj.extraction_method = "speech_transcription"
            
            # Store unified context
            file_obj.extracted_context = extracted_context
            
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
            
        except Exception as e:
            file_obj.fail_processing(str(e))
        
        finally:
            await db.commit()
    
    async def _extract_document_content(self, file_obj: File) -> Dict[str, Any]:
        """Extract structured document content (AWS Textract style)"""
        
        file_content = await self.file_service.get_file_content(db, file_obj.id)
        
        if file_obj.mime_type == "application/pdf":
            # Use document parser with structure detection
            result = await self.document_parser.analyze_document(
                file_content,
                features=["TEXT", "TABLES", "FORMS", "LAYOUT"]
            )
            
            return {
                "pages": [
                    {
                        "page_number": page["page_number"],
                        "text": page["text"],
                        "blocks": page["blocks"],  # Paragraphs, tables, forms
                        "confidence": page["confidence"]
                    }
                    for page in result["pages"]
                ],
                "metadata": {
                    "total_pages": result["page_count"],
                    "language": result["detected_language"],
                    "document_type": result["document_type"]
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
                    "language": "auto-detected"
                }
            }
    
    async def _extract_image_content(self, file_obj: File) -> Dict[str, Any]:
        """Extract structured image content with OCR and vision analysis"""
        
        file_content = await self.file_service.get_file_content(db, file_obj.id)
        
        # OCR extraction
        ocr_result = await self.ocr_service.extract_text_with_regions(file_content)
        
        # Vision analysis
        vision_result = await self.vision_service.analyze_image(
            file_content,
            features=["DESCRIPTION", "OBJECTS", "TEXT", "METADATA"]
        )
        
        return {
            "description": vision_result["description"],
            "objects": vision_result["detected_objects"],
            "text_regions": [
                {
                    "text": region["text"],
                    "confidence": region["confidence"],
                    "geometry": region["geometry"]
                }
                for region in ocr_result["text_regions"]
            ],
            "metadata": vision_result["metadata"]
        }
    
    async def _extract_audio_content(self, file_obj: File) -> Dict[str, Any]:
        """Extract audio transcription and analysis"""
        
        file_content = await self.file_service.get_file_content(db, file_obj.id)
        
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
                    "key_topics": analysis["topics"],
                    "urgency_level": analysis["urgency"]
                }
            }
        
        return {
            "transcription": {"text": "", "language": "unknown", "confidence": 0.0},
            "analysis": {}
        }
```

### 4. Ticket Integration (Updated for file_ids Array)

Since tickets now use a `file_ids` array instead of files having `ticket_id`, the integration works differently:

```python
class TicketAttachmentProcessor:
    """Process attachments using ticket.file_ids array"""
    
    async def create_ticket_with_files(
        self,
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
        
        # Create ticket with file_ids array
        ticket_data["file_ids"] = file_ids
        ticket = await self.ticket_service.create_ticket(
            db=db,
            ticket_data=ticket_data,
            created_by_id=user.id
        )
        
        # Process files for AI enhancement
        attachment_context = []
        for file_obj in validated_files:
            # Ensure file is processed
            if file_obj.status == FileStatus.UPLOADED:
                await self.file_processor.process_uploaded_file(file_obj)
            
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
        ticket_id: UUID,
        new_file_ids: List[UUID],
        user: User
    ) -> Ticket:
        """Add files to existing ticket via file_ids array"""
        
        ticket = await self.ticket_service.get_ticket(db, ticket_id, user.organization_id)
        if not ticket:
            raise ValueError("Ticket not found")
        
        # Validate new files
        for file_id in new_file_ids:
            file_obj = await self.file_service.get_file(db, file_id)
            if not file_obj or file_obj.organization_id != user.organization_id:
                raise ValueError(f"File {file_id} not accessible")
        
        # Update ticket file_ids array
        current_file_ids = ticket.file_ids or []
        updated_file_ids = list(set(current_file_ids + new_file_ids))
        ticket.file_ids = updated_file_ids
        
        await db.commit()
        return ticket
    
    async def get_ticket_files(self, ticket_id: UUID) -> List[File]:
        """Get all files associated with a ticket"""
        
        ticket = await self.ticket_service.get_ticket(db, ticket_id)
        if not ticket or not ticket.file_ids:
            return []
        
        files = []
        for file_id in ticket.file_ids:
            file_obj = await self.file_service.get_file(db, file_id)
            if file_obj and not file_obj.is_deleted:
                files.append(file_obj)
        
        return files
```

### 5. Organization Scoping

All file operations are automatically scoped to the user's organization:

```python
class FileService:
    async def get_files_for_organization(
        self, 
        db: AsyncSession, 
        organization_id: UUID,
        user_id: UUID,
        filters: Dict[str, Any] = None
    ) -> List[File]:
        """Get files scoped to organization"""
        
        query = select(File).where(
            and_(
                File.organization_id == organization_id,
                File.is_deleted == False,
                File.uploaded_by_id == user_id  # Phase 1: Only user's own files
            )
        )
        
        # Apply filters
        if filters:
            if filters.get("file_type"):
                query = query.where(File.file_type == filters["file_type"])
            if filters.get("status"):
                query = query.where(File.status == filters["status"])
        
        result = await db.execute(query)
        return result.scalars().all()
```

### 6. Basic File Validation

Phase 1 includes essential validation without malware scanning:

```python
class BasicFileValidator:
    """Phase 1 file validation without malware scanning"""
    
    async def validate_upload(self, file: UploadFile, user: User) -> FileValidationResult:
        """Basic file validation for Phase 1"""
        
        # 1. MIME type validation
        if file.content_type not in self.allowed_file_types:
            raise ValueError(f"File type {file.content_type} not allowed")
        
        # 2. File size validation
        file_content = await file.read()
        if len(file_content) > self.max_file_size:
            raise ValueError(f"File size exceeds limit of {self.max_file_size} bytes")
        
        # 3. Organization storage quota
        current_usage = await self.get_organization_storage_usage(user.organization_id)
        org_limit = self.get_organization_storage_limit(user.organization_id)
        
        if current_usage + len(file_content) > org_limit:
            raise ValueError("Organization storage quota exceeded")
        
        # 4. File extension validation
        filename = file.filename.lower()
        allowed_extensions = self.get_allowed_extensions_for_mime_type(file.content_type)
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            raise ValueError("File extension does not match MIME type")
        
        return FileValidationResult(valid=True, file_content=file_content)
```

### 7. Agent Integration with Structured Context

Agents now receive structured context from the JSON extraction:

```python
class AgentFileProcessor:
    """Process files for agent consumption using extracted_context"""
    
    async def process_user_files(
        self, 
        file_ids: List[UUID], 
        agent_context: Dict[str, Any]
    ) -> FileProcessingResult:
        """Process files using structured extracted_context"""
        
        processed_files = []
        for file_id in file_ids:
            file_obj = await self.file_service.get_file(db, file_id)
            
            # Extract structured content from JSON
            content_summary = self._build_content_summary(file_obj)
            
            processed_files.append({
                "file_id": file_id,
                "filename": file_obj.filename,
                "content_summary": content_summary,
                "file_type": file_obj.file_type,
                "ai_summary": file_obj.content_summary,
                "extraction_method": file_obj.extraction_method
            })
        
        return FileProcessingResult(files=processed_files)
    
    def _build_content_summary(self, file_obj: File) -> str:
        """Build human-readable summary from extracted_context JSON"""
        
        if not file_obj.extracted_context:
            return f"File: {file_obj.filename} ({file_obj.display_size})"
        
        context = file_obj.extracted_context
        summary_parts = []
        
        # Document content
        if "document" in context:
            doc = context["document"]
            total_text = ""
            for page in doc.get("pages", []):
                total_text += page.get("text", "")
            
            if total_text:
                summary_parts.append(f"Document Content: {total_text[:1000]}...")
        
        # Image content
        if "image" in context:
            img = context["image"]
            summary_parts.append(f"Image Description: {img.get('description', 'No description')}")
            
            text_regions = img.get("text_regions", [])
            if text_regions:
                image_text = " ".join([region["text"] for region in text_regions])
                summary_parts.append(f"Text in Image: {image_text}")
        
        # Audio content
        if "audio" in context:
            audio = context["audio"]
            transcription = audio.get("transcription", {}).get("text", "")
            if transcription:
                summary_parts.append(f"Audio Transcription: {transcription}")
        
        return "\n".join(summary_parts) if summary_parts else f"File: {file_obj.filename}"
```

## Implementation Plan

### Phase 1 Tasks (Weeks 1-4)

1. **Week 1: Core Infrastructure**
   - Update File model with new schema
   - Create Files API router with basic endpoints
   - Implement organization-scoped file operations
   - Basic file validation (no malware scanning)

2. **Week 2: Content Extraction**
   - Build unified extracted_context JSON structure
   - Implement document parsing (AWS Textract style)
   - Add image OCR and vision analysis
   - Create audio transcription pipeline

3. **Week 3: Ticket Integration**
   - Update ticket creation with file_ids array
   - Implement attachment management endpoints
   - Build AI enhancement with file context
   - Test end-to-end ticket workflows

4. **Week 4: Agent Integration & Polish**
   - Integrate structured content with agent conversations
   - Add external integration support (Jira/ServiceNow)
   - Performance optimization and testing
   - Documentation and API examples

## Success Metrics for Phase 1

### Technical Metrics
- **File Upload Success Rate**: >99%
- **Content Extraction Success Rate**: >95%
- **Average Processing Time**: <30 seconds for files <25MB
- **API Response Time**: <2 seconds for metadata endpoints

### Business Metrics
- **User Adoption**: 50% of tickets include attachments within 30 days
- **Agent Efficiency**: 15% improvement in response accuracy with file context
- **System Reliability**: 99.5% uptime for file operations

## 🚨 MANDATORY VALIDATION GATES

**CRITICAL REQUIREMENT**: Each service must pass ALL tests before proceeding to the next implementation step. No exceptions.

### Validation Gate Sequence

#### Gate 1: DocumentParserService Validation
**Status**: ❌ **BLOCKED** until all tests pass
**Requirements**:
- ✅ PDF text extraction (sample.pdf test)
- ✅ Word document parsing (sample.docx test) 
- ✅ Table extraction (document_with_table.pdf test)
- ✅ Error handling (corrupted file test)
- ✅ Performance requirements (<30 seconds for large docs)

**Command to validate**:
```bash
poetry run pytest tests/test_document_parser_service.py -v
# ALL tests must show PASSED status
```

#### Gate 2: OCRService Validation  
**Status**: ❌ **BLOCKED** until DocumentParserService passes
**Requirements**:
- ✅ Clear text image extraction
- ✅ Screenshot text extraction with error detection
- ✅ Bounding box geometric accuracy
- ✅ Multilingual text support
- ✅ Low quality image handling
- ✅ Performance requirements (<15 seconds)

**Command to validate**:
```bash
poetry run pytest tests/test_ocr_service.py -v
# ALL tests must show PASSED status
```

#### Gate 3: WhisperService Validation
**Status**: ❌ **BLOCKED** until OCRService passes  
**Requirements**:
- ✅ Clear speech transcription
- ✅ Multilingual transcription
- ✅ Timestamp segment accuracy
- ✅ Video audio extraction
- ✅ Low quality audio handling
- ✅ Performance requirements (<2x real-time)
- ✅ Multiple format support (MP3, WAV, M4A, OGG)

**Command to validate**:
```bash
poetry run pytest tests/test_whisper_service.py -v
# ALL tests must show PASSED status
```

#### Gate 4: VisionAnalysisService Validation
**Status**: ❌ **BLOCKED** until WhisperService passes
**Requirements**:
- ✅ Screenshot analysis with UI element detection
- ✅ Error message detection in images
- ✅ Technical diagram analysis
- ✅ Image metadata extraction
- ✅ Provider fallback handling
- ✅ Performance requirements (<30 seconds)

**Command to validate**:
```bash
poetry run pytest tests/test_vision_analysis_service.py -v
# ALL tests must show PASSED status
```

#### Gate 5: AIService Validation
**Status**: ❌ **BLOCKED** until VisionAnalysisService passes
**Requirements**:
- ✅ Content summarization accuracy
- ✅ Language detection for multiple languages
- ✅ Audio content analysis (sentiment, topics, urgency)
- ✅ Ticket analysis with attachments
- ✅ Provider fallback functionality
- ✅ Edge case handling
- ✅ Performance requirements (<10 seconds)

**Command to validate**:
```bash
poetry run pytest tests/test_ai_service.py -v
# ALL tests must show PASSED status
```

#### Gate 6: Integration Testing
**Status**: ❌ **BLOCKED** until AIService passes
**Requirements**:
- ✅ End-to-end file upload workflow
- ✅ Content extraction pipeline integration
- ✅ Ticket creation with file attachments
- ✅ Agent conversation with file context
- ✅ Organization scoping validation
- ✅ Error handling across all services

**Command to validate**:
```bash
poetry run pytest tests/test_file_attachment_integration.py -v
# ALL tests must show PASSED status
```

### Implementation Checklist

**Before starting implementation, ensure**:
- [ ] All required dependencies are installed
- [ ] Test files are prepared (PDFs, images, audio samples)
- [ ] AI configuration is updated in `ai_config.yaml`
- [ ] Database migration for file model changes is ready
- [ ] Docker environment includes all required system packages

**During implementation**:
- [ ] Each service implementation must be completed in order
- [ ] All tests for current service must pass before moving to next
- [ ] Test failures require immediate fix before proceeding
- [ ] No skipping of validation gates is permitted
- [ ] Integration tests must pass after all services are complete

**Success Criteria**:
- [ ] 100% test pass rate for all services
- [ ] All performance benchmarks met
- [ ] Error handling validates correctly
- [ ] Integration tests demonstrate end-to-end functionality
- [ ] Documentation includes working code examples

### Emergency Protocols

**If any validation gate fails**:
1. **STOP** implementation immediately
2. **FIX** failing tests before proceeding
3. **RE-RUN** all tests for the failing service
4. **VERIFY** fix doesn't break previously passing tests
5. **DOCUMENT** the issue and resolution

**No exceptions to validation gates** - this ensures:
- ✅ Reliable, production-ready code
- ✅ Predictable performance characteristics  
- ✅ Robust error handling
- ✅ Consistent behavior across all file types
- ✅ Proper integration with existing systems

This Phase 1 implementation provides a solid foundation for file attachments while maintaining simplicity and focusing on core functionality. Phase 2 will add advanced security features and additional capabilities.

**⚠️ REMEMBER: You MUST pass each validation gate before proceeding to the next service implementation.**