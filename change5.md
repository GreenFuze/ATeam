# Appendices — Deep Design Details (continuation of Draft v5, Part 4)

> This continues the same `change.md` spec. Everything below is additive and can be appended to the previous file.

---

## AY. RPC envelope, timeouts, and idempotency

### AY1. RPC envelope (Redis request/response)

**Request channel**: `mcp:req:{project}/{agent}`  
**Response channel**: `mcp:res:{project}/{agent}:{req_id}`

```json
{
  "req_id": "r-9f2f6c98",
  "method": "input",
  "params": { "text": "build", "meta": { "source": "console" } },
  "ts": 1724230001.112,
  "caller": "console:{session_id}",
  "timeout_sec": 15.0
}
```

**Response**
```json
{
  "req_id": "r-9f2f6c98",
  "ok": true,
  "value": { "queued": true, "qid": "q-001" },
  "error": null,
  "ts": 1724230001.298
}
```

**Error**
```json
{
  "req_id": "r-9f2f6c98",
  "ok": false,
  "error": { "code": "ownership.denied", "message": "Write owner is another console." }
}
```

### AY2. Timeouts & retries

- Console default `timeout_sec=15` for single RPCs; configurable per command.
- **Idempotency**:
  - Methods that mutate state (`input`, `prompt.set`, `kb.ingest`) include a `req_id` used as idempotency key in agent-side cache for `EX 60s`.
  - On duplicate `req_id`, agent returns the same result (or `ok:true` no-op).
- Transport resiliency:
  - Console retries **once** on `redis.unavailable` within `2s`, then surfaces error.

---

## AZ. Tool registry & versioning

### AZ1. Naming convention
- Tool names are lowercase, dot-separated: `os.exec`, `fs.read`, `kb.ingest`, `agents.spawn`.
- Version suffix optional: `fs.read@v1`. Default `@v1`.

### AZ2. Registration API
```python
# ateam/tools/registry.py
ToolFn = Callable[[Dict[str, Any]], Dict[str, Any]]

registry.register("fs.read", fs.read)
registry.register("fs.write", fs.write)
registry.register("os.exec", os.exec)
registry.register("kb.ingest", kb.ingest)
```

### AZ3. Tool descriptors (for prompts)
Each tool exposes a short schema-like descriptor used to render `system_base.md` snippets:

```yaml
- name: fs.read
  doc: "Read file contents within the sandboxed cwd."
  args:
    path: { type: "string", required: true }
```

Agents include a compact “Toolbox” section in their system prompt constructed from allowed tools.

---

## BA. End-to-end scenario (worked example)

**Goal**: Build a C++ project, run tests, and offload test triage.

1) **Start console**:
```bash
ateam console --redis redis://127.0.0.1:6379/0
```
2) **Create agent**:
```
/agent new     # fill: project=myproj, name=zeus, cwd=/work/myproj, model=gpt-5-nano, base=system_base.md
```
3) **Attach & seed KB**:
```
/attach myproj/zeus
/kb add --scope agent ./docs ./CMakeLists.txt ./src
```
4) **Ask to build**:
```
Please configure and build with CMake + Ninja.
```
- Agent uses `os.exec` to run `cmake -S . -B build -G Ninja` then `cmake --build build -j`.
- Streams logs to console via `TailEvent(type="token"|"tool")`.

5) **On failures**, agent proposes **offload**:
```
/offload
# wizard proposes: name=builder, cwd=/work/myproj, KB doc IDs selected from errors
# confirm
```
6) **Attach builder**:
```
/attach myproj/builder
```
7) **Builder** fixes scripts using `fs.read/write`, re-runs build, then suggests **test triage offload** to `tester`.
8) **Selective KB copy** from `builder` to `tester` with only failing test logs:
```
/kb copy-from myproj/builder --ids testlog_12a3,testlog_12a4
```
9) **Tester** runs `ctest` via `os.exec`, isolates flaky tests, reports summary.

---

## BB. Service management (keep agents running)

### BB1. systemd unit (Linux)
`/etc/systemd/system/ateam-agent@.service`
```ini
[Unit]
Description=ATeam Agent %i
After=network-online.target redis.service

[Service]
Type=simple
Environment=ATEAM_REDIS_URL=redis://127.0.0.1:6379/0
WorkingDirectory=%h/projects/%i
ExecStart=/usr/bin/ateam agent --project myproj --name %i --cwd %h/projects/%i
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
```
Enable:
```bash
systemctl --user enable --now ateam-agent@builder
```

### BB2. Windows Task Scheduler
- Action: `ateam.exe agent --project myproj --name builder --cwd C:\work\myproj`
- Trigger: At logon or on demand.

---

## BC. Dockerization (optional)

**Dockerfile (agent image)**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir flit && python -m flit install --deps production
ENV ATEAM_REDIS_URL=redis://redis:6379/0
ENTRYPOINT ["ateam"]
CMD ["agent", "--project", "myproj", "--name", "builder", "--cwd", "/workspace"]
```

**Compose snippet**:
```yaml
services:
  redis:
    image: redis:7
    ports: ["6379:6379"]
  builder:
    build: .
    volumes: ["./:/workspace"]
    environment: ["ATEAM_REDIS_URL=redis://redis:6379/0"]
    depends_on: ["redis"]
    command: ["agent","--project","myproj","--name","builder","--cwd","/workspace"]
