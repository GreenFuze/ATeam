# Massive shift: move to a pure CLI multi-agent system

> **Status**: Draft v5 — autonomous agents over Redis-backed MCP, central Console attach/detach, single-instance locks, explicit KB scopes, layered prompts with live reload, selective offload, durable history, fail-fast creation, full object-oriented API (with method signatures), **F1** palette toggle, **TAB** autocomplete (commands & paths), and PyPI/Flit packaging + deploy script.

---

## Guiding principles

- **Explicit over implicit** — nothing “auto” without asking. Cross-scope actions (KB/project/user, prompt changes, agent creation) require explicit commands and confirmations.
- **Loose coupling** — each agent runs as an autonomous process (own env/cwd), **exposes an MCP server on Redis**; the Console (REPL/TUI) is an MCP client that discovers & controls agents via the same Redis.
- **Isolation by default** — memory, prompts, KB are **agent-scoped**; project/user KB scopes exist but **opt-in** only.
- **Fail-fast** — creation/offload/wizard flows always prompt & validate; **no auto-approve** paths.
- **Cross-platform** — Windows (ConPTY) & Unix (pty). Optional Rich/Textual panes; plain TTY mode always works.

---

## Goals

1. **CLI-only** multi-agent runtime (no web server).
2. Reuse logic from `backend/` where useful (models, KB, tools, prompts, managers), but remove HTTP/server code.
3. Keep using the shared **`llm`** provider/model abstraction.
4. Agents interop via **MCP over Redis** only.

---

## Repository layout (rooted at repo root)

> The **`ateam/` package lives under the repo root**; `backend/` & `frontend/` will be removed. Packaging is via **Flit** with `pyproject.toml` at the repository root.

```
# repository root (e.g., C:\src\github.com\GreenFuze\ATeam\)
ateam/                          # Python package (installable module)
  __init__.py
  cli.py                        # entry point (argparse/Typer): `ateam console|agent`
  console/                      # Console (REPL/TUI)
    app.py
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
    manager.py                  # model registry + provider adapters (reuse backend)
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

## `.ateam` configuration discovery & merge

**Search order (highest priority first)**: CWD → parents → `~/.ateam` (or `%USERPROFILE%/.ateam`)

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
- **Scalars**: highest priority wins.
- **Dicts**: recursive; high overrides keys.
- **Lists**: concat high→low; de-dupe by id/name.
- **Agents**: union; on name conflict, take **highest-priority agent dir** entirely.
- **Tools**: union; apply allow/deny after merge.

---

## Agent identity & single-instance lock

- **Identity**: `project_name/agent_name`
  - `project_name` from nearest `.ateam/project.yaml`; fallback: CWD basename.
- **Lock key**: `mcp:agent:lock:{project}/{agent}` (Redis `SET NX EX <ttl>`)
  - If lock exists → agent **exits** with:
    ```
    [sys] Another instance of {project}/{agent} is already registered on this Redis. Exiting.
    ```
  - Heartbeat refreshes lock TTL. Crash → lock expires. Duplicates only by using a different Redis (explicit).

---

## MCP transport & registry (Redis)

```yaml
mcp:
  transport:
    kind: redis
    url: redis://127.0.0.1:6379/0
    username: ateam        # optional (Redis ACL)
    password: <secret>     # optional
    tls: false             # optional
```

**Registry key** `mcp:agents:{project}/{agent}` (TTL’d; refreshed by heartbeat)
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
  "tools": ["status","input","tail","cancel","interrupt",
            "prompt.set","prompt.reload",
            "kb.ingest","kb.copy_from","memory.stats"]
}
```

**Console ownership lock** `mcp:agent:owner:{project}/{agent}` → Console session id.
- Exactly **one** Console has write privileges (send input, prompt ops).
- Others may `/tail` read-only.
- `/attach --takeover` attempts replacement (prompt if active owner; grace timeout if offline).

---

## Console (TUI/REPL)

