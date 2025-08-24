# ATeam Multi-Agent System - Knowledge Base

## Overview

ATeam is a pure CLI multi-agent system built in Python that enables collaborative AI agents to work together on tasks. The system supports both distributed mode (with Redis) and standalone mode (without Redis), providing a flexible architecture for different deployment scenarios.

## Core Architecture

### Agent System
- **AgentApp** (`ateam/agent/main.py`): Central orchestrator for agent lifecycle
  - Manages MCP server, client, registry, heartbeat, ownership, and tail emitter
  - Supports standalone mode (no Redis) and distributed mode (with Redis)
  - Handles tool registration and execution
  - Manages agent identity and single-instance locking

- **AgentIdentity** (`ateam/agent/identity.py`): Computes unique agent ID and manages single-instance lock
  - Uses Redis for distributed locking with TTL
  - Prevents multiple instances of the same agent
  - Supports name and project overrides

- **TaskRunner** (`ateam/agent/runner.py`): Orchestrates agent tasks and streams LLM output
  - Handles tool execution and event emission
  - Manages task lifecycle (start, tokens, end, errors)
  - Integrates with TailEmitter for real-time updates

### REPL and Interaction
- **REPL** (`ateam/agent/repl.py`): Interactive command-line interface for agents
  - Supports commands like `status`, `clearhistory`, `help`
  - Indicates standalone mode when applicable
  - Handles command routing and execution

- **ConsoleApp** (`ateam/console/app.py`): Multi-agent console interface
  - Manages multiple agent sessions
  - Provides command completion and path completion
  - Handles agent attachment and detachment

### Memory and History
- **MemoryManager** (`ateam/agent/memory.py`): Manages conversation context and summarization
  - Tracks token usage and context limits
  - Implements summarization policies
  - Manages conversation turns and summaries

- **HistoryStore** (`ateam/agent/history.py`): Durable conversation history
  - JSONL-based persistence with fsync
  - Supports summary compaction and reconstruction
  - Integrates with tail events for context reconstruction

### Knowledge Base
- **KBAdapter** (`ateam/agent/kb_adapter.py`): Agent-specific knowledge base interface
  - Wraps core KB functionality for agent context
  - Handles collection naming and scoping
  - Provides ingest, search, and management operations

- **KBStorage** (`ateam/kb/storage.py`): Simple in-memory KB with JSON persistence
  - Content hash deduplication
  - JSON-based storage with file persistence
  - Collection-based organization

### MCP (Model Context Protocol) System
- **RedisTransport** (`ateam/mcp/redis_transport.py`): Redis-based message transport
  - Uses msgpack for serialization
  - Supports publish/subscribe and RPC patterns
  - Handles connection management

- **MCPServer** (`ateam/mcp/server.py`): MCP server implementation
  - Tool registration and execution
  - Event emission to connected clients
  - RPC method handling

- **MCPClient** (`ateam/mcp/client.py`): MCP client for RPC and tail subscriptions
  - RPC method calls to servers
  - Tail event subscription and processing
  - Connection management

- **MCPRegistry** (`ateam/mcp/registry.py`): Agent registration and discovery
  - Agent registration with TTL
  - Agent listing and state management
  - Agent watching and updates

- **HeartbeatService** (`ateam/mcp/heartbeat.py`): Agent health monitoring
  - Periodic heartbeat to maintain registration
  - Lock refresh for single-instance enforcement
  - Registry TTL refresh

- **OwnershipManager** (`ateam/mcp/ownership.py`): Agent ownership management
  - Ownership acquisition and release
  - Graceful takeover support
  - Lock-based ownership enforcement

- **TailEmitter** (`ateam/mcp/tail.py`): Real-time event streaming
  - In-process ring buffer for events
  - Redis publishing for distributed events
  - Monotonic offset tracking
  - Event replay capabilities

### Tools System
- **Built-in Tools**:
  - **FS Tools** (`ateam/tools/builtin/fs.py`): Sandboxed filesystem operations
    - `read_file`, `write_file`, `list_dir`, `stat_file`
    - Path sandboxing and safety checks
    - Error handling with Result types
  - **OS Tools** (`ateam/tools/builtin/os.py`): Command execution
    - `exec`: Synchronous command execution with PTY support
    - `exec_stream`: Asynchronous streaming command execution
    - Cross-platform PTY/ConPTY support
  - **PTY Executor** (`ateam/tools/ptyexec.py`): Cross-platform PTY execution
    - Unix PTY support with termios configuration
    - Windows fallback to merged pipes
    - Async streaming output

