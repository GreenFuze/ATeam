import asyncio
import json
import time
from typing import Optional, List, Dict, Any
from .redis_transport import RedisTransport
from ..util.types import Result, ErrorInfo
from ..util.const import DEFAULTS
from ..util.logging import log

class HeartbeatService:
    def __init__(self, agent_id: str, redis_url: str, ttl_sec: Optional[int] = None, identity: Optional[Any] = None, registry: Optional[Any] = None) -> None:
        self.agent_id = agent_id
        self.redis_url = redis_url
        self.ttl_sec = ttl_sec if ttl_sec is not None else DEFAULTS["HEARTBEAT_TTL_SEC"]
        self.interval_sec = DEFAULTS["HEARTBEAT_INTERVAL_SEC"]
        self._transport = RedisTransport(redis_url)
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False
        self._identity = identity  # AgentIdentity instance for lock refresh
        self._registry = registry  # MCPRegistryClient instance for registry refresh

    async def start(self) -> Result[None]:
        """Start the heartbeat service."""
        if self._running:
            return Result(ok=True)
        
        try:
            # Connect to Redis
            connect_result = await self._transport.connect()
            if not connect_result.ok:
                return connect_result
            
            self._running = True
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            log("INFO", "heartbeat", "started", agent_id=self.agent_id)
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("heartbeat.start_failed", str(e)))

    async def stop(self) -> Result[None]:
        """Stop the heartbeat service."""
        try:
            self._running = False
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
            await self._transport.disconnect()
            log("INFO", "heartbeat", "stopped", agent_id=self.agent_id)
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("heartbeat.stop_failed", str(e)))

    async def _heartbeat_loop(self) -> None:
        """Main heartbeat loop."""
        while self._running:
            try:
                await self._send_heartbeat()
                
                # Also refresh the single-instance lock if identity is available
                if self._identity:
                    try:
                        refresh_result = await self._identity.refresh_lock()
                        if not refresh_result.ok:
                            log("WARN", "heartbeat", "lock_refresh_failed", 
                                agent_id=self.agent_id, error=refresh_result.error.message)
                    except Exception as e:
                        log("ERROR", "heartbeat", "lock_refresh_error", 
                            agent_id=self.agent_id, error=str(e))
                
                # Also refresh the registry TTL if registry is available
                if self._registry:
                    try:
                        # Refresh registry TTL by updating the agent state
                        refresh_result = await self._registry.update_agent_state(self.agent_id, "registered", 0.0)
                        if not refresh_result.ok:
                            log("WARN", "heartbeat", "registry_refresh_failed", 
                                agent_id=self.agent_id, error=refresh_result.error.message)
                    except Exception as e:
                        log("ERROR", "heartbeat", "registry_refresh_error", 
                            agent_id=self.agent_id, error=str(e))
                
                await asyncio.sleep(self.interval_sec)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log("ERROR", "heartbeat", "loop_error", error=str(e), agent_id=self.agent_id)
                await asyncio.sleep(1)  # Brief pause before retry

    async def _send_heartbeat(self) -> None:
        """Send a heartbeat to Redis."""
        try:
            try:
                loop = asyncio.get_running_loop()
                pid = loop.time()
            except RuntimeError:
                pid = time.time()  # Fallback if no running loop
            
            heartbeat_data = {
                "agent_id": self.agent_id,
                "timestamp": time.time(),
                "pid": pid  # Placeholder for actual PID
            }
            
            # Set heartbeat key with TTL
            key = f"mcp:heartbeat:{self.agent_id}"
            result = await self._transport.set_key(key, str(heartbeat_data), ttl=self.ttl_sec)
            
            if not result.ok:
                error_msg = result.error.message if result.error else "Unknown error"
                log("ERROR", "heartbeat", "send_failed", error=error_msg, agent_id=self.agent_id)
            else:
                log("DEBUG", "heartbeat", "sent", agent_id=self.agent_id)
                
        except Exception as e:
            log("ERROR", "heartbeat", "send_error", error=str(e), agent_id=self.agent_id)


