# PRP: MCP Client Agent Refactoring

## Overview
Refactor the MCP (Model Context Protocol) client architecture to work with organization-created agents instead of the hardcoded `customer_support_agent.py`. Each agent with `mcp_enabled=True` will have the ability to connect to the MCP server and call associated tools.

## Current State Analysis
- Hardcoded `customer_support_agent.py` in `app/agents/`
- MCP client in `mcp_client/client.py` 
- Agent model has `mcp_enabled` field at line 270 in `app/models/ai_agent.py`
- Organizations can create custom agents
- Tests reference customer_support_agent directly

## Goals
1. Remove dependency on hardcoded `customer_support_agent.py`
2. Enable MCP functionality for any agent with `mcp_enabled=True`
3. Create default customer support agent during organization setup. Using the prompt coming from the ai_config.yaml file: 

Here is the request body we use to create the agent: 

{
    "name": "Customer Support Specialist",
    "agent_type": "customer_support",
    "avatar_url": "https://example.com/support-avatar.png",
    "role": "Specialized customer support agent for technical inquiries and issue resolution",
    "prompt": "You are an AI Customer Support Assistant for a comprehensive support ticket management system. You help users with:\n\n1. **Issue Resolution**: Understand problems and provide step-by-step solutions\n2. **Ticket Management**: Create, update, search, and manage support tickets with full lifecycle support\n3. **Integration Discovery**: Find and work with third-party systems (Jira, ServiceNow, Salesforce, etc.)\n4. **System Monitoring**: Check system health and integration status\n5. **Analytics & Reporting**: Provide ticket statistics and insights\n6. **Escalation Management**: Identify when issues need human expert attention\n\nGuidelines:\n- Be professional, empathetic, and solution-focused\n- Ask clarifying questions to understand the full context\n- Provide clear, actionable guidance with step-by-step instructions\n- Always explain what tools you're using and why\n- Escalate complex technical issues or when users explicitly request human assistance\n- Maintain conversation context and reference previous interactions appropriately\n\n**Available MCP Tools (13 tools organized by category):**\n\n**🎫 TICKET MANAGEMENT TOOLS (10 tools):**\nComplete ticket lifecycle management with full API schema support.\n\nTicket Creation:\n  * create_ticket: Create support tickets with full schema (title, description, category, priority, urgency, department, assigned_to_id, integration, create_externally, custom_fields, file_ids)\n  * create_ticket_with_ai: AI-powered ticket creation with automatic categorization\n\nTicket Retrieval & Management:\n  * get_ticket: Retrieve specific ticket details by ID\n  * update_ticket: Update existing ticket fields (title, description, status, priority, category)\n  * delete_ticket: Delete specific tickets by ID\n  * search_tickets: Search and filter tickets with pagination (query, status, category, priority, page, page_size)\n  * list_tickets: List tickets with optional filtering and pagination\n\nTicket Operations:\n  * update_ticket_status: Update ticket status (open, in_progress, resolved, closed)\n  * assign_ticket: Assign tickets to specific users or teams\n  * get_ticket_stats: Retrieve comprehensive ticket statistics and analytics\n\n**🔗 INTEGRATION TOOLS (2 tools):**\nIntegration discovery and management for external system routing.\n\n  * list_integrations: List available integrations (jira, servicenow, salesforce, zendesk, github, slack, teams, zoom, hubspot, freshdesk, asana, trello, webhook, email, sms)\n  * get_active_integrations: Get active integrations with health status and capabilities\n\n**🔍 SYSTEM TOOLS (1 tool):**\nSystem health monitoring and status reporting.\n\n  * get_system_health: Check backend system health and status\n\n**Tool Usage Strategy:**\n\nFor Issue Reporting:\n- Use create_ticket_with_ai for new issues (leverages AI categorization)\n- Use create_ticket for specific routing needs or custom field requirements\n- Use get_active_integrations to check available external systems before routing\n\nFor Issue Research:\n- Use search_tickets to find related or existing tickets\n- Use list_tickets with filters for broader exploration\n- Use get_ticket for detailed ticket information\n\nFor Issue Management:\n- Use update_ticket_status to change ticket status as issues progress\n- Use assign_ticket to route tickets to appropriate teams\n- Use update_ticket for general ticket field updates\n\nFor Analytics & Monitoring:\n- Use get_ticket_stats for comprehensive analytics and reporting\n- Use get_system_health to check backend system status\n- Use list_integrations to understand available integration options\n\n**Response Format:**\n- Provide clear, conversational responses\n- Use bullet points for multi-step instructions\n- Include relevant ticket IDs or integration names when available\n- Be concise but thorough in explanations\n- Always mention which tools you're using and the results\n\n**Example Tool Usage:**\n- \"What integrations are active?\" → Use get_active_integrations\n- \"Create a ticket for login issues\" → Use create_ticket_with_ai\n- \"Show recent high priority tickets\" → Use search_tickets with priority filter\n- \"Get ticket T-12345 details\" → Use get_ticket\n- \"Update ticket status to resolved\" → Use update_ticket_status\n\nRemember: Your goal is to resolve user issues efficiently while ensuring they feel heard and supported. Use the comprehensive tool set to provide thorough assistance with ticket management, integration routing, and system monitoring.",
    "initial_context": "Welcome! I'm here to help you resolve any issues you may be experiencing. Please describe your problem in detail.",
    "initial_ai_msg": "Hello! I'm your customer support specialist. How can I help you today?",
    "tone": "helpful",
    "communication_style": "professional",
    "use_streaming": true,
    "response_length": "detailed",
    "memory_retention": 10,
    "show_suggestions_after_each_message": true,
    "max_context_size": 150000,
    "use_memory_context": true,
    "max_iterations": 8,
    "timeout_seconds": 120,
    "tools_enabled": ["create_ticket", "search_tickets", "get_ticket", "update_ticket", "get_system_health"]
}

