# Plan: Standalone Agent Mode Implementation

## Overview
Implement the ability for agents to run in standalone mode without requiring a Redis connection. The agent should work normally with its REPL, but without the distributed features that require Redis (MCP server, registry, heartbeat, ownership, etc.).

## Current Architecture Analysis

### Redis-Dependent Components
1. **MCP Server** - Handles RPC calls from console
2. **MCP Client** - Makes RPC calls to other agents  
3. **Registry** - Registers agent with Redis for discovery
4. **Heartbeat Service** - Maintains agent liveness
5. **Ownership Manager** - Handles console ownership locks
6. **CLI Parameter** - `redis_url` is currently required

### Core Components (Redis-Independent)
1. **REPL** - Local command interface
2. **Queue** - Local prompt queue
3. **History** - Local conversation history
4. **Prompts** - Local system prompt management
5. **Memory** - Local memory management
6. **Task Runner** - Local task execution
7. **KB Adapter** - Local knowledge base

## Implementation Plan

### Phase 1: Core Infrastructure Changes

#### 1.1 Modify AgentApp Constructor
- [x] Change `redis_url` parameter to be optional (`Optional[str]`)
- [x] Add `standalone_mode` boolean flag
- [x] Update constructor to handle `None` redis_url
- [x] Add validation logic for standalone mode

#### 1.2 Update Bootstrap Method
- [x] Add conditional logic to skip Redis-dependent initialization
- [x] Skip ownership lock acquisition in standalone mode
- [x] Skip MCP server startup in standalone mode
- [x] Skip MCP client initialization in standalone mode
- [x] Skip registry registration in standalone mode
- [x] Skip heartbeat service in standalone mode
- [x] Ensure all core components still initialize properly

#### 1.3 Update Shutdown Method
- [x] Add conditional logic to skip Redis-dependent cleanup
- [x] Skip registry unregistration in standalone mode
- [x] Skip MCP server shutdown in standalone mode
- [x] Skip ownership release in standalone mode
- [x] Ensure graceful shutdown still works

### Phase 2: CLI Interface Updates

#### 2.1 Update CLI Command
- [x] Make `--redis` parameter optional in `ateam agent` command
- [x] Add `--standalone` flag as explicit standalone mode
- [x] Update help text to document standalone mode
- [x] Add validation to ensure either `--redis` or `--standalone` is provided

#### 2.2 Environment Variable Support
- [x] Support `ATEAM_REDIS_URL` environment variable
- [x] Allow `ATEAM_REDIS_URL=""` or unset for standalone mode
- [x] Update documentation for environment variable usage

### Phase 3: REPL Enhancements

#### 3.1 Update REPL Status Command
- [x] Show standalone mode indicator in status
- [x] Display appropriate status information for standalone mode
- [x] Hide Redis-dependent status fields in standalone mode

#### 3.2 Update REPL Help
- [x] Add standalone mode information to help text
- [x] Document which commands work in standalone mode
- [x] Add note about distributed features being unavailable

#### 3.3 Command Availability
- [x] Ensure all local commands work in standalone mode:
  - [x] `status` - Show local status
  - [x] `enqueue` - Add to local queue
  - [x] `sys show` - Show system prompt
  - [x] `sys reload` - Reload system prompt
  - [x] `reload` - Reload all prompts
  - [x] `kb add` - Add to local KB
  - [x] `clearhistory` - Clear local history
  - [x] `quit` - Exit agent

### Phase 4: Component Adaptations

#### 4.1 Task Runner Updates
- [x] Ensure task runner works without MCP client
- [x] Handle case where RPC calls to other agents are unavailable
- [x] Provide appropriate error messages for distributed features

#### 4.2 KB Adapter Updates
- [x] Ensure KB adapter works in standalone mode
- [x] Handle case where cross-agent KB operations are unavailable
- [x] Provide appropriate error messages for distributed KB features

#### 4.3 Memory Manager Updates
- [x] Ensure memory manager works without distributed features
- [x] Handle summarization in standalone mode
- [x] Ensure context reconstruction works locally

