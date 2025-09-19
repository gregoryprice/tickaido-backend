# PRP: AI Chat Service Attachment Context Refactoring

**Status**: Planning  
**Created**: 2025-09-18  
**Author**: AI Assistant  

## Overview

This PRP outlines a comprehensive refactoring of the AI chat service's attachment processing and context building to create a more generic, maintainable, and efficient system for handling file attachments in chat conversations.

## Problem Statement

The current AI chat service has several architectural issues:

1. **Duplicate Methods**: `_send_message_with_auth` and `_send_message_internal` contain nearly identical logic
2. **Inefficient File Processing**: Files are processed every time they're attached, even if already processed
3. **Hard-coded Context**: Uses `CustomerSupportContext` specifically, limiting flexibility for different agent types
4. **Poor Separation of Concerns**: File processing and context building logic is mixed within chat service
5. **Missing Text Interface**: No standardized way to extract text from different file types for AI consumption

## Goals

1. Consolidate duplicate message sending methods
2. Implement intelligent file processing that checks status before reprocessing
3. Create a generic context building system that works with any agent type
4. Separate file processing concerns into appropriate services
5. Add standardized text extraction interface for AI models
6. Improve maintainability and testability

## Proposed Changes

### 1. Method Consolidation

**Current State:**
- `_send_message_with_auth()`
- `_send_message_internal()`

**Target State:**
- Single `_send_message()` method
- Authentication handling moved to middleware layer
- Simpler, more maintainable code path

### 2. Intelligent File Processing

**Current State:**
```python
# Always processes attachments regardless of status
processed_attachments = await self._process_attachments(attachments)
```

**Target State:**
```python
# Check file status and only reprocess if needed
for attachment in attachments:
    file_obj = await self._get_file(attachment["file_id"])
    if file_obj.status != FileStatus.PROCESSED:
        await file_service.reprocess_file(file_obj.id)
```

**Requirements:**
- Add `reprocess_file()` method to `FileService`
- Check file status before processing
- Use existing processed content when available

### 3. Generic Context Building

**Current State:**
- Hard-coded `CustomerSupportContext`
- Chat service builds context directly

**Target State:**
- `dynamic_agent_factory.build_context()`
- Generic context building based on agent type
- Separation of concerns

**Interface:**
```python
async def build_context(
    agent_type: str,
    message: str,
    conversation_history: List[Dict],
    file_context: str,
    user_metadata: Dict[str, Any]
) -> Any:
    """Build appropriate context based on agent type"""
```

### 4. Standardized Text Extraction

**Requirements:**
Add `get_text_for_ai_model()` method to File model:

```python
def get_text_for_ai_model(self, max_length: Optional[int] = None) -> str:
    """
    Extract text content optimized for AI model consumption
    
    Handles:
    - Text files (.txt, .md, .py, etc.)
    - CSV files (formatted table)
    - Excel files (.xlsx) 
    - JSON files (formatted structure)
    - Processed content from extracted_context
    - Content summaries
    
    Args:
        max_length: Optional maximum length to truncate content
        
    Returns:
        str: Formatted text content ready for AI processing
    """
```

### 5. Improved File Context Building

**Current State:**
```python
uploaded_files=[att.get("filename", "") for att in processed_attachments]
```

**Target State:**
- Rich file context with metadata
- Use `extracted_context` and `content_summary`
- Standardized text extraction
- Proper formatting for AI consumption

## Implementation Plan

### Phase 1: File Service Enhancement

1. **Add `reprocess_file()` method to FileService**
   - Location: `app/services/file_service.py`
   - Functionality: Reprocess files that failed or need updating
   - Error handling and status updates

