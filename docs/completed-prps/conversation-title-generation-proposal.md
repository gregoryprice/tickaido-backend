# Conversation Title Generation API Implementation Proposal

## Overview

This proposal outlines the implementation of an AI-powered conversation title generation endpoint for the AI Ticket Creator Backend API. The feature will analyze all messages within a conversation and generate a concise, meaningful title suggestion that summarizes the conversation's content and context.

**IMPORTANT**: The generate_title endpoint is **READ-ONLY** and does NOT modify the conversation's title. It only generates and returns a suggested title. The actual title update must be done through the existing `PATCH /api/v1/chat/conversations/{conversation_id}/title` endpoint.

## Current State Analysis

The existing chat system has:
- **ChatConversation** model with a `title` field (max 500 chars) that defaults to "New Conversation"
- **ChatMessage** model storing user and assistant messages with full content
- **AI infrastructure** with PydanticAI agents and multi-provider support (OpenAI, Gemini)
- **Existing AI services** for customer support operations via `ai_chat_service.py`

### Existing Infrastructure
- **AI Config**: `app/config/ai_config.yaml` with gpt-4o-mini/gpt-4 models
- **PydanticAI Agents**: Customer support agent with MCP integration
- **Multi-provider Support**: OpenAI/Gemini with fallback chains
- **Message Storage**: Full conversation history in `chat_messages` table

## Proposed Implementation

### 1. API Endpoint

Add new endpoint to the existing chat router (`app/api/v1/chat.py`):

#### Generate Title (Read-Only)
```
GET /api/v1/chat/conversations/{conversation_id}/generate_title
```

**Note**: This endpoint generates a title suggestion but does NOT modify the conversation. To actually update the title, clients must call the existing `PATCH /api/v1/chat/conversations/{conversation_id}/title` endpoint with the generated title.

### 2. Service Layer Implementation

#### 2.1 Title Generation Agent

Create dedicated AI agent in `app/agents/title_generation_agent.py`:

```python
class TitleGenerationAgent:
    """PydanticAI agent for generating conversation titles"""
    
    async def generate_title(
        self,
        messages: List[ChatMessage],
        current_title: Optional[str] = None
    ) -> TitleGenerationResult
```

#### 2.2 AI Chat Service Extension

Extend `app/services/ai_chat_service.py` with:

```python
async def generate_conversation_title(
    self,
    conversation_id: str,
    user_id: str,
    force_regenerate: bool = False
) -> TitleGenerationResponse
```

#### 2.3 Chat Service Extension

Extend `app/services/chat_service.py` with:

```python
async def generate_title_suggestion(
    self,
    db: AsyncSession,
    conversation_id: UUID,
    user_id: UUID
) -> Optional[TitleGenerationResult]
```

### 3. Schema Implementation

Add schemas in `app/schemas/chat.py`:

```python
class GenerateTitleResponse(BaseSchema):
    """Response schema for title generation (read-only)"""
    
    id: UUID = Field(description="Conversation ID")
    title: str = Field(description="AI-generated title suggestion")
    current_title: str = Field(description="Current conversation title")
    generated_at: datetime = Field(description="When title was generated")
    confidence: float = Field(description="AI confidence score (0-1)")
    
class TitleGenerationResult(BaseModel):
    """Internal result from title generation agent"""
    
    title: str = Field(description="Generated title", max_length=500)
    confidence: float = Field(description="Confidence score (0-1)", ge=0, le=1)
```

### 4. AI Integration Strategy

#### 4.1 Model Selection
- **Primary**: `gpt-4o-mini` (fast, cost-effective for summarization)
- **Fallback**: `gpt-4` (higher quality if primary fails)
- **Configuration**: Use existing `ai_config.yaml` settings

#### 4.2 Prompt Design

```python
TITLE_GENERATION_PROMPT = """
You are an expert at creating concise, descriptive titles for customer support conversations.

Analyze the conversation below and generate a clear, specific title that captures:
1. The main topic or issue discussed
2. The type of request (question, problem, feature request, etc.)
3. Key technical details if relevant

Guidelines:
- Maximum 8 words, ideally 3-6 words
- Use professional, clear language
- Avoid generic terms like "Help", "Support", "Question"
- Include specific technology/product names when relevant
- Prioritize the most important aspect of the conversation

Examples of good titles:
- "Password Reset Email Issues"
- "API Rate Limiting Configuration"
- "Database Migration Rollback"
- "Billing Dispute Resolution"

Conversation Messages:
{conversation_content}

Current title: "{current_title}"

Generate a title that is more specific and descriptive than the current one.
"""
```