### LLM Integration
- **LLMProvider** (`ateam/llm/base.py`): Abstract base for LLM providers
  - `generate`, `stream`, `estimate_tokens` methods
  - Standardized interface for different providers
- **EchoProvider** (`ateam/llm/echo.py`): Simple echo provider for testing
  - Echoes input for testing and development
  - Implements streaming interface

### Configuration
- **ConfigDiscovery** (`ateam/config/loader.py`): Configuration loading and discovery
  - YAML-based configuration
  - Environment variable overrides
  - Runtime discovery of components
- **AgentCfg** (`ateam/config/schema_agents.py`): Agent configuration schema
  - Pydantic-based validation
  - Required fields: name, prompt
  - Optional fields for customization

### Utilities
- **Result/ErrorInfo** (`ateam/util/types.py`): Standardized error handling
  - `Result[T]` type for success/failure results
  - `ErrorInfo` for detailed error context
  - Consistent error handling across the system
- **SecretsRedactor** (`ateam/util/secrets.py`): Sensitive data redaction
  - Regex-based pattern matching
  - Environment-configurable patterns
  - String and dictionary redaction
- **Logging** (`ateam/util/logging.py`): Centralized logging with redaction
  - Integration with SecretsRedactor
  - Structured logging support
  - Sensitive data protection

## Key Design Patterns

### Fail-Fast Philosophy
- Immediate failure on unexpected conditions
- No silent failures or fallback logic
- Clear, actionable error messages
- Proper HTTP status codes (400 for validation, 500 for runtime errors)

### Manager Pattern
- Global registry with centralized initialization
- Direct function access via aliases
- No local manager copies
- Centralized initialization point

### Message-Driven Architecture
- Pure direct UI communication
- No return values for UI operations
- Message passing for component communication
- Event-driven over return-value orchestration

### Active Object Pattern
- Agent-level task queues for sequential processing
- Race condition prevention within agents
- Concurrent processing across agents
- Proper async/await usage

### Type Safety
- Pydantic models for all data structures
- Strict type annotations
- Enum usage over string literals
- No unnecessary type casting

## Standalone Mode Implementation

### Core Changes
1. **AgentApp**: Added `standalone_mode` flag and conditional Redis component initialization
2. **CLI**: Added `--standalone` option and validation logic
3. **REPL**: Updated status display to indicate standalone mode
4. **TaskRunner**: Modified event emission to use TailEmitter instead of MCP server
5. **Tool System**: Integrated tool registration and execution

### Redis-Dependent Components
- MCP Server, Client, Registry
- Heartbeat Service
- Ownership Manager
- Redis Transport

### Core Components (Always Available)
- REPL, PromptQueue, HistoryStore
- PromptLayer, MemoryManager, TaskRunner
- KB Adapter, Tool System
- TailEmitter (in-process ring buffer)

## Testing Strategy

### Test Infrastructure
- **RedisTestManager**: Docker-based Redis management for tests
- **pytest_configure/pytest_unconfigure**: Global test setup and teardown
- **redis_url fixture**: Provides Redis URL for tests
- **clear_redis_keys fixture**: Cleans Redis state between tests

### Test Categories
1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Component interaction testing
3. **End-to-End Tests**: Full system workflow testing
4. **Standalone Mode Tests**: Standalone functionality verification

### Key Test Files
- `tests/test_standalone.py`: Standalone mode functionality
- `tests/test_smoke_integration.py`: Basic integration scenarios
- `tests/test_fs.py`: Filesystem tool testing
- `tests/test_ptyexec.py`: PTY execution testing
- `tests/test_tool_integration.py`: Tool system integration
- `tests/test_change3_cases.py`: High-value test scenarios

## CLI Interface

### Commands
- `ateam agent`: Start an agent (with `--standalone` or `--redis` options)
- `ateam console`: Start the multi-agent console
- `ateam cli`: General CLI interface

### Options
- `--redis`: Redis URL for distributed mode
- `--standalone`: Enable standalone mode (no Redis)
- `--cwd`: Working directory override
- `--name`: Agent name override
- `--project`: Project name override

## Configuration Management

### Environment Variables
- `ATEAM_REDIS_URL`: Default Redis URL
- `ATEAM_SECRETS_PATTERNS`: Secrets redaction patterns
- Various configuration overrides

### Configuration Files
- YAML-based configuration
- Project-specific `.ateam` directories
- Environment-specific overrides

## Deployment and Packaging

### Docker Support
- `docker-compose.yml`: Production-ready Redis configuration
- Health checks and persistence
- Memory limits and restart policies

