import asyncio
import json
import time
import uuid
from typing import Optional
from .contracts import AgentId
from .redis_transport import RedisTransport
from ..util.types import Result, ErrorInfo
from ..util.logging import log
# Performance monitoring will be added in a future update
# from ..util.performance import measure_ownership_operation

class OwnershipManager:
    def __init__(self, redis_url: str) -> None:
        self._transport = RedisTransport(redis_url)
        self._connected = False
        self._session_id = str(uuid.uuid4())

    async def connect(self) -> Result[None]:
        """Connect to Redis."""
        try:
            result = await self._transport.connect()
            if result.ok:
                self._connected = True
            return result
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("ownership.connect_failed", str(e)))

    async def disconnect(self) -> Result[None]:
        """Disconnect from Redis."""
        try:
            self._connected = False
            return await self._transport.disconnect()
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("ownership.disconnect_failed", str(e)))

    async def acquire(self, agent_id: AgentId, takeover: bool = False, grace_timeout: int = 30) -> Result[str]:
        """Acquire ownership of an agent."""
        if not self._connected:
            return Result(ok=False, error=ErrorInfo("ownership.not_connected", "Not connected"))
        
        try:
            lock_key = f"mcp:agent:owner:{agent_id}"
            
            if takeover:
                # Graceful takeover with timeout
                result = await self._graceful_takeover(agent_id, lock_key, grace_timeout)
                if not result.ok:
                    return result
            
            # Try to acquire lock with TTL
            try:
                loop = asyncio.get_running_loop()
                console_pid = loop.time()
            except RuntimeError:
                console_pid = time.time()  # Fallback if no running loop
            
            lock_data = {
                "session_id": self._session_id,
                "acquired_at": time.time(),
                "console_pid": console_pid  # Placeholder for actual PID
            }
            
            # Use SET NX EX (set if not exists with expiry)
            result = await self._transport._redis.set(
                lock_key, 
                json.dumps(lock_data), 
                ex=300,  # 5 minute TTL
                nx=True  # Only set if key doesn't exist
            )
            
            if result:
                log("INFO", "ownership", "acquired", agent_id=agent_id, session_id=self._session_id)
                return Result(ok=True, value=self._session_id)
            else:
                # Check if we already own it
                existing_result = await self._transport.get_key(lock_key)
                if existing_result.ok and existing_result.value:
                    try:
                        existing_data = json.loads(existing_result.value.decode('utf-8'))
                        if existing_data.get("session_id") == self._session_id:
                            log("INFO", "ownership", "already_owned", agent_id=agent_id, session_id=self._session_id)
                            return Result(ok=True, value=self._session_id)
                    except:
                        pass
                
                return Result(ok=False, error=ErrorInfo("ownership.denied", f"Agent {agent_id} is owned by another console"))
                
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("ownership.acquire_failed", str(e)))

    async def release(self, agent_id: AgentId, token: str) -> Result[None]:
        """Release ownership of an agent."""
        if not self._connected:
            return Result(ok=False, error=ErrorInfo("ownership.not_connected", "Not connected"))
        
        try:
            lock_key = f"mcp:agent:owner:{agent_id}"
            
            # Verify we own it
            existing_result = await self._transport.get_key(lock_key)
            if existing_result.ok and existing_result.value:
                try:
                    existing_data = json.loads(existing_result.value.decode('utf-8'))
                    if existing_data.get("session_id") == token:
                        await self._transport.delete_key(lock_key)
                        log("INFO", "ownership", "released", agent_id=agent_id, session_id=token)
                        return Result(ok=True)
                except:
                    pass
            
            return Result(ok=False, error=ErrorInfo("ownership.not_owner", f"Session {token} does not own agent {agent_id}"))
            
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("ownership.release_failed", str(e)))

    async def _graceful_takeover(self, agent_id: AgentId, lock_key: str, grace_timeout: int) -> Result[None]:
        """Perform graceful takeover with timeout."""
        try:
            # Check if there's an existing owner
            existing_result = await self._transport.get_key(lock_key)
            if not existing_result.ok or not existing_result.value:
                # No existing owner, proceed normally
                return Result(ok=True)
            
            try:
                existing_data = json.loads(existing_result.value.decode('utf-8'))
                existing_session = existing_data.get("session_id")
                
                if existing_session == self._session_id:
                    # We already own it
                    return Result(ok=True)
                
                log("INFO", "ownership", "graceful_takeover_start", 
                    agent_id=agent_id, 
                    existing_session=existing_session,
                    grace_timeout=grace_timeout,
                    new_session=self._session_id)
                
                # Send takeover notification
                await self._send_takeover_notification(agent_id, existing_session, grace_timeout)
                
                # Wait for grace period
                start_time = time.time()
                while time.time() - start_time < grace_timeout:
                    # Check if the lock has been released
                    check_result = await self._transport.get_key(lock_key)
                    if not check_result.ok or not check_result.value:
                        log("INFO", "ownership", "graceful_release_detected", 
                            agent_id=agent_id, elapsed=time.time() - start_time)
                        return Result(ok=True)
                    
                    # Check if it's still the same owner
                    try:
                        current_data = json.loads(check_result.value.decode('utf-8'))
                        if current_data.get("session_id") != existing_session:
                            # Owner changed, might be us or someone else
                            if current_data.get("session_id") == self._session_id:
                                return Result(ok=True)
                            else:
                                # Someone else took over
                                return Result(ok=False, error=ErrorInfo(
                                    "ownership.takeover_conflict", 
                                    f"Another session took over agent {agent_id} during grace period"))
                    except:
                        pass
                    
                    await asyncio.sleep(1)  # Check every second
                
                # Grace period expired, force takeover
                log("WARN", "ownership", "force_takeover", 
                    agent_id=agent_id, 
                    existing_session=existing_session,
                    grace_timeout=grace_timeout)
                
                await self._transport.delete_key(lock_key)
                return Result(ok=True)
                
            except Exception as e:
                log("ERROR", "ownership", "graceful_takeover_parse_error", 
                    agent_id=agent_id, error=str(e))
                # If we can't parse the existing data, force takeover
                await self._transport.delete_key(lock_key)
                return Result(ok=True)
                
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("ownership.graceful_takeover_failed", str(e)))

    async def _send_takeover_notification(self, agent_id: AgentId, target_session: str, grace_timeout: int) -> None:
        """Send takeover notification to the current owner."""
        try:
            notification_key = f"mcp:takeover:notify:{target_session}"
            notification_data = {
                "agent_id": agent_id,
                "new_session": self._session_id,
                "grace_timeout": grace_timeout,
                "timestamp": time.time()
            }
            
            # Set notification with TTL slightly longer than grace timeout
            await self._transport._redis.set(
                notification_key,
                json.dumps(notification_data),
                ex=grace_timeout + 10
            )
            
            log("INFO", "ownership", "takeover_notification_sent",
                agent_id=agent_id, target_session=target_session, grace_timeout=grace_timeout)
                
        except Exception as e:
            log("ERROR", "ownership", "takeover_notification_failed", 
                agent_id=agent_id, target_session=target_session, error=str(e))

    async def check_takeover_notifications(self) -> Result[list]:
        """Check for pending takeover notifications for this session."""
        if not self._connected:
            return Result(ok=False, error=ErrorInfo("ownership.not_connected", "Not connected"))
        
        try:
            notification_key = f"mcp:takeover:notify:{self._session_id}"
            result = await self._transport.get_key(notification_key)
            
            if not result.ok or not result.value:
                return Result(ok=True, value=[])
            
            try:
                notification_data = json.loads(result.value.decode('utf-8'))
                # Remove the notification after reading
                await self._transport.delete_key(notification_key)
                
                log("INFO", "ownership", "takeover_notification_received",
                    agent_id=notification_data.get("agent_id"),
                    new_session=notification_data.get("new_session"),
                    grace_timeout=notification_data.get("grace_timeout"))
                
                return Result(ok=True, value=[notification_data])
                
            except Exception as e:
                log("ERROR", "ownership", "takeover_notification_parse_error", error=str(e))
                return Result(ok=True, value=[])
                
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("ownership.check_notifications_failed", str(e)))

    async def is_owner(self, agent_id: AgentId, token: str) -> Result[bool]:
        """Check if a session owns an agent."""
        if not self._connected:
            return Result(ok=False, error=ErrorInfo("ownership.not_connected", "Not connected"))
        
        try:
            lock_key = f"mcp:agent:owner:{agent_id}"
            existing_result = await self._transport.get_key(lock_key)
            
            if existing_result.ok and existing_result.value:
                try:
                    existing_data = json.loads(existing_result.value.decode('utf-8'))
                    is_owner = existing_data.get("session_id") == token
                    return Result(ok=True, value=is_owner)
                except:
                    return Result(ok=True, value=False)
            else:
                return Result(ok=True, value=False)
                
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("ownership.check_failed", str(e)))

    def has_ownership(self, agent_id: AgentId, token: str) -> bool:
        """Synchronous check if a session owns an agent (for server-side enforcement)."""
        # This is a simplified synchronous check for server-side enforcement
        # In a production system, this would need to be more sophisticated
        # For now, we'll assume ownership if we have a token and are in a session
        return bool(token and self._session_id == token)

    async def refresh(self, agent_id: AgentId, token: str) -> Result[None]:
        """Refresh ownership TTL."""
        if not self._connected:
            return Result(ok=False, error=ErrorInfo("ownership.not_connected", "Not connected"))
        
        try:
            lock_key = f"mcp:agent:owner:{agent_id}"
            
            # Verify we own it first
            is_owner_result = await self.is_owner(agent_id, token)
            if not is_owner_result.ok or not is_owner_result.value:
                return Result(ok=False, error=ErrorInfo("ownership.not_owner", f"Session {token} does not own agent {agent_id}"))
            
            # Refresh TTL
            existing = await self._transport.get_key(lock_key)
            if existing:
                await self._transport.set_key(lock_key, existing, ttl=300)  # 5 minute TTL
                log("DEBUG", "ownership", "refreshed", agent_id=agent_id, session_id=token)
                return Result(ok=True)
            else:
                return Result(ok=False, error=ErrorInfo("ownership.lock_missing", f"Lock for agent {agent_id} not found"))
                
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("ownership.refresh_failed", str(e)))
