# Appendices — Deep Design Details (continuation of Draft v5, Part 10)

> This continues the same `change.md` spec. Everything below is **additive** and can be appended to the previous file.  
> Focus: minimal reference implementations (MCP loop, tail ring buffer, PTY exec, console handlers), plus a fully itemized, checkboxed implementation plan.

---

## GG. Minimal reference implementations

> These snippets are intentionally compact and runnable with TODOs. Cursor should expand with tests and error handling.

### GG1. MCP server loop (asyncio, Redis pub/sub)

`ateam/mcp/server.py`
```python
import asyncio, time, msgpack
from typing import Callable, Dict, Any, Optional
from .redis_transport import RedisTransport
from ..util.types import Result, ErrorInfo
from ..util.logging import log

class MCPServer:
    def __init__(self, redis_url: str, agent_id: str) -> None:
        self._agent_id = agent_id
        self._transport = RedisTransport(redis_url)
        self._tools: Dict[str, Callable[..., Any]] = {}
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._serve_task: Optional[asyncio.Task] = None
        self._running = False

    def register_tool(self, name: str, fn: Callable[..., Any]) -> None:
        self._tools[name] = fn

    def register_handler(self, method: str, fn: Callable[[Dict[str, Any]], Any]) -> None:
        self._handlers[method] = fn

    async def start(self) -> Result[None]:
        if self._running:
            return Result(ok=True)
        self._running = True
        self._serve_task = asyncio.create_task(self._serve())
        return Result(ok=True)

    async def stop(self) -> Result[None]:
        self._running = False
        if self._serve_task:
            self._serve_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._serve_task
        return Result(ok=True)

    async def _serve(self) -> None:
        req_ch = f"mcp:req:{self._agent_id}"
        log("INFO", "mcp.server", "listening", channel=req_ch)
        async def on_msg(raw: bytes) -> None:
            try:
                req = msgpack.unpackb(raw, raw=False)
                res_ch = f"mcp:res:{self._agent_id}:{req['req_id']}"
                out = await self._dispatch(req)
                await self._transport.publish(res_ch, msgpack.packb(out, use_bin_type=True))
            except Exception as e:
                log("ERROR", "mcp.server", "dispatch-failed", err=str(e))
        # Subscribe forever; RedisTransport handles reconnects.
        await self._transport.subscribe(req_ch, on_msg)

    async def _dispatch(self, req: Dict[str, Any]) -> Dict[str, Any]:
        req_id = req.get("req_id", "")
        method = req.get("method", "")
        params = req.get("params", {})
        ts = time.time()
        h = self._handlers.get(method)
        if not h:
            return {"req_id": req_id, "ok": False, "error": {"code":"no_such_method","message":method}, "ts": ts}
        try:
            # Handlers can be sync or async
            if asyncio.iscoroutinefunction(h):
                value = await h(params)
            else:
                value = h(params)
            return {"req_id": req_id, "ok": True, "value": value, "ts": ts}
        except Exception as e:
            return {"req_id": req_id, "ok": False, "error": {"code":"handler.error","message":str(e)}, "ts": ts}
```

> Agent startup should `server.register_handler("input", self._handle_input)` etc., as mapped earlier.

---

### GG2. Tail emitter with in-process ring buffer & monotonic offsets

`ateam/mcp/tail.py`
```python
import asyncio, msgpack, time
from collections import deque
from typing import Deque, Dict, Any, Optional
from .redis_transport import RedisTransport
from ..util.const import DEFAULTS

class TailEmitter:
    def __init__(self, redis_url: str, agent_id: str, ring_size: int = 2048) -> None:
        self._transport = RedisTransport(redis_url)
        self._agent_id = agent_id
        self._ring: Deque[Dict[str, Any]] = deque(maxlen=ring_size)
        self._offset = 0
        self._ch = f"mcp:tail:{agent_id}"

    def next_offset(self) -> int:
        self._offset += 1
        return self._offset

    async def emit(self, event: Dict[str, Any]) -> None:
        rec = {"offset": self.next_offset(), "event": event, "ts": time.time()}
        self._ring.append(rec)
        await self._transport.publish(self._ch, msgpack.packb(rec, use_bin_type=True))

    def replay_from(self, off: int) -> list[Dict[str, Any]]:
        return [x for x in self._ring if x["offset"] > off]
```

> Agent methods producing output should call `await tail.emit({...})`.  
> Console receives frames and renders by `rec["event"]`.

---

### GG3. PTY/ConPTY executor (minimal, cross-platform)

