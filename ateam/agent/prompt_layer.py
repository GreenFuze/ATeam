import os
from typing import Optional
from ..util.types import Result, ErrorInfo
from ..util.logging import log

class PromptLayer:
    def __init__(self, base_path: str, overlay_path: str) -> None:
        self.base_path = base_path
        self.overlay_path = overlay_path
        self._base_content: str = ""
        self._overlay_content: str = ""
        self._overlay_lines: list[str] = []
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load base and overlay content from disk."""
        try:
            # Load base content
            if os.path.exists(self.base_path):
                with open(self.base_path, 'r', encoding='utf-8') as f:
                    self._base_content = f.read()
            else:
                # Create default base content
                self._base_content = "# System Prompt\n\nYou are a helpful AI assistant."
                self._save_base()
            
            # Load overlay content
            if os.path.exists(self.overlay_path):
                with open(self.overlay_path, 'r', encoding='utf-8') as f:
                    self._overlay_content = f.read()
                    self._overlay_lines = [line.strip() for line in self._overlay_content.split('\n') if line.strip()]
            else:
                self._overlay_content = ""
                self._overlay_lines = []
                
            log("DEBUG", "prompt", "loaded_from_disk", base_path=self.base_path, overlay_path=self.overlay_path)
            
        except Exception as e:
            log("ERROR", "prompt", "load_failed", error=str(e))

    def _save_base(self) -> None:
        """Save base content to disk."""
        try:
            os.makedirs(os.path.dirname(self.base_path), exist_ok=True)
            with open(self.base_path, 'w', encoding='utf-8') as f:
                f.write(self._base_content)
        except Exception as e:
            log("ERROR", "prompt", "save_base_failed", error=str(e))

    def _save_overlay(self) -> None:
        """Save overlay content to disk."""
        try:
            os.makedirs(os.path.dirname(self.overlay_path), exist_ok=True)
            with open(self.overlay_path, 'w', encoding='utf-8') as f:
                f.write(self._overlay_content)
        except Exception as e:
            log("ERROR", "prompt", "save_overlay_failed", error=str(e))

    def effective(self) -> str:
        """Get the effective system prompt (base + overlay)."""
        if not self._overlay_lines:
            return self._base_content
        
        overlay_text = '\n'.join(self._overlay_lines)
        return f"{self._base_content}\n\n# Overlay\n{overlay_text}"

    def reload_from_disk(self) -> Result[None]:
        """Reload base and overlay from disk."""
        try:
            self._load_from_disk()
            log("INFO", "prompt", "reloaded_from_disk")
            return Result(ok=True)
        except Exception as e:
            log("ERROR", "prompt", "reload_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("prompt.reload_failed", str(e)))

    def append_overlay(self, line: str) -> Result[None]:
        """Append a line to the overlay."""
        try:
            line = line.strip()
            if not line:
                return Result(ok=False, error=ErrorInfo("prompt.empty_line", "Cannot append empty line"))
            
            self._overlay_lines.append(line)
            self._overlay_content = '\n'.join(self._overlay_lines)
            self._save_overlay()
            
            log("INFO", "prompt", "overlay_appended", line=line)
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "prompt", "append_overlay_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("prompt.append_overlay_failed", str(e)))

    def set_base(self, text: str) -> Result[None]:
        """Set the base system prompt."""
        try:
            self._base_content = text
            self._save_base()
            
            log("INFO", "prompt", "base_updated")
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "prompt", "set_base_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("prompt.set_base_failed", str(e)))

    def set_overlay(self, text: str) -> Result[None]:
        """Set the overlay content."""
        try:
            self._overlay_content = text
            self._overlay_lines = [line.strip() for line in text.split('\n') if line.strip()]
            self._save_overlay()
            
            log("INFO", "prompt", "overlay_updated")
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "prompt", "set_overlay_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("prompt.set_overlay_failed", str(e)))

    def clear_overlay(self) -> Result[None]:
        """Clear the overlay content."""
        try:
            self._overlay_content = ""
            self._overlay_lines = []
            self._save_overlay()
            
            log("INFO", "prompt", "overlay_cleared")
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "prompt", "clear_overlay_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("prompt.clear_overlay_failed", str(e)))

    def get_base(self) -> str:
        """Get the base content."""
        return self._base_content

    def get_overlay(self) -> str:
        """Get the overlay content."""
        return self._overlay_content

    def get_overlay_lines(self) -> list[str]:
        """Get the overlay lines."""
        return self._overlay_lines.copy()
