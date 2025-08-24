"""Console UI with prompt-toolkit interface and rich input handling."""

import sys
from typing import Optional, List

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from ..util.logging import log


class ConsoleUI:
    """Console UI with prompt-toolkit interface and rich input handling."""
    
    def __init__(self, use_panes: bool = False) -> None:
        self.use_panes = use_panes
        self.completer = None
        self.prompt_session = None
        self.key_bindings = self._setup_key_bindings()
        self._setup_prompt_session()
        self.panes = None
        self.app = None  # Will be set by ConsoleApp
        self._takeover_banner_active = False
        self._read_only_banner_active = False
    
    def _setup_key_bindings(self) -> KeyBindings:
        """Setup key bindings for the console."""
        kb = KeyBindings()
        
        @kb.add(Keys.F1)
        def _(event):
            """F1 - Open help/palette."""
            self.print_help()
        
        @kb.add(Keys.F2)
        def _(event):
            """F2 - Toggle panes mode."""
            self.use_panes = not self.use_panes
            self.notify(f"Panes mode: {'ON' if self.use_panes else 'OFF'}", "info")
        
        @kb.add(Keys.F3)
        def _(event):
            """F3 - Show status."""
            self.notify("Status: Console active", "info")
        
        return kb
    
    def _setup_prompt_session(self) -> None:
        """Setup the prompt session."""
        try:
            self.prompt_session = PromptSession(
                completer=self.completer,
                key_bindings=self.key_bindings,
                complete_in_thread=True
            )
        except Exception as e:
            log("WARN", "ui", "prompt_session_failed", error=str(e))
            self.prompt_session = None
    
    def set_completer(self, completer) -> None:
        """Set the command completer."""
        self.completer = completer
        if self.prompt_session:
            self.prompt_session.completer = completer
    
    def set_app(self, app) -> None:
        """Set the console app reference."""
        self.app = app
        if self.use_panes and self.app:
            self._setup_panes()
    
    def _setup_panes(self) -> None:
        """Setup the panes interface if available."""
        if not self.use_panes or not self.app:
            return
        
        try:
            from .panes import ConsolePanes
            self.panes = ConsolePanes(self.app, self)
            if self.panes.is_available():
                self.panes.start()
                log("INFO", "ui", "panes_started")
            else:
                log("WARN", "ui", "panes_not_available")
                self.use_panes = False
        except Exception as e:
            log("ERROR", "ui", "panes_setup_failed", error=str(e))
            self.use_panes = False
    
    def read_command(self) -> str:
        """Read a command from the user."""
        # Use panes if available and running
        if self.panes and self.panes.is_running():
            return self.panes.read_command()
        
        # Fallback to prompt-toolkit or basic input
        try:
            if self.prompt_session:
                return self.prompt_session.prompt("ateam> ").strip()
            else:
                # Fallback to basic input
                return input("ateam> ").strip()
        except KeyboardInterrupt:
            return ""
        except EOFError:
            raise
        except Exception as e:
            log("ERROR", "ui", "read_command_error", error=str(e))
            return ""
    
    def input(self, prompt: str) -> str:
        """Read input with a custom prompt."""
        try:
            if self.prompt_session:
                return self.prompt_session.prompt(prompt).strip()
            else:
                return input(prompt).strip()
        except KeyboardInterrupt:
            return ""
        except EOFError:
            raise
        except Exception as e:
            log("ERROR", "ui", "input_error", error=str(e))
            return ""
    
    def notify(self, message: str, level: str = "info") -> None:
        """Display a notification message."""
        # Use panes if available
        if self.panes and self.panes.is_running():
            self.panes.notify(message, level)
            return
        
        # Fallback to basic output
        prefix_map = {
            "info": "[INFO]",
            "warn": "[WARN]", 
            "error": "[ERROR]",
            "success": "[OK]"
        }
        prefix = prefix_map.get(level, "[INFO]")
        print(f"{prefix} {message}")
    
    def print_error(self, message: str) -> None:
        """Print an error message."""
        self.notify(message, "error")
    
    def print_help(self) -> None:
        """Print help information."""
        help_text = """
ATeam Console - Available Commands:
===================================

Navigation:
  /ps                    - List running agents
  /attach <agent>        - Attach to an agent
  /detach                - Detach from current agent
  /quit                  - Exit console

Agent Interaction:
  /input <text>          - Send input to agent
  /ctx                   - Show context usage
  /who                   - Show ownership status

System Management:
  /sys show              - Show system prompt
  /reloadsysprompt       - Reload system prompt
  # <text>               - Append to prompt overlay

Knowledge Base:
  /kb add --scope <s> <path>  - Add documents to KB
  /kb search --scope <s> <q>  - Search KB
  /kb copy-from <agent> --ids <ids>  - Copy from agent

Agent Management:
  /agent new             - Create new agent
  /offload               - Offload to new agent
  /clearhistory          - Clear conversation history

UI:
  /ui panes on|off       - Toggle panes UI
  F1                     - Show this help
  F2                     - Toggle panes mode
  TAB                    - Command completion
"""
        print(help_text)
        
        # Only wait for input if not in a test environment
        try:
            import sys
            if hasattr(sys, '_called_main') and not sys._called_main:
                # We're in a test environment, don't wait for input
                return
            input("Press any key to continue...")
        except (KeyboardInterrupt, EOFError, OSError):
            # Handle cases where input is not available
            pass
    
    def show_takeover_banner(self, agent_id: str, new_session: str, grace_timeout: int) -> None:
        """Show a sticky takeover warning banner."""
        self._takeover_banner_active = True
        
        banner_text = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           ⚠️  OWNERSHIP LOST ⚠️                              ║