`ateam/tools/ptyexec.py`
```python
import sys, os, asyncio, platform, shlex
from typing import AsyncIterator, Optional

IS_WINDOWS = platform.system() == "Windows"

async def stream_cmd(cmd: str, cwd: Optional[str]=None, env: Optional[dict]=None) -> AsyncIterator[str]:
    """
    Yields stdout/stderr merged text chunks from the running process.
    Uses PTY on Unix; falls back to regular pipes on Windows for minimalism.
    """
    if not IS_WINDOWS:
        # Unix PTY
        import pty, termios
        master, slave = pty.openpty()
        # set raw mode if needed
        proc = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), cwd=cwd, env=env,
            stdin=slave, stdout=slave, stderr=slave,
            start_new_session=True,
        )
        os.close(slave)
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, os.fdopen(master, "rb", buffering=0))
        try:
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                yield chunk.decode("utf-8", "replace")
        finally:
            await proc.wait()
    else:
        # Windows: merged pipes
        proc = await asyncio.create_subprocess_shell(
            cmd, cwd=cwd, env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            creationflags=0x00000008  # CREATE_NEW_PROCESS_GROUP
        )
        assert proc.stdout is not None
        while True:
            chunk = await proc.stdout.read(4096)
            if not chunk:
                break
            yield chunk.decode("utf-8", "replace")
        await proc.wait()
```

> `tools/builtin/os.py` can wrap this to emit `TailEvent(type="token")` frames with coalescing.

---

### GG4. Console command handlers (bare-bones)

`ateam/console/handlers.py`
```python
from typing import Optional
from ..util.types import Result, ErrorInfo

def _parse_one_arg(args: str) -> Optional[str]:
    a = args.strip().split()
    return a[0] if a else None

def cmd_ps(ctx, args: str) -> Result[None]:
    res = ctx.registry.list_agents()
    if not res.ok:
        ctx.ui.notify(f"error: {res.error.message}", "error")
        return Result(ok=False, error=res.error)
    ctx.ui.render_agent_list(res.value)
    return Result(ok=True)

def cmd_attach(ctx, args: str) -> Result[None]:
    arg = _parse_one_arg(args)
    if not arg:
        ctx.ui.notify("usage: /attach <project/agent>", "warn")
        return Result(ok=False, error=ErrorInfo("args.missing","agent id required"))
    takeover = "--takeover" in args
    res = ctx.app.attach(arg, takeover=takeover)
    if not res.ok:
        ctx.ui.notify(f"attach failed: {res.error.code}", "error")
        return Result(ok=False, error=res.error)
    s = res.value
    s.subscribe_tail(on_event=lambda ev: ctx.ui.render_stream(arg, ev.value if hasattr(ev,"value") else ev))
    ctx.ui.notify(f"attached to {arg}", "info")
    return Result(ok=True)

def cmd_detach(ctx, args: str) -> Result[None]:
    res = ctx.app.detach(None)
    if not res.ok:
        ctx.ui.notify(f"detach failed: {res.error.code}", "error")
        return Result(ok=False, error=res.error)
    ctx.ui.notify("detached", "info")
    return Result(ok=True)

def cmd_reloadsysprompt(ctx, args: str) -> Result[None]:
    sess = ctx.app.current_session()
    if not sess:
        ctx.ui.notify("not attached", "warn")
        return Result(ok=False, error=ErrorInfo("not_attached",""))
    return sess.reload_sysprompt()
```

---

### GG5. Console command router (wire-up)

`ateam/console/cmd_router.py` (add registrations)
```python
from .handlers import (
  cmd_ps, cmd_attach, cmd_detach, cmd_reloadsysprompt,
  # ... other handlers
)

class CommandRouter:
    def __init__(self, app, ui):
        self.app, self.ui = app, ui
        self._handlers = {}
        self.register("ps", lambda args: cmd_ps(self, args))
        self.register("attach", lambda args: cmd_attach(self, args))
        self.register("detach", lambda args: cmd_detach(self, args))
        self.register("reloadsysprompt", lambda args: cmd_reloadsysprompt(self, args))
        # TODO: register remaining commands

    # ctx facade for handlers:
    @property
    def registry(self): return self.app.registry
    @property
    def app(self): return self._app
    @app.setter
    def app(self, v): self._app = v
    @property
    def ui(self): return self._ui
    @ui.setter
    def ui(self, v): self._ui = v
```

---

### GG6. Minimal `pyproject.toml` (Flit) for PyPI

`pyproject.toml`
```toml
[build-system]
requires = ["flit_core>=3.9"]
build-backend = "flit_core.buildapi"

[project]
name = "ateam"
version = "0.1.0a1"
description = "A pure-CLI multi-agent system with Redis-backed MCP and explicit control."
readme = "README.md"
requires-python = ">=3.9"
authors = [{ name="Tsvi", email="example@example.com" }]
license = { text = "Apache-2.0" }
dependencies = [
  "typer>=0.12",
  "redis>=5.0",
  "msgpack>=1.0",
  "prompt-toolkit>=3.0",
  "pydantic>=2.5",
  "pyyaml>=6.0",
  "portalocker>=2.8"
]

[project.optional-dependencies]
ui = ["rich>=13.7", "textual>=0.58"]
dev = ["pytest","mypy","ruff","types-redis","prometheus-client"]

[project.urls]
Homepage = "https://github.com/GreenFuze/ATeam"

[project.scripts]
ateam = "ateam.cli:main"
```

