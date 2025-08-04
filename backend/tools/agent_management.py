"""
Agent Management Tools for Zeus Agent

This module provides tool functions that allow the Zeus agent to manage other agents
in the ATeam system. These tools use the global manager registry to access the
agent manager and provide comprehensive agent management capabilities.
"""

from typing import Dict, List, Any, Optional, Union
from objects_registry import agent_manager
from schemas import AgentConfig


def get_all_agents() -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """
    Get all agents in the system.
    
    Returns:
        Union[List[Dict[str, Any]], Dict[str, str]]: List of all agent configurations as dictionaries,
        or error dict if failed.
        Each agent dict contains: id, name, description, model, prompts, tools, 
        schema_file, grammar_file, temperature, max_tokens, enable_summarization, 
        enable_scratchpad, created_at, updated_at
    """
    try:
        agent_configs = agent_manager().get_all_agent_configs()
        return [agent.model_dump() for agent in agent_configs]
    except Exception as e:
        return {"error": f"Failed to get agents: {str(e)}"}


def get_agent_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Get an agent by its name.
    
    Args:
        name (str): The name of the agent to retrieve.
        
    Returns:
        Optional[Dict[str, Any]]: Agent configuration as a dictionary if found, 
        None if not found, or error dict if error occurs.
        Contains: id, name, description, model, prompts, tools, schema_file, 
        grammar_file, temperature, max_tokens, enable_summarization, 
        enable_scratchpad, created_at, updated_at
    """
    try:
        agent_config = agent_manager().get_agent_by_name(name)
        if agent_config:
            return agent_config.model_dump()
        return None
    except Exception as e:
        return {"error": f"Failed to get agent by name: {str(e)}"}


def create_agent(
    name: str,
    description: str,
    model: str,
    prompts: Optional[List[str]] = None,
    tools: Optional[List[str]] = None,
    schema_file: Optional[str] = None,
    grammar_file: Optional[str] = None,
    temperature: float = 0.5,
    max_tokens: Optional[int] = None,
    enable_summarization: bool = True,
    enable_scratchpad: bool = True
) -> Dict[str, Any]:
    """
    Create a new agent with the specified configuration.
    
    Args:
        name (str): The name of the agent.
        description (str): A description of the agent's purpose and capabilities.
        model (str): The LLM model ID to use for this agent.
        prompts (Optional[List[str]]): List of prompt names to assign to the agent.
        tools (Optional[List[str]]): List of tool names to assign to the agent.
        schema_file (Optional[str]): Path to JSON schema file for structured outputs.
        grammar_file (Optional[str]): Path to grammar file for constrained outputs.
        temperature (float): Temperature setting for the LLM (0.0 to 2.0).
        max_tokens (Optional[int]): Maximum tokens for LLM responses.
        enable_summarization (bool): Whether to enable conversation summarization.
        enable_scratchpad (bool): Whether to enable scratchpad functionality.
        
    Returns:
        Dict[str, Any]: Result containing the new agent ID if successful, 
        or error dict if failed.
        Success: {"agent_id": "uuid-string", "message": "Agent created successfully"}
        Error: {"error": "error message"}
    """
    try:
        import uuid
        
        # Generate unique ID
        agent_id = str(uuid.uuid4())
        
        # Create the agent configuration
        agent_config = AgentConfig(
            id=agent_id,
            name=name,
            description=description,
            model=model,
            prompts=prompts or [],
            tools=tools or [],
            schema_file=schema_file,
            grammar_file=grammar_file,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_summarization=enable_summarization,
            enable_scratchpad=enable_scratchpad
        )
        
        # Add the agent
        agent_manager().add_agent(agent_config)
        
        return {
            "agent_id": agent_id,
            "message": f"Agent '{name}' created successfully with ID: {agent_id}"
        }
    except Exception as e:
        return {"error": f"Failed to create agent: {str(e)}"}


def update_agent(
    agent_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    model: Optional[str] = None,
    prompts: Optional[List[str]] = None,
    tools: Optional[List[str]] = None,
    schema_file: Optional[str] = None,
    grammar_file: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    enable_summarization: Optional[bool] = None,
    enable_scratchpad: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Update an existing agent's configuration.
    
    Args:
        agent_id (str): The unique identifier of the agent to update.
        name (Optional[str]): New name for the agent.
        description (Optional[str]): New description for the agent.
        model (Optional[str]): New LLM model ID for the agent.
        prompts (Optional[List[str]]): New list of prompt names for the agent.
        tools (Optional[List[str]]): New list of tool names for the agent.
        schema_file (Optional[str]): New path to JSON schema file.
        grammar_file (Optional[str]): New path to grammar file.
        temperature (Optional[float]): New temperature setting (0.0 to 2.0).
        max_tokens (Optional[int]): New maximum tokens setting.
        enable_summarization (Optional[bool]): New summarization setting.
        enable_scratchpad (Optional[bool]): New scratchpad setting.
        
    Returns:
        Dict[str, Any]: Result indicating success or failure.
        Success: {"message": "Agent updated successfully"}
        Error: {"error": "error message"}
    """
    try:
        # Build update data dict with only provided values
        update_data = {}
        if name is not None:
            update_data['name'] = name
        if description is not None:
            update_data['description'] = description
        if model is not None:
            update_data['model'] = model
        if prompts is not None:
            update_data['prompts'] = prompts
        if tools is not None:
            update_data['tools'] = tools
        if schema_file is not None:
            update_data['schema_file'] = schema_file
        if grammar_file is not None:
            update_data['grammar_file'] = grammar_file
        if temperature is not None:
            update_data['temperature'] = temperature
        if max_tokens is not None:
            update_data['max_tokens'] = max_tokens
        if enable_summarization is not None:
            update_data['enable_summarization'] = enable_summarization
        if enable_scratchpad is not None:
            update_data['enable_scratchpad'] = enable_scratchpad
        
        # Get existing agent config
        existing_agent = agent_manager().get_agent_config(agent_id)
        
        # Update the fields
        for key, value in update_data.items():
            if hasattr(existing_agent, key):
                setattr(existing_agent, key, value)
        
        # Update the agent
        agent_manager().update_agent(existing_agent)
        
        return {"message": f"Agent '{agent_id}' updated successfully"}
    except ValueError as e:
        return {"error": f"Agent not found: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to update agent: {str(e)}"}

