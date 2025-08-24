# Appendices — Deep Design Details (continuation of Draft v5, Part 9)

> This continues the same `change.md` spec. Everything below is additive and can be appended to the previous file.

---

## FK. Complete configuration models (Pydantic) & loaders

> These models back `project.yaml`, `models.yaml`, `tools.yaml`, and merged runtime config.

### FK1. Project config

`ateam/config/schema_project.py`
```python
from pydantic import BaseModel, Field
from typing import Optional

class ProjectCfg(BaseModel):
    name: str = Field(min_length=1, description="Project logical name")
    description: Optional[str] = None
    retention_days: Optional[int] = Field(default=None, ge=1, le=365)
```

### FK2. Tools config (transport + allow/deny)

`ateam/config/schema_tools.py`
```python
from pydantic import BaseModel, Field, AnyUrl
from typing import List, Optional, Literal

class TransportCfg(BaseModel):
    kind: Literal["redis"] = "redis"
    url: AnyUrl = Field(description="Redis URL")
    username: Optional[str] = None
    password: Optional[str] = None
    tls: bool = False
    ca_file: Optional[str] = None

class ToolsPolicyCfg(BaseModel):
    allow: List[str] = Field(default_factory=list)
    deny: List[str] = Field(default_factory=list)
    unsafe: bool = False  # global unsafe toggle; keep False

class ToolsCfg(BaseModel):
    mcp: TransportCfg
    tools: ToolsPolicyCfg = Field(default_factory=ToolsPolicyCfg)
```

### FK3. Agent config (full)

`ateam/config/schema_agents.py`
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class PromptCfg(BaseModel):
    base: str
    overlay: Optional[str] = None

class ScratchpadCfg(BaseModel):
    max_iterations: int = Field(ge=1, default=3)
    score_lower_bound: float = Field(ge=0, le=1, default=0.7)

class FSWhitelistCfg(BaseModel):
    whitelist: List[str] = Field(default_factory=list)

class TelemetryCfg(BaseModel):
    prometheus_port: int = 0  # 0=disabled

class AgentCfg(BaseModel):
    name: str
    model: str
    prompt: PromptCfg
    scratchpad: Optional[ScratchpadCfg] = None
    tools: Optional[Dict[str, bool]] = None  # legacy; prefer ToolsPolicyCfg
    fs: Optional[FSWhitelistCfg] = None
    telemetry: Optional[TelemetryCfg] = None
```

### FK4. Models config

`ateam/config/schema_models.py`
```python
from pydantic import BaseModel, Field
from typing import Dict

class ModelEntry(BaseModel):
    provider: str
    context_window_size: int = Field(gt=0)
    default_inference: dict = {}
    model_settings: dict = {}

class ModelsYaml(BaseModel):
    models: Dict[str, ModelEntry] = {}
```

### FK5. Loader utilities

`ateam/config/loader.py`
```python
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from .schema_project import ProjectCfg
from .schema_models import ModelsYaml
from .schema_tools import ToolsCfg
from .schema_agents import AgentCfg
from .discovery import ConfigDiscovery
from .merge import ConfigMerger

def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text()) if path.exists() else {}

def load_stack(start_cwd: str) -> Tuple[Optional[ProjectCfg], ModelsYaml, ToolsCfg, Dict[str, AgentCfg]]:
    stack = ConfigDiscovery(start_cwd).discover_stack().value
    merger = ConfigMerger()

    # aggregate dicts across layers (highest→lowest)
    project_dicts: List[Dict[str, Any]] = []
    models_dicts:  List[Dict[str, Any]] = []
    tools_dicts:   List[Dict[str, Any]] = []
    agents_maps:   List[Dict[str, Any]] = []

    for root in stack:
        p = Path(root)
        project_dicts.append(load_yaml(p / "project.yaml"))
        models_dicts.append(load_yaml(p / "models.yaml"))
        tools_dicts.append(load_yaml(p / "tools.yaml"))

        agents_dir = p / "agents"
        if agents_dir.exists():
            m: Dict[str, Any] = {}
            for d in agents_dir.iterdir():
                if d.is_dir():
                    m[d.name] = load_yaml(d / "agent.yaml")
            agents_maps.append(m)

    project_merged = merger.merge_dicts(project_dicts)
    models_merged  = merger.merge_dicts(models_dicts)
    tools_merged   = merger.merge_dicts(tools_dicts)

    # Agent precedence: take full directory from highest layer if conflict
    agents: Dict[str, Any] = {}
    for m in agents_maps:
        for name, cfg in m.items():
            if name not in agents:
                agents[name] = cfg  # first occurrence is highest-priority

    project = ProjectCfg(**project_merged) if project_merged else None
    models  = ModelsYaml(**models_merged) if models_merged else ModelsYaml()
    tools   = ToolsCfg(**tools_merged) if tools_merged else None

    agent_objs: Dict[str, AgentCfg] = {k: AgentCfg(**v) for k, v in agents.items()}
    return project, models, tools, agent_objs
