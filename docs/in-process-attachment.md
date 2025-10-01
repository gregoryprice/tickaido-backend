# PRP: In-Process Attachment Context for AI Agents

**Status**: Planning  
**Created**: 2025-09-30  
**Author**: AI Assistant  

## Overview

This PRP addresses a critical timing issue in the file attachment processing pipeline: users can send messages to AI agents while file attachments are still processing, causing the agent to respond without the file context. This document outlines a solution to ensure file context is always available for AI agent conversations while also identifying opportunities to optimize the file processing pipeline for speed.

## Problem Statement

### Current Issue
When a user attaches a file to a thread and immediately sends a message, the following race condition occurs:

1. **File Upload**: File is uploaded and queued for processing via Celery
2. **User Message**: User sends message with attachment before processing completes
3. **Agent Response**: AI agent responds without file context because file is still `PROCESSING` status
4. **Processing Complete**: File processing finishes after agent has already responded

This creates a poor user experience where the agent appears to ignore attached files.

### Current Architecture Flow
```
File Upload → Celery Queue → Processing (2-30s) → Status: PROCESSED
                ↓
User Message → Agent Response (without file context)
```

### Impact
- **User Frustration**: Agent appears to ignore attachments
- **Reduced AI Effectiveness**: Missing context leads to incomplete responses  
- **UX Inconsistency**: File processing time varies significantly by file type/size

## Goals

1. **Ensure File Context Availability**: Guarantee that AI agents always have access to file context during conversations
2. **Non-Blocking UI**: Maintain ability for users to send messages immediately without waiting for file processing
3. **Processing Pipeline Optimization**: Identify and implement performance improvements to reduce processing time
4. **Robust Error Handling**: Handle file processing failures gracefully
5. **Real-Time Status Updates**: Provide users with clear feedback on file processing status

## Analysis of Current Pipeline

### File Processing Service Flow

Based on `app/services/file_processing_service.py` analysis:

**Current Processing Steps:**
1. **File Upload** → Status: `UPLOADED`
2. **Celery Task Queued** → Status: `PROCESSING` 
3. **Content Extraction** (2-30 seconds depending on file type):
   - Text files: Document parsing via `DocumentParserService`
   - Images: OCR + vision analysis via `OCRService` + `VisionAnalysisService`
   - PDFs: PyMuPDF extraction + OCR fallback for scanned pages
   - Audio: Transcription via `TranscriptionService`
4. **AI Analysis** → Content summary generation via `AIAnalysisService`
5. **Status Update** → Status: `PROCESSED`

### Current Processing Times (Observed)
- **Small text files (<10KB)**: 2-5 seconds
- **Medium images (100KB-1MB)**: 5-15 seconds
- **Large PDFs (1MB-10MB)**: 10-30 seconds
- **Audio files**: 15-60 seconds (depending on length)

### AI Chat Service Current Behavior

From `app/services/ai_chat_service.py` analysis, the `_process_attachments()` method:

1. **Gets file from database**
2. **Checks file status**
3. **If NOT PROCESSED**: Calls `file_service.reprocess_file()` and waits
4. **Extracts text using**: `file_obj.get_text_for_ai_model()`

**Key Finding**: The system already has intelligent reprocessing logic, but it's synchronous and can cause message delays.

### Performance Optimization Opportunities Identified

#### 1. File Processing Pipeline Bottlenecks
- **PyMuPDF Processing**: Currently processes PDFs page-by-page with OCR fallback
- **Sequential Processing**: Files processed one at a time via Celery
- **AI Summary Generation**: Blocking operation that can take 3-10 seconds
- **Large File Handling**: No chunked processing for large files

#### 2. Context Building Inefficiencies  
- **Full Content Extraction**: Unnecessarily loads complete file content
- **Synchronous Reprocessing**: Blocks message sending during file reprocessing
- **Missing Caching**: No caching of processed file context
- **Token Limit Issues**: Large files can exceed AI model context limits

#### 3. Status Management Issues
- **Binary Status**: Only UPLOADED/PROCESSING/PROCESSED states
- **No Progress Tracking**: Users don't know processing progress
- **Failed State Recovery**: Limited retry mechanisms
- **Race Conditions**: Potential issues with concurrent processing attempts

## Proposed Solution

### 1. Asynchronous File Context Integration

**Strategy**: Implement asynchronous file context resolution that doesn't block message processing.

