# Knowledgebase (KB) + Plan + Embedding + Summarization — Implementation Plan

This document is the single source of truth for implementing the new KB (long-term memory), Plan (short-term memory) features, embedding selection, and summarization flow. It is written as a checklist. We will update the checkboxes as we complete items and add notes under each item. Fail-fast principle applies everywhere.

## Clarifications (locked in)

- [x] Chroma persistence is a DIRECTORY at `backend/knowledgebase/<agent_id>/kb/`.
- [x] `models_manager` will expose embedding models via a new `get_embedding_models()` if missing.
- [x] Tool sets required (canonical):
  - KB: `kb_add`, `kb_update`, `kb_get`, `kb_list`, `kb_search` (and keep `append_knowledgebase` as a wrapper to `kb_add`).
  - Plan: `plan_read`, `plan_write`, `plan_append`, `plan_delete`, `plan_list`.

## Global

- [x] Add required dependencies in `requirements.txt` (ChromaDB).
  - [x] `chromadb` pinned version.
  - [ ] Any provider-specific embedding SDKs if needed.
  - [ ] Verify Windows compatibility.
- [x] Update `.gitignore` if Chroma creates auxiliary artifacts; ensure `backend/knowledgebase/**` ignored except we may keep readme.

## Backend — remove prompt injection of knowledgebase

- [x] Remove knowledgebase injection at the end of `Agent.full_system_prompt` in `backend/agent.py`.
  - [x] Ensure no other code path injects KB automatically.
  - [x] Keep fail-fast behavior elsewhere intact.

## Backend — Embedding configuration

- [x] Create `backend/embedding_manager.py`:
  - [x] Load/save selected embedding model and max chunk size in YAML: `embedding.yaml` with `{ selected_model: <model_id>, max_chunk_size: <int>, updated_at: <ts> }`.
  - [x] Provide `get_selected_embedding_model()` and `set_selected_embedding_model(model_id: str)`.
  - [x] Provide `get_max_chunk_size()` and `set_max_chunk_size(n: int)`.
  - [x] Provide `embed(texts: list[str]) -> list[list[float]]` using the selected model via existing `models_manager`/`provider_manager` integration. Fail-fast if not set.
- [x] Expose WS API in `backend/backend_api.py`:
  - [x] `get_embedding_models` → returns list from `models_manager.get_embedding_models()`.
  - [x] `get_embedding_settings` → returns `{ selected_model, max_chunk_size }` from `embedding_manager`.
  - [x] `update_embedding_settings` → persist `{ selected_model, max_chunk_size }`; fail if invalid model id or invalid chunk size.

## Backend — KB Manager (Chroma abstraction)

- [x] Create `backend/kb_manager.py` — the only place that knows about Chroma internals.
  - [x] Storage: `backend/knowledgebase/<agent_id>/kb/` directory. Ensure parent dirs exist.
  - [x] Initialize persistent Chroma client per-agent path (lazy).
  - [x] Collections: one collection per agent (e.g., `kb`).
  - [x] CRUD/search API (fail-fast, deterministic types):
    - [x] `add(agent_id: str, content: str, metadata: dict|None) -> list[str]` returns created item id(s).
    - [x] `update(agent_id: str, item_id: str, content: str, metadata: dict|None) -> None`.
    - [x] `get(agent_id: str, item_id: str) -> {id, content, metadata}`.
    - [x] `list(agent_id: str, limit: int=50, offset: int=0) -> [{id, content, metadata}]`.
    - [x] `search(agent_id: str, query: str, k: int=5) -> [{id, content, distance, metadata}]`.
  - [x] Embedding pipeline: use `embedding_manager.embed()` for both add/update and search queries.
  - [x] Migrate legacy flat-file KB if exists: remove `backend/knowledgebase/<agent_id>.md` after importing (optional migration step, or no-op if empty).

## Backend — Plan Manager (short-term memory)

