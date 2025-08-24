# ATeam Knowledge Base

> **Status**: Complete CLI multi-agent system specification — autonomous agents over Redis-backed MCP, central Console attach/detach, single-instance locks, explicit KB scopes, layered prompts with live reload, selective offload, durable history, fail-fast creation, full object-oriented API, **F1** palette toggle, **TAB** autocomplete, and PyPI/Flit packaging.

---

## Table of Contents

1. [Overview & Architecture](#overview--architecture)
2. [Core Principles](#core-principles)
3. [Repository Structure](#repository-structure)
4. [Configuration System](#configuration-system)
5. [Agent System](#agent-system)
6. [Console System](#console-system)
7. [MCP Transport & Registry](#mcp-transport--registry)
8. [Knowledge Base](#knowledge-base)
9. [Tools & Execution](#tools--execution)
10. [Commands Reference](#commands-reference)
11. [Implementation Plan](#implementation-plan)
12. [API Reference](#api-reference)
13. [Deployment & Packaging](#deployment--packaging)
14. [Security & Best Practices](#security--best-practices)
15. [Troubleshooting](#troubleshooting)

---

## Overview & Architecture

ATeam is a **pure CLI multi-agent runtime** that enables autonomous agents to work together via Redis-backed MCP (Model Context Protocol). Each agent runs as an independent process with its own environment, while a central Console provides unified control and monitoring.

### Key Components

- **Agents**: Autonomous workers with local REPLs, exposing MCP tools over Redis
- **Console**: Central TUI/REPL that discovers, attaches to, and controls agents
- **MCP Transport**: Redis-based pub/sub for agent communication and control
- **Knowledge Base**: Scoped vector storage with selective copy capabilities
- **Tools**: Sandboxed filesystem and execution tools with security controls

### Architecture Flow

```
Console (TUI) ←→ Redis MCP ←→ Agent 1 (Process)
                ↕              ↕
              Registry      Agent 2 (Process)
                ↕              ↕
              Ownership     Agent N (Process)
```

---

## Core Principles

### 1. Explicit over Implicit
- **No automatic actions** without explicit user confirmation
- Cross-scope operations (KB/project/user, prompt changes, agent creation) require explicit commands
- Fail-fast validation with clear error messages

### 2. Loose Coupling
- Each agent runs as an autonomous process with its own environment
- Agents expose MCP servers on Redis for communication
- Console is an MCP client that discovers and controls agents

### 3. Isolation by Default
- Memory, prompts, and KB are **agent-scoped** by default
- Project/user KB scopes exist but are **opt-in only**
- Single-instance locks prevent duplicate agents

### 4. Cross-Platform Support
- Windows (ConPTY) and Unix (pty) support
- Optional Rich/Textual panes; plain TTY mode always works
- Consistent behavior across platforms

---

## Repository Structure

```
ateam/                          # Python package (installable module)
  __init__.py
  cli.py                        # entry point: `ateam console|agent`
  console/                      # Console (REPL/TUI)
    app.py                      # main application loop
    palette.py                  # F1 palette (agents, quick actions)
    panes.py                    # optional panes (Rich/Textual)
    attach.py                   # AgentSession attach/detach & tail
    cmd_router.py               # slash command parsing/dispatch
    completer.py                # TAB autocomplete (commands, agent IDs, paths)
    wizard_create.py            # /agent new
    wizard_offload.py           # /offload
  agent/                        # Agent (autonomous worker)
    main.py                     # AgentApp bootstrap
    repl.py                     # local agent REPL (simple, no panes)
    runner.py                   # TaskRunner, tool interception, streaming
    queue.py                    # durable prompt queue (jsonl)
    history.py                  # durable history & summaries (jsonl)
    identity.py                 # project/agent identity + single-instance lock
    prompt_layer.py             # base+overlay system prompt
    memory.py                   # ctx tokens %, summarize policy
    kb_adapter.py               # scope-aware KB ops
    completer.py                # TAB autocomplete for agent REPL
  mcp/
    server.py                   # MCPServer (tool registration, emit events)
    client.py                   # MCPClient (call tools, subscribe tail)
    redis_transport.py          # RedisTransport (pub/sub & RPC)
    registry.py                 # register/list/watch agents
    heartbeat.py                # TTL heartbeats
    ownership.py                # single console write owner per agent
    contracts.py                # dataclasses & wire contracts
    orchestrator.py             # create/spawn APIs used by Console
  config/
    discovery.py                # .ateam discovery (CWD→parents→home)
    merge.py                    # merge precedence rules
    schema_project.py
    schema_agents.py
    schema_models.py
    schema_tools.py
  tools/
    registry.py                 # builtin tool registry (config-level)
    builtin/
      os.py                     # os.exec with PTY/ConPTY
      fs.py                     # safe FS ops (sandbox)
      kb.py                     # kb config helpers
      agents.py                 # config-level agent mgmt
  models/
    manager.py                  # model registry + provider adapters
  util/
    tokenizer.py
    io.py
    paths.py
    logging.py

pyproject.toml                   # Flit packaging
README.md
LICENSE
deploy_to_pypi.py                # Flit-based publish script
```

---

## Configuration System

### `.ateam` Discovery & Merge

**Search order** (highest priority first): CWD → parents → `~/.ateam` (or `%USERPROFILE%/.ateam`)

**Directory structure**
```
.ateam/
  project.yaml                  # { name: "<project_name>" } (optional)
  agents/
    <agent_name>/
      agent.yaml                # agent definition (YAML)
      system_base.md            # base system prompt
      system_overlay.md         # overlay edits (via "#" or /sys edit)
      plan.md                   # optional plan
      kb/
        docs/                   # raw docs (optional)
        index/                  # vector index (optional)
      state/
        queue.jsonl             # prompt queue (append-only)
        history.jsonl           # conversation turns (append-only)
        summary.jsonl           # rolling summaries
  models.yaml                   # models registry
  tools.yaml                    # tool allow/deny + MCP defaults
  prompts/                      # shared prompt snippets (optional)
  defaults/
    agent                       # default agent name for this scope
```

**Merge rules**
- **Scalars**: highest priority wins
- **Dicts**: recursive; high overrides keys
- **Lists**: concat high→low; de-dupe by id/name
- **Agents**: union; on name conflict, take **highest-priority agent dir** entirely
- **Tools**: union; apply allow/deny after merge

### Configuration Files

#### `project.yaml`
```yaml
name: myproj
description: "Optional project description"
retention_days: 30  # optional history retention
```

#### `models.yaml`
```yaml
models:
  gpt-5-nano:
    provider: openai
    context_window_size: 128000
    default_inference:
      max_tokens: 4096
      stream: true
    model_settings: {}
```

#### `tools.yaml`
```yaml
mcp:
  transport:
    kind: redis
    url: redis://127.0.0.1:6379/0
    username: ateam        # optional (Redis ACL)
    password: <secret>     # optional
    tls: false             # optional

tools:
  allow: [ "os.exec", "fs.read", "fs.write", "kb.ingest", "kb.copy_from" ]
  deny:  [ ]
  unsafe: false  # global unsafe toggle
```

#### `agent.yaml`
```yaml
name: zeus
model: gpt-5-nano
prompt:
  base: system_base.md
  overlay: system_overlay.md
scratchpad:
  max_iterations: 4
  score_lower_bound: 0.78
tools:
  allow:
    - os.exec
    - fs.read
    - fs.write
    - kb.ingest
    - kb.copy_from
fs:
  whitelist:
    - /tmp/allowed
    - C:\Users\Tsvi\work\shared
```

---

## Agent System

### Agent Identity & Single-Instance Lock

- **Identity**: `project_name/agent_name`
  - `project_name` from nearest `.ateam/project.yaml`; fallback: CWD basename
- **Lock key**: `mcp:agent:lock:{project}/{agent}` (Redis `SET NX EX <ttl>`)
  - If lock exists → agent **exits** with clear message
  - Heartbeat refreshes lock TTL; crash → lock expires

### Agent State Machine

```
INIT → REGISTERED → {IDLE ↔ BUSY} → (DISCONNECTED)
   ^                                   |
   |------------- SHUTDOWN ------------- 
```

- **INIT**: startup, config, lock acquire
- **REGISTERED**: MCP server started, registry key written, heartbeat active
- **IDLE**: no current task; waiting on queue
- **BUSY**: processing one queue item; emits `task.start/task.end`
- **DISCONNECTED**: (Console view) when heartbeats missed > 3 intervals
- **SHUTDOWN**: graceful exit → release locks, remove registry

### Agent Runtime Components

#### PromptQueue (JSONL)
```json
{"id":"q-001","ts":1724221257.12,"source":"console","text":"build the project"}
```

#### HistoryStore (JSONL)
```json
{"ts":1724221258.42,"role":"user","source":"console","content":"build the project","tokens_in":25,"tokens_out":0}
{"ts":1724221265.02,"role":"assistant","source":"system","content":"Starting build...","tokens_in":350,"tokens_out":42,"tool_calls":[{"name":"os.exec","args":{"cmd":"cmake .."}}]}
```

#### PromptLayer
- **Base prompt**: `system_base.md` (static)
- **Overlay prompt**: `system_overlay.md` (editable)
- **Protected blocks**: `<!-- ateam-protect:start:toolbox -->` (auto-generated)
- **Live reload**: `/reloadsysprompt` applies changes immediately

#### MemoryManager
- Tracks context token usage and percentage
- Triggers summarization when `ctx_pct >= threshold` (default 0.75)
- Manages context reconstruction on restart

---

## Console System

### Console Features

- **Non-blocking input** — user input bar never blocks
- **F1 palette** — searchable list of agents (state/ctx%/host) + quick actions
- **Optional panes** — single-terminal (Rich/Textual):
  - Left: agents list; Center: attached stream; Right: compact tails; Bottom: command bar
- **Plain mode** — `--no-ui` or missing deps: lines prefixed `[A:<project/agent>]`
- **Key bindings**:
  - `F1`: toggle palette
  - `TAB`: autocomplete (commands, agent IDs, **filesystem paths**)
  - `Ctrl+C`: `/interrupt` if attached, else exits console

### Ownership Semantics

- **Single writer**: Exactly one Console has write privileges per agent
- **Read-only sessions**: Others may `/tail` read-only
- **Takeover**: `/attach --takeover` attempts replacement with grace timeout
- **Lock key**: `mcp:agent:owner:{project}/{agent}` → Console session id

### Console Commands

| Command | Args | Description |
|---|---|---|
| `/help` |  | Show command list |
| `/ps` | `[--json]` | List runtime agents with state/host/model/ctx% |
| `/agents` |  | List configured agents (from `.ateam`) |
| `/attach` | `<project/agent> [--takeover]` | Attach and acquire write ownership |
| `/detach` |  | Detach current session |
| `/who` |  | Show current attached agent and ownership |
| `/spawn` | `<agent_name> [--project N] [--cwd D] [--model M]` | Spawn a local agent (confirm) |
| `/agent new` |  | Wizard to create agent (explicit) |
| `/offload` |  | Wizard to offload current task to fresh agent |
| `/input` | `<text>` | Send one message to attached agent (plain text works too) |
| `/interrupt` |  | Cooperative cancel of current task |
| `/cancel` | `[--hard]` | Cancel current task/tool (hard = force) |
| `/kb add` | `--scope S <path|url>...` | Ingest docs into KB (S ∈ agent/project/user) |
| `/kb search` | `--scope S <query>` | Search KB scope |
| `/kb copy-from` | `<project/agent> --ids <id1,id2,...>` | Selective copy by ids |
| `/plan` | `read|write|append|delete|list` | Manage optional `plan.md` |
| `/ctx` |  | Show tokens in context and ctx% |
| `/sys show` |  | Show effective system prompt (base + overlay) |
| `/sys edit` |  | Open overlay in `$EDITOR`, apply on save |
| `/reloadsysprompt` |  | Reload base+overlay from disk and apply |
| `#` | `<line>` | Append single overlay line and apply |
| `/models` |  | List available models |
| `/use` | `<model_id>` | Set model for current agent (ephemeral until `/save`) |
| `/save` |  | Persist current agent config to highest-priority `.ateam` |
| `/tools` |  | List allowed tools and MCP health |
| `/ui panes` | `on|off` | Toggle panes UI |
| `/quit` |  | Exit console |

---

## MCP Transport & Registry

### Redis Keys & Channels

**Keys** (string with TTL unless noted)
- Registry: `mcp:agents:{project}/{agent}` → JSON `AgentInfo` (TTL refreshed by heartbeat)
- Single-instance lock: `mcp:agent:lock:{project}/{agent}` → value=`{host}:{pid}` (TTL refreshed each heartbeat)
- Ownership (write owner): `mcp:agent:owner:{project}/{agent}` → `{session_id}:{ts}` (no TTL; explicit release)

**Pub/Sub Channels**
- Tail events: `mcp:tail:{project}/{agent}` → msgpack/json-encoded `TailEvent`
- RPC request/response:
  - Requests: `mcp:req:{project}/{agent}`
  - Responses: `mcp:res:{project}/{agent}:{request_id}`

### Registry Entry Format

```json
{
  "id": "project/agent",
  "name": "agent",
  "project": "project",
  "model": "gpt-5-nano",
  "cwd": "/path/to/project",
  "host": "machine-1",
  "pid": 12345,
  "started_at": "2025-08-21T08:12:51Z",
  "state": "idle",
  "ctx_pct": 0.32,
  "tools": ["status","input","tail","cancel","interrupt",
            "prompt.set","prompt.reload",
            "kb.ingest","kb.copy_from","memory.stats"]
}
```

### RPC Envelope Format

**Request**
```json
{
  "req_id": "r-9f2f6c98",
  "method": "input",
  "params": { "text": "build", "meta": { "source": "console" } },
  "ts": 1724230001.112,
  "caller": "console:{session_id}",
  "timeout_sec": 15.0
}
```

**Response**
```json
{
  "req_id": "r-9f2f6c98",
  "ok": true,
  "value": { "queued": true, "qid": "q-001" },
  "error": null,
  "ts": 1724230001.298
}
```

### TailEvent Format

```json
{ "type": "token", "text": "...", "model": "gpt-5-nano" }
{ "type": "tool", "name": "os.exec", "input": {"cmd":"..."} }
{ "type": "warn", "msg": "...", "trace": "..." }
{ "type": "error", "msg": "...", "trace": "..." }
{ "type": "task.start", "id": "t-123", "prompt_id": "q-456" }
{ "type": "task.end", "id": "t-123", "ok": true }
```

---

## Knowledge Base

### KB Scopes & Storage

- **Default scope**: `agent`. Supported: `agent`, `project`, `user` — must be specified for KB commands
- **Storage locations**:
  - Agent → `.ateam/agents/<name>/kb/`
  - Project → `.ateam/kb/`
  - User → `~/.ateam/kb/`

### Content Processing

#### Ingestion Pipeline
1. Resolve paths/URLs; for directories, include files by glob
2. Optional pre-processors (code splitter, markdown splitter)
3. Chunking: target `CHUNK_TOKENS ~ 600`, overlap `OVERLAP_TOKENS ~ 80`
4. Embedding model (provider-agnostic)
5. Indexing: store vectors under `{scope_root}/index/`
6. Metadata: `{path, mtime, size, hash, scope, source_agent?, project?}`

#### Content Hashing
- **SHA-256** over normalized content
- Normalize line endings (`\n`), trim trailing spaces, collapse multiple blank lines to 2
- **De-dup**: if hash exists in target scope, skip ingest; report in `skipped`

#### Search
- KNN cosine similarity; top-K (default 8) with min score threshold (default 0.35)
- Return `KBHit{id, score, metadata}`; Console pretty-prints path & title

#### Selective Copy
- `/kb copy-from <id> --ids a,b,c`:
  - Resolve source scope and read doc metadata/contents by ids
  - Re-ingest into target scope; maintain provenance: `metadata.source = "<source_agent_id>"`

---

## Tools & Execution

### Tool Registry

#### Naming Convention
- Tool names are lowercase, dot-separated: `os.exec`, `fs.read`, `kb.ingest`, `agents.spawn`
- Version suffix optional: `fs.read@v1`. Default `@v1`

#### Built-in Tools

**os.exec**
```python
def exec(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload: { "cmd": str, "cwd"?: str, "timeout"?: int, "env"?: Dict[str,str], "pty"?: bool }
    returns: { "rc": int, "stdout": str, "stderr": str }
    """
```

**fs.read**
```python
def read(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload: { "path": str }
    returns: { "content": str }
    """
```

**fs.write**
```python
def write(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload: { "path": str, "content": str, "create_dirs"?: bool }
    returns: { "ok": bool }
    """
```

### Path Sandbox Rules

- **Base sandbox root** = agent `cwd`
- **Allowed**:
  - Relative paths inside sandbox
  - Absolute paths that resolve under sandbox after `realpath`
- **Denied by default**:
  - Parent escapes (`..`) that resolve outside sandbox
  - Symlink traversal to outside sandbox
  - Special device files
- **Overrides**:
  - Per-agent whitelist in `agent.yaml`
  - `/os exec --unsafe` disabled by default; if enabled, requires explicit confirmation

### PTY/ConPTY Handling

- **Unix**: use `pty` + non-blocking reads; forward stdout/stderr → tokenized events
- **Windows**: use `pywinpty` (ConPTY) with overlapped I/O
- Both paths expose unified API to `tools/builtin/os.py:exec()`

---

## Implementation Plan

### Phase 0 — Bootstrap & scaffolding ✅
- [x] Create `ateam/` package at repo root; add `pyproject.toml`, `README.md`, `LICENSE`
- [x] Add `ateam/cli.py` with Typer skeleton (`ateam console`, `ateam agent`)
- [x] Port minimal `util/logging.py`, `util/paths.py`

### Phase 1 — Config discovery & identity ✅
- [x] Implement `config/discovery.py` to collect `.ateam` stack (CWD→parents→home)
- [x] Implement `config/merge.py` precedence (scalars/dicts/lists)
- [x] Implement schemas: `schema_project.py`, `schema_agents.py`, `schema_models.py`, `schema_tools.py`
- [x] Implement `agent/identity.py` to compute `project/agent` (from project.yaml or dirname)
- [x] Unit tests for discovery/merge/identity

### Phase 2 — Redis MCP transport & registry ✅
- [x] Implement `mcp/redis_transport.py` (pub/sub + RPC)
- [x] Implement `mcp/server.py` + `mcp/client.py`
- [x] Implement `mcp/registry.py` (register/list/watch) + `RegistryEvent`
- [x] Implement `mcp/heartbeat.py` (TTL heartbeats)
- [x] Implement `mcp/ownership.py` (owner lock acquire/release/validate)
- [x] Smoke test with a dummy agent registering; Console lists it

### Phase 3 — Agent runtime (skeleton) ✅
- [x] Implement `agent/main.py` boot: discovery → identity → lock → MCP server → registry → heartbeat → REPL
- [x] Implement `agent/repl.py` (basic: `status`, `enqueue`, `sys reload`, `kb add`)
- [x] Implement `agent/completer.py` (TAB autocomplete for commands & paths)
- [x] Implement `agent/queue.py` (append/peek/pop + JSONL)
- [x] Implement `agent/history.py` (append + fsync; summaries stub)
- [x] Implement `agent/prompt_layer.py` (base+overlay + reload)
- [x] Bind MCP tools: `status`, `tail`, `input`, `interrupt`, `cancel`, `prompt.set`, `prompt.reload`

### Phase 4 — Console attach/detach & non-blocking UI ✅
- [x] Implement `console/app.py` with event loop and Redis connection
- [x] Implement `console/cmd_router.py` and handlers for `/ps`, `/attach`, `/detach`, `/input`
- [x] Implement `console/ui.py` with prompt-toolkit interface (F1/F2/F3 bindings)
- [x] Implement `console/completer.py` with full TAB completion (commands/agent ids/paths)
- [x] Implement `console/attach.py` (`AgentSession` + tail subscription)
- [x] Enforce ownership (write vs read-only sessions)

### Phase 5 — LLM integration & memory ✅
- [x] Port `llm/` provider adapters (from backend/)
- [x] Implement `agent/memory.py` (ctx tokens/pct; summarize policy)
- [x] Implement `agent/runner.py` integrated with `llm` & tools interception; stream tokens
- [x] Add `/ctx` and memory stats reporting

### Phase 6 — KB scopes & selective copy ✅
- [x] Port KB logic to `agent/kb_adapter.py` + `ateam/kb/`
- [x] Add MCP tools `kb.ingest`, `kb.copy_from`
- [x] Implement Console commands `/kb add`, `/kb search`, `/kb copy-from` with **explicit scope**
- [x] De-dupe by content hash

### Phase 7 — Comprehensive testing & integration ✅
- [x] Fix all async/await mocking issues in console tests
- [x] Fix ownership management test with proper JSON serialization
- [x] Ensure all 114 tests pass (100% success rate)
- [x] Validate Redis integration and MCP transport
- [x] Verify console UI and completer functionality
- [x] Confirm KB scopes and selective copy work correctly

### Phase 8 — System prompts & overlays ✅
- [x] Add Console commands: `# <text>`, `/sys show`, `/sys edit`, `/reloadsysprompt`
- [x] Persist overlays and reapply on reload
- [x] Render effective prompt with markers

### Phase 9 — Offload & creation wizards (fail-fast) ✅
- [x] Implement `mcp/orchestrator.py` client
- [x] Implement `console/wizard_create.py` (`/agent new`)
- [x] Implement `console/wizard_offload.py` (`/offload`)
- [x] Local spawn + remote one-liner printing
- [x] Enforce **no auto-approve**; confirmations mandatory

### Phase 10 — Optional panes UI (Rich/Textual) ✅
- [x] Implement `console/panes.py` (left list, center stream, right tails, bottom input)
- [x] Toggle via `/ui panes on|off`
- [x] Fallback to plain mode when unavailable

### Phase 11 — Reliability, security, edge cases ✅
- [x] Ownership takeover flow (`--takeover`) with grace timeout
- [x] Disconnected agent detection (missed heartbeats)
- [x] Graceful agent shutdown; lock release
- [x] Redis ACL/TLS configuration support
- [x] Path sandboxing for FS/OS tools

### Phase 12 — History & summaries polish ✅
- [x] Implement summarization compaction strategy
- [x] Reconstruct ctx from summaries + tail on agent restart
- [x] `/clearhistory` destructive flow with typed confirmation

### Phase 13 — Packaging & publish ✅
- [x] Ensure `pyproject.toml` is correct; `ateam` package imports cleanly
- [x] Add `deploy_to_pypi.py` and document env vars for API token
- [x] `flit build` and dry-run; verify wheel/metadata
- [x] Tag & `python deploy_to_pypi.py` to publish

### Phase 14 — Tests & docs ✅
- [x] Unit tests across config, identity, locks, queue, history, prompts, KB
- [x] Integration tests: attach/converse/detach; offload; KB copy; duplicate prevention
- [x] Snapshot tests of Console output (plain & panes); TAB autocomplete behavior
- [x] Update `README.md` with tutorial, quick start, examples
- [x] Ensure fail-fast policy

---

## API Reference

### Core Data Types

```python
# ateam/mcp/contracts.py
from dataclasses import dataclass
from typing import Literal, Optional, List, Dict, Any, Tuple

AgentId = str  # "project/agent"
DocId = str
Scope = Literal["agent", "project", "user"]
State = Literal["running", "idle", "busy", "disconnected"]

@dataclass
class AgentInfo:
    id: AgentId
    name: str
    project: str
    model: str
    cwd: str
    host: str
    pid: int
    started_at: str
    state: State
    ctx_pct: float = 0.0

@dataclass
class TailEvent:
    type: Literal["token", "tool", "warn", "error", "task.start", "task.end"]
    text: Optional[str] = None
    name: Optional[str] = None           # tool name
    input: Optional[Dict[str, Any]] = None
    msg: Optional[str] = None
    trace: Optional[str] = None
    id: Optional[str] = None             # task id
    prompt_id: Optional[str] = None
    ok: Optional[bool] = None
    model: Optional[str] = None

@dataclass
class QueueItem:
    id: str
    text: str
    source: Literal["console", "local"]
    ts: float

@dataclass
class Turn:
    ts: float
    role: Literal["user", "assistant", "tool"]
    source: Literal["console", "local", "system"]
    content: str
    tokens_in: int
    tokens_out: int
    tool_calls: Optional[List[Dict[str, Any]]] = None
```

### Error Handling

```python
# ateam/util/types.py
from dataclasses import dataclass
from typing import Generic, TypeVar, Optional, Dict, Any

T = TypeVar("T")

@dataclass
class ErrorInfo:
    code: str         # e.g., "redis.unavailable", "ownership.denied"
    message: str
    detail: Optional[Dict[str, Any]] = None

@dataclass
class Result(Generic[T]):
    ok: bool
    value: Optional[T] = None
    error: Optional[ErrorInfo] = None
```

### Key Classes

#### ConsoleApp
```python
class ConsoleApp:
    def __init__(self, redis_url: str, use_panes: bool = False) -> None: ...
    def run(self) -> None: ...
    def shutdown(self) -> None: ...
    def attach(self, agent_id: AgentId, takeover: bool = False) -> Result[AgentSession]: ...
    def detach(self, agent_id: Optional[AgentId] = None) -> Result[None]: ...
    def current_session(self) -> Optional[AgentSession]: ...
```

#### AgentApp
```python
class AgentApp:
    def __init__(self, redis_url: str, cwd: str, name_override: str = "", project_override: str = "") -> None: ...
    def run(self) -> Result[None]: ...
    def shutdown(self) -> Result[None]: ...
```

#### MCPServer
```python
class MCPServer:
    def __init__(self, redis_url: str, agent_id: str) -> None: ...
    def register_tool(self, name: str, fn: Callable[..., Any]) -> None: ...
    def emit(self, event: TailEvent) -> Result[None]: ...
    def start(self) -> Result[None]: ...
    def stop(self) -> Result[None]: ...
```

---

## Deployment & Packaging

### PyPI Package

**`pyproject.toml`**
```toml
[build-system]
requires = ["flit_core>=3.9"]
build-backend = "flit_core.buildapi"

[project]
name = "ateam"
version = "0.1.0"
description = "CLI multi-agent runtime over MCP/Redis with Console/REPL, agent REPLs, and KB"
readme = "README.md"
requires-python = ">=3.9"
license = { file = "LICENSE" }
authors = [{ name = "Your Name", email = "you@example.com" }]
classifiers = [
  "Programming Language :: Python :: 3",
  "License :: OSI Approved :: MIT License",
  "Operating System :: OS Independent"
]
dependencies = [
  "typer>=0.12",
  "rich>=13.7",
  "textual>=0.58; platform_system!='Windows'",
  "pyyaml>=6.0",
  "redis>=5.0",
  "msgpack>=1.0",
  "prompt-toolkit>=3.0",
  "psutil>=5.9",
  "pywinpty>=2.0; platform_system=='Windows'",
]

[project.scripts]
ateam = "ateam.cli:main"
```

### Deploy Script

**`deploy_to_pypi.py`**
```python
#!/usr/bin/env python3
"""
Deploy script for publishing ateam to PyPI.

Usage:
    python deploy_to_pypi.py [--repository testpypi]

Environment variables:
    FLIT_USERNAME: PyPI username (default: __token__)
    FLIT_PASSWORD: PyPI API token
"""

import os
import subprocess
import sys
from pathlib import Path

def ensure(condition: bool, msg: str) -> None:
    if not condition:
        print(f"ERROR: {msg}")
        sys.exit(1)

def main() -> None:
    print("🚀 Starting ateam deployment...")
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        ensure(False, "pyproject.toml not found. Run from project root.")
    
    # Check if flit is available
    try:
        import flit_core  # noqa
    except ImportError:
        ensure(False, "Flit not installed. Run: pip install flit")
    
    # Get repository from command line args
    repository = "pypi"  # default
    if "--repository" in sys.argv:
        idx = sys.argv.index("--repository")
        if idx + 1 < len(sys.argv):
            repository = sys.argv[idx + 1]
    
    # Validate repository
    if repository not in ["pypi", "testpypi"]:
        ensure(False, f"Invalid repository: {repository}. Use 'pypi' or 'testpypi'")
    
    # Get credentials
    username = os.getenv("FLIT_USERNAME", "__token__")
    password = os.getenv("FLIT_PASSWORD")
    
    ensure(password, "Set FLIT_PASSWORD environment variable to your PyPI API token")
    
    print(f"📦 Building package for {repository}...")
    
    # Build the package
    try:
        subprocess.run([sys.executable, "-m", "flit", "build"], 
                      check=True, capture_output=True, text=True)
        print("✅ Package built successfully")
    except subprocess.CalledProcessError as e:
        ensure(False, f"Build failed: {e.stderr}")
    
    # Verify wheel and metadata
    dist_dir = Path("dist")
    wheels = list(dist_dir.glob("*.whl"))
    sdists = list(dist_dir.glob("*.tar.gz"))
    
    ensure(wheels, "No wheel file found in dist/")
    ensure(sdists, "No source distribution found in dist/")
    
    print(f"📋 Found {len(wheels)} wheel(s) and {len(sdists)} source distribution(s)")
    
    # Show package info
    for wheel in wheels:
        print(f"   Wheel: {wheel.name}")
    for sdist in sdists:
        print(f"   Source: {sdist.name}")
    
    # Confirm before publishing
    if repository == "pypi":
        print("\n⚠️  WARNING: Publishing to PyPI (production)")
        confirm = input("Type 'publish' to confirm: ")
        ensure(confirm == "publish", "Publishing cancelled")
    else:
        print(f"\n📤 Publishing to {repository}...")
    
    # Publish
    try:
        cmd = [sys.executable, "-m", "flit", "publish"]
        if repository == "testpypi":
            cmd.extend(["--repository", "testpypi"])
        
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Successfully published to {repository}")
        
    except subprocess.CalledProcessError as e:
        ensure(False, f"Publish failed: {e.stderr}")
    
    print(f"🎉 ateam successfully deployed to {repository}!")
    
    if repository == "testpypi":
        print("\nTo install from TestPyPI:")
        print("pip install --index-url https://test.pypi.org/simple/ ateam")
    else:
        print("\nTo install from PyPI:")
        print("pip install ateam")

if __name__ == "__main__":
    main()
```

### Installation

```bash
# Install from PyPI
pip install ateam

# Install from source
git clone https://github.com/GreenFuze/ATeam.git
cd ATeam
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

---

## Security & Best Practices

### Security Model

- **Asset**: user files under `cwd`, secrets in env, Redis contents
- **Adversary**: malicious prompt/tool call trying to exfiltrate or delete data
- **Controls**:
  - FS sandbox + whitelist only
  - Tool allow/deny lists per agent; deny by default any unknown tool
  - Secrets redaction in stream/logs (regex)
  - Redis authentication (ACL) + TLS option
  - Explicit confirmations for offload/creation and `--unsafe` operations

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ATEAM_REDIS_URL` | Redis URL for MCP | `redis://127.0.0.1:6379/0` |
| `ATEAM_LOG_LEVEL` | `debug\|info\|warn\|error` | `info` |
| `ATEAM_EDITOR` | Editor for `/sys edit` | `$EDITOR` |
| `ATEAM_HISTORY_MAX` | Max history bytes before rotation | `50_000_000` |
| `ATEAM_SUMMARY_K` | Max summaries to keep | `200` |
| `ATEAM_FS_WHITELIST` | Extra semi-colon separated whitelisted paths | *(empty)* |

### Error Codes

| Code | Meaning | Common cause | Resolution |
|------|---------|--------------|------------|
| `redis.unavailable` | Redis not reachable | Wrong URL, server down | Check `ATEAM_REDIS_URL`, service status |
| `ownership.denied` | Another console owns writer | Attached elsewhere | Use `--takeover` or detach from other console |
| `agent.not_found` | Registry has no such id | Typo, agent offline | `/ps` again; check heartbeats |
| `duplicate.instance` | Single-instance lock held | Another identical agent running | Kill other or use different Redis |
| `config.invalid` | Bad YAML or schema | Missing fields | Fix YAML; run schema validator |
| `prompt.protected_violation` | Overlay edit touched protected block | Manual edit | Revert protected region |
| `kb.ingest.denied` | Path outside sandbox | Security policy | Whitelist path or move file |
| `tool.denied` | Tool not in allow-list | Misconfig | Add tool to allow-list in agent.yaml |
| `timeout` | RPC timed out | Long-running tool | Increase timeout or check agent logs |

---

## Troubleshooting

### Common Issues

**I attach but see no output.**
- Check heartbeats (`/ps`) and ensure `mcp:tail:*` events are arriving (enable debug tail)

**`duplicate.instance` on startup.**
- Another agent with same `project/name` is registered on this Redis. Stop it or use another Redis db

**TAB completion doesn't work on Windows.**
- Ensure terminal is VT-enabled (Windows Terminal or recent PowerShell), and `prompt-toolkit` is installed

**Ownership denial loop.**
- Stale owner key. Use `/attach --takeover`; check Redis clock skew

**PTY deadlock on Windows.**
- ConPTY handle not drained. Ensure reader thread runs even when no subscribers

### Performance Tuning

| Setting | Default | Description |
|---------|---------|-------------|
| `TAIL_COALESCE_MS` | 50 | Coalesce token events within this window |
| `OS_EXEC_PARTIAL_FLUSH_MS` | 40 | Flush PTY buffer even if line incomplete |
| `HISTORY_MAX_BYTES` | 50 MiB | Rotate history when exceeding this size |
| `SUMMARY_TARGET_TOKENS` | 400 | Target size per summary |
| `CONSOLE_RPC_TIMEOUT` | 15s | Default RPC timeout |
| `OWNERSHIP_TAKEOVER_GRACE` | 2s | Wait before takeover is final |

### Quickstart

**Start Console**
```bash
ateam console --redis redis://127.0.0.1:6379/0
# Press F1 to open palette. None yet? Run /agent new
```

**Create first agent**
```bash
/agent new
# Wizard asks: project, name, cwd, model, system_base.md, KB seeds
# Confirm → spawns locally and waits for heartbeat
/attach myproj/zeus
Hello Zeus, initialize the repo.
/ctx
/sys show
# Add an overlay line:
# Prefer concise step-by-step plans.
```

**Offload to fresh agent**
```bash
/offload
# Review proposal (name, cwd, model, selected KB doc IDs)
# Confirm → spawns new agent (or prints remote command)
/attach myproj/builder
```

**Selective KB copy**
```bash
/kb copy-from myproj/research --ids doc_abc123,doc_def456
```

**Reload system prompt**
```bash
/reloadsysprompt
```

**Clear history (irreversible)**
```bash
/clearhistory
# "Type 'myproj/zeus' to confirm:"
```

---

## Glossary

- **Agent (process)** — autonomous worker exposing MCP tools over Redis; owns its REPL
- **Console** — central CLI/TUI that attaches to agents, sends input, and renders streams
- **MCP** — Model Context Protocol (here: JSON/RPC-like over Redis pub/sub)
- **Owner** — the single Console session with write privileges to an agent
- **Prompt overlay** — append-only text merged on top of base system prompt
- **KB** — vectorized knowledge base (per-scope) with selective ingestion/copy
- **Offload** — moving a subtask into a newly created agent with a fresh context
- **Scope** — KB storage level: agent (default), project, or user
- **Tail** — real-time event stream from agent to console
- **Tool** — sandboxed function callable by agents (fs.read, os.exec, etc.)

---

*This knowledge base represents the complete specification for the ATeam CLI multi-agent system. All phases have been implemented and tested, providing a robust foundation for autonomous agent workflows with explicit control and security.*