#### 4.3 Input Processing
- **Message Aggregation**: Combine all user and assistant messages
- **Content Filtering**: Remove sensitive information (if any)
- **Length Management**: Truncate if total content > 4000 chars (keep first/last messages)
- **Context Preservation**: Maintain conversation flow and key topics

## Detailed Implementation Plan

### Phase 1: AI Agent and Service Implementation

#### Step 1.1: Title Generation Agent
**Implementation:**
- Create `app/agents/title_generation_agent.py`
- Implement PydanticAI agent with title generation prompt
- Add conversation analysis and title generation logic
- Include confidence scoring and reasoning

**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Create unit tests for title generation agent
poetry run pytest tests/test_title_generation_agent.py -v

# Test cases must include:
# - Generate title for short conversation (2-3 messages)
# - Generate title for long conversation (10+ messages)
# - Handle empty conversation (no messages)
# - Handle conversation with only user messages
# - Handle conversation with sensitive content
# - Confidence scoring validation
# - Error handling for AI service failures
# - Alternative title generation
```

**Exit Criteria:**
- [ ] All title generation agent tests pass
- [ ] Code coverage > 90% for new agent
- [ ] AI confidence scores are reasonable (>0.7 for good titles)
- [ ] Generated titles follow length and quality guidelines

#### Step 1.2: AI Chat Service Extension
**Implementation:**
- Add `generate_conversation_title` method to `ai_chat_service.py`
- Integrate with title generation agent
- Add message retrieval and processing logic
- Implement error handling and fallbacks

**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Create unit tests for AI chat service extension
poetry run pytest tests/test_ai_chat_service.py::test_generate_conversation_title -v

# Test cases must include:
# - Generate title for existing conversation (success)
# - Generate title for non-existent conversation (error)
# - Generate title for empty conversation (default behavior)
# - Handle AI service failures gracefully
# - Respect force_regenerate parameter
# - Performance with large conversations
# - Token usage tracking
```

**Exit Criteria:**
- [ ] All AI chat service tests pass
- [ ] Integration with existing AI infrastructure works
- [ ] Error handling comprehensive
- [ ] Performance acceptable for conversations with 50+ messages

#### Step 1.3: Chat Service Extension
**Implementation:**
- Add `generate_title` method to `chat_service.py`
- Integrate with AI chat service
- Add database update logic
- Implement ownership validation and transaction handling

**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Phase 1.3 MANDATORY Testing - Chat Service Extension  
poetry run pytest tests/test_chat_service.py::TestTitleGenerationService -v

# REQUIRED Test Cases (ALL must pass):
# ✓ test_generate_title_suggestion_success - returns suggestion without DB update
# ✓ test_generate_title_suggestion_nonexistent - returns None for invalid conversation
# ✓ test_generate_title_suggestion_unauthorized - returns None for other user's conversation
# ✓ test_generate_title_suggestion_deleted_conversation - returns None for deleted
# ✓ test_generate_title_suggestion_archived_conversation - works with archived
# ✓ test_message_retrieval_optimization - efficient message queries
# ✓ test_large_message_handling - handles conversations with many messages
# ✓ test_concurrent_access_safety - thread-safe operations
# ✓ test_database_transaction_isolation - no side effects on failure
# ✓ test_ownership_validation_edge_cases - comprehensive access control
# ✓ test_message_ordering_preservation - maintains chronological order
# ✓ test_deleted_message_exclusion - ignores soft-deleted messages
# ✓ test_performance_with_pagination - efficient for large conversations
# ✓ test_database_connection_failure - handles DB failures gracefully
# ✓ test_sqlalchemy_query_optimization - uses proper indexes

# Database Performance Testing
poetry run pytest tests/test_chat_service.py::TestTitleGenerationPerformance -v

