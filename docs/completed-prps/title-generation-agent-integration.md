# Title Generation Agent Integration PRP

**Name:** Title Generation Agent Integration - Thread Service Refactor  
**Description:** Integrate title generation functionality from `app/agents/title_generation_agent.py` into the Thread Service using the existing agent infrastructure, creating a single utility agent for system-wide title generation.

---

## Purpose

Refactor the standalone title generation agent into the integrated agent infrastructure to:
- Leverage the multi-agent system for title generation as a utility service
- Create a single system-wide title generation agent using the Agent model
- Integrate title generation seamlessly into Thread Service operations
- Maintain existing title generation quality while improving architecture consistency
- Simplify title generation by using a single, optimized agent for all organizations

## Why

**Current Problems:**
- **Architectural Inconsistency**: Title generation uses standalone agent pattern while main system uses integrated Agent model
- **Maintenance Overhead**: Separate agent implementation requires independent maintenance and updates
- **Configuration Duplication**: Title generation agent has its own configuration system separate from main agent infrastructure
- **Resource Inefficiency**: Standalone agent creates unnecessary complexity for a utility function

**Business Benefits:**
- **Unified Architecture**: All AI functionality uses the same agent infrastructure and patterns
- **Operational Efficiency**: Single utility agent serves all organizations with consistent title generation
- **Cost Optimization**: One optimized agent + limited message processing reduces LLM token costs
- **Simplified Management**: No need to manage title generation agents per organization

**Technical Benefits:**
- **Code Consolidation**: Reduce duplicate agent infrastructure and configuration code
- **Performance Optimization**: Single, well-tuned agent optimized for title generation workload
- **Token Efficiency**: Processing only latest 6 messages reduces LLM costs and latency
- **Monitoring**: Unified agent monitoring, logging, and performance tracking
- **Scalability**: Centralized title generation can be optimized and scaled independently

## What

Transform title generation from standalone agent to single utility agent:

### Core Changes

#### 1. Create System Title Generation Agent
- Add `title_generation` as a supported `agent_type` in Agent model
- Create single system-wide title generation agent (not organization-specific)
- Optimize agent configuration for fast, high-quality title generation

#### 2. Refactor Thread Service Integration
- Remove direct dependency on `title_generation_agent.py`
- Use system title generation agent when `POST /api/v1/chat/{agent_id}/threads/{thread_id}/generate_title` is called
- Maintain existing API signature for `generate_title_suggestion()`

#### 3. On-Demand Title Generation
- Load latest 6 messages from specified thread_id (to optimize LLM token usage)
- Use system title generation agent to analyze messages and generate title
- Return title suggestion without modifying thread

#### 4. Migration Strategy
- Create single system title generation agent during migration
- Preserve existing title generation functionality during transition
- Update Thread Service to use new agent-based approach

### Detailed Implementation

#### Agent Model Integration

```python
# Agent types supported
AGENT_TYPES = [
    "customer_support",
    "categorization", 
    "title_generation",  # NEW - System utility agent
    "file_analysis"
]

# System title generation agent configuration (single instance)
SYSTEM_TITLE_AGENT_CONFIG = {
    "name": "System Title Generator",
    "role": "Title Generation Utility",
    "prompt": """You are an expert at creating concise, descriptive titles for customer support conversations.
    
Analyze the conversation and generate a clear, specific title that captures the essence of the discussion.

TITLE GENERATION RULES:
1. Maximum 8 words, ideally 4-6 words
2. Use specific, descriptive terms
3. Avoid generic words: "Help", "Support", "Question", "Issue"
4. Include technical terms when relevant
5. Capture the primary topic/problem
6. Use title case formatting

Focus on the main issue or request being discussed.""",
    "communication_style": "professional",
    "response_length": "brief",
    "use_streaming": False,
    "timeout_seconds": 15,
    "tools": [],
    "organization_id": None  # System agent, not org-specific
}

# Message Limit Configuration
MAX_MESSAGES_FOR_TITLE = 6  # Process only latest 6 messages to optimize token usage
```

#### Thread Service Enhancement

