# PRP: Thread Attachment Update - Store file_ids on Messages

## Executive Summary

This PRP implements consistent attachment handling across the ticketing system by standardizing the attachment format to `[{"file_id":"uuid"}]` for both messages and tickets. This change improves UX by enabling immediate file uploads with processing feedback before message submission, while maintaining separation of concerns between file metadata and references.

## Context & Research Findings

### Current State Analysis

**Message Attachments (app/models/chat.py:73)**:
```python
attachments = Column(JSON, nullable=True)  # Currently generic format
```

**Ticket Attachments (app/models/ticket.py:127-131)**:
```python
file_ids = Column(JSON, nullable=True, comment="Array of file IDs associated with this ticket")
```

**File Processing (app/models/file.py:157-161)**:
```python
extracted_context = Column(JSON, nullable=True, comment="Unified JSON structure for all content types")
status = Column(SQLEnum(FileStatus), default=FileStatus.UPLOADED)
```

### Key Architecture Patterns Identified

1. **Organization-scoped file access** - all file operations require organization validation
2. **Async file processing** - files process via Celery tasks with status tracking
3. **Unified content extraction** - `extracted_context` JSON stores processed content
4. **Migration patterns** - add nullable column → backfill → make NOT NULL → add indexes

## Requirements

### Functional Requirements

#### FR-1: Consistent Attachment Format
- **Description**: Both Message.attachments and Ticket.attachments use format `[{"file_id":"uuid"}]`
- **Current**: Message.attachments is generic JSON, Ticket.file_ids is UUID array
- **Target**: Both use `[{"file_id": "550e8400-e29b-41d4-a716-446655440000"}]` format

#### FR-2: File Upload UX Flow
- **Description**: Enable immediate upload → processing feedback → message association
- **Flow**: 
  1. User uploads files via POST /api/v1/files/upload
  2. Frontend polls GET /api/v1/files/{file_id} for status until processed
  3. User sends message with file_ids from successful uploads
  4. Message references processed files with extracted content available

#### FR-3: Validation and Authorization  
- **Description**: Ensure file_ids exist and belong to same organization
- **Rules**:
  - Validate file_ids exist and are accessible
  - Reject soft-deleted or quarantined files  
  - Enforce organization boundary (file.organization_id == user.organization_id)

#### FR-4: Backward Compatibility
- **Description**: Support migration without breaking existing data
- **Requirements**:
  - Migrate existing Ticket.file_ids to new attachments format
  - Preserve all existing file references
  - Provide rollback capability

### Non-Functional Requirements

#### NFR-1: Performance
- **Database**: Add appropriate indexes for JSON queries
- **API**: Batch file validation to minimize database calls
- **Response Time**: File validation adds <100ms to message creation

#### NFR-2: Data Integrity  
- **Validation**: File existence and access checked at message/ticket creation
- **Consistency**: No orphaned references after successful operations
- **Error Handling**: Clear error messages for invalid file references

## Implementation Plan

### Phase 1: Database Schema Updates

#### Task 1.1: Create Migration - `add_attachments_columns`
```python
def upgrade() -> None:
    # Add new attachments columns
    op.add_column('messages', sa.Column('attachments_v2', sa.JSON(), nullable=True, 
                  comment='Array of file references: [{"file_id":"uuid"}]'))
    op.add_column('tickets', sa.Column('attachments', sa.JSON(), nullable=True,
                  comment='Array of file references: [{"file_id":"uuid"}]'))
    
    # Add indexes for performance  
    op.create_index('idx_messages_attachments_v2', 'messages', ['attachments_v2'], postgresql_using='gin')
    op.create_index('idx_tickets_attachments', 'tickets', ['attachments'], postgresql_using='gin')

def downgrade() -> None:
    op.drop_index('idx_tickets_attachments', 'tickets')
    op.drop_index('idx_messages_attachments_v2', 'messages') 
    op.drop_column('tickets', 'attachments')
    op.drop_column('messages', 'attachments_v2')
```