# Security and Authorization Testing
poetry run pytest tests/test_chat_service.py::TestTitleGenerationSecurity -v
```

**MANDATORY Exit Criteria (100% Required):**
- [ ] ALL 15 chat service tests pass without any failures or skips
- [ ] Code coverage ≥ 90% for new methods in `chat_service.py`
- [ ] Database operations are read-only (no updates to conversation)
- [ ] Ownership validation prevents unauthorized access in all scenarios
- [ ] No race conditions in concurrent title generation requests
- [ ] Database queries use proper indexes for performance
- [ ] Message retrieval efficiently handles large conversations
- [ ] Performance: <1 second for message retrieval (conversations <50 messages)
- [ ] Performance: <3 seconds for message retrieval (conversations <200 messages)
- [ ] Memory usage <30MB per title generation request
- [ ] Proper error handling for all database failure scenarios
- [ ] No side effects or data corruption on any failure

**BLOCKER CONDITIONS:**
🚫 If ANY test fails, you CANNOT proceed to Phase 2
🚫 If coverage is <90%, you CANNOT proceed to Phase 2
🚫 If security tests fail, you CANNOT proceed to Phase 2
🚫 If performance benchmarks fail, you CANNOT proceed to Phase 2

### Phase 2: API Endpoint Implementation

#### Step 2.1: Request/Response Schemas
**Implementation:**
- Add schemas to `app/schemas/chat.py`
- Implement validation rules
- Add comprehensive documentation

**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Test schema validation
poetry run pytest tests/test_schemas.py::test_title_generation_schemas -v

# Test cases must include:
# - Request schema validation with valid/invalid data
# - Response schema serialization
# - Field type validation and constraints
# - Optional field handling
# - JSON serialization/deserialization
```

**Exit Criteria:**
- [ ] Schema tests pass
- [ ] Validation rules comprehensive
- [ ] Documentation clear and accurate

#### Step 2.2: Generate Title Endpoint
**Implementation:**
- Add `PATCH /conversations/{conversation_id}/generate_title` endpoint
- Implement request validation and authentication
- Add comprehensive error handling
- Include logging and monitoring

**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Phase 2.2 MANDATORY Testing - Generate Title API Endpoint
poetry run pytest tests/test_chat_api_basic.py::TestGenerateTitleEndpoint -v

# REQUIRED Test Cases (ALL must pass):
# ✓ test_generate_title_success - 200 with valid conversation
# ✓ test_generate_title_nonexistent_conversation - 404 not found
# ✓ test_generate_title_no_authentication - 401/403 unauthorized
# ✓ test_generate_title_invalid_token - 401/403 invalid token
# ✓ test_generate_title_unauthorized_user - 404 for other user's conversation
# ✓ test_generate_title_deleted_conversation - 404 for deleted conversation
# ✓ test_generate_title_archived_conversation - 200 works with archived
# ✓ test_generate_title_invalid_uuid - 400 bad request format
# ✓ test_generate_title_malformed_uuid - 400 bad request format
# ✓ test_generate_title_empty_conversation - 200 handles no messages
# ✓ test_generate_title_ai_service_timeout - 500 with proper error message
# ✓ test_generate_title_ai_service_failure - 500 with fallback behavior
# ✓ test_generate_title_database_failure - 500 with proper error handling
# ✓ test_generate_title_rate_limiting - 429 when rate limit exceeded
# ✓ test_generate_title_response_format - validates all response fields
# ✓ test_generate_title_confidence_scoring - includes valid confidence score
# ✓ test_generate_title_current_title_preservation - doesn't modify DB
# ✓ test_generate_title_concurrent_requests - handles multiple simultaneous

# HTTP Method and Content Type Validation
poetry run pytest tests/test_chat_api_basic.py::TestGenerateTitleHTTP -v

# Response Schema Validation
poetry run pytest tests/test_chat_api_basic.py::TestGenerateTitleResponseValidation -v

# Manual Integration Testing (MANDATORY)
echo "Testing generate title endpoint manually..."
# Test 1: Valid conversation (expect 200 or 401/403 if no auth)
curl -X GET "http://localhost:8000/api/v1/chat/conversations/test-uuid/generate_title" \
     -H "Authorization: Bearer <valid-token>" \
     -w "\nStatus: %{http_code}\n"

# Test 2: Invalid conversation (expect 404)  
curl -X GET "http://localhost:8000/api/v1/chat/conversations/invalid-uuid/generate_title" \
     -H "Authorization: Bearer <valid-token>" \
     -w "\nStatus: %{http_code}\n"

# Test 3: No authentication (expect 401/403)
curl -X GET "http://localhost:8000/api/v1/chat/conversations/test-uuid/generate_title" \
     -w "\nStatus: %{http_code}\n"

# Test 4: Wrong HTTP method (expect 405)
curl -X POST "http://localhost:8000/api/v1/chat/conversations/test-uuid/generate_title" \
     -H "Authorization: Bearer <valid-token>" \
     -w "\nStatus: %{http_code}\n"
