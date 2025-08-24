# Appendices — Deep Design Details (continuation of Draft v5, Part 2)

> This continues the same `change.md` spec. Everything below is additive and can be appended to the previous file.

---

## Q. Complete typed interfaces (expanded signatures, returns, exceptions)

> These are scaffolding-quality interfaces for Cursor to generate concrete code.  
> All I/O that can fail returns `Result[T, ErrorInfo]`-style dicts or raises typed exceptions as noted.

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

### Q1. Console layer

```python
# ateam/console/app.py
from typing import Dict, Optional, Callable, List
from .attach import AgentSession
from .palette import ConsoleUI
from .cmd_router import CommandRouter
from ..mcp.registry import MCPRegistryClient, RegistryEvent
from ..mcp.ownership import OwnershipManager
from ..mcp.contracts import AgentId, AgentInfo
from ..util.types import Result

class ConsoleApp:
    def __init__(self, redis_url: str, use_panes: bool = False) -> None: ...
    def run(self) -> None:
        """Main event loop. Connects to Redis, sets up UI, registers handlers, and blocks until quit."""
    def shutdown(self) -> None:
        """Gracefully shutdown UI, detach sessions, close Redis clients."""
    def attach(self, agent_id: AgentId, takeover: bool = False) -> Result[AgentSession]:
        """Acquire ownership lock and attach. Errors: ownership.denied, agent.not_found"""
    def detach(self, agent_id: Optional[AgentId] = None) -> Result[None]:
        """Release ownership and unsubscribe. If agent_id is None, detach current."""
    def current_session(self) -> Optional[AgentSession]: ...
    def on_registry_event(self, evt: RegistryEvent) -> None:
        """UI refresh hook when agents join/leave or heartbeat changes state."""
```

```python
# ateam/console/palette.py
from typing import List, Optional, Tuple
from ..mcp.contracts import AgentInfo, TailEvent, AgentId

class ConsoleUI:
    def __init__(self, use_panes: bool = False) -> None: ...
    def render_agent_list(self, agents: List[AgentInfo]) -> None: ...
    def render_stream(self, agent_id: AgentId, event: TailEvent) -> None: ...
    def open_palette(self, agents: List[AgentInfo]) -> Optional[AgentId]:
        """Open F1 palette; returns selected AgentId or None if dismissed."""
    def notify(self, message: str, level: str = "info") -> None: ...
    def read_command(self) -> str:
        """Non-blocking read from input bar; returns accumulated line when Enter is pressed."""
    def handle_f1(self) -> None: ...
    def handle_tab_autocomplete(self, buffer: str, cursor_pos: int) -> str:
        """Return updated buffer with in-place completion if unique; otherwise show suggestions."""
    # helpers
    def set_status(self, text: str) -> None: ...
    def set_title(self, text: str) -> None: ...
```

```python
# ateam/console/completer.py
from typing import List, Tuple, Callable

class ConsoleCompleter:
    def __init__(self, commands: List[str], agent_ids_supplier: Callable[[], List[str]]) -> None: ...
    def complete(self, buffer: str, cursor_pos: int) -> Tuple[str, List[str]]:
        """
        Returns (new_buffer, candidates). Behavior:
        - If buffer starts with '/', complete commands.
        - If current command expects an AgentId, complete from agent_ids_supplier().
        - Else, complete filesystem path under cursor (tilde expansion, quotes).
        """
```

```python
# ateam/console/cmd_router.py
from typing import Callable, Dict
from ..util.types import Result

class CommandRouter:
    def __init__(self, app, ui) -> None: ...
    def register(self, cmd: str, handler: Callable[[str], Result[None]]) -> None:
        """Register '/cmd' → handler(line)."""
    def execute(self, line: str) -> None:
        """Dispatch '/cmd ...' or forward plain text to current session."""
```