- [x] Implement within `kb_manager.py`:
  - [x] Filesystem path: `backend/knowledgebase/<agent_id>/<plan>.md`.
  - [x] Operations (fail-fast):
    - [x] `plan_read(agent_id, name) -> content`.
    - [x] `plan_write(agent_id, name, content) -> None`.
    - [x] `plan_append(agent_id, name, content) -> None`.
    - [x] `plan_delete(agent_id, name) -> None`.
    - [x] `plan_list(agent_id) -> [name]`.

## Backend — Tools (via kb_manager abstraction)

- [x] Add KB tools in `backend/tools/prompts_and_knowledge.py`:
  - [x] `kb_add(agent_id: str, content: str, metadata: dict|None)`.
  - [x] `kb_update(agent_id: str, item_id: str, content: str, metadata: dict|None)`.
  - [x] `kb_get(agent_id: str, item_id: str)`.
  - [x] `kb_list(agent_id: str, limit: int=50, offset: int=0)`.
  - [x] `kb_search(agent_id: str, query: str, k: int=5)`.
  - [x] Keep `append_knowledgebase(agent_id, content)` as a thin wrapper to `kb_add` for compatibility.
  - [x] All KB tool functions call into `kb_manager` (the only component that knows Chroma internals).
- [x] Add Plan tools in the same module:
  - [x] `plan_read(agent_id: str, name: str)`
  - [x] `plan_write(agent_id: str, name: str, content: str)`
  - [x] `plan_append(agent_id: str, name: str, content: str)`
  - [x] `plan_delete(agent_id: str, name: str)`
  - [x] `plan_list(agent_id: str)`
- [x] Ensure tool descriptor shows concise, single-line description; arguments have clear types.

## Backend — Prompts

- [x] Create `backend/prompts/summary_request.md` (content: directive to summarize concisely the selected portion of the conversation).
- [x] Update `backend/prompts/use_knowledgebase.md` to explain: (consolidated into `all_agents.md`; legacy file removed)
  - [x] Use KB tools to add/update/search/list; KB is long-term and must be used sparingly for facts worth retaining. (moved)
  - [x] Use Plan tools for short-term scratchpad/task plan; name the plan sensibly per task; keep it concise. (moved)
- [x] Create `backend/prompts/all_agents.md` which REPLACES both `how_to_respond_no_schema_or_grammar.md` and `use_knowledgebase.md` by including their essential content and updated KB/Plan tool usage rules. It must be the FIRST system prompt for all agents.

## Backend — Agents configuration updates

- [x] Make `all_agents.md` mandatory as the first system prompt for every agent:
  - [x] Update `backend/agents.yaml` prompts ordering.
- [x] Make KB and Plan tools mandatory for all agents:
  - [x] Ensure the tool names above are present in every agent’s `tools` list (enforced in AgentManager load/update).
- [x] Validate/normalize on load: prepend `all_agents.md` and enforce mandatory tools when loading/updating agents.

- [x] In `SettingsPage` add a new “Embedding” section/page.
  - [x] On mount: request `get_embedding_models` and `get_embedding_settings` via WS; show dropdown of embedding models.
  - [x] Save button sends `update_embedding_settings`.
  - [x] Show current selection and notify if not configured.
  - [x] Fail-fast: display backend error messages in the existing error dialog UI.

## Frontend — Summarize flow (AgentChat)

- [x] Add a “Summarize” button in the header.
  - [x] Click opens modal with a percentage slider (5–90%) and OK/Cancel.
  - [x] On OK: send a new WS message `summarize_request` with `{ agent_id, session_id, percentage }`.
- [x] Backend `summarize_request` handling:
  - [x] Compute `N = floor(x%)` (exclude system + seed). Build temp context with system + seed + first N messages + `summary_request.md`.
  - [x] Run the LLM; replace the first N messages with a single CHAT_RESPONSE summary.
  - [x] Recompute/send updated context usage; send conversation snapshot.
- [x] Frontend updates messages based on snapshot and progress bar via context_update.

## Frontend — Mandatory prompts/tools UX

