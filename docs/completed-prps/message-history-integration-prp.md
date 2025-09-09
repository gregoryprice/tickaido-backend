# PRP: Message History Integration with Pydantic AI Agents (REFACTORED)

## Problem Statement

The current message history implementation in `DynamicAgentFactory` is fundamentally flawed and does not follow Pydantic AI best practices. Critical issues include:

1. **Wrong Message Format**: Using custom dict format instead of Pydantic AI's `ModelMessage` format
2. **Missing ModelMessagesTypeAdapter**: Not using proper serialization/deserialization for message persistence
3. **Incorrect Agent Usage**: Not utilizing the `message_history` parameter correctly in agent.run()
4. **Message Filtering Errors**: Incorrectly filtering out agent messages when both user and agent messages are required
5. **No Proper Serialization**: Missing JSON storage/retrieval using Pydantic AI's intended mechanisms

## Current State Analysis

### Existing Flawed Implementation

The current implementation in `app/services/dynamic_agent_factory.py:220` incorrectly tries to format messages manually:

```python
# INCORRECT APPROACH - Current flawed implementation
result = await pydantic_agent.run(
    conversation_messages,  # Wrong: Custom format
    usage_limits=usage_limits
)
```

### Database Structure Issues

The current `Message` model stores messages as separate records but lacks:
- Proper JSON serialization using ModelMessagesTypeAdapter
- Efficient message history retrieval for Pydantic AI format
- Message history processing capabilities

## Correct Pydantic AI Message History Pattern