```python
# In thread_service.py
async def generate_title_suggestion(
    self,
    db: AsyncSession,
    agent_id: UUID,
    thread_id: UUID,
    user_id: str
) -> Optional[dict]:
    """
    Generate title suggestion using system title generation agent
    """
    # Get the thread with proper validation
    thread = await self.get_thread(db, agent_id, thread_id, user_id)
    if not thread:
        return None
    
    # Get system title generation agent (single instance)
    title_agent = await agent_service.get_system_title_agent(db)
    if not title_agent:
        logger.error("System title generation agent not available")
        return None
    
    # Get latest 6 messages for title generation (optimize token usage)
    messages = await self.get_thread_messages(db, agent_id, thread_id, user_id, offset=0, limit=6)
    if not messages:
        logger.warning("No messages found for title generation")
        return None
    
    # Use title agent to generate title
    title_runner = TitleGenerationAgentRunner(title_agent)
    result = await title_runner.generate_title(messages, thread.title)
    
    return {
        "id": thread_id,
        "title": result.title,
        "current_title": thread.title,
        "confidence": result.confidence,
        "generated_at": datetime.now(timezone.utc)
    }
```

#### Agent Service Enhancement

```python
# In agent_service.py
async def get_system_title_agent(
    self,
    db: AsyncSession
) -> Optional[Agent]:
    """
    Get the system title generation agent (single instance)
    """
    # Try to find existing system title agent
    query = select(Agent).where(
        Agent.agent_type == "title_generation",
        Agent.is_active.is_(True),
        Agent.organization_id.is_(None)  # System agent has no organization
    )
    result = await db.execute(query)
    agent = result.scalar_one_or_none()
    
    if not agent:
        logger.warning("System title generation agent not found. Run migration to create it.")
    
    return agent

async def create_system_title_agent(
    self,
    db: AsyncSession
) -> Agent:
    """
    Create the system title generation agent (called during migration)
    """
    agent = Agent(
        agent_type="title_generation",
        organization_id=None,  # System agent
        **SYSTEM_TITLE_AGENT_CONFIG
    )
    
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    
    logger.info("Created system title generation agent")
    return agent
```

#### Title Generation Agent Runner

```python
# New: app/services/title_generation_runner.py
class TitleGenerationAgentRunner:
    """
    Runner for title generation using Agent infrastructure
    """
    
    def __init__(self, agent: Agent):
        self.agent = agent
        self.pydantic_agent = None
    
    async def ensure_initialized(self):
        """Initialize Pydantic AI agent from Agent configuration"""
        if self.pydantic_agent:
            return
            
        config = self.agent.get_configuration()
        
        # Use agent's configured model or fallback
        model = f"openai:{config.get('model_name', 'gpt-3.5-turbo')}"
        
        self.pydantic_agent = PydanticAgent(
            model=model,
            system_prompt=config.get('prompt', DEFAULT_TITLE_PROMPT),
            output_type=TitleGenerationResult,
            retries=2
        )
    
    async def generate_title(
        self,
        messages: List[Message], 
        current_title: Optional[str] = None
    ) -> TitleGenerationResult:
        """Generate title using agent configuration and latest messages only"""
        await self.ensure_initialized()
        
        # Use only the latest 6 messages (already limited by caller)
        message_contents = []
        for msg in messages[-6:]:  # Ensure we only use latest 6 even if more passed
            if msg.content and len(msg.content.strip()) > 0:
                role_prefix = "User: " if msg.role == "user" else "Assistant: "
                message_contents.append(f"{role_prefix}{msg.content.strip()}")
        
        if not message_contents:
            return TitleGenerationResult(
                title="Empty Conversation",
                confidence=0.5
            )
        
        # Create optimized prompt for latest messages
        conversation_text = "\n".join(message_contents)
        prompt = f"""
Analyze this recent conversation and generate a concise, descriptive title.

Current title: "{current_title or 'New Conversation'}"
Recent messages ({len(message_contents)} messages):

{conversation_text}

Generate a title that captures the main topic or issue being discussed.
"""
        
        result = await self.pydantic_agent.run(prompt)
        return result
```

### API Changes

No breaking changes to existing APIs:
- Thread Service `generate_title_suggestion()` maintains same signature
- `POST /api/v1/chat/{agent_id}/threads/{thread_id}/generate_title` endpoint works identically
- Backward compatibility preserved

