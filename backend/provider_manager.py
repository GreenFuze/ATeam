import yaml
import os
from typing import Dict, List, Optional, Any

class ProviderManager:
    def __init__(self, config_path: str = "providers.yaml"):
        self.config_path = config_path
        self.providers: Dict[str, Dict[str, Any]] = {}
        self.load_providers()
        
    def load_providers(self):
        """Load providers from YAML configuration file"""
        if not os.path.exists(self.config_path):
            print(f"Warning: Providers configuration file {self.config_path} not found")
            return
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
                if data and 'providers' in data:
                    for provider_data in data['providers']:
                        provider_name = provider_data.get('name')
                        if provider_name:
                            self.providers[provider_name] = provider_data
        except Exception as e:
            print(f"Error loading providers: {e}")
    
    def save_providers(self):
        """Save providers to YAML configuration file"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        data = {
            "providers": list(self.providers.values())
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as file:
            yaml.dump(data, file, default_flow_style=False, indent=2)
    
    def get_all_providers(self) -> List[Dict[str, Any]]:
        """Get all providers as dictionaries"""
        return list(self.providers.values())
    
    def get_provider(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific provider by name"""
        return self.providers.get(provider_name)
    
    def get_provider_info(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get provider information for a specific provider"""
        provider = self.get_provider(provider_name)
        if provider:
            return {
                "name": provider.get("name"),
                "display_name": provider.get("display_name"),
                "description": provider.get("description"),
                "api_key_required": provider.get("api_key_required", False),
                "api_key_env_var": provider.get("api_key_env_var"),
                "base_url": provider.get("base_url")
            }
        return None
    
    def create_provider(self, provider_config: Dict[str, Any]) -> str:
        """Create a new provider"""
        provider_name = provider_config.get('name')
        if not provider_name:
            raise ValueError("Provider name is required")
        
        if provider_name in self.providers:
            raise ValueError(f"Provider '{provider_name}' already exists")
        
        self.providers[provider_name] = provider_config
        
        # Save to YAML file
        self.save_providers()
        
        return provider_name
    
    def update_provider(self, provider_name: str, provider_config: Dict[str, Any]):
        """Update an existing provider"""
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not found")
        
        self.providers[provider_name].update(provider_config)
        
        # Save to YAML file
        self.save_providers()
    
    def delete_provider(self, provider_name: str):
        """Delete a provider"""
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not found")
        
        del self.providers[provider_name]
        
        # Save to YAML file
        self.save_providers()