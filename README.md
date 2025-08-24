# THIS IS STILL A CONCEPT IN RESEARCH - Not really working

# ATeam - Pure CLI Multi-Agent System

A powerful, pure command-line multi-agent system with Redis-backed MCP (Model Context Protocol), explicit control, and fail-fast design principles.

## Features

- **Pure CLI**: No web servers, no HTTP overhead
- **Dual Modes**: Standalone (no Redis) and Distributed (Redis-backed)
- **Explicit Control**: No auto-approval, all actions require confirmation
- **Fail-Fast**: Immediate failure with clear error messages
- **Agent Isolation**: Each agent runs in its own process with isolated state
- **Knowledge Base**: Multi-scope KB with selective copying
- **System Prompts**: Live-reloadable base + overlay prompts
- **History Management**: Durable conversation history with intelligent summarization
- **Ownership Model**: Single console per agent with takeover support

## Quick Start

### Installation

```bash
# Install from PyPI
pip install ateam

# Or install from source
git clone https://github.com/GreenFuze/ATeam.git
cd ATeam
pip install -e .
```

### Standalone Mode (No Redis Required)

Perfect for quick local development and testing:

```bash
# Start agent in standalone mode
ateam agent --standalone

# With specific working directory
ateam agent --standalone --cwd /path/to/project
```

### Distributed Mode (Redis Required)

For multi-agent coordination and collaboration:

```bash
# Start Redis server
redis-server

# Start agent in distributed mode
ateam agent --redis redis://localhost:6379/0

# Start console for multi-agent coordination
ateam console --redis redis://localhost:6379/0
```

## Tutorial

### 1. Create Your First Agent

```bash
# Start the console
ateam console --redis redis://localhost:6379/0

# Create a new agent using the wizard
/agent new

# The wizard will ask for:
# - Project name: myproject
# - Agent name: assistant
# - Working directory: /path/to/project
# - Model: gpt-4
# - System prompt: You are a helpful AI assistant...
# - KB seeds: (optional files to ingest)
```

### 2. Attach and Converse

```bash
# Attach to your agent
/attach myproject/assistant

# Send a message
Hello! Can you help me with this project?

# Check context usage
/ctx

# View system prompt
/sys show
```

### 3. Add System Prompt Overlay

```bash
# Add a line to the overlay (applies immediately)
# Prefer concise step-by-step plans.

# Reload system prompt from disk
/reloadsysprompt
```

### 4. Knowledge Base Operations

```bash
# Add files to agent KB
/kb add --scope agent /path/to/documentation.md

# Search KB
/kb search --scope agent "how to configure"

# Copy specific items from another agent
/kb copy-from myproject/researcher --ids doc_abc123,doc_def456
```

### 5. Offload to Fresh Agent

```bash
# Start offload wizard
/offload

# Review the proposal and confirm
# This creates a new agent with fresh context
```

### 6. History Management

```bash
# Clear history (requires confirmation)
/clearhistory
# Type 'myproject/assistant' to confirm
```

## Configuration

Agents are configured through `.ateam` directories in your project:

```
project/
├── .ateam/
│   ├── project.yaml              # Project configuration
│   ├── agents/
│   │   └── my-agent/
│   │       ├── agent.yaml        # Agent configuration
│   │       ├── system_base.md    # Base system prompt
│   │       ├── system_overlay.md # Overlay prompt (editable)
│   │       ├── kb/               # Agent KB storage
│   │       └── state/            # Agent state (queue, history)
│   ├── models.yaml               # Model registry
│   ├── tools.yaml                # Tool configuration
│   └── kb/                       # Project KB storage
```

### Example Configuration Files

**project.yaml**
```yaml
name: myproject
```

**agents/my-agent/agent.yaml**
```yaml
name: my-agent
model: gpt-4
prompt:
  base: system_base.md
  overlay: system_overlay.md
tools:
  allow:
    - os.exec
    - fs.read
    - fs.write
    - kb.ingest
```

