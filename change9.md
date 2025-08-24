# Appendices — Deep Design Details (continuation of Draft v5, Part 8)

> This continues the same `change.md` spec. Everything below is additive and can be appended to the previous file.

---

## EV. Constants & enumerations (centralized)

`ateam/util/const.py`
```python
from enum import Enum

class TailType(str, Enum):
    TOKEN = "token"
    TOOL = "tool"
    WARN = "warn"
    ERROR = "error"
    TASK_START = "task.start"
    TASK_END = "task.end"

class AgentState(str, Enum):
    INIT = "init"
    REGISTERED = "registered"
    IDLE = "idle"
    BUSY = "busy"
    DISCONNECTED = "disconnected"
    SHUTDOWN = "shutdown"

DEFAULTS = {
    "HEARTBEAT_INTERVAL_SEC": 3,
    "HEARTBEAT_TTL_SEC": 10,
    "RPC_TIMEOUT_SEC": 15.0,
    "TAIL_COALESCE_MS": 50,
    "PTY_READ_IDLE_MS": 15,
    "HISTORY_MAX_BYTES": 50 * 1024 * 1024,
    "SUMMARY_TARGET_TOKENS": 400,
    "SUMMARIZE_THRESHOLD": 0.75,
    "MAX_RPC_PAYLOAD": 256 * 1024,          # 256 KiB
    "MAX_TAIL_FRAME": 8 * 1024,             # 8 KiB
}
```

---

## EW. JSON Schemas (RPC & TailEvent)

`schemas/rpc_request.schema.json`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MCP RPC Request",
  "type": "object",
  "required": ["req_id", "method", "params", "ts", "caller"],
  "properties": {
    "req_id": { "type": "string" },
    "method": { "type": "string" },
    "params": { "type": "object" },
    "ts":     { "type": "number" },
    "caller": { "type": "string" },
    "timeout_sec": { "type": "number", "minimum": 0 }
  },
  "additionalProperties": false
}
```

`schemas/rpc_response.schema.json`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MCP RPC Response",
  "type": "object",
  "required": ["req_id", "ok"],
  "properties": {
    "req_id": { "type": "string" },
    "ok": { "type": "boolean" },
    "value": { "type": ["object","array","string","number","boolean","null"] },
    "error": {
      "type": "object",
      "required": ["code","message"],
      "properties": {
        "code": { "type": "string" },
        "message": { "type": "string" },
        "detail": { "type": "object" }
      },
      "additionalProperties": false
    },
    "ts": { "type": "number" }
  },
  "additionalProperties": false
}
```

`schemas/tail_event.schema.json`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "TailEvent",
  "type": "object",
  "required": ["type"],
  "properties": {
    "type": { "enum": ["token","tool","warn","error","task.start","task.end"] },
    "text": { "type": "string" },
    "name": { "type": "string" },
    "input": { "type": "object" },
    "msg": { "type": "string" },
    "trace": { "type": "string" },
    "id": { "type": "string" },
    "prompt_id": { "type": "string" },
    "ok": { "type": "boolean" },
    "model": { "type": "string" },
    "trace_id": { "type": "string" }
  },
  "additionalProperties": false
}
```

---

## EX. Prompt-toolkit integration details (Console)

### EX1. Input session wiring
```python
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import Completer, Completion

class PTCompleter(Completer):
    def __init__(self, adapter): self.adapter = adapter
    def get_completions(self, document, complete_event):
        buf, pos = document.text, document.cursor_position
        new_buf, cands = self.adapter.complete(buf, pos)
        # Only show cands if multiple
        for c in cands:
            yield Completion(c, start_position=-len(document.get_word_before_cursor()))

kb = KeyBindings()

@kb.add('f1')
def _f1(event): event.app.exit(result="__F1__")

@kb.add('tab')
def _tab(event): event.app.current_buffer.complete_next()

