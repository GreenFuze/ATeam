# Appendices — Deep Design Details (continuation of Draft v5, Part 5)

> This continues the same `change.md` spec. Everything below is additive and can be appended to the previous file.

---

## BT. Concurrency model & async runtime

We standardize on **`asyncio`** for MCP transport, Console, and Agent runtime. Blocking tasks
(`os.exec`, heavy FS ops, embedding) are dispatched to a **thread pool**.

### BT1. Event loops per component

- **Console**:
  - Single asyncio event loop.
  - Tasks:
    - `registry_watch_task`: subscribes to registry pub/sub and updates UI.
    - `input_task`: reads keystrokes (prompt-toolkit) without blocking.
    - `tail_task[N]`: one per attached agent (usually 1), consumes `TailEvent`s.
  - CPU-bound rendering runs in loop; file operations go to `run_in_executor`.

- **Agent**:
  - Single asyncio event loop.
  - Tasks:
    - `heartbeat_task`: periodic TTL refresh.
    - `rpc_server_task`: consumes MCP requests.
    - `queue_worker_task`: fetches next `QueueItem` and calls `TaskRunner`.
    - `repl_task`: reads from agent-local stdin REPL (non-blocking).
  - `TaskRunner`:
    - **LLM streaming** runs on loop (awaitable generator).
    - `os.exec` in PTY uses threads with `asyncio.to_thread` to read pipes incrementally.

### BT2. Cancellation & teardown order (Agent)

1. Stop **accepting** new RPCs (server returns `error.timeout.saturated` after a grace period).
2. Cancel `queue_worker_task` (cooperative).
3. Flush `history.jsonl`; fsync.
4. Stop heartbeat; delete registry key; **release lock**.
5. Cancel remaining tasks; close Redis connections; exit.

### BT3. Backpressure

- If `TailEvent` rate exceeds **200 msgs/s**, coalesce tokens within `TAIL_COALESCE_MS` and emit combined frames.
- Console renders at most **60 FPS** equivalent (throttled).
- Queue depth > threshold (e.g., 200) → Console warns `[warn] queue length high`.

---

## BU. Key bindings & input system

### BU1. Console (prompt-toolkit)

- **F1**: open/close palette (custom key binding).
- **TAB**: autocomplete (commands, agent ids, paths).
- **Ctrl+C**: `/interrupt` if attached, else exits console with confirm.
- **Ctrl+L**: clear screen (UI redraw).

### BU2. Agent REPL

- **F1**: toggle info/queue panel.
- **TAB**: autocomplete (local commands & paths).
- **Ctrl+C**: `TaskRunner.interrupt()` (does not kill process).

---

## BV. Validation & typed errors

We use **Pydantic** (`pydantic>=2`) for validating RPC payloads and YAML→object parsing.
All outward-facing methods return `Result[T]` with `ErrorInfo{code,message,detail}`.

Common error codes:

- `redis.unavailable`, `redis.timeout`
- `ownership.denied`, `ownership.stale_token`
- `agent.not_found`
- `duplicate.instance`
- `config.invalid`, `yaml.parse_error`
- `prompt.protected_violation`
- `kb.ingest.denied`, `kb.id.unknown`
- `tool.denied`, `tool.exec_error`
- `timeout`

---

## BW. Concrete scaffolding (code skeletons)

> Cursor should generate these files with the exact signatures and TODOs.

### BW1. `ateam/cli.py`

```python
import asyncio
import typer
from typing import Optional
from ateam.console.app import ConsoleApp
from ateam.agent.main import AgentApp

app = typer.Typer(add_completion=False, help="ATeam CLI - Console and Agent runtime")

@app.command()
def console(redis: str = typer.Option("redis://127.0.0.1:6379/0", "--redis"),
            no_ui: bool = typer.Option(False, "--no-ui", help="Disable panes"),
            panes: bool = typer.Option(False, "--panes", help="Force panes UI"),
            log_level: str = typer.Option("info", "--log-level")):
    """Run the central Console."""
    # TODO(tsvi): wire logging level
    use_panes = (not no_ui) and panes
    app_ = ConsoleApp(redis_url=redis, use_panes=use_panes)
    try:
        app_.run()
    except KeyboardInterrupt:
        pass
    finally:
        app_.shutdown()

@app.command()
def agent(redis: str = typer.Option("redis://127.0.0.1:6379/0", "--redis"),
          cwd: Optional[str] = typer.Option(None, "--cwd"),
          name: Optional[str] = typer.Option(None, "--name"),
          project: Optional[str] = typer.Option(None, "--project"),
          log_level: str = typer.Option("info", "--log-level")):
    """Run an Agent process (with local REPL)."""
    # TODO(tsvi): support overrides for cwd/name/project
    app_ = AgentApp(redis_url=redis, cwd=cwd or ".", name_override=name or "", project_override=project or "")
    res = app_.run()
    if not res.ok:
        typer.echo(f"[error] {res.error.code}: {res.error.message}")
        raise typer.Exit(code=1)

def main():
    app()

if __name__ == "__main__":
    main()
```

