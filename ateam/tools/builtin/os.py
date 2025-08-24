"""OS execution tool with PTY/ConPTY support and sandbox checks."""

import os
import sys
import asyncio
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path
from ...util.logging import log
from ...util.types import Result, ErrorInfo


def exec(cmd: str, cwd: Optional[str] = None, timeout: Optional[int] = None,
         env: Optional[Dict[str, str]] = None, pty: bool = True) -> Dict[str, Any]:
    """
    Execute a shell command with sandbox checks.
    
    Args:
        cmd: Command to execute
        cwd: Working directory (must be within sandbox)
        timeout: Command timeout in seconds
        env: Environment variables to set
        pty: Use PTY/ConPTY for interactive processes
        
    Returns:
        Dict with "rc", "stdout", "stderr", "duration_ms"
    """
    try:
        # Validate working directory is within sandbox
        if cwd:
            cwd_path = Path(cwd).resolve()
            if not _is_path_safe(cwd_path):
                return {
                    "rc": 1,
                    "stdout": "",
                    "stderr": f"Error: Working directory {cwd} is outside sandbox",
                    "duration_ms": 0
                }
        else:
            cwd = os.getcwd()
        
        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        # Execute command
        if pty and _supports_pty():
            result = _execute_with_pty(cmd, cwd, timeout, process_env)
        else:
            result = _execute_without_pty(cmd, cwd, timeout, process_env)
        
        log("INFO", "tools.os", "exec_completed", 
            cmd=cmd, cwd=cwd, rc=result["rc"], duration_ms=result["duration_ms"])
        
        return result
        
    except Exception as e:
        log("ERROR", "tools.os", "exec_failed", cmd=cmd, error=str(e))
        return {
            "rc": 1,
            "stdout": "",
            "stderr": f"Execution failed: {str(e)}",
            "duration_ms": 0
        }


def _is_path_safe(path: Path) -> bool:
    """Check if path is within the sandbox."""
    # Get the current working directory as sandbox root
    sandbox_root = Path.cwd().resolve()
    
    try:
        # Check if path resolves to within sandbox
        resolved_path = path.resolve()
        return resolved_path.is_relative_to(sandbox_root)
    except (ValueError, RuntimeError):
        # Path is not relative to sandbox
        return False


def _supports_pty() -> bool:
    """Check if PTY/ConPTY is supported on this platform."""
    if sys.platform == "win32":
        try:
            import pywinpty
            return True
        except ImportError:
            return False
    else:
        return True


def _execute_with_pty(cmd: str, cwd: str, timeout: Optional[int], env: Dict[str, str]) -> Dict[str, Any]:
    """Execute command with PTY/ConPTY support."""
    import time
    start_time = time.time()
    
    if sys.platform == "win32":
        return _execute_with_conpty(cmd, cwd, timeout, env)
    else:
        return _execute_with_unix_pty(cmd, cwd, timeout, env)


def _execute_with_conpty(cmd: str, cwd: str, timeout: Optional[int], env: Dict[str, str]) -> Dict[str, Any]:
    """Execute command with Windows ConPTY."""
    try:
        import pywinpty
        
        # Create ConPTY
        pty = pywinpty.PTY(
            cols=80,
            rows=24
        )
        
        # Start process
        process = subprocess.Popen(
            cmd,
            shell=True,
            cwd=cwd,
            env=env,
            stdout=pty.stdout,
            stderr=pty.stderr,
            stdin=pty.stdin
        )
        
        # Read output
        stdout_data = b""
        stderr_data = b""
        
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            return {
                "rc": -1,
                "stdout": stdout_data.decode('utf-8', errors='replace'),
                "stderr": stderr_data.decode('utf-8', errors='replace') + "\nCommand timed out",
                "duration_ms": int((time.time() - start_time) * 1000)
            }
        
        # Read remaining output
        while True:
            try:
                data = pty.read(1024, timeout=0.1)
                if not data:
                    break
                stdout_data += data
            except:
                break
        
        pty.close()
        
        return {
            "rc": process.returncode,
            "stdout": stdout_data.decode('utf-8', errors='replace'),
            "stderr": stderr_data.decode('utf-8', errors='replace'),
            "duration_ms": int((time.time() - start_time) * 1000)
        }
        
    except ImportError:
        # Fallback to non-PTY
        return _execute_without_pty(cmd, cwd, timeout, env)