```

---

## BD. Bootstrap token semantics (remote spawn)

- `bootstrap_token` included in `AgentSpawnSpec` and printed in remote command.
- Agent validates token **once** at startup via `create_agent` nonce in Redis:
  - Key: `mcp:agent:bootstrap:{project}/{agent}:{token}`, value: `{expires_at}`.
  - On success, agent deletes key (one-time).
- Prevents unauthenticated strangers from joining fleet on shared Redis.

---

## BE. Rate limits & backpressure

- **Console → Agent**: throttle `input()` calls to **1 in-flight**; queue subsequent until response or timeout.
- **Agent → Tail**: coalesce `token` events if >200 msgs/sec into frames (join substrings) every 50ms.
- **os.exec** output: line-buffer with partial flush at 40ms to keep latency low.

---

## BF. Prompt layering with protected blocks

`system_base.md` and `system_overlay.md` support **protected blocks**:

```md
<!-- ateam-protect:start:toolbox -->
(Generated toolbox goes here)
<!-- ateam-protect:end:toolbox -->
```

- `append_overlay()` never writes inside protected blocks.
- `/sys edit` opens overlay; saves are validated to preserve protected regions.

---

## BG. Command reference (exhaustive)

| Command | Args | Description |
|---|---|---|
| `/help` |  | Show command list |
| `/ps` | `[--json]` | List runtime agents with state/host/model/ctx% |
| `/agents` |  | List configured agents (from `.ateam`) |
| `/attach` | `<project/agent> [--takeover]` | Attach and acquire write ownership |
| `/detach` |  | Detach current session |
| `/who` |  | Show current attached agent and ownership |
| `/spawn` | `<agent_name> [--project N] [--cwd D] [--model M]` | Spawn a local agent (confirm) |
| `/agent new` |  | Wizard to create agent (explicit) |
| `/offload` |  | Wizard to offload current task to fresh agent |
| `/input` | `<text>` | Send one message to attached agent (plain text works too) |
| `/interrupt` |  | Cooperative cancel of current task |
| `/cancel` | `[--hard]` | Cancel current task/tool (hard = force) |
| `/kb add` | `--scope S <path|url>...` | Ingest docs into KB (S ∈ agent/project/user) |
| `/kb search` | `--scope S <query>` | Search KB scope |
| `/kb copy-from` | `<project/agent> --ids <id1,id2,...>` | Selective copy by ids |
| `/plan` | `read|write|append|delete|list` | Manage optional `plan.md` |
| `/ctx` |  | Show tokens in context and ctx% |
| `/sys show` |  | Show effective system prompt (base + overlay) |
| `/sys edit` |  | Open overlay in `$EDITOR`, apply on save |
| `/reloadsysprompt` |  | Reload base+overlay from disk and apply |
| `#` | `<line>` | Append single overlay line and apply |
| `/models` |  | List available models |
| `/use` | `<model_id>` | Set model for current agent (ephemeral until `/save`) |
| `/save` |  | Persist current agent config to highest-priority `.ateam` |
| `/tools` |  | List allowed tools and MCP health |
| `/ui panes` | `on|off` | Toggle panes UI |
| `/quit` |  | Exit console |

---

## BH. Error codes (expanded)

| Code | Meaning | Common cause | Resolution |
|---|---|---|---|
| `redis.unavailable` | Redis not reachable | Wrong URL, server down | Check `ATEAM_REDIS_URL`, service status |
| `ownership.denied` | Another console owns writer | Attached elsewhere | Use `--takeover` or detach from other console |
| `agent.not_found` | Registry has no such id | Typo, agent offline | `/ps` again; check heartbeats |
| `duplicate.instance` | Single-instance lock held | Another identical agent running | Kill other or use different Redis |
| `config.invalid` | Bad YAML or schema | Missing fields | Fix YAML; run schema validator |
| `prompt.protected_violation` | Overlay edit touched protected block | Manual edit | Revert protected region |
| `kb.ingest.denied` | Path outside sandbox | Security policy | Whitelist path or move file |
| `tool.denied` | Tool not in allow-list | Misconfig | Add tool to allow-list in agent.yaml |
| `timeout` | RPC timed out | Long-running tool | Increase timeout or check agent logs |

---

## BI. Migration map from `backend/` and `agents_lab/`

| Source | Keep / Adapt | New location in `ateam/` |
|---|---|---|
| `backend/llm/*` | **Keep** (adapt to streaming interface) | `llm/*` |
| `backend/schemas.py` | **Keep** (split to `mcp/contracts.py` dataclasses) | `mcp/contracts.py` |
| `backend/kb/*` | **Keep** (trim HTTP bits) | `agent/kb_adapter.py` |
| `backend/prompt_manager.py` | **Adapt** (base/overlay + protected) | `agent/prompt_layer.py` |
| `backend/tools/*` | **Refactor** into tool registry | `tools/builtin/*` |
| `agents_lab/models/*` | **Keep** adapters (OpenAI, LM Studio, etc.) | `llm/providers/*` |
| `agents_lab/agent/*` | **Patterns only** (replace with AgentApp/Runner) | `agent/*` |
| `frontend/*` | **Drop** | — |