```python
# ateam/console/attach.py
from typing import Optional, Callable
from ..mcp.client import MCPClient
from ..mcp.contracts import AgentId, TailEvent
from ..util.types import Result

class AgentSession:
    def __init__(self, agent_id: AgentId, mcp: MCPClient, owner_token: str) -> None: ...
    def subscribe_tail(self, from_offset: Optional[int] = None,
                       on_event: Optional[Callable[[TailEvent], None]] = None) -> Result[None]: ...
    def send_input(self, text: str) -> Result[None]: ...
    def interrupt(self) -> Result[None]: ...
    def cancel(self, hard: bool = False) -> Result[None]: ...
    def reload_sysprompt(self) -> Result[None]: ...
    def set_overlay_line(self, text: str) -> Result[None]: ...
    def close(self) -> Result[None]: ...
```

### Q2. MCP infrastructure

```python
# ateam/mcp/ownership.py
from ..mcp.contracts import AgentId
from ..util.types import Result

class OwnershipManager:
    def __init__(self, redis_url: str) -> None: ...
    def acquire(self, agent_id: AgentId, takeover: bool = False) -> Result[str]:
        """Return owner_token on success. Errors: ownership.held, redis.unavailable"""
    def release(self, agent_id: AgentId, token: str) -> Result[None]: ...
    def is_owner(self, agent_id: AgentId, token: str) -> bool: ...
```

```python
# ateam/mcp/registry.py
from typing import List, Callable
from .contracts import AgentInfo
from ..util.types import Result

class RegistryEvent:
    def __init__(self, kind: str, agent: AgentInfo) -> None: ...

class MCPRegistryClient:
    def __init__(self, redis_url: str) -> None: ...
    def list_agents(self) -> Result[List[AgentInfo]]: ...
    def watch(self, callback: Callable[[RegistryEvent], None]) -> Result[None]: ...
```

```python
# ateam/mcp/client.py
from typing import Any, Dict, Callable, Optional
from .contracts import TailEvent
from ..util.types import Result

class MCPClient:
    def __init__(self, redis_url: str, agent_id: str) -> None: ...
    def call(self, method: str, params: Dict[str, Any], timeout_sec: Optional[float] = 15.0) -> Result[Dict[str, Any]]: ...
    def subscribe_tail(self, on_event: Callable[[TailEvent], None]) -> Result[None]: ...
    def close(self) -> Result[None]: ...
```

```python
# ateam/mcp/server.py
from typing import Callable, Dict, Any
from .contracts import TailEvent
from ..util.types import Result

class MCPServer:
    def __init__(self, redis_url: str, agent_id: str) -> None: ...
    def register_tool(self, name: str, fn: Callable[..., Any]) -> None: ...
    def emit(self, event: TailEvent) -> Result[None]: ...
    def start(self) -> Result[None]: ...
    def stop(self) -> Result[None]: ...
```

```python
# ateam/mcp/redis_transport.py
from typing import Any, Callable, Optional
from ..util.types import Result

class RedisTransport:
    def __init__(self, url: str, username: str = "", password: str = "", tls: bool = False) -> None: ...
    def publish(self, channel: str, data: bytes) -> Result[None]: ...
    def subscribe(self, channel: str, cb: Callable[[bytes], None]) -> "Subscription": ...
    def call(self, method: str, params: dict, timeout_sec: Optional[float] = 15.0) -> Result[Any]: ...
```

```python
# ateam/mcp/heartbeat.py
from ..util.types import Result

class HeartbeatService:
    def __init__(self, agent_id: str, ttl_sec: int = 10) -> None: ...
    def start(self) -> Result[None]: ...
    def stop(self) -> Result[None]: ...
```

```python
# ateam/mcp/orchestrator.py
from .contracts import AgentCreateSpec, BootstrapInfo, AgentSpawnSpec
from ..util.types import Result

class OrchestratorClient:
    def __init__(self, redis_url: str) -> None: ...
    def create_agent(self, spec: AgentCreateSpec) -> Result[BootstrapInfo]: ...
    def spawn_local(self, spec: AgentSpawnSpec) -> Result[int]:  # pid
    def remote_cmd(self, spec: AgentSpawnSpec) -> Result[str]:   # printable cmd
```

