import asyncio
import json
import time
from typing import List, Callable, Optional
from .contracts import AgentInfo
from .redis_transport import RedisTransport
from ..util.types import Result, ErrorInfo
from ..util.logging import log

class RegistryEvent:
    def __init__(self, kind: str, agent: AgentInfo) -> None:
        self.kind = kind  # "added", "updated", "removed"
        self.agent = agent

class MCPRegistryClient:
    def __init__(self, redis_url: str) -> None:
        self._transport = RedisTransport(redis_url)
        self._connected = False
        self._agents: dict[str, AgentInfo] = {}
        self._watch_callback: Optional[Callable[[RegistryEvent], None]] = None
        self._watch_task: Optional[asyncio.Task] = None

    async def connect(self) -> Result[None]:
        """Connect to Redis and start watching for agents."""
        try:
            result = await self._transport.connect()
            if result.ok:
                self._connected = True
                # Start watching for registry changes
                self._watch_task = asyncio.create_task(self._watch_registry())
            return result
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("registry.connect_failed", str(e)))

    async def disconnect(self) -> Result[None]:
        """Disconnect from Redis."""
        try:
            self._connected = False
            if self._watch_task:
                self._watch_task.cancel()
                with asyncio.CancelledError:
                    await self._watch_task
            return await self._transport.disconnect()
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("registry.disconnect_failed", str(e)))

    async def list_agents(self) -> Result[List[AgentInfo]]:
        """List all currently registered agents."""
        if not self._connected:
            return Result(ok=False, error=ErrorInfo("registry.not_connected", "Not connected"))
        
        try:
            # Get all agent registry keys
            result = await self._transport._redis.keys("mcp:agents:*")
            agents = []
            
            for key in result:
                agent_id = key.decode('utf-8').replace("mcp:agents:", "")
                agent_data = await self._transport._redis.get(key)
                if agent_data:
                    try:
                        data = json.loads(agent_data.decode('utf-8'))
                        # Remove any extra fields that aren't in AgentInfo
                        agent_fields = {
                            "id", "name", "project", "model", "cwd", "host", 
                            "pid", "started_at", "state", "ctx_pct"
                        }
                        filtered_data = {k: v for k, v in data.items() if k in agent_fields}
                        agent_info = AgentInfo(**filtered_data)
                        agents.append(agent_info)
                    except Exception as e:
                        log("WARN", "registry", "parse_agent_failed", agent_id=agent_id, error=str(e))
            
            return Result(ok=True, value=agents)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("registry.list_failed", str(e)))

    async def register_agent(self, agent_info: AgentInfo) -> Result[None]:
        """Register an agent in the registry."""
        if not self._connected:
            return Result(ok=False, error=ErrorInfo("registry.not_connected", "Not connected"))
        
        try:
            key = f"mcp:agents:{agent_info.id}"
            data = json.dumps({
                "id": agent_info.id,
                "name": agent_info.name,
                "project": agent_info.project,
                "model": agent_info.model,
                "cwd": agent_info.cwd,
                "host": agent_info.host,
                "pid": agent_info.pid,
                "started_at": agent_info.started_at,
                "state": agent_info.state,
                "ctx_pct": agent_info.ctx_pct
            })
            
            # Set with TTL (heartbeat will refresh)
            result = await self._transport.set_key(key, data, ttl=30)  # 30 second TTL
            if result.ok:
                self._agents[agent_info.id] = agent_info
                log("INFO", "registry", "agent_registered", agent_id=agent_info.id)
            return result
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("registry.register_failed", str(e)))

    async def unregister_agent(self, agent_id: str) -> Result[None]:
        """Unregister an agent from the registry."""
        if not self._connected:
            return Result(ok=False, error=ErrorInfo("registry.not_connected", "Not connected"))
        
        try:
            key = f"mcp:agents:{agent_id}"
            result = await self._transport.delete_key(key)
            if result.ok:
                if agent_id in self._agents:
                    del self._agents[agent_id]
                log("INFO", "registry", "agent_unregistered", agent_id=agent_id)
            return result
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("registry.unregister_failed", str(e)))

    async def update_agent_state(self, agent_id: str, state: str, ctx_pct: float = 0.0) -> Result[None]:
        """Update an agent's state and context percentage."""
        if not self._connected:
            return Result(ok=False, error=ErrorInfo("registry.not_connected", "Not connected"))
        
        try:
            key = f"mcp:agents:{agent_id}"
            agent_data = await self._transport._redis.get(key)
            if agent_data:
                data = json.loads(agent_data.decode('utf-8'))
                data["state"] = state
                data["ctx_pct"] = ctx_pct
                data["updated_at"] = time.time()
                
                result = await self._transport.set_key(key, json.dumps(data), ttl=30)
                if result.ok and agent_id in self._agents:
                    self._agents[agent_id].state = state
                    self._agents[agent_id].ctx_pct = ctx_pct
                return result
            else:
                return Result(ok=False, error=ErrorInfo("registry.agent_not_found", f"Agent {agent_id} not found"))
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("registry.update_failed", str(e)))

    def watch(self, callback: Callable[[RegistryEvent], None]) -> None:
        """Set callback for registry events."""
        self._watch_callback = callback

    async def _watch_registry(self) -> None:
        """Watch for registry changes via Redis pub/sub."""
        if not self._connected:
            return
        
        try:
            # Subscribe to registry events
            registry_channel = "mcp:registry:events"
            
            def on_registry_event(data: bytes):
                try:
                    event_data = json.loads(data.decode('utf-8'))
                    event_type = event_data.get("type")
                    agent_data = event_data.get("agent")
                    
                    if event_type and agent_data and self._watch_callback:
                        agent_info = AgentInfo(**agent_data)
                        event = RegistryEvent(event_type, agent_info)
                        self._watch_callback(event)
                except Exception as e:
                    log("ERROR", "registry", "parse_event_failed", error=str(e))
            
            await self._transport.subscribe(registry_channel, on_registry_event)
            
            # Keep watching
            while self._connected:
                await asyncio.sleep(1)
        except Exception as e:
            log("ERROR", "registry", "watch_failed", error=str(e))