session = PromptSession(completer=PTCompleter(ConsoleCompleter(...)), key_bindings=kb)
```

### EX2. Event loop glue
- Run `session.prompt_async()` in a loop; if result is `"__F1__"`, open palette.
- Use `asyncio.Queue` to send lines into `CommandRouter`.

---

## EY. Windows launcher tips

- Provide `ateam.exe` via console_scripts entry point.
- Ensure `PYTHONIOENCODING=UTF-8` for correct Unicode.
- For PowerShell users, advise installing via **pipx**:
  ```
  pipx install ateam
  ```

---

## EZ. Secrets, redaction & env isolation

- Redaction rules live in `~/.ateam/redact.yaml` (optional):
  ```yaml
  patterns:
    - '(?i)api[_-]?key\\s*[:=]\\s*[A-Za-z0-9_\\-]{20,}'
    - 'sk-[A-Za-z0-9]{20,}'
  ```
- Agents sanitize:
  - TailEvents (`token`, `tool`, `error`).
  - Logs.
- Env isolation:
  - Agent inherits environment, but tools **do not** print env; `os.exec` starts with minimal env unless `--inherit-env` flag in config.

---

## FA. Privacy & data retention

- Local-only storage by default under `.ateam/agents/<name>/state/`.
- Rotation limits prevent unbounded growth.
- User may set `retention.days` (e.g., 30) to purge rotated history older than N days via periodic maintenance task.

---

## FB. File watchers (overlay auto-reload)

- Agent watches `system_base.md` and `system_overlay.md` (poll every 1s; no heavy watchdog dependency).
- If mtime changes and agent is **idle**, auto-trigger `prompt.reload`; if **busy**, queue a `sys-reload` sentinel after current task.

---

## FC. Autocomplete implementation notes

- For path completion:
  - Respect quotes and spaces.
  - On Windows, replace `/` with `\` visually, but accept either.
- For command completion:
  - Provide **subcommand** completion: `/kb <TAB>` → `add`, `search`, `copy-from`.
- Speed:
  - Cache agent IDs for 500ms; invalidate on registry events.

---

## FD. Performance tests (scripts)

- `bench_tail_latency.py`:
  - Simulates token stream at 1k tokens/sec from a dummy agent; measures p50/p95 render latency.
- `bench_queue_io.py`:
  - Appends 100k JSONL lines and measures fsync cost; asserts < 10ms per append on SSD.

---

## FE. Multi-agent docker-compose demo (extended)

```yaml
version: "3.9"
services:
  redis:
    image: redis:7
    ports: ["6379:6379"]
  zeus:
    build: .
    command: ["agent","--project","myproj","--name","zeus","--cwd","/workspace"]
    environment: ["ATEAM_REDIS_URL=redis://redis:6379/0"]
    volumes: ["./:/workspace"]
    depends_on: ["redis"]
  builder:
    build: .
    command: ["agent","--project","myproj","--name","builder","--cwd","/workspace"]
    environment: ["ATEAM_REDIS_URL=redis://redis:6379/0"]
    volumes: ["./:/workspace"]
    depends_on: ["redis"]
```

---

## FF. Log correlation identifiers

- `session_id` (Console) — random on startup.
- `owner_token` — returned by OwnershipManager; include in logs for mutate ops.
- `trace_id` — per `/input`; propagates to Tool events.

---

## FG. CLI help text (final copy)

```
/help
  Show commands.
  Tip: Press F1 to list agents; TAB completes commands, agent IDs, and file paths.

/ps [--json]
  List runtime agents and status. With --json prints machine-readable output.

/attach <project/agent> [--takeover]
  Attach to an agent and acquire write ownership. Use --takeover to claim from another console.

/kb add --scope agent|project|user <path|url>...
  Ingest documents into the selected KB scope. Explicit scope is required.

/reloadsysprompt
  Reload system prompt from disk (base + overlay). Use '#' to append overlay lines quickly.
```

(…full table already provided earlier; this copy is optimized for `--help`.)

---

## FH. Developer pitfalls & remedies

- **Symptom**: Double token rendering.  
  **Cause**: Both coalesced frames and raw chars being emitted.  
  **Fix**: Enable coalescer **or** raw mode, not both.

- **Symptom**: Ownership denial loop.  
  **Cause**: Stale owner key.  
  **Fix**: Use `/attach --takeover`; check Redis clock skew.

- **Symptom**: PTY deadlock on Windows.  
  **Cause**: ConPTY handle not drained.  
  **Fix**: Ensure reader thread runs even when no subscribers.

---

## FI. Roadmap after v0.1.0

- v0.2
  - Agent groups & broadcast `/input` to a group (explicit flag).
  - Read-only dashboard (`/tail <agent>` without ownership).
  - Rich/Textual panes enhancements (filter by `trace_id`).

- v0.3
  - Pluggable transports (ZeroMQ).
  - SSH helper to spawn remote agents via one command.
  - Optional **session replay** (render history as if live).

- v0.4
  - Structured “plan execution” mode (still explicit).
  - Signed agent configs for tamper detection.

---

## FJ. Appendix indices

- A: Class diagrams
- B: Redis Keys & Channels
- C: File Formats
- D: CLI Entrypoints
- …
- EU: Closing note
- EV–FJ: Advanced constants, schemas, PTK, Windows, privacy, perf, roadmap

> **End of Part 8** — if more detail is needed (e.g., full Pydantic models for every YAML file, or complete PTY executor code), we can append a Part 9 with those implementations.
