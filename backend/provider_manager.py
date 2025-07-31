import yaml
import os
from typing import Dict, List, Optional, Any
from schemas import ProviderInfo, ProviderInfoView

class ProviderManager:
    def __init__(self, config_path: str = "providers.yaml"):
        self.config_path = config_path
        self.providers: Dict[str, ProviderInfo] = {}
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
                        try:
                            provider_info = ProviderInfo(**provider_data)
                            self.providers[provider_info.name] = provider_info
                        except Exception as e:
                            print(f"Error loading provider {provider_data.get('name', 'unknown')}: {e}")
        except Exception as e:
            print(f"Error loading providers: {e}")
    
    def save_providers(self):
        """Save providers to YAML configuration file"""
        # Only create directory if there's a directory path (not empty)
        dir_path = os.path.dirname(self.config_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # Convert ProviderInfo objects to dictionaries for YAML serialization
        config_providers = []
        for provider in self.providers.values():
            config_providers.append(provider.model_dump())
        
        data = {
            "providers": config_providers
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as file:
            yaml.dump(data, file, default_flow_style=False, indent=2)
    
    def get_all_providers(self) -> List[ProviderInfo]:
        """Get all providers as ProviderInfo objects"""
        return list(self.providers.values())
    
    def get_provider(self, provider_name: str) -> Optional[ProviderInfo]:
        """Get a specific provider by name"""
        return self.providers.get(provider_name)
    
    def get_provider_info(self, provider_name: str) -> Optional[ProviderInfo]:
        """Get detailed provider information"""
        return self.providers.get(provider_name)
    
    def create_provider(self, provider_config: Dict[str, Any]) -> str:
        """Create a new provider"""
        provider_name = provider_config.get('name')
        if not provider_name:
            raise ValueError("Provider name is required")
        
        if provider_name in self.providers:
            raise ValueError(f"Provider '{provider_name}' already exists")
        
        provider_info = ProviderInfo(**provider_config)
        self.providers[provider_name] = provider_info
        self.save_providers()
        
        return provider_name
    
    def update_provider(self, provider_name: str, provider_config: Dict[str, Any]):
        """Update an existing provider"""
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not found")
        
        # Create new ProviderInfo object with updated data
        current_provider = self.providers[provider_name]
        updated_data = current_provider.model_dump()
        updated_data.update(provider_config)
        
        self.providers[provider_name] = ProviderInfo(**updated_data)
        self.save_providers()
    
    def delete_provider(self, provider_name: str):
        """Delete a provider"""
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not found")
        
        del self.providers[provider_name]
        self.save_providers()
    
    def get_provider_models(self, provider_name: str) -> List[Dict[str, Any]]:
        """Get all models for a specific provider"""
        # This would be implemented to get models from llm package
        # For now, return empty list
        return []
    
    def discover_providers_from_llm(self) -> Dict[str, Dict[str, Any]]:
        """Discover providers from llm package with model counts"""
        try:
            import llm
            
            models = llm.get_models()
            embedding_models = llm.get_embedding_models()
            
            providers = {}
            
            # Helper function to get provider info from model string
            def get_provider_from_model(model_str: str, is_embedding: bool = False) -> tuple[str, str]:
                """Extract provider name and key from model string"""
                if is_embedding:
                    if 'OpenAIEmbeddingModel' in model_str:
                        return 'OpenAI', 'openai'
                    elif 'Ollama' in model_str:
                        return 'Ollama', 'ollama'
                    else:
                        provider_name = model_str.split()[0]
                        # Remove trailing colon if present
                        provider_name = provider_name.rstrip(':')
                        return provider_name, provider_name.lower()
                else:
                    # Handle chat models - extract provider name
                    parts = model_str.split()
                    if len(parts) < 2:
                        raise ValueError(f"Unexpected model string format: {model_str}")
                    
                    provider_name = parts[0]  # 'OpenAI Chat: gpt-4o' -> 'OpenAI'
                    # Remove trailing colon if present
                    provider_name = provider_name.rstrip(':')
                    return provider_name, provider_name.lower()
            
            # Process all models (chat and embedding) in a single pass
            all_models = []
            
            # Add chat models
            for model in models:
                model_str = str(model)
                provider_name, provider_key = get_provider_from_model(model_str, False)
                all_models.append((provider_key, provider_name, 'chat'))
            
            # Add embedding models
            for model in embedding_models:
                model_str = str(model)
                provider_name, provider_key = get_provider_from_model(model_str, True)
                all_models.append((provider_key, provider_name, 'embedding'))
            
            # Process all models and count by provider
            for provider_key, provider_name, model_type in all_models:
                if provider_key not in providers:
                    providers[provider_key] = {
                        'name': provider_key,
                        'display_name': provider_name,
                        'description': f'{provider_name} provider',
                        'chat_models': 0,
                        'embedding_models': 0,
                        'api_key_required': provider_key in ['openai', 'anthropic', 'google'],
                        'api_key_env_var': f'{provider_name.upper()}_API_KEY' if provider_key in ['openai', 'anthropic', 'google'] else None,
                        'base_url': None
                    }
                
                if model_type == 'chat':
                    providers[provider_key]['chat_models'] += 1
                else:  # embedding
                    providers[provider_key]['embedding_models'] += 1
            
            return providers
            
        except ImportError:
            print("llm package not available for provider discovery")
            return {}
        except Exception as e:
            print(f"Error discovering providers: {e}")
            raise  # Re-raise the exception to not hide problems
    
    def get_all_providers_with_discovery(self) -> List[ProviderInfoView]:
        """Get all providers including discovered ones"""
        # Get configured providers
        configured_providers = list(self.providers.values())
        
        # Get discovered providers
        discovered_providers = self.discover_providers_from_llm()
        
        # Create a merged list
        merged_providers = []
        processed_names = set()
        
        # First, add configured providers
        for provider in configured_providers:
            provider_name = provider.name
            processed_names.add(provider_name)
            # Check if we have discovered info for this provider
            discovered_info = discovered_providers.get(provider_name)
            if discovered_info:
                # Create ProviderInfoView with discovered data
                provider_view = ProviderInfoView(
                    name=provider.name,
                    display_name=provider.display_name,
                    description=provider.description,
                    api_key_required=provider.api_key_required,
                    api_key_env_var=provider.api_key_env_var,
                    base_url=provider.base_url,
                    configured=True,
                    chat_models=discovered_info.get('chat_models', 0),
                    embedding_models=discovered_info.get('embedding_models', 0)
                )
            else:
                # Create ProviderInfoView without discovered data
                provider_view = ProviderInfoView(
                    name=provider.name,
                    display_name=provider.display_name,
                    description=provider.description,
                    api_key_required=provider.api_key_required,
                    api_key_env_var=provider.api_key_env_var,
                    base_url=provider.base_url,
                    configured=True,
                    chat_models=0,
                    embedding_models=0
                )
            merged_providers.append(provider_view)
        
        # Then, add discovered providers that aren't configured
        for provider_name, provider_info in discovered_providers.items():
            if provider_name not in processed_names:
                # Create ProviderInfoView for discovered provider
                provider_view = ProviderInfoView(
                    name=provider_info['name'],
                    display_name=provider_info['display_name'],
                    description=provider_info['description'],
                    api_key_required=provider_info['api_key_required'],
                    api_key_env_var=provider_info['api_key_env_var'],
                    base_url=provider_info['base_url'],
                    configured=False,
                    chat_models=provider_info['chat_models'],
                    embedding_models=provider_info['embedding_models']
                )
                merged_providers.append(provider_view)
        
        return merged_providers