As an example. 

4. Maintain all existing functionality through the new Agent class
5. Ensure all tests pass with new architecture
6. Verify end-to-end MCP functionality
7. Verify all test suite tests pass
8. Verify no errors in docker logs after completion

## Step-by-Step Implementation Plan

### Phase 1: Analysis and Setup
**Step 1.1: Analyze Current MCP Integration**
- [ ] Review `mcp_client/client.py` implementation
- [ ] Identify all references to `customer_support_agent.py` in codebase
- [ ] Map MCP tool connections and usage patterns
- [ ] Document current agent-MCP interaction flow

**Step 1.2: Review Agent Model Architecture**
- [ ] Examine `app/models/ai_agent.py` and `mcp_enabled` field
- [ ] Review agent creation and management services
- [ ] Understand organization-agent relationships
- [ ] Verify agent schema supports MCP configuration

### Phase 2: MCP Client Refactoring
**Step 2.1: Refactor MCP Client for Dynamic Agents**
- [ ] Modify `mcp_client/client.py` to accept agent configuration
- [ ] Remove hardcoded customer support agent references
- [ ] Implement agent-based MCP connection logic
- [ ] Add MCP capability checking (`mcp_enabled` validation)

**Step 2.2: Update Agent Service Layer**
- [ ] Modify `app/services/ai_agent_service.py` to handle MCP-enabled agents
- [ ] Add MCP initialization for agents with `mcp_enabled=True`
- [ ] Implement MCP tool discovery and registration per agent
- [ ] Update agent execution flow to include MCP tool calls

### Phase 3: Remove Customer Support Agent Dependencies
**Step 3.1: Remove customer_support_agent.py**
- [ ] Delete `app/agents/customer_support_agent.py`
- [ ] Remove imports and references in all service files
- [ ] Update any hardcoded agent instantiation
- [ ] Clean up configuration references

**Step 3.2: Update Organization Setup**
- [ ] Modify organization creation to auto-create customer support agent
- [ ] Ensure default agent has `mcp_enabled=True`
- [ ] Configure default agent with appropriate MCP tools
- [ ] Update organization setup tests

