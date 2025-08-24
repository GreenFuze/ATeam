from pathlib import Path
from typing import List
from ..util.types import Result, ErrorInfo

class ConfigDiscovery:
    def __init__(self, start_cwd: str) -> None:
        self.start_cwd = Path(start_cwd).resolve()

    def discover_stack(self) -> Result[List[str]]:
        """Return ordered list of .ateam dirs from CWD→parents→home (highest→lowest priority)."""
        try:
            stack = []
            
            # Walk up from start_cwd to root, collecting .ateam directories
            current = self.start_cwd
            while current != current.parent:  # Stop at root
                ateam_dir = current / ".ateam"
                if ateam_dir.exists() and ateam_dir.is_dir():
                    stack.append(str(ateam_dir))
                current = current.parent
            
            # Add user home .ateam directory (lowest priority)
            home_ateam = Path.home() / ".ateam"
            if home_ateam.exists() and home_ateam.is_dir():
                stack.append(str(home_ateam))
            
            return Result(ok=True, value=stack)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("discovery.failed", str(e)))