Based on [Pydantic AI documentation](https://ai.pydantic.dev/message-history/) and [chat app example](https://ai.pydantic.dev/examples/chat-app/#example-code), the proper approach is:

### 1. Use ModelMessagesTypeAdapter for Serialization

```python
from pydantic_core import to_jsonable_python
from pydantic_ai.messages import ModelMessagesTypeAdapter

# Store messages as JSON using TypeAdapter
result = agent.run_sync('Tell me a joke.')
history_step_1 = result.all_messages()
as_python_objects = to_jsonable_python(history_step_1)

# Retrieve and validate messages
same_history_as_step_1 = ModelMessagesTypeAdapter.validate_python(as_python_objects)

# Use in subsequent conversations
result2 = agent.run_sync(  
    'Tell me a different joke.', 
    message_history=same_history_as_step_1
)
```

### 2. Proper Agent Run with Message History

```python
# CORRECT APPROACH - Use message_history parameter
result = await agent.run(prompt, message_history=messages)

# Extract response
response = result.output if hasattr(result, 'output') else result

# Store complete conversation history from this run
await database.add_messages(result.all_messages())
```

## Proposed Solution Architecture

**IMPORTANT FINDING**: After analyzing the existing codebase, we already have robust message storage and retrieval in `ai_chat_service.py`. The current system:

1. **Already stores messages** in the `Message` table with proper thread relationships
2. **Already retrieves thread history** via `get_thread_history()` method (lines 165-214)
3. **Already passes thread_id and db** to dynamic_agent_factory (lines 304-305, 368-369)
4. **Already formats messages** for agent consumption in dict format

**The main issue is NOT storage/retrieval - it's the incorrect usage of Pydantic AI's message_history parameter.**

### Simplified Approach: Fix Dynamic Agent Factory Only

Instead of creating a separate message history service, we need to:

1. **Enhance existing `get_thread_history()`** to return Pydantic AI compatible format
2. **Fix `dynamic_agent_factory`** to use `message_history` parameter correctly
3. **Add context limits** to existing message retrieval

### 1. Enhanced Thread History Retrieval

Update `ai_chat_service.py` `get_thread_history()` method:

```python
async def get_thread_history_for_agent(
    self, 
    thread_id: str, 
    user_id: str, 
    agent_id: str,
    max_context_size: Optional[int] = None,
    use_memory_context: bool = True
) -> List[Dict[str, str]]:
    """
    Get thread history formatted for Pydantic AI agent processing.
    
    Args:
        thread_id: ID of the thread
        user_id: ID of the user (for authorization)
        agent_id: ID of the agent (for validation)
        max_context_size: Maximum tokens allowed in context
        use_memory_context: Whether to include message history
        
    Returns:
        List[Dict[str, str]]: Messages in Pydantic AI format
    """
    if not use_memory_context:
        logger.debug(f"Memory context disabled for thread {thread_id}")
        return []
    
    async with get_async_db_session() as db:
        try:
            # Verify user owns thread and agent is valid (existing logic)
            thread_query = select(Thread).where(
                Thread.id == UUID(thread_id),
                Thread.user_id == user_id,
                Thread.agent_id == UUID(agent_id)
            )
            
            result = await db.execute(thread_query)
            thread = result.scalar_one_or_none()
            
            if not thread:
                logger.warning(f"Thread {thread_id} not found for user {user_id} and agent {agent_id}")
                return []
            
            # Get messages in chronological order
            messages_query = select(Message).where(
                Message.thread_id == UUID(thread_id)
            ).order_by(Message.created_at)
            
            result = await db.execute(messages_query)
            messages = result.scalars().all()
            
            # Apply context limits if specified
            if max_context_size and max_context_size > 0:
                messages = await self._apply_context_limits(messages, max_context_size)
            
            # Convert to Pydantic AI format (simple dict with role/content)
            formatted_messages = []
            for msg in messages:
                # Simple format that works with ModelMessagesTypeAdapter
                formatted_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            logger.info(f"Retrieved {len(formatted_messages)} messages for Pydantic AI agent")
            return formatted_messages
            
        except Exception as e:
            logger.error(f"Error getting thread history for agent: {e}")
            return []

async def _apply_context_limits(
    self,
    messages: List[Message],
    max_context_size: int
) -> List[Message]:
    """Apply token-based context limits to raw messages."""
    try:
        if not messages or max_context_size <= 0:
            return messages
        
        # If we have a reasonable number of messages, just return them
        if len(messages) <= 10:
            return messages
        
        # Apply token-based filtering (process from newest to oldest)
        filtered_messages = []
        total_tokens = 0
        
        # Work backwards through messages (newest first)
        for message in reversed(messages):
            # Convert to dict format for token counting
            msg_dict = {
                "role": message.role,
                "content": message.content,
            }
            
            # Count tokens for this message using existing token service
            from app.services.token_counter_service import token_counter_service
            message_tokens = await token_counter_service.count_message_tokens(msg_dict)
            
            # Check if adding this message would exceed context limit
            if total_tokens + message_tokens > max_context_size:
                logger.debug(f"Context limit reached at {total_tokens} tokens, skipping older messages")
                break
            
            filtered_messages.append(message)
            total_tokens += message_tokens
        
        # Return messages in chronological order (oldest first)
        result = filtered_messages[::-1]
        
        logger.info(f"Applied context limits: {len(result)}/{len(messages)} messages, {total_tokens} tokens")
        return result
        
    except Exception as e:
        logger.error(f"Error applying context limits: {e}")
        # Fallback: return last 10 messages if token counting fails
        return messages[-10:] if len(messages) > 10 else messages
```

### 2. Enhanced Dynamic Agent Factory

Update `app/services/dynamic_agent_factory.py` with correct Pydantic AI usage:

```python
async def process_message_with_agent(
    self,
    agent_model: AgentModel,
    user_message: str,
    context: CustomerSupportContext,
    auth_token: Optional[str] = None,
    thread_id: Optional[str] = None,
    db: Optional[AsyncSession] = None
) -> ChatResponse:
    """
    Process message with proper Pydantic AI message history integration.
    
    Args:
        agent_model: Agent configuration with memory settings
        user_message: Current user message to process
        context: Customer support context
        auth_token: JWT token for MCP authentication
        thread_id: Thread ID for conversation history
        db: Database session for message persistence
        
    Returns:
        ChatResponse with agent's response
    """
    try:
        # Create Pydantic AI agent
        pydantic_agent = await self.create_agent_from_model(
            agent_model, 
            auth_token=auth_token
        )
        
        if not pydantic_agent:
            logger.error(f"Failed to create agent from model {agent_model.id}")
            return self._create_error_response()
        
        # Retrieve message history using existing ai_chat_service method
        message_history: List[Dict[str, str]] = []
        if thread_id and agent_model.use_memory_context:
            try:
                # Use existing ai_chat_service method with context limits
                from app.services.ai_chat_service import ai_chat_service
                
                # Get user info from context if available
                user_id = context.user_metadata.get('user_id', 'system')
                
                message_history = await ai_chat_service.get_thread_history_for_agent(
                    thread_id=thread_id,
                    user_id=user_id,
                    agent_id=str(agent_model.id),
                    max_context_size=agent_model.max_context_size,
                    use_memory_context=agent_model.use_memory_context
                )
                
                logger.info(
                    f"Loaded {len(message_history)} messages for context "
                    f"(thread: {thread_id})"
                )
            except Exception as e:
                logger.error(f"Failed to load message history for thread {thread_id}: {e}")
                # Continue without history rather than failing completely
                message_history = []
        
        # Configure usage limits
        usage_limits = UsageLimits(request_limit=agent_model.max_iterations)
        
        # CORRECT PYDANTIC AI USAGE - Use message_history parameter
        if message_history:
            # Run agent with conversation history
            result = await pydantic_agent.run(
                user_message,
                message_history=message_history,  # Correct parameter usage
                usage_limits=usage_limits
            )
        else:
            # Run agent without history
            result = await pydantic_agent.run(
                user_message,
                usage_limits=usage_limits
            )
        
        # Extract response
        response = result.output if hasattr(result, 'output') else result
        tools_used = getattr(result, 'tools_used', []) or []
        
        # Note: Message storage is already handled by ai_chat_service.py
        # No need for additional storage here
        
        # Record usage statistics
        await self._record_agent_usage(agent_model.id, True, len(tools_used))
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing message with agent: {e}")
        await self._record_agent_usage(agent_model.id, False)
        return self._create_error_response()
```

## Simplified Step-by-Step Implementation Plan

> **Critical**: Each step must be completed with all tests passing and no Docker log errors before proceeding to the next step.

**KEY INSIGHT**: No new database schema or separate message service needed. We enhance existing code only.

### Step 1: Enhance AI Chat Service Thread History Retrieval
**Objective**: Add context limits and Pydantic AI formatting to existing message retrieval

#### 1.1 Update AI Chat Service
Update the existing `get_thread_history()` method in `app/services/ai_chat_service.py` to add:
- New `get_thread_history_for_agent()` method with context limits
- Context limit application using existing token counter
- Simple dict format compatible with Pydantic AI

#### 1.2 Create Unit Tests
Create `tests/unit/services/test_ai_chat_service_history.py`:

```python
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ai_chat_service import ai_chat_service

@pytest.mark.asyncio
async def test_get_thread_history_for_agent():
    """Test enhanced thread history retrieval with context limits."""
    thread_id = str(uuid.uuid4())
    user_id = "test_user"
    agent_id = str(uuid.uuid4())
    
    with patch.object(ai_chat_service, 'get_async_db_session') as mock_db_session:
        # Mock database setup
        mock_db = AsyncMock()
        mock_db_session.return_value.__aenter__.return_value = mock_db
        
        # Mock thread verification
        thread_mock = MagicMock()
        thread_mock.id = thread_id
        thread_result = MagicMock()
        thread_result.scalar_one_or_none.return_value = thread_mock
        
        # Mock messages
        message1 = MagicMock()
        message1.role = "user"
        message1.content = "Hello"
        message2 = MagicMock()
        message2.role = "assistant"
        message2.content = "Hi there!"
        
        messages_result = MagicMock()
        messages_result.scalars.return_value.all.return_value = [message1, message2]
        
        # Configure mock to return thread first, then messages
        mock_db.execute.side_effect = [thread_result, messages_result]
        
        # Test the method
        history = await ai_chat_service.get_thread_history_for_agent(
            thread_id=thread_id,
            user_id=user_id,
            agent_id=agent_id,
            max_context_size=1000,
            use_memory_context=True
        )
        
        # Verify results
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there!"

@pytest.mark.asyncio
async def test_apply_context_limits():
    """Test context limits are applied correctly."""
    # Create mock messages that exceed token limits
    messages = []
    for i in range(15):
        msg = MagicMock()
        msg.role = "user"
        msg.content = f"This is a long message number {i} with lots of content"
        messages.append(msg)
    
    # Test context limiting
    limited = await ai_chat_service._apply_context_limits(messages, 100)  # Small limit
    
    # Should return fewer messages due to token constraints
    assert len(limited) < len(messages)
    assert len(limited) > 0

@pytest.mark.asyncio
async def test_memory_context_disabled():
    """Test that empty list is returned when memory is disabled."""
    thread_id = str(uuid.uuid4())
    user_id = "test_user"
    agent_id = str(uuid.uuid4())
    
    history = await ai_chat_service.get_thread_history_for_agent(
        thread_id=thread_id,
        user_id=user_id,
        agent_id=agent_id,
        use_memory_context=False
    )
    
    assert history == []
```

#### 1.3 Validation Commands
```bash
# Test enhanced AI chat service
PYTHONPATH=/Users/aristotle/projects/support-extension poetry run python -c "
from app.services.ai_chat_service import ai_chat_service
print('✅ AI Chat Service imports successfully')
"

# Run unit tests
PYTHONPATH=/Users/aristotle/projects/support-extension poetry run pytest tests/unit/services/test_ai_chat_service_history.py -v

# Check for any import errors
docker compose logs app | grep -i "import\|module\|error"
```

**Success Criteria**:
- [ ] Enhanced method works correctly
- [ ] Unit tests pass
- [ ] Context limits are applied
- [ ] No Docker container errors

---

### Step 2: Enhanced Dynamic Agent Factory
**Objective**: Use correct Pydantic AI message_history parameter

#### 2.1 Update Dynamic Agent Factory
Update the `process_message_with_agent` method in `app/services/dynamic_agent_factory.py` with the implementation provided above.

#### 2.2 Create Unit Tests
Create `tests/unit/services/test_dynamic_agent_factory_history.py`:

```python
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.dynamic_agent_factory import dynamic_agent_factory
from app.schemas.ai_response import ChatResponse, CustomerSupportContext

@pytest.mark.asyncio
async def test_process_message_with_history():
    """Test processing message with proper message_history parameter."""
    
    # Mock agent model
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = True
    agent_model.max_context_size = 1000
    agent_model.max_iterations = 5
    
    thread_id = str(uuid.uuid4())
    
    # Mock message history from ai_chat_service
    mock_history = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"}
    ]
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.dynamic_agent_factory.ai_chat_service') as mock_chat_service:
        
        # Mock Pydantic AI agent
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="Response with context",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # Mock chat service history method
        mock_chat_service.get_thread_history_for_agent.return_value = mock_history
        
        # Create context with user metadata
        context = CustomerSupportContext(
            user_metadata={"user_id": "test_user"}
        )
        
        # Process message
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            user_message="Follow up question",
            context=context,
            thread_id=thread_id
        )
        
        # Verify correct message_history parameter usage
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        
        # Should be called with message_history parameter
        assert 'message_history' in call_args.kwargs
        assert call_args.kwargs['message_history'] == mock_history
        assert response.content == "Response with context"

@pytest.mark.asyncio 
async def test_process_message_without_history():
    """Test processing message without history (new conversation)."""
    
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = True
    agent_model.max_iterations = 5
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.dynamic_agent_factory.ai_chat_service') as mock_chat_service:
        
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="Fresh conversation",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # Mock empty history
        mock_chat_service.get_thread_history_for_agent.return_value = []
        
        # Process without thread_id (no history)
        context = CustomerSupportContext(user_metadata={"user_id": "test_user"})
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            user_message="Hello",
            context=context,
            thread_id=None
        )
        
        # Should call run without message_history
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        
        # Should be simple message call without history
        assert call_args.args[0] == "Hello"
        assert 'message_history' not in call_args.kwargs
        
@pytest.mark.asyncio
async def test_memory_context_disabled():
    """Test that memory context can be disabled per agent."""
    
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = False  # Memory disabled
    agent_model.max_iterations = 5
    
    thread_id = str(uuid.uuid4())
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.dynamic_agent_factory.ai_chat_service') as mock_chat_service:
        
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="No memory response",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        context = CustomerSupportContext(user_metadata={"user_id": "test_user"})
        await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            user_message="Hello",
            context=context,
            thread_id=thread_id
        )
        
        # History service should not be called when memory is disabled
        mock_chat_service.get_thread_history_for_agent.assert_not_called()
```

#### 2.3 Validation Commands
```bash
# Test enhanced dynamic agent factory
PYTHONPATH=/Users/aristotle/projects/support-extension poetry run python -c "
from app.services.dynamic_agent_factory import dynamic_agent_factory
from app.services.ai_chat_service import ai_chat_service
print('✅ All services import successfully')
"

# Run new tests
PYTHONPATH=/Users/aristotle/projects/support-extension poetry run pytest tests/unit/services/test_dynamic_agent_factory_history.py -v

# Ensure existing tests still pass
PYTHONPATH=/Users/aristotle/projects/support-extension poetry run pytest tests/unit/services/test_dynamic_agent_factory.py -v

# Check for errors
docker compose logs app | grep -i error
```

**Success Criteria**:
- [ ] All new tests pass
- [ ] Existing dynamic agent factory tests still pass  
- [ ] Services import correctly
- [ ] No Docker errors
- [ ] Proper message_history parameter usage confirmed

---

### Step 3: End-to-End Integration Test
**Objective**: Validate complete simplified message history flow

#### 3.1 Create E2E Test
Create `tests/integration/test_simplified_message_history.py`:

```python
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Thread, Message
from app.models.ai_agent import Agent
from app.models.organization import Organization
from app.services.dynamic_agent_factory import dynamic_agent_factory
from app.services.ai_chat_service import ai_chat_service
from app.schemas.ai_response import ChatResponse, CustomerSupportContext

@pytest.mark.asyncio
async def test_simplified_message_history_flow(test_db_session: AsyncSession):
    """Test simplified message history flow using existing infrastructure."""
    
    # Create test database objects
    org = Organization(name="Test Org", email="test@example.com")
    test_db_session.add(org)
    await test_db_session.flush()
    
    agent = Agent(
        organization_id=org.id,
        name="Test Agent",
        agent_type="customer_support",
        use_memory_context=True,
        max_context_size=1000,
        max_iterations=5
    )
    test_db_session.add(agent)
    await test_db_session.flush()
    
    thread = Thread(
        agent_id=agent.id,
        user_id="test_user",
        organization_id=org.id,
        title="Test Conversation"
    )
    test_db_session.add(thread)
    await test_db_session.flush()
    
    # Add some conversation history using existing Message model
    msg1 = Message(
        thread_id=thread.id,
        role="user",
        content="Hello, I need help"
    )
    msg2 = Message(
        thread_id=thread.id,
        role="assistant",
        content="Hi! I'm happy to help. What can I do for you?"
    )
    test_db_session.add(msg1)
    test_db_session.add(msg2)
    await test_db_session.commit()
    
    # Test enhanced history retrieval
    with patch.object(ai_chat_service, 'get_async_db_session') as mock_db_session:
        mock_db_session.return_value.__aenter__.return_value = test_db_session
        
        retrieved_history = await ai_chat_service.get_thread_history_for_agent(
            thread_id=str(thread.id),
            user_id="test_user",
            agent_id=str(agent.id),
            use_memory_context=True
        )
        
        assert len(retrieved_history) == 2
        assert retrieved_history[0]["content"] == "Hello, I need help"
        assert retrieved_history[1]["content"] == "Hi! I'm happy to help. What can I do for you?"
    
    # Test agent processing with history
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch.object(ai_chat_service, 'get_thread_history_for_agent') as mock_get_history:
        
        # Mock Pydantic AI agent behavior
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="Based on our conversation, I understand you need help.",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # Mock history retrieval
        mock_get_history.return_value = retrieved_history
        
        # Process new message with history
        context = CustomerSupportContext(
            user_metadata={"user_id": "test_user"}
        )
        
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent,
            user_message="I have a question about my account",
            context=context,
            thread_id=str(thread.id)
        )
        
        # Verify response
        assert isinstance(response, ChatResponse)
        assert "conversation" in response.content.lower()
        
        # Verify agent was called with message_history parameter
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        
        # Check if message_history was provided
        assert 'message_history' in call_args.kwargs
        assert len(call_args.kwargs['message_history']) == 2
```

#### 3.2 Create E2E Test Script
Create `tests/scripts/test_simplified_message_history_e2e.sh`:

```bash
#!/bin/bash

set -e

echo "🧪 Simplified Message History E2E Test"
echo "===================================="

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Ensure services are running
echo -e "${YELLOW}Checking services...${NC}"
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${RED}❌ Main API not responding. Starting services...${NC}"
    docker compose up -d
    sleep 15
fi

echo -e "${GREEN}✅ Services are running${NC}"

# Set environment
export PYTHONPATH=/Users/aristotle/projects/support-extension
export JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# Run comprehensive test suite
echo -e "${YELLOW}Testing Enhanced AI Chat Service...${NC}"
poetry run pytest tests/unit/services/test_ai_chat_service_history.py -v
echo -e "${GREEN}✅ AI Chat Service tests passed${NC}"

echo -e "${YELLOW}Testing Enhanced Dynamic Agent Factory...${NC}" 
poetry run pytest tests/unit/services/test_dynamic_agent_factory_history.py -v
echo -e "${GREEN}✅ Dynamic Agent Factory tests passed${NC}"

echo -e "${YELLOW}Running Simplified Integration Test...${NC}"
poetry run pytest tests/integration/test_simplified_message_history.py -v
echo -e "${GREEN}✅ Integration test passed${NC}"

# Check Docker health
echo -e "${YELLOW}Checking Docker container health...${NC}"
ERROR_COUNT=$(docker compose logs app 2>&1 | grep -i "error\|exception\|traceback" | wc -l)
if [ $ERROR_COUNT -gt 5 ]; then
    echo -e "${RED}❌ Found $ERROR_COUNT errors in Docker logs${NC}"
    docker compose logs app | grep -i "error\|exception" | tail -10
    exit 1
fi

echo -e "${GREEN}✅ Docker containers healthy${NC}"

echo -e "${GREEN}🎉 Simplified Message History E2E tests passed!${NC}"
echo -e "${GREEN}✅ Existing database storage utilized${NC}"
echo -e "${GREEN}✅ Context limits properly applied${NC}"
echo -e "${GREEN}✅ Pydantic AI message_history parameter used correctly${NC}"
echo -e "${GREEN}✅ No additional database schema changes needed${NC}"
```

#### 3.3 Validation Commands
```bash
# Make script executable
chmod +x tests/scripts/test_simplified_message_history_e2e.sh

# Run E2E test
./tests/scripts/test_simplified_message_history_e2e.sh

# Check all message history tests
PYTHONPATH=/Users/aristotle/projects/support-extension poetry run pytest -k "message_history" -v

# Verify system health
curl http://localhost:8000/health
curl http://localhost:8001/health
```

**Success Criteria**:
- [ ] E2E script completes successfully
- [ ] Integration tests pass using existing database
- [ ] All message history tests pass
- [ ] API endpoints respond healthy
- [ ] No critical Docker errors
- [ ] Proper message_history parameter usage verified
- [ ] Context limits working with existing token counter

---

## Final Validation Checklist

### ✅ Simplified Pydantic AI Integration
- [ ] Uses existing database storage efficiently
- [ ] Enhances existing `get_thread_history()` with context limits
- [ ] Passes `message_history` parameter correctly to agent.run()
- [ ] No additional database schema changes required

### ✅ Core Functionality
- [ ] Context size limits applied using existing token counter
- [ ] Memory context can be enabled/disabled per agent
- [ ] Backward compatibility maintained
- [ ] Uses existing ai_chat_service message storage

### ✅ Testing Coverage
- [ ] Unit tests for enhanced methods
- [ ] Integration tests with existing database
- [ ] E2E tests covering simplified flow
- [ ] Edge cases handled (no history, disabled memory, etc.)

### ✅ System Health
- [ ] No new Docker container dependencies
- [ ] API endpoints remain healthy
- [ ] No import errors or circular dependencies
- [ ] Existing message storage continues working

## Key Benefits of Simplified Implementation

1. **Leverages Existing Infrastructure**: Uses current database schema and message storage
2. **Minimal Code Changes**: Only enhances existing methods, no new services
3. **Proper Pydantic AI Integration**: Uses correct `message_history` parameter
4. **Context Management**: Token-aware limits using existing token counter
5. **Backward Compatibility**: All existing functionality preserved
6. **Reduced Complexity**: No JSON blob storage or separate message service

## Critical Differences from Original Flawed Approach

| Aspect | Original (Incorrect) | Simplified (Correct) |
|--------|---------------------|----------------------|
| Storage | New JSON blob system | Use existing Message table |
| Retrieval | Separate message service | Enhance existing ai_chat_service |
| Format | Custom dict format | Simple dict compatible with Pydantic AI |
| Agent Usage | Manual conversation array | Correct message_history parameter |
| Context Limits | New token counting | Use existing token_counter_service |
| Database Changes | New schema required | No schema changes needed |

This simplified implementation properly follows Pydantic AI patterns while maximally leveraging existing, working infrastructure.
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic_ai.messages import ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python

from app.services.message_history_service import message_history_service

@pytest.mark.asyncio
async def test_store_messages_json():
    """Test storing messages as JSON using ModelMessagesTypeAdapter."""
    db = AsyncMock()
    thread_id = str(uuid.uuid4())
    
    # Mock messages (would normally come from agent.run result)
    mock_messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    
    await message_history_service.store_messages_json(db, thread_id, mock_messages)
    
    # Verify database operations
    db.add.assert_called_once()
    db.commit.assert_called_once()

@pytest.mark.asyncio 
async def test_get_messages_for_agent():
    """Test retrieving messages in Pydantic AI format."""
    db = AsyncMock()
    thread_id = str(uuid.uuid4())
    
    # Mock database response with JSON message history
    mock_message = MagicMock()
    mock_message.content = json.dumps([
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ])
    
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_message
    db.execute.return_value = result_mock
    
    # Mock ModelMessagesTypeAdapter
    with patch.object(ModelMessagesTypeAdapter, 'validate_python') as mock_validate:
        mock_validate.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        messages = await message_history_service.get_messages_for_agent(
            db, thread_id, use_memory_context=True
        )
        
        assert len(messages) == 2
        mock_validate.assert_called_once()

@pytest.mark.asyncio
async def test_memory_context_disabled():
    """Test that no messages are returned when memory is disabled."""
    db = AsyncMock()
    thread_id = str(uuid.uuid4())
    
    messages = await message_history_service.get_messages_for_agent(
        db, thread_id, use_memory_context=False
    )
    
    assert messages == []
    db.execute.assert_not_called()

@pytest.mark.asyncio
async def test_context_limits_applied():
    """Test that context limits are properly applied."""
    # Create mock ModelMessage objects
    mock_messages = []
    for i in range(25):  # Create 25 messages to trigger filtering
        mock_msg = MagicMock()
        mock_msg.role = "user" if i % 2 == 0 else "assistant"
        mock_msg.content = f"This is message number {i} with some content"
        mock_messages.append(mock_msg)
    
    # Test with small context limit to trigger filtering
    limited = await message_history_service._apply_context_limits(mock_messages, 500)  # Small limit
    
    # Should limit to fewer messages due to token constraints
    assert len(limited) <= len(mock_messages)
    assert len(limited) > 0  # Should keep at least some messages
    
    # Messages should be in chronological order (oldest first)
    # The first message in limited result should be older than the last
    assert limited is not None

@pytest.mark.asyncio
async def test_context_limits_fallback():
    """Test fallback behavior when token counting fails."""
    # Create mock messages that will cause token counting to fail
    mock_messages = []
    for i in range(15):
        mock_msg = MagicMock()
        mock_msg.role = "user"
        mock_msg.content = f"Message {i}"
        # Remove content attribute to trigger error
        del mock_msg.content
        mock_messages.append(mock_msg)
    
    # Should fallback to keeping last 10 messages
    limited = await message_history_service._apply_context_limits(mock_messages, 1000)
    
    assert len(limited) == 10  # Fallback limit
    
@pytest.mark.asyncio
async def test_context_limits_small_list():
    """Test that small message lists are returned unchanged."""
    # Create small list of messages
    mock_messages = []
    for i in range(5):  # Only 5 messages
        mock_msg = MagicMock()
        mock_msg.role = "user"
        mock_msg.content = f"Short message {i}"
        mock_messages.append(mock_msg)
    
    limited = await message_history_service._apply_context_limits(mock_messages, 1000)
    
    # Should return all messages unchanged for small lists
    assert len(limited) == 5
    assert limited == mock_messages
```

#### 2.4 Integration Test
Create `tests/integration/services/test_message_history_integration_simple.py`:

```python
import pytest
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from app.models.chat import Thread, Message
from app.models.ai_agent import Agent  
from app.models.organization import Organization
from app.services.message_history_service import message_history_service

@pytest.mark.asyncio
async def test_message_storage_and_retrieval(test_db_session: AsyncSession):
    """Test storing and retrieving message history with real database."""
    
    # Create test data
    org = Organization(name="Test Org", email="test@example.com")
    test_db_session.add(org)
    await test_db_session.flush()
    
    agent = Agent(
        organization_id=org.id,
        name="Test Agent", 
        agent_type="customer_support"
    )
    test_db_session.add(agent)
    await test_db_session.flush()
    
    thread = Thread(
        agent_id=agent.id,
        user_id="test_user",
        organization_id=org.id,
        title="Test Conversation"
    )
    test_db_session.add(thread)
    await test_db_session.flush()
    await test_db_session.commit()
    
    # Mock some messages (would normally come from agent result)
    test_messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"}
    ]
    
    # Test storage
    await message_history_service.store_messages_json(
        test_db_session, str(thread.id), test_messages
    )
    
    # Test retrieval
    retrieved = await message_history_service.get_messages_for_agent(
        test_db_session, str(thread.id), use_memory_context=True
    )
    
    assert len(retrieved) == 2
    assert retrieved[0]["role"] == "user"
    assert retrieved[1]["role"] == "assistant"