### BW2. `ateam/mcp/redis_transport.py` (excerpt)

```python
import asyncio, json, msgpack, uuid
from typing import Any, Callable, Optional
import redis.asyncio as aioredis
from ateam.util.types import Result, ErrorInfo

class RedisTransport:
    def __init__(self, url: str, username: str = "", password: str = "", tls: bool = False) -> None:
        self._url = url
        self._pool = aioredis.from_url(url, decode_responses=False)
        # TODO: tls/username/password

    async def publish(self, channel: str, data: bytes) -> Result[None]:
        try:
            await self._pool.publish(channel, data)
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("redis.unavailable", str(e)))

    async def subscribe(self, channel: str, cb: Callable[[bytes], None]):
        pubsub = self._pool.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    cb(msg["data"])
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    async def call(self, req_ch: str, res_ch: str, payload: dict, timeout_sec: Optional[float] = 15.0) -> Result[Any]:
        req_id = payload.get("req_id") or f"r-{uuid.uuid4().hex[:8]}"
        payload["req_id"] = req_id
        data = msgpack.packb(payload, use_bin_type=True)
        pubsub = self._pool.pubsub()
        await pubsub.subscribe(res_ch)
        try:
            pub_task = asyncio.create_task(self._pool.publish(req_ch, data))
            recv_task = asyncio.create_task(_await_response(pubsub, req_id))
            done, _ = await asyncio.wait({pub_task, recv_task}, timeout=timeout_sec, return_when=asyncio.FIRST_COMPLETED)
            if recv_task in done:
                resp = recv_task.result()
                return Result(ok=resp.get("ok", False),
                              value=resp.get("value"),
                              error=None if resp.get("ok") else ErrorInfo(resp["error"]["code"], resp["error"]["message"], resp["error"].get("detail")))
            return Result(ok=False, error=ErrorInfo("timeout", f"RPC timed out after {timeout_sec}s"))
        finally:
            await pubsub.unsubscribe(res_ch)
            await pubsub.close()

async def _await_response(pubsub) -> dict:
    async for msg in pubsub.listen():
        if msg["type"] == "message":
            try:
                resp = msgpack.unpackb(msg["data"], raw=False)
                return resp
            except Exception:
                continue
    return {"ok": False, "error": {"code": "redis.unavailable", "message": "channel closed"}}
```

> Note: Cursor should fill `_await_response` signature to include `req_id` filter and verify it matches.

---

## BX. Tool descriptor generator → prompt toolbox

We render an agent’s **Toolbox** section into the effective prompt, using tool descriptors.

```python
# ateam/tools/descriptors.py
from typing import List, Dict, Any

def render_toolbox(descriptors: List[Dict[str, Any]]) -> str:
    """
    Returns a markdown fenced block listing allowed tools & concise usage.
    Protected with <!-- ateam-protect:start:toolbox --> markers.
    """
    lines = ["<!-- ateam-protect:start:toolbox -->", "### Toolbox", ""]
    for d in descriptors:
        args = ", ".join([f"{k}: {v.get('type','str')}" + ("*" if v.get("required") else "") for k, v in d.get("args", {}).items()])
        lines.append(f"- **{d['name']}** — {d.get('doc','')}")
        if args:
            lines.append(f"  - args: {args}")
    lines += ["", "<!-- ateam-protect:end:toolbox -->"]
    return "\n".join(lines)
```

`PromptLayer.effective()` merges base + overlay and **replaces** the prior toolbox protected block with regenerated content.

---

## BY. Protected overlay merge rules

- If overlay lacks toolbox block, append toolbox at the **end**.
- If multiple toolbox blocks found, keep the **first**, remove the rest.
- Deny edits that delete the start/end markers → `prompt.protected_violation`.

---

## BZ. Autocomplete: path rules & quoting

- Preserve user quoting:
  - Input: `"/path with/spaces"/fi<TAB>` → completes within quotes.
- Add trailing separator on directory match:
  - `~/Doc<TAB>` → `~/Documents/`
- Windows drive completion:
  - `C:<TAB>` → `C:\`
- UNC:
  - `\\se<TAB>` → `\\server\`
- WSL:
  - Detect `/mnt/<drive>/` patterns.

---

## CA. Sample system prompts (starter kit)

### CA1. `system_base.md` (Zeus)

```md
You are **Zeus**, an engineering orchestrator. Principles:
- Be explicit, concise, and stepwise. Ask for confirmation before destructive actions.
- Use tools when factual operations are required (fs.read/write, os.exec).
- Keep context small: summarize when context exceeds 75%.