║                                                                              ║
║  Agent {agent_id} has been taken over by another console.                   ║
║  You are now in read-only mode.                                             ║
║  New session: {new_session[:8]}...                                           ║
║  Grace timeout: {grace_timeout}s                                             ║
║                                                                              ║
║  Use /detach to disconnect or wait for the other console to release.       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        print(banner_text)
    
    def hide_takeover_banner(self) -> None:
        """Hide the takeover banner."""
        self._takeover_banner_active = False
    
    def show_read_only_banner(self, agent_id: str) -> None:
        """Show read-only mode banner."""
        self._read_only_banner_active = True
        
        banner_text = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                              📖 READ-ONLY MODE 📖                           ║
║                                                                              ║
║  Agent {agent_id} is owned by another console.                              ║
║  You can view output but cannot send commands.                              ║
║                                                                              ║
║  Use /detach to disconnect or /attach --takeover to force takeover.         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        print(banner_text)
    
    def hide_read_only_banner(self) -> None:
        """Hide the read-only banner."""
        self._read_only_banner_active = False
    
    def is_takeover_banner_active(self) -> bool:
        """Check if takeover banner is active."""
        return self._takeover_banner_active
    
    def is_read_only_banner_active(self) -> bool:
        """Check if read-only banner is active."""
        return self._read_only_banner_active
    
    def print_output(self, text: str, prefix: str = "") -> None:
        """Print output text."""
        if prefix:
            print(f"{prefix} {text}")
        else:
            print(text)
    
    def print_agents_list(self, agents: List[dict]) -> None:
        """Print a list of agents."""
        if not agents:
            print("No agents found.")
            return
        
        print("\nAvailable Agents:")
        print("=================")
        
        for agent in agents:
            status = agent.get("state", "unknown")
            model = agent.get("model", "unknown")
            cwd = agent.get("cwd", "unknown")
            
            print(f"  {agent['id']}")
            print(f"    Status: {status}")
            print(f"    Model: {model}")
            print(f"    CWD: {cwd}")
            print()
    
    def print_session_status(self, session_info: dict) -> None:
        """Print current session status."""
        print("\nCurrent Session:")
        print("================")
        print(f"Agent: {session_info.get('agent_id', 'none')}")
        print(f"Status: {session_info.get('status', 'unknown')}")
        print(f"Model: {session_info.get('model', 'unknown')}")
        print(f"CWD: {session_info.get('cwd', 'unknown')}")
        print(f"Context: {session_info.get('ctx_pct', 0):.1f}%")
        print()
    
    def clear_screen(self) -> None:
        """Clear the screen."""
        print("\033[2J\033[H", end="")
    
    def is_tty(self) -> bool:
        """Check if running in a TTY."""
        return sys.stdin.isatty()
    
    def get_terminal_size(self) -> tuple[int, int]:
        """Get terminal size (columns, rows)."""
        try:
            import shutil
            return shutil.get_terminal_size()
        except:
            return (80, 24)