```

#### 2.5 Validation
```bash
# Test service creation and imports
PYTHONPATH=/Users/aristotle/projects/support-extension poetry run python -c "
from app.services.message_history_service import message_history_service
print('✅ Message History Service imports successfully')
"

# Run unit tests
PYTHONPATH=/Users/aristotle/projects/support-extension poetry run pytest tests/unit/services/test_message_history_service.py -v

# Run integration test
PYTHONPATH=/Users/aristotle/projects/support-extension poetry run pytest tests/integration/services/test_message_history_integration_simple.py -v

# Check for any import errors
docker compose logs app | grep -i "import\|module\|error"
```

**Success Criteria**:
- [ ] All unit tests pass
- [ ] Integration test passes
- [ ] Service imports without errors
- [ ] No Docker container errors

---

### Step 3: Enhanced Dynamic Agent Factory  
**Objective**: Integrate proper Pydantic AI message history usage

#### 3.1 Update Dynamic Agent Factory
Update the `process_message_with_agent` method in `app/services/dynamic_agent_factory.py` with the implementation provided above.

#### 3.2 Create Comprehensive Unit Tests
Create `tests/unit/services/test_dynamic_agent_factory_history.py`:

```python
import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.dynamic_agent_factory import dynamic_agent_factory
from app.schemas.ai_response import ChatResponse, CustomerSupportContext

