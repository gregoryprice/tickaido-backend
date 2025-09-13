# AI Configuration Service Refactor - Product Requirements and Plan (PRP)

## Overview

This PRP outlines the refactoring of the AI configuration service to simplify the architecture by removing agent-specific configurations, caching, quality control, and environment overrides. The new approach will create agents on-the-fly using the core AI provider and strategy configurations.

## Background

The current AI configuration system has grown complex with extensive agent-specific settings, caching mechanisms, and quality control features that are no longer needed. The system now supports dynamic agent creation, making static agent configurations redundant.

## Goals

1. **Simplify Configuration**: Remove unnecessary complexity from `ai_config.yaml`
2. **Dynamic Agent Creation**: Enable on-the-fly agent instantiation using core AI settings
3. **Maintain Core Functionality**: Preserve essential AI provider and strategy configurations
4. **Reduce Maintenance Overhead**: Eliminate unused configuration sections

## Current State Issues

- **Over-configuration**: Extensive agent-specific settings that duplicate core functionality
- **Unused Features**: Caching, quality control, and environment overrides not actively used
- **Maintenance Burden**: Large configuration files with redundant settings
- **Tool Configuration Complexity**: Tools specified in config rather than at agent creation time

## Proposed Changes

### 1. Configuration File Simplification

**Remove the following sections from `ai_config.yaml`:**
- Agent-specific configuration (agents section)
- Caching configuration (caching section) 
- Quality and safety configuration (quality_control section)
- Development and testing configuration
- Environment-specific overrides (environments section)
- Feature flags (features section)

**Keep the following sections:**
- AI providers configuration
- AI strategy configuration
- Title generation prompt configuration
- Categorization agent base configuration

### 2. Service Layer Updates

**Update `ai_config_service.py`:**
- Modify `load_default_agent_configuration()` to remove unused behavioral settings
- Remove references to auto_escalation_enabled, integration_routing_enabled, response_style, default_priority, default_category
- Simplify agent configuration to use core AI provider and strategy settings
- Remove tool configuration from service (tools will be specified at agent creation time)

### 3. Dynamic Agent Creation

**New Approach:**
- Agents created on-demand using core AI provider configuration
- Tool assignment happens at agent instantiation, not in configuration
- Agent behavior determined by AI strategy settings and runtime parameters
- Simplified configuration focuses on provider connections and model strategies

## Implementation Plan

### Phase 1: Configuration Cleanup
1. Create backup of current `ai_config.yaml`
2. Remove unused configuration sections
3. Retain only essential provider and strategy configurations
4. Keep title_generation_prompt and minimal categorization_agent config

### Phase 2: Service Refactoring  
1. Update `ai_config_service.py` methods
2. Remove unused behavioral setting references
3. Simplify agent configuration loading
4. Remove tool configuration logic

### Phase 3: Testing and Validation
1. Verify existing functionality still works
2. Test dynamic agent creation
3. Validate AI provider connections
4. Ensure categorization and title generation continue working

## Success Criteria

- [ ] Reduced `ai_config.yaml` file size by ~70%
- [ ] Simplified `ai_config_service.py` with removed unused methods
- [ ] All existing AI functionality continues to work
- [ ] Dynamic agent creation works properly
- [ ] No breaking changes to existing APIs

## Risks and Mitigations

**Risk**: Breaking existing agent creation logic
**Mitigation**: Thorough testing of all agent-dependent functionality

**Risk**: Loss of configuration flexibility
**Mitigation**: Core AI provider and strategy settings remain configurable

**Risk**: Runtime errors from missing configuration
**Mitigation**: Careful removal with validation of what's actually used

## Timeline

- **Configuration Cleanup**: 1 hour
- **Service Refactoring**: 2 hours  
- **Testing and Validation**: 1 hour
- **Total Estimated Time**: 4 hours

## Dependencies

- No external dependencies
- Internal dependency on existing agent creation code working with simplified config

## Future Considerations

This refactor sets the foundation for:
- More flexible agent creation patterns
- Runtime agent configuration
- Simplified deployment and environment management
- Easier testing with minimal configuration requirements