def _execute_with_unix_pty(cmd: str, cwd: str, timeout: Optional[int], env: Dict[str, str]) -> Dict[str, Any]:
    """Execute command with Unix PTY."""
    import pty
    import time
    start_time = time.time()
    
    # Create PTY
    master_fd, slave_fd = pty.openpty()
    
    # Start process
    process = subprocess.Popen(
        cmd,
        shell=True,
        cwd=cwd,
        env=env,
        stdout=slave_fd,
        stderr=slave_fd,
        stdin=slave_fd,
        close_fds=True
    )
    
    os.close(slave_fd)
    
    # Read output
    output_data = b""
    
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        return {
            "rc": -1,
            "stdout": output_data.decode('utf-8', errors='replace'),
            "stderr": "Command timed out",
            "duration_ms": int((time.time() - start_time) * 1000)
        }
    
    # Read remaining output
    while True:
        try:
            data = os.read(master_fd, 1024)
            if not data:
                break
            output_data += data
        except (OSError, BlockingIOError):
            break
    
    os.close(master_fd)
    
    return {
        "rc": process.returncode,
        "stdout": output_data.decode('utf-8', errors='replace'),
        "stderr": "",
        "duration_ms": int((time.time() - start_time) * 1000)
    }


def _execute_without_pty(cmd: str, cwd: str, timeout: Optional[int], env: Dict[str, str]) -> Dict[str, Any]:
    """Execute command without PTY (fallback)."""
    import time
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            "rc": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_ms": int((time.time() - start_time) * 1000)
        }
        
    except subprocess.TimeoutExpired:
        return {
            "rc": -1,
            "stdout": "",
            "stderr": "Command timed out",
            "duration_ms": int((time.time() - start_time) * 1000)
        }
    except Exception as e:
        return {
            "rc": 1,
            "stdout": "",
            "stderr": f"Execution failed: {str(e)}",
            "duration_ms": int((time.time() - start_time) * 1000)
        }


async def exec_stream(cmd: str, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None,
                     tail_emitter=None) -> Dict[str, Any]:
    """
    Execute a shell command with streaming output and tail event emission.
    
    Args:
        cmd: Command to execute
        cwd: Working directory (must be within sandbox)
        env: Environment variables to set
        tail_emitter: Optional TailEmitter instance for emitting events
        
    Returns:
        Dict with "rc", "stdout", "stderr", "duration_ms"
    """
    import time
    from ..ptyexec import stream_cmd
    
    start_time = time.time()
    stdout_chunks = []
    stderr_chunks = []
    
    try:
        # Validate working directory is within sandbox
        if cwd:
            cwd_path = Path(cwd).resolve()
            if not _is_path_safe(cwd_path):
                error_msg = f"Error: Working directory {cwd} is outside sandbox"
                if tail_emitter:
                    await tail_emitter.emit({
                        "type": "error",
                        "message": error_msg
                    })
                return {
                    "rc": 1,
                    "stdout": "",
                    "stderr": error_msg,
                    "duration_ms": 0
                }
        else:
            cwd = os.getcwd()
        
        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        # Emit start event
        if tail_emitter:
            await tail_emitter.emit({
                "type": "tool.start",
                "tool": "os.exec",
                "cmd": cmd,
                "cwd": cwd
            })
        
        # Stream command output
        async for chunk in stream_cmd(cmd, cwd, process_env):
            stdout_chunks.append(chunk)
            
            # Emit token event for each chunk
            if tail_emitter:
                await tail_emitter.emit({
                    "type": "token",
                    "content": chunk,
                    "tool": "os.exec"
                })
        
        # Emit end event
        if tail_emitter:
            await tail_emitter.emit({
                "type": "tool.end",
                "tool": "os.exec",
                "cmd": cmd,
                "duration_ms": int((time.time() - start_time) * 1000)
            })
        
        log("INFO", "tools.os", "exec_stream_completed", 
            cmd=cmd, cwd=cwd, duration_ms=int((time.time() - start_time) * 1000))
        
        return {
            "rc": 0,  # Assume success for streaming
            "stdout": "".join(stdout_chunks),
            "stderr": "".join(stderr_chunks),
            "duration_ms": int((time.time() - start_time) * 1000)
        }
        
    except Exception as e:
        error_msg = f"Streaming execution failed: {str(e)}"
        if tail_emitter:
            await tail_emitter.emit({
                "type": "error",
                "message": error_msg
            })
        
        log("ERROR", "tools.os", "exec_stream_failed", cmd=cmd, error=str(e))
        return {
            "rc": 1,
            "stdout": "".join(stdout_chunks),
            "stderr": error_msg,
            "duration_ms": int((time.time() - start_time) * 1000)
        }