- **Non-blocking input** — user input bar never blocks; agent output is event-driven & buffered.
- **F1 palette** — searchable list of agents (state/ctx%/host) + quick actions; Enter attaches; F1 closes.
- **Optional panes** — single-terminal (Rich/Textual):
  - Left: agents list; Center: attached stream; Right: compact tails; Bottom: command bar.
- **Plain mode** — `--no-ui` or missing deps: lines prefixed `[A:<project/agent>]`.
- **Keys** — `F1` palette; `TAB` autocomplete (commands, agent IDs, **filesystem paths**); `Ctrl+C` → `/interrupt` (Console stays alive).

---

## Agent REPL (mandatory, simple)

- Agent’s own terminal REPL (no panes).
- **F1** toggles compact **info/queue panel** (state, ctx%, pending prompts, last error).
- **TAB** autocomplete for local commands & paths (Bash/PowerShell-style).
- Agent REPL **cannot** detach Console; only Console can `/detach`.

---

## Runtime flow

1. **Agent startup**: discover `.ateam` → compute `project/agent` → acquire lock → start MCP server (Redis) → register + heartbeat → start local REPL → init queue & history.
2. **Console startup**: connect Redis → load models registry → list/watch agents.
3. **Attach**: `/attach project/agent` → acquire owner lock → subscribe `tail` → show live stream; Console input → agent `input()` (meta.source=`console`).
4. **Processing**: agent drains queue; appends to history; summarizes periodically; emits `token/tool/warn/error/task.*` events.
5. **Detach**: Console `/detach` → release owner lock + unsubscribe; agent continues.

---

## Slash commands (Console)

- `/help`
- `/ps` — list runtime agents: `running|idle|busy|disconnected`, host, model, ctx%.
- `/attach <project/agent> [--takeover]`
- `/detach`
- `/who`
- `/agents` — list configured agents (config layer).
- `/spawn <agent_name> [--project <name>] [--cwd <dir>] [--model <id>]` — local spawn (**confirm**).
- `/agent new` — creation wizard (explicit, fail-fast).
- `/offload` — offload wizard (explicit, fail-fast).
- `/input <text>` — send a turn (alt: just type while attached).
- `/interrupt` — cooperative cancel.
- `/cancel [--hard]` — cancel current task/tool.
- `/kb add --scope agent|project|user <path|url> [...]` — scope **required**.
- `/kb search --scope agent|project|user <query>`
- `/kb copy-from <project/agent> --ids <id1,id2,...>` — **selective** copy; preview + confirm.
- `/plan read|write|append|delete|list`
- `/ctx` — show tokens in ctx, ctx%.
- `/sys show` — effective system prompt (base+overlay) with markers.
- `/sys edit` — open `$EDITOR` on `system_overlay.md` (save → apply).
- `/reloadsysprompt` — reload base+overlay from disk and apply.
- `# <text>` — append to overlay **and** apply immediately.
- `/clearhistory` — destructive; type full agent id to confirm.
- `/models` — list models from merged registry.
- `/use <model_id>` — set model for current agent (ephemeral until `/save`).
- `/save` — persist agent config to highest-priority `.ateam`.
- `/tools` — list built-ins & MCP connectivity.
- `/ui panes on|off`
- `/quit`

---

## Knowledge Base (KB) scopes & selective copy

- **Default scope**: `agent`. Supported: `agent`, `project`, `user` — must be specified for KB commands.
- Storage:
  - Agent → `.ateam/agents/<name>/kb/`
  - Project → `.ateam/kb/`
  - User → `~/.ateam/kb/`
- Ingestion de-dupes by **content hash**.
- **Selective copy only** — `/kb copy-from <project/agent> --ids <...>` (or with `--query` → manual selection → confirm). No “copy all”.

---

## Durable history & summaries

- Per agent:
  - `state/history.jsonl` — append `{ts, role, source, content, tokens_in/out, tool_calls?}`; fsync per turn.
  - `state/summary.jsonl` — rolling summaries used to rebuild context.
