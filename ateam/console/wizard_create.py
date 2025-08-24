"""
Agent Creation Wizard

Handles the /agent new command with fail-fast validation and mandatory confirmations.
"""

import os
from pathlib import Path
from typing import Optional, List

from ..mcp.orchestrator import MCPOrchestratorClient, LocalAgentSpawner
from ..util.types import Result, ErrorInfo
from ..config.loader import load_stack


class WizardCancelledException(Exception):
    """Exception raised when user cancels the wizard."""
    pass


class AgentCreationWizard:
    """Wizard for creating new agents with fail-fast validation."""
    
    def __init__(self, redis_url: str, ui):
        self.redis_url = redis_url
        self.ui = ui
        self.orchestrator: MCPOrchestratorClient = None  # type: ignore
    
    async def run(self) -> Result[str]:
        """
        Run the agent creation wizard.
        
        Returns:
            Result with agent_id on success
        """
        try:
            # Connect to orchestrator
            self.orchestrator = MCPOrchestratorClient(self.redis_url)
            connect_result = await self.orchestrator.connect()
            if not connect_result.ok:
                return connect_result
            
            # Step 1: Get project name
            project = self._get_project_name()
            if not project:
                return Result(ok=False, error=ErrorInfo(
                    code="wizard.cancelled",
                    message="Agent creation cancelled"
                ))
            
            # Step 2: Get agent name
            name = self._get_agent_name(project)
            if not name:
                return Result(ok=False, error=ErrorInfo(
                    code="wizard.cancelled",
                    message="Agent creation cancelled"
                ))
            
            # Step 3: Get working directory
            cwd = self._get_working_directory()
            if not cwd:
                return Result(ok=False, error=ErrorInfo(
                    code="wizard.cancelled",
                    message="Agent creation cancelled"
                ))
            
            # Step 4: Select model
            model = self._select_model()
            if not model:
                return Result(ok=False, error=ErrorInfo(
                    code="wizard.cancelled",
                    message="Agent creation cancelled"
                ))
            
            # Step 5: Get system base prompt
            system_base = self._get_system_base()
            
            # Step 6: Get KB seeds
            kb_seeds = self._get_kb_seeds()
            
            # Step 7: Show summary and confirm
            agent_id = f"{project}/{name}"
            confirmed = self._confirm_creation(
                agent_id, project, name, cwd, model, system_base, kb_seeds
            )
            
            if not confirmed:
                return Result(ok=False, error=ErrorInfo(
                    code="wizard.cancelled",
                    message="Agent creation cancelled"
                ))
            
            # Step 8: Create agent
            self.ui.notify(f"Creating agent {agent_id}...")
            create_result = await self.orchestrator.create_agent(
                project=project,
                name=name,
                cwd=cwd,
                model=model,
                system_base=system_base,
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
            return Result(ok=True, value=agent_id)
            
        except WizardCancelledException:
            return Result(ok=False, error=ErrorInfo(
                code="wizard.cancelled",
                message="Agent creation cancelled"
            ))
        except Exception as e:
            return Result(ok=False, error=ErrorInfo(
                code="wizard.error",
                message=f"Wizard error: {e}"
            ))
        finally:
            if self.orchestrator:
                await self.orchestrator.disconnect()
    
    def _get_project_name(self) -> str:
        """Get project name from user."""
        self.ui.print("=== Agent Creation Wizard ===")
        self.ui.print("Step 1: Project Name")
        self.ui.print("Enter the project name (e.g., 'myproj'):")
        
        while True:
            project_input = self.ui.input("Project name: ")
            project = project_input.strip()
            
            if not project:
                self.ui.print("Project name cannot be empty.")
                continue
            
            if not project.replace("-", "").replace("_", "").isalnum():
                self.ui.print("Project name must contain only letters, numbers, hyphens, and underscores.")
                continue
            
            # Check if user wants to cancel
            confirm_input = self.ui.input(f"Use project '{project}'? (y/n): ")
            confirm = confirm_input.strip().lower()
            if confirm in ['y', 'yes']:
                return project
            elif confirm in ['n', 'no']:
                raise WizardCancelledException("User cancelled project name input")
            else:
                self.ui.print("Please enter 'y' or 'n'.")
    
    def _get_agent_name(self, project: str) -> str:
        """Get agent name from user."""
        self.ui.print(f"\nStep 2: Agent Name (for project '{project}')")
        self.ui.print("Enter the agent name (e.g., 'zeus', 'builder'):")
        
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
                raise Exception("User cancelled agent name input")
            else:
                self.ui.print("Please enter 'y' or 'n'.")
    
    def _get_working_directory(self) -> Optional[str]:
        """Get working directory from user."""
        self.ui.print(f"\nStep 3: Working Directory")
        self.ui.print("Enter the working directory for the agent:")
        
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
                raise Exception("User cancelled working directory input")
            else:
                self.ui.print("Please enter 'y' or 'n'.")
    
    def _select_model(self) -> Optional[str]:
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
    
    def _get_system_base(self) -> Optional[str]:
        """Get system base prompt file path."""
        self.ui.print(f"\nStep 5: System Base Prompt (Optional)")
        self.ui.print("Enter the path to a system base prompt file (or press Enter to skip):")
        
        while True:
            path = self.ui.input("System base file: ").strip()
            
            if not path:
                self.ui.print("Skipping system base prompt.")
                return None
            
            # Expand user path if needed
            path = os.path.expanduser(path)
            
            if not os.path.exists(path):
                self.ui.print(f"File '{path}' does not exist.")
                continue
            
            if not os.path.isfile(path):
                self.ui.print("Path must be a file.")
                continue
            
            # Check if user wants to cancel
            confirm = self.ui.input(f"Use system base file '{path}'? (y/n): ").strip().lower()
            if confirm in ['y', 'yes']:
                return path
            elif confirm in ['n', 'no']:
                continue
            else:
                self.ui.print("Please enter 'y' or 'n'.")
    
    def _get_kb_seeds(self) -> List[str]:
        """Get KB seed document IDs."""
        self.ui.print(f"\nStep 6: Knowledge Base Seeds (Optional)")
        self.ui.print("Enter comma-separated KB document IDs to copy (or press Enter to skip):")
        
        while True:
            seeds_input = self.ui.input("KB seeds: ").strip()
            
            if not seeds_input:
                self.ui.print("No KB seeds specified.")
                return []
            
            seeds = [seed.strip() for seed in seeds_input.split(",") if seed.strip()]
            
            if not seeds:
                self.ui.print("No valid seeds found.")
                continue
            
            # Check if user wants to cancel
            confirm = self.ui.input(f"Use KB seeds: {', '.join(seeds)}? (y/n): ").strip().lower()
            if confirm in ['y', 'yes']:
                return seeds
            elif confirm in ['n', 'no']:
                continue
            else:
                self.ui.print("Please enter 'y' or 'n'.")
    
    def _confirm_creation(self, agent_id: str, project: str, name: str, 
                         cwd: str, model: str, system_base: Optional[str], 
                         kb_seeds: List[str]) -> bool:
        """Show summary and get final confirmation."""
        self.ui.print(f"\n=== Agent Creation Summary ===")
        self.ui.print(f"Agent ID: {agent_id}")
        self.ui.print(f"Project: {project}")
        self.ui.print(f"Name: {name}")
        self.ui.print(f"Working Directory: {cwd}")
        self.ui.print(f"Model: {model}")
        self.ui.print(f"System Base: {system_base or 'None'}")
        self.ui.print(f"KB Seeds: {', '.join(kb_seeds) if kb_seeds else 'None'}")
        self.ui.print()
        
        while True:
            confirm = self.ui.input("Create this agent? (y/n): ").strip().lower()
            if confirm in ['y', 'yes']:
                return True
            elif confirm in ['n', 'no']:
                return False
            else:
                self.ui.print("Please enter 'y' or 'n'.")
