"""Agent KB adapter for MCP integration."""

from typing import List, Dict, Any, Optional
from pathlib import Path

from ..kb.adapter import KBAdapter
from ..kb.storage import KBStorage
from ..mcp.contracts import KBItem, KBHit, DocId, Scope
from ..util.logging import log


class AgentKBAdapter:
    """Agent-specific KB adapter for MCP integration."""
    
    def __init__(self, agent_id: str, agent_root: str, project_root: str, user_root: str) -> None:
        self.agent_id = agent_id
        self.kb_adapter = KBAdapter(agent_root, project_root, user_root)
    
    def ingest(self, paths: List[str], scope: Scope, metadata: Optional[Dict[str, Any]] = None) -> List[DocId]:
        """Ingest files into KB."""
        if not paths:
            return []
        
        # Convert paths to KBItems
        items = []
        for path in paths:
            item = KBItem(
                path_or_url=path,
                metadata=metadata or {}
            )
            items.append(item)
        
        # Use agent_id for agent scope
        agent_id = self.agent_id if scope == "agent" else None
        
        try:
            ingested_ids = self.kb_adapter.ingest(items, scope, agent_id)
            log("INFO", "agent_kb", "ingest_completed", 
                agent_id=self.agent_id, scope=scope, count=len(ingested_ids))
            return ingested_ids
            
        except Exception as e:
            log("ERROR", "agent_kb", "ingest_failed", 
                agent_id=self.agent_id, scope=scope, error=str(e))
            return []
    
    def search(self, query: str, scope: Scope, k: int = 5) -> List[KBHit]:
        """Search KB in specified scope."""
        if not query:
            return []
        
        # Use agent_id for agent scope
        agent_id = self.agent_id if scope == "agent" else None
        
        try:
            hits = self.kb_adapter.search(query, scope, agent_id, k)
            log("INFO", "agent_kb", "search_completed", 
                agent_id=self.agent_id, scope=scope, query=query, results=len(hits))
            return hits
            
        except Exception as e:
            log("ERROR", "agent_kb", "search_failed", 
                agent_id=self.agent_id, scope=scope, query=query, error=str(e))
            return []
    
    def copy_from(self, source_agent: str, ids: List[DocId]) -> Dict[str, List[str]]:
        """Copy items from another agent via RPC calls."""
        if not ids:
            return {"copied": [], "skipped": []}
        
        # This method is deprecated - copy operations should be done via RPC calls
        # from the agent's main handler, not directly from the KB adapter
        log("WARN", "agent_kb", "copy_from_deprecated", 
            agent_id=self.agent_id, source=source_agent)
        return {"copied": [], "skipped": ids}
    
    def list(self, scope: Scope, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List items in specified scope."""
        # Use agent_id for agent scope
        agent_id = self.agent_id if scope == "agent" else None
        
        try:
            items = self.kb_adapter.list(scope, agent_id, limit, offset)
            log("INFO", "agent_kb", "list_completed", 
                agent_id=self.agent_id, scope=scope, count=len(items))
            return items
            
        except Exception as e:
            log("ERROR", "agent_kb", "list_failed", 
                agent_id=self.agent_id, scope=scope, error=str(e))
            return []
    
    def get(self, scope: Scope, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item by ID from specified scope."""
        # Use agent_id for agent scope
        agent_id = self.agent_id if scope == "agent" else None
        
        try:
            item = self.kb_adapter.get(scope, item_id, agent_id)
            if item:
                log("INFO", "agent_kb", "get_completed", 
                    agent_id=self.agent_id, scope=scope, item_id=item_id)
            return item
            
        except Exception as e:
            log("ERROR", "agent_kb", "get_failed", 
                agent_id=self.agent_id, scope=scope, item_id=item_id, error=str(e))
            return None
    
    def delete(self, scope: Scope, item_id: str) -> bool:
        """Delete item by ID from specified scope."""
        # Use agent_id for agent scope
        agent_id = self.agent_id if scope == "agent" else None
        
        try:
            success = self.kb_adapter.delete(scope, item_id, agent_id)
            if success:
                log("INFO", "agent_kb", "delete_completed", 
                    agent_id=self.agent_id, scope=scope, item_id=item_id)
            return success
            
        except Exception as e:
            log("ERROR", "agent_kb", "delete_failed", 
                agent_id=self.agent_id, scope=scope, item_id=item_id, error=str(e))
            return False