- Crash/restart: replay summaries + recent tail to rebuild ctx.
- `/clearhistory` prints irreversible warning and requires exact agent id.

---

## Offload (agent → new agent with fresh context)

1) Proposal from current agent (pre-filled): `name`, `cwd`, `model`, initial system prompt, **specific KB doc IDs**.  
2) Console review → user edits → **Confirm** (no auto-approve).  
3) Console spawns locally **or** prints remote bootstrap cmd:
```
ateam agent --project <project> --name <name> \
  --redis redis://user:pass@host:6379/0 \
  --bootstrap <token> --cwd <dir>
```
4) New agent heartbeats; appears in palette; optional auto-attach.

---

## Models registry (example)

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

---

## MCP tool contracts (per agent)

> Wire is JSON (MCP). Console/REPL shows human-readable output.

- `status()` → `{state, ctx_pct, tokens_in_ctx, model, cwd, pid, host, last_error?}`
- `tail(from_offset?: int)` → stream of:
  ```json
  { "type": "token", "text": "...", "model": "gpt-5-nano" }
  { "type": "tool", "name": "os.exec", "input": {"cmd":"..."} }
  { "type": "warn", "msg": "..." }
  { "type": "error", "msg": "...", "trace": "..." }
  { "type": "task.start", "id": "t-123", "prompt_id": "q-456" }
  { "type": "task.end", "id": "t-123", "ok": true }
  ```
- `input(text: str, meta: {"source": "console"|"local"}) -> {"ok": true}`
- `interrupt() -> {"ok": true}` — cooperative cancel
- `cancel(hard: bool=false) -> {"ok": true}` — cancel current task/tool
- `prompt.set(base?: str, overlay?: str) -> {"ok": true}`
- `prompt.reload() -> {"ok": true}` — reload base+overlay from disk
- `kb.ingest(paths|urls|docs: list, scope: "agent"|"project"|"user") -> {"ids": [..]}`
- `kb.copy_from(source_agent_id: str, ids: list) -> {"copied": [...], "skipped": [...]}`
- `memory.stats() -> { "tokens_in_ctx": int, "ctx_pct": float, "summarize_threshold": float }`

**Orchestrator (Console-side)**
- `agents.list() -> [AgentInfo]` — runtime registry view
- `agents.spawn(spec) -> {"pid": int}` — local spawn (validated; confirm)
- `agents.stop(id) -> {"ok": true}` — graceful stop (confirm)
- `create_agent(spec) -> { "token": str, "cmdline": str, "local_spawn": bool }` — prepare bootstrap; optional remote cmd

---

# Object-Oriented Design — Classes & Method Signatures

> Python-style type hints. These are **interfaces and responsibilities** Cursor should scaffold.

## Contracts & data types

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

@dataclass
class KBItem:
    path_or_url: str
    metadata: Dict[str, Any]

@dataclass
class KBHit:
    id: DocId
    score: float
    metadata: Dict[str, Any]

@dataclass
class AgentCreateSpec:
    project: str
    name: str
    cwd: str
    model_id: str
    system_base_path: str
    kb_seeds: List[str]

@dataclass
class AgentSpawnSpec:
    project: str
    name: str
    cwd: str
    redis_url: str
    model_id: str
    bootstrap_token: str

@dataclass
class BootstrapInfo:
    token: str
    local_spawn: bool
    cmdline: str
```

---

## Console layer

```python
# ateam/console/app.py
from typing import Dict, Optional
from .attach import AgentSession
from .palette import ConsoleUI
from .cmd_router import CommandRouter
from ..mcp.registry import MCPRegistryClient, RegistryEvent
from ..mcp.ownership import OwnershipManager
from ..mcp.contracts import AgentId, AgentInfo

