import json
import time
import uuid
from pathlib import Path
from typing import Optional
from ..config.loader import load_stack
from ..util.types import Result, ErrorInfo
from ..util.logging import log

class AgentIdentity:
    def __init__(self, cwd: str, project_override: str = "", name_override: str = "", redis_url: str = None) -> None:
        self.cwd = Path(cwd).resolve()
        self.project_override = project_override
        self.name_override = name_override
        self.redis_url = redis_url
        self._computed_id: Optional[str] = None
        self._transport = None
        self._lock_session_id = str(uuid.uuid4())
        self._host_pid = f"{self._get_hostname()}:{self._get_pid()}"

    def compute(self) -> str:
        """Compute agent ID as 'project/agent'."""
        if self._computed_id:
            return self._computed_id

        # Get project name
        if self.project_override:
            project_name = self.project_override
        else:
            # Load config to get project name
            config_result = load_stack(str(self.cwd))
            if config_result.ok and config_result.value[0]:  # project config exists
                project_name = config_result.value[0].name
            else:
                # Fallback to directory name
                project_name = self.cwd.name

        # Get agent name
        if self.name_override:
            agent_name = self.name_override
        else:
            # Try to load from agent config
            agent_dir = self.cwd / ".ateam" / "agents"
            if agent_dir.exists():
                # Find first agent directory
                for d in agent_dir.iterdir():
                    if d.is_dir():
                        agent_yaml = d / "agent.yaml"
                        if agent_yaml.exists():
                            try:
                                import yaml
                                config = yaml.safe_load(agent_yaml.read_text())
                                if config and "name" in config:
                                    agent_name = config["name"]
                                    break
                            except Exception:
                                pass
                else:
                    # No agent config found, use directory name
                    agent_name = self.cwd.name
            else:
                # No .ateam/agents, use directory name
                agent_name = self.cwd.name

        self._computed_id = f"{project_name}/{agent_name}"
        return self._computed_id

    def _get_hostname(self) -> str:
        """Get hostname for lock identification."""
        try:
            import socket
            return socket.gethostname()
        except:
            return "unknown"

    def _get_pid(self) -> int:
        """Get process ID for lock identification."""
        try:
            import os
            return os.getpid()
        except:
            return 0

    async def _ensure_transport(self) -> Result[None]:
        """Ensure Redis transport is initialized."""
        if not self.redis_url:
            return Result(ok=False, error=ErrorInfo("identity.no_redis", "No Redis URL provided"))
        
        if not self._transport:
            try:
                from ..mcp.redis_transport import RedisTransport
                self._transport = RedisTransport(self.redis_url)
                result = await self._transport.connect()
                if not result.ok:
                    return result
            except Exception as e:
                return Result(ok=False, error=ErrorInfo("identity.transport_failed", str(e)))
        
        return Result(ok=True)

    async def acquire_lock(self) -> Result[None]:
        """Acquire single-instance lock for this agent."""
        if not self.redis_url:
            # No Redis, no lock needed (standalone mode)
            return Result(ok=True)
        
        transport_result = await self._ensure_transport()
        if not transport_result.ok:
            return transport_result
        
        try:
            agent_id = self.compute()
            lock_key = f"mcp:agent:lock:{agent_id}"
            
            # Try to acquire lock with TTL
            lock_data = {
                "session_id": self._lock_session_id,
                "host_pid": self._host_pid,
                "acquired_at": time.time()
            }
            
            # Use SET NX EX (set if not exists with expiry)
            result = await self._transport._redis.set(
                lock_key, 
                json.dumps(lock_data), 
                ex=300,  # 5 minute TTL
                nx=True  # Only set if key doesn't exist
            )
            
            if result:
                log("INFO", "identity", "lock_acquired", agent_id=agent_id, session_id=self._lock_session_id)
                return Result(ok=True)
            else:
                # Check if we already own it
                existing_result = await self._transport.get_key(lock_key)
                if existing_result.ok and existing_result.value:
                    try:
                        existing_data = json.loads(existing_result.value.decode('utf-8'))
                        if existing_data.get("session_id") == self._lock_session_id:
                            log("INFO", "identity", "lock_already_owned", agent_id=agent_id, session_id=self._lock_session_id)
                            return Result(ok=True)
                    except:
                        pass
                
                # Another instance is running
                log("ERROR", "identity", "lock_failed", agent_id=agent_id, error="Another instance is already running")
                return Result(ok=False, error=ErrorInfo("agent.duplicate", f"Another instance of {agent_id} is already running"))
                
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("identity.lock_failed", str(e)))

    async def refresh_lock(self) -> Result[None]:
        """Refresh the lock TTL."""
        if not self.redis_url:
            return Result(ok=True)
        
        transport_result = await self._ensure_transport()
        if not transport_result.ok:
            return transport_result
        
        try:
            agent_id = self.compute()
            lock_key = f"mcp:agent:lock:{agent_id}"
            
            # Verify we own it first
            existing_result = await self._transport.get_key(lock_key)
            if existing_result.ok and existing_result.value:
                try:
                    existing_data = json.loads(existing_result.value.decode('utf-8'))
                    if existing_data.get("session_id") == self._lock_session_id:
                        # Refresh TTL
                        await self._transport._redis.expire(lock_key, 300)  # 5 minute TTL
                        log("DEBUG", "identity", "lock_refreshed", agent_id=agent_id, session_id=self._lock_session_id)
                        return Result(ok=True)
                except:
                    pass
            
            return Result(ok=False, error=ErrorInfo("identity.lock_missing", f"Lock for agent {agent_id} not found or not owned"))
                
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("identity.refresh_failed", str(e)))

    async def release_lock(self) -> Result[None]:
        """Release the single-instance lock."""
        if not self.redis_url:
            return Result(ok=True)
        
        if not self._transport:
            return Result(ok=True)  # No transport, nothing to release
        
        try:
            agent_id = self.compute()
            lock_key = f"mcp:agent:lock:{agent_id}"
            
            # Verify we own it
            existing_result = await self._transport.get_key(lock_key)
            if existing_result.ok and existing_result.value:
                try:
                    existing_data = json.loads(existing_result.value.decode('utf-8'))
                    if existing_data.get("session_id") == self._lock_session_id:
                        await self._transport.delete_key(lock_key)
                        log("INFO", "identity", "lock_released", agent_id=agent_id, session_id=self._lock_session_id)
                        return Result(ok=True)
                except:
                    pass
            
            return Result(ok=False, error=ErrorInfo("identity.not_owner", f"Session {self._lock_session_id} does not own lock for agent {agent_id}"))
            
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("identity.release_failed", str(e)))

    async def disconnect(self) -> Result[None]:
        """Disconnect from Redis."""
        if self._transport:
            try:
                return await self._transport.disconnect()
            except Exception as e:
                return Result(ok=False, error=ErrorInfo("identity.disconnect_failed", str(e)))
        return Result(ok=True)