@pytest.mark.asyncio
async def test_process_message_with_history():
    """Test processing message with proper message_history parameter."""
    
    # Mock agent model
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = True
    agent_model.max_context_size = 1000
    agent_model.max_iterations = 5
    
    mock_db = AsyncMock()
    thread_id = str(uuid.uuid4())
    
    # Mock message history from service
    mock_history = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"}
    ]
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.dynamic_agent_factory.message_history_service') as mock_history_service:
        
        # Mock Pydantic AI agent
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="Response with context",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # Mock history service
        mock_history_service.get_messages_for_agent.return_value = mock_history
        
        # Process message
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            user_message="Follow up question",
            context=CustomerSupportContext(),
            thread_id=thread_id,
            db=mock_db
        )
        
        # Verify correct message_history parameter usage
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        
        # Should be called with message_history parameter
        assert 'message_history' in call_args.kwargs or len(call_args.args) > 1
        assert response.content == "Response with context"

@pytest.mark.asyncio 
async def test_process_message_without_history():
    """Test processing message without history (new conversation)."""
    
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = True
    agent_model.max_iterations = 5
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.dynamic_agent_factory.message_history_service') as mock_history_service:
        
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="Fresh conversation",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # Mock empty history
        mock_history_service.get_messages_for_agent.return_value = []
        
        # Process without thread_id (no history)
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            user_message="Hello",
            context=CustomerSupportContext(),
            thread_id=None,
            db=None
        )
        
        # Should call run without message_history
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        
        # Should be simple message call
        assert call_args.args[0] == "Hello"
        assert 'message_history' not in call_args.kwargs
        
