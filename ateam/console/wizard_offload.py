"""
Agent Offload Wizard

Handles the /offload command with fail-fast validation and mandatory confirmations.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..mcp.orchestrator import MCPOrchestratorClient, LocalAgentSpawner
from ..util.types import Result, ErrorInfo
from ..config.loader import load_stack


class WizardCancelledException(Exception):
    """Exception raised when user cancels the wizard."""
    pass


class AgentOffloadWizard:
    """Wizard for offloading tasks to new agents with fail-fast validation."""
    
    def __init__(self, redis_url: str, ui, current_session):
        self.redis_url = redis_url
        self.ui = ui
        self.current_session = current_session
        self.orchestrator: MCPOrchestratorClient = None  # type: ignore
    
    async def run(self) -> Result[str]:
        """
        Run the agent offload wizard.
        
        Returns:
            Result with agent_id on success
        """
        try:
            # Check if we have a current session
            if not self.current_session:
                return Result(ok=False, error=ErrorInfo(
                    code="offload.no_session",
                    message="No active agent session. Use /attach first."
                ))
            
            # Connect to orchestrator
            self.orchestrator = MCPOrchestratorClient(self.redis_url)
            connect_result = await self.orchestrator.connect()
            if not connect_result.ok:
                return connect_result
            
            # Step 1: Get current context
            context = await self._get_current_context()
            if not context:
                return Result(ok=False, error=ErrorInfo(
                    code="offload.no_context",
                    message="No context available for offloading"
                ))
            
            # Step 2: Get project name
            project = self._get_project_name()
            if not project:
                return Result(ok=False, error=ErrorInfo(
                    code="offload.cancelled",
                    message="Offload cancelled"
                ))
            
            # Step 3: Get agent name
            name = self._get_agent_name(project)
            if not name:
                return Result(ok=False, error=ErrorInfo(
                    code="offload.cancelled",
                    message="Offload cancelled"
                ))
            
            # Step 4: Get working directory
            cwd = self._get_working_directory()
            if not cwd:
                return Result(ok=False, error=ErrorInfo(
                    code="offload.cancelled",
                    message="Offload cancelled"
                ))
            
            # Step 5: Select model
            model = self._select_model()
            if not model:
                return Result(ok=False, error=ErrorInfo(
                    code="offload.cancelled",
                    message="Offload cancelled"
                ))
            
            # Step 6: Select KB documents to copy
            kb_seeds = await self._select_kb_documents()
            
            # Step 7: Show summary and confirm
            agent_id = f"{project}/{name}"
            confirmed = self._confirm_offload(
                agent_id, project, name, cwd, model, context, kb_seeds
            )
            
            if not confirmed:
                return Result(ok=False, error=ErrorInfo(
                    code="offload.cancelled",
                    message="Offload cancelled"
                ))
            
            # Step 8: Create agent
            self.ui.notify(f"Creating agent {agent_id}...")
            create_result = await self.orchestrator.create_agent(
                project=project,
                name=name,
                cwd=cwd,
                model=model,
                system_base=None,  # Use default
                kb_seeds=kb_seeds
            )
            
            if not create_result.ok:
                return create_result
            
            # Step 9: Spawn agent
            self.ui.notify(f"Spawning agent {agent_id}...")
            spawn_result = await self.orchestrator.spawn_agent(agent_id)
            
            if not spawn_result.ok:
                return spawn_result
            
            self.ui.notify(f"Agent {agent_id} created and spawned successfully!")
            self.ui.notify(f"Use /attach {agent_id} to connect to the new agent.")
            return Result(ok=True, value=agent_id)
            
        except Exception as e:
            return Result(ok=False, error=ErrorInfo(
                code="offload.error",
                message=f"Offload error: {e}"
            ))
        finally:
            if self.orchestrator:
                await self.orchestrator.disconnect()
    
    async def _get_current_context(self) -> Optional[str]:
        """Get current context from the active session."""
        try:
            # Get the current context from the session
            context_result = await self.current_session.get_context()
            if not context_result.ok:
                self.ui.print(f"Warning: Could not get context: {context_result.error.message if context_result.error else 'Unknown error'}")
                return None
            
            context = context_result.value
            if not context:
                self.ui.print("No context available.")
                return None
            
            return context
            
        except Exception as e:
            self.ui.print(f"Error getting context: {e}")
            return None
    
    def _get_project_name(self) -> str:
        """Get project name from user."""
        self.ui.print("=== Agent Offload Wizard ===")
        self.ui.print("Step 1: Project Name")
        self.ui.print("Enter the project name for the new agent:")
        
        while True:
            project = self.ui.input("Project name: ").strip()
            
            if not project:
                self.ui.print("Project name cannot be empty.")
                continue
            
            if not project.replace("-", "").replace("_", "").isalnum():
                self.ui.print("Project name must contain only letters, numbers, hyphens, and underscores.")
                continue
            
            # Check if user wants to cancel
            confirm = self.ui.input(f"Use project '{project}'? (y/n): ").strip().lower()
            if confirm in ['y', 'yes']:
                return project
            elif confirm in ['n', 'no']:
                continue
            else:
                self.ui.print("Please enter 'y' or 'n'.")
    
    def _get_agent_name(self, project: str) -> str:
        """Get agent name from user."""
        self.ui.print(f"\nStep 2: Agent Name (for project '{project}')")
        self.ui.print("Enter the agent name (e.g., 'builder', 'researcher'):")
        
        while True:
            name = self.ui.input("Agent name: ").strip()
            
            if not name:
                self.ui.print("Agent name cannot be empty.")
                continue
            
            if not name.replace("-", "").replace("_", "").isalnum():
                self.ui.print("Agent name must contain only letters, numbers, hyphens, and underscores.")
                continue
            
            agent_id = f"{project}/{name}"
            
            # Check if user wants to cancel
            confirm = self.ui.input(f"Use agent name '{name}' (full ID: {agent_id})? (y/n): ").strip().lower()
            if confirm in ['y', 'yes']:
                return name
            elif confirm in ['n', 'no']:
                continue
            else:
                self.ui.print("Please enter 'y' or 'n'.")
    
    def _get_working_directory(self) -> str:
        """Get working directory from user."""
        self.ui.print(f"\nStep 3: Working Directory")
        self.ui.print("Enter the working directory for the new agent:")
        
        while True:
            cwd = self.ui.input("Working directory: ").strip()
            
            if not cwd:
                self.ui.print("Working directory cannot be empty.")
                continue
            
            # Expand user path if needed
            cwd = os.path.expanduser(cwd)
            
            # Check if directory exists
            if not os.path.exists(cwd):
                create = self.ui.input(f"Directory '{cwd}' does not exist. Create it? (y/n): ").strip().lower()
                if create in ['y', 'yes']:
                    try:
                        os.makedirs(cwd, exist_ok=True)
                    except Exception as e:
                        self.ui.print(f"Failed to create directory: {e}")
                        continue
                else:
                    continue
            
            if not os.path.isdir(cwd):
                self.ui.print("Path must be a directory.")
                continue
            
            # Check if user wants to cancel
            confirm = self.ui.input(f"Use working directory '{cwd}'? (y/n): ").strip().lower()
            if confirm in ['y', 'yes']:
                return cwd
            elif confirm in ['n', 'no']:
                continue
            else:
                self.ui.print("Please enter 'y' or 'n'.")
    
    def _select_model(self) -> str:
        """Select model from available models."""
        self.ui.print(f"\nStep 4: Model Selection")
        
        # Load available models
        try:
            config_result = load_stack(os.getcwd())
            if not config_result.ok:
                if config_result.error:
                    self.ui.print(f"Error loading config: {config_result.error.message}")
                else:
                    self.ui.print("Error loading config: Unknown error")
                return None
            
            if config_result.value is None:
                self.ui.print("No config found")
                return None
            
            _, models_config, _, _ = config_result.value
            models = models_config.dict()
            
            if not models:
                self.ui.print("No models configured. Please configure models first.")
                return None
            
            self.ui.print("Available models:")
            model_list = list(models.keys())
            for i, model_id in enumerate(model_list, 1):
                model_config = models[model_id]
                provider = model_config.get("provider", "unknown")
                self.ui.print(f"  {i}. {model_id} ({provider})")
            
            while True:
                choice = self.ui.input(f"Select model (1-{len(model_list)}): ").strip()
                
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(model_list):
                        model_id = model_list[index]
                        confirm = self.ui.input(f"Use model '{model_id}'? (y/n): ").strip().lower()
                        if confirm in ['y', 'yes']:
                            return model_id
                        elif confirm in ['n', 'no']:
                            continue
                        else:
                            self.ui.print("Please enter 'y' or 'n'.")
                    else:
                        self.ui.print(f"Please enter a number between 1 and {len(model_list)}.")
                except ValueError:
                    self.ui.print("Please enter a valid number.")
                    
        except Exception as e:
            self.ui.print(f"Error loading models: {e}")
            return None
    
    async def _select_kb_documents(self) -> List[str]:
        """Select KB documents to copy to the new agent."""
        self.ui.print(f"\nStep 5: Knowledge Base Documents (Optional)")
        self.ui.print("Select KB documents to copy to the new agent:")
        
        try:
            # Get available KB documents from current session
            kb_result = await self.current_session.search_kb("", scope="agent")
            if not kb_result.ok or not kb_result.value:
                self.ui.print("No KB documents available to copy.")
                return []
            
            documents = kb_result.value
            if not documents:
                self.ui.print("No KB documents available to copy.")
                return []
            
            self.ui.print("Available KB documents:")
            for i, doc in enumerate(documents, 1):
                doc_id = doc.get("id", "unknown")
                metadata = doc.get("metadata", {})
                title = metadata.get("title", "Untitled")
                self.ui.print(f"  {i}. {doc_id} - {title}")
            
            while True:
                choice_input = self.ui.input("Select documents (comma-separated numbers, or 'all'): ").strip()
                
                if choice_input.lower() == 'all':
                    selected_docs = documents
                else:
                    try:
                        indices = [int(x.strip()) - 1 for x in choice_input.split(",")]
                        selected_docs = [documents[i] for i in indices if 0 <= i < len(documents)]
                    except (ValueError, IndexError):
                        self.ui.print("Invalid selection. Please enter valid numbers.")
                        continue
                
                if not selected_docs:
                    self.ui.print("No documents selected.")
                    continue
                
                doc_ids = [doc.get("id") for doc in selected_docs if doc.get("id")]
                
                # Check if user wants to cancel
                confirm = self.ui.input(f"Copy {len(doc_ids)} documents? (y/n): ").strip().lower()
                if confirm in ['y', 'yes']:
                    return doc_ids
                elif confirm in ['n', 'no']:
                    continue
                else:
                    self.ui.print("Please enter 'y' or 'n'.")
                    
        except Exception as e:
            self.ui.print(f"Error selecting KB documents: {e}")
            return []
    
    def _confirm_offload(self, agent_id: str, project: str, name: str, 
                        cwd: str, model: str, context: str, 
                        kb_seeds: List[str]) -> bool:
        """Show summary and get final confirmation."""
        self.ui.print(f"\n=== Agent Offload Summary ===")
        self.ui.print(f"New Agent ID: {agent_id}")
        self.ui.print(f"Project: {project}")
        self.ui.print(f"Name: {name}")
        self.ui.print(f"Working Directory: {cwd}")
        self.ui.print(f"Model: {model}")
        self.ui.print(f"Context Length: {len(context)} characters")
        self.ui.print(f"KB Documents to Copy: {len(kb_seeds)}")
        if kb_seeds:
            self.ui.print(f"  - {', '.join(kb_seeds)}")
        self.ui.print()
        
        # Show a preview of the context
        preview = context[:200] + "..." if len(context) > 200 else context
        self.ui.print(f"Context Preview: {preview}")
        self.ui.print()
        
        while True:
            confirm = self.ui.input("Create this agent and offload the task? (y/n): ").strip().lower()
            if confirm in ['y', 'yes']:
                return True
            elif confirm in ['n', 'no']:
                return False
            else:
                self.ui.print("Please enter 'y' or 'n'.")

