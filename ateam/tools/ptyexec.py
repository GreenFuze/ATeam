"""
PTY/ConPTY executor for cross-platform command streaming.
"""

import sys
import os
import asyncio
import platform
import shlex
from typing import AsyncIterator, Optional

IS_WINDOWS = platform.system() == "Windows"


async def stream_cmd(cmd: str, cwd: Optional[str] = None, env: Optional[dict] = None) -> AsyncIterator[str]:
    """
    Yields stdout/stderr merged text chunks from the running process.
    Uses PTY on Unix; falls back to regular pipes on Windows for minimalism.
    """
    if not IS_WINDOWS:
        # Unix PTY
        import pty
        import termios
        
        master, slave = pty.openpty()
        
        # Set raw mode if needed
        try:
            mode = termios.tcgetattr(master)
            mode[3] &= ~termios.ECHO
            termios.tcsetattr(master, termios.TCSAFLUSH, mode)
        except (termios.error, OSError):
            pass  # Ignore if terminal settings can't be changed
        
        proc = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), cwd=cwd, env=env,
            stdin=slave, stdout=slave, stderr=slave,
            start_new_session=True,
        )
        os.close(slave)
        
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, os.fdopen(master, "rb", buffering=0))
        
        try:
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                yield chunk.decode("utf-8", "replace")
        finally:
            await proc.wait()
    else:
        # Windows: merged pipes
        proc = await asyncio.create_subprocess_shell(
            cmd, cwd=cwd, env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            creationflags=0x00000008  # CREATE_NEW_PROCESS_GROUP
        )
        assert proc.stdout is not None
        
        while True:
            chunk = await proc.stdout.read(4096)
            if not chunk:
                break
            yield chunk.decode("utf-8", "replace")
        
        await proc.wait()