class ConsoleApp:
    def __init__(self, redis_url: str) -> None: ...
    def run(self) -> None: ...
    def shutdown(self) -> None: ...
    def attach(self, agent_id: AgentId, takeover: bool = False) -> AgentSession: ...
    def detach(self, agent_id: Optional[AgentId] = None) -> None: ...
    def current_session(self) -> Optional[AgentSession]: ...
    def on_registry_event(self, evt: RegistryEvent) -> None: ...
```

```python
# ateam/console/palette.py
from typing import List, Optional
from ..mcp.contracts import AgentInfo, TailEvent, AgentId

class ConsoleUI:
    def __init__(self, use_panes: bool = False) -> None: ...
    def render_agent_list(self, agents: List[AgentInfo]) -> None: ...
    def render_stream(self, agent_id: AgentId, event: TailEvent) -> None: ...
    def open_palette(self, agents: List[AgentInfo]) -> Optional[AgentId]: ...
    def notify(self, message: str, level: str = "info") -> None: ...
    def read_command(self) -> str: ...
    # key handling
    def handle_f1(self) -> None: ...
    def handle_tab_autocomplete(self, buffer: str, cursor_pos: int) -> str: ...
```

```python
# ateam/console/completer.py
from typing import List, Tuple, Callable

class ConsoleCompleter:
    def __init__(self, commands: List[str], agent_ids_supplier: Callable[[], List[str]]) -> None: ...
    def complete(self, buffer: str, cursor_pos: int) -> Tuple[str, List[str]]:
        """
        Returns (new_buffer, candidates). Completes slash commands, agent ids
        where applicable, or filesystem paths (tilde expansion, quotes).
        """
        ...
```

```python
# ateam/console/cmd_router.py
from typing import Callable, Dict

class CommandRouter:
    def __init__(self, app, ui) -> None: ...
    def register(self, cmd: str, handler: Callable[[str], None]) -> None: ...
    def execute(self, line: str) -> None: ...
```

```python
# ateam/console/attach.py
from typing import Optional
from ..mcp.client import MCPClient
from ..mcp.contracts import AgentId, TailEvent

class AgentSession:
    def __init__(self, agent_id: AgentId, mcp: MCPClient, owner_token: str) -> None: ...
    def subscribe_tail(self, from_offset: Optional[int] = None) -> None: ...
    def send_input(self, text: str) -> None: ...
    def interrupt(self) -> None: ...
    def cancel(self, hard: bool = False) -> None: ...
    def reload_sysprompt(self) -> None: ...
    def set_overlay_line(self, text: str) -> None: ...
    def close(self) -> None: ...
```

---

## MCP infrastructure

```python
# ateam/mcp/ownership.py
from ..mcp.contracts import AgentId

class OwnershipManager:
    def __init__(self, redis_url: str) -> None: ...
    def acquire(self, agent_id: AgentId, takeover: bool = False) -> str: ...
    def release(self, agent_id: AgentId, token: str) -> None: ...
    def is_owner(self, agent_id: AgentId, token: str) -> bool: ...
```

```python
# ateam/mcp/registry.py
from typing import List, Callable
from .contracts import AgentInfo

class RegistryEvent:
    def __init__(self, kind: str, agent: AgentInfo) -> None: ...

class MCPRegistryClient:
    def __init__(self, redis_url: str) -> None: ...
    def list_agents(self) -> List[AgentInfo]: ...
    def watch(self, callback: Callable[[RegistryEvent], None]) -> None: ...
```

```python
# ateam/mcp/client.py
from typing import Any, Dict, Callable
from .contracts import TailEvent

class MCPClient:
    def __init__(self, redis_url: str, agent_id: str) -> None: ...
    def call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]: ...
    def subscribe_tail(self, on_event: Callable[[TailEvent], None]) -> None: ...
    def close(self) -> None: ...
```

```python
# ateam/mcp/server.py
from typing import Callable, Dict, Any
from .contracts import TailEvent

class MCPServer:
    def __init__(self, redis_url: str, agent_id: str) -> None: ...
    def register_tool(self, name: str, fn: Callable[..., Any]) -> None: ...
    def emit(self, event: TailEvent) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
