# Appendices — Deep Design Details (continuation of Draft v5)

> This continues the same `change.md` spec. Everything below is additive and can be appended to the previous file.

---

## A. Class & Sequence Diagrams (Mermaid)

### A1. High-level class diagram (Console, Agent, MCP)

```mermaid
classDiagram
    direction LR

    class ConsoleApp {
      +ConsoleApp(redis_url: str)
      +run() -> None
      +shutdown() -> None
      +attach(agent_id: AgentId, takeover: bool=False) -> AgentSession
      +detach(agent_id: Optional[AgentId]=None) -> None
      +current_session() -> Optional[AgentSession]
      +on_registry_event(evt: RegistryEvent) -> None
      -registry: MCPRegistryClient
      -ui: ConsoleUI
      -router: CommandRouter
      -ownership: OwnershipManager
      -sessions: Dict[AgentId, AgentSession]
    }

    class ConsoleUI {
      +ConsoleUI(use_panes: bool=False)
      +render_agent_list(agents: List~AgentInfo~) -> None
      +render_stream(agent_id: AgentId, event: TailEvent) -> None
      +open_palette(agents: List~AgentInfo~) -> Optional[AgentId]
      +notify(message: str, level: str="info") -> None
      +read_command() -> str
      +handle_f1() -> None
      +handle_tab_autocomplete(buffer: str, cursor_pos: int) -> str
      -completer: ConsoleCompleter
    }

    class ConsoleCompleter {
      +ConsoleCompleter(commands: List~str~, agent_ids_supplier: Callable[[], List~str~])
      +complete(buffer: str, cursor_pos: int) -> Tuple[str, List~str~]
    }

    class CommandRouter {
      +CommandRouter(app: ConsoleApp, ui: ConsoleUI)
      +register(cmd: str, handler: Callable[[str], None]) -> None
      +execute(line: str) -> None
    }

    class AgentSession {
      +AgentSession(agent_id: AgentId, mcp: MCPClient, owner_token: str)
      +subscribe_tail(from_offset: Optional[int]=None) -> None
      +send_input(text: str) -> None
      +interrupt() -> None
      +cancel(hard: bool=False) -> None
      +reload_sysprompt() -> None
      +set_overlay_line(text: str) -> None
      +close() -> None
      -tail_cb: Callable[[TailEvent], None]
    }

    class OwnershipManager {
      +OwnershipManager(redis_url: str)
      +acquire(agent_id: AgentId, takeover: bool=False) -> str
      +release(agent_id: AgentId, token: str) -> None
      +is_owner(agent_id: AgentId, token: str) -> bool
    }

    class MCPRegistryClient {
      +MCPRegistryClient(redis_url: str)
      +list_agents() -> List~AgentInfo~
      +watch(callback: Callable[[RegistryEvent], None]) -> None
    }

    class MCPClient {
      +MCPClient(redis_url: str, agent_id: str)
      +call(method: str, params: Dict) -> Dict
      +subscribe_tail(on_event: Callable[[TailEvent], None]) -> None
      +close() -> None
    }

    class MCPServer {
      +MCPServer(redis_url: str, agent_id: str)
      +register_tool(name: str, fn: Callable[..., Any]) -> None
      +emit(event: TailEvent) -> None
      +start() -> None
      +stop() -> None
    }

    class AgentApp {
      +AgentApp(redis_url: str)
      +run() -> None
      +shutdown() -> None
      -identity: AgentIdentity
      -mcp: MCPServer
      -queue: PromptQueue
      -history: HistoryStore
      -prompts: PromptLayer
      -memory: MemoryManager
      -kb: KBAdapter
      -repl: AgentREPL
      -heartbeat: HeartbeatService
    }

    class AgentIdentity {
      +AgentIdentity(cwd: str)
      +compute() -> AgentId
      +acquire_lock() -> None
      +refresh_lock() -> None
      +release_lock() -> None
    }

    ConsoleApp --> MCPRegistryClient
    ConsoleApp --> ConsoleUI
    ConsoleApp --> CommandRouter
    ConsoleApp --> OwnershipManager
    ConsoleApp --> AgentSession
    ConsoleUI --> ConsoleCompleter
    AgentSession --> MCPClient
    AgentApp --> AgentIdentity
    AgentApp --> MCPServer
    AgentApp --> PromptQueue
    AgentApp --> HistoryStore
    AgentApp --> PromptLayer
    AgentApp --> MemoryManager
    AgentApp --> KBAdapter
    AgentApp --> AgentREPL
```

### A2. Agent runtime internals

