"""
MCP Orchestrator Client

Provides RPC methods for creating and spawning agents remotely.
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

from .redis_transport import RedisTransport
from ..util.types import Result, ErrorInfo


class MCPOrchestratorClient:
    """Client for orchestrating agent creation and spawning via MCP."""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._transport: Optional[RedisTransport] = None
    
    async def connect(self) -> Result[None]:
        """Connect to Redis transport."""
        try:
            self._transport = RedisTransport(self.redis_url)
            await self._transport.connect()
            return Result(ok=True)
        except Exception as e:
            return Result(ok=False, error=ErrorInfo(
                code="orchestrator.connect_failed",
                message=f"Failed to connect to Redis: {e}"
            ))
    
    async def disconnect(self) -> None:
        """Disconnect from Redis transport."""
        if self._transport:
            await self._transport.disconnect()
            self._transport = None
    
    async def create_agent(self, 
                          project: str,
                          name: str,
                          cwd: str,
                          model: str,
                          system_base: Optional[str] = None,
                          kb_seeds: Optional[List[str]] = None) -> Result[str]:
        """
        Create a new agent configuration and spawn it.
        
        Returns the agent ID (project/name) on success.
        """
        if not self._transport:
            return Result(ok=False, error=ErrorInfo(
                code="orchestrator.not_connected",
                message="Not connected to Redis transport"
            ))
        
        try:
            # Prepare agent configuration
            config = {
                "project": project,
                "name": name,
                "cwd": cwd,
                "model": model,
                "system_base": system_base,
                "kb_seeds": kb_seeds or []
            }
            
            # Call the orchestrator.create_agent RPC
            result = await self._transport.call("orchestrator.create_agent", config)
            
            if not result.ok:
                return result
            
            if result.value is None:
                return Result(ok=False, error=ErrorInfo(
                    code="orchestrator.invalid_response",
                    message="No response value"
                ))
            
            agent_id = result.value.get("agent_id")
            if not agent_id:
                return Result(ok=False, error=ErrorInfo(
                    code="orchestrator.invalid_response",
                    message="No agent_id in response"
                ))
            
            return Result(ok=True, value=agent_id)
            
        except Exception as e:
            return Result(ok=False, error=ErrorInfo(
                code="orchestrator.create_failed",
                message=f"Failed to create agent: {e}"
            ))
    
    async def spawn_agent(self, agent_id: str, remote: bool = False) -> Result[str]:
        """
        Spawn an existing agent configuration.
        
        Args:
            agent_id: The agent ID (project/name)
            remote: If True, return a command to run remotely instead of spawning locally
            
        Returns:
            If remote=False: Success result
            If remote=True: Command string to run remotely
        """
        if not self._transport:
            return Result(ok=False, error=ErrorInfo(
                code="orchestrator.not_connected",
                message="Not connected to Redis transport"
            ))
        
        try:
            params = {
                "agent_id": agent_id,
                "remote": remote
            }
            
            result = await self._transport.call("orchestrator.spawn_agent", params)
            
            if not result.ok:
                return result
            
            if remote:
                if result.value is None:
                    return Result(ok=False, error=ErrorInfo(
                        code="orchestrator.invalid_response",
                        message="No response value"
                    ))
                command = result.value.get("command")
                if not command:
                    return Result(ok=False, error=ErrorInfo(
                        code="orchestrator.invalid_response",
                        message="No command in remote spawn response"
                    ))
                return Result(ok=True, value=command)
            else:
                return Result(ok=True)
                
        except Exception as e:
            return Result(ok=False, error=ErrorInfo(
                code="orchestrator.spawn_failed",
                message=f"Failed to spawn agent: {e}"
            ))
    
    async def list_agents(self) -> Result[List[Dict[str, Any]]]:
        """List all available agent configurations."""
        if not self._transport:
            return Result(ok=False, error=ErrorInfo(
                code="orchestrator.not_connected",
                message="Not connected to Redis transport"
            ))
        
        try:
            result = await self._transport.call("orchestrator.list_agents", {})
            
            if not result.ok:
                return result
            
            if result.value is None:
                return Result(ok=False, error=ErrorInfo(
                    code="orchestrator.invalid_response",
                    message="No response value"
                ))
            
            agents = result.value.get("agents", [])
            return Result(ok=True, value=agents)
            
        except Exception as e:
            return Result(ok=False, error=ErrorInfo(
                code="orchestrator.list_failed",
                message=f"Failed to list agents: {e}"
            ))
    
    async def delete_agent(self, agent_id: str) -> Result[None]:
        """Delete an agent configuration."""
        if not self._transport:
            return Result(ok=False, error=ErrorInfo(
                code="orchestrator.not_connected",
                message="Not connected to Redis transport"
            ))
        
        try:
            params = {"agent_id": agent_id}
            result = await self._transport.call("orchestrator.delete_agent", params)
            
            if not result.ok:
                return result
            
            return Result(ok=True)
            
        except Exception as e:
            return Result(ok=False, error=ErrorInfo(
                code="orchestrator.delete_failed",
                message=f"Failed to delete agent: {e}"
            ))


class LocalAgentSpawner:
    """Handles local agent spawning for development and testing."""
    
    @staticmethod
    def spawn_local(agent_id: str, redis_url: str, cwd: Optional[str] = None) -> subprocess.Popen:
        """
        Spawn an agent locally as a subprocess.
        
        Args:
            agent_id: The agent ID (project/name)
            redis_url: Redis connection URL
            cwd: Working directory for the agent
            
        Returns:
            Popen object for the spawned process
        """
        cmd = [
            sys.executable, "-m", "ateam", "agent",
            "--agent-id", agent_id,
            "--redis", redis_url
        ]
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent)
        
        return subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    
    @staticmethod
    def generate_remote_command(agent_id: str, redis_url: str) -> str:
        """
        Generate a command string for remote execution.
        
        Args:
            agent_id: The agent ID (project/name)
            redis_url: Redis connection URL
            
        Returns:
            Command string to run remotely
        """
        return f"ateam agent --agent-id {agent_id} --redis {redis_url}"