### Q3. Agent layer

```python
# ateam/agent/main.py
from ..util.types import Result

class AgentApp:
    def __init__(self, redis_url: str, cwd: str, name_override: str = "", project_override: str = "") -> None: ...
    def run(self) -> Result[None]: ...
    def shutdown(self) -> Result[None]: ...
```

```python
# ateam/agent/identity.py
from ..mcp.contracts import AgentId
from ..util.types import Result

class AgentIdentity:
    def __init__(self, cwd: str, project_override: str = "", name_override: str = "") -> None: ...
    def compute(self) -> AgentId: ...
    def acquire_lock(self) -> Result[None]: ...
    def refresh_lock(self) -> Result[None]: ...
    def release_lock(self) -> Result[None]: ...
```

```python
# ateam/agent/repl.py
from ..util.types import Result

class AgentREPL:
    def __init__(self, app: "AgentApp") -> None: ...
    def loop(self) -> Result[None]: ...
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
from dataclasses import dataclass
from typing import Optional, Dict, Any
from ..mcp.contracts import QueueItem
from ..util.types import Result

@dataclass
class TaskResult:
    id: str
    ok: bool
    output: str
    tokens_in: int
    tokens_out: int
    tool_calls: Optional[list] = None

class TaskRunner:
    def __init__(self, app: "AgentApp") -> None: ...
    def run_next(self, item: QueueItem) -> Result[TaskResult]: ...
    def interrupt(self) -> Result[None]: ...
    def cancel(self, hard: bool = False) -> Result[None]: ...
    def on_tool_call(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]: ...
```

```python
# ateam/agent/queue.py
from typing import Optional, List
from ..mcp.contracts import QueueItem
from ..util.types import Result

class PromptQueue:
    def __init__(self, path: str) -> None: ...
    def append(self, text: str, source: str) -> Result[str]:  # returns id
    def peek(self) -> Result[Optional[QueueItem]]: ...
    def pop(self) -> Result[Optional[QueueItem]]: ...
    def list(self) -> Result[List[QueueItem]]: ...
```

```python
# ateam/agent/history.py
from typing import List
from ..mcp.contracts import Turn
from ..util.types import Result

class HistoryStore:
    def __init__(self, history_path: str, summary_path: str) -> None: ...
    def append(self, turn: Turn) -> Result[None]: ...
    def summarize(self) -> Result[None]: ...
    def tail(self, n: int = 100) -> Result[List[Turn]]: ...
    def clear(self, confirm: bool) -> Result[None]: ...
```

```python
# ateam/agent/prompt_layer.py
from ..util.types import Result

class PromptLayer:
    def __init__(self, base_path: str, overlay_path: str) -> None: ...
    def effective(self) -> str: ...
    def reload_from_disk(self) -> Result[None]: ...
    def append_overlay(self, line: str) -> Result[None]: ...
    def set_base(self, text: str) -> Result[None]: ...
    def set_overlay(self, text: str) -> Result[None]: ...
```

```python
# ateam/agent/memory.py
class MemoryManager:
    def __init__(self, ctx_limit_tokens: int, summarize_threshold: float = 0.75) -> None: ...
    def ctx_tokens(self) -> int: ...
    def ctx_pct(self) -> float: ...
    def should_summarize(self) -> bool: ...
```

```python
# ateam/agent/kb_adapter.py
from typing import List, Dict, Any
from ..mcp.contracts import KBItem, KBHit, DocId, Scope
from ..util.types import Result

class KBAdapter:
    def __init__(self, agent_root: str, project_root: str, user_root: str) -> None: ...
    def ingest(self, items: List[KBItem], scope: Scope) -> Result[List[DocId]]: ...
    def search(self, query: str, scope: Scope) -> Result[List[KBHit]]: ...
    def copy_from(self, source_agent: str, ids: List[DocId]) -> Result[Dict[str, Any]]: ...
```