```mermaid
classDiagram
    direction TB
    class TaskRunner {
      +TaskRunner(app: AgentApp)
      +run_next(item: QueueItem) -> TaskResult
      +interrupt() -> None
      +cancel(hard: bool=False) -> None
      +on_tool_call(tool_name: str, payload: dict) -> dict
    }
    class PromptQueue {
      +PromptQueue(path: str)
      +append(text: str, source: str) -> str
      +peek() -> Optional[QueueItem]
      +pop() -> Optional[QueueItem]
      +list() -> List[QueueItem]
    }
    class HistoryStore {
      +HistoryStore(history_path: str, summary_path: str)
      +append(turn: Turn) -> None
      +summarize() -> None
      +tail(n: int=100) -> List[Turn]
      +clear(confirm: bool) -> None
    }
    class PromptLayer {
      +PromptLayer(base_path: str, overlay_path: str)
      +effective() -> str
      +reload_from_disk() -> None
      +append_overlay(line: str) -> None
      +set_base(text: str) -> None
      +set_overlay(text: str) -> None
    }
    class MemoryManager {
      +MemoryManager(ctx_limit_tokens: int)
      +ctx_tokens() -> int
      +ctx_pct() -> float
      +should_summarize() -> bool
    }
    class KBAdapter {
      +KBAdapter(agent_root: str, project_root: str, user_root: str)
      +ingest(items: List[KBItem], scope: Scope) -> List[DocId]
      +search(query: str, scope: Scope) -> List[KBHit]
      +copy_from(source_agent: str, ids: List[DocId]) -> dict
    }
    class AgentREPL {
      +AgentREPL(app: AgentApp)
      +loop() -> None
      +toggle_info_panel() -> None
      +handle_tab_autocomplete(buffer: str, cursor_pos: int) -> str
    }
    AgentApp --> TaskRunner
    AgentApp --> PromptQueue
    AgentApp --> HistoryStore
    AgentApp --> PromptLayer
    AgentApp --> MemoryManager
    AgentApp --> KBAdapter
    AgentApp --> AgentREPL
```

### A3. Sequence diagram — UC1 “Attach & converse”

```mermaid
sequenceDiagram
    participant User
    participant ConsoleUI
    participant ConsoleApp
    participant Ownership as OwnershipManager
    participant Session as AgentSession
    participant MCPc as MCPClient
    participant MCPs as MCPServer
    participant Agent as AgentApp
    participant Runner as TaskRunner
    participant Queue as PromptQueue

    User->>ConsoleUI: /attach myproj/zeus
    ConsoleUI->>ConsoleApp: attach("myproj/zeus")
    ConsoleApp->>Ownership: acquire(agent_id, takeover=False)
    Ownership-->>ConsoleApp: owner_token
    ConsoleApp->>Session: new AgentSession(agent_id, MCPClient, owner_token)
    Session->>MCPc: subscribe_tail(on_event)
    MCPc->>MCPs: subscribe channel (tail)
    ConsoleUI->>ConsoleApp: "hello"
    ConsoleApp->>Session: send_input("hello")
    Session->>MCPc: call("input", {text:"hello", meta:{source:"console"}})
    MCPc->>Agent: input()
    Agent->>Queue: append("hello","console")
    Agent->>Runner: run_next(queue_item)
    Runner-->>MCPs: emit(token/tool events...)
    MCPs-->>MCPc: events
    MCPc-->>Session: on_event(event)
    Session-->>ConsoleUI: render_stream(event)
```

### A4. Sequence diagram — UC2 “Offload”

```mermaid
sequenceDiagram
    participant User
    participant ConsoleApp
    participant Orchestrator as OrchestratorClient
    participant NewAgent as AgentApp

    User->>ConsoleApp: /offload
    ConsoleApp->>Orchestrator: create_agent(spec)  (review & confirm)
    Orchestrator-->>ConsoleApp: BootstrapInfo(token, cmdline)
    ConsoleApp->>Orchestrator: spawn_local(spec) OR show remote cmd
    NewAgent->>NewAgent: run() → register + heartbeat
    ConsoleApp->>ConsoleApp: detects heartbeat → list shows new agent
```

---

## B. Redis Keys & Channels (Wire Protocol)

**Keys (string with TTL unless noted)**
- Registry: `mcp:agents:{project}/{agent}` → JSON `AgentInfo` (TTL refreshed by heartbeat).
- Single-instance lock: `mcp:agent:lock:{project}/{agent}` → value=`{host}:{pid}` (TTL refreshed each heartbeat).
- Ownership (write owner): `mcp:agent:owner:{project}/{agent}` → `{session_id}:{ts}` (no TTL; explicit release; takeover updates value).

