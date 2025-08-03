import yaml
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from schemas import AgentConfig, CreateAgentRequest
from agent import Agent
from notification_utils import log_error, log_warning, log_info

class AgentManager:
    def __init__(self, config_path: str = "agents.yaml"):
        self.config_path = config_path
        self.agents_config: Dict[str, AgentConfig] = {}
        self.agent_instances: Dict[str, Agent] = {}  # Lazy-loaded agent instances
        self.load_agents()
        
    def load_agents(self):
        """Load agents from YAML configuration file"""
        if not os.path.exists(self.config_path):
            log_warning("AgentManager", f"Agents configuration file {self.config_path} not found", {"config_path": self.config_path})
            return
            
        with open(self.config_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            if data and 'agents' in data:
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
    
    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get all agents as dictionaries"""
        return [agent.model_dump() for agent in self.agents_config.values()]
    
    def get_agent_config(self, agent_id: str) -> AgentConfig:
        """Get a specific agent by ID"""
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
    
    def create_agent(self, agent_request: CreateAgentRequest) -> str:
        """Create a new agent"""
        # Generate unique ID
        agent_id = str(uuid.uuid4())
        
        # Create agent configuration
        agent_data = agent_request.model_dump()
        agent_data['id'] = agent_id
        agent_data['created_at'] = datetime.now().isoformat()
        agent_data['updated_at'] = datetime.now().isoformat()
        
        agent = AgentConfig(**agent_data)
        self.agents_config[agent_id] = agent
        
        # Save to YAML file
        self.save_agents()
        
        return agent_id
    
    def update_agent(self, agent_id: str, agent_data: Dict[str, Any]):
        """Update an existing agent"""
        if agent_id not in self.agents_config:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        # Update agent configuration
        agent = self.agents_config[agent_id]
        for key, value in agent_data.items():
            if hasattr(agent, key) and key not in ['id', 'created_at']:
                setattr(agent, key, value)
        
        # Update timestamp
        agent.updated_at = datetime.now().isoformat()
        
        # Clear cached instance since configuration changed
        self.clear_agent_instance(agent_id)
        
        # Save to YAML file
        self.save_agents()
    
    def delete_agent(self, agent_id: str):
        """Delete an agent"""
        if agent_id not in self.agents_config:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        # Clear cached instance
        self.clear_agent_instance(agent_id)
        
        del self.agents_config[agent_id]
        
        # Save to YAML file
        self.save_agents()
    
    def get_agent_by_name(self, name: str) -> Optional[AgentConfig]:
        """Get an agent by name"""
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
    
    def get_agent_info(self, agent_id: str) -> Dict[str, Any]:
        """Get detailed information about an agent"""
        agent = self.get_agent_config(agent_id)
        if not agent:
            return {}
        
        info = agent.model_dump()
        
        # Add validation status
        info['is_valid'] = self.validate_agent(agent_id)
        
        # Add additional metadata
        info['tool_count'] = len(agent.tools)
        info['prompt_count'] = len(agent.prompts)
        
        return info 