"""
Console Panes UI

Rich/Textual-based pane interface for the console with fallback to plain mode.
"""

import asyncio
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.live import Live
    from rich.prompt import Prompt
    from rich.align import Align
    from rich.columns import Columns
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from ..util.logging import log


class ConsolePanes:
    """Rich/Textual-based pane interface for the console."""
    
    def __init__(self, app, ui):
        self.app = app
        self.ui = ui
        self.console = Console() if RICH_AVAILABLE else None
        self.layout = None
        self.live_display = None
        self._running = False
        self._agents = []
        self._tail_events = []
        self._output_buffer = []
        self._max_output_lines = 100
        self._max_tail_events = 50
        
        if RICH_AVAILABLE:
            self._setup_layout()
    
    def _setup_layout(self) -> None:
        """Setup the Rich layout with panes."""
        self.layout = Layout()
        
        # Create the main layout
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="input", size=3)
        )
        
        # Split the main area into left, center, and right panes
        self.layout["main"].split_row(
            Layout(name="left", ratio=1, minimum_size=20),
            Layout(name="center", ratio=2),
            Layout(name="right", ratio=1, minimum_size=20)
        )
        
        # Setup the panes
        self._setup_header()
        self._setup_left_pane()
        self._setup_center_pane()
        self._setup_right_pane()
        self._setup_input_pane()
    
    def _setup_header(self) -> None:
        """Setup the header pane."""
        header_text = Text("ATeam Console", style="bold blue")
        header_text.append(" | Press F1 for help, F2 to toggle panes", style="dim")
        
        self.layout["header"].update(
            Panel(
                Align.center(header_text),
                border_style="blue",
                box=box.ROUNDED
            )
        )
    
    def _setup_left_pane(self) -> None:
        """Setup the left pane (agent list)."""
        table = Table(title="Agents", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("State", style="green")
        table.add_column("Model", style="yellow")
        
        # Add some sample data for now
        table.add_row("test/agent1", "running", "gpt-4")
        table.add_row("test/agent2", "idle", "gpt-3.5")
        
        self.layout["left"].update(
            Panel(
                table,
                title="[bold cyan]Agents[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED
            )
        )
    
    def _setup_center_pane(self) -> None:
        """Setup the center pane (main output)."""
        output_text = Text("Welcome to ATeam Console!\n")
        output_text.append("Use /ps to list agents, /attach <agent_id> to connect.\n", style="dim")
        output_text.append("Press F1 for help.\n", style="dim")
        
        self.layout["center"].update(
            Panel(
                output_text,
                title="[bold green]Output[/bold green]",
                border_style="green",
                box=box.ROUNDED
            )
        )
    
    def _setup_right_pane(self) -> None:
        """Setup the right pane (tail events)."""
        table = Table(title="Tail Events", show_header=True, header_style="bold red")
        table.add_column("Time", style="dim")
        table.add_column("Event", style="red")
        
        # Add some sample data for now
        table.add_row("12:34:56", "task.start")
        table.add_row("12:34:57", "token")
        
        self.layout["right"].update(
            Panel(
                table,
                title="[bold red]Tail Events[/bold red]",
                border_style="red",
                box=box.ROUNDED
            )
        )
    
    def _setup_input_pane(self) -> None:
        """Setup the input pane."""
        input_text = Text("ateam> ", style="bold white")
        input_text.append("Type your command here...", style="dim")
        
        self.layout["input"].update(
            Panel(
                input_text,
                title="[bold white]Input[/bold white]",
                border_style="white",
                box=box.ROUNDED
            )
        )
    
    def start(self) -> None:
        """Start the panes interface."""
        if not RICH_AVAILABLE:
            self.ui.notify("Rich not available, falling back to plain mode", "warn")
            return
        
        try:
            self._running = True
            self.live_display = Live(
                self.layout,
                console=self.console,
                refresh_per_second=4,
                screen=True
            )
            self.live_display.start()
            log("INFO", "panes", "started")
        except Exception as e:
            log("ERROR", "panes", "start_failed", error=str(e))
            self.ui.notify(f"Failed to start panes: {e}", "error")
            self._running = False
    
    def stop(self) -> None:
        """Stop the panes interface."""
        if self.live_display:
            self.live_display.stop()
            self._running = False
            log("INFO", "panes", "stopped")
    
    def update_agents(self, agents: List[Dict[str, Any]]) -> None:
        """Update the agents list in the left pane."""
        if not RICH_AVAILABLE or not self._running:
            return
        
        self._agents = agents
        table = Table(title="Agents", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("State", style="green")
        table.add_column("Model", style="yellow")
        
        for agent in agents:
            state_style = "green" if agent.get("state") == "running" else "yellow"
            table.add_row(
                agent.get("id", "unknown"),
                agent.get("state", "unknown"),
                agent.get("model", "unknown"),
                style=state_style
            )
        
        self.layout["left"].update(
            Panel(
                table,
                title="[bold cyan]Agents[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED
            )
        )
    
    def add_output(self, text: str, style: str = "white") -> None:
        """Add output to the center pane."""
        if not RICH_AVAILABLE or not self._running:
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        output_line = f"[{timestamp}] {text}"
        self._output_buffer.append((output_line, style))
        
        # Keep only the last N lines
        if len(self._output_buffer) > self._max_output_lines:
            self._output_buffer = self._output_buffer[-self._max_output_lines:]
        
        # Update the center pane
        output_text = Text()
        for line, line_style in self._output_buffer:
            output_text.append(line + "\n", style=line_style)
        
        self.layout["center"].update(
            Panel(
                output_text,
                title="[bold green]Output[/bold green]",
                border_style="green",
                box=box.ROUNDED
            )
        )
    
    def add_tail_event(self, event: Dict[str, Any]) -> None:
        """Add a tail event to the right pane."""
        if not RICH_AVAILABLE or not self._running:
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        event_type = event.get("type", "unknown")
        
        self._tail_events.append((timestamp, event_type))
        
        # Keep only the last N events
        if len(self._tail_events) > self._max_tail_events:
            self._tail_events = self._tail_events[-self._max_tail_events:]
        
        # Update the right pane
        table = Table(title="Tail Events", show_header=True, header_style="bold red")
        table.add_column("Time", style="dim")
        table.add_column("Event", style="red")
        
        for ts, evt in self._tail_events:
            table.add_row(ts, evt)
        
        self.layout["right"].update(
            Panel(
                table,
                title="[bold red]Tail Events[/bold red]",
                border_style="red",
                box=box.ROUNDED
            )
        )
    
    def read_command(self) -> str:
        """Read a command from the user."""
        if not RICH_AVAILABLE or not self._running:
            # Fallback to the regular UI
            return self.ui.read_command()
        
        try:
            # Update input pane to show prompt
            input_text = Text("ateam> ", style="bold white")
            self.layout["input"].update(
                Panel(
                    input_text,
                    title="[bold white]Input[/bold white]",
                    border_style="white",
                    box=box.ROUNDED
                )
            )
            
            # Read input using Rich prompt
            command = Prompt.ask("ateam>", console=self.console)
            return command.strip()
        except KeyboardInterrupt:
            return ""
        except EOFError:
            raise
        except Exception as e:
            log("ERROR", "panes", "read_command_error", error=str(e))
            return ""
    
    def notify(self, message: str, level: str = "info") -> None:
        """Display a notification message."""
        if not RICH_AVAILABLE or not self._running:
            # Fallback to the regular UI
            self.ui.notify(message, level)
            return
        
        # Add to output buffer
        style_map = {
            "info": "blue",
            "warn": "yellow", 
            "error": "red",
            "success": "green"
        }
        style = style_map.get(level, "white")
        self.add_output(f"[{level.upper()}] {message}", style)
    
    def print_error(self, message: str) -> None:
        """Print an error message."""
        self.notify(message, "error")
    
    def print_help(self) -> None:
        """Print help information."""
        if not RICH_AVAILABLE or not self._running:
            # Fallback to the regular UI
            self.ui.print_help()
            return
        
        help_text = Text("ATeam Console Commands:\n\n", style="bold blue")
        help_text.append("/ps", style="cyan")
        help_text.append(" - List agents\n", style="white")
        help_text.append("/attach <agent_id>", style="cyan")
        help_text.append(" - Attach to agent\n", style="white")
        help_text.append("/detach", style="cyan")
        help_text.append(" - Detach from current agent\n", style="white")
        help_text.append("/input <message>", style="cyan")
        help_text.append(" - Send input to agent\n", style="white")
        help_text.append("/status", style="cyan")
        help_text.append(" - Show agent status\n", style="white")
        help_text.append("/help", style="cyan")
        help_text.append(" - Show this help\n", style="white")
        help_text.append("/quit", style="cyan")
        help_text.append(" - Exit console\n", style="white")
        help_text.append("/ui panes on|off", style="cyan")
        help_text.append(" - Toggle panes mode\n", style="white")
        
        self.add_output(help_text, "blue")
    
    def is_available(self) -> bool:
        """Check if Rich is available for panes."""
        return RICH_AVAILABLE
    
    def is_running(self) -> bool:
        """Check if panes are currently running."""
        return self._running
