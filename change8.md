# Appendices — Deep Design Details (continuation of Draft v5, Part 7)

> This continues the same `change.md` spec. Everything below is additive and can be appended to the previous file.

---

## DZ. Message size limits, chunking & streaming hygiene

### DZ1. Size ceilings
- **RPC request/response** payloads: hard-limit **256 KiB** per message (after msgpack).
- **TailEvent token frames**: soft-limit **8 KiB** per frame; coalescer splits larger chunks.
- **KB ingest**: paths list max **512 entries** per call; larger batches must paginate.

### DZ2. Chunking rules
- If a tool needs to return >256 KiB (e.g., `fs.read` of a large file), it **streams** via TailEvents:
  - Emit `{"type":"tool","name":"fs.read","input":{...}}`
  - Follow with `{"type":"token","text":"<base64-chunk>", "model":"tool:fs.read"}` frames
  - Terminate with `{"type":"task.end","id":"t-xyz","ok":true}`
- Console detects `model:"tool:*"` and switches to **binary decode** mode for that tool view.

### DZ3. Truncation policy
- RPC route: on oversized payload, agent returns:
  ```json
  {"ok":false, "error":{"code":"payload.too_large","message":"payload exceeds 256KiB"}}
  ```
- Tail route: never truncates silently; always splits.

---

## EA. Redis reconnect & resilience

### EA1. Exponential backoff
- Initial delay 250ms → max 5s, jitter 25%.
- Console/Agent both retry on:
  - transient `ConnectionError`
  - `TimeoutError` on pub/sub
- After **5 consecutive failures**, emit `warn` TailEvent.

### EA2. Subscription rejoin
- On reconnect, Console re-subscribes to:
  - `mcp:tail:{agent}`
  - outstanding RPC `res_ch` channels (with req timeout cancellation)

### EA3. Heartbeat grace
- Agent heartbeats every **3s**; TTL=10s.
- Console marks **disconnected** after **>10s** since last beat; clears when heartbeat resumes.

---

## EB. Windows path canonicalization & symlink policy

- Canonicalize with `Path.resolve(strict=True)` where available.
- Deny symlink targets **outside sandbox** even if path prefix matches.
- UNC normalization:
  - `\\Server\Share\path` → canonical; check share root against whitelist if provided.

---

## EC. Model adapters — structure & stubs

```
ateam/llm/
  base.py               # LLMClient Protocol
  providers/
    openai.py           # class OpenAIClient(LLMClient)
    lmstudio.py         # class LmStudioClient(LLMClient)
    ollama.py           # class OllamaClient(LLMClient) [optional]
```

### EC1. Adapter interface (recap)
```python
class LLMClient(Protocol):
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]: ...
    def stream(self, prompt: str, **kwargs) -> Iterable[StreamChunk]: ...
```

### EC2. OpenAI adapter (sketch)
```python
class OpenAIClient:
    def __init__(self, model: str, api_key: str, **kw): ...
    def generate(self, prompt: str, **kw) -> Dict[str, Any]:
        # call chat.completions with messages=[{"role":"system"...},...]
        # return {"text": full_text, "usage": {"in": t_in, "out": t_out}}
    def stream(self, prompt: str, **kw) -> Iterable[StreamChunk]:
        # yield small chunks with .text and .tokens (approximate)
```

### EC3. LM Studio / Ollama
- HTTP local endpoints; stream via SSE.
- Provide `timeout` and `stop` token controls.

---

## ED. Summarization prompts (concrete)

### ED1. Internal template for history compaction
```
SYSTEM: You compress past conversation turns into a factual outline.
- Keep filenames, code identifiers, numeric values.
- No speculation, no new facts.
- Max ~{target_tokens} tokens.

INPUT:
<RECENT TURNS>
- {t-3} user: ...
- {t-2} assistant: ...
- {t-1} tool(fs.read): path=...

OUTPUT:
- Bullet 1
- Bullet 2
- ...
```

### ED2. Guardrail
- If LLM returns > `target_tokens * 1.2`, retry once with stricter instruction, else keep raw turns.

---

## EE. Config Pydantic models (schemas)