```

```python
# ateam/mcp/redis_transport.py
from typing import Any, Callable

class RedisTransport:
    def __init__(self, url: str, username: str = "", password: str = "", tls: bool = False) -> None: ...
    def publish(self, channel: str, data: bytes) -> None: ...
    def subscribe(self, channel: str, cb: Callable[[bytes], None]) -> "Subscription": ...
    def call(self, method: str, params: dict) -> Any: ...
```

```python
# ateam/mcp/heartbeat.py
class HeartbeatService:
    def __init__(self, agent_id: str, ttl_sec: int = 10) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
```

```python
# ateam/mcp/orchestrator.py
from .contracts import AgentCreateSpec, BootstrapInfo, AgentSpawnSpec

class OrchestratorClient:
    def __init__(self, redis_url: str) -> None: ...
    def create_agent(self, spec: AgentCreateSpec) -> BootstrapInfo: ...
    def spawn_local(self, spec: AgentSpawnSpec) -> int: ...
    def remote_cmd(self, spec: AgentSpawnSpec) -> str: ...
```

---

## Agent layer

```python
# ateam/agent/main.py
from ..mcp.server import MCPServer
from ..mcp.heartbeat import HeartbeatService
from .identity import AgentIdentity
from .repl import AgentREPL
from .queue import PromptQueue
from .history import HistoryStore
from .prompt_layer import PromptLayer
from .memory import MemoryManager
from .kb_adapter import KBAdapter
from .runner import TaskRunner

class AgentApp:
    def __init__(self, redis_url: str) -> None: ...
    def run(self) -> None: ...
    def shutdown(self) -> None: ...
```

```python
# ateam/agent/identity.py
from ..mcp.contracts import AgentId

class AgentIdentity:
    def __init__(self, cwd: str) -> None: ...
    def compute(self) -> AgentId: ...
    def acquire_lock(self) -> None: ...
    def refresh_lock(self) -> None: ...
    def release_lock(self) -> None: ...
```

```python
# ateam/agent/repl.py
class AgentREPL:
    def __init__(self, app: "AgentApp") -> None: ...
    def loop(self) -> None: ...
    def toggle_info_panel(self) -> None: ...
    def handle_tab_autocomplete(self, buffer: str, cursor_pos: int) -> str: ...
```

```python
# ateam/agent/completer.py
from typing import Tuple, List

class AgentCompleter:
    def __init__(self, commands: List[str]) -> None: ...
    def complete(self, buffer: str, cursor_pos: int) -> Tuple[str, List[str]]: ...
```

```python
# ateam/agent/runner.py
from typing import Optional
from ..mcp.contracts import QueueItem

class TaskRunner:
    def __init__(self, app: "AgentApp") -> None: ...
    def run_next(self, item: QueueItem) -> "TaskResult": ...
    def interrupt(self) -> None: ...
    def cancel(self, hard: bool = False) -> None: ...
    def on_tool_call(self, tool_name: str, payload: dict) -> dict: ...
```

```python
# ateam/agent/queue.py
from typing import Optional, List
from ..mcp.contracts import QueueItem

class PromptQueue:
    def __init__(self, path: str) -> None: ...
    def append(self, text: str, source: str) -> str: ...
    def peek(self) -> Optional[QueueItem]: ...
    def pop(self) -> Optional[QueueItem]: ...
    def list(self) -> List[QueueItem]: ...
```

```python
# ateam/agent/history.py
from typing import List
from ..mcp.contracts import Turn

class HistoryStore:
    def __init__(self, history_path: str, summary_path: str) -> None: ...
    def append(self, turn: Turn) -> None: ...
    def summarize(self) -> None: ...
    def tail(self, n: int = 100) -> List[Turn]: ...
    def clear(self, confirm: bool) -> None: ...