2. **Add `get_text_for_ai_model()` to File model**
   - Location: `app/models/file.py`
   - **Implementation priority order:**
     1. Return `content_summary` (always available, concise)
     2. For text files: Extract from `extracted_context["document"]["pages"]`
     3. For images: Extract OCR text from `extracted_context["image"]["text_regions"]` 
     4. For audio: Extract transcription from `extracted_context["audio"]["transcription"]["text"]`
   - **Token limiting**: Max 2000 tokens for context, with intelligent truncation
   - **File-type specific formatting:**
     - **CSV/Excel**: Format as structured table data
     - **JSON**: Pretty-print with key structure
     - **Code**: Include syntax highlighting markers
     - **Markdown**: Preserve formatting structure

### Phase 2: Context Building Refactoring

1. **Create generic context builder in dynamic_agent_factory**
   - Method: `build_context()`
   - Support multiple agent types
   - File context integration
   - Conversation history handling

2. **Refactor attachment processing**
   - Update `_process_attachments()` to use FileService
   - Check file status before processing
   - Build rich file context using new methods

### Phase 3: Chat Service Consolidation

1. **Merge `_send_message_with_auth` and `_send_message_internal`**
   - Single `_send_message()` method
   - Remove authentication logic (handled by middleware)
   - Simplified control flow

2. **Update context building**
   - Remove hard-coded `CustomerSupportContext`
   - Use `dynamic_agent_factory.build_context()`
   - Generic agent type handling

### Phase 4: Testing and Validation

#### 4.1 Unit Testing Strategy

**New Methods Testing:**

1. **`FileService.reprocess_file()` tests**
   ```python
   # Test cases:
   - Reprocess failed file (status=FAILED) → status=PROCESSED
   - Reprocess uploaded file (status=UPLOADED) → status=PROCESSED  
   - Reprocess already processed file → no changes
   - Reprocess with processing errors → proper error handling
   - Reprocess soft-deleted file → skip processing
   ```

2. **`File.get_text_for_ai_model()` tests**
   ```python
   # Test cases for each file type:
   - TEXT file: Return content_summary + extracted text
   - JSON file: Return formatted JSON structure + summary
   - CSV file: Return table format + summary
   - PDF file: Return extracted pages text + summary  
   - Image file: Return OCR text + description + summary
   - Audio file: Return transcription + summary
   - Large file (>2000 tokens): Return truncated content
   - File without content: Return content_summary only
   ```

3. **`dynamic_agent_factory.build_context()` tests**
   ```python
   # Test cases:
   - Customer support context building
   - Generic agent context building
   - Context with file attachments
   - Context with conversation history
   - Empty context handling
   ```

4. **Enhanced MIME type detection tests**
   ```python
   # Test `FileService._detect_file_type()`:
   - 'text/csv' → FileType.SPREADSHEET
   - 'application/json' → FileType.TEXT
   - 'text/markdown' → FileType.TEXT
   - Excel MIME types → FileType.SPREADSHEET
   - PowerPoint MIME types → FileType.PRESENTATION
   ```

#### 4.2 Integration Testing Strategy

**File Processing Integration Tests:**

1. **Attachment Processing Workflow**
   ```python
   async def test_attachment_processing_workflow():
       # Upload various file types
       # Verify status checking logic
       # Test reprocessing when needed
       # Validate context building
       # Ensure no duplicate processing
   ```

2. **AI Chat Service Integration**
   ```python
   async def test_ai_chat_with_attachments():
       # Test consolidated _send_message() method
       # Verify file status checking
       # Test context building with different agent types
       # Validate attachment metadata in responses
   ```

#### 4.3 End-to-End Testing Strategy

**API Testing with Dev Bearer Token:**
```
Bearer: ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8
```

**E2E Test Scenarios:**

1. **Complete File Upload and Chat Flow**
   ```bash
   # Test 1: Text File Processing
   curl -X POST "http://localhost:8000/api/v1/files/upload" \
     -H "Authorization: Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@test_files/sample.txt" \
     -F "file_type=text"
   
   # Verify file processing status
   curl -X GET "http://localhost:8000/api/v1/files/{file_id}/status" \
     -H "Authorization: Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"
   
   # Send chat message with attachment
   curl -X POST "http://localhost:8000/api/v1/chat/{agent_id}/threads/{thread_id}/messages" \
     -H "Authorization: Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8" \
     -H "Content-Type: application/json" \
     -d '{
       "content": "Please analyze this file",
       "role": "user", 
       "attachments": [{"file_id": "{file_id}"}]
     }'
   ```

