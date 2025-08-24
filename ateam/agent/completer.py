from typing import Tuple, List
import os

class AgentCompleter:
    def __init__(self, commands: List[str]) -> None:
        self.commands = commands

    def complete(self, buffer: str, cursor_pos: int) -> Tuple[str, List[str]]:
        """
        Complete the buffer at cursor position.
        Returns (new_buffer, candidates).
        """
        # Simple word-based completion for now
        words = buffer[:cursor_pos].split()
        
        if not words:
            # Complete command
            return buffer, self.commands
        
        current_word = words[-1]
        prefix = current_word.lower()
        
        # If we're completing the first word, it's a command
        if len(words) == 1:
            candidates = [cmd for cmd in self.commands if cmd.startswith(prefix)]
            if candidates:
                # Replace the current word with the first candidate
                new_buffer = buffer[:cursor_pos - len(current_word)] + candidates[0] + buffer[cursor_pos:]
                return new_buffer, candidates
        else:
            # For subsequent words, try path completion
            if prefix.startswith('~'):
                # Handle home directory expansion
                try:
                    home = os.path.expanduser('~')
                    prefix = prefix.replace('~', home, 1)
                except:
                    pass
            
            if os.path.exists(prefix):
                # Directory completion
                try:
                    if os.path.isdir(prefix):
                        items = os.listdir(prefix)
                        candidates = [os.path.join(prefix, item) for item in items]
                    else:
                        # File completion - get parent directory
                        parent = os.path.dirname(prefix)
                        if parent:
                            items = os.listdir(parent)
                            candidates = [os.path.join(parent, item) for item in items if item.startswith(os.path.basename(prefix))]
                        else:
                            candidates = []
                    
                    if candidates:
                        # Find common prefix
                        common_prefix = os.path.commonprefix(candidates)
                        if common_prefix and common_prefix != prefix:
                            new_buffer = buffer[:cursor_pos - len(current_word)] + common_prefix + buffer[cursor_pos:]
                            return new_buffer, candidates
                except:
                    pass
        
        return buffer, []

    def get_completions(self, text: str) -> List[str]:
        """Get all possible completions for the given text."""
        words = text.split()
        
        if not words:
            return self.commands
        
        current_word = words[-1].lower()
        
        if len(words) == 1:
            return [cmd for cmd in self.commands if cmd.startswith(current_word)]
        else:
            # Path completion
            prefix = current_word
            if prefix.startswith('~'):
                try:
                    home = os.path.expanduser('~')
                    prefix = prefix.replace('~', home, 1)
                except:
                    pass
            
            if os.path.exists(prefix):
                try:
                    if os.path.isdir(prefix):
                        items = os.listdir(prefix)
                        return [os.path.join(prefix, item) for item in items]
                    else:
                        parent = os.path.dirname(prefix)
                        if parent:
                            items = os.listdir(parent)
                            return [os.path.join(parent, item) for item in items if item.startswith(os.path.basename(prefix))]
                except:
                    pass
        
        return []