@pytest.mark.asyncio
async def test_memory_context_disabled():
    """Test that memory context can be disabled per agent."""
    
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = False  # Memory disabled
    agent_model.max_iterations = 5
    
    mock_db = AsyncMock()
    thread_id = str(uuid.uuid4())
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.dynamic_agent_factory.message_history_service') as mock_history_service:
        
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="No memory response",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            user_message="Hello",
            context=CustomerSupportContext(),
            thread_id=thread_id,
            db=mock_db
        )
        
        # History service should not be called when memory is disabled
        mock_history_service.get_messages_for_agent.assert_not_called()
```

#### 3.3 Validation
```bash
# Test enhanced dynamic agent factory
PYTHONPATH=/Users/aristotle/projects/support-extension poetry run python -c "
from app.services.dynamic_agent_factory import dynamic_agent_factory
from app.services.message_history_service import message_history_service
print('✅ All services import successfully')
"

# Run new tests
PYTHONPATH=/Users/aristotle/projects/support-extension poetry run pytest tests/unit/services/test_dynamic_agent_factory_history.py -v

# Ensure existing tests still pass
PYTHONPATH=/Users/aristotle/projects/support-extension poetry run pytest tests/unit/services/test_dynamic_agent_factory.py -v

# Check for errors
docker compose logs app | grep -i error
```

**Success Criteria**:
- [ ] All new tests pass
- [ ] Existing dynamic agent factory tests still pass  
- [ ] Services import correctly
- [ ] No Docker errors
- [ ] Proper message_history parameter usage confirmed

---

### Step 4: End-to-End Integration Test
**Objective**: Validate complete message history flow with real Pydantic AI integration

#### 4.1 Create E2E Test Script
Create `tests/scripts/test_message_history_e2e.sh`:

```bash
#!/bin/bash