### Q4. Config & models

```python
# ateam/config/discovery.py
from typing import List
from ..util.types import Result

class ConfigDiscovery:
    def __init__(self, start_cwd: str) -> None: ...
    def discover_stack(self) -> Result[List[str]]:
        """Return ordered list of .ateam dirs from CWD→parents→home (highest→lowest priority)."""
```

```python
# ateam/config/merge.py
from typing import Dict, Any, List

class ConfigMerger:
    def merge_scalars(self, values: List[Any]) -> Any: ...
    def merge_dicts(self, dicts: List[Dict[str, Any]]) -> Dict[str, Any]: ...
    def merge_lists(self, lists: List[List[Any]], key: str = "") -> List[Any]:
        """If key given, de-dupe by that item key; else naive de-dupe by value."""
```

```python
# ateam/models/manager.py
from typing import Dict, Any, List
from ..util.types import Result

class ModelManager:
    def __init__(self, merged_models_yaml: Dict[str, Any]) -> None: ...
    def resolve(self, model_id: str) -> Result[Dict[str, Any]]: ...
    def list_models(self) -> Result[Dict[str, Any]]: ...
    def default_for_agent(self, agent_name: str) -> Result[str]: ...
```

```python
# ateam/tools/registry.py
from typing import Callable, Dict, Any
from ..util.types import Result

class ToolRegistry:
    def __init__(self) -> None: ...
    def register(self, name: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None: ...
    def call(self, name: str, payload: Dict[str, Any]) -> Result[Dict[str, Any]]: ...
```

---

## R. Autocomplete algorithms (TAB) — precise behavior

### R1. Command completion (Console)
1. If buffer begins with `/` and cursor is within the command token:
   - Collect known commands from `CommandRouter`.
   - Find longest common prefix across matches; insert inline if unique.
   - If multiple matches:
     - First TAB: show inline hint (ghost text or list beneath).
     - Second TAB: cycle through candidates; wrap around.

2. If current command expects an `AgentId` (e.g., `/attach`, `/kb copy-from`):
   - Use `MCPRegistryClient.list_agents()` → `[project/agent]`.
   - Same prefix/cycle rules as above.

3. Else treat token under cursor as **filesystem path**:
   - Expand `~` (user home), respect quotes and spaces.
   - Windows: support `C:\...`, UNC `\\host\share\...`; Unix: `/...`.
   - If a single match is a directory, append path separator.
   - Keep original quoting if present.

### R2. Agent REPL completion
- Only local commands + paths; **no** AgentId completion.
- Same cycle rules; same path semantics.

---

## S. Redis lock & ownership — reference pseudocode

```python
# single-instance lock (AgentIdentity.acquire_lock)
key = f"mcp:agent:lock:{project}/{agent}"
ok = redis.set(key, f"{host}:{pid}", nx=True, ex=ttl)
if not ok:
    raise DuplicateInstance("Another instance is registered on this Redis")

# heartbeat refresh
redis.expire(key, ttl)

# console ownership
owner_key = f"mcp:agent:owner:{project}/{agent}"
if takeover:
    redis.set(owner_key, session_id)  # replace
else:
    ok = redis.set(owner_key, session_id, nx=True)
    if not ok:
        raise OwnershipDenied("Write owner already set")
```

---

## T. Error handling & logging

- **Error classes**: `DuplicateInstance`, `OwnershipDenied`, `TransportError`, `ConfigError`, `ToolError`, `ModelError`.
- **Logging format** (JSON):
```json
{"ts":"2025-08-21T11:42:00.123Z","lvl":"INFO","where":"agent.runner","msg":"task.start","agent":"myproj/zeus","task":"t-123","qid":"q-456"}
```
- Redaction: apply regex-list to `msg`/`detail` before emit (e.g., API keys, tokens).
- Levels: `DEBUG, INFO, WARN, ERROR`.