**models.yaml**
```yaml
models:
  gpt-4:
    provider: openai
    context_window_size: 8192
    default_inference:
      max_tokens: 4096
      stream: true
```

## CLI Reference

### Agent Commands

```bash
# Standalone mode
ateam agent --standalone [--cwd <path>] [--name <name>]

# Distributed mode
ateam agent --redis <url> [--cwd <path>] [--name <name>] [--project <project>]

# Options
--standalone          Run in standalone mode (no Redis)
--redis <url>         Redis URL for distributed mode
--cwd <path>          Working directory
--name <name>         Agent name override
--project <project>   Project name override
--log-level <level>   Log level (debug, info, warn, error)
```

### Console Commands

```bash
# Start console
ateam console --redis <url> [--no-ui] [--panes]

# Options
--redis <url>         Redis URL
--no-ui              Disable UI panes (plain TTY mode)
--panes              Force UI panes (if available)
--log-level <level>  Log level
```

### Console Slash Commands

- `/help` - Show help
- `/ps` - List running agents
- `/attach <agent_id> [--takeover]` - Attach to agent
- `/detach` - Detach from current agent
- `/input <text>` - Send input to agent
- `/ctx` - Show context usage
- `/sys show` - Show system prompt
- `/reloadsysprompt` - Reload system prompt
- `/kb add --scope <scope> <path>` - Add to KB
- `/kb search --scope <scope> <query>` - Search KB
- `/kb copy-from <agent> --ids <ids>` - Copy from agent
- `/agent new` - Create new agent
- `/offload` - Offload to new agent
- `/clearhistory` - Clear conversation history
- `/ui panes on|off` - Toggle UI panes
- `/quit` - Quit console

## Environment Variables

- `ATEAM_REDIS_URL`: Default Redis URL (default: `redis://127.0.0.1:6379/0`)
- `FLIT_USERNAME`: PyPI username for deployment (default: `__token__`)
- `FLIT_PASSWORD`: PyPI API token for deployment

## Agent Modes

### Standalone Mode
- **Purpose**: Quick local development and testing
- **Requirements**: No external dependencies
- **Features**: All local functionality (REPL, queue, history, prompts, memory, KB)
- **Limitations**: No multi-agent coordination, no remote RPC calls

### Distributed Mode
- **Purpose**: Multi-agent coordination and collaboration
- **Requirements**: Redis server
- **Features**: All standalone features plus MCP server, registry, heartbeat, ownership management
- **Benefits**: Agent discovery, remote RPC calls, console integration

## Architecture

### Core Components

- **AgentApp**: Main agent runtime with REPL and task processing
- **ConsoleApp**: Multi-agent console with attach/detach capabilities
- **MCP Server/Client**: Redis-backed Model Context Protocol implementation
- **Registry**: Agent discovery and state management
- **Ownership Manager**: Single console per agent with takeover support
- **Knowledge Base**: Multi-scope storage with selective copying
- **History Store**: Durable conversation history with intelligent summarization

### Design Principles

- **Fail-Fast**: Immediate failure with clear error messages
- **Explicit Control**: No auto-approval, all actions require confirmation
- **Isolation**: Each agent runs in its own process with isolated state
- **Durability**: All state is persisted to disk
- **Composability**: Agents can be combined and orchestrated

## Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with Redis (Docker required)
python -m pytest tests/ --redis-docker

# Run specific test
python -m pytest tests/test_standalone.py::TestStandaloneCLI
```

### Building and Publishing

```bash
# Build package
python -m flit build

# Publish to TestPyPI
python deploy_to_pypi.py --repository testpypi

# Publish to PyPI
python deploy_to_pypi.py
```

## Migration Guide

### From Standalone to Distributed
1. Install and start Redis server
2. Replace `--standalone` with `--redis <url>`
3. Start console for multi-agent coordination

### From Distributed to Standalone
1. Replace `--redis <url>` with `--standalone`
2. Note: Remote RPC calls will no longer work
3. All local state and configuration is preserved

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

Apache 2.0 License - see LICENSE file for details.

