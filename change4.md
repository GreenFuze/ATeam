# Appendices — Deep Design Details (continuation of Draft v5, Part 3)

> This continues the same `change.md` spec. Everything below is additive and can be appended to the previous file.

---

## AI. Signals, lifecycle, and graceful shutdown

### AI1. Process signals & behaviors

| Platform | Signal / Event      | Console behavior                                   | Agent behavior                                                     |
|---------:|----------------------|----------------------------------------------------|--------------------------------------------------------------------|
| Unix     | `SIGINT` (Ctrl+C)    | If attached: send `/interrupt` to agent; else quit | Forward cooperative cancel to `TaskRunner.interrupt()`             |
| Unix     | `SIGTERM`            | Graceful shutdown: detach sessions, close Redis    | Stop heartbeat, flush history, release lock, stop MCP server       |
| Unix     | `SIGHUP`             | Reload UI prefs (future: config)                   | Reload prompts (`PromptLayer.reload_from_disk()`); keep running    |
| Windows  | `CTRL_C_EVENT`       | Same as Unix `SIGINT`                              | Same as Unix `SIGINT` (via ConPTY)                                 |
| Windows  | `CTRL_CLOSE_EVENT`   | Graceful shutdown                                  | Graceful shutdown                                                  |

**Invariant**: agent **must** release single-instance lock and ownership keys on graceful exit.

### AI2. Zero-downtime agent restart

- Agent writes `mcp:agent:grace:{id}` with short TTL before stopping.
- Console seeing `grace` suppresses “disconnected” warnings for that id for N seconds.
- On restart, same id reacquires lock; registry key updated; Console reattaches stream seamlessly (if `--resume-last` later enabled).

---

## AJ. Storage rotation & retention

### AJ1. JSONL rotation

- `history.jsonl`:
  - Rotate when file size exceeds `HISTORY_MAX_BYTES` (default: 50 MiB) or number of lines exceeds `HISTORY_MAX_LINES`.
  - Rotation scheme: `history.jsonl.1`, `.2`, … up to `HISTORY_KEEP=5`.
- `queue.jsonl`:
  - Compact after N processed items (default every 100) to remove consumed entries (write fresh file from tail).
- `summary.jsonl`:
  - Append-only; capped to last `K` summaries (default 200). Prune older with exponential backoff.

### AJ2. Summarization algorithm

- Trigger when `MemoryManager.ctx_pct() >= summarize_threshold` (default 0.75).
- Strategy:
  1. Collect last M user/assistant turns (configurable).
  2. Prompt LLM: “compress to factual bullet outline; preserve IDs, filenames, numeric values.”
  3. Validate length ≤ `SUMMARY_TARGET_TOKENS` (default 400).
  4. Append to `summary.jsonl` with `[window]: [start_turn_idx, end_turn_idx]`.
  5. Drop those turns from active context; keep summary token(s) instead.

**Safety gates**:
- If summarization fails or exceeds length twice → keep original turns (never lose data).
- On restart, rebuild context: fold summaries + last N raw turns.

---

## AK. Knowledge base details

### AK1. Content hashing

- **SHA-256** over normalized content:
  - Normalize line endings (`\n`), trim trailing spaces, collapse multiple blank lines to 2.
  - Hash `sha256(normalized_bytes)`.
- **De-dup**: if hash exists in target scope, skip ingest; report in `skipped`.

### AK2. Ingestion pipeline

1. Resolve paths/URLs; for directories, include files by glob (configurable, default `**/*.{md,txt,py,c,cpp,h,java,cs,go,rs,js,ts,json,yaml,yml,cmake}`).
2. Optional pre-processors:
   - Code splitter by function/class (Python/C-like) → smaller chunks.
   - Markdown splitter by heading.
3. Chunking: target `CHUNK_TOKENS ~ 600`, overlap `OVERLAP_TOKENS ~ 80`.
4. Embedding model (provider-agnostic; reuse `llm` embedding adapter).
5. Indexing: store vectors under `{scope_root}/index/` (Faiss/Chroma on-disk).
6. Metadata: `{path, mtime, size, hash, scope, source_agent?, project?}`.

