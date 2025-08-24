"""
Path sandboxing and security validation for file system operations.

Provides security controls to prevent agents from accessing files outside
of their designated sandbox directories.
"""

import os
import stat
from pathlib import Path
from typing import List, Optional, Set, Union
from ..util.types import Result, ErrorInfo
from ..util.logging import log


class PathSandbox:
    """Path sandboxing for file system operations."""
    
    def __init__(self, allowed_paths: List[str], denied_paths: Optional[List[str]] = None, 
                 allow_temp: bool = True, allow_home: bool = False) -> None:
        """
        Initialize path sandbox.
        
        Args:
            allowed_paths: List of allowed directory paths (absolute)
            denied_paths: List of explicitly denied paths (takes precedence)
            allow_temp: Allow access to system temp directory
            allow_home: Allow access to user home directory
        """
        self.allowed_paths = [Path(p).resolve() for p in allowed_paths]
        self.denied_paths = [Path(p).resolve() for p in (denied_paths or [])]
        self.allow_temp = allow_temp
        self.allow_home = allow_home
        
        # Add temp directory if allowed
        if allow_temp:
            import tempfile
            self.allowed_paths.append(Path(tempfile.gettempdir()).resolve())
        
        # Add home directory if allowed
        if allow_home:
            self.allowed_paths.append(Path.home().resolve())
        
        log("INFO", "sandbox", "initialized", 
            allowed_count=len(self.allowed_paths),
            denied_count=len(self.denied_paths),
            allow_temp=allow_temp,
            allow_home=allow_home)
    
    def validate_path(self, path: Union[str, Path], operation: str = "access") -> Result[Path]:
        """
        Validate that a path is allowed for the given operation.
        
        Args:
            path: Path to validate
            operation: Type of operation (access, read, write, execute)
            
        Returns:
            Result with resolved path if allowed, error if denied
        """
        try:
            # Resolve the path to handle symlinks and relative paths
            resolved_path = Path(path).resolve()
            
            # Check if path is explicitly denied
            for denied in self.denied_paths:
                if self._is_path_under(resolved_path, denied):
                    return Result(ok=False, error=ErrorInfo(
                        "sandbox.path_denied",
                        f"Path {resolved_path} is explicitly denied"
                    ))
            
            # Check if path is under any allowed directory
            for allowed in self.allowed_paths:
                if self._is_path_under(resolved_path, allowed):
                    log("DEBUG", "sandbox", "path_allowed", 
                        path=str(resolved_path), operation=operation, 
                        allowed_root=str(allowed))
                    return Result(ok=True, value=resolved_path)
            
            # Path is not under any allowed directory
            return Result(ok=False, error=ErrorInfo(
                "sandbox.path_not_allowed",
                f"Path {resolved_path} is not under any allowed directory"
            ))
            
        except Exception as e:
            return Result(ok=False, error=ErrorInfo(
                "sandbox.validation_error",
                f"Error validating path {path}: {e}"
            ))
    
    def validate_file_operation(self, path: Union[str, Path], operation: str, 
                              create_dirs: bool = False) -> Result[Path]:
        """
        Validate a file operation with additional checks.
        
        Args:
            path: File path to validate
            operation: Operation type (read, write, append, delete, execute)
            create_dirs: Whether to allow creating parent directories
            
        Returns:
            Result with resolved path if allowed
        """
        # First validate basic path access
        path_result = self.validate_path(path, operation)
        if not path_result.ok:
            return path_result
        
        resolved_path = path_result.value
        
        try:
            # Additional checks based on operation
            if operation in ["write", "append", "delete"]:
                # Check if we can write to parent directory
                parent = resolved_path.parent
                if not parent.exists():
                    if create_dirs:
                        # Validate parent directory creation
                        parent_result = self.validate_path(parent, "write")
                        if not parent_result.ok:
                            return Result(ok=False, error=ErrorInfo(
                                "sandbox.parent_dir_denied",
                                f"Cannot create parent directory {parent}: {parent_result.error.message}"
                            ))
                    else:
                        return Result(ok=False, error=ErrorInfo(
                            "sandbox.parent_dir_missing",
                            f"Parent directory {parent} does not exist"
                        ))
                elif not os.access(parent, os.W_OK):
                    return Result(ok=False, error=ErrorInfo(
                        "sandbox.parent_dir_readonly",
                        f"Parent directory {parent} is not writable"
                    ))
            
            # Check for dangerous file types
            if operation in ["write", "append"] and self._is_dangerous_file(resolved_path):
                return Result(ok=False, error=ErrorInfo(
                    "sandbox.dangerous_file_type",
                    f"File type of {resolved_path} is potentially dangerous"
                ))
            
            log("DEBUG", "sandbox", "file_operation_allowed",
                path=str(resolved_path), operation=operation)
            return Result(ok=True, value=resolved_path)
            
        except Exception as e:
            return Result(ok=False, error=ErrorInfo(
                "sandbox.file_operation_error",
                f"Error validating file operation {operation} on {path}: {e}"
            ))
    
    def _is_path_under(self, path: Path, root: Path) -> bool:
        """Check if path is under root directory."""
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False
    
    def _is_dangerous_file(self, path: Path) -> bool:
        """Check if file type is potentially dangerous."""
        dangerous_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.scr', '.pif',
            '.sh', '.bash', '.zsh', '.fish', '.ps1', '.psm1',
            '.vbs', '.vbe', '.js', '.jse', '.wsf', '.wsh',
            '.msi', '.msp', '.mst', '.jar', '.app', '.deb', '.rpm'
        }
        
        return path.suffix.lower() in dangerous_extensions
    
    def get_safe_temp_dir(self) -> Result[Path]:
        """Get a safe temporary directory within the sandbox."""
        import tempfile
        
        temp_dir = Path(tempfile.gettempdir()).resolve()
        
        # Validate temp directory access
        temp_result = self.validate_path(temp_dir, "write")
        if not temp_result.ok:
            return Result(ok=False, error=ErrorInfo(
                "sandbox.temp_dir_denied",
                f"Temporary directory {temp_dir} is not accessible"
            ))
        
        return Result(ok=True, value=temp_dir)
    
    def create_sandbox_subdir(self, name: str, base_path: Optional[Union[str, Path]] = None) -> Result[Path]:
        """
        Create a subdirectory within the sandbox for agent use.
        
        Args:
            name: Name of the subdirectory
            base_path: Base path (must be within sandbox), uses first allowed path if None
            
        Returns:
            Result with created directory path
        """
        try:
            if base_path:
                base = Path(base_path).resolve()
                base_result = self.validate_path(base, "write")
                if not base_result.ok:
                    return base_result
            else:
                if not self.allowed_paths:
                    return Result(ok=False, error=ErrorInfo(
                        "sandbox.no_allowed_paths",
                        "No allowed paths configured for sandbox"
                    ))
                base = self.allowed_paths[0]
            
            # Create subdirectory
            subdir = base / name
            subdir_result = self.validate_path(subdir, "write")
            if not subdir_result.ok:
                return subdir_result
            
            # Create the directory if it doesn't exist
            subdir.mkdir(parents=True, exist_ok=True)
            
            log("INFO", "sandbox", "subdir_created", path=str(subdir))
            return Result(ok=True, value=subdir)
            
        except Exception as e:
            return Result(ok=False, error=ErrorInfo(
                "sandbox.subdir_creation_error",
                f"Error creating sandbox subdirectory {name}: {e}"
            ))