---

## U. YAML validation (JSON Schema excerpts)

### `agent.yaml` schema (excerpt)
```json
{
  "type": "object",
  "required": ["name", "model", "prompt"],
  "properties": {
    "name": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
    "model": {"type": "string"},
    "prompt": {
      "type": "object",
      "required": ["base"],
      "properties": {
        "base": {"type": "string"},
        "overlay": {"type": "string"}
      }
    },
    "scratchpad": {
      "type": "object",
      "properties": {
        "max_iterations": {"type": "integer", "minimum": 1},
        "score_lower_bound": {"type": "number", "minimum": 0.0, "maximum": 1.0}
      }
    },
    "tools": {
      "type": "object",
      "properties": {
        "allow": {"type": "array", "items": {"type": "string"}},
        "deny": {"type": "array", "items": {"type": "string"}}
      }
    }
  }
}
```

---

## V. LLM provider abstraction (streaming API)

```python
# ateam/llm/base.py
from typing import Iterable, Dict, Any, Protocol

class StreamChunk(Protocol):
    text: str
    tokens: int

class LLMClient(Protocol):
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Non-streaming completion. Returns dict with 'text', 'usage'."""
    def stream(self, prompt: str, **kwargs) -> Iterable[StreamChunk]:
        """Streaming generator of chunks. Yields until complete."""
```

**Adapters** implement `LLMClient` (e.g., `OpenAIClient`, `LmStudioClient`).  
`TaskRunner` prefers `stream()` and maps chunks to `TailEvent(type="token")`.

---

## W. Tool calling protocol

- Tool call envelope (agent → server):
```json
{
  "name": "fs.read",
  "args": {"path": "README.md"},
  "meta": {"agent": "myproj/zeus", "trace_id": "abc123"}
}
```
- Result:
```json
{"ok": true, "result": {"content": "..."}}  # or {"ok": false, "error": {"code": "...", "message": "..."}}
```
- Restrictions:
  - `fs.*` confined to agent `cwd` subtree unless config explicitly whitelists external paths.
  - `os.exec` defaults to PTY (Unix) / ConPTY (Windows) for interactive processes.

---

## X. PTY/ConPTY handling (cross-platform)

- **Unix**: use `pty` + non-blocking reads; forward stdout/stderr → tokenized events if needed.
- **Windows**: use `pywinpty` (ConPTY) with overlapped I/O.
- Both paths expose unified API to `tools/builtin/os.py:exec()`.

---

## Y. Configuration precedence — precise algorithm

1. Walk up from `cwd` to root, collecting every directory containing `.ateam/`.
2. Append user directory (`~/.ateam`).
3. Order: `cwd` closest → farthest parent → user (lowest).
4. For each config file (`project.yaml`, `models.yaml`, `tools.yaml`, `agents/*`), load in that order and **merge**:
   - Scalar: keep **first** seen (highest priority).
   - Dict: deep merge (higher overrides keys).
   - List: prepend high, then append lower; de-dupe by `id`/`name` if present.
   - Agents: if the same agent name appears in multiple layers → **take the entire highest-priority directory** and ignore lower.

---

## Z. Performance instrumentation

- `tail_latency_ms` (token emit → console render) p95 < 100ms.
- `ownership_op_ms` p95 < 50ms.
- `queue_io_ms` (append/pop fsync) p95 < 10ms.
- Emit metrics via `util/logging.py` or optional `prometheus_client` if configured.

---

## AA. CI & Quality Gates

- **Linters**: `ruff`, `mypy` (strict on `ateam/*`), `black`.
- **CI steps**:
  - [ ] lint
  - [ ] type-check
  - [ ] unit tests
  - [ ] integration tests (Redis-in-docker)
  - [ ] build wheel (`flit build`)
  - [ ] (optional) publish to TestPyPI on `main` tags
- **Pre-commit**: hooks for black/ruff/mypy.