**Pitfalls**:
- Remove any Flask/FastAPI deps.
- Replace websocket streams with `TailEvent` over Redis.
- Ensure file paths are package-relative (under `ateam/`) for PyPI.

---

## BJ. Performance & tuning knobs

| Setting | Default | Description |
|---|---|---|
| `TAIL_COALESCE_MS` | 50 | Coalesce token events within this window |
| `OS_EXEC_PARTIAL_FLUSH_MS` | 40 | Flush PTY buffer even if line incomplete |
| `HISTORY_MAX_BYTES` | 50 MiB | Rotate history when exceeding this size |
| `SUMMARY_TARGET_TOKENS` | 400 | Target size per summary |
| `CONSOLE_RPC_TIMEOUT` | 15s | Default RPC timeout |
| `OWNERSHIP_TAKEOVER_GRACE` | 2s | Wait before takeover is final |

---

## BK. Example `.ateam` seed (ready to copy)

```
.ateam/
  project.yaml
  models.yaml
  tools.yaml
  agents/
    zeus/
      agent.yaml
      system_base.md
      system_overlay.md
```

**project.yaml**
```yaml
name: myproj
```

**models.yaml**
```yaml
models:
  gpt-5-nano:
    provider: openai
    context_window_size: 128000
    default_inference: { max_tokens: 4096, stream: true }
```

**tools.yaml**
```yaml
mcp:
  transport:
    kind: redis
    url: redis://127.0.0.1:6379/0
```

**agents/zeus/agent.yaml**
```yaml
name: zeus
model: gpt-5-nano
prompt:
  base: system_base.md
  overlay: system_overlay.md
tools:
  allow: [ "os.exec", "fs.read", "fs.write", "kb.ingest", "kb.copy_from" ]
```

**agents/zeus/system_base.md** (minimal)
```md
You are ZeUS, an engineering orchestrator. Be explicit; ask for confirmation before destructive actions.
```

**agents/zeus/system_overlay.md** (initially empty)
```md
<!-- ateam-protect:start:toolbox -->
<!-- toolbox generated here -->
<!-- ateam-protect:end:toolbox -->
```

---

## BL. Concrete TODOs for Cursor (seed files with content)

- [x] Create all package skeleton files per **Repository layout**.
- [x] Paste seed `.ateam` from **BK** into a sample project for local testing.
- [x] Implement `mcp/redis_transport.py` minimal pub/sub and request/response with timeouts.
- [x] Implement `mcp/server.py` with handlers for all MCP tool contracts.
- [x] Implement `console/app.py` command loop; wire `F1` and `TAB`.
- [x] Implement `agent/main.py` boot, lock, registry, heartbeat, REPL.
- [x] Implement `tools/builtin/os.py` PTY/ConPTY exec with sandbox checks.
- [x] Implement `agent/prompt_layer.py` with protected blocks merge.
- [x] Implement `deploy_to_pypi.py` and validate `flit build`.

---

## BM. Human-in-the-loop hooks

- Confirmation prompts for:
  - `/spawn`, `/agent new`, `/offload`, `/clearhistory`, any `--unsafe` op.
- Optional `review()` step: agent may propose a change (e.g., patch to file); Console shows diff, user confirms `y/N`.

---

## BN. Minimal telemetry for debugging (env-gated)

- If `ATEAM_DEBUG_TAIL=1`, include sequence numbers in `TailEvent` and print dropped-frame warnings.

---

## BO. Backward compatibility shims (temporary)

- Provide `ateam/compat/backend_adapter.py` to read legacy `models.yaml` and `agents.yaml` formats from `backend/`.
- Mark with `# TODO(tsvi): remove after migration`.

---

## BP. Licensing & notices

- Include LICENSE in wheel.
- If bundling LM Studio adapters, respect their licenses.
- Add `NOTICE` if any third-party code requires attribution.

---

## BQ. UX polish backlog

- `/ps --json` and `/agents --json` for scripting.
- `/tail <agent> [--since now-5m]` to view without attaching.
- Configurable themes for panes; monochrome fallback for dumb terminals.

---

## BR. Security checklist before first release

- [x] Redis auth required in production (ACL + TLS).
- [x] Sandbox enforced; denial-tested for path escapes & symlink hops.
- [x] Offload/creation flows cannot run without explicit confirm.
- [x] Ownership takeover path audited for race conditions.
- [x] Secrets redaction rules validated on sample logs.

---

## BS. Release notes template

```
## v0.1.0 (YYYY-MM-DD)
- Initial CLI console (F1 palette, TAB autocomplete).
- Agent runtime with Redis MCP, locks, heartbeats, ownership.
- KB ingestion (scoped) + selective copy.
- System prompt base+overlay with protected blocks and live reload.
- Offload wizard; local spawn & remote bootstrap token.
- Flit packaging + deploy script.
```

---
