# Appendices — Deep Design Details (continuation of Draft v5, Part 6)

> This continues the same `change.md` spec. Everything below is additive and can be appended to the previous file.

---

## CV. File I/O durability, locking, and concurrency

### CV1. Atomic writes (POSIX & Windows)
- **Write-rename** pattern:
  1. Write to `*.tmp`
  2. `fsync(tmp_fd)`
  3. `os.replace(tmp, final)` (atomic on both platforms)
- Always use `os.open(..., O_CLOEXEC | O_CREAT | O_WRONLY, 0o600)` where available.

### CV2. Advisory file locks
- Use `portalocker` (cross-platform) for short critical sections; mode:
  - `LOCK_EX` for writers; `LOCK_SH` for readers.
- `queue.jsonl` and `history.jsonl`:
  - Writers hold lock only while appending a line; readers retry with small backoff (`5–10ms`) if locked.

### CV3. Monotonic IDs
- Generate monotonic, sortable IDs per file using **K-sorted** stamp:
  - `q-{timestamp_ms}-{counter:03x}` for queue items.
  - Derive `counter` from per-process incrementing int; reset on process start.

---

## CW. JSONL integrity & recovery

### CW1. Trailing partial lines
- On start, if last line of JSONL fails to parse, **truncate** file to last valid byte offset (scan backward up to 1 MiB).

### CW2. Crash-safe append
- After writing a line, call `os.fsync(fd)` **before** acknowledging the operation back to caller.

### CW3. Compaction
- For `queue.jsonl`, compaction rewrites **only** remaining (unprocessed) items to a fresh file using atomic replace.

---

## CX. Model selection strategy (smart switching)

### CX1. Heuristics (explicit first)
- If user sets model via `/use`, **stick** until changed.
- Else choose based on **task type** tags (the agent can self-tag):
  - `code_search`, `build_logs`, `triage`: prefer fast model.
  - `design_doc`, `complex_planning`: prefer larger model.
- Fallback: default from agent config.

### CX2. Token budgeting
- Query `MemoryManager.ctx_pct()`:
  - If `> 0.9`, **summarize** before next turn.
  - If `> 0.95`, refuse additional input until summarize completes; emit warning.

---

## CY. Tool execution constraints

### CY1. Time & resource limits
- Default tool timeouts:
  - `fs.*` 3s, `kb.*` 30s, `os.exec` user-configurable (default 300s).
- `os.exec`:
  - Set **CPU time** and **wall clock** timeouts (kill group on expiry).
  - Memory soft limit (where supported): cgroups on Linux (optional).
- Working directory **always** `agent.cwd`.

### CY2. Process groups
- Start subprocess in its own **process group**.
- `cancel(hard=True)` sends `SIGKILL` (POSIX) / `TerminateProcess` (Windows) to entire group.

---

## CZ. PTY streaming algorithm (outline)

```text
loop:
  read up to N bytes non-blocking from PTY
  if bytes:
     decode UTF-8 with 'replace' for partials
     buffer += text
     if '\n' seen or TAIL_COALESCE_MS elapsed:
         emit TailEvent{type:"token", text: buffered}
         buffer = ""
  else:
     sleep 10–20ms
```

- Ensure boundaries do not split multi-byte sequences; maintain small carry-over buffer.

---

## DA. Context reconstruction algorithm

1. Load `summary.jsonl` → select last `K` summaries until **target tokens** ≤ `S_MAX` (config).
2. Load last `N` raw turns from `history.jsonl` (not summarized).
3. Rebuild prompt:
   - `system_base + system_overlay + summaries + raw_tail`
4. Update `MemoryManager` counters accordingly.

---

## DB. Queue semantics

- **Single FIFO** queue per agent.
- One **worker** at a time (`queue_worker_task`), no parallel task execution.
- Add future `priority` field (default `0`) reserved; higher number → earlier dequeue (stable sort).
- `/queue clear` (agent REPL) requires confirm; not exposed via Console to avoid accidental global clears.

