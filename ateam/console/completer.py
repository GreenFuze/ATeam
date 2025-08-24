"""Console command completion with commands, agent IDs, and path completion."""

import os
from typing import List, Optional

from prompt_toolkit.completion import Completion

from ..util.logging import log


class ConsoleCompleter:
    """Console completer with commands, agent IDs, and path completion."""
    
    def __init__(self, app) -> None:
        self.app = app
        
        # Command definitions with descriptions
        self.commands = {
            # Session management
            "/ps": "List all agents",
            "/attach": "Attach to an agent",
            "/detach": "Detach from an agent",
            "/status": "Show current status",
            
            # Agent interaction
            "/input": "Send input to current agent",
            "/ctx": "Show context/memory stats",
            "/sys": "System prompt commands",
            "/reloadsysprompt": "Reload system prompt",
            
            # Knowledge base
            "/kb": "Knowledge base commands",
            
            # Agent management
            "/agent": "Agent management commands",
            "/offload": "Offload task to new agent",
            
            # System
            "/help": "Show help",
            "/quit": "Exit console",
            "/ui": "UI commands",
        }
        
        # Subcommands
        self.subcommands = {
            "/sys": ["show", "edit"],
            "/kb": ["add", "search", "copy-from"],
            "/ui": ["toggle", "panes"],
            "/agent": ["new", "list", "delete"],
        }
    
    def get_completions(self, document, complete_event):
        """Get completions for the current document."""
        text = document.text_before_cursor
        words = text.split()
        
        if not words:
            # Complete with all commands
            for cmd, desc in self.commands.items():
                yield Completion(cmd, start_position=0, display=cmd, display_meta=desc)
            # Also suggest overlay line command
            yield Completion("# ", start_position=0, display="# ", display_meta="Add overlay line")
            return
        
        # Handle overlay line command (# <text>)
        if len(words) == 1 and words[0] == "#":
            # Suggest some common overlay lines
            common_overlays = [
                "Prefer concise step-by-step plans.",
                "Always explain your reasoning.",
                "Use markdown formatting for responses.",
                "Focus on practical solutions.",
                "Ask clarifying questions when needed."
            ]
            for overlay in common_overlays:
                yield Completion(
                    overlay,
                    start_position=0,
                    display=overlay,
                    display_meta="Overlay line"
                )
            return
        
        current_word = words[-1]
        
        # Handle command completion
        if len(words) == 1:
            # First word - complete commands
            for cmd, desc in self.commands.items():
                if cmd.startswith(current_word):
                    yield Completion(
                        cmd, 
                        start_position=-len(current_word), 
                        display=cmd, 
                        display_meta=desc
                    )
            return
        
        # Handle subcommand completion
        if len(words) == 2 and words[0] in self.subcommands:
            base_cmd = words[0]
            subcommands = self.subcommands[base_cmd]
            
            for subcmd in subcommands:
                if subcmd.startswith(current_word):
                    yield Completion(
                        subcmd,
                        start_position=-len(current_word),
                        display=subcmd
                    )
            return
        
        # Handle agent ID completion for /attach, /detach, and /agent delete
        if len(words) == 2 and words[0] in ["/attach", "/detach"]:
            agent_ids = self._get_available_agent_ids()
            for agent_id in agent_ids:
                if agent_id.startswith(current_word):
                    yield Completion(
                        agent_id,
                        start_position=-len(current_word),
                        display=agent_id
                    )
            return
        
        # Handle agent ID completion for /agent delete
        if len(words) == 3 and words[0] == "/agent" and words[1] == "delete":
            agent_ids = self._get_available_agent_ids()
            for agent_id in agent_ids:
                if agent_id.startswith(current_word):
                    yield Completion(
                        agent_id,
                        start_position=-len(current_word),
                        display=agent_id
                    )
            return
        
        # Handle path completion for file-based commands
        if self._is_path_completion_context(words):
            yield from self._complete_paths(current_word)
            return
    
    def _get_available_agent_ids(self) -> List[str]:
        """Get available agent IDs from registry."""
        try:
            if self.app.registry:
                # This would need to be async, but completer is sync
                # For now, return empty list - will be enhanced later
                return []
        except:
            pass
        return []
    
    def _is_path_completion_context(self, words: List[str]) -> bool:
        """Check if we're in a path completion context."""
        if len(words) < 2:
            return False
        
        # Commands that expect file paths
        path_commands = [
            "/kb", "add", "/input", 
            "--cwd", "--path", "--file", "--config",
            "add", "copy", "move", "cp", "mv"
        ]
        
        # Check if we're after a path command
        for i, word in enumerate(words[:-1]):
            if word in path_commands:
                return True
            
            # Check for commands that expect paths as arguments
            if word in ["/kb", "add"] and i + 1 < len(words):
                # After /kb add, expect paths
                return True
        
        return False
    
    def _complete_paths(self, current_word: str):
        """Complete file paths with cross-platform support."""
        try:
            # Handle quoted paths
            original_word = current_word
            quoted = False
            if (current_word.startswith('"') and current_word.endswith('"')) or \
               (current_word.startswith("'") and current_word.endswith("'")):
                quoted = True
                current_word = current_word[1:-1]
            
            # Handle tilde expansion
            if current_word.startswith('~'):
                try:
                    home = os.path.expanduser('~')
                    current_word = current_word.replace('~', home, 1)
                except:
                    pass
            
            # Handle WSL paths (/mnt/c/...)
            if current_word.startswith('/mnt/') and len(current_word) > 5:
                # Convert WSL path to Windows path if on Windows
                if os.name == 'nt':
                    wsl_parts = current_word.split('/')
                    if len(wsl_parts) >= 4 and wsl_parts[1] == 'mnt':
                        drive_letter = wsl_parts[2].upper()
                        rest_path = '/'.join(wsl_parts[3:])
                        current_word = f"{drive_letter}:\\{rest_path.replace('/', '\\')}"
            
            # Handle Windows drive letters
            if os.name == 'nt' and len(current_word) >= 2 and current_word[1] == ':':
                # Ensure proper Windows path format
                if len(current_word) == 2:
                    current_word += "\\"
                elif current_word[2] != '\\':
                    current_word = current_word[:2] + "\\" + current_word[2:]
            
            # Handle UNC paths (\\server\share)
            if current_word.startswith('\\\\'):
                # Ensure proper UNC path format
                if current_word.count('\\') < 4:
                    current_word += "\\"
            
            # Get the directory to list
            if os.path.isdir(current_word):
                directory = current_word
                prefix = ""
            else:
                directory = os.path.dirname(current_word) or "."
                prefix = os.path.basename(current_word)
            
            if not os.path.exists(directory):
                return
            
            # List directory contents
            try:
                items = os.listdir(directory)
                
                for item in items:
                    if item.startswith(prefix):
                        full_path = os.path.join(directory, item)
                        
                        # Add trailing slash for directories
                        if os.path.isdir(full_path):
                            display = item + ("\\" if os.name == 'nt' else "/")
                        else:
                            display = item
                        
                        # Handle spaces in filenames
                        if ' ' in item and not quoted:
                            display = f'"{display}"'
                        
                        # Calculate start position
                        if prefix:
                            start_pos = -len(prefix)
                        else:
                            start_pos = 0
                        
                        # Handle quoted paths
                        if quoted:
                            start_pos -= 1  # Account for opening quote
                        
                        yield Completion(
                            item,
                            start_position=start_pos,
                            display=display
                        )
                        
            except PermissionError:
                pass
            except OSError:
                pass
                
        except Exception as e:
            log("ERROR", "completer", "path_completion_error", error=str(e))
    
    def update_agent_ids(self, agent_ids: List[str]) -> None:
        """Update the list of available agent IDs."""
        # This would be called when agent list changes
        pass