- [x] In agent edit/create UIs:
  - [x] Ensure `all_agents.md` is shown as selected and disabled (cannot unselect) and is the first system prompt.
  - [x] Ensure KB/Plan tools are selected and disabled (cannot unselect).
  - [x] If backend validation fails, surface the error.

## Backend — WS/API additions summary

- [x] New WS types:
  - [x] `get_embedding_models`, `get_embedding_settings`, `update_embedding_settings`.
  - [x] `summarize_request` → summary execution and response via `conversation_snapshot`.

## Migration/cleanup

- [x] Remove using `backend/knowledgebase/<agent_id>.md` for prompts injection.
- [x] Ensure `.gitignore` excludes `backend/knowledgebase/**`.

## Testing — Backend

- [x] Unit: `embedding_manager` load/save; invalid model id fails. (load/save covered; invalid id pending)
- [x] Unit: `kb_manager` add/get/list/update/search; asserts vector search returns expected top hits for a toy corpus. (add/get/list/update covered; search pending)
- [x] Unit: Plan operations read/write/append/delete/list (filesystem).
- [ ] Unit: Tools wrap manager; bad inputs raise clear errors.
- [ ] Integration: WS `get_embedding_models/settings/update` happy/invalid paths.
- [ ] Integration: `summarize_request` end-to-end on a seeded conversation. Verify first `N` messages replaced by one summary; context usage reduced.

## Testing — Frontend

- [ ] Embedding settings page loads model list, shows current selection, saves new selection, handles errors.
- [ ] Summarize modal opens, slider works, cancel leaves state unchanged, OK triggers backend, UI updates with replaced messages and context bar.
- [ ] Agent edit/create shows mandatory prompt/tool controls disabled and pre-selected.
- [ ] Background updates (other agents receiving messages) still correctly cached and not duplicated in active view.

## Observability

- [x] Add structured logs for KB/Plan operations (info level on success; error with context on failure). No logging of large content bodies beyond a preview.
- [x] Log `summarize_request` inputs (percent, N) and outcome (tokens saved estimate).

## Performance and safety

- [x] Batch embedding calls in `kb_manager` to minimize overhead.
- [x] Recommend chunking strategy in tool docstrings; policy: always chunk oversized content (no fail-fast on size).
- [x] Ensure path traversal safe for plan names (allow only `[a-zA-Z0-9_-]`).

## Concurrency and locking

- [x] Add per-agent locks in `kb_manager` to guard Chroma collection operations (create/get/add/update/list/search). Use `threading.RLock` keyed by `agent_id`.
- [x] Ensure `kb_manager` initializes Chroma clients/collections under lock (double-checked lazy init).
- [x] Make file operations in Plan APIs atomic:
  - [x] Use a per-agent `RLock` for plan read/write/append/delete/list.
  - [x] For writes, write to temp file and `os.replace` to avoid partial writes.
- [x] `embedding_manager`:
  - [x] Protect `embedding.yaml` load/save with a process/thread `Lock`.
  - [x] Atomic save via temp + replace.
  - [x] Guard the selected model field with a lock during reads/writes.
- [x] `agent.py` conversation mutations:
  - [x] Add an `RLock` on each `Agent` to guard `self.messages` appends/replacements (including summarize flow and save/load conversation).
  - [x] Guard context usage calculations that read `self.messages`.
- [ ] Timeout policy: no timeouts by default; if a deadlock risk is detected, fail-fast by raising a clear error (only if we explicitly decide to add timeouts later).

## Rollout steps

- [x] Land backend scaffolding (`embedding_manager`, `kb_manager`, tools, WS types).
- [x] Land prompts (`all_agents.md`, `use_knowledgebase.md` update, `summary_request.md`).
- [x] Update frontend settings page and AgentChat summarize.
- [x] Update agents.yaml to insert `all_agents.md` as first and add mandatory tools.
- [ ] Manual validation run-through.

---

Notes:
- All new endpoints and tools will strictly validate inputs and raise errors on violations; frontend will display errors as-is (no silent fallbacks).
- We will keep `append_knowledgebase` but internally route to `kb_add` to preserve earlier usage until all prompts/tools are migrated.


