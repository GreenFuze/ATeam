"""Agent session management with MCP client and tail subscription."""

import asyncio
from typing import Optional, Dict, Any, List

from ..mcp.client import MCPClient
from ..mcp.ownership import OwnershipManager
from ..util.logging import log
from ..util.types import Result, ErrorInfo


class AgentSession:
    """Session for managing connection to a single agent."""
    
    def __init__(self, redis_url: str, agent_id: str, ui, takeover: bool = False, grace_timeout: int = 30) -> None:
        self.redis_url = redis_url
        self.agent_id = agent_id
        self.ui = ui
        self.takeover = takeover
        self.grace_timeout = grace_timeout
        
        # MCP client for RPC calls
        self.client: Optional[MCPClient] = None
        
        # Ownership management
        self.ownership: Optional[OwnershipManager] = None
        self._ownership_token: Optional[str] = None
        self._read_only_mode = False
        
        # Tail subscription
        self._tail_task: Optional[asyncio.Task] = None
        self._notification_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def attach(self) -> Result[None]:
        """Attach to the agent session."""
        try:
            log("INFO", "session", "attach_start", agent_id=self.agent_id)
            
            # 1. Connect MCP client
            self.client = MCPClient(self.redis_url, self.agent_id)
            client_result = await self.client.connect()
            if not client_result.ok:
                return client_result
            
            # 2. Connect ownership manager
            self.ownership = OwnershipManager(self.redis_url)
            ownership_result = await self.ownership.connect()
            if not ownership_result.ok:
                return ownership_result
            
            # 3. Acquire ownership
            acquire_result = await self.ownership.acquire(self.agent_id, self.takeover, self.grace_timeout)
            if not acquire_result.ok:
                if acquire_result.error.code == "ownership.denied":
                    self.ui.print_error(f"Agent {self.agent_id} is owned by another console. Use --takeover to force takeover.")
                return acquire_result
            
            self._ownership_token = acquire_result.value
            self._read_only_mode = False
            log("INFO", "session", "ownership_acquired", agent_id=self.agent_id, token=self._ownership_token)
            
            # 4. Start tail subscription
            self._running = True
            self._tail_task = asyncio.create_task(self._tail_loop())
            self._notification_task = asyncio.create_task(self._notification_loop())
            
            log("INFO", "session", "attach_complete", agent_id=self.agent_id)
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "session", "attach_failed", agent_id=self.agent_id, error=str(e))
            return Result(ok=False, error=ErrorInfo("session.attach_failed", str(e)))
    
    async def detach(self) -> None:
        """Detach from the agent session."""
        try:
            log("INFO", "session", "detach_start", agent_id=self.agent_id)
            
            # Stop tasks
            self._running = False
            if self._tail_task:
                self._tail_task.cancel()
                try:
                    await self._tail_task
                except asyncio.CancelledError:
                    pass
            
            if self._notification_task:
                self._notification_task.cancel()
                try:
                    await self._notification_task
                except asyncio.CancelledError:
                    pass
            
            # Release ownership
            if self.ownership and self._ownership_token:
                release_result = await self.ownership.release(self.agent_id, self._ownership_token)
                if release_result.ok:
                    log("INFO", "session", "ownership_released", agent_id=self.agent_id)
                else:
                    log("WARN", "session", "ownership_release_failed", 
                        agent_id=self.agent_id, error=release_result.error.message)
            
            # Disconnect MCP client
            if self.client:
                await self.client.disconnect()
            
            # Disconnect ownership manager
            if self.ownership:
                await self.ownership.disconnect()
            
            log("INFO", "session", "detach_complete", agent_id=self.agent_id)
            
        except Exception as e:
            log("ERROR", "session", "detach_failed", agent_id=self.agent_id, error=str(e))
    
    async def _notification_loop(self) -> None:
        """Monitor for takeover notifications."""
        while self._running:
            try:
                if self.ownership:
                    notifications_result = await self.ownership.check_takeover_notifications()
                    if notifications_result.ok and notifications_result.value:
                        for notification in notifications_result.value:
                            await self._handle_takeover_notification(notification)
                
                await asyncio.sleep(2)  # Check every 2 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                log("ERROR", "session", "notification_loop_error", 
                    agent_id=self.agent_id, error=str(e))
                await asyncio.sleep(5)  # Wait longer on error
    
    async def _handle_takeover_notification(self, notification: Dict[str, Any]) -> None:
        """Handle takeover notification from another console."""
        try:
            agent_id = notification.get("agent_id")
            new_session = notification.get("new_session")
            grace_timeout = notification.get("grace_timeout", 30)
            
            if agent_id == self.agent_id:
                # We're being taken over
                self._read_only_mode = True
                self._ownership_token = None
                
                # Display takeover warning banner
                self.ui.notify(
                    f"⚠️  OWNERSHIP LOST: Agent {agent_id} has been taken over by another console. "
                    f"You are now in read-only mode.",
                    "warn"
                )
                
                # Show sticky banner in UI
                if hasattr(self.ui, 'show_takeover_banner'):
                    self.ui.show_takeover_banner(agent_id, new_session, grace_timeout)
                
                log("WARN", "session", "takeover_received", 
                    agent_id=agent_id, new_session=new_session, grace_timeout=grace_timeout)
                
        except Exception as e:
            log("ERROR", "session", "takeover_notification_handle_error", 
                agent_id=self.agent_id, error=str(e))
    
    def is_read_only(self) -> bool:
        """Check if the session is in read-only mode."""
        return self._read_only_mode
    
    def get_ownership_token(self) -> Optional[str]:
        """Get the current ownership token."""
        return self._ownership_token if not self._read_only_mode else None
    
    async def _tail_loop(self) -> None:
        """Main loop for tail subscription."""
        try:
            if not self.client:
                return
            
            # Subscribe to agent tail with callback
            def on_tail_event(event):
                asyncio.create_task(self._handle_tail_event(event))
            
            subscribe_result = await self.client.subscribe_tail(on_tail_event)
            if not subscribe_result.ok:
                log("ERROR", "session", "tail_subscribe_failed", agent_id=self.agent_id, error=subscribe_result.error.message)
                return
            
            log("INFO", "session", "tail_subscribed", agent_id=self.agent_id)
            
            # Keep the task running until cancelled
            while self._running:
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            log("INFO", "session", "tail_cancelled", agent_id=self.agent_id)
        except Exception as e:
            log("ERROR", "session", "tail_loop_error", agent_id=self.agent_id, error=str(e))
        finally:
            # Unsubscribe from tail
            if self.client:
                await self.client.unsubscribe_tail()
    
    async def _handle_tail_event(self, event: Dict[str, Any]) -> None:
        """Handle a tail event from the agent."""
        try:
            event_type = event.get("type", "unknown")
            
            # Send to panes if available
            if hasattr(self.ui, 'panes') and self.ui.panes and self.ui.panes.is_running():
                self.ui.panes.add_tail_event(event)
            
            if event_type == "task.start":
                self.ui.notify(f"Task started: {event.get('id', 'unknown')}", "info")
                
            elif event_type == "task.complete":
                self.ui.notify(f"Task completed: {event.get('id', 'unknown')}", "success")
                
            elif event_type == "task.error":
                self.ui.print_error(f"Task error: {event.get('error', 'unknown error')}")
                
            elif event_type == "token":
                # Stream token to UI
                token = event.get("token", "")
                if token:
                    print(token, end="", flush=True)
                
            elif event_type == "warn":
                self.ui.notify(event.get("msg", "Warning"), "warn")
                
            elif event_type == "error":
                self.ui.print_error(event.get("msg", "Error"))
                
            else:
                # Unknown event type - log for debugging
                log("DEBUG", "session", "unknown_tail_event", agent_id=self.agent_id, event_type=event_type)
                
        except Exception as e:
            log("ERROR", "session", "tail_event_error", agent_id=self.agent_id, error=str(e))
    
    async def send_input(self, text: str) -> Result[None]:
        """Send input to the agent."""
        try:
            if not self.client:
                return Result(ok=False, error=ErrorInfo("session.not_connected", "Not connected to agent"))
            
            result = await self.client.call("input", {"text": text, "meta": {"source": "console"}})
            if result.ok:
                log("DEBUG", "session", "input_sent", agent_id=self.agent_id, text_length=len(text))
                return Result(ok=True)
            else:
                return Result(ok=False, error=result.error)
                
        except Exception as e:
            log("ERROR", "session", "send_input_failed", agent_id=self.agent_id, error=str(e))
            return Result(ok=False, error=ErrorInfo("session.send_input_failed", str(e)))

    async def send_interrupt(self) -> Result[None]:
        """Send interrupt to the agent."""
        try:
            if not self.client:
                return Result(ok=False, error=ErrorInfo("session.not_connected", "Not connected to agent"))
            
            result = await self.client.call("interrupt", {})
            if result.ok:
                log("DEBUG", "session", "interrupt_sent", agent_id=self.agent_id)
                return Result(ok=True)
            else:
                return Result(ok=False, error=result.error)
                
        except Exception as e:
            log("ERROR", "session", "send_interrupt_failed", agent_id=self.agent_id, error=str(e))
            return Result(ok=False, error=ErrorInfo("session.send_interrupt_failed", str(e)))
    
    async def get_status(self) -> Result[Dict[str, Any]]:
        """Get agent status."""
        try:
            if not self.client:
                return Result(ok=False, error=ErrorInfo("session.not_connected", "Not connected to agent"))
            
            # Call the status RPC
            result = await self.client.call("status", {})
            if not result.ok:
                return result
            
            status = result.value
            status["agent_id"] = self.agent_id
            
            return Result(ok=True, value=status)
            
        except Exception as e:
            log("ERROR", "session", "get_status_error", agent_id=self.agent_id, error=str(e))
            return Result(ok=False, error=ErrorInfo("session.get_status_failed", str(e)))
    
    async def get_context(self) -> Result[Dict[str, Any]]:
        """Get agent context/memory information."""
        try:
            if not self.client:
                return Result(ok=False, error=ErrorInfo("session.not_connected", "Not connected to agent"))
            
            # For now, return basic info - will be enhanced with actual memory stats
            status_result = await self.get_status()
            if not status_result.ok:
                return status_result
            
            status = status_result.value
            
            # Mock context info for now
            context = {
                "tokens_in": 0,
                "tokens_out": 0,
                "ctx_pct": status.get("ctx_pct", 0.0),
                "history_turns": 0,
                "queue_items": 0
            }
            
            return Result(ok=True, value=context)
            
        except Exception as e:
            log("ERROR", "session", "get_context_error", agent_id=self.agent_id, error=str(e))
            return Result(ok=False, error=ErrorInfo("session.get_context_failed", str(e)))
    
    async def get_system_prompt(self) -> Result[dict]:
        """Get the agent's system prompt."""
        try:
            if not self.client:
                return Result(ok=False, error=ErrorInfo("session.not_connected", "Not connected to agent"))
            
            result = await self.client.call("prompt.get", {})
            if not result.ok:
                return result
            
            return Result(ok=True, value=result.value)
            
        except Exception as e:
            log("ERROR", "session", "get_system_prompt_error", agent_id=self.agent_id, error=str(e))
            return Result(ok=False, error=ErrorInfo("session.get_system_prompt_failed", str(e)))
    
    async def reload_system_prompt(self) -> Result[None]:
        """Reload the agent's system prompt."""
        try:
            if not self.client:
                return Result(ok=False, error=ErrorInfo("session.not_connected", "Not connected to agent"))
            
            # Call the prompt.reload RPC
            result = await self.client.call("prompt.reload", {})
            if not result.ok:
                return result
            
            log("INFO", "session", "system_prompt_reloaded", agent_id=self.agent_id)
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "session", "reload_system_prompt_error", agent_id=self.agent_id, error=str(e))
            return Result(ok=False, error=ErrorInfo("session.reload_system_prompt_failed", str(e)))

    async def add_overlay(self, line: str) -> Result[None]:
        """Add a line to the system prompt overlay."""
        try:
            if not self.client:
                return Result(ok=False, error=ErrorInfo("session.not_connected", "Not connected to agent"))
            
            # Call the prompt.overlay RPC
            result = await self.client.call("prompt.overlay", {"line": line})
            if not result.ok:
                return result
            
            log("INFO", "session", "overlay_added", agent_id=self.agent_id, line=line)
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "session", "add_overlay_error", agent_id=self.agent_id, error=str(e))
            return Result(ok=False, error=ErrorInfo("session.add_overlay_failed", str(e)))
    
    async def kb_search(self, query: str, scope: str = "agent") -> Result[List[Dict[str, Any]]]:
        """Search KB."""
        try:
            if not self.client:
                return Result(ok=False, error=ErrorInfo("session.not_connected", "Not connected to agent"))
            
            result = await self.client.call("kb.search", {"query": query, "scope": scope})
            if not result.ok:
                return Result(ok=False, error=ErrorInfo("kb_search_failed", result.error.message))
            return Result(ok=True, value=result.value.get("hits", []))
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("kb_search_error", str(e)))

    async def kb_ingest(self, paths: List[str], scope: str = "agent") -> Result[List[str]]:
        """Ingest files into KB."""
        try:
            if not self.client:
                return Result(ok=False, error=ErrorInfo("session.not_connected", "Not connected to agent"))
            
            result = await self.client.call("kb.ingest", {"paths": paths, "scope": scope})
            if not result.ok:
                return Result(ok=False, error=ErrorInfo("kb_ingest_failed", result.error.message))
            return Result(ok=True, value=result.value.get("ids", []))
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("kb_ingest_error", str(e)))

    async def kb_copy_from(self, source_agent: str, ids: List[str]) -> Result[Dict[str, List[str]]]:
        """Copy items from another agent."""
        try:
            if not self.client:
                return Result(ok=False, error=ErrorInfo("session.not_connected", "Not connected to agent"))
            
            result = await self.client.call("kb.copy_from", {"source_agent": source_agent, "ids": ids})
            if not result.ok:
                return Result(ok=False, error=ErrorInfo("kb_copy_failed", result.error.message))
            return Result(ok=True, value={
                "copied": result.value.get("copied", []),
                "skipped": result.value.get("skipped", [])
            })
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("kb_copy_error", str(e)))

    async def set_system_prompt(self, base: Optional[str] = None, overlay: Optional[str] = None) -> Result[None]:
        """Set the agent's system prompt."""
        try:
            if not self.client:
                return Result(ok=False, error=ErrorInfo("session.not_connected", "Not connected to agent"))
            
            params = {}
            if base is not None:
                params["base"] = base
            if overlay is not None:
                params["overlay"] = overlay
            
            result = await self.client.call("prompt.set", params)
            if not result.ok:
                return result
            
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "session", "set_system_prompt_error", agent_id=self.agent_id, error=str(e))
            return Result(ok=False, error=ErrorInfo("session.set_system_prompt_failed", str(e)))

    async def append_overlay_line(self, line: str) -> Result[None]:
        """Append a line to the system prompt overlay."""
        try:
            if not self.client:
                return Result(ok=False, error=ErrorInfo("session.not_connected", "Not connected to agent"))
            
            # Get current overlay
            prompt_result = await self.get_system_prompt()
            if not prompt_result.ok:
                return prompt_result
            
            current_overlay = prompt_result.value.get("overlay", "")
            current_lines = prompt_result.value.get("overlay_lines", [])
            
            # Add new line
            new_lines = current_lines + [line.strip()]
            new_overlay = '\n'.join(new_lines)
            
            # Set the new overlay
            return await self.set_system_prompt(overlay=new_overlay)
            
        except Exception as e:
            log("ERROR", "session", "append_overlay_line_error", agent_id=self.agent_id, error=str(e))
            return Result(ok=False, error=ErrorInfo("session.append_overlay_line_failed", str(e)))
    
    async def clear_history(self) -> Result[None]:
        """Clear the agent's conversation history."""
        try:
            if not self.client:
                return Result(ok=False, error=ErrorInfo("session.not_connected", "Not connected to agent"))
            
            # Call the agent's history.clear method
            result = await self.client.call("history.clear", {"confirm": True})
            if not result.ok:
                return result
            
            log("INFO", "session", "history_cleared", agent_id=self.agent_id)
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "session", "clear_history_failed", agent_id=self.agent_id, error=str(e))
            return Result(ok=False, error=ErrorInfo("session.clear_history_failed", str(e)))