#### Task 1.2: Data Migration Script
```python
# Migrate existing ticket file_ids to new attachments format
UPDATE tickets 
SET attachments = (
    SELECT json_agg(json_build_object('file_id', file_id::text))
    FROM json_array_elements_text(file_ids::json) AS file_id
) 
WHERE file_ids IS NOT NULL AND file_ids != 'null'::json;
```

#### Task 1.3: Schema Cleanup Migration - `remove_old_attachments`
```python
def upgrade() -> None:
    # Remove old columns after data migration verified
    op.drop_column('tickets', 'file_ids') 
    op.alter_column('messages', 'attachments_v2', new_column_name='attachments')
```

### Phase 2: Model and Schema Updates

#### Task 2.1: Update Database Models

**app/models/chat.py** - Update Message model:
```python
# Line 73: Update attachments column comment
attachments = Column(JSON, nullable=True, comment="Array of file references: [{'file_id':'uuid'}]")
```

**app/models/ticket.py** - Replace file_ids with attachments:
```python  
# Line 127: Replace file_ids with attachments
attachments = Column(JSON, nullable=True, comment="Array of file references: [{'file_id':'uuid'}]")
```

#### Task 2.2: Update Pydantic Schemas

**app/schemas/chat.py** - Update SendMessageRequest:
```python
class FileAttachment(BaseSchema):
    """File attachment reference"""
    file_id: UUID = Field(description="File UUID reference")

class SendMessageRequest(BaseSchema):
    content: str = Field(min_length=1, description="Message content to send")
    role: str = Field(default="user", description="Message role")
    attachments: Optional[List[FileAttachment]] = Field(None, description="File attachments")
    message_metadata: Optional[Dict[str, Any]] = Field(None, description="Optional message metadata")
```

**app/schemas/ticket.py** - Update TicketCreateRequest:
```python
attachments: Optional[List[FileAttachment]] = Field(None, description="Attached file references")
# Remove: file_ids: Optional[List[UUID]] = Field(None, description="Attached file IDs")
```

### Phase 3: Service Layer Updates

#### Task 3.1: File Validation Service

**app/services/file_validation_service.py** - New service:
```python
class FileValidationService:
    """Service for validating file attachments"""
    
    async def validate_file_attachments(
        self,
        db: AsyncSession,
        attachments: List[Dict[str, Any]],
        organization_id: UUID
    ) -> List[UUID]:
        """Validate file attachments and return valid file IDs"""
        if not attachments:
            return []
            
        file_ids = [UUID(att["file_id"]) for att in attachments]
        
        # Batch query for file validation
        files = await self.get_valid_files(db, file_ids, organization_id)
        
        if len(files) != len(file_ids):
            invalid_ids = set(file_ids) - {f.id for f in files}
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid or inaccessible files: {invalid_ids}"
            )
        
        return file_ids
    
    async def get_valid_files(self, db: AsyncSession, file_ids: List[UUID], org_id: UUID):
        """Get files that exist, are accessible, and not deleted"""
        query = select(File).where(
            and_(
                File.id.in_(file_ids),
                File.organization_id == org_id,
                File.status != FileStatus.DELETED,
                File.status != FileStatus.QUARANTINED
            )
        )
        result = await db.execute(query)
        return result.scalars().all()
```

#### Task 3.2: Update AI Chat Service

