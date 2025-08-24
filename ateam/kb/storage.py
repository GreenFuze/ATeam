"""Simple in-memory KB storage for testing."""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..util.logging import log


class KBStorage:
    """Simple in-memory KB storage with JSON persistence."""
    
    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._collections: Dict[str, Dict[str, Any]] = {}
        self._id_counter = 0
        self._load_collections()
    
    def _get_collection_path(self, collection_id: str) -> Path:
        """Get path for collection storage."""
        return self.base_dir / f"{collection_id}.json"
    
    def _load_collections(self) -> None:
        """Load existing collections from disk."""
        for json_file in self.base_dir.glob("*.json"):
            collection_id = json_file.stem
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    self._collections[collection_id] = json.load(f)
                log("DEBUG", "kb_storage", "loaded_collection", collection_id=collection_id)
            except Exception as e:
                log("ERROR", "kb_storage", "load_failed", collection_id=collection_id, error=str(e))
    
    def _save_collection(self, collection_id: str) -> None:
        """Save collection to disk."""
        collection_path = self._get_collection_path(collection_id)
        try:
            with open(collection_path, 'w', encoding='utf-8') as f:
                json.dump(self._collections[collection_id], f, indent=2)
            log("DEBUG", "kb_storage", "saved_collection", collection_id=collection_id)
        except Exception as e:
            log("ERROR", "kb_storage", "save_failed", collection_id=collection_id, error=str(e))
            raise
    
    def _ensure_collection(self, collection_id: str) -> None:
        """Ensure collection exists."""
        if collection_id not in self._collections:
            self._collections[collection_id] = {"items": {}, "metadata": {}}
    
    def _compute_content_hash(self, content: str) -> str:
        """Compute hash for content deduplication."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def add(self, collection_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """Add content to collection with deduplication."""
        if not content or not isinstance(content, str):
            raise ValueError("content must be a non-empty string")
        
        self._ensure_collection(collection_id)
        content_hash = self._compute_content_hash(content)
        
        # Check for duplicates
        for item_id, item in self._collections[collection_id]["items"].items():
            if item.get("content_hash") == content_hash:
                log("DEBUG", "kb_storage", "duplicate_found", collection_id=collection_id, item_id=item_id)
                return [item_id]
        
        # Add new item
        self._id_counter += 1
        item_id = f"kb_item_{int(datetime.now().timestamp() * 1000)}_{self._id_counter}"
        now = datetime.now().isoformat()
        
        item_data = {
            "id": item_id,
            "content": content,
            "content_hash": content_hash,
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now,
        }
        
        self._collections[collection_id]["items"][item_id] = item_data
        self._save_collection(collection_id)
        
        log("INFO", "kb_storage", "item_added", collection_id=collection_id, item_id=item_id)
        return [item_id]
    
    def get(self, collection_id: str, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item by ID."""
        self._ensure_collection(collection_id)
        return self._collections[collection_id]["items"].get(item_id)
    
    def list(self, collection_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List items in collection."""
        self._ensure_collection(collection_id)
        items = list(self._collections[collection_id]["items"].values())
        return items[offset:offset + limit]
    
    def search(self, collection_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Simple text search (exact match for now)."""
        if not query:
            raise ValueError("query must be non-empty")
        
        self._ensure_collection(collection_id)
        results = []
        
        for item in self._collections[collection_id]["items"].values():
            content = item.get("content", "").lower()
            if query.lower() in content:
                results.append({
                    **item,
                    "score": 1.0,  # Simple scoring
                    "distance": 0.0
                })
        
        # Sort by creation time (newest first) and limit
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results[:k]
    
    def delete(self, collection_id: str, item_id: str) -> bool:
        """Delete item by ID."""
        self._ensure_collection(collection_id)
        if item_id in self._collections[collection_id]["items"]:
            del self._collections[collection_id]["items"][item_id]
            self._save_collection(collection_id)
            log("INFO", "kb_storage", "item_deleted", collection_id=collection_id, item_id=item_id)
            return True
        return False
    
    def copy_items(self, source_collection: str, target_collection: str, item_ids: List[str]) -> Dict[str, List[str]]:
        """Copy items from source to target collection."""
        copied = []
        skipped = []
        
        self._ensure_collection(source_collection)
        self._ensure_collection(target_collection)
        
        for item_id in item_ids:
            item = self._collections[source_collection]["items"].get(item_id)
            if not item:
                skipped.append(item_id)
                continue
            
            # Check for duplicates in target
            content_hash = item.get("content_hash")
            duplicate_found = False
            for target_item in self._collections[target_collection]["items"].values():
                if target_item.get("content_hash") == content_hash:
                    skipped.append(item_id)
                    duplicate_found = True
                    break
            
            if not duplicate_found:
                # Copy item with new ID
                import time
                self._id_counter += 1
                new_item_id = f"kb_item_{int(time.time() * 1000000)}_{self._id_counter}"  # Use microseconds for better uniqueness
                new_item = {
                    **item,
                    "id": new_item_id,
                    "copied_from": item_id,
                    "copied_at": datetime.now().isoformat()
                }
                self._collections[target_collection]["items"][new_item_id] = new_item
                copied.append(new_item_id)
        
        if copied:
            self._save_collection(target_collection)
        
        log("INFO", "kb_storage", "items_copied", 
            source=source_collection, target=target_collection, 
            copied=len(copied), skipped=len(skipped))
        
        return {"copied": copied, "skipped": skipped}