### Phase 5: Error Handling & User Experience

#### 5.1 Graceful Degradation
- [x] Provide clear error messages when distributed features are attempted
- [x] Suggest standalone mode when Redis is unavailable
- [x] Handle Redis connection failures gracefully

#### 5.2 Status Indicators
- [x] Add clear visual indicators for standalone mode
- [x] Show which features are available/unavailable
- [x] Provide helpful messages about mode limitations

#### 5.3 Logging Updates
- [x] Add appropriate log messages for standalone mode
- [x] Log when Redis-dependent features are skipped
- [x] Ensure logging works without Redis

### Phase 6: Testing Implementation

#### 6.1 Unit Tests
- [x] Test AgentApp constructor with None redis_url
- [x] Test bootstrap method in standalone mode
- [x] Test shutdown method in standalone mode
- [x] Test all core components in standalone mode

#### 6.2 Integration Tests
- [x] Test full agent startup in standalone mode
- [x] Test REPL functionality in standalone mode
- [x] Test all commands in standalone mode
- [x] Test graceful degradation when Redis is unavailable

#### 6.3 CLI Tests
- [x] Test CLI with `--standalone` flag
- [x] Test CLI with no `--redis` parameter
- [x] Test environment variable handling
- [x] Test validation and error messages

#### 6.4 Edge Case Tests
- [x] Test agent startup with invalid Redis URL
- [x] Test agent startup with Redis unavailable
- [x] Test transition from standalone to connected mode
- [x] Test transition from connected to standalone mode

### Phase 7: Documentation Updates

#### 7.1 CLI Documentation
- [x] Update `ateam agent --help` output
- [x] Document standalone mode usage
- [x] Provide examples for standalone mode

#### 7.2 User Guide Updates
- [x] Add section on standalone mode
- [x] Document limitations of standalone mode
- [x] Provide migration guide from standalone to connected mode

#### 7.3 Code Documentation
- [x] Update docstrings for modified methods
- [x] Add comments explaining standalone mode logic
- [x] Document new parameters and flags

### Phase 8: Validation & Quality Assurance

#### 8.1 Functionality Verification
- [x] Verify all local features work in standalone mode
- [x] Verify no Redis dependencies remain in core functionality
- [x] Verify graceful error handling for distributed features

#### 8.2 Performance Testing
- [x] Test startup time in standalone mode
- [x] Test memory usage in standalone mode
- [x] Test REPL responsiveness in standalone mode

#### 8.3 Compatibility Testing
- [x] Test with existing agent configurations
- [x] Test with existing prompt files
- [x] Test with existing knowledge base files

## Implementation Details

### Key Design Decisions

1. **Backward Compatibility**: Existing agents should continue to work unchanged
2. **Explicit Mode**: Use explicit `--standalone` flag rather than inferring from missing Redis
3. **Graceful Degradation**: Distributed features should fail gracefully with helpful messages
4. **Local-First**: All local functionality should work identically in both modes

### Error Handling Strategy

1. **Clear Messages**: Provide clear error messages when distributed features are unavailable
2. **Helpful Suggestions**: Suggest standalone mode when Redis is unavailable
3. **Graceful Failures**: Don't crash when distributed features fail

### Testing Strategy

1. **Comprehensive Coverage**: Test all components in both modes
2. **Edge Cases**: Test various failure scenarios
3. **Integration**: Test full workflows in both modes
4. **Performance**: Ensure no performance regression in connected mode

## Success Criteria

- [x] Agent can start without Redis connection
- [x] All local REPL commands work in standalone mode
- [x] Clear status indicators show standalone mode
- [x] Helpful error messages for distributed features
- [x] No performance regression in connected mode
- [x] Comprehensive test coverage
- [x] Updated documentation
- [x] Backward compatibility maintained

## Risk Mitigation

1. **Complexity**: Keep changes minimal and focused
2. **Testing**: Comprehensive testing to prevent regressions
3. **Documentation**: Clear documentation of limitations
4. **User Experience**: Clear indicators and helpful messages
