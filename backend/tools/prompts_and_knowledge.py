"""
Prompt and knowledge tools.

Tools in this module allow agents to fetch prompt contents by exact filename.
"""

from typing import Optional
from pathlib import Path
from datetime import datetime
from objects_registry import prompt_manager, agent_manager, kb_manager


def get_prompt(name: str) -> str:
    """
    Get the full content of a prompt by exact file name (including .md).

    Parameters
    ----------
    name : str
        Exact prompt file name including the .md extension (e.g., "zeus_system.md").

    Returns
    -------
    str
        The prompt content as plain text.

    Raises
    ------
    ValueError
        If the name is empty or does not end with ".md".
    FileNotFoundError
        If a prompt with the given name does not exist.
    """
    if not name or not isinstance(name, str):
        raise ValueError("Prompt name must be a non-empty string")
    if not name.endswith(".md"):
        raise ValueError("Prompt name must include the '.md' extension (e.g., 'zeus_system.md')")

    content: Optional[str] = prompt_manager().get_prompt_content(name)
    if content is None:
        # get_prompt raises for missing prompts; this is a guard for unexpected None
        raise FileNotFoundError(f"Prompt '{name}' not found")
    return content


def append_knowledgebase(agent_id: str, content: str) -> str:
    """Append text to the per-agent knowledgebase file.

    The caller MUST pass its own agent_id explicitly. The content is appended
    to `backend/knowledgebase/<agent_id>.md`. If the agent_id does not exist,
    this function fails immediately.
    """
    if not agent_id or not isinstance(agent_id, str):
        raise ValueError("agent_id must be a non-empty string")
    if not content or not isinstance(content, str):
        raise ValueError("content must be a non-empty string")

    # Validate agent exists (fail-fast)
    cfg = agent_manager().get_agent_config(agent_id)
    if cfg is None:
        raise ValueError(f"Agent '{agent_id}' not found")

    # Route to kb_manager add for canonical behavior
    ids = kb_manager().add(agent_id=agent_id, content=content, metadata={"title": content.strip().splitlines()[0][:80] if content else "KB entry"})
    return f"Knowledgebase updated for agent '{agent_id}'. Created items: {ids}."


def kb_add(agent_id: str, content: str, metadata: Optional[dict] = None) -> str:
    """Add content to the agent's knowledgebase.

    Behavior:
    - Content longer than the configured max_chunk_size is automatically chunked; multiple KB items will be created.
    - Use `metadata.title` to set a human-readable title; otherwise, the first line of content is used.
    - Prefer adding only durable, reusable facts to the KB.
    """
    ids = kb_manager().add(agent_id=agent_id, content=content, metadata=metadata or {})
    return str({"created_ids": ids})


def kb_update(agent_id: str, item_id: str, content: str, metadata: Optional[dict] = None) -> str:
    """Update a KB item by id.

    Behavior:
    - Recomputes the embedding for the updated content.
    - Updates `updated_at` metadata automatically.
    """
    kb_manager().update(agent_id=agent_id, item_id=item_id, content=content, metadata=metadata or {})
    return "OK"


def kb_get(agent_id: str, item_id: str) -> str:
    """Get a KB item by id."""
    item = kb_manager().get(agent_id=agent_id, item_id=item_id)
    return str(item)


def kb_list(agent_id: str, limit: int = 50, offset: int = 0) -> str:
    """List KB items."""
    items = kb_manager().list(agent_id=agent_id, limit=limit, offset=offset)
    return str(items)


def kb_search(agent_id: str, query: str, k: int = 5) -> str:
    """Semantic search over KB.

    Behavior:
    - Computes the embedding for the query and returns top-k similar items with distances.
    - Use this to retrieve relevant KB facts for current tasks.
    """
    items = kb_manager().search(agent_id=agent_id, query=query, k=k)
    return str(items)


def plan_read(agent_id: str, name: str) -> str:
    """Read a plan file content."""
    return kb_manager().plan_read(agent_id=agent_id, name=name)


def plan_write(agent_id: str, name: str, content: str) -> str:
    """Write (overwrite) a plan file content.

    Policy:
    - Plans are short-term memory capped at 4k characters. If you exceed, summarize and try again.
    - Allowed plan names: [a-zA-Z0-9_-]+ to avoid path issues.
    """
    kb_manager().plan_write(agent_id=agent_id, name=name, content=content)
    return "OK"


def plan_append(agent_id: str, name: str, content: str) -> str:
    """Append to a plan file content.

    Policy:
    - Appending that results in content > 4k characters will fail. Summarize first.
    - Use concise bullet points and checklists; avoid verbosity.
    """
    kb_manager().plan_append(agent_id=agent_id, name=name, content=content)
    return "OK"


def plan_delete(agent_id: str, name: str) -> str:
    """Delete a plan file."""
    kb_manager().plan_delete(agent_id=agent_id, name=name)
    return "OK"


def plan_list(agent_id: str) -> str:
    """List plan file names for an agent."""
    return str(kb_manager().plan_list(agent_id=agent_id))