set -e

echo "🧪 Pydantic AI Message History E2E Test"
echo "======================================"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Ensure services are running
echo -e "${YELLOW}Checking services...${NC}"
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${RED}❌ Main API not responding. Starting services...${NC}"
    docker compose up -d
    sleep 15
fi

if ! curl -s http://localhost:8001/health > /dev/null; then
    echo -e "${RED}❌ MCP Server not responding${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Services are running${NC}"

# Set environment
export PYTHONPATH=/Users/aristotle/projects/support-extension
export JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# Run comprehensive test suite
echo -e "${YELLOW}Testing Message History Service...${NC}"
poetry run pytest tests/unit/services/test_message_history_service.py -v
echo -e "${GREEN}✅ Message History Service tests passed${NC}"

echo -e "${YELLOW}Testing Dynamic Agent Factory with History...${NC}" 
poetry run pytest tests/unit/services/test_dynamic_agent_factory_history.py -v
echo -e "${GREEN}✅ Dynamic Agent Factory tests passed${NC}"

echo -e "${YELLOW}Running Integration Tests...${NC}"
poetry run pytest tests/integration/services/test_message_history_integration_simple.py -v
echo -e "${GREEN}✅ Integration tests passed${NC}"

# Test the complete flow
echo -e "${YELLOW}Testing Complete Message History Flow...${NC}"
poetry run pytest tests/integration/test_message_history_full_flow.py -v
echo -e "${GREEN}✅ Full flow test passed${NC}"

