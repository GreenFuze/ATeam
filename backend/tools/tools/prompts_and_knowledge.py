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


def append_knowledgebase(content: str, caller_agent_id: Optional[str] = None) -> str:
    """Append text to the per-agent knowledgebase file.

    The content is appended to the calling agent's knowledgebase.
    """
    if not content or not isinstance(content, str):
        raise ValueError("content must be a non-empty string")
    if not caller_agent_id:
        raise ValueError("caller_agent_id is required")

    # Validate agent exists (fail-fast)
    cfg = agent_manager().get_agent_config(caller_agent_id)
    if cfg is None:
        raise ValueError(f"Agent '{caller_agent_id}' not found")

    # Route to kb_manager add for canonical behavior
    ids = kb_manager().add(agent_id=caller_agent_id, content=content, metadata={"title": content.strip().splitlines()[0][:80] if content else "KB entry"}, caller_agent_id=caller_agent_id)
    return f"Knowledgebase updated for agent '{caller_agent_id}'. Created items: {ids}."


def kb_add(title: str, content: str, metadata: Optional[dict] = None, caller_agent_id: Optional[str] = None) -> str:
    """Add content to the agent's knowledgebase.

    Behavior:
    - Content longer than the configured max_chunk_size is automatically chunked; multiple KB items will be created.
    - Use `metadata` to set a human-readable title; otherwise, the first line of content is used.
    - Prefer adding only durable, reusable facts to the KB.
    - ignore "caller_agent_id" parameter
    """
    if not caller_agent_id:
        raise ValueError("caller_agent_id is required")
    
    if metadata is None:
        metadata = {'title': title}
    else:
        metadata['title'] = title
    
    ids = kb_manager().add(agent_id=caller_agent_id, content=content, metadata=metadata or {}, caller_agent_id=caller_agent_id)
    return str({"created_ids": ids})


def kb_update(item_id: str, content: str, metadata: Optional[dict] = None, caller_agent_id: Optional[str] = None) -> str:
    """Update a KB item by id.

    Behavior:
    - Recomputes the embedding for the updated content.
    - Updates `updated_at` metadata automatically.
    """
    if not caller_agent_id:
        raise ValueError("caller_agent_id is required")
    kb_manager().update(agent_id=caller_agent_id, item_id=item_id, content=content, metadata=metadata or {}, caller_agent_id=caller_agent_id)
    return "OK"


def kb_get(item_id: str, caller_agent_id: Optional[str] = None) -> str:
    """Get a KB item by id."""
    if not caller_agent_id:
        raise ValueError("caller_agent_id is required")
    item = kb_manager().get(agent_id=caller_agent_id, item_id=item_id, caller_agent_id=caller_agent_id)
    return str(item)


def kb_list(limit: int = 50, offset: int = 0, caller_agent_id: Optional[str] = None) -> str:
    """List KB items."""
    if not caller_agent_id:
        raise ValueError("caller_agent_id is required")
    items = kb_manager().list(agent_id=caller_agent_id, limit=limit, offset=offset, caller_agent_id=caller_agent_id)
    return str(items)


def kb_search(query: str, k: int = 5, caller_agent_id: Optional[str] = None) -> str:
    """Semantic search over KB.

    Behavior:
    - Computes the embedding for the query and returns top-k similar items with distances.
    - Use this to retrieve relevant KB facts for current tasks.
    """
    if not caller_agent_id:
        raise ValueError("caller_agent_id is required")
    items = kb_manager().search(agent_id=caller_agent_id, query=query, k=k, caller_agent_id=caller_agent_id)
    return str(items)


def kb_delete(item_id: str, caller_agent_id: Optional[str] = None) -> str:
    """Delete a KB item by id.

    Behavior:
    - Permanently removes the item from the knowledgebase.
    - Fails if the item doesn't exist.
    - Use this to clean up outdated or incorrect information.
    """
    if not caller_agent_id:
        raise ValueError("caller_agent_id is required")
    kb_manager().delete(agent_id=caller_agent_id, item_id=item_id, caller_agent_id=caller_agent_id)
    return "OK"


def plan_read(name: str, caller_agent_id: Optional[str] = None) -> str:
    """Read a plan file content."""
    if not caller_agent_id:
        raise ValueError("caller_agent_id is required")
    return kb_manager().plan_read(agent_id=caller_agent_id, name=name, caller_agent_id=caller_agent_id)


def plan_write(name: str, content: str, caller_agent_id: Optional[str] = None) -> str:
    """Write (overwrite) a plan file content.

    Policy:
    - Plans are short-term memory capped at 4k characters. If you exceed, summarize and try again.
    - Allowed plan names: [a-zA-Z0-9_-]+ to avoid path issues.
    """
    if not caller_agent_id:
        raise ValueError("caller_agent_id is required")
    kb_manager().plan_write(agent_id=caller_agent_id, name=name, content=content, caller_agent_id=caller_agent_id)
    return "OK"


def plan_append(name: str, content: str, caller_agent_id: Optional[str] = None) -> str:
    """Append to a plan file content.

    Policy:
    - Appending that results in content > 4k characters will fail. Summarize first.
    - Use concise bullet points and checklists; avoid verbosity.
    """
    if not caller_agent_id:
        raise ValueError("caller_agent_id is required")
    kb_manager().plan_append(agent_id=caller_agent_id, name=name, content=content, caller_agent_id=caller_agent_id)
    return "OK"


def plan_delete(name: str, caller_agent_id: Optional[str] = None) -> str:
    """Delete a plan file."""
    if not caller_agent_id:
        raise ValueError("caller_agent_id is required")
    kb_manager().plan_delete(agent_id=caller_agent_id, name=name, caller_agent_id=caller_agent_id)
    return "OK"


def plan_list(caller_agent_id: Optional[str] = None) -> str:
    """List plan file names for an agent."""
    if not caller_agent_id:
        raise ValueError("caller_agent_id is required")
    return str(kb_manager().plan_list(agent_id=caller_agent_id, caller_agent_id=caller_agent_id))

