import os
import markdown
from typing import Dict, List, Optional, Any
from models import PromptConfig, PromptType
from datetime import datetime
import json

class PromptManager:
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = prompts_dir
        self.prompts: Dict[str, PromptConfig] = {}
        self.load_prompts()
        
    def load_prompts(self):
        """Load all prompt files from the prompts directory"""
        # Check if prompts directory exists - create it if it doesn't exist
        if not os.path.exists(self.prompts_dir):
            os.makedirs(self.prompts_dir, exist_ok=True)
            print(f"Created prompts directory: {self.prompts_dir}")
            return  # Empty prompts directory is OK
        
        # Load existing prompts (empty directory is OK)
        for filename in os.listdir(self.prompts_dir):
            if filename.endswith('.md'):
                prompt_name = filename  # Keep the full filename including .md extension
                file_path = os.path.join(self.prompts_dir, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Try to extract metadata from frontmatter or filename
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
                    print(f"Error loading prompt {prompt_name}: {e}")
                    raise  # Re-raise the exception to fail fast
    
    def _determine_prompt_type(self, filename: str, content: str) -> PromptType:
        """Determine prompt type based on filename and content"""
        filename_lower = filename.lower()
        
        if "system" in filename_lower:
            return PromptType.SYSTEM
        elif "seed" in filename_lower:
            return PromptType.SEED
        elif "agent" in filename_lower:
            return PromptType.AGENT
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
    
    def update_prompt(self, name: str, content: str):
        """Update an existing prompt"""
        # Ensure name has .md extension
        if not name.endswith('.md'):
            name = f"{name}.md"
            
        if name not in self.prompts:
            raise ValueError(f"Prompt '{name}' not found")
        
        # Update file
        file_path = os.path.join(self.prompts_dir, name)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Update config
        self.prompts[name].content = content
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