```python
# New flow in AI Chat Service
async def _process_attachments_async(self, attachments: List[dict]) -> Tuple[str, List[str]]:
    """
    Process attachments with non-blocking context resolution
    
    Returns:
        Tuple[str, List[str]]: (immediate_context, pending_file_ids)
    """
    immediate_context = ""
    pending_files = []
    
    for attachment in attachments:
        file_obj = await self._get_file(attachment["file_id"])
        
        if file_obj.status == FileStatus.PROCESSED:
            # File ready - include full context
            ai_context = file_obj.get_text_for_ai_model(max_length=2000)
            immediate_context += f"\n\n---FILE: {file_obj.filename}---\n{ai_context}"
            
        elif file_obj.status == FileStatus.PROCESSING:
            # File processing - include placeholder with metadata
            immediate_context += f"\n\n---FILE: {file_obj.filename} (Processing...)---\n"
            immediate_context += f"File Type: {file_obj.file_type.value}\n"
            immediate_context += f"Size: {file_obj.file_size} bytes\n"
            immediate_context += "Note: Full content analysis in progress\n"
            pending_files.append(file_obj.id)
            
        else:
            # File failed or needs reprocessing
            pending_files.append(file_obj.id)
            # Trigger reprocessing in background
            asyncio.create_task(self._reprocess_file_async(file_obj.id))
    
    return immediate_context, pending_files
```

### 2. Follow-Up Context Delivery

**Strategy**: Send follow-up message with complete file context once processing completes.

```python
async def _handle_pending_file_context(
    self, 
    thread_id: str, 
    pending_file_ids: List[str],
    original_message_id: str
):
    """Monitor pending files and send follow-up context when ready"""
    
    while pending_file_ids:
        await asyncio.sleep(2)  # Check every 2 seconds
        
        completed_files = []
        for file_id in pending_file_ids.copy():
            file_obj = await self._get_file(file_id)
            
            if file_obj.status == FileStatus.PROCESSED:
                completed_files.append(file_obj)
                pending_file_ids.remove(file_id)
                
            elif file_obj.status == FileStatus.FAILED:
                # Remove failed file from pending
                pending_file_ids.remove(file_id)
        
        # Send follow-up message with newly processed files
        if completed_files:
            await self._send_followup_context_message(
                thread_id, 
                completed_files, 
                original_message_id
            )
```

### 3. Enhanced File Processing Pipeline Optimizations

Based on analysis of current pipeline, implement these optimizations:

#### A. Granular Status Tracking with Progress Updates
```python
class DetailedFileStatus(enum.Enum):
    """Enhanced file processing status with granular tracking"""
    UPLOADED = "uploaded"
    QUEUED = "queued"                    # Waiting in Celery queue
    EXTRACTING = "extracting"            # Content extraction in progress  
    OCR_PROCESSING = "ocr_processing"    # OCR analysis running
    AI_ANALYZING = "ai_analyzing"        # AI summary generation
    PROCESSED = "processed"              # Complete
    FAILED = "failed"
    QUARANTINED = "quarantined"

# Add to File model:
processing_stage = Column(String(50), default="uploaded")
processing_progress = Column(Integer, default=0)  # 0-100
estimated_completion_at = Column(DateTime)
```

#### B. Parallel Processing for Multi-File Uploads  
```python
@celery_app.task(bind=True)
def process_multiple_files_task(self, file_ids: List[str], max_concurrent: int = 3):
    """Process multiple files with concurrency control"""
    
    async def process_batch():
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(file_id: str):
            async with semaphore:
                return await _process_single_file_async(file_id)
        
        # Process files concurrently with limit
        tasks = [process_with_semaphore(fid) for fid in file_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    return asyncio.run(process_batch())
```