class HeartbeatMonitor:
    """Monitor for detecting disconnected agents via missed heartbeats."""
    
    def __init__(self, redis_url: str, check_interval: int = 30) -> None:
        self.redis_url = redis_url
        self.check_interval = check_interval
        self._transport = RedisTransport(redis_url)
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        self._callbacks: List[callable] = []
    
    async def start(self) -> Result[None]:
        """Start the heartbeat monitor."""
        if self._running:
            return Result(ok=True)
        
        try:
            # Connect to Redis
            connect_result = await self._transport.connect()
            if not connect_result.ok:
                return connect_result
            
            self._running = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            log("INFO", "heartbeat_monitor", "started", check_interval=self.check_interval)
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("heartbeat_monitor.start_failed", str(e)))
    
    async def stop(self) -> Result[None]:
        """Stop the heartbeat monitor."""
        try:
            self._running = False
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
            await self._transport.disconnect()
            log("INFO", "heartbeat_monitor", "stopped")
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("heartbeat_monitor.stop_failed", str(e)))
    
    def add_callback(self, callback: callable) -> None:
        """Add a callback for disconnected agent notifications."""
        self._callbacks.append(callback)
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_heartbeats()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log("ERROR", "heartbeat_monitor", "loop_error", error=str(e))
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _check_heartbeats(self) -> None:
        """Check for missed heartbeats and detect disconnected agents."""
        try:
            # Get all heartbeat keys
            pattern = "mcp:heartbeat:*"
            keys_result = await self._transport.scan_keys(pattern)
            if not keys_result.ok:
                log("ERROR", "heartbeat_monitor", "scan_failed", error=keys_result.error.message)
                return
            
            current_time = time.time()
            disconnected_agents = []
            
            for key in keys_result.value:
                try:
                    # Extract agent_id from key
                    agent_id = key.replace("mcp:heartbeat:", "")
                    
                    # Get heartbeat data
                    heartbeat_result = await self._transport.get_key(key)
                    if not heartbeat_result.ok or not heartbeat_result.value:
                        # Heartbeat key exists but no data - consider disconnected
                        disconnected_agents.append({
                            "agent_id": agent_id,
                            "reason": "no_data",
                            "last_seen": None
                        })
                        continue
                    
                    try:
                        # Parse heartbeat data
                        heartbeat_str = heartbeat_result.value.decode('utf-8')
                        # Handle both JSON and string formats
                        if heartbeat_str.startswith('{'):
                            heartbeat_data = json.loads(heartbeat_str)
                            last_seen = heartbeat_data.get("timestamp", 0)
                        else:
                            # Legacy string format - try to extract timestamp
                            last_seen = current_time - DEFAULTS["HEARTBEAT_TTL_SEC"] - 1
                        
                        # Check if heartbeat is stale
                        time_since_heartbeat = current_time - last_seen
                        if time_since_heartbeat > DEFAULTS["HEARTBEAT_TTL_SEC"] * 1.5:  # 1.5x TTL for grace
                            disconnected_agents.append({
                                "agent_id": agent_id,
                                "reason": "stale_heartbeat",
                                "last_seen": last_seen,
                                "time_since": time_since_heartbeat
                            })
                    
                    except Exception as e:
                        log("ERROR", "heartbeat_monitor", "parse_heartbeat_error", 
                            agent_id=agent_id, error=str(e))
                        disconnected_agents.append({
                            "agent_id": agent_id,
                            "reason": "parse_error",
                            "last_seen": None
                        })
                
                except Exception as e:
                    log("ERROR", "heartbeat_monitor", "check_agent_error", key=key, error=str(e))
            
            # Notify callbacks about disconnected agents
            if disconnected_agents:
                log("WARN", "heartbeat_monitor", "disconnected_agents_detected", 
                    count=len(disconnected_agents), agents=[a["agent_id"] for a in disconnected_agents])
                
                for callback in self._callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(disconnected_agents)
                        else:
                            callback(disconnected_agents)
                    except Exception as e:
                        log("ERROR", "heartbeat_monitor", "callback_error", error=str(e))
        
        except Exception as e:
            log("ERROR", "heartbeat_monitor", "check_error", error=str(e))
