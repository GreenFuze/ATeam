import os
import re
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from objects_registry import embedding_manager

logger = logging.getLogger(__name__)


class KBManager:
    """
    Abstraction over Chroma DB for agent-specific knowledgebases, plus plan files.
    Only this class knows about Chroma internals. Enforces agent isolation.
    """

    def __init__(self, base_dir: str = "knowledgebase"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._locks: Dict[str, threading.RLock] = {}
        self._collections: Dict[str, Any] = {}
        self._collections_lock = threading.RLock()

    # ---------- internals ----------
    def _get_lock(self, agent_id: str) -> threading.RLock:
        with self._collections_lock:
            if agent_id not in self._locks:
                self._locks[agent_id] = threading.RLock()
            return self._locks[agent_id]

    def _ensure_collection(self, agent_id: str):
        from chromadb import PersistentClient  # type: ignore[import-not-found]
        with self._collections_lock:
            if agent_id in self._collections:
                return
            agent_kb_dir = self.base_dir / agent_id / "kb"
            agent_kb_dir.mkdir(parents=True, exist_ok=True)
            client = PersistentClient(path=str(agent_kb_dir))
            # Use a descriptive collection name that meets ChromaDB validation requirements
            collection_name = f"knowledgebase_{agent_id}"
            self._collections[agent_id] = client.get_or_create_collection(name=collection_name)

    def _assert_caller(self, agent_id: str, caller_agent_id: Optional[str]):
        if caller_agent_id is None:
            # We expect Agent._handle_tool_call to inject caller_agent_id; fail-fast otherwise
            raise RuntimeError("caller_agent_id missing in tool call")
        if agent_id != caller_agent_id:
            raise PermissionError("Agent is not allowed to access another agent's knowledgebase")

    # ---------- KB API ----------
    def add(self, *, agent_id: str, content: str, metadata: Optional[Dict[str, Any]] = None, caller_agent_id: Optional[str] = None) -> List[str]:

        self._assert_caller(agent_id, caller_agent_id)
        if not content or not isinstance(content, str):
            raise ValueError("content must be a non-empty string")

        self._ensure_collection(agent_id)
        lock = self._get_lock(agent_id)
        created_ids: List[str] = []
 
        with lock:
            max_chunk = embedding_manager().get_max_chunk_size()
            chunks: List[str] = []
            if len(content) <= max_chunk:
                chunks = [content]
            else:
                for i in range(0, len(content), max_chunk):
                    chunks.append(content[i:i+max_chunk])

            now = datetime.now().isoformat()
            metabase = dict(metadata or {})
            
            # Compute embeddings for all chunks at once (batch for performance)
            try:
                embeddings = embedding_manager().embed(chunks)
            except Exception as e:
                logger.error(f"KB add embed failed for agent={agent_id}: {e}")
                raise
            
            for idx, chunk in enumerate(chunks):
                item_id = f"knowledgebase_item_{int(datetime.now().timestamp()*1000)}_{idx}"
                item_meta = {
                    **metabase,
                    "id": item_id,
                    "title": metabase.get("title") or chunk.strip().splitlines()[0][:80],
                    "created_at": now,
                    "updated_at": now,
                }
                self._collections[agent_id].add(
                    documents=[chunk],
                    metadatas=[item_meta],
                    ids=[item_id],
                    embeddings=[embeddings[idx]] if embeddings else None,
                )
                created_ids.append(item_id)
                
            logger.info(f"KB add: agent={agent_id} items={len(created_ids)}")
        return created_ids


    def update(self, *, agent_id: str, item_id: str, content: str, metadata: Optional[Dict[str, Any]] = None, caller_agent_id: Optional[str] = None) -> None:
        
        self._assert_caller(agent_id, caller_agent_id)
        
        if not item_id:
            raise ValueError("item_id is required")
        
        self._ensure_collection(agent_id)
       
        with self._get_lock(agent_id):
            now = datetime.now().isoformat()
            metas = metadata or {}
            metas.update({"updated_at": now})
            
            # Recompute embedding for updated content
            try:
                embedding = embedding_manager().embed([content])[0]
            except Exception as e:
                logger.error(f"KB update embed failed for agent={agent_id} item={item_id}: {e}")
                raise
            
            self._collections[agent_id].update(
                ids=[item_id],
                documents=[content],
                metadatas=[metas],
                embeddings=[embedding],
            )
            
            logger.info(f"KB update: agent={agent_id} item={item_id}")

    def get(self, *, agent_id: str, item_id: str, caller_agent_id: Optional[str] = None) -> Dict[str, Any]:
        self._assert_caller(agent_id, caller_agent_id)
        if not item_id:
            raise ValueError("item_id is required")
        self._ensure_collection(agent_id)
        with self._get_lock(agent_id):
            res = self._collections[agent_id].get(ids=[item_id])
            if not res or not res.get("ids"):
                raise ValueError("item not found")
            logger.info(f"KB get: agent={agent_id} item={item_id}")
            return {
                "id": res["ids"][0],
                "content": res["documents"][0],
                "metadata": res["metadatas"][0],
            }

    def list(self, *, agent_id: str, limit: int = 50, offset: int = 0, caller_agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        self._assert_caller(agent_id, caller_agent_id)
        if limit < 0 or offset < 0:
            raise ValueError("limit/offset must be non-negative")
        self._ensure_collection(agent_id)
        with self._get_lock(agent_id):
            res = self._collections[agent_id].get()
            items = []
            count = len(res.get("ids", [])) if res else 0
            for i in range(count):
                items.append({
                    "id": res["ids"][i],
                    "content": res["documents"][i],
                    "metadata": res["metadatas"][i],
                })
            out = items[offset:offset+limit]
            logger.info(f"KB list: agent={agent_id} count={len(out)}")
            return out

    def search(self, *, agent_id: str, query: str, k: int = 5, caller_agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        self._assert_caller(agent_id, caller_agent_id)
        if not query:
            raise ValueError("query must be non-empty")
        self._ensure_collection(agent_id)
        with self._get_lock(agent_id):
            embeds = embedding_manager().embed([query])[0]
            res = self._collections[agent_id].query(query_embeddings=[embeds], n_results=k)
            out: List[Dict[str, Any]] = []
            ids = res.get("ids", [[]])[0]
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]
            for i in range(len(ids)):
                out.append({
                    "id": ids[i],
                    "content": docs[i],
                    "metadata": metas[i],
                    "distance": dists[i] if i < len(dists) else None,
                })
            logger.info(f"KB search: agent={agent_id} q_len={len(query)} results={len(out)}")
            return out

    def delete(self, *, agent_id: str, item_id: str, caller_agent_id: Optional[str] = None) -> None:
        """Delete a KB item by id."""
        self._assert_caller(agent_id, caller_agent_id)
        if not item_id:
            raise ValueError("item_id is required")
        self._ensure_collection(agent_id)
        with self._get_lock(agent_id):
            # Check if item exists before deleting
            try:
                res = self._collections[agent_id].get(ids=[item_id])
                if not res or not res.get("ids"):
                    raise ValueError("item not found")
            except Exception as e:
                logger.error(f"KB delete check failed for agent={agent_id} item={item_id}: {e}")
                raise
            
            # Delete the item from ChromaDB
            self._collections[agent_id].delete(ids=[item_id])
            logger.info(f"KB delete: agent={agent_id} item={item_id}")

    # ---------- Plan API ----------
    _PLAN_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

    def _plan_path(self, agent_id: str, name: str) -> Path:
        if not self._PLAN_NAME_RE.match(name):
            raise ValueError("Invalid plan name; allowed: [a-zA-Z0-9_-]+")
        agent_dir = self.base_dir / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        return agent_dir / f"{name}.md"

    def plan_read(self, *, agent_id: str, name: str, caller_agent_id: Optional[str] = None) -> str:
        self._assert_caller(agent_id, caller_agent_id)
        path = self._plan_path(agent_id, name)
        with self._get_lock(agent_id):
            if not path.exists():
                raise FileNotFoundError("plan not found")
            logger.info(f"Plan read: agent={agent_id} name={name}")
            return path.read_text(encoding="utf-8")

    def plan_write(self, *, agent_id: str, name: str, content: str, caller_agent_id: Optional[str] = None) -> None:
        self._assert_caller(agent_id, caller_agent_id)
        if len(content) > 4000:
            raise ValueError("plan is too big, please summarize")
        path = self._plan_path(agent_id, name)
        tmp = path.with_suffix(".tmp")
        with self._get_lock(agent_id):
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, path)
            logger.info(f"Plan write: agent={agent_id} name={name} bytes={len(content)}")

    def plan_append(self, *, agent_id: str, name: str, content: str, caller_agent_id: Optional[str] = None) -> None:
        self._assert_caller(agent_id, caller_agent_id)
        path = self._plan_path(agent_id, name)
        with self._get_lock(agent_id):
            existing = path.read_text(encoding="utf-8") if path.exists() else ""
            new = existing + ("\n" if existing else "") + content
            if len(new) > 4000:
                raise ValueError("plan is too big after append, please summarize")
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(new)
            os.replace(tmp, path)
            logger.info(f"Plan append: agent={agent_id} name={name} add_bytes={len(content)}")

    def plan_delete(self, *, agent_id: str, name: str, caller_agent_id: Optional[str] = None) -> None:
        self._assert_caller(agent_id, caller_agent_id)
        path = self._plan_path(agent_id, name)
        with self._get_lock(agent_id):
            if path.exists():
                path.unlink()
                logger.info(f"Plan delete: agent={agent_id} name={name}")

    def plan_list(self, *, agent_id: str, caller_agent_id: Optional[str] = None) -> List[str]:
        self._assert_caller(agent_id, caller_agent_id)
        with self._get_lock(agent_id):
            agent_dir = self.base_dir / agent_id
            if not agent_dir.exists():
                return []
            names = [p.stem for p in agent_dir.glob("*.md")]
            logger.info(f"Plan list: agent={agent_id} count={len(names)}")
            return names