```

**MANDATORY Exit Criteria (100% Required):**
- [ ] ALL 20 API endpoint tests pass without any failures or skips
- [ ] Manual curl tests return expected status codes
- [ ] Response format matches GenerateTitleResponse schema exactly
- [ ] Error responses follow FastAPI/HTTP standards
- [ ] OpenAPI documentation generates correctly
- [ ] No database modifications during title generation
- [ ] Rate limiting works correctly for new endpoint
- [ ] Authentication/authorization enforced properly
- [ ] HTTP method restrictions work (GET only)
- [ ] Content-Type headers handled correctly
- [ ] CORS headers included if configured
- [ ] Request/response logging works properly

**BLOCKER CONDITIONS:**
🚫 If ANY test fails, you CANNOT proceed to Step 2.3
🚫 If manual testing reveals any issues, you CANNOT proceed to Step 2.3
🚫 If OpenAPI spec is malformed, you CANNOT proceed to Step 2.3
🚫 If any database modification detected, you CANNOT proceed to Step 2.3

### Phase 3: Integration & Performance Testing

#### Step 3.1: Complete Integration Testing
**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Run full integration test suite
poetry run pytest tests/test_chat_integration.py::test_title_generation_workflow -v

# REQUIRED E2E Workflow (ALL steps must pass):
# 1. Create conversation via API
# 2. Add multiple messages (user and assistant) via API
# 3. Generate title suggestion (GET /generate_title) - verify NO DB modification
# 4. Verify suggested title quality and format
# 5. Apply suggested title via existing PATCH /title endpoint  
# 6. Verify title persistence in conversation
# 7. Generate title again - verify consistent suggestions
# 8. Test with archived conversation - verify works correctly
# 9. Test with unarchived conversation - verify works correctly
# 10. Test title update workflow with generated suggestions
```

**Exit Criteria:**
- [ ] All existing tests continue to pass (no regressions)
- [ ] New integration tests pass
- [ ] End-to-end workflow validates correctly
- [ ] Title quality meets standards

#### Step 3.2: Performance and Scalability Testing
**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Performance testing
poetry run pytest tests/test_title_generation_performance.py -v

# Test scenarios:
# - Title generation for conversations with 1-5 messages
# - Title generation for conversations with 10-25 messages  
# - Title generation for conversations with 50+ messages
# - Concurrent title generation requests
# - AI service timeout handling
# - Memory usage with large conversations
# - Token usage optimization
```

**Exit Criteria:**
- [ ] Response time < 3 seconds for typical conversations
- [ ] Response time < 10 seconds for large conversations (50+ messages)
- [ ] Memory usage reasonable
- [ ] Token usage optimized
- [ ] Concurrent requests handled properly

#### Step 3.3: Security and Data Privacy Testing
**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Security testing
poetry run pytest tests/test_title_generation_security.py -v

# Test scenarios:
# - Cannot generate title for conversations owned by other users
# - JWT token validation works correctly
# - Rate limiting applies to new endpoint
# - Sensitive data not included in generated titles
# - SQL injection attempts fail safely
# - Input validation prevents malicious payloads
# - Generated titles don't leak sensitive information
```

**Exit Criteria:**
- [ ] All security tests pass
- [ ] Authorization properly enforced
- [ ] No data leakage in titles
- [ ] Input validation comprehensive

### Phase 4: Documentation and Final Validation

#### Step 4.1: Documentation Updates
**Implementation:**
- Update OpenAPI specification
- Add endpoint documentation with examples
- Create usage guidelines for title generation

**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Documentation validation
# - OpenAPI spec generates without errors
# - All endpoints documented with proper examples
# - Request/response schemas accurate
# - Error codes documented
# - Postman collection updated and tested
```

**Exit Criteria:**
- [ ] OpenAPI spec validates
- [ ] Documentation complete and accurate
- [ ] Examples tested and working

#### Step 4.2: Final System Validation
**Validation & Testing (MANDATORY - Cannot proceed without passing):**
```bash
# Complete system test
docker compose up -d
poetry run pytest tests/ -v --cov=app --cov-report=html

# Manual testing scenarios:
# 1. Create conversation via API
# 2. Send multiple messages
# 3. Generate title via API
# 4. Verify title in conversation list
# 5. Test with different conversation types
# 6. Test performance with various conversation sizes
```

**Exit Criteria:**
- [ ] All tests pass in clean environment
- [ ] Code coverage targets met (>90% for new code)
- [ ] Manual testing validates all scenarios
- [ ] Performance acceptable under realistic load

## API Specification

### Generate Title Endpoint

**Request:**
```http
GET /api/v1/chat/conversations/{conversation_id}/generate_title
Authorization: Bearer <token>
```

**Response (200 - Success):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "API Rate Limiting Configuration",
  "current_title": "New Conversation",
  "generated_at": "2024-01-15T10:30:00Z",
  "confidence": 0.89
}
```

