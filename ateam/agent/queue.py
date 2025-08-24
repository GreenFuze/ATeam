import json
import time
import uuid
from typing import Optional, List
from ..mcp.contracts import QueueItem
from ..util.types import Result, ErrorInfo
from ..util.logging import log

class PromptQueue:
    def __init__(self, path: str) -> None:
        self.path = path
        self._items: List[QueueItem] = []
        self._load_existing()

    def _load_existing(self) -> None:
        """Load existing items from JSONL file."""
        try:
            import os
            if os.path.exists(self.path):
                with open(self.path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                item = QueueItem(
                                    id=data["id"],
                                    text=data["text"],
                                    source=data["source"],
                                    ts=data["ts"]
                                )
                                self._items.append(item)
                            except Exception as e:
                                log("WARN", "queue", "parse_line_failed", error=str(e), line=line)
        except Exception as e:
            log("ERROR", "queue", "load_failed", error=str(e))

    def append(self, text: str, source: str) -> Result[str]:
        """Append a new item to the queue."""
        try:
            item_id = str(uuid.uuid4())
            ts = time.time()
            
            item = QueueItem(
                id=item_id,
                text=text,
                source=source,
                ts=ts
            )
            
            self._items.append(item)
            
            # Persist to file
            self._persist_item(item)
            
            log("DEBUG", "queue", "item_appended", id=item_id, source=source)
            return Result(ok=True, value=item_id)
            
        except Exception as e:
            log("ERROR", "queue", "append_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("queue.append_failed", str(e)))

    def _persist_item(self, item: QueueItem) -> None:
        """Persist a single item to the JSONL file."""
        try:
            import os
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            
            with open(self.path, 'a', encoding='utf-8') as f:
                data = {
                    "id": item.id,
                    "text": item.text,
                    "source": item.source,
                    "ts": item.ts
                }
                f.write(json.dumps(data) + '\n')
                f.flush()  # Ensure immediate write
                
        except Exception as e:
            log("ERROR", "queue", "persist_failed", error=str(e))

    def peek(self) -> Optional[QueueItem]:
        """Peek at the next item without removing it."""
        if self._items:
            return self._items[0]
        return None

    def pop(self) -> Optional[QueueItem]:
        """Remove and return the next item."""
        if self._items:
            item = self._items.pop(0)
            log("DEBUG", "queue", "item_popped", id=item.id)
            return item
        return None

    def list(self) -> List[QueueItem]:
        """List all items in the queue."""
        return self._items.copy()

    def clear(self) -> Result[None]:
        """Clear all items from the queue."""
        try:
            self._items.clear()
            
            # Clear the file
            import os
            if os.path.exists(self.path):
                os.remove(self.path)
            
            log("INFO", "queue", "cleared")
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "queue", "clear_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("queue.clear_failed", str(e)))

    def size(self) -> int:
        """Get the number of items in the queue."""
        return len(self._items)