```python
# ateam/config/schema_agents.py
from pydantic import BaseModel, Field
from typing import List, Optional

class PromptCfg(BaseModel):
    base: str
    overlay: Optional[str] = None

class ScratchpadCfg(BaseModel):
    max_iterations: int = Field(ge=1, default=3)
    score_lower_bound: float = Field(ge=0, le=1, default=0.7)

class ToolsCfg(BaseModel):
    allow: List[str] = []
    deny: List[str] = []

class AgentCfg(BaseModel):
    name: str
    model: str
    prompt: PromptCfg
    scratchpad: Optional[ScratchpadCfg] = None
    tools: Optional[ToolsCfg] = None
```

```python
# ateam/config/schema_models.py
class ModelEntry(BaseModel):
    provider: str
    context_window_size: int
    default_inference: dict = {}
    model_settings: dict = {}

class ModelsYaml(BaseModel):
    models: dict[str, ModelEntry]
```

---

## EF. Command handlers signatures (Console)

```python
# ateam/console/handlers.py
from ..util.types import Result

def cmd_ps(ctx, args: str) -> Result[None]: ...
def cmd_attach(ctx, args: str) -> Result[None]: ...
def cmd_detach(ctx, args: str) -> Result[None]: ...
def cmd_offload(ctx, args: str) -> Result[None]: ...
def cmd_agent_new(ctx, args: str) -> Result[None]: ...
def cmd_kb_add(ctx, args: str) -> Result[None]: ...
def cmd_kb_search(ctx, args: str) -> Result[None]: ...
def cmd_kb_copy_from(ctx, args: str) -> Result[None]: ...
def cmd_ctx(ctx, args: str) -> Result[None]: ...
def cmd_sys_show(ctx, args: str) -> Result[None]: ...
def cmd_sys_edit(ctx, args: str) -> Result[None]: ...
def cmd_reloadsysprompt(ctx, args: str) -> Result[None]: ...
def cmd_models(ctx, args: str) -> Result[None]: ...
def cmd_use(ctx, args: str) -> Result[None]: ...
def cmd_save(ctx, args: str) -> Result[None]: ...
def cmd_tools(ctx, args: str) -> Result[None]: ...
def cmd_ui_panes(ctx, args: str) -> Result[None]: ...
def cmd_quit(ctx, args: str) -> Result[None]: ...
```

- `ctx` exposes `ConsoleApp`, `ConsoleUI`, `MCPRegistryClient`, and an optional current `AgentSession`.

---

## EG. Unit test snippets (more)

`tests/test_queue_jsonl.py`
```python
from ateam.agent.queue import PromptQueue
def test_append_pop(tmp_path):
    q = PromptQueue(str(tmp_path/"queue.jsonl"))
    rid = q.append("hello", "console").value
    it = q.peek().value; assert it and it.id == rid
    got = q.pop().value; assert got and got.text == "hello"
```

`tests/test_ownership.py`
```python
from ateam.mcp.ownership import OwnershipManager
def test_owner_cycle(redis_url):
    own = OwnershipManager(redis_url)
    t1 = own.acquire("demo/zeus").value
    assert own.is_owner("demo/zeus", t1)
    t2 = own.acquire("demo/zeus", takeover=True).value
    assert own.is_owner("demo/zeus", t2)
```

---

## EH. Knowledge Base — doc id & metadata spec

- **DocId**: `sha256[:12] + "-" + basename[:24].lower()` (safe for display)
- Metadata minimal set:
  ```json
  {
    "id": "a1b2c3d4e5f6-setup.md",
    "path": "/abs/path/setup.md",
    "hash": "a1b2c3...fe",
    "mtime": 1724231112.12,
    "scope": "agent",
    "size": 12034,
    "provenance": "myproj/builder"
  }
  ```

---

## EI. Task planning (optional, explicit)

- Agents may output a **plan.md** (stored under agent state).
- Console `/plan` commands:
  - `read`: prints plan
  - `write`: replaces file (confirm)
  - `append`: adds bullet(s)
  - `delete`: removes file (confirm)
- No implicit execution; plans are just text aids.

---

## EJ. Multi-redis support note

- We **do not** federate across Redis instances.
- Users may intentionally run multiple fleets by selecting different `--redis` URLs.
- Identity lock is per-Redis; duplicates across instances are allowed by design.

---

## EK. Example: sandbox escape test (code)