## Critical Implementation Requirements

### **MANDATORY SEPARATION OF CONCERNS**

**🚨 CRITICAL**: The title generation endpoint (`GET /generate_title`) and title update endpoint (`PATCH /title`) are **COMPLETELY SEPARATE** operations:

1. **Title Generation** (`GET /generate_title`):
   - **READ-ONLY operation** - does NOT modify any database records
   - Analyzes conversation messages and generates title suggestions
   - Returns suggestions with confidence scores and alternatives
   - Can be called multiple times safely
   - No side effects on conversation or messages

2. **Title Update** (`PATCH /title` - existing endpoint):
   - **WRITE operation** - modifies the conversation title in database
   - Updates `title` field and `updated_at` timestamp
   - Requires explicit user action to apply generated suggestions
   - Single source of truth for title modifications

**VALIDATION REQUIREMENT**: Every test must verify that `GET /generate_title` does NOT modify the conversation title in the database.

### **USER WORKFLOW DESIGN**

The feature implements a **two-step workflow** for title management:

#### **Step 1: Generate Title Suggestion**
```bash
# User/Client calls title generation endpoint
GET /api/v1/chat/conversations/{id}/generate_title
→ Returns suggested title with alternatives and confidence score
→ NO database modification occurs
```

#### **Step 2: Apply Title (Optional)**
```bash  
# User/Client decides to apply the suggested title
PATCH /api/v1/chat/conversations/{id}/title
Content-Type: application/json
{"title": "API Rate Limiting Configuration"}
→ Updates conversation title in database
→ Updates updated_at timestamp
```

**Benefits of Two-Step Approach:**
- **User Control**: Users can review suggestions before applying
- **Safety**: No accidental title overwrites
- **Flexibility**: Users can modify suggested titles before applying
- **Consistency**: Single endpoint responsible for all title updates
- **Auditability**: Clear separation between suggestion and modification events

### **MANDATORY TESTING VALIDATION GATES**

**🛑 PHASE GATE SYSTEM**: Each phase has mandatory validation that must be 100% complete before proceeding:

- **Phase 1**: Service Layer Implementation - 41 tests total
- **Phase 2**: API Implementation - 23 tests total  
- **Phase 3**: Integration Testing - 36 scenarios total
- **Phase 4**: Final Validation - 18 criteria total

**TOTAL**: 118 validation points that must ALL pass

**🚫 BLOCKER POLICY**: 
- ANY single test failure blocks progression to next phase
- ANY coverage below 90% blocks progression
- ANY performance regression blocks progression
- ANY security vulnerability blocks progression

### **COMPREHENSIVE TESTING VALIDATION MATRIX**

| Phase | Component | Test Count | Must Pass | Coverage | Performance | Security |
|-------|-----------|------------|-----------|----------|-------------|----------|
| 1.1   | Title Agent | 15 tests | 100% | ≥90% | <2s small, <5s large | ✓ Content filtering |
| 1.2   | AI Service | 14 tests | 100% | ≥90% | <3s typical, <10s large | ✓ Token monitoring |
| 1.3   | Chat Service | 12 tests | 100% | ≥90% | <1s retrieval | ✓ Authorization |
| 2.1   | Schemas | 6 tests | 100% | ≥90% | <100ms | ✓ Input validation |
| 2.2   | API Endpoint | 17 tests | 100% | ≥90% | <500ms overhead | ✓ Auth enforcement |
| 3.1   | Integration | 14 tests | 100% | ≥90% | No regression | ✓ E2E security |
| 3.2   | Performance | 12 tests | 100% | ≥90% | Meet all targets | ✓ Load testing |
| 3.3   | Security | 10 tests | 100% | ≥90% | <5% overhead | ✓ Penetration |
| 4.1   | Documentation | 6 tests | 100% | N/A | N/A | ✓ API security |
| 4.2   | Final | 12 tests | 100% | ≥90% | Full system | ✓ Full audit |

**TOTAL VALIDATION POINTS**: 118 individual validation requirements

### **PHASE GATE APPROVAL CHECKLIST**

Before proceeding to each phase, the following MUST be verified:

#### ✅ **Phase 1 Gate** (Service Layer Complete)
- [ ] All 41 service layer tests pass (15+14+12)
- [ ] Code coverage ≥90% for all new service code
- [ ] Performance benchmarks met for all service operations
- [ ] Security validation complete for service layer
- [ ] No regressions in existing service functionality
- [ ] Database read operations optimized and indexed
- [ ] AI service integration stable and reliable

#### ✅ **Phase 2 Gate** (API Layer Complete)  
- [ ] All 23 API tests pass (6+17)
- [ ] OpenAPI documentation complete and accurate
- [ ] HTTP method restrictions enforced (GET only)
- [ ] Authentication/authorization working end-to-end
- [ ] Rate limiting integrated and functional
- [ ] Error responses follow FastAPI standards
- [ ] No database modifications in title generation endpoint

#### ✅ **Phase 3 Gate** (Integration Complete)
- [ ] All 36 integration tests pass (14+12+10)
- [ ] E2E workflows complete successfully
- [ ] Cross-system integration validated
- [ ] Performance testing under load complete
- [ ] Security testing complete with no vulnerabilities
- [ ] Regression testing shows zero impact on existing features

#### ✅ **Phase 4 Gate** (Production Ready)
- [ ] All 18 final validation tests pass (6+12)
- [ ] Documentation complete and reviewed
- [ ] Manual testing successful in clean environment
- [ ] Load testing validates production readiness
- [ ] Security audit complete with approval
- [ ] Deployment checklist complete

## Technical Architecture

### 1. AI Agent Design

#### Title Generation Agent Structure
```python
class TitleGenerationAgent:
    """Specialized agent for conversation title generation"""
    
    def __init__(self):
        self.agent_type = "title_generation_agent"
        self.model_preference = ["gpt-4o-mini", "gpt-4"]  # Fast, then quality
        self.max_input_tokens = 4000  # Conversation content limit
        
    async def analyze_conversation(
        self, 
        messages: List[ChatMessage]
    ) -> ConversationAnalysis
    
    async def generate_title(
        self,
        analysis: ConversationAnalysis,
        current_title: Optional[str] = None
    ) -> TitleGenerationResult
```

#### Conversation Analysis Logic
1. **Message Filtering**: Remove system messages, focus on user/assistant content
2. **Topic Extraction**: Identify main themes and technical terms
3. **Context Analysis**: Understand problem type (question, issue, request, etc.)
4. **Content Summarization**: Extract key points and resolution status
5. **Quality Assessment**: Determine if current title is adequate

### 2. Prompt Engineering Strategy

#### Core Prompt Template
```python
TITLE_GENERATION_PROMPT = """
You are an expert at creating concise, descriptive titles for customer support conversations.

Analyze this conversation and generate a title that captures the essence of the discussion.

CONVERSATION ANALYSIS:
- Total messages: {message_count}
- User messages: {user_message_count}  
- Assistant messages: {assistant_message_count}
- Conversation length: {conversation_length_chars} characters
- Current title: "{current_title}"

CONVERSATION CONTENT:
{formatted_messages}

TITLE GENERATION RULES:
1. Maximum 8 words, ideally 4-6 words
2. Use specific, descriptive terms
3. Avoid generic words: "Help", "Support", "Question", "Issue"
4. Include technical terms when relevant
5. Capture the primary topic/problem
6. Use title case formatting

EXAMPLES:
- "Password Reset Email Delivery"
- "API Authentication Token Expiry" 
- "Database Connection Pool Timeout"
- "Feature Request: Dark Mode"
- "Billing Invoice Payment Error"

Generate a title that is more specific and informative than "{current_title}".
"""
```

#### Content Processing
- **Message Aggregation**: Combine messages with role indicators
- **Length Management**: Truncate to fit within token limits
- **Sensitive Data Filtering**: Remove potential PII or credentials
- **Technical Term Preservation**: Maintain important technical context

### 3. Database Integration

#### Title Update Logic
1. **Ownership Validation**: Verify user owns conversation
2. **Message Retrieval**: Get all conversation messages
3. **AI Processing**: Generate title using AI agent
4. **Atomic Update**: Update conversation title and timestamp
5. **Audit Trail**: Log title generation events

#### Performance Considerations
- **Indexing**: Utilize existing conversation indexes
- **Caching**: Consider caching titles for frequently accessed conversations
- **Batch Processing**: Support future bulk title generation
- **Token Tracking**: Monitor AI usage and costs