---

## AB. Release & TestPyPI

- Test release:
```bash
python -m flit build
python -m flit publish --repository testpypi
# env: FLIT_USERNAME="__token__", FLIT_PASSWORD="<testpypi-token>"
```
- Promote to PyPI by rerunning publish with PyPI token after version bump.

---

## AC. Additional use cases

### AC1. Agent-local inbox scan to enqueue tasks
1. User drops `.txt` requests into `.ateam/agents/<name>/inbox/`.
2. Agent REPL `inbox scan` finds files and offers to enqueue each (explicit confirm).
3. On confirm, agent moves file to `processed/` and appends text as queue items.

### AC2. Ownership takeover when previous console is stale
1. Console A holds owner but disconnects (network).
2. Console B `/attach --takeover` → writes owner key; A receives `warn` event on reconnect and becomes read-only.

### AC3. Multi-host fleet
1. Agents run on Docker hosts A/B; Console on host C; all share `redis://cluster/0`.
2. Palette shows hostnames; `/ps` groups by host; attach works transparently.

---

## AD. Test cases (high-value)

- **Identity & lock**
  - [x] Two agents same id on same Redis → second exits with code 11.
- **Ownership**
  - [x] Attach when unowned → success; write operations accepted.
  - [x] Second attach without takeover → denied.
  - [x] Takeover → old becomes read-only; new can write.
- **Queue & history**
  - [x] Append, peek, pop roundtrip; fsync durability.
  - [x] Crash & restart → ctx rebuild from summaries + tail.
- **Prompts**
  - [x] `/reloadsysprompt` applies new overlay.
  - [x] `# <line>` appends to overlay & effective prompt reflects it.
- **KB**
  - [x] `kb.ingest` de-dupes by hash.
  - [x] `kb.copy_from` only copies selected ids.
- **Autocomplete**
  - [x] `/att<TAB>` → `/attach`.
  - [x] Path completion with spaces and quotes (Windows/Unix).
- **Panes off**
  - [x] `--no-ui` works in dumb terminals.
- **Security**
  - [x] Secrets redaction in token stream & logs.

---

## AE. Developer ergonomics

- `ateam console --no-ui` for SSH or CI logs.
- `ATEAM_REDIS_URL` env var picked up by both console and agents.
- `ATEAM_EDITOR` overrides `$EDITOR` for `/sys edit`.

---

## AF. Future relaxations (explicit → optional)

- Auto-summarize can become implicit when `ctx_pct > 90%` (behind `--auto-summarize` flag).
- Console can optionally re-attach to last session on startup (behind `--resume-last`).
- Agents may auto-register prompts from `prompts/` without explicit `/sys` (feature flag).

---

## AG. Minimal stubs to unblock implementation

> Cursor can generate these files with TODOs, then iterate.

- `ateam/cli.py` — Typer app with `console` and `agent` commands.
- `ateam/mcp/redis_transport.py` — wrap `redis` client; pub/sub and RPC pattern with request ids.
- `ateam/mcp/server.py` — register tools; expose RPC handlers.
- `ateam/mcp/client.py` — call/subscribe helpers with timeouts.
- `ateam/agent/queue.py` — JSONL append/pop with file locks.
- `ateam/agent/history.py` — JSONL append; (TODO) summaries.
- `ateam/agent/prompt_layer.py` — base+overlay merge; reload.
- `ateam/console/completer.py` — command/agent/path completion.
- `deploy_to_pypi.py` — flit wrapper (as in Packaging section).

---

## AH. Final guardrails (re-affirmed)

- **Explicit over implicit** in creation, offload, KB copy, prompt changes.
- **Single instance per identity per Redis** enforced; duplicates exit.
- **Scopes**: `agent` is default; `project`/`user` require explicit flag.
- **F1** opens palette; **TAB** only completes; **no hidden actions** bound to TAB.
- **Console owns write**; agents cannot detach Console.

---
