"""
Global manager registry for the ATeam application.
Provides centralized access to all manager instances.
"""

from agent_manager import AgentManager
from tool_manager import ToolManager
from prompt_manager import PromptManager
from provider_manager import ProviderManager
from models_manager import ModelsManager
from schema_manager import SchemaManager
from notification_manager import NotificationManager
from frontend_api import FrontendAPI

# Global manager instances
_agent_manager: AgentManager | None = None
_tool_manager: ToolManager | None = None
_prompt_manager: PromptManager | None = None
_provider_manager: ProviderManager | None = None
_models_manager: ModelsManager | None = None
_schema_manager: SchemaManager | None = None
_notification_manager: NotificationManager | None = None
_frontend_api: FrontendAPI | None = None

def initialize_managers():
    """Initialize all global manager instances"""
    global _agent_manager, _tool_manager, _prompt_manager, _provider_manager, _models_manager, _schema_manager, _notification_manager, _frontend_api
    
    # Initialize managers in dependency order
    _tool_manager = ToolManager("tools")
    _agent_manager = AgentManager("agents.yaml")
    _prompt_manager = PromptManager("prompts")
    _provider_manager = ProviderManager("providers.yaml")
    _models_manager = ModelsManager("models.yaml")
    _schema_manager = SchemaManager("schemas")
    _notification_manager = NotificationManager()
    _frontend_api = FrontendAPI()

def get_agent_manager() -> AgentManager:
    """Get the global agent manager instance"""
    if _agent_manager is None:
        raise RuntimeError("Managers not initialized. Call initialize_managers() first.")
    return _agent_manager

def get_tool_manager() -> ToolManager:
    """Get the global tool manager instance"""
    if _tool_manager is None:
        raise RuntimeError("Managers not initialized. Call initialize_managers() first.")
    return _tool_manager

def get_prompt_manager() -> PromptManager:
    """Get the global prompt manager instance"""
    if _prompt_manager is None:
        raise RuntimeError("Managers not initialized. Call initialize_managers() first.")
    return _prompt_manager

def get_provider_manager() -> ProviderManager:
    """Get the global provider manager instance"""
    if _provider_manager is None:
        raise RuntimeError("Managers not initialized. Call initialize_managers() first.")
    return _provider_manager

def get_models_manager() -> ModelsManager:
    """Get the global models manager instance"""
    if _models_manager is None:
        raise RuntimeError("Managers not initialized. Call initialize_managers() first.")
    return _models_manager

def get_schema_manager() -> SchemaManager:
    """Get the global schema manager instance"""
    if _schema_manager is None:
        raise RuntimeError("Managers not initialized. Call initialize_managers() first.")
    return _schema_manager

def get_notification_manager() -> NotificationManager:
    """Get the global notification manager instance"""
    if _notification_manager is None:
        raise RuntimeError("Managers not initialized. Call initialize_managers() first.")
    return _notification_manager

def get_frontend_api() -> FrontendAPI:
    """Get the global frontend API instance"""
    if _frontend_api is None:
        raise RuntimeError("Managers not initialized. Call initialize_managers() first.")
    return _frontend_api

# Convenience aliases for direct use - always get current instances
agent_manager = get_agent_manager
tool_manager = get_tool_manager
prompt_manager = get_prompt_manager
provider_manager = get_provider_manager
models_manager = get_models_manager
schema_manager = get_schema_manager
notification_manager = get_notification_manager
frontend_api = get_frontend_api 