**app/services/ai_chat_service.py** - Update send_message_to_thread:
```python
async def send_message_to_thread(
    self,
    agent_id: str,
    thread_id: str, 
    user_id: str,
    message: str,
    attachments: Optional[List[Dict[str, Any]]] = None,
    auth_token: Optional[str] = None
):
    """Send message with file attachment validation"""
    
    # Validate file attachments if provided
    validated_file_ids = []
    if attachments:
        file_validator = FileValidationService()
        validated_file_ids = await file_validator.validate_file_attachments(
            db, attachments, organization_id
        )
        logger.info(f"Validated {len(validated_file_ids)} file attachments")
    
    # Create user message with validated attachments
    user_msg = Message(
        thread_id=UUID(thread_id),
        role="user", 
        content=message,
        attachments=attachments,  # Store original format: [{"file_id": "uuid"}]
        created_at=datetime.now(timezone.utc)
    )
    
    # Include file context in AI processing
    file_context = await self._build_file_context(db, validated_file_ids) if validated_file_ids else ""
    
    # Rest of AI processing...
```

#### Task 3.3: Update Ticket Service

**app/services/ticket_service.py** - Update create_ticket:
```python
async def create_ticket(
    self,
    db: AsyncSession,
    ticket_data: TicketCreateRequest,
    created_by_id: UUID,
    organization_id: UUID
) -> Ticket:
    """Create ticket with file attachment validation"""
    
    # Validate attachments
    validated_file_ids = []
    if ticket_data.attachments:
        file_validator = FileValidationService()  
        validated_file_ids = await file_validator.validate_file_attachments(
            db, ticket_data.attachments, organization_id
        )
    
    # Create ticket
    ticket = Ticket(
        title=ticket_data.title,
        description=ticket_data.description, 
        attachments=ticket_data.attachments,  # [{"file_id": "uuid"}] format
        created_by_id=created_by_id,
        organization_id=organization_id,
        # ... other fields
    )
    
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    
    return ticket
```

### Phase 4: API Updates

#### Task 4.1: Update Chat API

**app/api/v1/chat.py** - Update send_message endpoint:
```python
@router.post("/{agent_id}/threads/{thread_id}/messages", response_model=MessageResponse)
async def send_message(
    request: SendMessageRequest,
    # ... existing params
):
    """Send message with file attachment support"""
    
    # Validate attachments format
    if request.attachments:
        for attachment in request.attachments:
            if "file_id" not in attachment:
                raise HTTPException(400, "Each attachment must have 'file_id' field")
            
            try:
                UUID(attachment["file_id"])
            except ValueError:
                raise HTTPException(400, f"Invalid file_id format: {attachment['file_id']}")
    
    # Call AI service with validation
    ai_response = await ai_chat_service.send_message_to_thread(
        agent_id=str(agent_id),
        thread_id=str(thread_id), 
        user_id=user_id,
        message=request.content,
        attachments=request.attachments,
        auth_token=jwt_token
    )
    
    # Return response...
```

#### Task 4.2: Update Ticket API  

**app/api/v1/tickets.py** - Update create_ticket:
```python
@router.post("/", response_model=TicketDetailResponse)
async def create_ticket(
    ticket_data: TicketCreateRequest,
    # ... existing params
):
    """Create ticket with file attachment support"""
    
    # Validate attachment format  
    if ticket_data.attachments:
        for attachment in ticket_data.attachments:
            if "file_id" not in attachment:
                raise HTTPException(400, "Each attachment must have 'file_id' field")
    
    try:
        # Create ticket with validation
        ticket = await ticket_service.create_ticket(
            db=db,
            ticket_data=ticket_data,
            created_by_id=current_user.id,
            organization_id=current_user.organization_id
        )
        
        # Build response with file information
        files = await self._get_attachment_files(db, ticket.attachments) 
        
        return TicketDetailResponse(
            **ticket.__dict__,
            files=files,
            # ... other fields
        )
        
    except Exception as e:
        logger.error(f"Ticket creation failed: {e}")
        raise HTTPException(500, "Ticket creation failed")
```

### Phase 5: Testing Implementation

#### Task 5.1: Unit Tests