```

---

## FL. Tail offset protocol (reliable resume)

We define a **monotonic tail offset** per agent for Console resume and for “tail since N”.

- Redis key: `mcp:tail:offset:{agent}` → integer (ever-increasing; never resets)
- Every `TailEvent` is wrapped with:
  ```json
  { "offset": 12345, "event": { "type": "token", ... } }
  ```
- Console persists last seen offset per agent under local cache `~/.ateam/.console/tail_offsets.json`.

**RPC `tail(from_offset)` behavior**
- If `from_offset` is provided:
  - Server replays buffered events from **ring buffer** (in-memory; size configurable, e.g., last 2048 events) with offsets `>from_offset`.
  - Then subscribes live.
- If requested offset is older than server buffer, server emits a `warn` event: “tail gap; replay not available”.

> Agents maintain a small **in-memory ring buffer** only; durable replays are not guaranteed (history JSONL covers conversation content, not token-by-token frames).

---

## FM. Registry events & state transitions

**RegistryEvent.kind**
- `join` — new agent key appeared
- `update` — same id, payload changed (ctx%, model, host, etc.)
- `leave` — key expired (heartbeats missed)

**Console handling**
- `join`: add to list; optionally notify “Agent joined: …”
- `update`: patch card; refresh ctx% and state
- `leave`: mark **disconnected**; keep in list for 2 minutes for quick reattach; then purge

---

## FN. Monotonic clocks & time math

- Use `time.monotonic()` for durations/timeouts; do not compute with wall clock.
- When writing timestamps into JSONL, serialize **UTC ISO8601** via `datetime.now(timezone.utc).isoformat()`.

---

## FO. Thread-pool sizing & queues

- Single global `ThreadPoolExecutor` per process:
  - Agents: `max_workers = min(32, cpu_count()*5)` to handle PTY/FS read/write.
  - Console: `max_workers = 8` (rendering & file I/O are light).
- Use `asyncio.to_thread` over bespoke threads to integrate with loop.

---

## FP. Example: path resolver & sandbox

`ateam/util/paths.py`
```python
from pathlib import Path

class SandboxViolation(Exception): ...

def expand_user_vars(path: str) -> str:
    return str(Path(path).expanduser())

def resolve_within(base: str, candidate: str) -> str:
    base_p = Path(base).resolve(strict=True)
    cand_p = (base_p / candidate).resolve(strict=True) if not Path(candidate).is_absolute() else Path(candidate).resolve(strict=True)
    try:
        cand_p.relative_to(base_p)
    except ValueError as e:
        raise SandboxViolation(f"path escapes sandbox: {cand_p} !~ {base_p}") from e
    return str(cand_p)
```

---

## FQ. MCP server request dispatcher (sketch)

`ateam/mcp/server.py`
```python
class MCPServer:
    def __init__(self, redis_url: str, agent_id: str) -> None:
        self._transport = RedisTransport(redis_url)
        self._agent_id = agent_id
        self._tools: Dict[str, Callable[..., Any]] = {}
        self._handlers = {
            "status": self._handle_status,
            "tail": self._handle_tail,
            "input": self._handle_input,
            "interrupt": self._handle_interrupt,
            "cancel": self._handle_cancel,
            "prompt.set": self._handle_prompt_set,
            "prompt.reload": self._handle_prompt_reload,
            "kb.ingest": self._handle_kb_ingest,
            "kb.copy_from": self._handle_kb_copy_from,
            "memory.stats": self._handle_memory_stats,
        }

    def register_tool(self, name: str, fn: Callable[..., Any]) -> None:
        self._tools[name] = fn

    async def _serve(self):
        req_ch = f"mcp:req:{self._agent_id}"
        # subscribe & dispatch …
```

---

## FR. Sample built-in tools (interfaces)

`ateam/tools/builtin/os.py`
```python
from typing import Optional, Dict, Any
import subprocess, shlex, os, sys, threading