```python
from ateam.util.paths import resolve_within
import pytest

def test_symlink_escape(tmp_path):
    base = tmp_path/"sandbox"; base.mkdir()
    outside = tmp_path/"outside"; outside.mkdir()
    target = outside/"secret.txt"; target.write_text("x")
    sneaky = base/"link"; sneaky.symlink_to(target)
    with pytest.raises(Exception):
        resolve_within(str(base), str(sneaky))
```

---

## EL. Panic recovery (agent watchdog)

- If `queue_worker_task` crashes:
  - Emit `error` TailEvent with traceback.
  - Auto-restart worker after 1s (single cycle).
  - If it crashes again within 5s, escalate to `agent.stop` and exit with code 15.

---

## EM. Console UX — minimal rendering rules

- Prefix stream lines:
  - `[token]` for model chunks
  - `[tool]` for tool calls
  - `[warn]`, `[error]` for signals
- Compact timestamps disabled by default; enable with `--log-level debug`.

---

## EN. Model token counting

- `tokenizer.py`:
  - Provides best-effort token count for supported models; fallback to char/4.
  - Used by `MemoryManager` to compute `ctx_pct` and summarization threshold trip.

---

## EO. Diff safety

- Before applying edits:
  - Ensure file hasn't changed since `fs.read` baseline (`mtime` & `hash`).
  - If changed, abort with `tool.denied` and show 3-way merge hint.

---

## EP. MCP method catalog (final)

- Agent methods:
  - `status`, `tail`, `input`, `interrupt`, `cancel`, `prompt.set`, `prompt.reload`, `kb.ingest`, `kb.copy_from`, `memory.stats`
- Orchestrator (console-side helper, non-RPC):
  - `agents.list`, `agents.spawn`, `create_agent`, `remote_cmd`
- No hidden methods. Any expansion must be added to catalog & allowed lists.

---

## EQ. Flit deployment script — enhancements

`deploy_to_pypi.py` improvements:
- `--repository` flag to target **TestPyPI**.
- Pre-flight: verify `CHANGELOG` bump and git working tree clean.

```python
import argparse, subprocess, sys, os

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repository", default="pypi", choices=["pypi","testpypi"])
    args = ap.parse_args()

    token = os.getenv("FLIT_PASSWORD")
    if not token:
        print("Set FLIT_PASSWORD to your (Test)PyPI token."); sys.exit(1)

    subprocess.run([sys.executable, "-m", "flit", "build"], check=True)
    repo_arg = ["--repository", args.repository] if args.repository != "pypi" else []
    subprocess.run([sys.executable, "-m", "flit", "publish", *repo_arg], check=True)

if __name__ == "__main__":
    main()
```

---

## ER. Final adoption playbook (1-day sprint)

**Morning**
1. Scaffold `ateam/` per layout; add `pyproject.toml`.
2. Implement Redis transport & MCP server/client minimal.
3. Spin up agent that registers + heartbeats.

**Afternoon**
4. Implement Console attach + tail render + input RPC.
5. Add single `os.exec` tool; run `echo hello` via agent.
6. Persist history/queue JSONL; add `/reloadsysprompt`.

**End of day**
7. Offload wizard stub; KB ingest stub.
8. Tag `v0.1.0a1`; publish to **TestPyPI** via `deploy_to_pypi.py --repository testpypi`.

---

## ES. What “explicit” means (short canon)

- **No** automatic agent creation → always via `/agent new` or `/offload` (with confirm).
- **No** silent KB ingestion → always `/kb add` or `/kb copy-from`.
- **No** hidden prompt changes → only `#` or `/sys edit` + `/reloadsysprompt`.
- **No** automatic destructive ops (write/overwrite/delete) without explicit confirmation.

---

## ET. Source of truth recap

- Runtime fleet: **Redis registry** (TTL heartbeats).
- Identity: `project/name` from `.ateam` + overrides.
- State: on-disk JSONL per agent under `.ateam/agents/<name>/state/`.
- Prompts: `system_base.md` + `system_overlay.md` merged with protected toolbox.
- Config: merged `.ateam` stack (CWD→parents→home).

---

## EU. Closing note

The design is now **implementation-grade**: fully object-oriented, explicit control surfaces, resilient MCP over Redis, reproducible packaging, and a phased plan with checklists. Cursor can scaffold from the class/method signatures directly and iterate feature-by-feature without ambiguity.

---