#### C. Optimized PDF Processing with Smart OCR
```python
async def _extract_document_content_optimized(self, file_obj: File, file_content: bytes):
    """Optimized PDF processing with intelligent OCR decisions"""
    
    if file_obj.mime_type == "application/pdf":
        file_obj.processing_stage = "extracting"
        await self._notify_processing_update(file_obj.id, "extracting", 20)
        
        # Fast text extraction attempt first
        result = await self.document_parser.analyze_document(file_content)
        
        pages_data = []
        total_pages = len(result["pages"])
        
        for i, page in enumerate(result["pages"]):
            # Update progress
            progress = 20 + (50 * (i + 1) // total_pages)  # 20-70% range
            await self._notify_processing_update(file_obj.id, "extracting", progress)
            
            page_data = {
                "page_number": page["page_number"],
                "text": page["text"],
                "blocks": page["blocks"],
                "confidence": page["confidence"]
            }
            
            # Smart OCR decision based on text quality
            if self._should_use_ocr(page_data["text"], page_data["confidence"]):
                file_obj.processing_stage = "ocr_processing"
                await self._notify_processing_update(file_obj.id, "ocr_processing", progress)
                
                try:
                    # Optimized OCR with image preprocessing
                    ocr_result = await self._ocr_pdf_page_optimized(
                        file_content, page["page_number"]
                    )
                    if ocr_result.get("full_text") and len(ocr_result["full_text"]) > len(page_data["text"]):
                        page_data["text"] = ocr_result["full_text"]
                        page_data["confidence"] = ocr_result.get("total_confidence", 0.5)
                        file_obj.extraction_method = "document_parser_ocr_enhanced"
                        
                except Exception as e:
                    logger.warning(f"OCR enhancement failed for page {page['page_number']}: {e}")
            
            pages_data.append(page_data)
        
        return {"pages": pages_data, "metadata": result["metadata"]}

def _should_use_ocr(self, text: str, confidence: float) -> bool:
    """Determine if OCR would improve text extraction"""
    # Use OCR if:
    # 1. Text confidence is low
    # 2. Text appears to be garbled (PDF extraction artifacts)
    # 3. Very little text extracted from what should be content-rich page
    
    if confidence < 0.7:
        return True
    if text.startswith('%PDF') or len(text.strip()) < 50:
        return True
    if any(marker in text for marker in ['▯', '□', '\ufffd']):  # Garbled text markers
        return True
    return False
```

#### D. Smart Content Summary Generation with Caching
```python
async def _generate_smart_summary(self, text_content: str, file_type: str, file_id: str):
    """Generate content summaries with type-specific strategies and caching"""
    
    # Check cache first
    cache_key = f"summary:{file_id}:{hash(text_content)}"
    cached_summary = await self.cache_service.get(cache_key)
    if cached_summary:
        return cached_summary
    
    file_obj.processing_stage = "ai_analyzing"
    await self._notify_processing_update(file_id, "ai_analyzing", 80)
    
    summary = None
    
    if len(text_content) > 15000:  # Large files - use sampling
        # Smart sampling: beginning + middle + end
        sample_size = 5000
        beginning = text_content[:sample_size]
        end = text_content[-1000:]
        middle_start = len(text_content) // 2 - 500
        middle = text_content[middle_start:middle_start + 1000]
        
        sample_text = f"{beginning}\n\n[... content continues ...]\n\n{middle}\n\n[... content continues ...]\n\n{end}"
        summary = await self.ai_service.generate_summary(sample_text, max_length=300)
        
    elif file_type == "code":
        # Code-specific summarization with structure analysis
        summary = await self.ai_service.generate_code_summary(text_content)
        
    elif file_type == "spreadsheet":
        # Spreadsheet summarization focusing on data structure
        summary = await self.ai_service.generate_data_summary(text_content)
        
    else:
        # Standard summarization
        summary = await self.ai_service.generate_summary(text_content, max_length=500)
    
    # Cache the result
    if summary:
        await self.cache_service.set(cache_key, summary, ttl=3600)  # 1 hour cache
    
    return summary

async def _ocr_pdf_page_optimized(self, file_content: bytes, page_number: int):
    """Optimized OCR with image preprocessing"""
    import pymupdf
    
    doc = pymupdf.open(stream=file_content, filetype="pdf")
    pdf_page = doc[page_number - 1]
    
    # Enhanced rendering for better OCR results
    # Higher DPI for better text recognition
    matrix = pymupdf.Matrix(3, 3)  # 3x zoom instead of 2x
    pix = pdf_page.get_pixmap(matrix=matrix, alpha=False)
    
    # Convert to high-quality PNG
    img_data = pix.tobytes("png")
    doc.close()
    
    # Use enhanced OCR with preprocessing
    return await self.ocr_service.extract_text_with_regions(
        img_data, 
        preprocess=True,  # Enable image preprocessing
        enhance_text=True # Enable text enhancement
    )
```