### AK3. Search

- KNN cosine similarity; top-K (default 8) with min score threshold (default 0.35).
- Return `KBHit{id, score, metadata}`; Console pretty-prints path & title.

### AK4. Selective copy

- `/kb copy-from <id> --ids a,b,c`:
  - Resolve source scope and read doc metadata/contents by ids.
  - Re-ingest into target scope; maintain provenance: `metadata.source = "<source_agent_id>"`.

---

## AL. Path sandbox rules

- Base sandbox root = agent `cwd`.
- Allowed:
  - Relative paths inside sandbox.
  - Absolute paths that resolve under sandbox after `realpath`.
- Denied by default:
  - Parent escapes (`..`) that resolve outside sandbox.
  - Symlink traversal to outside sandbox.
  - Special device files.
- Overrides:
  - Per-agent whitelist in `agent.yaml`:
    ```yaml
    fs:
      whitelist:
        - /tmp/allowed
        - C:\Users\Tsvi\work\shared
    ```
  - `/os exec --unsafe` disabled by default; if enabled, requires explicit confirmation in Console per command.

---

## AM. Windows/WSL specifics

- Path completion supports:
  - Drives: `C:\`, `D:\…`
  - UNC: `\\server\share\…`
  - WSL interop: `/mnt/c/User/...`; detection via `WSL_INTEROP` env.
- ConPTY:
  - Use `pywinpty` for interactive `os.exec`.
  - Fallback to non-pty if ConPTY unavailable (older Windows).

---

## AN. F1 palette wireframe (plain TTY)

```
┌───────────────────────────────────────────────────────────────────────┐
│  Agents (F1 to close)        Filter: myproj z                         │
├───────────────────────────────────────────────────────────────────────┤
│  myproj/zeus         running  ctx 32%   host devbox   model gpt-5     │
│  myproj/builder      idle     ctx  4%   host devbox   model gpt-5     │
│  myproj/research     busy     ctx 68%   host node2    model gpt-4o    │
│  other/sweeper       disc.    ctx  0%   host node3    model llama3    │
├───────────────────────────────────────────────────────────────────────┤
│  ↑↓ to navigate, Enter attach, T toggle tails, i info, d detach       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## AO. Command grammar (EBNF)

```
command      = slash_cmd | free_text ;
slash_cmd    = "/" verb [ WS args ] ;
verb         = ALPHA { ALNUM | "-" } ;
args         = token { WS token } ;
token        = quoted | bare ;
quoted       = DQUOTE { any - DQUOTE } DQUOTE
             | SQUOTE { any - SQUOTE } SQUOTE ;
bare         = { any - WS } ;
free_text    = { any - NEWLINE } ;
```

Parser is tolerant to extra spaces, supports quotes for paths with spaces.

---

## AP. Environment variables

| Variable            | Purpose                                        | Default                                   |
|---------------------|------------------------------------------------|-------------------------------------------|
| `ATEAM_REDIS_URL`   | Redis URL for MCP                              | `redis://127.0.0.1:6379/0`                |
| `ATEAM_LOG_LEVEL`   | `debug|info|warn|error`                         | `info`                                    |
| `ATEAM_EDITOR`      | Editor for `/sys edit`                          | `$EDITOR`                                 |
| `ATEAM_HISTORY_MAX` | Max history bytes before rotation               | `50_000_000`                               |
| `ATEAM_SUMMARY_K`   | Max summaries to keep                           | `200`                                     |
| `ATEAM_FS_WHITELIST`| Extra semi-colon separated whitelisted paths    | *(empty)*                                 |

---

## AQ. Telemetry & metrics (optional)

