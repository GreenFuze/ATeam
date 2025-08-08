import os
import markdown
import yaml
from typing import Dict, List, Optional, Any
from schemas import PromptConfig, PromptType, SeedMessage, SeedPromptData
from datetime import datetime
import json
from notification_utils import log_error, log_warning, log_info

class PromptManager:
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = prompts_dir
        self.prompts: Dict[str, PromptConfig] = {}
        self.prompts_yaml_path = "prompts.yaml"
        self.load_prompts()
        
    def load_prompts(self):
        """Load all prompt files from the prompts directory"""
        # Check if prompts directory exists - create it if it doesn't exist
        if not os.path.exists(self.prompts_dir):
            os.makedirs(self.prompts_dir, exist_ok=True)
            log_info("PromptManager", f"Created prompts directory: {self.prompts_dir}", {"prompts_dir": self.prompts_dir})
            return  # Empty prompts directory is OK
        
        # Load metadata from prompts.yaml if it exists
        prompts_metadata = self._load_prompts_metadata()
        
        # Load existing prompts (empty directory is OK)
        for filename in os.listdir(self.prompts_dir):
            if filename.endswith('.md'):
                prompt_name = filename  # Keep the full filename including .md extension
                file_path = os.path.join(self.prompts_dir, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Get prompt type from metadata or fallback to filename analysis
                    if prompt_name in prompts_metadata:
                        prompt_type = PromptType(prompts_metadata[prompt_name]['type'])
                    else:
                        prompt_type = self._determine_prompt_type(filename, content)
                    
                    prompt_config = PromptConfig(
                        name=prompt_name,
                        content=content,
                        type=prompt_type,
                        created_at=datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                        updated_at=datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    )
                    
                    self.prompts[prompt_name] = prompt_config
                    
                except Exception as e:
                    log_error("PromptManager", f"Error loading prompt {prompt_name}", e, {"prompt_name": prompt_name, "file_path": file_path})
                    raise  # Re-raise the exception to fail fast
    
    def _determine_prompt_type(self, filename: str, content: str) -> PromptType:
        """Determine prompt type based on filename and content"""
        filename_lower = filename.lower()
        
        if "system" in filename_lower:
            return PromptType.SYSTEM
        elif "seed" in filename_lower:
            return PromptType.SEED
        else:
            # Default to system if can't determine
            return PromptType.SYSTEM
    
    def get_all_prompts(self) -> List[Dict[str, Any]]:
        """Get all prompts as dictionaries"""
        return [prompt.model_dump() for prompt in self.prompts.values()]
    
    def get_prompt(self, prompt_name: str) -> Optional[PromptConfig]:
        """Get a specific prompt by name"""
        if prompt_name not in self.prompts:
            # Provide detailed error information about missing prompt
            available_prompts = list(self.prompts.keys())
            error_msg = f"Prompt '{prompt_name}' not found. "
            if available_prompts:
                error_msg += f"Available prompts: {', '.join(available_prompts)}"
            else:
                error_msg += f"No prompts found in '{self.prompts_dir}' directory."
            error_msg += f" Expected file: {os.path.join(self.prompts_dir, prompt_name)}"
            raise FileNotFoundError(error_msg)
        return self.prompts.get(prompt_name)
    
    def get_prompt_content(self, prompt_name: str) -> Optional[str]:
        """Get the content of a specific prompt"""
        prompt = self.get_prompt(prompt_name)
        return prompt.content if prompt else None
    
    def create_prompt(self, name: str, content: str, prompt_type: PromptType = PromptType.SYSTEM) -> str:
        """Create a new prompt file"""
        # Ensure name has .md extension
        if not name.endswith('.md'):
            name = f"{name}.md"
        
        if name in self.prompts:
            raise ValueError(f"Prompt '{name}' already exists")
        
        # Create file path
        file_path = os.path.join(self.prompts_dir, name)
        
        # Write content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Update metadata
        self._update_prompt_metadata(name, prompt_type)
        
        # Create prompt config
        now = datetime.now().isoformat()
        prompt_config = PromptConfig(
            name=name,
            content=content,
            type=prompt_type,
            created_at=now,
            updated_at=now
        )
        
        # Add to collection
        self.prompts[name] = prompt_config
        
        return name
    
    def update_prompt(self, name: str, content: str, new_name: Optional[str] = None, prompt_type: Optional[PromptType] = None):
        """Update an existing prompt"""
        # Ensure name has .md extension
        if not name.endswith('.md'):
            name = f"{name}.md"
            
        if name not in self.prompts:
            raise ValueError(f"Prompt '{name}' not found")
        
        # Handle rename if new_name is provided
        if new_name and new_name != name:
            if not new_name.endswith('.md'):
                new_name = f"{new_name}.md"
            
            # Check if new name already exists
            if new_name in self.prompts:
                raise ValueError(f"Prompt '{new_name}' already exists")
            
            # Rename file
            old_file_path = os.path.join(self.prompts_dir, name)
            new_file_path = os.path.join(self.prompts_dir, new_name)
            os.rename(old_file_path, new_file_path)
            
            # Update metadata
            if prompt_type:
                self._update_prompt_metadata(new_name, prompt_type)
            
            # Remove old metadata
            metadata = self._load_prompts_metadata()
            if name in metadata:
                del metadata[name]
                self._save_prompts_metadata(metadata)
            
            # Update collection
            prompt_config = self.prompts[name]
            prompt_config.name = new_name
            prompt_config.content = content
            if prompt_type:
                prompt_config.type = prompt_type
            prompt_config.updated_at = datetime.now().isoformat()
            
            # Move to new key
            self.prompts[new_name] = prompt_config
            del self.prompts[name]
            
        else:
            # Update file
            file_path = os.path.join(self.prompts_dir, name)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update metadata if type changed
            if prompt_type and prompt_type != self.prompts[name].type:
                self._update_prompt_metadata(name, prompt_type)
            
            # Update config
            self.prompts[name].content = content
            if prompt_type:
                self.prompts[name].type = prompt_type
            self.prompts[name].updated_at = datetime.now().isoformat()
    
    def delete_prompt(self, name: str):
        """Delete a prompt file"""
        # Ensure name has .md extension
        if not name.endswith('.md'):
            name = f"{name}.md"
            
        if name not in self.prompts:
            raise ValueError(f"Prompt '{name}' not found")
        
        # Delete file
        file_path = os.path.join(self.prompts_dir, name)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Remove from metadata
        metadata = self._load_prompts_metadata()
        if name in metadata:
            del metadata[name]
            self._save_prompts_metadata(metadata)
        
        # Remove from collection
        del self.prompts[name]
    
    def get_prompts_by_type(self, prompt_type: PromptType) -> List[PromptConfig]:
        """Get all prompts of a specific type"""
        return [prompt for prompt in self.prompts.values() if prompt.type == prompt_type]
    
    def render_prompt_html(self, prompt_name: str) -> Optional[str]:
        """Render a prompt as HTML"""
        prompt = self.get_prompt(prompt_name)
        if not prompt:
            return None
        
        # Convert markdown to HTML
        html = markdown.markdown(prompt.content)
        return html
    
    def search_prompts(self, query: str) -> List[PromptConfig]:
        """Search prompts by content"""
        query_lower = query.lower()
        results = []
        
        for prompt in self.prompts.values():
            if (query_lower in prompt.name.lower() or 
                query_lower in prompt.content.lower() or
                query_lower in prompt.type.value.lower()):
                results.append(prompt)
        
        return results
    
    def _load_prompts_metadata(self) -> Dict[str, Dict[str, str]]:
        """Load prompts metadata from prompts.yaml file"""
        if not os.path.exists(self.prompts_yaml_path):
            return {}
        
        try:
            with open(self.prompts_yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data.get('prompts', {})
        except Exception as e:
            raise RuntimeError(f"Error loading prompts metadata from {self.prompts_yaml_path}: {str(e)}")
        
        return {}
    
    def _save_prompts_metadata(self, metadata: Dict[str, Dict[str, str]]):
        """Save prompts metadata to prompts.yaml file"""
        try:
            # Ensure directory exists
            dir_path = os.path.dirname(self.prompts_yaml_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            with open(self.prompts_yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump({'prompts': metadata}, f, default_flow_style=False, indent=2)
        except Exception as e:
            log_error("PromptManager", "Error saving prompts metadata", e, {"prompts_yaml_path": self.prompts_yaml_path})
            raise
    
    def _update_prompt_metadata(self, prompt_name: str, prompt_type: PromptType):
        """Update prompts metadata in prompts.yaml"""
        metadata = self._load_prompts_metadata()
        metadata[prompt_name] = {'type': prompt_type.value}
        self._save_prompts_metadata(metadata)
    
    def create_seed_prompt(self, name: str, messages: List[SeedMessage]) -> str:
        """Create a seed prompt from a list of messages"""
        # Convert messages to JSON format for llm chat
        content = json.dumps([msg.model_dump() for msg in messages], indent=2)
        return self.create_prompt(name, content, PromptType.SEED)
    
    def update_seed_prompt(self, name: str, messages: List[SeedMessage]):
        """Update a seed prompt with new messages"""
        # Convert messages to JSON format for llm chat
        content = json.dumps([msg.model_dump() for msg in messages], indent=2)
        self.update_prompt(name, content)
    
    def parse_seed_prompt(self, name: str) -> List[SeedMessage]:
        """Parse a seed prompt and return list of messages"""
        prompt = self.get_prompt(name)
        if not prompt or prompt.type != PromptType.SEED:
            raise ValueError(f"Prompt '{name}' is not a seed prompt")
        
        try:
            # Try to parse as JSON first (new format)
            messages_data = json.loads(prompt.content)
            return [SeedMessage(**msg) for msg in messages_data]
        except (json.JSONDecodeError, TypeError):
            # Fallback to old markdown format for backward compatibility
            messages = []
            lines = prompt.content.split('\n')
            current_role = None
            current_content = []
            
            for line in lines:
                if line.startswith('## '):
                    # Save previous message if exists
                    if current_role and current_content:
                        messages.append(SeedMessage(
                            role=current_role.lower(),
                            content='\n'.join(current_content).strip()
                        ))
                    
                    # Start new message
                    current_role = line[3:].strip().lower()
                    current_content = []
                else:
                    if current_role:
                        current_content.append(line)
            
            # Add last message
            if current_role and current_content:
                messages.append(SeedMessage(
                    role=current_role.lower(),
                    content='\n'.join(current_content).strip()
                ))
            
            return messages 