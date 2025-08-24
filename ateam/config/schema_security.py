"""Security configuration schema."""

from pydantic import BaseModel, Field
from typing import List, Optional, Set


class PathSandboxCfg(BaseModel):
    """Configuration for path sandboxing."""
    
    allowed_paths: List[str] = Field(
        default_factory=list,
        description="List of allowed directory paths (absolute)"
    )
    denied_paths: List[str] = Field(
        default_factory=list,
        description="List of explicitly denied paths (takes precedence)"
    )
    allow_temp: bool = Field(
        True,
        description="Allow access to system temp directory"
    )
    allow_home: bool = Field(
        False,
        description="Allow access to user home directory"
    )
    allow_cwd: bool = Field(
        True,
        description="Allow access to current working directory"
    )


class CommandSandboxCfg(BaseModel):
    """Configuration for command execution sandboxing."""
    
    allowed_commands: Optional[List[str]] = Field(
        None,
        description="List of allowed command names (if None, all are allowed except denied)"
    )
    denied_commands: List[str] = Field(
        default_factory=lambda: [
            "rm", "rmdir", "del", "format", "fdisk", "mkfs",
            "sudo", "su", "chmod", "chown", "passwd",
            "nc", "netcat", "telnet", "ssh", "ftp", "curl", "wget"
        ],
        description="List of explicitly denied commands"
    )
    allow_shell: bool = Field(
        False,
        description="Allow shell command execution"
    )
    allow_network: bool = Field(
        False,
        description="Allow network-related commands"
    )


class SecurityCfg(BaseModel):
    """Security configuration."""
    
    enabled: bool = Field(
        True,
        description="Enable security controls"
    )
    path_sandbox: PathSandboxCfg = Field(
        default_factory=PathSandboxCfg,
        description="Path sandboxing configuration"
    )
    command_sandbox: CommandSandboxCfg = Field(
        default_factory=CommandSandboxCfg,
        description="Command execution sandboxing configuration"
    )
    strict_mode: bool = Field(
        False,
        description="Enable strict security mode (more restrictive)"
    )