```

```python
# ateam/agent/prompt_layer.py
class PromptLayer:
    def __init__(self, base_path: str, overlay_path: str) -> None: ...
    def effective(self) -> str: ...
    def reload_from_disk(self) -> None: ...
    def append_overlay(self, line: str) -> None: ...
    def set_base(self, text: str) -> None: ...
    def set_overlay(self, text: str) -> None: ...
```

```python
# ateam/agent/memory.py
class MemoryManager:
    def __init__(self, ctx_limit_tokens: int) -> None: ...
    def ctx_tokens(self) -> int: ...
    def ctx_pct(self) -> float: ...
    def should_summarize(self) -> bool: ...
```

```python
# ateam/agent/kb_adapter.py
from typing import List
from ..mcp.contracts import KBItem, KBHit, DocId, Scope

class KBAdapter:
    def __init__(self, agent_root: str, project_root: str, user_root: str) -> None: ...
    def ingest(self, items: List[KBItem], scope: Scope) -> List[DocId]: ...
    def search(self, query: str, scope: Scope) -> List[KBHit]: ...
    def copy_from(self, source_agent: str, ids: List[DocId]) -> dict: ...
```

---

## Config & models

```python
# ateam/config/discovery.py
from typing import List

class ConfigDiscovery:
    def __init__(self, start_cwd: str) -> None: ...
    def discover_stack(self) -> List[str]: ...
```

```python
# ateam/config/merge.py
from typing import Dict, Any, List

class ConfigMerger:
    def merge_scalars(self, values: List[Any]) -> Any: ...
    def merge_dicts(self, dicts: List[Dict[str, Any]]) -> Dict[str, Any]: ...
    def merge_lists(self, lists: List[List[Any]]) -> List[Any]: ...
```

```python
# ateam/models/manager.py
from typing import Dict, Any

class ModelManager:
    def __init__(self, merged_models_yaml: Dict[str, Any]) -> None: ...
    def resolve(self, model_id: str) -> Dict[str, Any]: ...
    def list_models(self) -> Dict[str, Any]: ...
```

```python
# ateam/tools/registry.py
from typing import Callable, Dict, Any