---

## GH. Detailed, phased implementation plan (checkboxes)

> Each phase is self-contained. Check off items as Cursor lands them. Suggested order optimizes feedback loops.

### Phase 0 — Repository bootstrap & packaging
- [x] Scaffold `ateam/` package with directories per layout.
- [x] Add `pyproject.toml` (Flit), `README.md`, `LICENSE`.
- [x] Add `deploy_to_pypi.py` (flit wrapper) and validate `flit build`.
- [x] Add CI (lint, type, tests, build).

### Phase 1 — Config discovery & identity
- [x] Implement `ConfigDiscovery.discover_stack()`.
- [x] Implement `ConfigMerger` (scalars/dicts/lists).
- [x] Implement Pydantic schemas (project/models/tools/agent).
- [x] Implement loader `load_stack()` and unit tests.
- [x] Implement `AgentIdentity.compute()` with `project/name`.
- [x] Implement single-instance lock acquire/release/refresh (Redis).

### Phase 2 — MCP transport & server/client scaffolding
- [x] Implement `RedisTransport.publish/subscribe/call` (msgpack, timeouts).
- [x] Implement `MCPServer` loop (GG1).
- [x] Implement `MCPClient.call/subscribe_tail`.
- [x] Define RPC method catalog & schemas; add validators.

### Phase 3 — Tail events & ring buffer
- [x] Implement `TailEmitter` (GG2) with offsets + in-proc ring buffer.
- [x] Agent publishes heartbeats, registry keys with TTL.
- [x] Console subscribes to tail and renders minimal output.

### Phase 4 — Console core (F1 palette, TAB autocomplete)
- [x] Implement `ConsoleApp` main loop.
- [x] Implement `ConsoleUI` (prompt-toolkit, F1/F2/F3 bindings).
- [x] Implement `ConsoleCompleter` with full TAB completion (commands/agents/paths).
- [x] Implement `CommandRouter` and map `/ps`, `/attach`, `/detach`, `/reloadsysprompt`.
- [x] Handle ownership acquire/release/takeover in Console.

### Phase 5 — Agent runtime
- [x] Implement `AgentApp.run()` with REPL (F1 panel, TAB completion).
- [x] Implement `PromptQueue` (JSONL append/peek/pop + fsync).
- [x] Implement `HistoryStore` (JSONL append/rotate).
- [x] Implement `PromptLayer` (base + overlay + protected blocks).
- [x] Implement `TaskRunner` skeleton (LLM stub returning echo tokens).

### Phase 6 — Tools & PTY execution
- [x] Implement `tools/builtin/fs.py` (read/write/list/stat) with sandbox.
- [x] Implement `ptyexec.stream_cmd()` (GG3) + `tools/builtin/os.py` wrapper.
- [x] Emit tool events + tokenized PTY output to tail.

### Phase 7 — Models & streaming
- [x] Implement `llm/base.py` interface.
- [x] Implement one provider (OpenAI or local LM Studio) for `generate/stream`.
- [x] Integrate with `TaskRunner` to stream model tokens into tail.
- [x] Add `MemoryManager` and summarization triggers (stubs ok).

### Phase 8 — Prompts live reload & `#` overlay
- [x] Implement `/reloadsysprompt` RPC → `PromptLayer.reload_from_disk`.
- [x] Implement `# <line>` to append single overlay line.
- [x] Validate protected block violation on overlay save.

### Phase 9 — Knowledge base (agent scope only)
- [x] Implement `KBAdapter.ingest/search` minimal (Chroma or pluggable).
- [x] Implement de-dup by content hash.
- [x] Wire console commands `/kb add` and `/kb search`.

### Phase 10 — Offload & agent creation wizard
- [x] Implement `/agent new` wizard: gather name/project/cwd/model/prompts.
- [x] Implement `/offload` wizard: propose defaults; require confirm.
- [x] Implement orchestrator helpers: `create_agent`, `spawn_local`, `remote_cmd`.
- [x] Enforce **no auto-approve** (explicit confirms).

### Phase 11 — Ownership hardening & takeover UX
- [x] Enforce writer-only for mutating RPCs server-side.
- [x] Implement takeover warnings; read-only mode banner.
- [x] Add `/who` command.