## Error Handling

### Standard Error Responses

- **400 Bad Request**: Invalid conversation ID format or request body
- **401 Unauthorized**: Missing or invalid authentication token
- **404 Not Found**: Conversation doesn't exist or user doesn't have access
- **422 Unprocessable Entity**: AI service unable to generate appropriate title
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Database or AI service errors
- **503 Service Unavailable**: AI service temporarily unavailable

### Error Scenarios and Handling

1. **Empty Conversation**: Return default behavior or error
2. **AI Service Failure**: Graceful degradation, return error with retry suggestion
3. **Very Long Conversations**: Implement content truncation strategy
4. **Sensitive Content**: Filter out sensitive information before AI processing
5. **Non-English Content**: Handle multi-language conversations appropriately

## Security Considerations

1. **Data Privacy**: Ensure conversation content is not logged in plain text
2. **Access Control**: Strict ownership validation for all operations
3. **Rate Limiting**: Prevent abuse of AI services via existing middleware
4. **Content Filtering**: Remove sensitive information before AI processing
5. **Audit Logging**: Track title generation events for compliance
6. **Token Usage Monitoring**: Prevent excessive AI service usage

## Performance Requirements

### Response Time Targets
- **Small conversations (1-5 messages)**: < 1.5 seconds
- **Medium conversations (6-20 messages)**: < 3 seconds  
- **Large conversations (21-50 messages)**: < 5 seconds
- **Very large conversations (50+ messages)**: < 10 seconds

### Resource Usage Limits
- **Token Usage**: < 500 tokens per title generation (input + output)
- **Memory Usage**: < 50MB per request
- **Database Queries**: < 3 queries per title generation
- **Concurrent Requests**: Support 10+ simultaneous title generations

## Implementation Files

### New Files to Create
1. `app/agents/title_generation_agent.py` - Dedicated title generation agent
2. `tests/test_title_generation_agent.py` - Agent unit tests
3. `tests/test_title_generation_performance.py` - Performance tests
4. `tests/test_title_generation_security.py` - Security tests

### Files to Modify
1. `app/services/ai_chat_service.py` - Add title generation method
2. `app/services/chat_service.py` - Add title generation orchestration
3. `app/api/v1/chat.py` - Add generate_title endpoint
4. `app/schemas/chat.py` - Add request/response schemas
5. `tests/test_chat_integration.py` - Add integration tests
6. `tests/test_chat_api_basic.py` - Add API endpoint tests
7. `tests/test_ai_chat_service.py` - Add AI service tests
8. `tests/test_chat_service.py` - Add service tests

## Quality Assurance

### Title Quality Metrics
- **Specificity**: Title should be more specific than "New Conversation"
- **Relevance**: Title should reflect actual conversation content
- **Conciseness**: Follow length guidelines (4-8 words)
- **Clarity**: Understandable to users not familiar with conversation
- **Consistency**: Similar conversations should generate similar titles

### Validation Criteria
- **AI Confidence**: Minimum 0.6 confidence score for generated titles
- **User Testing**: Generated titles should make sense to human reviewers
- **A/B Testing**: Compare generated titles vs. human-created titles
- **Performance Benchmarks**: Meet response time requirements consistently

## Backward Compatibility

- **Existing Endpoints**: No breaking changes to current API
- **Database Schema**: No migration required (title field already exists)
- **Default Behavior**: Conversations retain existing titles unless explicitly regenerated
- **Client Integration**: New endpoint is optional, existing functionality unaffected

## Future Enhancements

1. **Bulk Title Generation**: Generate titles for multiple conversations
2. **Smart Title Updates**: Auto-regenerate titles when conversations evolve significantly
3. **Title History**: Track title changes over time
4. **Custom Title Templates**: Allow users to customize title generation rules
5. **Multi-language Support**: Generate titles in user's preferred language
6. **Title Quality Feedback**: Allow users to rate and improve title generation

## Risk Assessment

### Technical Risks
- **AI Service Availability**: Mitigated by multi-provider fallback
- **Token Cost Escalation**: Mitigated by usage monitoring and limits
- **Performance Degradation**: Mitigated by timeout controls and caching
- **Data Privacy**: Mitigated by content filtering and secure processing

### Mitigation Strategies
- **Circuit Breaker**: Disable title generation if AI services fail repeatedly
- **Usage Quotas**: Implement per-user limits on title generation
- **Content Sanitization**: Remove sensitive data before AI processing
- **Graceful Degradation**: Continue functioning even if title generation fails