2. **Multiple File Types Test**
   ```python
   # Test files to upload and process:
   test_files = [
       "sample.txt",      # TEXT
       "data.csv",        # SPREADSHEET  
       "config.json",     # JSON/TEXT
       "document.pdf",    # DOCUMENT
       "image.png",       # IMAGE
       "audio.mp3",       # AUDIO
       "presentation.pptx" # PRESENTATION
   ]
   
   # For each file:
   # 1. Upload file
   # 2. Verify correct FileType detection  
   # 3. Wait for processing completion
   # 4. Verify content_summary generation
   # 5. Test get_text_for_ai_model() output
   # 6. Send chat message with attachment
   # 7. Verify AI response includes file context
   ```

3. **File Status and Reprocessing Test**
   ```python
   # Test reprocessing logic:
   # 1. Upload file that fails processing (corrupted PDF)
   # 2. Verify status = FAILED
   # 3. Send chat message with failed file
   # 4. Verify reprocess_file() is called
   # 5. Check that processing is retried
   # 6. Validate final status and content
   ```

4. **Agent Context Building Test**
   ```python
   # Test different agent types:
   agents_to_test = [
       "customer_support_agent",
       "technical_support_agent", 
       "document_analysis_agent"
   ]
   
   # For each agent:
   # 1. Create thread
   # 2. Send message with file attachments
   # 3. Verify context building matches agent requirements
   # 4. Check response uses file content appropriately
   ```

#### 4.4 Test Suite Validation Requirements

**All Tests Must Pass:**

1. **Unit Test Suites**
   ```bash
   # Run all unit tests
   poetry run pytest tests/unit/ -v
   
   # Specific new test files
   poetry run pytest tests/unit/models/test_file_get_text_for_ai.py -v
   poetry run pytest tests/unit/services/test_file_service_reprocess.py -v
   poetry run pytest tests/unit/services/test_dynamic_agent_factory.py -v
   ```

2. **Integration Test Suites**
   ```bash
   # File processing integration
   poetry run pytest tests/integration/test_file_processing_workflow.py -v
   
   # AI chat service integration  
   poetry run pytest tests/integration/test_ai_chat_attachments.py -v
   
   # End-to-end attachment flow
   poetry run pytest tests/integration/test_attachment_e2e_flow.py -v
   ```

3. **Existing Test Compatibility**
   ```bash
   # Ensure no regressions in existing functionality
   poetry run pytest tests/test_simple.py -v
   poetry run pytest tests/test_api_endpoints.py -v  
   poetry run pytest tests/test_services.py -v
   poetry run pytest tests/test_ai_agents.py -v
   poetry run pytest tests/test_file_attachment_integration.py -v
   ```

#### 4.5 Docker Log Monitoring Requirements

**Zero Error Policy:**

1. **Application Logs**
   ```bash
   # Monitor during all tests - no errors allowed
   docker compose logs app --tail 100 -f
   
   # Key error patterns to watch for:
   - ImportError or ModuleNotFoundError
   - Database connection errors
   - File processing failures
   - AI service connection issues
   - Authentication/authorization errors
   ```

2. **Database Logs**
   ```bash
   # Check for database errors
   docker compose logs postgres --tail 50
   
   # Monitor for:
   - Connection timeouts
   - Query execution errors  
   - Schema validation issues
   ```

3. **Redis Logs**
   ```bash
   # Check task queue health
   docker compose logs redis --tail 50
   docker compose logs celery-worker --tail 50
   
   # Monitor for:
   - Connection failures
   - Task execution errors
   - Memory issues
   ```

#### 4.6 Performance Validation

**Response Time Requirements:**

1. **File Processing Times**
   - Small text files (<10KB): < 2 seconds
   - Medium files (10KB-1MB): < 10 seconds  
   - Large files (1MB-10MB): < 30 seconds

