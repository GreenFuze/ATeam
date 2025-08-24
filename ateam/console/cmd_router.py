"""Console command router and handlers."""

import shlex
from typing import Optional

from ..util.logging import log
from ..util.types import Result, ErrorInfo


class CommandRouter:
    """Router for console commands."""
    
    def __init__(self, app, ui):
        self.app = app
        self.ui = ui
    
    async def execute(self, line: str) -> None:
        """Execute a command line."""
        try:
            # Check for overlay line command (# <text>)
            if line.startswith("# "):
                await self._handle_overlay_line(line[2:])  # Remove "# " prefix
                return
            
            # Parse command
            parts = shlex.split(line)
            if not parts:
                return
            
            command = parts[0]
            args = parts[1:]
            
            # Check if current session is in read-only mode
            current_session = self.app.get_current_session()
            if current_session and current_session.is_read_only():
                # Show read-only banner if not already shown
                if not self.ui.is_read_only_banner_active():
                    self.ui.show_read_only_banner(current_session.agent_id)
                
                # Allow read-only commands
                read_only_commands = {"/ps", "/help", "/quit", "/who", "/ctx", "/sys", "/detach"}
                if command in read_only_commands:
                    # Route to appropriate handler
                    if command == "/ps":
                        await self._handle_ps(args)
                    elif command == "/help":
                        await self._handle_help(args)
                    elif command == "/quit":
                        await self._handle_quit(args)
                    elif command == "/who":
                        await self._handle_who(args)
                    elif command == "/ctx":
                        await self._handle_ctx(args)
                    elif command == "/sys":
                        await self._handle_sys(args)
                    elif command == "/detach":
                        await self._handle_detach(args)
                else:
                    # Block write commands in read-only mode
                    self.ui.print_error("Command blocked: Session is in read-only mode. Use /detach to disconnect.")
                    return
            
            # Route to appropriate handler
            if command == "/ps":
                await self._handle_ps(args)
            elif command == "/attach":
                await self._handle_attach(args)
            elif command == "/detach":
                await self._handle_detach(args)
            elif command == "/input":
                await self._handle_input(args)
            elif command == "/status":
                await self._handle_status(args)
            elif command == "/help":
                await self._handle_help(args)
            elif command == "/quit":
                await self._handle_quit(args)
            elif command == "/ctx":
                await self._handle_ctx(args)
            elif command == "/sys":
                await self._handle_sys(args)
            elif command == "/reloadsysprompt":
                await self._handle_reloadsysprompt(args)
            elif command == "/clearhistory":
                await self._handle_clearhistory(args)
            elif command == "/kb":
                await self._handle_kb(args)
            elif command == "/kb add":
                await self._handle_kb_add(args)
            elif command == "/kb search":
                await self._handle_kb_search(args)
            elif command == "/kb copy-from":
                await self._handle_kb_copy_from(args)
            elif command == "/ui":
                await self._handle_ui(args)
            elif command == "/agent":
                await self._handle_agent(args)
            elif command == "/offload":
                await self._handle_offload(args)
            elif command == "/who":
                await self._handle_who(args)
            elif command == "/interrupt":
                await self._handle_interrupt(args)
            elif command.startswith("/"):
                self.ui.print_error(f"Unknown command: {command}")
            elif line.startswith("#"):
                # Handle overlay command
                await self._handle_overlay(line)
            else:
                # Treat as input to current agent
                await self._handle_input([line])
                
        except Exception as e:
            log("ERROR", "router", "execute_error", error=str(e))
            self.ui.print_error(f"Command execution failed: {e}")
    
    async def _handle_ps(self, args: list) -> None:
        """Handle /ps command - list agents."""
        try:
            if not self.app.registry:
                self.ui.print_error("Registry not connected")
                return
            
            agents_result = await self.app.registry.list_agents()
            if not agents_result.ok:
                self.ui.print_error(f"Failed to list agents: {agents_result.error.message}")
                return
            
            # Convert AgentInfo objects to dictionaries for UI compatibility
            agents = agents_result.value
            agents_dict = []
            for agent in agents:
                # Check if agent is already a dict or an AgentInfo object
                if isinstance(agent, dict):
                    agents_dict.append(agent)
                else:
                    # Convert AgentInfo object to dict
                    agents_dict.append({
                        "id": agent.id,
                        "name": agent.name,
                        "project": agent.project,
                        "model": agent.model,
                        "cwd": agent.cwd,
                        "host": agent.host,
                        "pid": agent.pid,
                        "started_at": agent.started_at,
                        "state": agent.state,
                        "ctx_pct": agent.ctx_pct
                    })
            
            self.ui.print_agents_list(agents_dict)
            
            # Update panes if available
            if self.ui.panes and self.ui.panes.is_running():
                self.ui.panes.update_agents(agents_dict)
            
        except Exception as e:
            log("ERROR", "router", "ps_error", error=str(e))
            self.ui.print_error(f"Failed to list agents: {e}")
    
    async def _handle_attach(self, args: list) -> None:
        """Handle /attach command - attach to agent."""
        if not args:
            self.ui.print_error("Usage: /attach <agent_id>")
            return
        
        agent_id = args[0]
        
        try:
            attach_result = await self.app.attach_session(agent_id)
            if not attach_result.ok:
                self.ui.print_error(f"Failed to attach: {attach_result.error.message}")
                return
            
            self.ui.notify(f"Attached to {agent_id}", "success")
            
        except Exception as e:
            log("ERROR", "router", "attach_error", error=str(e))
            self.ui.print_error(f"Failed to attach: {e}")
    
    async def _handle_detach(self, args: list) -> None:
        """Handle /detach command - detach from current agent."""
        try:
            current_session = self.app.get_current_session()
            
            if not current_session:
                self.ui.notify("No active session", "info")
                return
            
            # Hide any active banners
            if self.ui.is_takeover_banner_active():
                self.ui.hide_takeover_banner()
            if self.ui.is_read_only_banner_active():
                self.ui.hide_read_only_banner()
            
            await current_session.detach()
            self.app._current_session = None
            
            self.ui.notify(f"Detached from {current_session.agent_id}", "info")
            
        except Exception as e:
            log("ERROR", "router", "detach_error", error=str(e))
            self.ui.print_error(f"Failed to detach: {e}")
    
    async def _handle_input(self, args: list) -> None:
        """Handle /input command - send input to current agent."""
        if not args:
            self.ui.print_error("Usage: /input <text>")
            return
        
        text = " ".join(args)
        current_session = self.app.get_current_session()
        
        if not current_session:
            self.ui.print_error("No active session. Use /attach first.")
            return
        
        # Check for read-only mode
        if current_session.is_read_only():
            self.ui.print_error("Cannot send input: Session is in read-only mode. Use /detach to disconnect.")
            return
        
        try:
            input_result = await current_session.send_input(text)
            if not input_result.ok:
                self.ui.print_error(f"Failed to send input: {input_result.error.message}")
                return
            
            self.ui.notify("Input sent", "success")
            
        except Exception as e:
            log("ERROR", "router", "input_error", error=str(e))
            self.ui.print_error(f"Failed to send input: {e}")
    
    async def _handle_status(self, args: list) -> None:
        """Handle /status command - show current status."""
        try:
            current_session = self.app.get_current_session()
            
            if current_session:
                status_result = await current_session.get_status()
                if status_result.ok:
                    self.ui.print_session_status(status_result.value)
                else:
                    self.ui.print_error(f"Failed to get status: {status_result.error.message}")
            else:
                self.ui.notify("No active session", "info")
            
        except Exception as e:
            log("ERROR", "router", "status_error", error=str(e))
            self.ui.print_error(f"Failed to get status: {e}")
    
    async def _handle_help(self, args: list) -> None:
        """Handle /help command - show help."""
        self.ui.print_help()
    
    async def _handle_quit(self, args: list) -> None:
        """Handle /quit command - exit console."""
        self.ui.notify("Shutting down...", "info")
        await self.app.shutdown()
        self.app._running = False
    
    async def _handle_ctx(self, args: list) -> None:
        """Handle /ctx command - show context/memory stats."""
        current_session = self.app.get_current_session()
        
        if not current_session:
            self.ui.print_error("No active session. Use /attach first.")
            return
        
        try:
            ctx_result = await current_session.get_context()
            if not ctx_result.ok:
                self.ui.print_error(f"Failed to get context: {ctx_result.error.message}")
                return
            
            ctx_info = ctx_result.value
            print(f"\nContext Information:")
            print(f"===================")
            print(f"Tokens in: {ctx_info.get('tokens_in', 0)}")
            print(f"Tokens out: {ctx_info.get('tokens_out', 0)}")
            print(f"Context %: {ctx_info.get('ctx_pct', 0):.1f}%")
            print(f"History turns: {ctx_info.get('history_turns', 0)}")
            print(f"Queue items: {ctx_info.get('queue_items', 0)}")
            print()
            
        except Exception as e:
            log("ERROR", "router", "ctx_error", error=str(e))
            self.ui.print_error(f"Failed to get context: {e}")
    
    async def _handle_sys(self, args: list) -> None:
        """Handle /sys command - system prompt operations."""
        if not args:
            self.ui.print_error("Usage: /sys <show|edit>")
            return
        
        subcommand = args[0]
        current_session = self.app.get_current_session()
        
        if not current_session:
            self.ui.print_error("No active session. Use /attach first.")
            return
        
        try:
            if subcommand == "show":
                sys_result = await current_session.get_system_prompt()
                if not sys_result.ok:
                    self.ui.print_error(f"Failed to get system prompt: {sys_result.error.message}")
                    return
                
                prompt_data = sys_result.value
                
                print(f"\nSystem Prompt:")
                print(f"==============")
                
                # Show base prompt
                print(f"Base Prompt:")
                print(f"------------")
                print(prompt_data.get("base", "No base prompt"))
                print()
                
                # Show overlay
                overlay_lines = prompt_data.get("overlay_lines", [])
                if overlay_lines:
                    print(f"Overlay Lines:")
                    print(f"--------------")
                    for i, line in enumerate(overlay_lines, 1):
                        print(f"{i}. {line}")
                    print()
                
                # Show effective prompt
                print(f"Effective Prompt:")
                print(f"-----------------")
                print(prompt_data.get("effective", "No effective prompt"))
                print()
                
            elif subcommand == "edit":
                self.ui.print_error("System prompt editing not implemented yet")
                
            else:
                self.ui.print_error(f"Unknown subcommand: {subcommand}")
                
        except Exception as e:
            log("ERROR", "router", "sys_error", error=str(e))
            self.ui.print_error(f"Failed to handle sys command: {e}")

    async def _handle_overlay_line(self, line: str) -> None:
        """Handle # <text> command - add overlay line."""
        current_session = self.app.get_current_session()
        
        if not current_session:
            self.ui.print_error("No active session. Use /attach first.")
            return
        
        if not line.strip():
            self.ui.print_error("Empty overlay line not allowed")
            return
        
        try:
            result = await current_session.append_overlay_line(line)
            if not result.ok:
                self.ui.print_error(f"Failed to add overlay line: {result.error.message}")
                return
            
            self.ui.notify(f"Added overlay line: {line}", "success")
            
        except Exception as e:
            log("ERROR", "router", "overlay_line_error", error=str(e))
            self.ui.print_error(f"Failed to add overlay line: {e}")
    
    async def _handle_reloadsysprompt(self, args: list) -> None:
        """Handle /reloadsysprompt command - reload system prompt."""
        current_session = self.app.get_current_session()
        
        if not current_session:
            self.ui.print_error("No active session. Use /attach first.")
            return
        
        try:
            reload_result = await current_session.reload_system_prompt()
            if not reload_result.ok:
                self.ui.print_error(f"Failed to reload system prompt: {reload_result.error.message}")
                return
            
            self.ui.notify("System prompt reloaded", "success")
            
        except Exception as e:
            log("ERROR", "router", "reloadsysprompt_error", error=str(e))
            self.ui.print_error(f"Failed to reload system prompt: {e}")
    
    async def _handle_clearhistory(self, args: list) -> None:
        """Handle /clearhistory command - clear conversation history with confirmation."""
        current_session = self.app.get_current_session()
        
        if not current_session:
            self.ui.print_error("No active session. Use /attach first.")
            return
        
        try:
            agent_id = current_session.agent_id
            
            # Show warning about destructive action
            self.ui.print_error("⚠️  WARNING: This action is IRREVERSIBLE!")
            self.ui.print_error("This will permanently delete all conversation history and summaries.")
            self.ui.print_error("Type the full agent ID to confirm:")
            self.ui.print_error(f"  {agent_id}")
            
            # Get confirmation from user
            confirmation = await self.ui.read_input("Confirmation: ")
            
            if confirmation.strip() != agent_id:
                self.ui.print_error("Confirmation failed. Agent ID does not match.")
                self.ui.print_error("History was NOT cleared.")
                return
            
            # Clear the history
            result = await current_session.clear_history()
            if not result.ok:
                self.ui.print_error(f"Failed to clear history: {result.error.message}")
                return
            
            self.ui.notify("Conversation history cleared", "success")
            
        except Exception as e:
            log("ERROR", "router", "clearhistory_error", error=str(e))
            self.ui.print_error(f"Failed to clear history: {e}")
    
    async def _handle_kb(self, args: list) -> None:
        """Handle /kb command - show KB help."""
        self.ui.print_help("""
KB Commands:
  /kb add --scope <agent|project|user> <path> [path2...]  - Add files to KB
  /kb search --scope <agent|project|user> <query>        - Search KB
  /kb copy-from <agent_id> --ids <id1,id2...>           - Copy items from agent
  /kb list --scope <agent|project|user>                  - List KB items
        """)

    async def _handle_kb_add(self, args: list) -> None:
        """Handle /kb add command - add files to KB."""
        if len(args) < 2:
            self.ui.print_error("Usage: /kb add --scope <agent|project|user> <path> [path2...]")
            return
        
        # Parse scope
        scope = None
        paths = []
        i = 0
        while i < len(args):
            if args[i] == "--scope" and i + 1 < len(args):
                scope = args[i + 1]
                i += 2
            else:
                paths.append(args[i])
                i += 1
        
        if not scope or scope not in ["agent", "project", "user"]:
            self.ui.print_error("Usage: /kb add --scope <agent|project|user> <path> [path2...]")
            return
        
        if not paths:
            self.ui.print_error("No paths provided")
            return
        
        current_session = self.app.get_current_session()
        if not current_session:
            self.ui.print_error("No active session. Use /attach first.")
            return
        
        try:
            result = await current_session.kb_ingest(paths, scope)
            if not result.ok:
                self.ui.print_error(f"Failed to ingest: {result.error.message}")
                return
            
            self.ui.notify(f"Ingested {len(result.value)} items into {scope} KB", "success")
            
        except Exception as e:
            log("ERROR", "router", "kb_add_error", error=str(e))
            self.ui.print_error(f"Failed to add to KB: {e}")

    async def _handle_kb_search(self, args: list) -> None:
        """Handle /kb search command - search KB."""
        if len(args) < 2:
            self.ui.print_error("Usage: /kb search --scope <agent|project|user> <query>")
            return
        
        # Parse scope
        scope = None
        query = ""
        i = 0
        while i < len(args):
            if args[i] == "--scope" and i + 1 < len(args):
                scope = args[i + 1]
                i += 2
            else:
                query = " ".join(args[i:])
                break
        
        if not scope or scope not in ["agent", "project", "user"]:
            self.ui.print_error("Usage: /kb search --scope <agent|project|user> <query>")
            return
        
        if not query:
            self.ui.print_error("No query provided")
            return
        
        current_session = self.app.get_current_session()
        if not current_session:
            self.ui.print_error("No active session. Use /attach first.")
            return
        
        try:
            result = await current_session.kb_search(query, scope)
            if not result.ok:
                self.ui.print_error(f"Failed to search: {result.error.message}")
                return
            
            hits = result.value
            if not hits:
                self.ui.print_output(f"No results found for '{query}' in {scope} KB")
            else:
                self.ui.print_output(f"Found {len(hits)} results in {scope} KB:")
                for hit in hits:
                    self.ui.print_output(f"  ID: {hit['id']}, Score: {hit['score']:.3f}")
                    if hit.get('metadata', {}).get('title'):
                        self.ui.print_output(f"    Title: {hit['metadata']['title']}")
            
        except Exception as e:
            log("ERROR", "router", "kb_search_error", error=str(e))
            self.ui.print_error(f"Failed to search KB: {e}")

    async def _handle_kb_copy_from(self, args: list) -> None:
        """Handle /kb copy-from command - copy items from another agent."""
        if len(args) < 2:
            self.ui.print_error("Usage: /kb copy-from <agent_id> --ids <id1,id2...>")
            return
        
        # Parse agent_id and ids
        source_agent = args[0]
        ids = []
        i = 1
        while i < len(args):
            if args[i] == "--ids" and i + 1 < len(args):
                ids_str = args[i + 1]
                ids = [id.strip() for id in ids_str.split(",")]
                break
            i += 1
        
        if not ids:
            self.ui.print_error("Usage: /kb copy-from <agent_id> --ids <id1,id2...>")
            return
        
        current_session = self.app.get_current_session()
        if not current_session:
            self.ui.print_error("No active session. Use /attach first.")
            return
        
        try:
            result = await current_session.kb_copy_from(source_agent, ids)
            if not result.ok:
                self.ui.print_error(f"Failed to copy: {result.error.message}")
                return
            
            copied = result.value.get("copied", [])
            skipped = result.value.get("skipped", [])
            
            self.ui.notify(f"Copied {len(copied)} items, skipped {len(skipped)}", "success")
            
        except Exception as e:
            log("ERROR", "router", "kb_copy_error", error=str(e))
            self.ui.print_error(f"Failed to copy from KB: {e}")
    
    async def _handle_ui(self, args: list) -> None:
        """Handle /ui command - UI operations."""
        if not args:
            self.ui.print_error("Usage: /ui <toggle|panes>")
            return
        
        subcommand = args[0]
        
        try:
            if subcommand == "toggle":
                self.app.use_panes = not self.app.use_panes
                self.ui.notify(f"Panes mode: {'on' if self.app.use_panes else 'off'}", "info")
                
            elif subcommand == "panes":
                if len(args) < 2:
                    self.ui.print_error("Usage: /ui panes <on|off>")
                    return
                
                mode = args[1]
                if mode == "on":
                    self.app.use_panes = True
                    self.ui.notify("Panes mode enabled", "info")
                elif mode == "off":
                    self.app.use_panes = False
                    self.ui.notify("Panes mode disabled", "info")
                else:
                    self.ui.print_error("Usage: /ui panes <on|off>")
                    
            else:
                self.ui.print_error(f"Unknown UI subcommand: {subcommand}")
                
        except Exception as e:
            log("ERROR", "router", "ui_error", error=str(e))
            self.ui.print_error(f"Failed to handle UI command: {e}")
    
    async def _handle_agent(self, args: list) -> None:
        """Handle /agent command - agent management."""
        if not args:
            self.ui.print_error("Usage: /agent <new|list|delete>")
            return
        
        subcommand = args[0]
        
        try:
            if subcommand == "new":
                await self._handle_agent_new(args[1:])
            elif subcommand == "list":
                await self._handle_agent_list(args[1:])
            elif subcommand == "delete":
                await self._handle_agent_delete(args[1:])
            else:
                self.ui.print_error(f"Unknown agent subcommand: {subcommand}")
                
        except Exception as e:
            log("ERROR", "router", "agent_error", error=str(e))
            self.ui.print_error(f"Failed to handle agent command: {e}")
    
    async def _handle_agent_new(self, args: list) -> None:
        """Handle /agent new command - create new agent."""
        try:
            from .wizard_create import AgentCreationWizard
            
            wizard = AgentCreationWizard(self.app.redis_url, self.ui)
            result = await wizard.run()
            
            if not result.ok:
                if result.error and result.error.code == "wizard.cancelled":
                    self.ui.notify("Agent creation cancelled", "info")
                else:
                    error_msg = result.error.message if result.error else "Unknown error"
                    self.ui.print_error(f"Failed to create agent: {error_msg}")
                return
            
            agent_id = result.value
            self.ui.notify(f"Agent {agent_id} created successfully!", "success")
            self.ui.notify(f"Use /attach {agent_id} to connect to the new agent.", "info")
            
        except Exception as e:
            log("ERROR", "router", "agent_new_error", error=str(e))
            self.ui.print_error(f"Failed to create agent: {e}")
    
    async def _handle_agent_list(self, args: list) -> None:
        """Handle /agent list command - list agent configurations."""
        try:
            from ..mcp.orchestrator import MCPOrchestratorClient
            
            orchestrator = MCPOrchestratorClient(self.app.redis_url)
            connect_result = await orchestrator.connect()
            if not connect_result.ok:
                self.ui.print_error(f"Failed to connect to orchestrator: {connect_result.error.message}")
                return
            
            try:
                result = await orchestrator.list_agents()
                if not result.ok:
                    self.ui.print_error(f"Failed to list agents: {result.error.message}")
                    return
                
                agents = result.value
                if not agents:
                    self.ui.print_output("No agent configurations found.")
                else:
                    self.ui.print_output("Agent configurations:")
                    for agent in agents:
                        agent_id = agent.get("id", "unknown")
                        project = agent.get("project", "unknown")
                        name = agent.get("name", "unknown")
                        model = agent.get("model", "unknown")
                        cwd = agent.get("cwd", "unknown")
                        self.ui.print_output(f"  {agent_id} (project: {project}, model: {model}, cwd: {cwd})")
                        
            finally:
                await orchestrator.disconnect()
                
        except Exception as e:
            log("ERROR", "router", "agent_list_error", error=str(e))
            self.ui.print_error(f"Failed to list agents: {e}")
    
    async def _handle_agent_delete(self, args: list) -> None:
        """Handle /agent delete command - delete agent configuration."""
        if not args:
            self.ui.print_error("Usage: /agent delete <agent_id>")
            return
        
        agent_id = args[0]
        
        try:
            from ..mcp.orchestrator import MCPOrchestratorClient
            
            # Confirm deletion
            confirm = await self.ui.input(f"Are you sure you want to delete agent '{agent_id}'? (y/n): ").strip().lower()
            if confirm not in ['y', 'yes']:
                self.ui.notify("Agent deletion cancelled", "info")
                return
            
            orchestrator = MCPOrchestratorClient(self.app.redis_url)
            connect_result = await orchestrator.connect()
            if not connect_result.ok:
                self.ui.print_error(f"Failed to connect to orchestrator: {connect_result.error.message}")
                return
            
            try:
                result = await orchestrator.delete_agent(agent_id)
                if not result.ok:
                    self.ui.print_error(f"Failed to delete agent: {result.error.message}")
                    return
                
                self.ui.notify(f"Agent {agent_id} deleted successfully!", "success")
                
            finally:
                await orchestrator.disconnect()
                
        except Exception as e:
            log("ERROR", "router", "agent_delete_error", error=str(e))
            self.ui.print_error(f"Failed to delete agent: {e}")
    
    async def _handle_offload(self, args: list) -> None:
        """Handle /offload command - offload task to new agent."""
        try:
            from .wizard_offload import AgentOffloadWizard
            
            current_session = self.app.get_current_session()
            wizard = AgentOffloadWizard(self.app.redis_url, self.ui, current_session)
            result = await wizard.run()
            
            if not result.ok:
                if result.error and result.error.code == "offload.cancelled":
                    self.ui.notify("Offload cancelled", "info")
                else:
                    error_msg = result.error.message if result.error else "Unknown error"
                    self.ui.print_error(f"Failed to offload task: {error_msg}")
                return
            
            agent_id = result.value
            self.ui.notify(f"Task offloaded to agent {agent_id} successfully!", "success")
            self.ui.notify(f"Use /attach {agent_id} to connect to the new agent.", "info")
            
        except Exception as e:
            log("ERROR", "router", "offload_error", error=str(e))
            self.ui.print_error(f"Failed to offload task: {e}")

    async def _handle_overlay(self, line: str) -> None:
        """Handle # overlay command - add line to system prompt overlay."""
        try:
            current_session = self.app.get_current_session()
            if not current_session:
                self.ui.print_error("No active session. Use /attach first.")
                return
            
            # Extract the overlay line (remove the # prefix)
            overlay_line = line[1:].strip()
            if not overlay_line:
                self.ui.print_error("Empty overlay line not allowed")
                return
            
            # Send overlay command to agent
            result = await current_session.add_overlay(overlay_line)
            if not result.ok:
                self.ui.print_error(f"Failed to add overlay: {result.error.message}")
                return
            
            self.ui.print_output(f"Added overlay: {overlay_line}")
            
        except Exception as e:
            log("ERROR", "router", "overlay_error", error=str(e))
            self.ui.print_error(f"Failed to add overlay: {e}")

    async def _handle_who(self, args: list) -> None:
        """Handle /who command - show current attached agent and ownership."""
        try:
            current_session = self.app.get_current_session()
            if not current_session:
                self.ui.print_output("Not attached to any agent.")
                return
            
            agent_id = current_session.agent_id
            owner_token = current_session.get_ownership_token()
            
            # Get agent status
            status_result = await current_session.get_status()
            if status_result.ok:
                status = status_result.value
                state = status.get("state", "unknown")
                ctx_pct = status.get("ctx_pct", 0.0)
                model = status.get("model", "unknown")
                cwd = status.get("cwd", "unknown")
                
                self.ui.print_output(f"Currently attached to: {agent_id}")
                self.ui.print_output(f"  State: {state}")
                self.ui.print_output(f"  Context: {ctx_pct:.1%}")
                self.ui.print_output(f"  Model: {model}")
                self.ui.print_output(f"  CWD: {cwd}")
                self.ui.print_output(f"  Owner token: {owner_token[:8]}...")
            else:
                self.ui.print_output(f"Currently attached to: {agent_id}")
                self.ui.print_output(f"  Status: Unable to retrieve (error: {status_result.error.message})")
                self.ui.print_output(f"  Owner token: {owner_token[:8]}...")
                
        except Exception as e:
            log("ERROR", "router", "who_error", error=str(e))
            self.ui.print_error(f"Failed to get agent status: {e}")

    async def _handle_interrupt(self, args: list) -> None:
        """Handle /interrupt command - interrupt current task."""
        try:
            current_session = self.app.get_current_session()
            if not current_session:
                self.ui.print_error("No active session. Use /attach first.")
                return
            
            # Send interrupt to agent
            result = await current_session.send_interrupt()
            if result.ok:
                self.ui.notify("Interrupt sent", "info")
            else:
                self.ui.print_error(f"Failed to send interrupt: {result.error.message}")
                
        except Exception as e:
            log("ERROR", "router", "interrupt_error", error=str(e))
            self.ui.print_error(f"Failed to send interrupt: {e}")