### PyPI Packaging
- `pyproject.toml`: Flit-based packaging configuration
- `deploy_to_pypi.py`: Automated deployment script
- Wheel building and verification

## Security Considerations

### Sandboxing
- Path sandboxing for filesystem operations
- Command execution restrictions
- Tool access controls

### Secrets Management
- Regex-based secrets redaction
- Environment-configurable patterns
- Log protection

### Access Control
- Agent ownership management
- Single-instance locking
- Graceful takeover support

## Performance Optimizations

### TailEmitter
- In-process ring buffer for low-latency events
- Redis publishing for distributed events
- Monotonic offset tracking
- Event replay capabilities

### Memory Management
- Context token tracking
- Summarization policies
- History compaction

### Async Operations
- Proper async/await usage
- Non-blocking I/O operations
- Concurrent agent processing

## Error Handling

### Result Types
- `Result[T]` for success/failure results
- `ErrorInfo` for detailed error context
- Consistent error codes and messages

### Exception Handling
- Fail-fast philosophy
- Proper error propagation
- Clear error messages with context

### Recovery Mechanisms
- LLM auto-recovery for invalid requests
- Graceful degradation where possible
- User guidance for error resolution

## Development Workflow

### Code Organization
- Logical grouping of related methods
- Public before private method ordering
- Consistent patterns throughout codebase
- Modular, testable components

### Testing Practices
- Fail-fast testing philosophy
- Comprehensive test coverage
- Integration testing
- Validation testing

### Code Quality
- Type checking and linting
- Documentation standards
- Code review processes
- Continuous integration

## Current Implementation Status

### Completed Features
- ✅ Standalone agent mode
- ✅ Tool registration and execution system
- ✅ Filesystem and OS tools
- ✅ PTY/ConPTY execution
- ✅ Real-time event streaming
- ✅ Agent identity and locking
- ✅ Memory management and summarization
- ✅ Knowledge base integration
- ✅ CLI interface and console
- ✅ Comprehensive testing infrastructure
- ✅ Docker and packaging support

### Pending Tasks (from change11.md)
- Ownership hardening & takeover UX
- Persistence polish & recovery
- Windows polish & paths
- Packaging & TestPyPI
- Security & gating
- Docs & examples

### High-Value Test Cases (from change3.md)
- Identity & lock (duplicate agent)
- Ownership (attach/unowned, second attach denied, takeover)
- Queue & history (append/peek/pop roundtrip)
- Prompts (`/reloadsysprompt`, `# <line>` overlay)
- KB (`kb.ingest` deduplication, `kb.copy_from` selective copying)
- Autocomplete (command completion, path completion with quotes)
- Panes off (`--no-ui` functionality)
- Security (secrets redaction)

## Key Implementation Details

### Tool Registration System
```python
# In AgentApp
self._tools: Dict[str, Any] = {}
self.register_tool(name, tool_func)
self.get_tool(name)
self.list_tools()
```

### Event Emission
```python
# In TaskRunner
self.app.tail.emit("tool.start", {"name": tool_name})
self.app.tail.emit("tool.result", {"output": result})
self.app.tail.emit("tool.end", {})
```

### Sandbox Protection
```python
# In fs.py
def _is_safe_path(path: str, cwd: str) -> bool:
    cwd_resolved = Path(cwd).resolve()
    if Path(path).is_absolute():
        path_resolved = Path(path).resolve()
        return str(path_resolved).startswith(str(cwd_resolved))
```

### TailEmitter Ring Buffer
```python
# In tail.py
self._ring_buffer = deque(maxlen=ring_capacity)
self._current_offset = 0
self.emit(event_type, data)
```

### Agent Identity
```python
# In identity.py
self.agent_id = self._compute_agent_id()
self._lock_key = f"ateam:lock:{self.agent_id}"
```

## Troubleshooting Guide

### Common Issues
1. **Redis Connection**: Check Redis URL and connectivity
2. **Agent Lock**: Ensure single instance per agent
3. **Tool Execution**: Verify tool registration and permissions
4. **Path Issues**: Check sandbox restrictions and working directory
5. **PTY Support**: Verify platform-specific PTY implementation

### Debugging Tools
- Agent status command
- Console logging with secrets redaction
- Tail event monitoring
- Tool execution tracing

### Performance Monitoring
- Tail latency tracking
- Memory usage monitoring
- Tool execution timing
- Event throughput metrics

This knowledge base provides a comprehensive understanding of the ATeam multi-agent system, enabling new sessions to implement features and maintain the codebase effectively.
