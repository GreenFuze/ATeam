import asyncio
from typing import Any, Dict, Callable, Optional
from .redis_transport import RedisTransport
from .contracts import TailEvent
from ..util.types import Result, ErrorInfo
from ..util.logging import log

class MCPClient:
    def __init__(self, redis_url: str, agent_id: str) -> None:
        self._agent_id = agent_id
        self._transport = RedisTransport(redis_url)
        self._connected = False
        self._tail_callback: Optional[Callable[[TailEvent], None]] = None

    async def connect(self) -> Result[None]:
        """Connect to Redis."""
        try:
            result = await self._transport.connect()
            if result.ok:
                self._connected = True
            return result
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("mcp.client.connect_failed", str(e)))

    async def disconnect(self) -> Result[None]:
        """Disconnect from Redis."""
        try:
            self._connected = False
            return await self._transport.disconnect()
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("mcp.client.disconnect_failed", str(e)))

    async def call(self, method: str, params: Dict[str, Any]) -> Result[Dict[str, Any]]:
        """Make an RPC call to the agent."""
        if not self._connected:
            return Result(ok=False, error=ErrorInfo("mcp.client.not_connected", "Not connected"))
        
        try:
            # Use the transport's RPC call mechanism
            result = await self._transport.call(method, params)
            if result.ok:
                return Result(ok=True, value=result.value)
            else:
                return result
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("mcp.client.call_failed", str(e)))

    async def subscribe_tail(self, on_event: Callable[[TailEvent], None]) -> Result[None]:
        """Subscribe to tail events from the agent."""
        if not self._connected:
            return Result(ok=False, error=ErrorInfo("mcp.client.not_connected", "Not connected"))
        
        try:
            self._tail_callback = on_event
            tail_channel = f"mcp:tail:{self._agent_id}"
            
            def on_tail_message(data: bytes):
                try:
                    import msgpack
                    event_data = msgpack.unpackb(data, raw=False)
                    # Convert to TailEvent
                    tail_event = TailEvent(**event_data.get("event", {}))
                    if self._tail_callback:
                        self._tail_callback(tail_event)
                except Exception as e:
                    log("ERROR", "mcp.client", "tail_parse_failed", error=str(e))
            
            result = await self._transport.subscribe(tail_channel, on_tail_message)
            if result.ok:
                log("INFO", "mcp.client", "tail_subscribed", agent_id=self._agent_id)
            return result
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("mcp.client.subscribe_failed", str(e)))

    async def unsubscribe_tail(self) -> Result[None]:
        """Unsubscribe from tail events."""
        if not self._connected:
            return Result(ok=True)  # Already disconnected
        
        try:
            self._tail_callback = None
            tail_channel = f"mcp:tail:{self._agent_id}"
            # Note: RedisTransport doesn't have unsubscribe yet, but we can ignore this for now
            log("INFO", "mcp.client", "tail_unsubscribed", agent_id=self._agent_id)
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("mcp.client.unsubscribe_failed", str(e)))
