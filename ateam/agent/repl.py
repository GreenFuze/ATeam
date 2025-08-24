import asyncio
from typing import TYPE_CHECKING
from ..util.types import Result, ErrorInfo
from ..util.logging import log
from .completer import AgentCompleter

if TYPE_CHECKING:
    from .main import AgentApp

class AgentREPL:
    def __init__(self, app: "AgentApp") -> None:
        self.app = app
        self.completer = AgentCompleter([
            "status", "enqueue", "sys", "reload", "kb", "add", "help", "quit"
        ])
        self.running = False

    async def loop(self) -> None:
        """Main REPL loop."""
        self.running = True
        print(f"[{self.app.agent_id}] Agent REPL started. Type 'help' for commands.")
        
        while self.running and self.app.running:
            try:
                # Simple input for now - will be enhanced with prompt-toolkit
                line = input(f"[{self.app.agent_id}]> ").strip()
                
                if not line:
                    continue
                
                await self._handle_command(line)
                
            except KeyboardInterrupt:
                print("\nInterrupted. Type 'quit' to exit.")
                # Don't break immediately - let signal handler manage shutdown
            except EOFError:
                print("\nEOF received. Exiting.")
                break
            except Exception as e:
                log("ERROR", "repl", "loop_error", error=str(e))
                print(f"Error: {e}")
        
        print(f"[{self.app.agent_id}] REPL shutting down...")

    def stop(self) -> None:
        """Stop the REPL loop."""
        self.running = False

    async def _handle_command(self, line: str) -> None:
        """Handle a command line."""
        parts = line.split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if cmd == "help":
            self._show_help()
        elif cmd == "status":
            await self._cmd_status()
        elif cmd == "enqueue":
            await self._cmd_enqueue(args)
        elif cmd == "sys":
            await self._cmd_sys(args)
        elif cmd == "reload":
            await self._cmd_reload()
        elif cmd == "kb":
            await self._cmd_kb(args)
        elif cmd == "clearhistory":
            await self._cmd_clearhistory(args)
        elif cmd == "quit":
            await self._cmd_quit()
        else:
            print(f"Unknown command: {cmd}. Type 'help' for available commands.")

    def _show_help(self) -> None:
        """Show help information."""
        mode_info = " (STANDALONE MODE)" if self.app.standalone_mode else ""
        help_text = f"""
Available commands{mode_info}:
  help                    - Show this help
  status                  - Show agent status
  enqueue <text>          - Add text to queue
  sys show                - Show system prompt
  sys reload              - Reload system prompt from disk
  kb add <path>           - Add file to knowledge base
  reload                  - Reload all prompts
  clearhistory            - Clear conversation history (requires confirmation)
  quit                    - Exit agent
        """
        if self.app.standalone_mode:
            help_text += """

Note: Running in standalone mode. Distributed features (console connection, 
cross-agent communication) are not available.
        """
        print(help_text.strip())

    async def _cmd_status(self) -> None:
        """Handle status command."""
        if not self.app.queue:
            print("Queue not initialized")
            return
        
        queue_size = self.app.queue.size()
        history_size = self.app.history.size() if self.app.history else 0
        
        print(f"Status:")
        print(f"  Agent ID: {self.app.agent_id}")
        print(f"  Mode: {'STANDALONE' if self.app.standalone_mode else 'CONNECTED'}")
        print(f"  State: {self.app.state}")
        print(f"  Queue size: {queue_size}")
        print(f"  History size: {history_size}")
        print(f"  CWD: {self.app.cwd}")
        
        if self.app.standalone_mode:
            print(f"  Note: Running in standalone mode - distributed features unavailable")

    async def _cmd_enqueue(self, args: list[str]) -> None:
        """Handle enqueue command."""
        if not args:
            print("Usage: enqueue <text>")
            return
        
        if not self.app.queue:
            print("Queue not initialized")
            return
        
        text = " ".join(args)
        result = self.app.queue.append(text, "local")
        
        if result.ok:
            print(f"Queued: {text}")
        else:
            print(f"Failed to queue: {result.error.message}")

    async def _cmd_sys(self, args: list[str]) -> None:
        """Handle sys command."""
        if not args:
            print("Usage: sys <show|reload>")
            return
        
        subcmd = args[0].lower()
        
        if subcmd == "show":
            if not self.app.prompts:
                print("Prompt layer not initialized")
                return
            
            print("System Prompt:")
            print("=" * 50)
            print(self.app.prompts.effective())
            print("=" * 50)
            
        elif subcmd == "reload":
            if not self.app.prompts:
                print("Prompt layer not initialized")
                return
            
            result = self.app.prompts.reload_from_disk()
            if result.ok:
                print("System prompt reloaded")
            else:
                print(f"Failed to reload: {result.error.message}")
        else:
            print(f"Unknown sys command: {subcmd}")

    async def _cmd_reload(self) -> None:
        """Handle reload command."""
        if not self.app.prompts:
            print("Prompt layer not initialized")
            return
        
        result = self.app.prompts.reload_from_disk()
        if result.ok:
            print("Prompts reloaded")
        else:
            print(f"Failed to reload: {result.error.message}")

    async def _cmd_kb(self, args: list[str]) -> None:
        """Handle kb command."""
        if not args:
            print("Usage: kb <add> <path>")
            return
        
        subcmd = args[0].lower()
        
        if subcmd == "add":
            if len(args) < 2:
                print("Usage: kb add <path>")
                return
            
            path = args[1]
            print(f"KB add not implemented yet: {path}")
        else:
            print(f"Unknown kb command: {subcmd}")

    async def _cmd_clearhistory(self, args: list[str]) -> None:
        """Handle clearhistory command with confirmation."""
        if not self.app.history:
            print("History not initialized")
            return
        
        # Check for confirmation
        if not args or args[0] != "--confirm":
            print("WARNING: This will permanently delete all conversation history and summaries.")
            print("This action cannot be undone.")
            print("")
            print("To confirm, run: clearhistory --confirm")
            print("")
            print("History statistics:")
            stats = self.app.history.get_summarization_stats()
            print(f"  Total summaries: {stats['total_summaries']}")
            print(f"  Total turns summarized: {stats['total_turns_summarized']}")
            print(f"  Total tokens summarized: {stats['total_tokens_summarized']}")
            print(f"  Current history size: {self.app.history.size()}")
            return
        
        # User confirmed - clear history
        result = self.app.history.clear(confirm=True)
        if result.ok:
            print("✓ Conversation history cleared successfully")
        else:
            print(f"✗ Failed to clear history: {result.error.message}")

    async def _cmd_quit(self) -> None:
        """Handle quit command."""
        print("Shutting down agent...")
        self.running = False
        
        # Shutdown the app
        if self.app:
            await self.app.shutdown()