---

## DC. Crash recovery sequence (agent)

1. On boot, attempt `acquire_lock()`:
   - If held by stale instance (no heartbeat for `> TTL * 2`), allow **lock steal** with warning event.
2. Repair JSONL tails (CW1).
3. Publish `task.recover` event with counts: `{summaries_loaded, raw_turns_loaded}`.
4. Resume `IDLE`.

---

## DD. Traceability (trace_id propagation)

- Console assigns `trace_id` to each `/input` (UUID short).
- TailEvents inherit `trace_id` for correlation.
- Tool calls add `meta.trace_id` for end-to-end linkage in logs.

---

## DE. Plugin tools via entry points

- Third-party packages can register tools:
  - `pyproject.toml`
    ```toml
    [project.entry-points."ateam.tools"]
    aws.s3 = "ateam_aws.s3:toolset"
    ```
- Loader discovers entry points at startup and **registers** tools into `ToolRegistry` (deny by default; agents must allow-list).

---

## DF. Patch proposal flow for file edits

1. Agent calls `fs.read` target file(s).
2. Agent computes unified diff proposal (context 3 lines).
3. Console shows diff; user confirms `/apply` or rejects.
4. On confirm, agent calls `fs.write` with updated content.  
   - Optional: create `.bak` file first if configured.

---

## DG. Code style & quality

- Formatting: **Black** (line length 100).
- Ruff ruleset: `E,F,I,UP,ASYNC,ANN` (type annotation required in `ateam/*`).
- Mypy: `--strict` for `ateam/mcp/*`, `ateam/agent/*`, `ateam/console/*`.

---

## DH. Supported runtimes & deps

| Component | Python | Notes |
|---|---|---|
| Console | 3.9–3.12 | prompt-toolkit & Rich/Textual optional |
| Agent   | 3.9–3.12 | pywinpty on Windows |
| Redis   | 6.2+     | 7.x recommended |

---

## DI. Redis topology (prod)

- Prefer **Redis 7** with **ACL** and **TLS**.
- For HA:
  - Sentinel or Cluster; channels must be enabled.
  - Ensure pub/sub propagation over cluster (keyhash doesn’t matter for pub/sub).
- Config knobs:
  - `transport: { url, username, password, tls: true, ca_file? }`

---

## DJ. Bootstrap token security

- Generate 32-byte random token (hex).
- Store **hashed** token in Redis using `SHA-256`:
  - `mcp:agent:bootstrap:{id}:{hash}` with TTL (default 5 min).
- Agent receives plaintext token; hashes and compares; on success deletes key.

---

## DK. I18N & encoding

- All text handled as **UTF-8**.
- Ensure Windows code pages do not mangle input: force `PYTHONIOENCODING=UTF-8` in launcher if needed.

---

## DL. Default timeouts & limits (consolidated)

| Operation | Default |
|---|---|
| RPC call timeout | 15s |
| Ownership takeover grace | 2s |
| Heartbeat interval / TTL | 3s / 10s |
| KB ingest per file | 10s |
| `os.exec` wall timeout | 300s |
| PTY read idle sleep | 15ms |
| Tail coalesce window | 50ms |

---

## DM. Telemetry events (names)

- `agent.start`, `agent.stop`, `agent.recover`
- `task.start`, `task.end`, `task.error`
- `rpc.call`, `rpc.error`, `rpc.timeout`
- `ownership.acquire`, `ownership.release`, `ownership.takeover`
- `kb.ingest`, `kb.copy`
- `prompt.reload`, `prompt.overlay.append`

---

## DN. Example interactive transcript