class CommandSandbox:
    """Sandbox for command execution with path and command restrictions."""
    
    def __init__(self, path_sandbox: PathSandbox, allowed_commands: Optional[Set[str]] = None,
                 denied_commands: Optional[Set[str]] = None, allow_shell: bool = False) -> None:
        """
        Initialize command sandbox.
        
        Args:
            path_sandbox: PathSandbox instance for file access control
            allowed_commands: Set of allowed command names (if None, all are allowed)
            denied_commands: Set of explicitly denied commands
            allow_shell: Allow shell command execution
        """
        self.path_sandbox = path_sandbox
        self.allowed_commands = allowed_commands
        self.denied_commands = denied_commands or set()
        self.allow_shell = allow_shell
        
        log("INFO", "command_sandbox", "initialized",
            allowed_commands_count=len(allowed_commands) if allowed_commands else "all",
            denied_commands_count=len(self.denied_commands),
            allow_shell=allow_shell)
    
    def validate_command(self, command: List[str], cwd: Optional[Union[str, Path]] = None) -> Result[dict]:
        """
        Validate a command execution request.
        
        Args:
            command: Command and arguments as list
            cwd: Working directory for command execution
            
        Returns:
            Result with validation info if allowed
        """
        try:
            if not command:
                return Result(ok=False, error=ErrorInfo(
                    "sandbox.empty_command",
                    "Command cannot be empty"
                ))
            
            cmd_name = Path(command[0]).name
            
            # Check if command is explicitly denied
            if cmd_name in self.denied_commands:
                return Result(ok=False, error=ErrorInfo(
                    "sandbox.command_denied",
                    f"Command {cmd_name} is explicitly denied"
                ))
            
            # Check if command is in allowed list (if specified)
            if self.allowed_commands and cmd_name not in self.allowed_commands:
                return Result(ok=False, error=ErrorInfo(
                    "sandbox.command_not_allowed",
                    f"Command {cmd_name} is not in allowed commands list"
                ))
            
            # Check for shell commands if not allowed
            if not self.allow_shell and self._is_shell_command(cmd_name):
                return Result(ok=False, error=ErrorInfo(
                    "sandbox.shell_command_denied",
                    f"Shell command {cmd_name} is not allowed"
                ))
            
            # Validate working directory if specified
            validated_cwd = None
            if cwd:
                cwd_result = self.path_sandbox.validate_path(cwd, "access")
                if not cwd_result.ok:
                    return Result(ok=False, error=ErrorInfo(
                        "sandbox.cwd_denied",
                        f"Working directory {cwd} is not allowed: {cwd_result.error.message}"
                    ))
                validated_cwd = cwd_result.value
            
            # Validate file arguments (basic check for paths)
            validated_args = []
            for arg in command[1:]:
                # If argument looks like a path, validate it
                if self._looks_like_path(arg):
                    # For now, just validate read access - specific tools should do more specific validation
                    arg_result = self.path_sandbox.validate_path(arg, "read")
                    if not arg_result.ok:
                        log("WARN", "command_sandbox", "arg_path_denied",
                            command=cmd_name, arg=arg, error=arg_result.error.message)
                        # Don't fail here - let the specific tool handle path validation
                validated_args.append(arg)
            
            log("DEBUG", "command_sandbox", "command_allowed",
                command=cmd_name, args_count=len(validated_args))
            
            return Result(ok=True, value={
                "command": command[0],
                "args": validated_args,
                "cwd": validated_cwd
            })
            
        except Exception as e:
            return Result(ok=False, error=ErrorInfo(
                "sandbox.command_validation_error",
                f"Error validating command {command}: {e}"
            ))
    
    def _is_shell_command(self, cmd_name: str) -> bool:
        """Check if command is a shell command."""
        shell_commands = {
            'sh', 'bash', 'zsh', 'fish', 'csh', 'tcsh', 'ksh',
            'cmd', 'powershell', 'pwsh', 'command', 'eval'
        }
        return cmd_name.lower() in shell_commands
    
    def _looks_like_path(self, arg: str) -> bool:
        """Check if argument looks like a file path."""
        # Simple heuristic - contains path separators or file extensions
        return ('/' in arg or '\\' in arg or 
                ('.' in arg and not arg.startswith('-')))
