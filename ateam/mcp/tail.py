"""Tail event emitter with in-process ring buffer and monotonic offsets."""

import asyncio
import msgpack
import time
from collections import deque
from typing import Deque, Dict, Any, Optional
from .redis_transport import RedisTransport
from ..util.const import DEFAULTS
from ..util.logging import log
# Performance monitoring will be added in a future update
# from ..util.performance import measure_tail_latency

class TailEmitter:
    """Emit tail events with in-process ring buffer and monotonic offsets."""
    
    def __init__(self, redis_url: str, agent_id: str, ring_size: int = 2048) -> None:
        self._transport = RedisTransport(redis_url)
        self._agent_id = agent_id
        self._ring: Deque[Dict[str, Any]] = deque(maxlen=ring_size)
        self._offset = 0
        self._ch = f"mcp:tail:{agent_id}"
        self._connected = False

    async def connect(self) -> None:
        """Connect to Redis transport."""
        if not self._connected:
            result = await self._transport.connect()
            if result.ok:
                self._connected = True
            else:
                raise Exception(f"Failed to connect TailEmitter: {result.error.message}")

    async def disconnect(self) -> None:
        """Disconnect from Redis transport."""
        if self._connected:
            await self._transport.disconnect()
            self._connected = False

    def next_offset(self) -> int:
        """Get the next monotonic offset."""
        self._offset += 1
        return self._offset

    async def emit(self, event: Dict[str, Any]) -> None:
        """Emit a tail event with offset and timestamp."""
        if not self._connected:
            raise Exception("TailEmitter not connected")
        
        rec = {
            "offset": self.next_offset(), 
            "event": event, 
            "ts": time.time()
        }
        self._ring.append(rec)
        
        # Publish to Redis
        await self._transport.publish(self._ch, msgpack.packb(rec, use_bin_type=True))
        
        log("DEBUG", "tail", "emitted", 
            agent_id=self._agent_id, 
            offset=rec["offset"], 
            event_type=event.get("type"))

    def replay_from(self, off: int) -> list[Dict[str, Any]]:
        """Replay events from a given offset."""
        return [x for x in self._ring if x["offset"] > off]

    def get_current_offset(self) -> int:
        """Get the current offset."""
        return self._offset

    def get_ring_size(self) -> int:
        """Get the current ring buffer size."""
        return len(self._ring)

    def get_ring_capacity(self) -> int:
        """Get the ring buffer capacity."""
        return self._ring.maxlen if self._ring.maxlen else 0

    def get_recent_events(self, count: int = 50) -> list[Dict[str, Any]]:
        """Get recent tail events for context reconstruction."""
        if not self._ring:
            return []
        
        # Get the most recent events from the ring buffer
        recent_events = list(self._ring)[-count:]
        
        # Extract just the event data (not the full record with offset/timestamp)
        return [record["event"] for record in recent_events]