2. **Chat Response Times**
   - Without attachments: < 3 seconds
   - With 1-3 attachments: < 5 seconds
   - With complex file content: < 10 seconds

3. **Memory Usage**
   - No memory leaks during file processing
   - Stable memory usage during extended testing
   - Proper cleanup of temporary file content

#### 4.7 Test Data Requirements

**Create comprehensive test file suite:**

```bash
# Create test_files directory with:
test_files/
├── text/
│   ├── simple.txt          # Basic text file
│   ├── large.txt           # >10KB text file  
│   ├── unicode.txt         # Unicode characters
│   └── empty.txt           # Edge case: empty file
├── documents/
│   ├── simple.pdf          # Text-based PDF
│   ├── scanned.pdf         # Image-based PDF (OCR required)
│   ├── document.docx       # Word document
│   └── corrupted.pdf       # Intentionally corrupted for error testing
├── data/
│   ├── sample.csv          # CSV with headers and data
│   ├── large.csv           # Large dataset
│   ├── config.json         # JSON configuration
│   └── nested.json         # Complex nested JSON
├── media/
│   ├── screenshot.png      # Image with text (OCR testable)
│   ├── photo.jpg           # Photo without text
│   ├── audio.mp3           # Speech audio file
│   └── video.mp4           # Video with speech
└── office/
    ├── presentation.pptx   # PowerPoint file
    └── spreadsheet.xlsx    # Excel file
```

#### 4.8 Test Automation and Verification Scripts

**Pre-implementation Test Script:**
```bash
#!/bin/bash
# test_current_state.sh - Verify current system works before refactoring

echo "🧪 Testing current AI chat attachment functionality..."

# Test current API endpoints work
echo "Testing health endpoint..."
curl -s http://localhost:8000/health | jq .

# Test file upload (should work)
echo "Testing current file upload..."
curl -X POST "http://localhost:8000/api/v1/files/upload" \
  -H "Authorization: Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_files/simple.txt"

# Run existing test suites
echo "Running existing test suites..."
poetry run pytest tests/test_simple.py -v
poetry run pytest tests/test_api_endpoints.py -v

echo "✅ Baseline testing complete"
```

**Post-implementation Verification Script:**
```bash
#!/bin/bash  
# test_refactored_system.sh - Comprehensive verification after refactoring

echo "🔍 Testing refactored AI chat attachment system..."

# Test 1: MIME type detection improvements
echo "Testing enhanced file type detection..."
python -c "
from app.services.file_service import FileService
fs = FileService()
assert fs._detect_file_type('text/csv') == 'spreadsheet'
assert fs._detect_file_type('application/json') == 'text'
print('✅ MIME type detection enhanced')
"

# Test 2: New methods exist and work  
echo "Testing new methods..."
python -c "
from app.models.file import File
from app.services.file_service import FileService
assert hasattr(File, 'get_text_for_ai_model')
assert hasattr(FileService, 'reprocess_file')
print('✅ New methods implemented')
"

# Test 3: E2E file upload and chat
echo "Testing E2E file upload and chat..."
FILE_ID=$(curl -s -X POST "http://localhost:8000/api/v1/files/upload" \
  -H "Authorization: Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_files/sample.csv" | jq -r .file_id)

# Wait for processing
sleep 5

# Test chat with attachment  
curl -X POST "http://localhost:8000/api/v1/chat/{agent_id}/threads/{thread_id}/messages" \
  -H "Authorization: Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8" \
  -H "Content-Type: application/json" \
  -d "{
    \"content\": \"Please analyze this CSV file\",
    \"role\": \"user\",
    \"attachments\": [{\"file_id\": \"$FILE_ID\"}]
  }"

echo "✅ E2E test complete"
```

#### 4.9 Continuous Monitoring During Implementation  