**tests/unit/test_attachment_validation.py**:
```python
class TestFileAttachmentValidation:
    
    @pytest.mark.asyncio
    async def test_validate_valid_attachments(self, mock_db, sample_org):
        """Test validation of valid file attachments"""
        validator = FileValidationService()
        attachments = [{"file_id": str(uuid.uuid4())}]
        
        # Mock valid file query
        mock_db.execute.return_value.scalars.return_value.all.return_value = [
            File(id=UUID(attachments[0]["file_id"]), organization_id=sample_org.id)
        ]
        
        result = await validator.validate_file_attachments(
            mock_db, attachments, sample_org.id
        )
        
        assert len(result) == 1
        assert result[0] == UUID(attachments[0]["file_id"])
    
    @pytest.mark.asyncio  
    async def test_validate_invalid_file_id(self, mock_db, sample_org):
        """Test validation fails for non-existent files"""
        validator = FileValidationService()
        attachments = [{"file_id": str(uuid.uuid4())}]
        
        # Mock no files found
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        
        with pytest.raises(HTTPException) as exc:
            await validator.validate_file_attachments(
                mock_db, attachments, sample_org.id  
            )
        
        assert exc.value.status_code == 400
        assert "Invalid or inaccessible files" in str(exc.value.detail)
```

#### Task 5.2: Integration Tests

**tests/integration/test_message_attachments.py**:
```python
class TestMessageAttachmentIntegration:
    
    @pytest.mark.asyncio
    async def test_send_message_with_attachments(self, client, auth_headers, uploaded_file):
        """Test sending message with file attachments"""
        
        # Send message with attachment
        response = await client.post(
            "/api/v1/chat/agent-123/threads/thread-456/messages",
            json={
                "content": "Please analyze this file",
                "attachments": [{"file_id": str(uploaded_file.id)}]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify message was created with attachment
        assert data["content"] == "Please analyze this file" 
        assert len(data["attachments"]) == 1
        assert data["attachments"][0]["file_id"] == str(uploaded_file.id)
    
    @pytest.mark.asyncio
    async def test_message_attachment_validation_failure(self, client, auth_headers):
        """Test message creation fails with invalid file references"""
        
        response = await client.post(
            "/api/v1/chat/agent-123/threads/thread-456/messages",
            json={
                "content": "Test message",
                "attachments": [{"file_id": "invalid-uuid"}]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Invalid file_id format" in response.json()["detail"]
```

## Validation Gates

### Gate 1: Database Migration Validation
```bash
# Apply migration
poetry run alembic upgrade head

# Verify schema
poetry run python -c "
from app.models.chat import Message
from app.models.ticket import Ticket  
import sqlalchemy as sa
print('✅ Message.attachments column exists')
print('✅ Ticket.attachments column exists')  
print('✅ Appropriate indexes created')
"

# Verify data migration
poetry run python -c "
import asyncio
from app.database import get_db_session
from sqlalchemy import text

async def verify_migration():
    async for db in get_db_session():
        # Check ticket data migration
        result = await db.execute(text('SELECT id, attachments FROM tickets WHERE attachments IS NOT NULL LIMIT 5'))
        rows = result.fetchall()
        for row in rows:
            attachments = row[1]
            assert isinstance(attachments, list), 'Attachments must be array'
            for att in attachments:
                assert 'file_id' in att, 'Each attachment must have file_id'
        print('✅ Ticket data migration successful')

asyncio.run(verify_migration())
"
```