- Add optional dependency `prometheus_client`.
- Serve metrics on ephemeral local port (agent-only):
  - `ateam_agent_tokens_total{agent_id=...}`
  - `ateam_tail_latency_ms_bucket{le="..."}` histogram
  - `ateam_queue_depth{agent_id=...}`
- Disabled by default; enable via `agent.yaml`:
  ```yaml
  telemetry:
    prometheus_port: 0   # 0 = disabled; else port number
  ```

---

## AR. Security threat model (concise)

- **Asset**: user files under `cwd`, secrets in env, Redis contents.
- **Adversary**: malicious prompt/tool call trying to exfiltrate or delete data.
- **Controls**:
  - FS sandbox + whitelist only.
  - Tool allow/deny lists per agent; deny by default any unknown tool.
  - Secrets redaction in stream/logs (regex).
  - Redis authentication (ACL) + TLS option.
  - Explicit confirmations for offload/creation and `--unsafe` operations.
- **Residual risk**: model hallucination; mitigate via confirmations and constrained tools.

---

## AS. Developer tooling

### AS1. Pre-commit

`.pre-commit-config.yaml`
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.8.0
    hooks: [{ id: black }]
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.2
    hooks: [{ id: ruff }]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks: [{ id: mypy, additional_dependencies: ["types-redis"] }]
```

### AS2. Makefile (optional)

```make
.PHONY: dev test build publish lint type

dev:
\tpython -m ateam.console --redis $(REDIS)

lint:
\truff check ateam

type:
\tmypy ateam

test:
\tpytest -q

build:
\tpython -m flit build

publish:
\tFLIT_USERNAME=__token__ FLIT_PASSWORD=$$PYPI_TOKEN python deploy_to_pypi.py
```

### AS3. GitHub Actions (CI)

`.github/workflows/ci.yml`
```yaml
name: ci
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install flit ruff mypy pytest redis msgpack typer rich textual pyyaml
      - run: ruff check ateam
      - run: mypy ateam
      - run: pytest -q
      - run: python -m flit build
```

---

## AT. Cursor-specific guidance

- Generate files in the paths listed under **Repository layout**; keep module names exact.
- Implement interfaces with `pass` and `TODO` comments first, then iterate per **Phases**.
- Use the **checkbox plan** as task list; keep updating file headers with `Status:`.

---

## AU. UX microcopy (Console)

- On duplicate instance:
  ```
  [sys] Another instance of {project}/{agent} is already registered on this Redis. Exiting.
  ```
- On ownership denied:
  ```
  [warn] {agent} is controlled by another Console. Use /attach {agent} --takeover to claim writer.
  ```
- On `/clearhistory`:
  ```
  [danger] This will permanently delete history for {agent}. Type '{agent}' to confirm:
  ```

---

## AV. Invariants & assertions

- Registry entry TTL must be renewed before expiration (heartbeat period < TTL/2).
- Exactly one writer (owner) exists per agent; all writes check `OwnershipManager.is_owner`.
- Queue `append` → `pop` monotonic: item id increases strictly.
- History append is fsynced before acknowledging completion to Console.

---

## AW. Glossary

- **Agent (process)** — autonomous worker exposing MCP tools over Redis; owns its REPL.
- **Console** — central CLI/TUI that attaches to agents, sends input, and renders streams.
- **MCP** — Model Context Protocol (here: JSON/RPC-like over Redis pub/sub).
- **Owner** — the single Console session with write privileges to an agent.
- **Prompt overlay** — append-only text merged on top of base system prompt.
- **KB** — vectorized knowledge base (per-scope) with selective ingestion/copy.
- **Offload** — moving a subtask into a newly created agent with a fresh context.

---

## AX. Final roadmap nudges

- After Phase 6 (KB) and Phase 7 (Prompts), prioritize **Phase 8** (Offload) to unlock truly fluid multi-agent workflows.
- Keep telemetry behind a flag; focus on correctness, explicit controls, and stability first.
- Once features stabilize, consider packaging `ateam` as a **plug-in host**: load third-party tool packs by entry points.

---