**Real-time Test Execution:**
```bash
# Terminal 1: Monitor application logs
docker compose logs app --tail 100 -f | grep -E "(ERROR|WARNING|CRITICAL)"

# Terminal 2: Monitor test execution
watch -n 10 'poetry run pytest tests/test_simple.py --tb=short'

# Terminal 3: Monitor system health
watch -n 5 'curl -s http://localhost:8000/health | jq .'
```

**Test Coverage Requirements:**
- Unit test coverage: >90% for new code
- Integration test coverage: >80% for modified workflows  
- E2E test coverage: 100% for critical user paths

**Rollback Criteria:**
- Any existing test fails
- Docker logs show new errors
- E2E tests with dev token fail
- Performance degrades >20%
- Memory usage increases >50%

## Content Summary Analysis Findings

### Current Content Summary Generation

**Analysis of existing codebase shows:**

1. **Content summaries ARE generated** for all processed files in `FileProcessingService.process_uploaded_file()` (lines 86-89)
2. **Text-based files get full AI summaries** via `ai_service.generate_summary()` with extracted text content  
3. **Non-text files get fallback summaries** like "Processed [file_type] file: [filename]" (line 252 in file_tasks.py)

### File Types That Get Full AI Content Summaries

Based on `File.is_text_file` property (lines 326-331 in file.py), the following file types get full text extraction and AI-generated content summaries:

- **FileType.TEXT**: Plain text files (.txt, .md, etc.)
- **FileType.CODE**: Source code files (.py, .js, .html, .css, etc.) 
- **FileType.DOCUMENT**: PDFs, Word docs (.pdf, .docx, .doc)
- **FileType.SPREADSHEET**: Excel, CSV files (.xlsx, .xls, .csv)
- **FileType.PRESENTATION**: PowerPoint files (.pptx, .ppt)

### File Types That Need Enhanced Content Summary

**Current gaps identified:**

1. **CSV/Excel files**: Currently detected as `FileType.OTHER` (not SPREADSHEET) due to incomplete MIME type detection in `_detect_file_type()` 
2. **JSON files**: Currently detected as `FileType.OTHER`, need specific handling
3. **Markdown files**: Currently detected as `FileType.TEXT` (correct) but need specialized formatting
4. **Large text files**: Need token sampling strategy for summary generation
   - **Current issue**: Large files (>10k tokens) may exceed AI model context limits
   - **Solution**: Sample first 5000 tokens + last 1000 tokens for content summary generation
   - **Implementation**: Use `token_counter_service` to measure content before summarization

### Required File Type Detection Enhancements

**Missing MIME types in `FileService._detect_file_type()`:**

```python
# Current missing types that should be added:
'text/csv': FileType.SPREADSHEET,
'application/json': FileType.TEXT,  # Treat JSON as text
'text/markdown': FileType.TEXT,
'application/vnd.ms-excel': FileType.SPREADSHEET,
'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': FileType.SPREADSHEET,
'application/vnd.openxmlformats-officedocument.presentationml.presentation': FileType.PRESENTATION,
```

### Context Building Strategy

**The `get_text_for_ai_model()` method should use this priority order:**

1. **Primary**: `content_summary` (available for ALL processed files)
2. **Secondary**: `extracted_context` structured data (for rich content like images, audio)  
3. **Fallback**: Raw text content for text-based files (with token limits)

**Context building hierarchy:**
- **All files**: Include `content_summary` (concise AI-generated summary)
- **Text-based files**: Include structured text from `extracted_context["document"]["pages"]`
- **Images**: Include OCR text and descriptions from `extracted_context["image"]`
- **Audio**: Include transcriptions from `extracted_context["audio"]`

### Updated Attachment Processing Logic

**Current target state implementation:**
```python
# In _process_attachments() method:
for attachment in attachments:
    file_obj = await self._get_file(attachment["file_id"])
    if file_obj.status != FileStatus.PROCESSED:
        await file_service.reprocess_file(file_obj.id)
        # Refresh file object to get updated status and content
        file_obj = await self._get_file(attachment["file_id"])
    
    # Build rich context using new method
    ai_context = file_obj.get_text_for_ai_model(max_length=2000)
    processed_attachments.append({
        "file_id": str(file_obj.id),
        "filename": file_obj.filename,
        "content_summary": file_obj.content_summary,
        "ai_context": ai_context,
        "file_type": file_obj.file_type.value
    })
```