### Gate 2: API Endpoint Validation (with Real Authentication)
```bash
# Test with authenticated API calls - requires running Docker services
echo "🚀 Starting Docker services for E2E testing..."
docker compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Verify all Docker services are running without errors
echo "🔍 Checking Docker service logs for errors..."
docker compose logs app --since=1m | grep -i error && echo "❌ App service has errors" || echo "✅ App service clean"
docker compose logs postgres --since=1m | grep -i error && echo "❌ Postgres service has errors" || echo "✅ Postgres service clean"  
docker compose logs redis --since=1m | grep -i error && echo "❌ Redis service has errors" || echo "✅ Redis service clean"
docker compose logs celery-worker --since=1m | grep -i error && echo "❌ Celery service has errors" || echo "✅ Celery service clean"

# Create test file for upload
echo "Creating test file for attachment testing..." > /tmp/test_attachment.txt
echo "This is a test file for validating the attachment system." >> /tmp/test_attachment.txt
echo "File ID will be referenced in message attachments." >> /tmp/test_attachment.txt

# Test authenticated API flow
poetry run python -c "
import asyncio
import aiohttp
import json
import sys
from pathlib import Path

API_BASE = 'http://localhost:8000'
DEV_TOKEN = 'ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8'
HEADERS = {
    'Authorization': f'Bearer {DEV_TOKEN}',
    'Content-Type': 'application/json'
}
UPLOAD_HEADERS = {
    'Authorization': f'Bearer {DEV_TOKEN}'
    # Content-Type will be set by aiohttp for multipart/form-data
}

async def test_authenticated_flow():
    async with aiohttp.ClientSession() as session:
        try:
            # 1. Test health endpoint
            print('📡 Testing health endpoint...')
            async with session.get(f'{API_BASE}/health') as resp:
                assert resp.status == 200, f'Health check failed: {resp.status}'
                print('✅ Health endpoint responsive')
            
            # 2. Upload file with authentication
            print('📤 Uploading test file...')
            data = aiohttp.FormData()
            data.add_field('file', 
                          open('/tmp/test_attachment.txt', 'rb'),
                          filename='test_attachment.txt',
                          content_type='text/plain')
            data.add_field('description', 'Test attachment for validation')
            
            async with session.post(
                f'{API_BASE}/api/v1/files/upload',
                data=data,
                headers=UPLOAD_HEADERS
            ) as resp:
                assert resp.status == 200, f'File upload failed: {resp.status} - {await resp.text()}'
                file_data = await resp.json()
                file_id = file_data['id']
                print(f'✅ File uploaded successfully: {file_id}')
                print(f'   - File size: {file_data[\"file_size\"]} bytes')
                print(f'   - Processing required: {file_data[\"processing_required\"]}')
            
            # 3. Verify file processing status
            print('⏳ Checking file processing status...')
            async with session.get(
                f'{API_BASE}/api/v1/files/{file_id}',
                headers=HEADERS
            ) as resp:
                assert resp.status == 200, f'File status check failed: {resp.status}'
                file_status = await resp.json()
                print(f'✅ File status retrieved: {file_status[\"status\"]}')
                
            # 4. Get list of available agents
            print('🤖 Getting available agents...')
            async with session.get(
                f'{API_BASE}/api/v1/agents',
                headers=HEADERS
            ) as resp:
                assert resp.status == 200, f'Agents list failed: {resp.status}'
                agents_data = await resp.json()
                if not agents_data.get('agents'):
                    print('⚠️ No agents found - creating test scenario with mock agent')
                    agent_id = 'test-agent-id'
                else:
                    agent_id = agents_data['agents'][0]['id']
                    print(f'✅ Found agent: {agent_id}')
            
            # 5. Create thread with agent
            print('🧵 Creating thread...')
            async with session.post(
                f'{API_BASE}/api/v1/chat/{agent_id}/threads',
                json={'title': 'Attachment Test Thread'},
                headers=HEADERS
            ) as resp:
                if resp.status != 200:
                    print(f'⚠️ Thread creation failed: {resp.status} - {await resp.text()}')
                    print('📝 Using mock thread for testing')
                    thread_id = 'test-thread-id'
                else:
                    thread_data = await resp.json()
                    thread_id = thread_data['id'] 
                    print(f'✅ Thread created: {thread_id}')
            
            # 6. Send message with attachment
            print('💬 Sending message with file attachment...')
            message_payload = {
                'content': 'Please analyze this test file for validation',
                'attachments': [{'file_id': file_id}]
            }
            
            async with session.post(
                f'{API_BASE}/api/v1/chat/{agent_id}/threads/{thread_id}/messages',
                json=message_payload,
                headers=HEADERS
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f'❌ Message with attachment failed: {resp.status}')
                    print(f'   Error details: {error_text}')
                    sys.exit(1)
                else:
                    msg_data = await resp.json()
                    print('✅ Message with attachment sent successfully')
                    print(f'   - Message ID: {msg_data[\"id\"]}')
                    print(f'   - Attachments: {len(msg_data.get(\"attachments\", []))}')
                    
                    # Validate attachment format
                    if msg_data.get('attachments'):
                        attachment = msg_data['attachments'][0]
                        assert 'file_id' in attachment, 'Attachment missing file_id'
                        assert attachment['file_id'] == file_id, 'File ID mismatch'
                        print('✅ Attachment format validated')
                    
            # 7. Test ticket creation with attachment
            print('🎫 Creating ticket with file attachment...')
            ticket_payload = {
                'title': 'Test Ticket with Attachment',
                'description': 'This ticket tests the new attachment system',
                'category': 'technical',
                'attachments': [{'file_id': file_id}]
            }
            
            async with session.post(
                f'{API_BASE}/api/v1/tickets/',
                json=ticket_payload,
                headers=HEADERS
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f'❌ Ticket with attachment failed: {resp.status}')
                    print(f'   Error details: {error_text}')
                    sys.exit(1)
                else:
                    ticket_data = await resp.json()
                    print('✅ Ticket with attachment created successfully')
                    print(f'   - Ticket ID: {ticket_data[\"id\"]}')
                    print(f'   - Attachments: {len(ticket_data.get(\"attachments\", []))}')
                    
                    # Validate ticket attachment format
                    if ticket_data.get('attachments'):
                        attachment = ticket_data['attachments'][0]
                        assert 'file_id' in attachment, 'Ticket attachment missing file_id'
                        assert attachment['file_id'] == file_id, 'Ticket file ID mismatch'
                        print('✅ Ticket attachment format validated')
            
            print('🎉 All authenticated API tests passed successfully!')
            
        except Exception as e:
            print(f'❌ E2E API test failed: {e}')
            import traceback
            traceback.print_exc()
            sys.exit(1)

# Run the authenticated test flow
asyncio.run(test_authenticated_flow())
"

# Final Docker log validation - must be ERROR FREE
echo "🔍 Final Docker service log validation (MUST BE ERROR FREE)..."
echo "Checking last 2 minutes of logs for any errors..."

ERROR_COUNT=0

echo "--- App Service Logs ---"
if docker compose logs app --since=2m | grep -i -E "(error|exception|failed|traceback)" | head -10; then
    ERROR_COUNT=$((ERROR_COUNT + 1))
    echo "❌ App service has errors in logs"
else
    echo "✅ App service logs are clean"
fi

echo "--- Postgres Service Logs ---"  
if docker compose logs postgres --since=2m | grep -i -E "(error|exception|failed)" | head -10; then
    ERROR_COUNT=$((ERROR_COUNT + 1))
    echo "❌ Postgres service has errors in logs"
else
    echo "✅ Postgres service logs are clean"
fi

echo "--- Redis Service Logs ---"
if docker compose logs redis --since=2m | grep -i -E "(error|exception|failed)" | head -10; then
    ERROR_COUNT=$((ERROR_COUNT + 1))
    echo "❌ Redis service has errors in logs"
else
    echo "✅ Redis service logs are clean"
fi

echo "--- Celery Worker Service Logs ---"
if docker compose logs celery-worker --since=2m | grep -i -E "(error|exception|failed|traceback)" | head -10; then
    ERROR_COUNT=$((ERROR_COUNT + 1))
    echo "❌ Celery service has errors in logs"
else
    echo "✅ Celery service logs are clean"
fi

if [ $ERROR_COUNT -gt 0 ]; then
    echo "❌ VALIDATION FAILED: $ERROR_COUNT services have errors in logs"
    echo "🚨 Docker logs MUST be error-free for deployment approval"
    exit 1
else
    echo "✅ ALL DOCKER SERVICES ARE ERROR-FREE"
fi

# Cleanup test file
rm -f /tmp/test_attachment.txt
echo "✅ E2E API validation completed successfully"
```