#### E. Context Caching and Token Management
```python
class FileContextCache:
    """Cache processed file contexts for AI consumption"""
    
    async def get_ai_context(self, file_id: str, max_length: int = 2000) -> Optional[str]:
        """Get cached AI context for file"""
        cache_key = f"ai_context:{file_id}:{max_length}"
        return await self.cache_service.get(cache_key)
    
    async def set_ai_context(self, file_id: str, context: str, max_length: int = 2000):
        """Cache AI context for file"""
        cache_key = f"ai_context:{file_id}:{max_length}"
        await self.cache_service.set(cache_key, context, ttl=1800)  # 30 min cache

# Enhanced get_text_for_ai_model with caching
async def get_text_for_ai_model_cached(self, max_length: Optional[int] = 2000) -> str:
    """Enhanced version with caching and token counting"""
    
    # Check cache first
    context_cache = FileContextCache()
    cached_context = await context_cache.get_ai_context(str(self.id), max_length)
    if cached_context:
        return cached_context
    
    # Generate context using existing method
    context = self.get_text_for_ai_model(max_length)
    
    # Verify token count and adjust if needed
    from app.services.token_counter_service import token_counter_service
    token_count = await token_counter_service.count_tokens(context)
    
    if max_length and token_count > max_length * 0.8:  # Token to char ratio ~0.8
        # Regenerate with smaller limit
        adjusted_length = int(max_length * 0.6)  # Conservative adjustment
        context = self.get_text_for_ai_model(adjusted_length)
    
    # Cache the result
    await context_cache.set_ai_context(str(self.id), context, max_length)
    return context
```

### 4. Real-Time Processing Status Updates

**WebSocket Integration**: Send real-time updates to frontend about file processing status.

```python
# In file processing service
async def process_uploaded_file(self, db: AsyncSession, file_obj: File):
    """Enhanced processing with real-time status updates"""
    
    file_obj.start_processing()
    await db.commit()
    
    # Notify frontend of processing start
    await self._send_processing_update(file_obj.id, "started")
    
    try:
        # ... processing logic ...
        
        # Send progress updates
        await self._send_processing_update(file_obj.id, "extracting_content")
        
        # ... content extraction ...
        
        await self._send_processing_update(file_obj.id, "generating_summary")
        
        # ... AI summary generation ...
        
        file_obj.complete_processing()
        await self._send_processing_update(file_obj.id, "completed")
        
    except Exception as e:
        file_obj.fail_processing(str(e))
        await self._send_processing_update(file_obj.id, "failed", error=str(e))
```

## Implementation Plan

### Phase 1: Asynchronous Context Resolution (Week 1)

1. **Update AI Chat Service**
   - Modify `_process_attachments()` to use asynchronous context resolution
   - Add `_process_attachments_async()` method
   - Implement placeholder context for processing files

2. **Add Follow-Up Context Delivery**
   - Create `_handle_pending_file_context()` method
   - Implement background monitoring for pending files
   - Add follow-up message sending logic

3. **Testing**
   - Unit tests for async context resolution
   - Integration tests for follow-up message delivery
   - E2E tests with various file types and sizes

### Phase 2: Pipeline Optimizations (Week 2)

1. **Parallel Processing Implementation**
   - Update Celery task to handle concurrent file processing
   - Add file dependency resolution for related uploads
   - Optimize resource usage for parallel tasks

2. **PDF Processing Optimization**
   - Implement smart text quality detection
   - Add selective OCR processing
   - Optimize PyMuPDF usage patterns

3. **Content Summary Improvements**
   - Add file-type specific summarization strategies
   - Implement smart sampling for large files
   - Optimize AI service calls

### Phase 3: Real-Time Status Updates (Week 3)

1. **WebSocket Integration**
   - Add processing status events
   - Implement frontend notification system
   - Add error handling for WebSocket failures

2. **Enhanced File Status Management**
   - Add granular processing stages
   - Implement progress percentage tracking
   - Add estimated completion times

3. **User Experience Enhancements**
   - Add file processing progress indicators
   - Implement retry mechanisms for failed files
   - Add bulk file processing status views

## Technical Implementation Details

### New Database Schema Changes

```sql
-- Add processing stage tracking
ALTER TABLE files ADD COLUMN processing_stage VARCHAR(50) DEFAULT 'uploaded';
ALTER TABLE files ADD COLUMN processing_progress INTEGER DEFAULT 0;
ALTER TABLE files ADD COLUMN estimated_completion_at TIMESTAMP;

-- Add message relationship for follow-up contexts
ALTER TABLE messages ADD COLUMN parent_message_id UUID REFERENCES messages(id);
ALTER TABLE messages ADD COLUMN message_type VARCHAR(20) DEFAULT 'user';
```

### New Service Methods

1. **FileProcessingService Enhancements**
   ```python
   async def get_processing_status_with_progress(self, file_id: str) -> FileProcessingStatusWithProgress
   async def process_files_concurrently(self, file_ids: List[str]) -> List[ProcessingResult]
   async def estimate_processing_time(self, file_obj: File) -> int
   ```