Workflow guidance:
1) Clarify the goal.
2) Plan a minimal sequence of operations.
3) Execute with tools, streaming progress.
4) If the task grows in scope, propose offloading to a fresh agent with a focused context.
```

### CA2. `system_base.md` (Builder)

```md
You are **Builder**, focused on build configuration, CMake/Ninja, compilers, and linker errors.
- Prefer minimal, reversible changes. Propose a patch/diff and request confirmation.
- Run `cmake`/`ninja` with `os.exec` and capture outputs; extract actionable diagnostics.
```

---

## CB. Agent creation wizard — UX outline

1. **Name** (validate `^[a-zA-Z0-9_-]+$`).
2. **Project** (default from nearest `.ateam/project.yaml`).
3. **CWD** (path must exist; sandbox root).
4. **Model** (pick from `models.yaml`).
5. **Base prompt path** (create if missing).
6. **Overlay prompt path** (create empty with toolbox markers).
7. **KB seeds** (optional paths/urls; display count and size).

**Review screen** shows JSON summary → user must type `create` to confirm.

---

## CC. Selective KB copy — UX outline

- When `/kb copy-from` without ids, offer **interactive picker**:
  - Fetch top-N recent docs from source agent (by mtime).
  - Filter by pattern; SPACE to mark; ENTER to confirm.
- Show copy plan summary (N docs, total size, target scope).
- Require `copy` confirmation.

---

## CD. Logging format configuration

`util/logging.py` supports **structured JSON** and **human**:

- Env `ATEAM_LOG_FORMAT=json|human`
- Default fields:
  - `ts`, `lvl`, `where`, `msg`, `agent_id?`, `host`, `pid`, `trace_id?`
- Redaction: list of regex from config:
  ```
  redact:
    - "(?i)api[_-]?key\\s*[:=]\\s*[A-Za-z0-9_\\-]{20,}"
    - "sk-[A-Za-z0-9]{20,}"
  ```

---

## CE. Extras in PyPI packaging

Extend `pyproject.toml`:

```toml
[project.optional-dependencies]
ui = ["rich>=13.7","textual>=0.58"]
dev = ["pytest","mypy","ruff","types-redis","prometheus-client","pydantic>=2"]

[tool.flit.module]
name = "ateam"
```

---

## CF. Minimal unit tests (examples)

`tests/test_identity.py`
```python
from ateam.agent.identity import AgentIdentity

def test_compute_id(tmp_path, monkeypatch):
    (tmp_path/".ateam").mkdir()
    (tmp_path/".ateam"/"project.yaml").write_text("name: myproj\n")
    ident = AgentIdentity(cwd=str(tmp_path))
    assert ident.compute() == "myproj/" + tmp_path.name  # fallback name is dir name
```

`tests/test_prompt_layer.py`
```python
from ateam.agent.prompt_layer import PromptLayer

def test_overlay_protected_merge(tmp_path):
    base = tmp_path/"base.md"; overlay = tmp_path/"overlay.md"
    base.write_text("# Base\n")
    overlay.write_text("<!-- ateam-protect:start:toolbox -->\nX\n<!-- ateam-protect:end:toolbox -->\n")
    pl = PromptLayer(str(base), str(overlay))
    eff = pl.effective()
    assert "ateam-protect:start:toolbox" in eff
