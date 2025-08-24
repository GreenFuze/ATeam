import asyncio
import contextlib
import time
import msgpack
from typing import Callable, Dict, Any, Optional
from .redis_transport import RedisTransport
from ..util.types import Result, ErrorInfo
from ..util.logging import log

class MCPServer:
    def __init__(self, redis_url: str, agent_id: str) -> None:
        self._agent_id = agent_id
        self._transport = RedisTransport(redis_url)
        self._tools: Dict[str, Callable[..., Any]] = {}
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._serve_task: Optional[asyncio.Task] = None
        self._running = False

    def register_tool(self, name: str, fn: Callable[..., Any]) -> None:
        """Register a tool function."""
        self._tools[name] = fn

    def register_handler(self, method: str, fn: Callable[[Dict[str, Any]], Any]) -> None:
        """Register an RPC method handler."""
        self._handlers[method] = fn

    async def start(self) -> Result[None]:
        """Start the MCP server."""
        if self._running:
            return Result(ok=True)
        
        try:
            # Connect to Redis
            connect_result = await self._transport.connect()
            if not connect_result.ok:
                return connect_result
            
            self._running = True
            self._serve_task = asyncio.create_task(self._serve())
            log("INFO", "mcp.server", "started", agent_id=self._agent_id)
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("mcp.server.start_failed", str(e)))

    async def stop(self) -> Result[None]:
        """Stop the MCP server."""
        try:
            self._running = False
            if self._serve_task:
                self._serve_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._serve_task
            await self._transport.disconnect()
            log("INFO", "mcp.server", "stopped", agent_id=self._agent_id)
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("mcp.server.stop_failed", str(e)))

    async def _serve(self) -> None:
        """Main server loop - listen for RPC requests."""
        req_ch = f"mcp:req:{self._agent_id}"
        log("INFO", "mcp.server", "listening", channel=req_ch, agent_id=self._agent_id)
        
        async def on_msg(raw: bytes) -> None:
            try:
                req = msgpack.unpackb(raw, raw=False)
                res_ch = f"mcp:res:{self._agent_id}:{req.get('req_id', '')}"
                out = await self._dispatch(req)
                await self._transport.publish(res_ch, msgpack.packb(out, use_bin_type=True))
            except Exception as e:
                log("ERROR", "mcp.server", "dispatch_failed", err=str(e), agent_id=self._agent_id)
        
        # Subscribe to request channel
        subscribe_result = await self._transport.subscribe(req_ch, on_msg)
        if not subscribe_result.ok:
            log("ERROR", "mcp.server", "subscribe_failed", error=subscribe_result.error.message)
            return
        
        # Keep running until stopped
        while self._running:
            await asyncio.sleep(1)

    async def _dispatch(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch an RPC request to the appropriate handler."""
        req_id = req.get("req_id", "")
        method = req.get("method", "")
        params = req.get("params", {})
        ts = time.time()
        
        h = self._handlers.get(method)
        if not h:
            return {
                "req_id": req_id, 
                "ok": False, 
                "error": {"code": "no_such_method", "message": f"Method '{method}' not found"}, 
                "ts": ts
            }
        
        try:
            # Handlers can be sync or async
            if asyncio.iscoroutinefunction(h):
                value = await h(params)
            else:
                value = h(params)
            return {"req_id": req_id, "ok": True, "value": value, "ts": ts}
        except Exception as e:
            log("ERROR", "mcp.server", "handler_error", method=method, error=str(e))
            return {
                "req_id": req_id, 
                "ok": False, 
                "error": {"code": "handler.error", "message": str(e)}, 
                "ts": ts
            }