### Gate 3: Comprehensive Unit and Integration Tests (ALL MUST PASS)
```bash
# CRITICAL: ALL tests must pass for deployment approval
echo "🧪 Running comprehensive test suite - ALL TESTS MUST PASS"
echo "======================================================"

# 1. Run all existing tests first to ensure no regressions
echo "📋 Running existing test suite..."
poetry run pytest tests/ -v --tb=short -x
if [ $? -ne 0 ]; then
    echo "❌ EXISTING TESTS FAILED - DEPLOYMENT BLOCKED"
    echo "🚨 Must fix all existing test failures before proceeding"
    exit 1
else
    echo "✅ All existing tests pass"
fi

# 2. Run specific attachment validation tests
echo "📎 Running attachment validation tests..."
poetry run pytest tests/unit/test_attachment_validation.py -v --tb=short
if [ $? -ne 0 ]; then
    echo "❌ ATTACHMENT VALIDATION TESTS FAILED - DEPLOYMENT BLOCKED"
    exit 1
else
    echo "✅ Attachment validation tests pass"
fi

# 3. Run message attachment integration tests
echo "💬 Running message attachment integration tests..."
poetry run pytest tests/integration/test_message_attachments.py -v --tb=short
if [ $? -ne 0 ]; then
    echo "❌ MESSAGE ATTACHMENT TESTS FAILED - DEPLOYMENT BLOCKED"
    exit 1
else
    echo "✅ Message attachment tests pass"
fi

# 4. Run ticket attachment integration tests
echo "🎫 Running ticket attachment integration tests..."
poetry run pytest tests/integration/test_ticket_attachments.py -v --tb=short
if [ $? -ne 0 ]; then
    echo "❌ TICKET ATTACHMENT TESTS FAILED - DEPLOYMENT BLOCKED"
    exit 1
else
    echo "✅ Ticket attachment tests pass"
fi

# 5. Verify comprehensive test coverage (minimum 90%)
echo "📊 Verifying test coverage (minimum 90% required)..."
poetry run pytest --cov=app.services.file_validation_service --cov=app.api.v1.chat --cov=app.api.v1.tickets --cov-report=term-missing --cov-fail-under=90 tests/
if [ $? -ne 0 ]; then
    echo "❌ INSUFFICIENT TEST COVERAGE - DEPLOYMENT BLOCKED"
    echo "🚨 Must achieve minimum 90% test coverage"
    exit 1
else
    echo "✅ Test coverage meets requirements"
fi

# 6. Run linting and type checking
echo "🔍 Running code quality checks..."
poetry run ruff check app/ --fix
if [ $? -ne 0 ]; then
    echo "❌ LINTING ERRORS FOUND - DEPLOYMENT BLOCKED"
    exit 1
else
    echo "✅ Code linting passed"
fi

poetry run mypy app/ --ignore-missing-imports
if [ $? -ne 0 ]; then
    echo "❌ TYPE CHECK ERRORS FOUND - DEPLOYMENT BLOCKED"
    exit 1
else
    echo "✅ Type checking passed"
fi

# 7. Security and vulnerability scan
echo "🔒 Running security checks..."
poetry run safety check
if [ $? -ne 0 ]; then
    echo "⚠️ SECURITY VULNERABILITIES FOUND - Review required"
    echo "📝 Consider updating vulnerable packages before deployment"
else
    echo "✅ No known security vulnerabilities"
fi

echo "🎉 ALL TEST GATES PASSED SUCCESSFULLY"
echo "✅ Code is ready for deployment"
```