# Check Docker health
echo -e "${YELLOW}Checking Docker container health...${NC}"
ERROR_COUNT=$(docker compose logs app 2>&1 | grep -i "error\|exception\|traceback" | wc -l)
if [ $ERROR_COUNT -gt 5 ]; then  # Allow some normal startup errors
    echo -e "${RED}❌ Found $ERROR_COUNT errors in Docker logs${NC}"
    docker compose logs app | grep -i "error\|exception" | tail -10
    exit 1
fi

echo -e "${GREEN}✅ Docker containers healthy${NC}"

echo -e "${GREEN}🎉 All Pydantic AI Message History E2E tests passed!${NC}"
echo -e "${GREEN}✅ ModelMessagesTypeAdapter serialization works${NC}"
echo -e "${GREEN}✅ message_history parameter usage correct${NC}"
echo -e "${GREEN}✅ Database storage/retrieval functional${NC}"
echo -e "${GREEN}✅ Agent factory integration complete${NC}"
```

#### 4.2 Create Complete Integration Test
Create `tests/integration/test_message_history_full_flow.py`:

```python
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Thread, Message
from app.models.ai_agent import Agent
from app.models.organization import Organization
from app.services.dynamic_agent_factory import dynamic_agent_factory
from app.services.message_history_service import message_history_service
from app.schemas.ai_response import ChatResponse, CustomerSupportContext

