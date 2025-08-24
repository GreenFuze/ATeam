"""KB adapter for agent KB operations with scoped storage."""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from .storage import KBStorage
from .embedding import EmbeddingProvider
from ..mcp.contracts import KBItem, KBHit, DocId, Scope
from ..util.logging import log


class KBAdapter:
    """Adapter for KB operations with scoped storage."""
    
    def __init__(self, agent_root: str, project_root: str, user_root: str) -> None:
        self.agent_root = Path(agent_root)
        self.project_root = Path(project_root)
        self.user_root = Path(user_root)
        
        # Initialize storage for each scope
        self.agent_storage = KBStorage(str(self.agent_root / "kb"))
        self.project_storage = KBStorage(str(self.project_root / "kb"))
        self.user_storage = KBStorage(str(self.user_root / "kb"))
        
        # Initialize embedding provider
        self.embedding_provider = EmbeddingProvider()
    
    def _get_storage_for_scope(self, scope: Scope) -> KBStorage:
        """Get storage instance for the given scope."""
        if scope == "agent":
            return self.agent_storage
        elif scope == "project":
            return self.project_storage
        elif scope == "user":
            return self.user_storage
        else:
            raise ValueError(f"Invalid scope: {scope}")
    
    def _get_collection_id(self, scope: Scope, agent_id: Optional[str] = None) -> str:
        """Get collection ID for the given scope."""
        if scope == "agent":
            if not agent_id:
                raise ValueError("agent_id required for agent scope")
            return f"agent_{agent_id}"
        elif scope == "project":
            return "project"
        elif scope == "user":
            return "user"
        else:
            raise ValueError(f"Invalid scope: {scope}")
    
    def ingest(self, items: List[KBItem], scope: Scope, agent_id: Optional[str] = None) -> List[DocId]:
        """Ingest items into the specified scope."""
        if not items:
            return []
        
        storage = self._get_storage_for_scope(scope)
        collection_id = self._get_collection_id(scope, agent_id)
        
        ingested_ids = []
        for item in items:
            try:
                # Read content from file or URL
                content = self._read_content(item.path_or_url)
                if not content:
                    log("WARN", "kb_adapter", "empty_content", path=item.path_or_url)
                    continue
                
                # Add to storage
                item_ids = storage.add(collection_id, content, item.metadata)
                ingested_ids.extend(item_ids)
                
            except Exception as e:
                log("ERROR", "kb_adapter", "ingest_failed", 
                    path=item.path_or_url, error=str(e))
        
        log("INFO", "kb_adapter", "ingest_completed", 
            scope=scope, count=len(ingested_ids))
        return ingested_ids
    
    def search(self, query: str, scope: Scope, agent_id: Optional[str] = None, k: int = 5) -> List[KBHit]:
        """Search for items in the specified scope."""
        if not query:
            return []
        
        storage = self._get_storage_for_scope(scope)
        collection_id = self._get_collection_id(scope, agent_id)
        
        try:
            results = storage.search(collection_id, query, k)
            
            # Convert to KBHit format
            hits = []
            for result in results:
                hit = KBHit(
                    id=result["id"],
                    score=result.get("score", 1.0),
                    metadata=result.get("metadata", {})
                )
                hits.append(hit)
            
            log("INFO", "kb_adapter", "search_completed", 
                scope=scope, query=query, results=len(hits))
            return hits
            
        except Exception as e:
            log("ERROR", "kb_adapter", "search_failed", 
                scope=scope, query=query, error=str(e))
            return []
    
    def copy_from(self, source_agent: str, target_agent: str, ids: List[DocId]) -> Dict[str, List[str]]:
        """Copy items from source agent to target agent."""
        if not ids:
            return {"copied": [], "skipped": []}
        
        source_collection = self._get_collection_id("agent", source_agent)
        target_collection = self._get_collection_id("agent", target_agent)
        
        try:
            result = self.agent_storage.copy_items(source_collection, target_collection, ids)
            
            log("INFO", "kb_adapter", "copy_completed", 
                source=source_agent, target=target_agent,
                copied=len(result["copied"]), skipped=len(result["skipped"]))
            return result
            
        except Exception as e:
            log("ERROR", "kb_adapter", "copy_failed", 
                source=source_agent, target=target_agent, error=str(e))
            return {"copied": [], "skipped": ids}
    
    def list(self, scope: Scope, agent_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List items in the specified scope."""
        storage = self._get_storage_for_scope(scope)
        collection_id = self._get_collection_id(scope, agent_id)
        
        try:
            items = storage.list(collection_id, limit, offset)
            log("INFO", "kb_adapter", "list_completed", 
                scope=scope, count=len(items))
            return items
            
        except Exception as e:
            log("ERROR", "kb_adapter", "list_failed", 
                scope=scope, error=str(e))
            return []
    
    def get(self, scope: Scope, item_id: str, agent_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get item by ID from the specified scope."""
        storage = self._get_storage_for_scope(scope)
        collection_id = self._get_collection_id(scope, agent_id)
        
        try:
            item = storage.get(collection_id, item_id)
            if item:
                log("INFO", "kb_adapter", "get_completed", 
                    scope=scope, item_id=item_id)
            return item
            
        except Exception as e:
            log("ERROR", "kb_adapter", "get_failed", 
                scope=scope, item_id=item_id, error=str(e))
            return None
    
    def delete(self, scope: Scope, item_id: str, agent_id: Optional[str] = None) -> bool:
        """Delete item by ID from the specified scope."""
        storage = self._get_storage_for_scope(scope)
        collection_id = self._get_collection_id(scope, agent_id)
        
        try:
            success = storage.delete(collection_id, item_id)
            if success:
                log("INFO", "kb_adapter", "delete_completed", 
                    scope=scope, item_id=item_id)
            return success
            
        except Exception as e:
            log("ERROR", "kb_adapter", "delete_failed", 
                scope=scope, item_id=item_id, error=str(e))
            return False
    
    def _read_content(self, path_or_url: str) -> Optional[str]:
        """Read content from file or URL."""
        try:
            # For now, only handle local files
            if path_or_url.startswith(('http://', 'https://')):
                log("WARN", "kb_adapter", "url_not_supported", url=path_or_url)
                return None
            
            file_path = Path(path_or_url)
            if not file_path.exists():
                log("WARN", "kb_adapter", "file_not_found", path=path_or_url)
                return None
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            log("DEBUG", "kb_adapter", "content_read", 
                path=path_or_url, size=len(content))
            return content
            
        except Exception as e:
            log("ERROR", "kb_adapter", "read_content_failed", 
                path=path_or_url, error=str(e))
            return None