2. **AIChatService Enhancements**
   ```python
   async def send_message_with_async_attachments(self, ...) -> ChatResponse
   async def send_followup_context_message(self, ...) -> None
   async def monitor_pending_attachments(self, ...) -> None
   ```

3. **WebSocket Service Addition**
   ```python
   class FileProcessingWebSocketService:
       async def send_processing_update(self, file_id: str, status: str) -> None
       async def send_completion_notification(self, file_id: str) -> None
   ```

### Configuration Updates

```yaml
# In ai_config.yaml
file_processing:
  max_concurrent_files: 3
  processing_timeout_seconds: 300
  enable_realtime_updates: true
  enable_followup_messages: true
  
  # Optimization settings
  pdf_ocr_threshold: 0.7  # OCR if text confidence < 70%
  large_file_threshold: 10000  # bytes
  summary_max_tokens: 2000
```

## Error Handling Strategy

### 1. File Processing Failures
- **Graceful Degradation**: Use filename and file type info if processing fails
- **Retry Logic**: Automatic retry with exponential backoff
- **User Notification**: Clear error messages via WebSocket

### 2. Follow-Up Message Failures
- **Message Queue**: Persist follow-up messages for retry
- **Fallback Delivery**: Use REST API if WebSocket fails
- **User Recovery**: Provide manual refresh option

### 3. Performance Monitoring
- **Processing Time Tracking**: Monitor and alert on slow processing
- **Resource Usage**: Monitor memory and CPU during concurrent processing
- **Error Rate Monitoring**: Track processing failure rates by file type

## Testing Strategy

### 1. Unit Tests
```python
# Test async attachment processing
async def test_async_attachment_processing():
    # Test with mix of processed and processing files
    # Verify immediate context includes processed files
    # Verify pending files are tracked correctly

# Test follow-up message delivery
async def test_followup_message_delivery():
    # Test with processing files
    # Verify follow-up sent when processing completes
    # Test error handling for failed processing
```

### 2. Integration Tests
```python
# Test complete flow with real file processing
async def test_complete_attachment_flow():
    # Upload multiple file types
    # Send message immediately
    # Verify immediate response with partial context
    # Verify follow-up messages with complete context
```

### 3. Performance Tests
```python
# Test concurrent file processing
async def test_concurrent_processing_performance():
    # Upload 10 files simultaneously  
    # Measure processing time improvements
    # Verify no resource exhaustion
```

## Success Metrics

### 1. User Experience Metrics
- **Immediate Response Rate**: >99% of messages get immediate response
- **Context Completeness**: >95% of file context delivered within 30 seconds
- **User Satisfaction**: Reduced complaints about ignored attachments

### 2. Performance Metrics
- **Processing Time Reduction**: 20-40% improvement through optimizations
- **Concurrent Processing**: Support 3-5 files simultaneously
- **Error Rate**: <2% file processing failures

### 3. Technical Metrics
- **Response Time**: <3 seconds for immediate response (regardless of attachments)
- **Follow-Up Delivery**: <5 seconds after processing completion
- **Memory Usage**: No memory leaks during concurrent processing

## Risk Mitigation

### 1. Performance Risks
- **Risk**: Concurrent processing overloads system
- **Mitigation**: Configurable concurrency limits, resource monitoring

### 2. User Experience Risks  
- **Risk**: Users confused by follow-up messages
- **Mitigation**: Clear UI indicators, message threading

### 3. Data Consistency Risks
- **Risk**: Race conditions in file status updates
- **Mitigation**: Database-level locking, idempotent operations

## Rollout Strategy

### Phase 1 Rollout (Internal Testing)
- Enable for development environment
- Test with various file types and sizes
- Monitor performance and error rates

### Phase 2 Rollout (Staged Production)
- Enable for 10% of users
- Monitor user feedback and system metrics
- Adjust configuration based on real usage

### Phase 3 Rollout (Full Production)
- Enable for all users
- Continuous monitoring and optimization
- Gather user feedback for further improvements

## Future Enhancements

1. **Predictive Processing**: Pre-process files based on user patterns
2. **Smart Summarization**: Context-aware summarization based on conversation topic
3. **File Versioning**: Handle file updates and version comparison
4. **Collaborative Processing**: Share processing results across users for common files

---

**This PRP provides a comprehensive solution for ensuring AI agents always have access to file context while maintaining a responsive user experience and optimizing the file processing pipeline for performance.**