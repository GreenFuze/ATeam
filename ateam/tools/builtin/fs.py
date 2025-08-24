"""
Filesystem operations with sandbox protection.
"""

import os
import stat
from pathlib import Path
from typing import Dict, List, Optional, Any
from ...util.types import Result, ErrorInfo


def _is_safe_path(path: str, cwd: str) -> bool:
    """Check if path is safe within sandbox."""
    try:
        # Resolve the cwd first
        cwd_resolved = Path(cwd).resolve()
        
        # Handle relative paths properly
        if Path(path).is_absolute():
            # For absolute paths, check if they're within cwd
            path_resolved = Path(path).resolve()
            return str(path_resolved).startswith(str(cwd_resolved))
        else:
            # For relative paths, join with cwd and check
            combined_path = cwd_resolved / Path(path)
            resolved_path = combined_path.resolve()
            return str(resolved_path).startswith(str(cwd_resolved))
    except (ValueError, RuntimeError):
        return False


def _get_safe_path(path: str, cwd: str) -> Optional[Path]:
    """Get safe path within sandbox."""
    if not _is_safe_path(path, cwd):
        return None
    try:
        return Path(cwd) / Path(path)
    except (ValueError, RuntimeError):
        return None


def read_file(path: str, cwd: str) -> Result[str]:
    """Read file safely within sandbox."""
    safe_path = _get_safe_path(path, cwd)
    if not safe_path:
        return Result(ok=False, error=ErrorInfo(
            code="fs.access_denied", 
            message=f"Access denied: {path} is outside sandbox"
        ))
    
    try:
        if not safe_path.exists():
            return Result(ok=False, error=ErrorInfo(
                code="fs.not_found", 
                message=f"File not found: {path}"
            ))
        
        if not safe_path.is_file():
            return Result(ok=False, error=ErrorInfo(
                code="fs.not_file", 
                message=f"Path is not a file: {path}"
            ))
        
        content = safe_path.read_text(encoding='utf-8')
        return Result(ok=True, value=content)
        
    except PermissionError:
        return Result(ok=False, error=ErrorInfo(
            code="fs.permission_denied", 
            message=f"Permission denied: {path}"
        ))
    except Exception as e:
        return Result(ok=False, error=ErrorInfo(
            code="fs.read_error", 
            message=f"Error reading file: {path}"
        ))


def write_file(path: str, content: str, cwd: str, mode: str = "w") -> Result[None]:
    """Write file safely within sandbox."""
    safe_path = _get_safe_path(path, cwd)
    if not safe_path:
        return Result(ok=False, error=ErrorInfo(
            code="fs.access_denied", 
            message=f"Access denied: {path} is outside sandbox"
        ))
    
    try:
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        with safe_path.open(mode, encoding='utf-8') as f:
            f.write(content)
        return Result(ok=True)
        
    except PermissionError:
        return Result(ok=False, error=ErrorInfo(
            code="fs.permission_denied", 
            message=f"Permission denied: {path}"
        ))
    except Exception as e:
        return Result(ok=False, error=ErrorInfo(
            code="fs.write_error", 
            message=f"Error writing file: {path}"
        ))


def list_dir(path: str, cwd: str) -> Result[List[Dict[str, Any]]]:
    """List directory contents safely within sandbox."""
    safe_path = _get_safe_path(path, cwd)
    if not safe_path:
        return Result(ok=False, error=ErrorInfo(
            code="fs.access_denied", 
            message=f"Access denied: {path} is outside sandbox"
        ))
    
    try:
        if not safe_path.exists():
            return Result(ok=False, error=ErrorInfo(
                code="fs.not_found", 
                message=f"Directory not found: {path}"
            ))
        
        if not safe_path.is_dir():
            return Result(ok=False, error=ErrorInfo(
                code="fs.not_directory", 
                message=f"Path is not a directory: {path}"
            ))
        
        entries = []
        for item in safe_path.iterdir():
            try:
                stat_info = item.stat()
                entry = {
                    "name": item.name,
                    "path": str(item.relative_to(Path(cwd))),
                    "is_file": item.is_file(),
                    "is_dir": item.is_dir(),
                    "size": stat_info.st_size if item.is_file() else None,
                    "modified": stat_info.st_mtime,
                    "permissions": oct(stat_info.st_mode)[-3:]
                }
                entries.append(entry)
            except (PermissionError, OSError):
                continue
        
        return Result(ok=True, value=entries)
        
    except PermissionError:
        return Result(ok=False, error=ErrorInfo(
            code="fs.permission_denied", 
            message=f"Permission denied: {path}"
        ))
    except Exception as e:
        return Result(ok=False, error=ErrorInfo(
            code="fs.list_error", 
            message=f"Error listing directory: {path}"
        ))


def stat_file(path: str, cwd: str) -> Result[Dict[str, Any]]:
    """Get file/directory statistics safely within sandbox."""
    safe_path = _get_safe_path(path, cwd)
    if not safe_path:
        return Result(ok=False, error=ErrorInfo(
            code="fs.access_denied", 
            message=f"Access denied: {path} is outside sandbox"
        ))
    
    try:
        if not safe_path.exists():
            return Result(ok=False, error=ErrorInfo(
                code="fs.not_found", 
                message=f"Path not found: {path}"
            ))
        
        stat_info = safe_path.stat()
        stats = {
            "path": str(safe_path.relative_to(Path(cwd))),
            "name": safe_path.name,
            "is_file": safe_path.is_file(),
            "is_dir": safe_path.is_dir(),
            "size": stat_info.st_size if safe_path.is_file() else None,
            "modified": stat_info.st_mtime,
            "created": stat_info.st_ctime,
            "permissions": oct(stat_info.st_mode)[-3:],
            "owner_readable": bool(stat_info.st_mode & stat.S_IRUSR),
            "owner_writable": bool(stat_info.st_mode & stat.S_IWUSR),
            "owner_executable": bool(stat_info.st_mode & stat.S_IXUSR)
        }
        
        return Result(ok=True, value=stats)
        
    except PermissionError:
        return Result(ok=False, error=ErrorInfo(
            code="fs.permission_denied", 
            message=f"Permission denied: {path}"
        ))
    except Exception as e:
        return Result(ok=False, error=ErrorInfo(
            code="fs.stat_error", 
            message=f"Error getting stats: {path}"
        ))