## File Changes Required

### New/Modified Files

1. **`app/services/file_service.py`**
   - Add `reprocess_file()` method
   - **Fix `_detect_file_type()` method** to properly detect:
     - CSV files (`text/csv` → `FileType.SPREADSHEET`)
     - Excel files (`application/vnd.ms-excel`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` → `FileType.SPREADSHEET`)
     - JSON files (`application/json` → `FileType.TEXT`)
     - PowerPoint files (`application/vnd.openxmlformats-officedocument.presentationml.presentation` → `FileType.PRESENTATION`)
     - Markdown files (`text/markdown` → `FileType.TEXT`)
   - Enhanced error handling

2. **`app/models/file.py`**
   - Add `get_text_for_ai_model()` method
   - Support multiple file format extraction

3. **`app/services/dynamic_agent_factory.py`**
   - Add `build_context()` method
   - Generic context building logic

4. **`app/services/ai_chat_service.py`**
   - Merge `_send_message_*` methods
   - Refactor `_process_attachments()`
   - Update context building
   - Remove hard-coded context types

### Test Files

1. **`tests/unit/services/test_file_service.py`**
   - Tests for `reprocess_file()`

2. **`tests/unit/models/test_file.py`**
   - Tests for `get_text_for_ai_model()`

3. **`tests/unit/services/test_ai_chat_service.py`**
   - Tests for refactored attachment processing
   - Context building tests

## Technical Considerations

### File Format Support

The `get_text_for_ai_model()` method should support:

- **Text files**: `.txt`, `.md`, `.py`, `.js`, `.html`, `.css` 
- **Structured data**: `.json`, `.xml`, `.yaml`, `.har` 
- **Spreadsheets**: `.csv`, `.xlsx`, `.xls`
- **Documents**: Use `extracted_context` from processing
- **Images**: Use OCR results from `extracted_context`
- **Audio/Video**: Use transcription from `extracted_context`

### Context Building Strategy

Different agent types may require different context formats:
- **Customer Support**: Include user metadata, conversation history
- **Code Review**: Focus on technical content, file structures
- **Document Analysis**: Emphasize content summaries, key topics

### Performance Considerations

1. **Caching**: Cache processed file content to avoid repeated extraction
2. **Lazy Loading**: Only process files when needed
3. **Content Limits**: Implement reasonable limits for AI context size
4. **Async Processing**: Maintain async patterns for file operations

## Migration Strategy

1. **Backward Compatibility**: Maintain existing interfaces during transition
2. **Feature Flags**: Use feature flags to enable new behavior gradually
3. **Rollback Plan**: Keep old methods available until new system is proven
4. **Monitoring**: Add logging and metrics to track adoption and performance

## Success Criteria

1. **Functionality**:
   - All existing chat functionality works unchanged
   - File attachments process correctly
   - Different file types extract text appropriately

2. **Performance**:
   - No degradation in response times
   - Reduced file processing overhead
   - Efficient context building

3. **Maintainability**:
   - Single message sending method
   - Clear separation of concerns
   - Testable components

4. **Flexibility**:
   - Generic context building supports multiple agent types
   - Easy to add new file format support
   - Extensible architecture

## Risk Mitigation

1. **Testing Strategy**: Comprehensive unit and integration tests
2. **Rollback Plan**: Keep existing methods as fallbacks
3. **Monitoring**: Enhanced logging for debugging
4. **Gradual Rollout**: Feature flags for controlled deployment

## Next Steps

1. Review and approve this PRP
2. Begin Phase 1 implementation
3. Create detailed technical specifications for each component
4. Set up development environment and testing infrastructure
5. Begin iterative development with regular reviews

---

**Note**: This refactoring will significantly improve the architecture while maintaining all existing functionality. The changes are designed to be non-breaking and can be implemented incrementally.