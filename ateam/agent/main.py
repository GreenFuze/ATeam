import asyncio
import os
import signal
import sys
import time
from typing import Optional, Dict, Any, List
from ..config.discovery import ConfigDiscovery
from ..config.loader import load_stack
from ..agent.identity import AgentIdentity
from ..mcp.server import MCPServer
from ..mcp.client import MCPClient
from ..mcp.registry import MCPRegistryClient
from ..mcp.heartbeat import HeartbeatService
from ..mcp.ownership import OwnershipManager
from ..mcp.tail import TailEmitter
from ..mcp.contracts import AgentInfo, State
from ..util.types import Result, ErrorInfo
from ..util.logging import log
from .repl import AgentREPL
from .queue import PromptQueue
from .history import HistoryStore
from .prompt_layer import PromptLayer
from .memory import MemoryManager
from .runner import TaskRunner
from .kb_adapter import AgentKBAdapter

class AgentApp:
    """Agent application that can run in distributed or standalone mode.
    
    In distributed mode (redis_url provided), the agent connects to Redis for
    multi-agent coordination, MCP server, registry, and heartbeat services.
    
    In standalone mode (redis_url is None), the agent runs locally without
    Redis dependencies. All local functionality (REPL, queue, history, prompts,
    memory, task runner, KB) works normally.
    """
    
    def __init__(self, redis_url: Optional[str], cwd: str, name_override: str = "", project_override: str = "") -> None:
        self.redis_url = redis_url
        self.cwd = cwd
        self.name_override = name_override
        self.project_override = project_override
        
        # Determine if we're in standalone mode
        self.standalone_mode = redis_url is None
        
        # Core components
        self.identity: Optional[AgentIdentity] = None
        self.server: Optional[MCPServer] = None
        self.client: Optional[MCPClient] = None
        self.registry: Optional[MCPRegistryClient] = None
        self.heartbeat: Optional[HeartbeatService] = None
        self.ownership: Optional[OwnershipManager] = None
        self.tail: Optional[TailEmitter] = None
        self.repl: Optional[AgentREPL] = None
        
        # State management
        self.queue: Optional[PromptQueue] = None
        self.history: Optional[HistoryStore] = None
        self.prompts: Optional[PromptLayer] = None
        self.memory: Optional[MemoryManager] = None
        self.runner: Optional[TaskRunner] = None
        self.kb: Optional[AgentKBAdapter] = None
        
        # Runtime state
        self.agent_id: str = ""
        self.state: State = "init"
        self.running = False
        self._ownership_token: Optional[str] = None
        
        # Tool registry
        self._tools: Dict[str, Any] = {}

    async def bootstrap(self) -> Result[None]:
        """Bootstrap the agent: discovery → identity → lock → MCP server → registry → heartbeat → REPL.
        
        In standalone mode, skips Redis-dependent components (lock, MCP server, registry, heartbeat).
        All local functionality remains available.
        """
        try:
            log("INFO", "agent", "bootstrap_start", cwd=self.cwd)
            
            # 1. Config discovery
            discovery = ConfigDiscovery(self.cwd)
            config_stack = discovery.discover_stack()
            if not config_stack.ok:
                return Result(ok=False, error=ErrorInfo("agent.no_config", "No .ateam configuration found"))
            
            # 2. Load merged config
            config_result = load_stack(self.cwd)
            if not config_result.ok:
                return config_result
            
            project, models, tools, agents = config_result.value
            
            # 3. Compute identity
            self.identity = AgentIdentity(
                cwd=self.cwd,
                name_override=self.name_override,
                project_override=self.project_override,
                redis_url=self.redis_url
            )
            
            self.agent_id = self.identity.compute()
            log("INFO", "agent", "identity_computed", agent_id=self.agent_id)
            
            # 4. Acquire single-instance lock (skip in standalone mode)
            if not self.standalone_mode:
                lock_result = await self.identity.acquire_lock()
                if not lock_result.ok:
                    log("ERROR", "agent", "lock_failed", agent_id=self.agent_id, error=lock_result.error.message)
                    return lock_result
                
                log("INFO", "agent", "lock_acquired", agent_id=self.agent_id)
            else:
                log("INFO", "agent", "standalone_mode", agent_id=self.agent_id)
            
            # 5. Initialize state management
            agent_name = self.agent_id.split("/")[1]  # Extract agent name from agent_id
            agent_config = agents.get(agent_name, {})
            agent_dir = os.path.join(self.cwd, ".ateam", "agents", agent_name)
            state_dir = os.path.join(agent_dir, "state")
            
            os.makedirs(state_dir, exist_ok=True)
            
            self.queue = PromptQueue(os.path.join(state_dir, "queue.jsonl"))
            
            # Initialize history with summarization configuration
            from .summarization import SummarizationConfig, SummarizationStrategy
            summarization_config = SummarizationConfig(
                strategy=SummarizationStrategy.TOKEN_BASED,
                token_threshold=getattr(agent_config, "summarization_token_threshold", 1000),
                time_threshold=getattr(agent_config, "summarization_time_threshold", 3600),
                max_summaries=getattr(agent_config, "max_summaries", 10),
                importance_threshold=getattr(agent_config, "importance_threshold", 0.7),
                preserve_tool_calls=getattr(agent_config, "preserve_tool_calls", True)
            )
            
            self.history = HistoryStore(
                os.path.join(state_dir, "history.jsonl"),
                os.path.join(state_dir, "summary.jsonl"),
                summarization_config
            )
            
            # Reconstruct context from summaries and raw tail on startup
            self._reconstruct_context_on_startup()
            
            # 6. Initialize prompt layer
            base_path = os.path.join(agent_dir, "system_base.md")
            overlay_path = os.path.join(agent_dir, "system_overlay.md")
            self.prompts = PromptLayer(base_path, overlay_path)
            
            # 7. Initialize memory manager
            ctx_limit = getattr(agent_config, "ctx_limit_tokens", 128000)
            summarize_threshold = getattr(agent_config, "summarize_threshold", 0.8)
            self.memory = MemoryManager(ctx_limit, summarize_threshold)
            
            # 8. Initialize task runner
            self.runner = TaskRunner(self)
            
            # Set up LLM provider using the llm package
            model_id = getattr(agent_config, "model", "echo")
            if model_id == "echo":
                # Use echo provider for testing
                from ..llm.echo import EchoProvider
                llm_provider = EchoProvider(model_id=model_id)
            else:
                # Use the llm package for real models
                from ..llm.base import LLMProvider
                try:
                    llm_provider = LLMProvider(model_id=model_id)
                except ValueError as e:
                    log("WARN", "agent", "model_not_found", model_id=model_id, error=str(e))
                    # Fallback to echo provider
                    from ..llm.echo import EchoProvider
                    llm_provider = EchoProvider(model_id="echo")
            
            self.runner.set_llm_provider(llm_provider)
            
            # 9. Register built-in tools
            self._register_builtin_tools()
            
            # 9. Initialize KB adapter
            agent_dir = os.path.join(self.cwd, ".ateam", "agents", agent_name)
            project_dir = os.path.join(self.cwd, ".ateam")
            user_dir = os.path.expanduser("~/.ateam")
            self.kb = AgentKBAdapter(self.agent_id, agent_dir, project_dir, user_dir)
            
            # 7. Start MCP server (skip in standalone mode)
            if not self.standalone_mode:
                self.server = MCPServer(self.redis_url, self.agent_id)
                self._register_mcp_handlers()
                
                server_result = await self.server.start()
                if not server_result.ok:
                    return server_result
                
                log("INFO", "agent", "mcp_server_started", agent_id=self.agent_id)
                
                # 8. Initialize TailEmitter for emitting events
                self.tail = TailEmitter(self.redis_url, self.agent_id)
                await self.tail.connect()
                
                log("INFO", "agent", "tail_emitter_initialized", agent_id=self.agent_id)
                
                # Now that tail emitter is available, reconstruct context with tail events
                self._reconstruct_context_with_tail_events()
                
                # 9. Initialize MCP client for making RPC calls to other agents
                self.client = MCPClient(self.redis_url, self.agent_id)
                await self.client.connect()
                
                log("INFO", "agent", "mcp_client_initialized", agent_id=self.agent_id)
                
                # 10. Register with registry
                self.registry = MCPRegistryClient(self.redis_url)
                await self.registry.connect()
                
                agent_info = AgentInfo(
                    id=self.agent_id,
                    name=agent_name,
                    project=self.agent_id.split("/")[0],
                    model=getattr(agent_config, "model", "gpt-4"),
                    cwd=self.cwd,
                    host=os.uname().nodename if hasattr(os, 'uname') else "localhost",
                    pid=os.getpid(),
                    started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    state="registered",
                    ctx_pct=0.0
                )
                
                register_result = await self.registry.register_agent(agent_info)
                if not register_result.ok:
                    return register_result
                
                log("INFO", "agent", "registered", agent_id=self.agent_id)
                
                # 11. Start heartbeat
                self.heartbeat = HeartbeatService(self.agent_id, self.redis_url, identity=self.identity, registry=self.registry)
                heartbeat_result = await self.heartbeat.start()
                if not heartbeat_result.ok:
                    return heartbeat_result
                
                log("INFO", "agent", "heartbeat_started", agent_id=self.agent_id)
            else:
                log("INFO", "agent", "distributed_features_skipped", agent_id=self.agent_id)
            
            # 11. Initialize REPL
            self.repl = AgentREPL(self)
            
            # Set state based on mode
            if self.standalone_mode:
                self.state = "standalone"
            else:
                self.state = "registered"
            
            self.running = True
            
            log("INFO", "agent", "bootstrap_complete", agent_id=self.agent_id, mode="standalone" if self.standalone_mode else "connected")
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "agent", "bootstrap_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("agent.bootstrap_failed", str(e)))

    def register_tool(self, name: str, tool_func: Any) -> None:
        """Register a tool function."""
        self._tools[name] = tool_func
        log("INFO", "agent", "tool_registered", tool=name)
    
    def get_tool(self, name: str) -> Optional[Any]:
        """Get a registered tool function."""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    def _register_builtin_tools(self) -> None:
        """Register built-in tools."""
        # Register filesystem tools
        from ..tools.builtin.fs import read_file, write_file, list_dir, stat_file
        
        def fs_read_file(path: str) -> Dict[str, Any]:
            result = read_file(path, self.cwd)
            return {"ok": result.ok, "value": result.value, "error": result.error.message if result.error else None}
        
        def fs_write_file(path: str, content: str, mode: str = "w") -> Dict[str, Any]:
            result = write_file(path, content, self.cwd, mode)
            return {"ok": result.ok, "error": result.error.message if result.error else None}
        
        def fs_list_dir(path: str) -> Dict[str, Any]:
            result = list_dir(path, self.cwd)
            return {"ok": result.ok, "value": result.value, "error": result.error.message if result.error else None}
        
        def fs_stat_file(path: str) -> Dict[str, Any]:
            result = stat_file(path, self.cwd)
            return {"ok": result.ok, "value": result.value, "error": result.error.message if result.error else None}
        
        self.register_tool("fs.read_file", fs_read_file)
        self.register_tool("fs.write_file", fs_write_file)
        self.register_tool("fs.list_dir", fs_list_dir)
        self.register_tool("fs.stat_file", fs_stat_file)
        
        # Register OS execution tools
        from ..tools.builtin.os import exec, exec_stream
        
        def os_exec(cmd: str, cwd: str = None, timeout: int = None, env: Dict[str, str] = None, pty: bool = True) -> Dict[str, Any]:
            return exec(cmd, cwd or self.cwd, timeout, env, pty)
        
        async def os_exec_stream(cmd: str, cwd: str = None, env: Dict[str, str] = None) -> Dict[str, Any]:
            return await exec_stream(cmd, cwd or self.cwd, env, self.tail)
        
        self.register_tool("os.exec", os_exec)
        self.register_tool("os.exec_stream", os_exec_stream)
        
        log("INFO", "agent", "builtin_tools_registered", tools=list(self._tools.keys()))
    
    def _register_mcp_handlers(self) -> None:
        """Register MCP method handlers."""
        if not self.server:
            return
        
        self.server.register_handler("status", self._handle_status)
        self.server.register_handler("input", self._handle_input)
        self.server.register_handler("interrupt", self._handle_interrupt)
        self.server.register_handler("cancel", self._handle_cancel)
        self.server.register_handler("prompt.set", self._handle_prompt_set)
        self.server.register_handler("prompt.reload", self._handle_prompt_reload)
        self.server.register_handler("prompt.get", self._handle_prompt_get)
        self.server.register_handler("prompt.overlay", self._handle_prompt_overlay)
        self.server.register_handler("kb.ingest", self._handle_kb_ingest)
        self.server.register_handler("kb.search", self._handle_kb_search)
        self.server.register_handler("kb.copy_from", self._handle_kb_copy_from)
        self.server.register_handler("kb.get_items", self._handle_kb_get_items)
        self.server.register_handler("history.clear", self._handle_history_clear)
    
    def _check_writer_access(self) -> bool:
        """Check if current session has write access to this agent."""
        # In standalone mode, always grant write access
        if self.standalone_mode:
            return True
        
        # Check if we still own the agent
        return self.ownership.has_ownership(self.agent_id, self._ownership_token)

    def _reconstruct_context_on_startup(self) -> None:
        """Reconstruct context from summaries and raw tail on agent startup."""
        try:
            # Initial reconstruction without tail events (will be updated later)
            reconstructed_context = self.history.reconstruct_context()
            
            # Log the initial reconstruction
            log("INFO", "agent", "context_reconstructed_initial", 
                agent_id=self.agent_id, 
                context_length=len(reconstructed_context),
                summaries_count=len(self.history._summaries),
                turns_count=len(self.history._turns))
            
            # Store the reconstructed context for use in the task runner
            self._reconstructed_context = reconstructed_context
            
        except Exception as e:
            log("ERROR", "agent", "context_reconstruction_failed", 
                agent_id=self.agent_id, error=str(e))
            # Continue without reconstructed context
            self._reconstructed_context = "No conversation history available."

    def _reconstruct_context_with_tail_events(self) -> None:
        """Reconstruct context using the history store and the latest tail events."""
        try:
            # Get recent tail events if available
            tail_events = []
            if not self.standalone_mode and hasattr(self, 'tail'):
                # Get recent tail events from the tail emitter's ring buffer
                tail_events = self.tail.get_recent_events(count=50)
            
            # Reconstruct context using the history store
            reconstructed_context = self.history.reconstruct_context_from_tail(tail_events)
            
            # Log the reconstruction
            log("INFO", "agent", "context_reconstructed_with_tail", 
                agent_id=self.agent_id, 
                context_length=len(reconstructed_context),
                summaries_count=len(self.history._summaries),
                turns_count=len(self.history._turns),
                tail_events_count=len(tail_events))
            
            # Store the reconstructed context for use in the task runner
            self._reconstructed_context = reconstructed_context
            
        except Exception as e:
            log("ERROR", "agent", "context_reconstruction_with_tail_failed", 
                agent_id=self.agent_id, error=str(e))
            # Continue without reconstructed context
            self._reconstructed_context = "No conversation history available."

    async def _handle_status(self, params: dict) -> dict:
        """Handle status RPC call."""
        ctx_pct = 0.0
        if self.memory:
            ctx_pct = self.memory.ctx_pct()
        
        return {
            "state": self.state,
            "ctx_pct": ctx_pct,
            "tokens_in_ctx": 0,  # TODO: implement memory manager
            "model": "gpt-4",  # TODO: get from config
            "cwd": self.cwd,
            "pid": os.getpid(),
            "host": os.uname().nodename if hasattr(os, 'uname') else "localhost"
        }

    async def _handle_input(self, params: dict) -> dict:
        """Handle input RPC call."""
        if not self._check_writer_access():
            return {"ok": False, "error": "Not the owner of this agent"}
        
        text = params.get("text", "")
        source = params.get("meta", {}).get("source", "console")
        
        if not self.queue:
            return {"ok": False, "error": "Queue not initialized"}
        
        queue_result = self.queue.append(text, source)
        if not queue_result.ok:
            return {"ok": False, "error": queue_result.error.message}
        
        qid = queue_result.value
        log("INFO", "agent", "input_queued", qid=qid, source=source)
        
        # Start processing the task if runner is available
        if self.runner and not self.runner.is_running():
            asyncio.create_task(self._process_queue())
        
        return {"ok": True, "qid": qid}

    async def _handle_interrupt(self, params: dict) -> dict:
        """Handle interrupt RPC call."""
        if not self._check_writer_access():
            return {"ok": False, "error": "Not the owner of this agent"}
        
        log("INFO", "agent", "interrupt_received")
        if self.runner:
            self.runner.interrupt()
        return {"ok": True}

    async def _handle_cancel(self, params: dict) -> dict:
        """Handle cancel RPC call."""
        if not self._check_writer_access():
            return {"ok": False, "error": "Not the owner of this agent"}
        
        hard = params.get("hard", False)
        log("INFO", "agent", "cancel_received", hard=hard)
        if self.runner:
            self.runner.cancel(hard)
        return {"ok": True}

    async def _handle_prompt_set(self, params: dict) -> dict:
        """Handle prompt.set RPC call."""
        if not self._check_writer_access():
            return {"ok": False, "error": "Not the owner of this agent"}
        
        if not self.prompts:
            return {"ok": False, "error": "Prompt layer not initialized"}
        
        base = params.get("base")
        overlay = params.get("overlay")
        
        if base is not None:
            self.prompts.set_base(base)
        if overlay is not None:
            self.prompts.set_overlay(overlay)
        
        log("INFO", "agent", "prompt_updated")
        return {"ok": True}

    async def _handle_prompt_reload(self, params: dict) -> dict:
        """Handle prompt.reload RPC call."""
        if not self._check_writer_access():
            return {"ok": False, "error": "Not the owner of this agent"}
        
        if not self.prompts:
            return {"ok": False, "error": "Prompt layer not initialized"}
        
        result = self.prompts.reload_from_disk()
        if not result.ok:
            return {"ok": False, "error": result.error.message}
        
        log("INFO", "agent", "prompt_reloaded")
        return {"ok": True}

    async def _handle_prompt_get(self, params: dict) -> dict:
        """Handle prompt.get RPC call."""
        if not self.prompts:
            return {"ok": False, "error": "Prompt layer not initialized"}
        
        try:
            effective_prompt = self.prompts.effective()
            base_content = self.prompts.get_base()
            overlay_content = self.prompts.get_overlay()
            overlay_lines = self.prompts.get_overlay_lines()
            
            return {
                "ok": True,
                "effective": effective_prompt,
                "base": base_content,
                "overlay": overlay_content,
                "overlay_lines": overlay_lines
            }
        except Exception as e:
            log("ERROR", "agent", "prompt_get_failed", error=str(e))
            return {"ok": False, "error": str(e)}

    async def _handle_prompt_overlay(self, params: dict) -> dict:
        """Handle prompt.overlay RPC call."""
        if not self._check_writer_access():
            return {"ok": False, "error": "Not the owner of this agent"}
        
        if not self.prompts:
            return {"ok": False, "error": "Prompt layer not initialized"}
        
        line = params.get("line")
        if not line:
            return {"ok": False, "error": "No line provided"}
        
        try:
            result = self.prompts.append_overlay(line)
            if not result.ok:
                return {"ok": False, "error": result.error.message}
            
            log("INFO", "agent", "prompt_overlay_added", line=line)
            return {"ok": True}
        except Exception as e:
            log("ERROR", "agent", "prompt_overlay_failed", error=str(e))
            return {"ok": False, "error": str(e)}
    
    async def _process_queue(self) -> None:
        """Process items from the queue using the task runner."""
        if not self.queue or not self.runner:
            return
        
        while self.queue.size() > 0 and not self.runner.is_running():
            item = self.queue.peek()
            if not item:
                break
            
            # Process the item
            result = await self.runner.run_next(item)
            
            if result.success:
                # Add to history
                if self.history:
                    from ..mcp.contracts import Turn
                    turn = Turn(
                        ts=time.time(),
                        role="assistant",
                        source="system",
                        content=result.response,
                        tokens_in=0,  # Will be updated by memory manager
                        tokens_out=result.tokens_used
                    )
                    self.history.append(turn)
                
                # Remove from queue
                self.queue.pop()
                
                log("INFO", "agent", "task_completed", qid=item.id, tokens=result.tokens_used)
            else:
                log("ERROR", "agent", "task_failed", qid=item.id, error=result.error)
                break

    async def _handle_kb_ingest(self, params: dict) -> dict:
        """Handle KB ingest RPC call."""
        if not self._check_writer_access():
            return {"ok": False, "error": "Not the owner of this agent"}
        
        if not self.kb:
            return {"ok": False, "error": "KB adapter not initialized"}
        
        paths = params.get("paths", [])
        scope = params.get("scope", "agent")
        metadata = params.get("metadata", {})
        
        if not paths:
            return {"ok": False, "error": "No paths provided"}
        
        try:
            ingested_ids = self.kb.ingest(paths, scope, metadata)
            return {"ok": True, "ids": ingested_ids}
        except Exception as e:
            log("ERROR", "agent", "kb_ingest_failed", error=str(e))
            return {"ok": False, "error": str(e)}

    async def _handle_kb_search(self, params: dict) -> dict:
        """Handle KB search RPC call."""
        if not self.kb:
            return {"ok": False, "error": "KB adapter not initialized"}
        
        query = params.get("query", "")
        scope = params.get("scope", "agent")
        k = params.get("k", 5)
        
        if not query:
            return {"ok": False, "error": "No query provided"}
        
        try:
            hits = self.kb.search(query, scope, k)
            # Convert KBHit objects to dicts for JSON serialization
            hits_data = [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "metadata": hit.metadata
                }
                for hit in hits
            ]
            return {"ok": True, "hits": hits_data}
        except Exception as e:
            log("ERROR", "agent", "kb_search_failed", error=str(e))
            return {"ok": False, "error": str(e)}

    async def _handle_kb_copy_from(self, params: dict) -> dict:
        """Handle KB copy from RPC call."""
        if not self._check_writer_access():
            return {"ok": False, "error": "Not the owner of this agent"}
        
        if not self.kb:
            return {"ok": False, "error": "KB adapter not initialized"}
        
        source_agent = params.get("source_agent", "")
        ids = params.get("ids", [])
        
        if not source_agent:
            return {"ok": False, "error": "No source agent provided"}
        if not ids:
            return {"ok": False, "error": "No IDs provided"}
        
        if not self.client:
            return {"ok": False, "error": "MCP client not initialized"}
        
        try:
            # Make RPC call to source agent to get KB content
            rpc_result = await self.client.call(source_agent, "kb.get_items", {"ids": ids})
            if not rpc_result.ok:
                return {"ok": False, "error": f"Failed to get items from {source_agent}: {rpc_result.error.message}"}
            
            items_data = rpc_result.value.get("items", [])
            if not items_data:
                return {"ok": True, "copied": [], "skipped": ids}
            
            # Add items to our own KB storage
            copied_ids = []
            skipped_ids = []
            
            for item_data in items_data:
                try:
                    # Add content to our agent KB storage
                    item_ids = self.kb.kb_adapter.agent_storage.add(
                        f"agent_{self.agent_id}",
                        item_data["content"],
                        item_data.get("metadata", {})
                    )
                    copied_ids.extend(item_ids)
                except Exception as e:
                    log("ERROR", "agent", "kb_copy_item_failed", 
                        item_id=item_data.get("id"), error=str(e))
                    skipped_ids.append(item_data.get("id", "unknown"))
            
            result = {"copied": copied_ids, "skipped": skipped_ids}
            log("INFO", "agent", "kb_copy_completed", 
                source=source_agent, copied=len(copied_ids), skipped=len(skipped_ids))
            return {"ok": True, **result}
            
        except Exception as e:
            log("ERROR", "agent", "kb_copy_failed", error=str(e))
            return {"ok": False, "error": str(e)}

    async def _handle_kb_get_items(self, params: dict) -> dict:
        """Handle KB get items RPC call (for copy operations)."""
        if not self.kb:
            return {"ok": False, "error": "KB adapter not initialized"}
        
        ids = params.get("ids", [])
        
        if not ids:
            return {"ok": False, "error": "No IDs provided"}
        
        try:
            items = []
            for item_id in ids:
                # Get item from agent KB storage
                item = self.kb.kb_adapter.agent_storage.get(f"agent_{self.agent_id}", item_id)
                if item:
                    items.append({
                        "id": item["id"],
                        "content": item["content"],
                        "metadata": item.get("metadata", {})
                    })
            
            log("INFO", "agent", "kb_get_items_completed", 
                agent_id=self.agent_id, requested=len(ids), found=len(items))
            return {"ok": True, "items": items}
            
        except Exception as e:
            log("ERROR", "agent", "kb_get_items_failed", error=str(e))
            return {"ok": False, "error": str(e)}

    async def _handle_history_clear(self, params: dict) -> dict:
        """Handle history clear RPC call."""
        if not self._check_writer_access():
            return {"ok": False, "error": "Not the owner of this agent"}
        
        confirm = params.get("confirm", False)
        
        if not confirm:
            return {"ok": False, "error": "Confirmation required to clear history"}
        
        try:
            if not self.history:
                return {"ok": False, "error": "History store not initialized"}
            
            # Clear the history
            result = self.history.clear(confirm=True)
            if not result.ok:
                return {"ok": False, "error": result.error.message}
            
            log("INFO", "agent", "history_cleared", agent_id=self.agent_id)
            return {"ok": True}
            
        except Exception as e:
            log("ERROR", "agent", "history_clear_failed", error=str(e))
            return {"ok": False, "error": str(e)}

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            log("INFO", "agent", "signal_received", signal=signum, agent_id=self.agent_id)
            # Set running to False to trigger graceful shutdown
            self.running = False
            
        # Handle SIGINT (Ctrl+C) and SIGTERM
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # On Windows, also handle SIGBREAK
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, signal_handler)

    async def run(self) -> Result[None]:
        """Run the agent REPL with graceful shutdown support."""
        if not self.running:
            return Result(ok=False, error=ErrorInfo("agent.not_bootstrapped", "Agent not bootstrapped"))
        
        try:
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            log("INFO", "agent", "starting_repl", agent_id=self.agent_id)
            await self.repl.loop()
            
            log("INFO", "agent", "repl_stopped", agent_id=self.agent_id)
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "agent", "repl_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("agent.repl_failed", str(e)))

    async def shutdown(self) -> Result[None]:
        """Shutdown the agent gracefully.
        
        In standalone mode, skips cleanup of Redis-dependent components.
        All local state is preserved.
        """
        try:
            self.running = False
            
            # Stop REPL
            if self.repl:
                self.repl.stop()
            
            # Stop distributed services (skip in standalone mode)
            if not self.standalone_mode:
                # Stop heartbeat
                if self.heartbeat:
                    await self.heartbeat.stop()
                
                # Unregister from registry
                if self.registry and self.agent_id:
                    await self.registry.unregister_agent(self.agent_id)
                    await self.registry.disconnect()
                
                # Stop MCP server
                if self.server:
                    await self.server.stop()
                
                # Disconnect TailEmitter
                if self.tail:
                    await self.tail.disconnect()
                    log("INFO", "agent", "tail_emitter_disconnected", agent_id=self.agent_id)
                
                # Release single-instance lock
                if self.identity and self.agent_id:
                    release_result = await self.identity.release_lock()
                    if release_result.ok:
                        log("INFO", "agent", "lock_released", agent_id=self.agent_id)
                    else:
                        log("WARN", "agent", "lock_release_failed", 
                            agent_id=self.agent_id, error=release_result.error.message)
                    await self.identity.disconnect()
            else:
                log("INFO", "agent", "distributed_cleanup_skipped", agent_id=self.agent_id)
            
            log("INFO", "agent", "shutdown_complete", agent_id=self.agent_id, mode="standalone" if self.standalone_mode else "connected")
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "agent", "shutdown_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("agent.shutdown_failed", str(e)))