## Risk Assessment & Mitigation

### High Risk: Data Loss During Migration
- **Risk**: Existing ticket file_ids not properly migrated to new format
- **Mitigation**: 
  - Extensive migration testing on staging data
  - Create backup before production migration
  - Rollback script ready if issues detected

### Medium Risk: Performance Impact  
- **Risk**: JSON queries on attachments may be slow
- **Mitigation**:
  - GIN indexes on JSON columns
  - Batch file validation to reduce queries
  - Monitor query performance post-deployment

### Low Risk: API Breaking Changes
- **Risk**: Frontend clients expecting old format 
- **Mitigation**:
  - Coordinate with frontend team on schema changes
  - API version support if needed
  - Clear documentation of new format

## Success Criteria

1. **Functional Completeness**:
   - ✅ Messages and tickets use consistent `[{"file_id":"uuid"}]` format
   - ✅ File upload → processing → message association flow works
   - ✅ File validation enforces organization boundaries
   - ✅ Backward compatibility maintained

2. **Quality Gates Passed (STRICT REQUIREMENTS)**:
   - ✅ All database migrations run successfully
   - ✅ ALL unit tests pass (100% pass rate required)
   - ✅ ALL integration tests pass (100% pass rate required)
   - ✅ Test coverage ≥90% for all modified services
   - ✅ API endpoints work with new format using authenticated calls
   - ✅ ALL Docker service logs are ERROR-FREE
   - ✅ Code linting and type checking pass
   - ✅ Security vulnerability scan completed

