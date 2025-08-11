import yaml
import os
import random
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import json

from schemas import AgentConfig
from agent import Agent
from notification_utils import log_error, log_warning, log_info

class AgentManager:
    def __init__(self, config_path: str = "agents.yaml"):
        self.config_path = config_path
        self.agents_config: dict[str, AgentConfig] = {}
        self.agent_instances: dict[str, Agent] = {}  # Lazy-loaded agent instances
        self.session_to_agent: Dict[str, Agent] = {}  # session_id -> agent_instance
        self.agent_to_sessions: Dict[str, List[str]] = {}  # agent_id -> [session_ids]
        self.load_agents()
        
    def load_agents(self):
        """Load agents from YAML configuration file"""
        if not os.path.exists(self.config_path):
            log_warning("AgentManager", f"Agents configuration file {self.config_path} not found", {"config_path": self.config_path})
            return
            
        with open(self.config_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            
            if data is None:
                raise RuntimeError(f'Failed to read (returned None) agents.yaml at: {self.config_path}')
            
            if 'agents' not in data:
                raise RuntimeError(f'Malformed agents.yaml at: {self.config_path}.\nagents.yaml:\n{data}')
            
            for agent_data in data['agents']:
                # Enforce mandatory prompt/tools
                prompts = agent_data.get('prompts') or []
                if 'all_agents.md' not in prompts:
                    prompts = ['all_agents.md'] + [p for p in prompts if p != 'all_agents.md']
                agent_data['prompts'] = prompts

                tools = agent_data.get('tools') or []
                mandatory_tools = [
                    'kb_add', 'kb_update', 'kb_get', 'kb_list', 'kb_search',
                    'plan_read', 'plan_write', 'plan_append', 'plan_delete', 'plan_list',
                ]
                for t in mandatory_tools:
                    if t not in tools:
                        tools.append(t)
                agent_data['tools'] = tools

                agent = AgentConfig(**agent_data)
                self.agents_config[agent.id] = agent
    
    def save_agents(self):
        """Save agents to YAML configuration file"""
        # Only create directory if there's a directory path (not empty)
        dir_path = os.path.dirname(self.config_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        data = {
            "agents": [agent.model_dump() for agent in self.agents_config.values()]
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as file:
            yaml.dump(data, file, default_flow_style=False, indent=2)
    
    def get_all_agent_configs(self) -> List[AgentConfig]:
        """Get all agent configurations as AgentConfig objects"""
        return list(self.agents_config.values())
    
    def get_agent_config(self, agent_id: str) -> AgentConfig:
        """Get a specific agent configuration by ID"""
        if agent_id not in self.agents_config:
            raise ValueError(f'Agent {agent_id} not found')
        
        return self.agents_config[agent_id]
    
    def get_agent(self, agent_id: str) -> Agent:
        """Get an agent instance with lazy loading"""
        
        # Return cached instance if available
        if agent_id in self.agent_instances:
            return self.agent_instances[agent_id]
        
        # Check if agent exists
        agent_config = self.get_agent_config(agent_id)

        # Create new instance
        agent_instance = Agent(agent_config)
        self.agent_instances[agent_id] = agent_instance
        return agent_instance
    
    def clear_agent_instance(self, agent_id: str) -> None:
        """Clear a cached agent instance"""
        if agent_id in self.agent_instances:
            del self.agent_instances[agent_id]
    
    def clear_all_agent_instances(self) -> None:
        """Clear all cached agent instances"""
        self.agent_instances.clear()
    
    def add_agent(self, agent_config: AgentConfig) -> None:
        """Add a new agent with the provided configuration"""
        # Verify agent ID doesn't already exist
        if agent_config.id in self.agents_config:
            raise ValueError(f"Agent with ID '{agent_config.id}' already exists")
        
        # Set timestamps if not provided
        if not agent_config.created_at:
            agent_config.created_at = datetime.now().isoformat()
        if not agent_config.updated_at:
            agent_config.updated_at = datetime.now().isoformat()
        
        # Add to configuration
        self.agents_config[agent_config.id] = agent_config
        
        # Save to YAML file
        self.save_agents()
    
    def update_agent(self, agent_config: AgentConfig) -> None:
        """Update an existing agent with the provided configuration"""
        # Verify agent exists
        if agent_config.id not in self.agents_config:
            raise ValueError(f"Agent '{agent_config.id}' not found")
        
        # Enforce mandatory prompt/tools on update as well
        if 'all_agents.md' not in agent_config.prompts:
            agent_config.prompts = ['all_agents.md'] + [p for p in agent_config.prompts if p != 'all_agents.md']
        mandatory_tools = [
            'kb_add', 'kb_update', 'kb_get', 'kb_list', 'kb_search',
            'plan_read', 'plan_write', 'plan_append', 'plan_delete', 'plan_list',
        ]
        for t in mandatory_tools:
            if t not in agent_config.tools:
                agent_config.tools.append(t)

        # Update timestamp
        agent_config.updated_at = datetime.now().isoformat()
        
        # Update configuration
        self.agents_config[agent_config.id] = agent_config
        
        # Clear cached instance since configuration changed
        self.clear_agent_instance(agent_config.id)
        
        # Save to YAML file
        self.save_agents()
    
    def delete_agent(self, agent_id: str) -> None:
        """Delete an agent"""
        if agent_id not in self.agents_config:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        # Clear cached instance
        self.clear_agent_instance(agent_id)
        
        del self.agents_config[agent_id]
        
        # Save to YAML file
        self.save_agents()
    
    def get_agent_by_name(self, name: str) -> Optional[AgentConfig]:
        """Get an agent configuration by name"""
        for agent in self.agents_config.values():
            if agent.name == name:
                return agent
        return None
    
    def search_agents(self, query: str) -> List[AgentConfig]:
        """Search agents by name or description"""
        query = query.lower()
        results = []
        
        for agent in self.agents_config.values():
            if (query in agent.name.lower() or 
                query in agent.description.lower()):
                results.append(agent)
        
        return results
    
    def get_agents_by_model(self, model: str) -> List[AgentConfig]:
        """Get all agents using a specific model"""
        return [agent for agent in self.agents_config.values() if agent.model == model]
    
    def get_agents_by_tool(self, tool_name: str) -> List[AgentConfig]:
        """Get all agents that have a specific tool"""
        return [agent for agent in self.agents_config.values() if tool_name in agent.tools]
    
    def validate_agent(self, agent_id: str) -> bool:
        """Validate if an agent can be used"""
        agent = self.get_agent_config(agent_id)
        if not agent:
            return False
        
        # Check if model exists (this would typically check against available models)
        # For now, we'll just check if the model field is not empty
        if not agent.model:
            return False
        
        return True
    
    def create_agent_session(self, agent_id: str) -> str:
        """Create a new session for an agent and return session_id"""
        # Verify agent exists
        agent_config = self.get_agent_config(agent_id)
        
        # Generate session ID: [agent_name]_XXX
        session_id = f"{agent_config.name}_{random.randint(100, 999)}"
        
        # Create agent instance if not exists
        agent_instance = self.get_agent(agent_id)
        
        # Store session mapping
        self.session_to_agent[session_id] = agent_instance
        
        # Track sessions per agent
        if agent_id not in self.agent_to_sessions:
            self.agent_to_sessions[agent_id] = []
        self.agent_to_sessions[agent_id].append(session_id)
        
        log_info("AgentManager", f"Created session {session_id} for agent {agent_id}")
        return session_id
    
    def get_agent_by_session(self, session_id: str) -> Agent:
        """Get agent instance by session ID"""
        if session_id not in self.session_to_agent:
            raise ValueError(f"Session '{session_id}' not found")
        return self.session_to_agent[session_id]
    
    def close_session(self, session_id: str) -> None:
        """Close a session and clean up mappings"""
        if session_id in self.session_to_agent:
            agent_instance = self.session_to_agent[session_id]
            
            # Find agent_id for this instance
            agent_id = None
            for aid, instance in self.agent_instances.items():
                if instance == agent_instance:
                    agent_id = aid
                    break
            
            # Remove from mappings
            del self.session_to_agent[session_id]
            
            if agent_id and agent_id in self.agent_to_sessions:
                if session_id in self.agent_to_sessions[agent_id]:
                    self.agent_to_sessions[agent_id].remove(session_id)
                
                # If no more sessions for this agent, clear the instance
                if not self.agent_to_sessions[agent_id]:
                    del self.agent_to_sessions[agent_id]
                    if agent_id in self.agent_instances:
                        del self.agent_instances[agent_id]
            
            log_info("AgentManager", f"Closed session {session_id}")
    
    def get_sessions_for_agent(self, agent_id: str) -> List[str]:
        """Get all session IDs for a specific agent"""
        return self.agent_to_sessions.get(agent_id, []) 

    # ===== Conversation Persistence (history/) =====
    def _history_dir(self) -> Path:
        return Path("history")

    def _agent_history_dir(self, agent_id: str) -> Path:
        return self._history_dir() / agent_id

    def _conversation_file_path(self, agent_id: str, session_id: str) -> Path:
        return self._agent_history_dir(agent_id) / f"{session_id}.json"

    def save_conversation(self, agent_id: str, session_id: str) -> str:
        """Persist the full conversation for an agent's session into ./history/<agent_id>/<session_id>.json
        Fail-fast on any error.
        Returns the absolute file path as string.
        """
        if not session_id:
            raise ValueError("session_id is required to save conversation")
        agent_instance = self.get_agent_by_session(session_id)
        history_dir = self._agent_history_dir(agent_id)
        history_dir.mkdir(parents=True, exist_ok=True)

        # Build conversation data similar to Agent.save_conversation but under ./history
        from schemas import ConversationData
        conversation_data = ConversationData(
            session_id=session_id,
            agent_id=agent_id,
            agent_name=self.get_agent_config(agent_id).name,
            model=self.get_agent_config(agent_id).model,
            created_at=datetime.now().isoformat(),
            responses=[]
        )
        for message in agent_instance.get_conversation_history():
            conversation_data.responses.append(message.model_dump())

        path = self._conversation_file_path(agent_id, session_id)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(conversation_data.model_dump(), f, indent=2, default=str)
        return str(path.resolve())

    def list_conversations(self, agent_id: str) -> List[Dict[str, Any]]:
        """List available saved sessions for an agent with last-modified times.
        Returns list sorted by mtime desc: [{session_id, modified_at, file_path}]
        """
        dir_path = self._agent_history_dir(agent_id)
        if not dir_path.exists():
            return []
        sessions: List[Dict[str, Any]] = []
        for file_path in dir_path.glob('*.json'):
            try:
                session_id = file_path.stem
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                sessions.append({
                    "session_id": session_id,
                    "modified_at": mtime,
                    "file_path": str(file_path.resolve()),
                })
            except Exception as e:
                raise RuntimeError(f"Failed to list conversation file '{file_path}': {e}")
        # Sort by modified time descending
        sessions.sort(key=lambda x: x["modified_at"], reverse=True)
        return sessions

    def load_conversation(self, agent_id: str, session_id: str) -> Dict[str, Any]:
        """Load a saved conversation into the agent instance, switching to the loaded session.
        Returns a snapshot dict with 'session_id' and 'messages' (list of Message dicts).
        """
        if not session_id:
            raise ValueError("session_id is required to load conversation")

        path = self._conversation_file_path(agent_id, session_id)
        if not path.exists():
            raise FileNotFoundError(f"Saved conversation not found for agent '{agent_id}' and session '{session_id}'")

        # Read and parse
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        from schemas import ConversationData, Message
        conv_data = ConversationData.model_validate(data)

        # Ensure agent instance exists and replace messages
        agent_instance = self.get_agent(agent_id)
        agent_instance.clear_conversation()
        messages_models: List[Message] = []
        for msg in conv_data.responses:
            msg_model = Message.model_validate(msg)
            messages_models.append(msg_model)
        # Assign reconstructed messages
        agent_instance.messages = messages_models

        # Switch mapping to the loaded session id
        self.session_to_agent[conv_data.session_id] = agent_instance
        if agent_id not in self.agent_to_sessions:
            self.agent_to_sessions[agent_id] = []
        if conv_data.session_id not in self.agent_to_sessions[agent_id]:
            self.agent_to_sessions[agent_id].append(conv_data.session_id)

        # Build snapshot for frontend
        snapshot = {
            "session_id": conv_data.session_id,
            "messages": [m.model_dump() for m in messages_models]
        }
        return snapshot