## Implementation Timeline

- **Phase 1 (AI Agent & Services):** 8-12 hours
  - Implementation: 4-6 hours
  - **Comprehensive Testing & Validation: 4-6 hours** (48 tests)
- **Phase 2 (API Endpoint):** 6-10 hours
  - Implementation: 2-4 hours
  - **Comprehensive Testing & Validation: 4-6 hours** (35 tests)
- **Phase 3 (Integration & Performance):** 8-12 hours
  - Integration Testing: 4-6 hours
  - **Performance & Security Testing: 4-6 hours** (22 scenarios)
- **Phase 4 (Documentation & Final Validation):** 4-6 hours
  - Documentation: 2-3 hours
  - **Final Comprehensive Validation: 2-3 hours** (15 criteria)
- **Total Estimated Time:** 26-40 hours

**⚠️ IMPORTANT**: This timeline includes mandatory comprehensive testing that cannot be skipped or abbreviated.

**Critical Dependencies:**
- Existing AI infrastructure must remain stable
- Database performance with message queries optimized  
- AI service provider availability and quotas sufficient
- Rate limiting configuration compatibility maintained
- **ALL existing tests must continue passing throughout implementation**

## **MANDATORY VALIDATION SUMMARY**

### **🚨 CRITICAL SUCCESS CRITERIA**

Before considering this feature complete, the following MUST be validated:

#### **Functional Validation (MANDATORY)**
- [ ] Title generation endpoint is READ-ONLY (never modifies database)
- [ ] Generated titles meet quality standards (specific, 3-8 words, professional)
- [ ] Confidence scores provided and validated (0-1 range)
- [ ] Integration with existing title update endpoint works seamlessly
- [ ] All error scenarios handled gracefully with proper HTTP status codes
- [ ] Performance targets met for all conversation sizes

#### **Security Validation (MANDATORY)**
- [ ] Authorization prevents access to other users' conversations
- [ ] Content filtering removes sensitive information before AI processing
- [ ] Rate limiting prevents abuse of AI services
- [ ] Input validation prevents injection attacks
- [ ] Audit logging captures all title generation events
- [ ] No data leakage in error responses

#### **Quality Validation (MANDATORY)**
- [ ] Code coverage ≥90% for ALL new code
- [ ] ALL 137 test validation points pass
- [ ] Zero regressions in existing functionality
- [ ] OpenAPI documentation complete and accurate
- [ ] Manual testing validates all scenarios
- [ ] Performance benchmarks met under realistic load

#### **Production Readiness (MANDATORY)**
- [ ] Clean environment deployment successful
- [ ] Load testing validates scalability
- [ ] Monitoring and observability adequate
- [ ] Error handling comprehensive
- [ ] Resource usage within acceptable limits
- [ ] Database queries optimized and indexed

**🛑 DEPLOYMENT BLOCKERS**: If ANY of the above criteria fail, the feature CANNOT be deployed to production.

## Success Metrics

### Functional Success
- [ ] All test suites pass (unit, integration, performance, security)
- [ ] API endpoints respond within performance targets
- [ ] Generated titles meet quality standards
- [ ] Error handling comprehensive and user-friendly

### Quality Success  
- [ ] Code coverage > 90% for all new code
- [ ] Zero security vulnerabilities introduced
- [ ] OpenAPI documentation complete and accurate
- [ ] Integration with existing systems seamless

### User Experience Success
- [ ] Generated titles are more descriptive than defaults
- [ ] Response times acceptable for interactive use
- [ ] Error messages clear and actionable
- [ ] Backward compatibility maintained

## Deployment Considerations

### Environment Requirements
- **AI API Keys**: Ensure OpenAI/Gemini keys have sufficient quota
- **Rate Limits**: Configure appropriate limits for title generation
- **Monitoring**: Add metrics for title generation usage and quality
- **Logging**: Ensure proper logging without exposing sensitive data

### Rollout Strategy
1. **Development Environment**: Full implementation and testing
2. **Staging Environment**: Integration testing with realistic data
3. **Production Deployment**: Gradual rollout with monitoring
4. **Feature Flag**: Ability to disable if issues arise

### Monitoring and Observability
- **Usage Metrics**: Track title generation requests and success rates
- **Performance Metrics**: Monitor response times and AI service usage
- **Quality Metrics**: Track user feedback on generated titles
- **Error Metrics**: Monitor failure rates and error types
- **Cost Metrics**: Track AI service usage and associated costs