**Pub/Sub Channels**
- Tail events: `mcp:tail:{project}/{agent}` → msgpack/json-encoded `TailEvent`.
- RPC request/response (if using simple RPC over Redis):
  - Requests: `mcp:req:{project}/{agent}`
  - Responses: `mcp:res:{project}/{agent}:{request_id}`

**Error model**
- Tool/command errors: event `{type:"error", msg, trace?}`
- Ownership violations: RPC error `{error:"not_owner"}`
- Unknown method: `{error:"no_such_method", method}`

---

## C. File Formats

### C1. `queue.jsonl` (per agent)
One JSON per line:
```json
{"id":"q-001","ts":1724221257.12,"source":"console","text":"build the project"}
```

### C2. `history.jsonl` (per agent)
```json
{"ts":1724221258.42,"role":"user","source":"console","content":"build the project","tokens_in":25,"tokens_out":0}
{"ts":1724221265.02,"role":"assistant","source":"system","content":"Starting build...","tokens_in":350,"tokens_out":42,"tool_calls":[{"name":"os.exec","args":{"cmd":"cmake .."}}]}
```

### C3. `summary.jsonl`
```json
{"ts":1724222000.0,"summary":"Built modules A,B; failures in C", "window":[100, 240]} 
```

### C4. `agent.yaml` (example)
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
    - agents.list
    - agents.spawn
```

### C5. `models.yaml` (example)
```yaml
models:
  gpt-5-nano:
    provider: openai
    context_window_size: 128000
    default_inference: {max_tokens: 4096, stream: true}
    model_settings: {}
```

### C6. `tools.yaml` (example)
```yaml
mcp:
  transport:
    kind: redis
    url: redis://127.0.0.1:6379/0

tools:
  allow: [ "os.exec", "fs.read", "fs.write", "kb.ingest", "kb.copy_from" ]
  deny:  [ ]
```

---

## D. CLI Entrypoints & Options

### D1. `ateam console`
```
Usage: ateam console [--redis URL] [--no-ui] [--panes] [--log-level LEVEL]

Options:
  --redis URL        Redis URL (env: ATEAM_REDIS_URL), default: redis://127.0.0.1:6379/0
  --no-ui            Plain TTY mode (no Rich/Textual panes).
  --panes            Force panes UI (if available).
  --log-level LEVEL  debug|info|warn|error (default: info)
Keys:
  F1                 Toggle palette.
  TAB                Autocomplete (commands, agent IDs, paths).
  Ctrl+C             Send /interrupt to attached agent.
```

### D2. `ateam agent`
```
Usage: ateam agent [--redis URL] [--cwd DIR] [--name NAME] [--project NAME] [--log-level LEVEL]

Options:
  --redis URL        Redis URL (env: ATEAM_REDIS_URL)
  --cwd DIR          Working directory for .ateam discovery (default: current dir)
  --name NAME        Agent name override (else from agent.yaml/defaults)
  --project NAME     Project name override (else project.yaml or dirname)
  --log-level LEVEL  debug|info|warn|error (default: info)
Keys:
  F1                 Toggle info/queue panel.
  TAB                Autocomplete (commands, paths).
```

---

## E. Autocomplete (TAB) Behavior

**ConsoleCompleter.complete(buffer, cursor_pos)**
- If buffer starts with `/` → complete **command** name (from `CommandRouter` registry).
- If buffer is `/attach <partial>` or any command expecting an **agent id** → complete from `MCPRegistryClient.list_agents()`.
- Else → treat token under cursor as **filesystem path**:
  - Tilde expansion (`~`), quotes-aware, Windows drive letters, WSL paths.
  - Single match: inline complete; multiple: show candidates; second TAB cycles.

**AgentCompleter**
- Same as Console, but for **local commands** and **paths**; no agent-id completion.

---

## F. Agent State Machine

```
INIT → REGISTERED → {IDLE ↔ BUSY} → (DISCONNECTED)
   ^                                   |
   |------------- SHUTDOWN ------------- 