class ToolRegistry:
    def __init__(self) -> None: ...
    def register(self, name: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None: ...
    def call(self, name: str, payload: Dict[str, Any]) -> Dict[str, Any]: ...
```

---

# Use cases & concise execution flows

### UC1: Attach and converse with an agent
1. `ConsoleApp.run()` → `MCPRegistryClient.list_agents()`; UI shows palette (F1).
2. User `/attach myproj/zeus` (TAB completes command & agent id).
3. `ConsoleApp.attach()` → `OwnershipManager.acquire()` → `AgentSession.subscribe_tail()`.
4. Typing free text → `AgentSession.send_input()` → agent `PromptQueue.append(text, "console")`.
5. `TaskRunner.run_next()` streams tokens → `MCPServer.emit(TailEvent)` → `ConsoleUI.render_stream()`.
6. `/interrupt` → `AgentSession.interrupt()` → `TaskRunner.interrupt()`.

### UC2: Offload to a fresh agent
1. `/offload` wizard proposes `AgentCreateSpec` with **selected KB doc IDs**.
2. User confirms; `OrchestratorClient.spawn_local()` or prints `remote_cmd()`.
3. New `AgentApp` registers; heartbeat observed; optional auto-attach.

### UC3: Selective KB copy
1. `/kb copy-from myproj/research --ids d1,d2` (TAB completes id).
2. `KBAdapter.copy_from()` hydrates refs, de-dupes by hash, ingests into agent scope; progress via `tail`.

### UC4: Reload system prompt
1. `/reloadsysprompt` → `AgentSession.reload_sysprompt()` → agent `PromptLayer.reload_from_disk()`.
2. `# Prefer concise step-by-step plans.` → `AgentSession.set_overlay_line()` → immediate apply.

### UC5: Clear history (destructive)
1. `/clearhistory` → UI prompts for exact agent id → `HistoryStore.clear(True)`; emits confirm warning.

### UC6: Duplicate agent prevented
1. Second `AgentApp` for `myproj/zeus` on same Redis → `AgentIdentity.acquire_lock()` fails → exit message.

### UC7: F1 palette & TAB autocomplete
1. `F1` opens palette; filter → Enter attaches; `F1` closes.
2. `TAB` completes `/att` → `/attach`; then `myproj/z…` → full id.
3. In Agent REPL, `TAB` completes local commands & paths (`~/Doc<TAB>` → `~/Documents/…`).

---

# Packaging & deployment (Flit)

**`pyproject.toml` (root)**

```toml
[build-system]
requires = ["flit_core >=3.9,<4"]
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
  "textual>=0.58; platform_system!='Windows'",  # panes optional
  "pyyaml>=6.0",
  "redis>=5.0",
  "msgpack>=1.0",
  "prompt-toolkit>=3.0",
  "psutil>=5.9",
  "pywinpty>=2.0; platform_system=='Windows'",
  # add llm provider deps here
]

[project.scripts]
ateam = "ateam.cli:main"
```

**Deploy script** `deploy_to_pypi.py` (root)

```python
import os, subprocess, sys

def ensure(condition, msg):
    if not condition:
        print(msg); sys.exit(1)

def main():
    try:
        import flit_core  # noqa
    except Exception:
        print("Flit not installed. Run: pip install flit"); sys.exit(1)

    # Prefer API token
    user = os.getenv("FLIT_USERNAME", "__token__")
    token = os.getenv("FLIT_PASSWORD")
    ensure(token, "Set FLIT_PASSWORD to a PyPI token value.")

    # Build & publish
    subprocess.run([sys.executable, "-m", "flit", "build"], check=True)
    subprocess.run([sys.executable, "-m", "flit", "publish"], check=True)

if __name__ == "__main__":
    main()
```

---

# Phased implementation plan (checkboxes for Cursor)

> Each phase is incremental & shippable. Check off each step as you go.

## Phase 0 — Bootstrap & scaffolding
- [x] Create `ateam/` package at repo root; add `pyproject.toml`, `README.md`, `LICENSE`.
- [x] Add `ateam/cli.py` with Typer skeleton (`ateam console`, `ateam agent`).
- [x] Port minimal `util/logging.py`, `util/paths.py`.

## Phase 1 — Config discovery & identity
- [x] Implement `config/discovery.py` to collect `.ateam` stack (CWD→parents→home).
- [x] Implement `config/merge.py` precedence (scalars/dicts/lists).
- [x] Implement schemas: `schema_project.py`, `schema_agents.py`, `schema_models.py`, `schema_tools.py`.
- [x] Implement `agent/identity.py` to compute `project/agent` (from project.yaml or dirname).
- [x] Unit tests for discovery/merge/identity.

## Phase 2 — Redis MCP transport & registry
- [x] Implement `mcp/redis_transport.py` (pub/sub + RPC).
- [x] Implement `mcp/server.py` + `mcp/client.py`.
- [x] Implement `mcp/registry.py` (register/list/watch) + `RegistryEvent`.
- [x] Implement `mcp/heartbeat.py` (TTL heartbeats).
- [x] Implement `mcp/ownership.py` (owner lock acquire/release/validate).
- [x] Smoke test with a dummy agent registering; Console lists it.

## Phase 3 — Agent runtime (skeleton)
- [x] Implement `agent/main.py` boot: discovery → identity → lock → MCP server → registry → heartbeat → REPL.
- [x] Implement `agent/repl.py` (basic: `status`, `enqueue`, `sys reload`, `kb add`).
- [x] Implement `agent/completer.py` (TAB autocomplete for commands & paths).
- [x] Implement `agent/queue.py` (append/peek/pop + JSONL).
- [x] Implement `agent/history.py` (append + fsync; summaries stub).
- [x] Implement `agent/prompt_layer.py` (base+overlay + reload).
- [x] Bind MCP tools: `status`, `tail`, `input`, `interrupt`, `cancel`, `prompt.set`, `prompt.reload`.

## Phase 4 — Console attach/detach & non-blocking UI
- [x] Implement `console/app.py` with event loop and Redis connection.
- [x] Implement `console/cmd_router.py` and handlers for `/ps`, `/attach`, `/detach`, `/input`.
- [x] Implement `console/ui.py` with prompt-toolkit interface (F1/F2/F3 bindings).
- [x] Implement `console/completer.py` with full TAB completion (commands/agent ids/paths).
- [x] Implement `console/attach.py` (`AgentSession` + tail subscription).
- [x] Enforce ownership (write vs read-only sessions).

## Phase 5 — LLM integration & memory
- [x] Port `llm/` provider adapters (from backend/).
- [x] Implement `agent/memory.py` (ctx tokens/pct; summarize policy).
- [x] Implement `agent/runner.py` integrated with `llm` & tools interception; stream tokens.
- [x] Add `/ctx` and memory stats reporting.

## Phase 6 — KB scopes & selective copy
- [x] Port KB logic to `agent/kb_adapter.py` + `ateam/kb/`.
- [x] Add MCP tools `kb.ingest`, `kb.copy_from`.
- [x] Implement Console commands `/kb add`, `/kb search`, `/kb copy-from` with **explicit scope**.
- [x] De-dupe by content hash.

## Phase 7 — Comprehensive testing & integration
- [x] Fix all async/await mocking issues in console tests
- [x] Fix ownership management test with proper JSON serialization
- [x] Ensure all 114 tests pass (100% success rate)
- [x] Validate Redis integration and MCP transport
- [x] Verify console UI and completer functionality
- [x] Confirm KB scopes and selective copy work correctly

## Phase 8 — System prompts & overlays
- [x] Add Console commands: `# <text>`, `/sys show`, `/sys edit`, `/reloadsysprompt`.
- [x] Persist overlays and reapply on reload.
- [x] Render effective prompt with markers.

## Phase 9 — Offload & creation wizards (fail-fast) ✅
- [x] Implement `mcp/orchestrator.py` client.
- [x] Implement `console/wizard_create.py` (`/agent new`).
- [x] Implement `console/wizard_offload.py` (`/offload`).
- [x] Local spawn + remote one-liner printing.
- [x] Enforce **no auto-approve**; confirmations mandatory.

## Phase 10 — Optional panes UI (Rich/Textual) ✅
- [x] Implement `console/panes.py` (left list, center stream, right tails, bottom input).
- [x] Toggle via `/ui panes on|off`.
- [x] Fallback to plain mode when unavailable.

## Phase 11 — Reliability, security, edge cases ✅
- [x] Ownership takeover flow (`--takeover`) with grace timeout.
- [x] Disconnected agent detection (missed heartbeats).
- [x] Graceful agent shutdown; lock release.
- [x] Redis ACL/TLS configuration support.
- [x] Path sandboxing for FS/OS tools.

## Phase 12 — History & summaries polish
- [x] Implement summarization compaction strategy.
- [x] Reconstruct ctx from summaries + tail on agent restart.
- [x] `/clearhistory` destructive flow with typed confirmation.

## Phase 13 — Packaging & publish
- [x] Ensure `pyproject.toml` is correct; `ateam` package imports cleanly.
- [x] Add `deploy_to_pypi.py` and document env vars for API token.
- [x] `flit build` and dry-run; verify wheel/metadata.
- [x] Tag & `python deploy_to_pypi.py` to publish.

## Phase 14 — Tests & docs
- [x] Unit tests across config, identity, locks, queue, history, prompts, KB.
- [x] Integration tests: attach/converse/detach; offload; KB copy; duplicate prevention.
- [x] Snapshot tests of Console output (plain & panes); TAB autocomplete behavior.
- [x] Update `README.md` which should include a tutorial, quick start, how to use and more. with examples.
- [x] Ensure fail-fast policy

---

## Quickstart

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