```

---

## CG. RPC handlers mapping (Agent MCP server)

| Method | Handler | Notes |
|---|---|---|
| `status` | `AgentApp.status()` | returns state/ctx/model/cwd/pid/host |
| `tail` | `AgentApp.tail(from_offset)` | server-side stream (pub/sub only) |
| `input` | `AgentApp.enqueue(text, meta)` | appends to queue |
| `interrupt` | `TaskRunner.interrupt()` | cooperative |
| `cancel` | `TaskRunner.cancel(hard)` | force if `hard` |
| `prompt.set` | `PromptLayer.set_*` | base/overlay updates |
| `prompt.reload` | `PromptLayer.reload_from_disk()` | live apply |
| `kb.ingest` | `KBAdapter.ingest(items, scope)` | de-dupe |
| `kb.copy_from` | `KBAdapter.copy_from(source, ids)` | selective |
| `memory.stats` | `MemoryManager.*` | ctx stats |

---

## CH. Tail event framing

When coalescing, we emit:

```json
{ "type": "token", "text": "chunk1chunk2chunk3", "model": "gpt-5-nano" }
```

We **never** split multi-byte UTF-8 codepoints (coalescer is byte-aware).

---

## CI. History compaction (safe)

- Compaction **never** mutates original rotated files.
- On compaction:
  - Create `history.jsonl.tmp`.
  - Stream-copy last `N` turns + all summaries.
  - `fsync()` → `rename()` atomically to `history.jsonl`.

---

## CJ. Ownership takeover protocol (race-free)

- Acquire with `--takeover`:
  - Write new `owner` key with session id.
  - Publish `{"type":"warn","msg":"ownership.takeover"}` to old owner-specific channel `mcp:owner:{agent}:{old_session}`.
  - Old session marks itself **read-only** and UI displays banner.
- If both UIs claim ownership due to race, **server** enforces by checking the **current** owner key at the start of every mutating RPC.

---

## CK. Agent local commands (REPL)

| Command | Description |
|---|---|
| `status` | Print current state, ctx%, model, cwd |
| `queue` | List pending prompts (ids + first 60 chars) |
| `queue clear` | Clear queue (confirm) |
| `history tail [N]` | Tail last N turns |
| `sys show` | Show effective prompt |
| `sys reload` | Reload base+overlay |
| `kb ingest <path...>` | Ingest locally to agent scope |
| `help` | List commands |

---

## CL. Safe defaults

- Start with **deny**-first tool policy; allow minimal set per agent.
- `--unsafe` path operations are **disabled** globally unless set in config:
  ```yaml
  tools:
    unsafe: false
  ```

---

## CM. Example offload proposal (JSON)

```json
{
  "project": "myproj",
  "name": "builder",
  "cwd": "/work/myproj",
  "model_id": "gpt-5-nano",
  "system_base_path": ".ateam/agents/builder/system_base.md",
  "kb_seeds": [
    ".ateam/agents/zeus/kb/index/doc_abc123.json",
    ".ateam/agents/zeus/kb/index/doc_def456.json"
  ]
}
```

---

## CN. Future MCP transport adapters (pluggable)

`mcp/transport/base.py` defines an interface; `redis_transport.py` is default. We reserve:
- `zmq_transport.py` for ZeroMQ pub/sub.
- `amqp_transport.py` for RabbitMQ.

Transport is selected by `tools.yaml → mcp.transport.kind`.

---

## CO. Robust path resolution helper

`util/paths.py` exposes:

```python
def expand_user_vars(path: str) -> str: ...
def resolve_within(base: str, candidate: str) -> str:
    """
    Resolve candidate path within base; raise if outside sandbox (symlinks resolved).
    """
```

---

## CP. Minimal smoke script (for developers)

```
# 1) Start Redis locally
docker run --rm -p 6379:6379 redis:7

# 2) Start an agent
ateam agent --project myproj --name zeus --cwd .

# 3) In another shell, start console
ateam console

# 4) F1 → attach to myproj/zeus, send "echo hi"
input: please run `os.exec` echo hi
```

---

## CQ. Documentation index (README anchors)

- Quickstart
- Installing (PyPI vs source)
- Running console and agents
- `.ateam` directory layout & precedence
- Commands reference
- Offload & creation wizards
- KB scopes & selective copy
- Prompt layering & live reload
- Packaging & deploy (Flit)
- Security and sandboxing
- Troubleshooting & FAQs

---

## CR. Troubleshooting (FAQs)

- **I attach but see no output.**
  - Check heartbeats (`/ps`) and ensure `mcp:tail:*` events are arriving (enable debug tail).
- **`duplicate.instance` on startup.**
  - Another agent with same `project/name` is registered on this Redis. Stop it or use another Redis db.
- **TAB completion doesn’t work on Windows.**
  - Ensure terminal is VT-enabled (Windows Terminal or recent PowerShell), and `prompt-toolkit` is installed.

---

## CS. Cutover checklist from web app to CLI

- [x] Remove FastAPI/HTTP server dependencies.
- [x] Port LLM adapters to streaming interface.
- [x] Replace websocket events with `TailEvent` pub/sub.
- [x] Retain prompts & KB, move under `.ateam/agents/...`.
- [x] Migrate model configs to `models.yaml` (PEP 621 remains in `pyproject.toml`).

---

## CT. End-to-end acceptance criteria (E2E)

- **E2E-1**: Start agent and console; attach; send text; see streamed tokens.
- **E2E-2**: Interrupt long tool; agent remains responsive; queue processes next item.
- **E2E-3**: Offload creates new agent; it registers; console attaches; old agent continues.
- **E2E-4**: KB ingest with de-dup; search returns relevant hits.
- **E2E-5**: `#` modifies overlay; `/reloadsysprompt` reflects on next turn.
- **E2E-6**: Duplicate agent prevented (exit 11).

---

## CU. Final implementation nudges

- Keep functions **small and pure** where possible; side effects live in adapters.
- Unit-test merge precedence and sandbox path resolver early to avoid subtle bugs.
- Dogfood with a **tiny demo** repository checked into `examples/` (optional).

---