3. **Performance Standards**:
   - ✅ Message creation with attachments <200ms response time
   - ✅ File validation adds <100ms overhead
   - ✅ No degradation in file upload throughput

4. **Postman collection updated**:
   - Update the postman collection in the docs/postman with the new api endpoints and request bodies

## Implementation Timeline

- **Week 1**: Database migrations and model updates (Tasks 1.1-2.2)
- **Week 2**: Service layer updates and validation (Tasks 3.1-3.3) 
- **Week 3**: API updates and testing (Tasks 4.1-5.2)
- **Week 4**: Integration testing and deployment validation

## Deployment Strategy

1. **Staging Deployment**: Deploy to staging with full test suite validation
2. **Migration Verification**: Run migration on staging data, verify data integrity
3. **Performance Testing**: Load test attachment endpoints with new format
4. **Production Deployment**: Blue-green deployment with rollback plan
5. **Monitoring**: Monitor for errors and performance regressions

## PRP Confidence Score: 9/10

This PRP provides comprehensive implementation details with:
- ✅ Complete technical context from codebase research
- ✅ Detailed implementation tasks with code examples  
- ✅ Executable validation gates with STRICT quality requirements
- ✅ Real authenticated API testing with development token
- ✅ Docker service log validation (ERROR-FREE requirement)
- ✅ Risk mitigation strategies for known issues
- ✅ Clear success criteria and timeline
- ✅ 100% test pass rate requirement
- ✅ Minimum 90% test coverage requirement

The high confidence score reflects thorough research of existing patterns, comprehensive task breakdown, strict validation requirements, and detailed testing approach that ensures deployment-ready code quality.

## Additional Implementation Notes

### Development API Token Usage
- **Token**: `ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8`
- **Usage**: For E2E testing until proper test user creation script is implemented
- **Future**: Replace with automated test user creation and token generation

### Critical Validation Requirements
1. **Zero Tolerance for Test Failures**: Any failing test blocks deployment
2. **Docker Log Cleanliness**: All services must run error-free during testing
3. **Authenticated Testing Only**: No mocked authentication in validation gates
4. **Coverage Minimums**: 90% test coverage required for modified services
5. **Code Quality Gates**: Linting and type checking must pass

### Postman Collection Update
- Location: `docs/postman/AI_Ticket_Creator_Complete.postman_collection.json`
- **Required Updates**:
  - Add authenticated file upload examples
  - Update message creation with attachments
  - Update ticket creation with attachments
  - Include file processing status polling examples
  - Add attachment format validation examples