### Phase 4: Test Infrastructure Updates
**Step 4.1: Update Unit Tests**
- [ ] Fix `tests/test_ai_agents.py` to use new Agent class
- [ ] Update `tests/test_ai_agents_simple.py` references
- [ ] Modify any tests importing `customer_support_agent`
- [ ] Update mocking and fixture creation

**Step 4.2: Update Integration Tests**
- [ ] Fix `tests/test_integration_comprehensive.py`
- [ ] Update `tests/test_mcp_server.py` for dynamic agent testing
- [ ] Modify API endpoint tests using agents
- [ ] Update WebSocket protocol tests if needed

**Step 4.3: Update API Tests**
- [ ] Fix `tests/test_api_endpoints.py` agent references
- [ ] Update chat and conversation tests
- [ ] Modify agent endpoint tests
- [ ] Update authentication tests if affected

### Phase 5: Validation and Testing
**Step 5.1: Run Complete Test Suite**
- [ ] Execute `poetry run pytest` and ensure all tests pass
- [ ] Fix any failing tests related to agent changes
- [ ] Verify test coverage remains adequate
- [ ] Run Docker-based tests: `docker compose exec app poetry run pytest`

**Step 5.2: Docker Services Validation**
- [ ] Start all services: `docker compose up -d`
- [ ] Check service health endpoints
- [ ] Inspect Docker logs for errors: `docker logs <container-name>`
- [ ] Verify MCP server connectivity and tool registration

**Step 5.3: End-to-End MCP Functionality Testing**
**Acceptance Criteria:**
1. **Customer Support Agent Creation**
   - [ ] Verify customer support agent is auto-created during org setup
   - [ ] Confirm agent has `mcp_enabled=True`
   - [ ] Validate agent is properly configured with MCP tools

2. **Thread Creation and Messaging**
   - [ ] Create a new thread with the customer support agent
   - [ ] Send a help message requiring MCP tool usage
   - [ ] Verify thread creation and message handling

3. **MCP Tool Access**
   - [ ] Confirm agent can connect to MCP server
   - [ ] Verify agent calls appropriate tools (e.g., "get all tickets", "check system health")
   - [ ] Validate tool discovery and registration

4. **Tool Call Recording and Response**
   - [ ] Verify tool calls are recorded in message history
   - [ ] Confirm MCP server processes tool calls correctly
   - [ ] Validate agent receives tool responses
   - [ ] Ensure agent provides meaningful response using tool data

### Phase 6: Documentation and Cleanup
**Step 6.1: Update Documentation**
- [ ] Update README.md if affected
- [ ] Modify API documentation for agent endpoints
- [ ] Update architecture documentation
- [ ] Document new MCP-agent integration pattern

**Step 6.2: Final Validation**
- [ ] Run full test suite one final time
- [ ] Perform manual testing of key workflows
- [ ] Verify Docker deployment works correctly
- [ ] Confirm no regression in existing functionality

## Success Criteria
- [ ] All tests pass (`poetry run pytest`)
- [ ] Docker services start without errors
- [ ] Customer support agent auto-creation works
- [ ] MCP tools are accessible by enabled agents
- [ ] End-to-end agent-MCP interaction functions correctly
- [ ] No references to `customer_support_agent.py` remain in codebase

## Risk Mitigation
- Comprehensive testing at each phase
- Docker logs monitoring for service health
- Rollback plan if critical functionality breaks

## Technical Notes
- Preserve existing MCP server functionality
- Maintain agent isolation and security
- Ensure MCP connections are properly managed
- Handle agent creation/deletion with MCP state cleanup
- Consider performance implications of dynamic MCP connections

## Estimated Timeline
- Phase 1-2: Analysis and core refactoring (Priority 1)
- Phase 3: Dependency removal (Priority 1) 
- Phase 4-5: Testing and validation (Priority 1)
- Phase 6: Documentation and cleanup (Priority 2)