def exec(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload: { "cmd": str, "cwd"?: str, "timeout"?: int, "env"?: Dict[str,str], "pty"?: bool }
    returns: { "rc": int, "stdout": str, "stderr": str }
    """
    # TODO: implement PTY/ConPTY, sandbox cwd, timeouts, process groups.
    ...
```

`ateam/tools/builtin/fs.py`
```python
from typing import Dict, Any
from ateam.util.paths import resolve_within

def read(payload: Dict[str, Any]) -> Dict[str, Any]:
    path = resolve_within(payload["sandbox"], payload["path"])
    with open(path, "r", encoding="utf-8") as f:
        return {"content": f.read()}
```

---

## FS. Protected block utils

`ateam/agent/prompt_layer.py` (concept)
```python
TOOLBOX_START = "<!-- ateam-protect:start:toolbox -->"
TOOLBOX_END   = "<!-- ateam-protect:end:toolbox -->"

def _merge_protected(base_text: str, overlay_text: str, new_toolbox: str) -> str:
    # Ensure exactly one protected block; create if missing at end.
    ...
```

Rules recap:
- Never allow editing/removing start/end tags.
- If user attempts to remove → raise `prompt.protected_violation`.

---

## FT. Editor integration for `/sys edit`

- Resolve `$ATEAM_EDITOR` → `$EDITOR` → platform defaults:
  - Unix: `vi`
  - Windows: `notepad`
- Write overlay to temp path; open editor; on save and close:
  - Validate protected block
  - Atomically replace overlay

---

## FU. Console ownership banners

- When not owner but attached read-only:
  - Show `[read-only]` banner above input; sending text refuses with `ownership.denied`.
- On takeover by another console:
  - Show sticky banner “Ownership lost to {session_id}; you are now read-only.”

---

## FV. Example manpage stubs

`docs/ateam-console.1.md`
```md
% ATEAM-CONSOLE(1) | ATeam Manual

# NAME
ateam console - central console for multi-agent CLI system

# SYNOPSIS
**ateam console** [--redis URL] [--no-ui] [--panes] [--log-level LEVEL]
…
```

`docs/ateam-agent.1.md` similar.

---

## FW. Packaging: including static schemas

Add to `pyproject.toml`:
```toml
[tool.flit.sdist]
include = ["schemas/*.json", "docs/*.md"]

[tool.flit.metadata]
module = "ateam"
```

If using package data in wheel:
```toml
[tool.setuptools.package-data]
ateam = ["schemas/*.json", "docs/*.md"]
```
*(Flit will include files under the package by default; placing them under `ateam/schemas` is simplest.)*

---

## FX. Lint & type config files

`pyproject.toml` (append)
```toml
[tool.ruff]
line-length = 100
select = ["E","F","I","UP","ASYNC","ANN"]
target-version = "py39"

[tool.mypy]
python_version = "3.11"
strict = true
mypy_path = "ateam"
packages = ["ateam"]
```

---

## FY. Additional tests (high-signal)

- `test_tail_offsets_resume.py`: ensure replay after console restart resumes correctly when within ring buffer.
- `test_prompt_protected_violation.py`: editing overlay to remove markers raises error.
- `test_kb_dedupe.py`: ingest same file twice → one doc id, `skipped` list populated.
- `test_console_takeover_banner.py`: verify UI transitions to read-only on takeover.

---

## FZ. Structured logging helper

`ateam/util/logging.py`
```python
import json, sys, time, os

def log(lvl: str, where: str, msg: str, **kw):
    if os.getenv("ATEAM_LOG_FORMAT","json") == "json":
        rec = {"ts": time.time(), "lvl": lvl, "where": where, "msg": msg}
        rec.update(kw)
        sys.stdout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(f"[{lvl}] {where}: {msg} {kw}\n")
    sys.stdout.flush()
```

---

## GA. README outline (deliverable)

- What is ATeam?
- Install (pip / pipx)
- Quickstart (start Redis, run agent, run console)
- `.ateam` structure & precedence
- Working with agents (F1 attach, TAB autocomplete)
- Knowledge base (scopes, ingest, selective copy)
- System prompts (overlay, `#`, reload)
- Offload and creation wizards
- Security model (sandbox, ownership)
- Packaging & PyPI deploy (Flit + script)
- Troubleshooting

---

## GB. End-to-end demo transcript (KB + search)

```
/agent new
# (create 'research' agent)

/attach myproj/research
/kb add --scope agent ./papers ./notes.md
/kb search --scope agent "vector database architecture"
[token] 1) papers/pinecone-arch.md (score 0.82)
[token] 2) papers/chroma-design.md (0.77)
```

---

## GC. Minimal UX style guide (text-only)

- Keep lines under ~100 chars for terminals.
- Use `[ok]`, `[warn]`, `[error]` prefixes consistently.
- No flashing or beeps.
- Respect `$NO_COLOR` env var to disable ANSI colors.

---

## GD. Ownership healthcheck command

Add `/who` output example:
```
[who] attached: myproj/zeus (writer: yes)
owner: console:3b1a (you)
since: 2025-08-21T12:03:11Z
```

Read-only example:
```
[who] attached: myproj/zeus (writer: no)
owner: console:9f70 (other)
```

---

## GE. Upgrade & migration hints

- When bumping RPC fields, add feature flags:
  - `server_capabilities: ["tail.offsets","kb.copy.selective"]`
- Console checks capabilities and hides unsupported commands.

---

## GF. Final consistency checklist (impl ready)

- [x] All classes and methods from Parts **A–F** exist with exact signatures.
- [x] Console keybindings: **F1** palette, **TAB** autocomplete implemented.
- [x] Agent REPL keybindings: **F1** info/queue panel; **TAB** autocomplete.
- [x] Single-instance lock enforced with TTL refresh.
- [x] Ownership lock & takeover path enforced by server-side checks.
- [x] JSONL append with fsync before ack.
- [x] Protected block merge validated on `/sys edit` and `#`.
- [x] KB scope enforcement; sandbox path resolver in use for FS tools.
- [x] RPC envelope uses msgpack; payload limits enforced.
- [x] Tail offsets included and ring buffer present.
- [x] Flit packaging builds wheel; `ateam` entry point resolves.
- [x] `deploy_to_pypi.py` works against TestPyPI.

---

> **End of Part 9.** If you want, we can append **Part 10** with concrete minimal implementations for the MCP server loop, Redis ring buffer, the PTY executor, and the Console command handlers.