### Database Changes

Minimal database impact:
- Single system title generation agent created during migration
- Existing thread data remains unchanged
- Agent table used for system title generation configuration
- No organization-specific agents needed

## Implementation Plan

### Phase 1: Infrastructure Setup (Week 1)
- [ ] Add `title_generation` agent type support to Agent model
- [ ] Create `TitleGenerationAgentRunner` class
- [ ] Add `get_system_title_agent()` and `create_system_title_agent()` to agent service
- [ ] Create system title generation agent configuration

### Phase 2: Thread Service Integration (Week 2)
- [ ] Refactor `generate_title_suggestion()` to use system title generation agent
- [ ] Create migration to create single system title generation agent
- [ ] Update Thread Service to use new agent-based title generation
- [ ] Add fallback mechanism to current title generation system

### Phase 3: Testing and Validation (Week 3)
- [ ] Comprehensive testing of agent-based title generation
- [ ] Performance comparison with current system
- [ ] Load testing of single system agent handling multiple requests
- [ ] End-to-end testing of title generation endpoints

### Phase 4: Cleanup and Migration (Week 4)
- [ ] Remove dependency on standalone `title_generation_agent.py`
- [ ] Clean up unused title generation infrastructure
- [ ] Update documentation and API specs
- [ ] Monitor production performance and quality

## Success Criteria

- [ ] **Functional Parity**: Title generation quality matches or exceeds current system
- [ ] **Performance**: Title generation response times ≤ current system performance (improved by 6-message limit)
- [ ] **Cost Efficiency**: Token usage reduced by processing only latest 6 messages per request
- [ ] **API Compatibility**: `POST /api/v1/chat/{agent_id}/threads/{thread_id}/generate_title` endpoint works unchanged
- [ ] **Agent Integration**: System title generation agent visible in agent management interfaces
- [ ] **Scalability**: Single agent handles concurrent requests from all organizations efficiently
- [ ] **Configuration Management**: System title agent can be managed through standard agent CRUD operations
- [ ] **Monitoring**: Title generation activity tracked through unified agent monitoring

## Risk Mitigation

**Quality Degradation**:
- Maintain fallback to current title generation system during transition
- Side-by-side testing and comparison during migration
- Gradual rollout with performance monitoring

**Single Point of Failure**:
- Robust error handling and fallback mechanisms
- System agent health monitoring and automatic recovery
- Consider agent redundancy for high availability if needed

**Performance Bottleneck**:
- Load testing to ensure single agent can handle concurrent requests
- Optimize agent initialization and caching
- Monitor response times and scale if necessary

## Files Affected

**New Files:**
- `app/services/title_generation_runner.py` - Agent runner for title generation
- `app/migrations/create_system_title_agent.py` - Migration to create system title agent

**Modified Files:**
- `app/services/thread_service.py` - Use system agent for title generation
- `app/services/agent_service.py` - Add system title agent management
- `app/models/ai_agent.py` - Support title_generation agent type
- `app/config/ai_config.yaml` - Add system title generation agent configuration

**Removed Files (Phase 4):**
- `app/agents/title_generation_agent.py` - Standalone title agent (deprecated)

## Summary

This approach provides a clean integration path that:
- Leverages existing agent infrastructure for consistency
- Uses a single, optimized utility agent for all title generation requests
- **Optimizes token usage by processing only the latest 6 messages per thread**
- Maintains backward compatibility with existing APIs
- Eliminates the complexity of per-organization title agents
- Provides unified monitoring and management of title generation functionality

### Message Limit Rationale

The 6-message limit provides an optimal balance:
- **Cost Efficiency**: Reduces LLM token usage significantly for long conversations
- **Quality**: Latest messages typically contain the most relevant context for title generation
- **Performance**: Faster processing with smaller payloads
- **Consistency**: Predictable token usage across all requests

For most conversations, the latest 6 messages (3 user + 3 assistant messages) contain sufficient context to generate accurate, descriptive titles while keeping costs minimal.

The system title generation agent will be automatically created during migration and can be managed through standard agent CRUD operations, while serving title generation requests efficiently across all organizations.