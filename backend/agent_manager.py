import yaml
import os
import random
from datetime import datetime
from typing import List, Optional, Dict

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