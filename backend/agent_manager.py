import yaml
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from schemas import AgentConfig, CreateAgentRequest

class AgentManager:
    def __init__(self, config_path: str = "agents.yaml"):
        self.config_path = config_path
        self.agents: Dict[str, AgentConfig] = {}
        self.load_agents()
        
    def load_agents(self):
        """Load agents from YAML configuration file"""
        if not os.path.exists(self.config_path):
            print(f"Warning: Agents configuration file {self.config_path} not found")
            return
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
                if data and 'agents' in data:
                    for agent_data in data['agents']:
                        agent = AgentConfig(**agent_data)
                        self.agents[agent.id] = agent
        except Exception as e:
            print(f"Error loading agents: {e}")
    
    def save_agents(self):
        """Save agents to YAML configuration file"""
        # Only create directory if there's a directory path (not empty)
        dir_path = os.path.dirname(self.config_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        data = {
            "agents": [agent.model_dump() for agent in self.agents.values()]
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as file:
            yaml.dump(data, file, default_flow_style=False, indent=2)
    
    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get all agents as dictionaries"""
        return [agent.model_dump() for agent in self.agents.values()]
    
    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """Get a specific agent by ID"""
        return self.agents.get(agent_id)
    
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
        self.agents[agent_id] = agent
        
        # Save to YAML file
        self.save_agents()
        
        return agent_id
    
    def update_agent(self, agent_id: str, agent_data: Dict[str, Any]):
        """Update an existing agent"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        # Update agent configuration
        agent = self.agents[agent_id]
        for key, value in agent_data.items():
            if hasattr(agent, key) and key not in ['id', 'created_at']:
                setattr(agent, key, value)
        
        # Update timestamp
        agent.updated_at = datetime.now().isoformat()
        
        # Save to YAML file
        self.save_agents()
    
    def delete_agent(self, agent_id: str):
        """Delete an agent"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        del self.agents[agent_id]
        
        # Save to YAML file
        self.save_agents()
    
    def get_agent_by_name(self, name: str) -> Optional[AgentConfig]:
        """Get an agent by name"""
        for agent in self.agents.values():
            if agent.name == name:
                return agent
        return None
    
    def search_agents(self, query: str) -> List[AgentConfig]:
        """Search agents by name or description"""
        query = query.lower()
        results = []
        
        for agent in self.agents.values():
            if (query in agent.name.lower() or 
                query in agent.description.lower()):
                results.append(agent)
        
        return results
    
    def get_agents_by_model(self, model: str) -> List[AgentConfig]:
        """Get all agents using a specific model"""
        return [agent for agent in self.agents.values() if agent.model == model]
    
    def get_agents_by_tool(self, tool_name: str) -> List[AgentConfig]:
        """Get all agents that have a specific tool"""
        return [agent for agent in self.agents.values() if tool_name in agent.tools]
    
    def validate_agent(self, agent_id: str) -> bool:
        """Validate if an agent can be used"""
        agent = self.get_agent(agent_id)
        if not agent:
            return False
        
        # Check if model exists (this would typically check against available models)
        # For now, we'll just check if the model field is not empty
        if not agent.model:
            return False
        
        return True
    
    def get_agent_info(self, agent_id: str) -> Dict[str, Any]:
        """Get detailed information about an agent"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {}
        
        info = agent.model_dump()
        
        # Add validation status
        info['is_valid'] = self.validate_agent(agent_id)
        
        # Add additional metadata
        info['tool_count'] = len(agent.tools)
        info['prompt_count'] = len(agent.prompts)
        
        return info 