```
$ ateam console
[info] Connected to redis://127.0.0.1:6379/0
F1
> agents: myproj/zeus (idle) …
Enter

/attach myproj/zeus
[ok] Attached (writer). Type to chat; /interrupt to stop current task.

Please configure and build with CMake + Ninja.
[tool] os.exec: cmake -S . -B build -G Ninja
[token] -- The C compiler identification is GNU 13.2.0
[token] CMake Error at CMakeLists.txt:14 (add_executable): …
[info] Consider /offload to a fresh 'builder' agent?

/offload
Proposed: name=builder, cwd=/work/myproj, model=gpt-5-nano, KB: 2 docs
Type 'create' to confirm: create
[ok] Spawned pid 28112. New agent: myproj/builder

/attach myproj/builder
# Prefer concise step-by-step plans.
[ok] Overlay appended.
```

---

## DO. Advanced FAQs

**Q: Can two consoles attach as writers to the same agent?**  
A: No. Exactly one writer. Others can `/tail` read-only or attempt `--takeover`.

**Q: Can an agent detach the console?**  
A: No. Only Console controls attach/detach. Agents expose no API to force-detach.

**Q: How are models configured per agent?**  
A: Via `agent.yaml` → `model:`; can override at runtime with `/use` then `/save` to persist.

**Q: Can I run agents across different Redis instances?**  
A: Yes, but they won’t see each other. That’s an intentional isolation boundary.

---

## DP. Structured RPC errors (schema)

```json
{
  "error": {
    "code": "ownership.denied",
    "message": "Write owner is another console.",
    "detail": {
      "owner": "console:abcd1234",
      "since": "2025-08-21T10:22:35Z"
    }
  }
}
```

- **Codes** are stable; clients should branch on `code`, not message.

---

## DQ. Tiny demo (`examples/hello/`)

```
examples/hello/
  .ateam/
    project.yaml         # name: hello
    models.yaml          # minimal
    agents/
      zeus/
        agent.yaml
        system_base.md
        system_overlay.md
  README.md              # step-by-step run guide
```

---

## DR. Diff rendering (console)

- Show colored unified diff using Rich.
- Keys:
  - `Y` apply, `N` cancel, `V` open in `$EDITOR`.

---

## DS. Sandbox test battery

- Paths:
  - `../../etc/passwd` → **denied**
  - `symlink -> /etc` then `symlink/passwd` → **denied**
  - `./sub/ok.txt` → **allowed**
- Programmatic tests live in `tests/test_sandbox.py`.

---

## DT. Minimal KB backend plug

- Default: **Chroma** (on-disk) with embeddings via LLM adapter.
- Interface allows swapping to **FAISS**; keep the adapter behind `KBAdapter`.

---

## DU. Console theming (optional)

- Themes file `~/.ateam/theme.toml` (not required):
  ```toml
  [colors]
  token = "cyan"
  tool = "magenta"
  warn = "yellow"
  error = "red"
  ```
- If missing, use Rich defaults.

---

## DV. Memory footprint tips

- Disable panes (`--no-ui`) over SSH.
- Lower history rotation size for low-disk environments.
- Turn off embeddings for KB if not needed.

---

## DW. Cross-version compatibility

- Serialize TailEvents and RPC envelopes using **msgpack** with explicit field names.
- Never remove a field; deprecate only after two minor versions; add new fields as optional.

---

## DX. End-to-end smoke checklist (developer)

- [x] Start Redis.
- [x] `ateam agent --project demo --name zeus --cwd .`
- [x] `ateam console` → `/attach demo/zeus`
- [x] Send text, see tokens.
- [x] `/reloadsysprompt` works.
- [x] `/offload` spawns builder; can attach to it.

---

## DY. Final polish & sign-off criteria

- Explicitness preserved (no hidden automations).
- Single-instance lock enforced reliably (tested).
- Ownership semantics race-free (tested takeover).
- KB selective copy only; no bulk implicit copies.
- Prompts reload and overlays applied live with protected blocks honored.
- Packaging builds clean with Flit; `ateam` entry point works on Windows/Linux.

---