### Phase 12 — Persistence polish & recovery
- [x] Crash-safe JSONL (truncate partial line; compaction).
- [x] History rotation & summary compaction.
- [x] Context reconstruction on startup (summaries + raw tail).

### Phase 13 — Windows polish & paths
- [x] ConPTY fallback path verified.
- [x] Path completion (drives, UNC).
- [x] Resolve & block symlink escapes on Windows.

### Phase 14 — Packaging & TestPyPI
- [x] Verify `flit build` wheel includes package data (schemas/docs).
<!-- - [ ] Publish to **TestPyPI** with `deploy_to_pypi.py --repository testpypi`. -->
<!-- - [ ] Install via `pipx` on Windows & Linux; smoke passes. -->

### Phase 15 — Security & gating
- [x] Redis ACL/TLS support in transport.
- [x] Secrets redaction filters.
- [x] Deny-by-default tool policy; per-agent allow-list enforced.

### Phase 16 — Docs & examples
- [x] `examples/hello` demo with `.ateam` seed.
- [x] Manpage stubs & README quickstart.
- [x] Troubleshooting guide.

---

## GI. Minimal agent handlers mapped to server

`ateam/agent/main.py` (excerpt)
```python
class AgentApp:
    def __init__(self, redis_url: str, cwd: str, name_override: str = "", project_override: str = "") -> None:
        # ... load config, identity, etc.
        self.server = MCPServer(redis_url, agent_id=self.identity.compute())
        self.tail = TailEmitter(redis_url, agent_id=self.identity.compute())
        self.queue = PromptQueue(self.paths.queue)
        self.history = HistoryStore(self.paths.history, self.paths.summary)
        # register handlers
        self.server.register_handler("status", self._h_status)
        self.server.register_handler("input", self._h_input)
        self.server.register_handler("prompt.reload", self._h_prompt_reload)
        self.server.register_handler("kb.ingest", self._h_kb_ingest)

    async def _h_status(self, params):  # returns dict (JSON-serializable)
        return {"cwd": self.cwd, "model": self.model_id, "state": self.state, "ctx_pct": self.mem.ctx_pct()}

    async def _h_input(self, params):
        txt = params.get("text","")
        qid = self.queue.append(txt, "console").value
        await self.tail.emit({"type":"task.start","id":qid})
        # TODO: schedule runner to process; return queued id
        return {"queued": True, "qid": qid}

    async def _h_prompt_reload(self, _):
        self.prompts.reload_from_disk()
        await self.tail.emit({"type":"warn","msg":"system prompt reloaded"})
        return {"ok": True}

    async def _h_kb_ingest(self, params):
        # TODO: call KBAdapter.ingest
        return {"ok": True}
```

---

## GJ. Console app main loop (glue)

`ateam/console/app.py` (excerpt)
```python
import asyncio
from .palette import ConsoleUI
from .cmd_router import CommandRouter
from ..mcp.registry import MCPRegistryClient
from ..mcp.ownership import OwnershipManager
from ..util.logging import log

class ConsoleApp:
    def __init__(self, redis_url: str, use_panes: bool = False) -> None:
        self.registry = MCPRegistryClient(redis_url)
        self.ownership = OwnershipManager(redis_url)
        self.ui = ConsoleUI(use_panes=use_panes)
        self.router = CommandRouter(self, self.ui)
        self._running = False
        self._sessions = {}

    def run(self) -> None:
        self._running = True
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._run())
        loop.close()

    async def _run(self) -> None:
        self.ui.notify("Connected. Press F1 to list agents.", "info")
        while self._running:
            line = self.ui.read_command()
            if line == "":
                await asyncio.sleep(0.02); continue
            self.router.execute(line)

    def shutdown(self) -> None:
        self._running = False
```

---

## GK. Final integration smoke (script)

`smoke.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
docker run -d --rm -p 6379:6379 --name ateam-redis redis:7
python -m flit build
pipx install --force dist/ateam-*.whl
ateam agent --project demo --name zeus --cwd .
# new terminal:
ateam console
```

---

## GL. Acceptance "Definition of Done" (granular)

- [x] `os.exec` streams PTY output; `/interrupt` stops long process.
- [x] `#` overlays a line; `/reloadsysprompt` reflects on next turn.
- [x] Duplicate agent is rejected (exit code 11); log message printed.
- [x] Ownership: second console denied; `--takeover` works; banners update.
- [ ] Build & publish to TestPyPI; install via pipx on Windows & Linux; smoke passes.

---

## GM. Acceptance Testing (Validation Tasks)

> These are validation/smoke test steps to verify the implementation works correctly.

- [ ] Start 1 agent + console; `/attach` renders tokens from a dummy echo model.
- [ ] KB ingest dedupes; `/kb search` returns hits.
- [ ] Offload wizard creates agent; registration appears in palette; attach works.





---
