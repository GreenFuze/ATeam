"""Console application main loop and session management."""

import asyncio
import os
from typing import Dict, Optional

from ..mcp.registry import MCPRegistryClient
from ..mcp.ownership import OwnershipManager
from ..mcp.client import MCPClient
from ..util.logging import log
from ..util.types import Result, ErrorInfo

from .ui import ConsoleUI
from .cmd_router import CommandRouter
from .attach import AgentSession


class ConsoleApp:
    """Main console application with event loop and session management."""
    
    def __init__(self, redis_url: str, use_panes: bool = False, takeover: bool = False, grace_timeout: int = 30) -> None:
        self.redis_url = redis_url
        self.use_panes = use_panes
        self.takeover = takeover
        self.grace_timeout = grace_timeout
        
        # Core components
        self.registry: Optional[MCPRegistryClient] = None
        self.ownership: Optional[OwnershipManager] = None
        self.ui: Optional[ConsoleUI] = None
        self.router: Optional[CommandRouter] = None
        
        # Session management
        self._sessions: Dict[str, AgentSession] = {}
        self._running = False
        self._current_session: Optional[str] = None
    
    async def bootstrap(self) -> Result[None]:
        """Bootstrap the console: connect to Redis, initialize components."""
        try:
            log("INFO", "console", "bootstrap_start")
            
            # 1. Connect to registry
            self.registry = MCPRegistryClient(self.redis_url)
            registry_result = await self.registry.connect()
            if not registry_result.ok:
                return registry_result
            
            # 2. Connect to ownership manager
            self.ownership = OwnershipManager(self.redis_url)
            ownership_result = await self.ownership.connect()
            if not ownership_result.ok:
                return ownership_result
            
            # 3. Initialize UI
            self.ui = ConsoleUI(use_panes=self.use_panes)
            self.ui.set_app(self)  # Set app reference for panes integration
            
            # 4. Initialize command router
            self.router = CommandRouter(self, self.ui)
            
            self._running = True
            
            log("INFO", "console", "bootstrap_complete")
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "console", "bootstrap_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("console.bootstrap_failed", str(e)))
    
    def run(self) -> None:
        """Run the console application."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._run())
        finally:
            loop.close()
    
    async def _run(self) -> None:
        """Main event loop."""
        # Bootstrap
        bootstrap_result = await self.bootstrap()
        if not bootstrap_result.ok:
            print(f"Failed to start console: {bootstrap_result.error.message}")
            return
        
        # Show welcome message
        self.ui.notify("Connected. Press F1 to list agents.", "info")
        
        # Main loop
        while self._running:
            try:
                line = self.ui.read_command()
                if line == "":
                    await asyncio.sleep(0.02)
                    continue
                
                await self.router.execute(line)
                
            except KeyboardInterrupt:
                print("\nInterrupted. Type 'quit' to exit.")
            except EOFError:
                print("\nEOF received. Exiting.")
                break
            except Exception as e:
                log("ERROR", "console", "run_error", error=str(e))
                print(f"Error: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the console and cleanup resources."""
        try:
            self._running = False
            
            # Stop panes if running
            if self.ui and self.ui.panes:
                self.ui.panes.stop()
            
            # Close all sessions
            for session_id in list(self._sessions.keys()):
                await self.detach_session(session_id)
            
            # Disconnect from Redis
            if self.ownership:
                await self.ownership.disconnect()
            
            if self.registry:
                await self.registry.disconnect()
            
            log("INFO", "console", "shutdown_complete")
            
        except Exception as e:
            log("ERROR", "console", "shutdown_error", error=str(e))
    
    async def attach_session(self, agent_id: str) -> Result[None]:
        """Attach to an agent session."""
        try:
            if agent_id in self._sessions:
                return Result(ok=False, error=ErrorInfo("console.session_exists", f"Already attached to {agent_id}"))
            
            # Create session
            session = AgentSession(self.redis_url, agent_id, self.ui, self.takeover, self.grace_timeout)
            attach_result = await session.attach()
            if not attach_result.ok:
                return attach_result
            
            self._sessions[agent_id] = session
            self._current_session = agent_id
            
            log("INFO", "console", "session_attached", agent_id=agent_id)
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "console", "attach_failed", agent_id=agent_id, error=str(e))
            return Result(ok=False, error=ErrorInfo("console.attach_failed", str(e)))
    
    async def detach_session(self, agent_id: str) -> Result[None]:
        """Detach from an agent session."""
        try:
            if agent_id not in self._sessions:
                return Result(ok=False, error=ErrorInfo("console.session_not_found", f"Not attached to {agent_id}"))
            
            session = self._sessions[agent_id]
            await session.detach()
            
            del self._sessions[agent_id]
            
            if self._current_session == agent_id:
                self._current_session = None
            
            log("INFO", "console", "session_detached", agent_id=agent_id)
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "console", "detach_failed", agent_id=agent_id, error=str(e))
            return Result(ok=False, error=ErrorInfo("console.detach_failed", str(e)))
    
    def get_current_session(self) -> Optional[AgentSession]:
        """Get the currently active session."""
        if self._current_session and self._current_session in self._sessions:
            return self._sessions[self._current_session]
        return None
    
    def list_sessions(self) -> Dict[str, AgentSession]:
        """Get all active sessions."""
        return self._sessions.copy()