```

- **INIT**: startup, config, lock acquire.
- **REGISTERED**: MCP server started, registry key written, heartbeat active.
- **IDLE**: no current task; waiting on queue.
- **BUSY**: processing one queue item; emits `task.start/task.end`.
- **DISCONNECTED**: (Console view) when heartbeats missed > 3 intervals.
- **SHUTDOWN**: graceful exit → release locks, remove registry.

---

## G. Ownership Semantics

- Acquire: set `mcp:agent:owner:{id}` to `{session_id}:{ts}` if empty; else reject unless `--takeover`.
- Takeover: write new owner and publish `warn` event to old session; old session becomes read-only.
- Release: owner token required; deleting key frees writer slot.

---

## H. Security Model

- Redis ACL or URL user:pass; TLS optional.
- FS tools sandboxed to agent `cwd` subtree unless command specifies `--unsafe` (disabled by default).
- Secrets redaction in streams (`****`), configurable via regex list.
- Offload & create flows: **always** confirmed by user; no auto-approval.

---

## I. Packaging (Flit) — Data Inclusion & Versioning

- All resources under `ateam/` are included by default (wheels include package data).
- If you add non-package data elsewhere, relocate it under `ateam/` or add a MANIFEST-in only for sdist (wheel uses package-only).
- Version bump policy: `pyproject.toml [project].version`. Tag in VCS for traceability.
- `deploy_to_pypi.py` uses API token (`FLIT_USERNAME="__token__"`, `FLIT_PASSWORD=<pypi-token>`).

---

## J. Testing Matrix & Benchmarks

- **Unit**: config merge, identity, locks, queue/histo I/O, prompt layering, KB hashing.
- **Integration**: agent register/heartbeat; console attach/detach; ownership takeover; offload; selective KB copy; duplicate prevention.
- **Snapshot**: console plain output; panes rendering; autocomplete tables.
- **Perf targets**:
  - Registry discovery < 150 ms on local Redis.
  - Tail latency (token→render) p95 < 100 ms.
  - Ownership acquire/release < 50 ms.
  - History append fsync < 10 ms per turn on SSD.

---

## K. Migration from `backend/` & `agents_lab/`

- **Keep**: model adapters, KB logic, prompt files, tool registry ideas.
- **Drop**: HTTP routers, FastAPI, web sockets, UI-generic DTOs not needed for CLI.
- **Refactor**: `llm/` adapters to streaming; tool execution to MCP tools.

---

## L. Error Codes & Messages

- Console exit codes:
  - 0 success; 2 Redis unavailable; 3 ownership denied; 4 invalid command.
- Agent exit codes:
  - 0 success; 11 duplicate instance (lock held); 12 config invalid; 13 MCP transport error.

---

## M. Examples

### M1. Remote spawn one-liner (Linux)
```bash
ATEAM_REDIS_URL=redis://user:pass@10.0.0.5:6379/0 \
ateam agent --project myproj --name builder --cwd /work/myproj
```

### M2. Windows PowerShell
```powershell
$env:ATEAM_REDIS_URL="redis://user:pass@10.0.0.5:6379/0"
ateam agent --project myproj --name builder --cwd "C:\work\myproj"
```

### M3. Selective KB copy
```text
/kb copy-from myproj/research --ids doc_abc123,doc_def456
```

---

## N. Full API Completeness (Additions)

### N1. `ateam/cli.py`
```python
def main() -> None:
    """
    Entrypoint for console_scripts 'ateam'.
    Subcommands:
      - console: run ConsoleApp
      - agent:   run AgentApp
    """
    ...
```

### N2. `tools/builtin/os.py` (interface sketch)
```python
def exec(cmd: str, cwd: Optional[str]=None, timeout: Optional[int]=None,
         env: Optional[Dict[str,str]]=None, pty: bool=True) -> Dict[str, Any]:
    """Execute a shell command (sandboxed to agent cwd). Returns {"rc": int, "stdout": str, "stderr": str}."""
```

### N3. `tools/builtin/fs.py`
```python
def read(path: str) -> Dict[str, Any]
def write(path: str, content: str, create_dirs: bool=False) -> Dict[str, Any]
def listdir(path: str) -> Dict[str, Any]
def stat(path: str) -> Dict[str, Any]
```

### N4. `agent/memory.py` thresholds
```python
class MemoryManager:
    def __init__(self, ctx_limit_tokens: int, summarize_threshold: float=0.75) -> None: ...
```

---

## O. Notes on Cross-Env Agents

- Different machines/containers can run agents; same Redis = same fleet.
- Identity collision prevented by lock even across hosts.
- Use `--project`/`--name` to disambiguate intentionally.

---

## P. Final Checklist Addendum

- [x] Implement Redis channel naming exactly as in Section B.
- [x] Implement JSONL schemas exactly as in Section C.
- [x] Validate CLI args map to config overrides (project/name/cwd).
- [x] Implement TAB autocomplete path rules for Windows/Unix (tilde, drives, WSL).
- [x] Add secrets redaction regex list (env-configurable).
- [x] Add perf timers for tail latency and ownership ops.
- [x] Ensure `/clearhistory` double-confirm prints irreversible warning and requires exact `project/agent`.

---
