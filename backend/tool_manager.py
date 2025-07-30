import yaml
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from models import ToolConfig
import json

class ToolManager:
    def __init__(self, config_path: str = "tools.yaml"):
        self.config_path = config_path
        self.tools: Dict[str, ToolConfig] = {}
        self.load_tools()
        
    def load_tools(self):
        """Load tools from YAML configuration file"""
        if not os.path.exists(self.config_path):
            print(f"Warning: Tools configuration file {self.config_path} not found")
            return
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
                if data and 'tools' in data:
                    for tool_data in data['tools']:
                        tool = ToolConfig(**tool_data)
                        self.tools[tool.name] = tool
        except Exception as e:
            print(f"Error loading tools: {e}")
    
    def save_tools(self):
        """Save tools to YAML configuration file"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        data = {
            "tools": [tool.model_dump() for tool in self.tools.values()]
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as file:
            yaml.dump(data, file, default_flow_style=False, indent=2)
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools as dictionaries (custom tools only)"""
        return [tool.model_dump() for tool in self.tools.values()]
    
    def get_tool(self, tool_name: str) -> Optional[ToolConfig]:
        """Get a specific tool by name"""
        return self.tools.get(tool_name)
    
    def create_tool(self, tool_config: Dict[str, Any]) -> str:
        """Create a new tool"""
        # Generate unique name if not provided
        if 'name' not in tool_config or not tool_config['name']:
            tool_config['name'] = f"tool_{uuid.uuid4().hex[:8]}"
        
        tool_name = tool_config['name']
        
        # Check if tool already exists
        if tool_name in self.tools:
            raise ValueError(f"Tool '{tool_name}' already exists")
        
        # Create tool configuration
        tool = ToolConfig(**tool_config)
        self.tools[tool_name] = tool
        
        # Save to YAML file
        self.save_tools()
        
        return tool_name
    
    def update_tool(self, tool_name: str, tool_data: Dict[str, Any]):
        """Update an existing tool"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        # Update tool configuration
        tool = self.tools[tool_name]
        for key, value in tool_data.items():
            if hasattr(tool, key) and key not in ['name']:
                setattr(tool, key, value)
        
        # Save to YAML file
        self.save_tools()
    
    def delete_tool(self, tool_name: str):
        """Delete a custom tool"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        del self.tools[tool_name]
        
        # Save to YAML file
        self.save_tools()
    
    def get_custom_tools(self) -> List[ToolConfig]:
        """Get all custom tools"""
        return list(self.tools.values())
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a tool with given parameters"""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        # For custom tools, execute the code
        if tool.file_path and os.path.exists(tool.file_path):
            return self._execute_custom_tool(tool, parameters)
        else:
            raise ValueError(f"Tool '{tool_name}' has no executable code")
    
    def _execute_custom_tool(self, tool: ToolConfig, parameters: Dict[str, Any]) -> Any:
        """Execute a custom tool by running its Python code"""
        try:
            # Create a namespace for the tool execution
            namespace = {
                'parameters': parameters,
                'result': None,
                'json': json,
                'datetime': datetime,
                'uuid': uuid
            }
            
            # Read and execute the tool code
            if tool.file_path:
                with open(tool.file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                exec(code, namespace)
                
                # Return the result
                return namespace.get('result')
            else:
                raise ValueError(f"Tool '{tool.name}' has no file path")
            
        except Exception as e:
            raise Exception(f"Error executing tool '{tool.name}': {str(e)}")
    
    def validate_tool(self, tool_name: str) -> bool:
        """Validate if a tool can be executed"""
        tool = self.get_tool(tool_name)
        if not tool:
            return False
        
        # For custom tools, check if file exists
        return bool(tool.file_path and os.path.exists(tool.file_path))
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed information about a tool"""
        tool = self.get_tool(tool_name)
        if not tool:
            return {}
        
        info = tool.model_dump()
        
        # Add validation status
        info['is_valid'] = self.validate_tool(tool_name)
        
        # Add additional metadata
        info['parameter_count'] = len(tool.parameters) if tool.parameters else 0
        info['file_exists'] = bool(tool.file_path and os.path.exists(tool.file_path)) if tool.file_path else False
        
        return info 