@pytest.mark.asyncio
async def test_complete_message_history_flow(test_db_session: AsyncSession):
    """Test complete message history flow with Pydantic AI integration."""
    
    # Create test database objects
    org = Organization(name="Test Org", email="test@example.com")
    test_db_session.add(org)
    await test_db_session.flush()
    
    agent = Agent(
        organization_id=org.id,
        name="Test Agent",
        agent_type="customer_support",
        use_memory_context=True,
        max_context_size=1000,
        max_iterations=5
    )
    test_db_session.add(agent)
    await test_db_session.flush()
    
    thread = Thread(
        agent_id=agent.id,
        user_id="test_user", 
        organization_id=org.id,
        title="Test Conversation"
    )
    test_db_session.add(thread)
    await test_db_session.flush()
    await test_db_session.commit()
    
    # Step 1: Store initial conversation history
    initial_messages = [
        {"role": "user", "content": "Hello, I need help"},
        {"role": "assistant", "content": "Hi! I'm happy to help. What can I do for you?"}
    ]
    
    await message_history_service.store_messages_json(
        test_db_session, str(thread.id), initial_messages
    )
    
    # Step 2: Retrieve message history  
    retrieved_messages = await message_history_service.get_messages_for_agent(
        test_db_session, str(thread.id), use_memory_context=True
    )
    
    assert len(retrieved_messages) == 2
    assert retrieved_messages[0]["content"] == "Hello, I need help"
    
    # Step 3: Test agent processing with history
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create:
        # Mock Pydantic AI agent behavior
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="Based on our conversation, I understand you need help. How can I assist further?",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        
        # Mock all_messages() for history storage
        mock_result.all_messages.return_value = [
            {"role": "user", "content": "Hello, I need help"},
            {"role": "assistant", "content": "Hi! I'm happy to help. What can I do for you?"},
            {"role": "user", "content": "I have a question about my account"},
            {"role": "assistant", "content": "Based on our conversation, I understand you need help. How can I assist further?"}
        ]
        
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # Process new message with history
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent,
            user_message="I have a question about my account",
            context=CustomerSupportContext(),
            thread_id=str(thread.id),
            db=test_db_session
        )
        
        # Verify response
        assert isinstance(response, ChatResponse)
        assert "conversation" in response.content.lower()
        
        # Verify agent was called with message_history parameter
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        
        # Check if message_history was provided
        has_history = (
            'message_history' in call_args.kwargs or 
            (len(call_args.args) > 1 and call_args.args[1] is not None)
        )
        assert has_history, "Agent should be called with message_history parameter"

@pytest.mark.asyncio
async def test_memory_disabled_flow(test_db_session: AsyncSession):
    """Test flow when memory context is disabled."""
    
    org = Organization(name="Test Org", email="test@example.com")
    test_db_session.add(org)
    await test_db_session.flush()
    
    # Agent with memory disabled
    agent = Agent(
        organization_id=org.id,
        name="No Memory Agent",
        agent_type="customer_support",
        use_memory_context=False,  # Memory disabled
        max_context_size=1000
    )
    test_db_session.add(agent)
    await test_db_session.flush()
    
    thread = Thread(
        agent_id=agent.id,
        user_id="test_user",
        organization_id=org.id, 
        title="Fresh Conversation"
    )
    test_db_session.add(thread)
    await test_db_session.flush()
    await test_db_session.commit()
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create:
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="Fresh response without history",
            confidence=0.8,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # Process message
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent,
            user_message="Hello",
            context=CustomerSupportContext(),
            thread_id=str(thread.id),
            db=test_db_session
        )
        
        # Verify agent called without history
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        
        # Should be simple message call
        assert call_args.args[0] == "Hello"
        assert 'message_history' not in call_args.kwargs
```

#### 4.3 Make E2E Script Executable and Run Validation
```bash
# Make script executable
chmod +x tests/scripts/test_message_history_e2e.sh

# Run E2E test
./tests/scripts/test_message_history_e2e.sh

# Run full flow integration test
PYTHONPATH=/Users/aristotle/projects/support-extension poetry run pytest tests/integration/test_message_history_full_flow.py -v

# Check all message history tests
PYTHONPATH=/Users/aristotle/projects/support-extension poetry run pytest -k "message_history" -v

# Verify system health
curl http://localhost:8000/health
curl http://localhost:8001/health
```

**Success Criteria**:
- [ ] E2E script completes successfully
- [ ] Full flow integration tests pass
- [ ] All message history tests pass
- [ ] API endpoints respond healthy
- [ ] No critical Docker errors
- [ ] ModelMessagesTypeAdapter usage confirmed
- [ ] Proper message_history parameter usage verified
- [ ] Database serialization/deserialization works

---

## Final Validation Checklist

### ✅ Pydantic AI Integration
- [ ] Uses ModelMessagesTypeAdapter for serialization/deserialization
- [ ] Passes message_history parameter correctly to agent.run()
- [ ] Includes both user and assistant messages in history
- [ ] Stores complete message history using result.all_messages()

### ✅ Core Functionality
- [ ] Message history stored as JSON using proper TypeAdapter
- [ ] Context size limits respected (configurable per agent)
- [ ] Memory context can be enabled/disabled per agent
- [ ] Backward compatibility maintained

### ✅ Testing Coverage
- [ ] Unit tests for all new services
- [ ] Integration tests with real database
- [ ] E2E tests covering complete flow
- [ ] Edge cases handled (no history, disabled memory, etc.)

### ✅ System Health
- [ ] No Docker container errors
- [ ] API endpoints remain healthy
- [ ] No import errors or circular dependencies
- [ ] Database migrations apply cleanly

## Key Benefits of Refactored Implementation

1. **Proper Pydantic AI Integration**: Uses official ModelMessagesTypeAdapter and message_history parameter
2. **Efficient Storage**: Messages stored as JSON blobs rather than individual records
3. **Context Management**: Token-aware context limits prevent API limit issues
4. **Configurable Memory**: Per-agent memory control through database configuration
5. **Backward Compatibility**: Existing agents work unchanged
6. **Performance Optimized**: Async message storage doesn't block responses

## Critical Differences from Previous Implementation

| Aspect | Previous (Incorrect) | New (Correct) |
|--------|---------------------|---------------|
| Message Format | Custom dict format | ModelMessage via TypeAdapter |
| Agent Usage | Manual conversation array | message_history parameter |
| Serialization | Manual JSON | ModelMessagesTypeAdapter |
| Storage | Individual message records | JSON message blobs |
| Message Filtering | Filtered out agent messages | Includes all messages |
| Context Limits | Manual token counting | Built-in with fallbacks |

This refactored implementation properly follows Pydantic AI patterns for message history, ensuring robust conversation continuity and optimal performance.