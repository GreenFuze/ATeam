"""Model manager using the llm package for discovery and management."""

import os
import yaml
from typing import Dict, List, Optional, Any
import llm
from ..util.types import Result, ErrorInfo
from ..util.logging import log


class ModelInfo:
    """Model information."""
    
    def __init__(self, model_id: str, name: str, provider: str, description: str = "",
                 context_window_size: Optional[int] = None, model_settings: Dict[str, Any] = None,
                 default_inference: Dict[str, Any] = None):
        self.model_id = model_id
        self.name = name
        self.provider = provider
        self.description = description
        self.context_window_size = context_window_size
        self.model_settings = model_settings or {}
        self.default_inference = default_inference or {}


class ModelManager:
    """Manages LLM model configurations and dynamic discovery using the llm package."""
    
    def __init__(self, config_path: str = "models.yaml"):
        self.config_path = config_path
        self.models: Dict[str, ModelInfo] = {}
        self.load_models()
        
        # Provider schema mapping for dynamic discovery
        self.provider_schema_map = {
            'openai': 'llm.default_plugins.openai_models.Chat.Options',
            'ollama': 'llm_ollama.Ollama.Options',
        }
    
    def load_models(self) -> None:
        """Load models from YAML configuration file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file)
                    models_data = data.get("models", {})
                    
                    for model_id, config in models_data.items():
                        model_info = ModelInfo(
                            model_id=model_id,
                            name=config.get("name", model_id),
                            provider=config.get("provider", "unknown"),
                            description=config.get("description", ""),
                            context_window_size=config.get("context_window_size"),
                            model_settings=config.get("model_settings", {}),
                            default_inference=config.get("default_inference", {})
                        )
                        self.models[model_id] = model_info
            else:
                log("WARN", "models.manager", "models.yaml not found", config_path=self.config_path)
        except Exception as e:
            raise RuntimeError(f"Error loading models.yaml from {self.config_path}: {str(e)}")
    
    def save_models(self) -> None:
        """Save models to YAML configuration file."""
        # Only create directory if there's a directory path (not empty)
        dir_path = os.path.dirname(self.config_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # Convert ModelInfo objects to dictionaries for YAML serialization
        config_models = {}
        for model_id, model in self.models.items():
            config_models[model_id] = {
                "name": model.name,
                "provider": model.provider,
                "description": model.description,
                "context_window_size": model.context_window_size,
                "model_settings": model.model_settings,
                "default_inference": model.default_inference
            }
        
        data = {
            "models": config_models
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as file:
            yaml.dump(data, file, default_flow_style=False, indent=2)
    
    def discover_models_from_llm(self) -> Dict[str, Any]:
        """Discover models from llm package without loading them."""
        discovered_models = {}
        chat_model_ids = set()
        embedding_model_ids = set()
        
        try:
            # Discover chat models
            chat_models = llm.get_models()
            for model in chat_models:
                model_id = model.model_id
                provider_name = self._get_provider_from_model(model)
                chat_model_ids.add(model_id)
                
                discovered_models[model_id] = {
                    'id': model_id,
                    'name': getattr(model, 'model_name', None) or model_id,
                    'provider': provider_name,
                    'description': f'{model_id} model from {provider_name}',
                    'supports_schema': getattr(model, 'supports_schema', False),
                    'supports_tools': getattr(model, 'supports_tools', False),
                    'can_stream': getattr(model, 'can_stream', False),
                    'vision': getattr(model, 'vision', False),
                    'attachment_types': list(getattr(model, 'attachment_types', set())),
                    'embedding_model': False,
                    'is_chat_model': True,
                    'is_embedding_model': False
                }
            
            # Discover embedding models
            embedding_models = llm.get_embedding_models()
            for model in embedding_models:
                model_id = model.model_id
                provider_name = self._get_provider_from_model(model)
                embedding_model_ids.add(model_id)
                
                if model_id in discovered_models:
                    # Model exists as both chat and embedding - merge capabilities
                    existing_model = discovered_models[model_id]
                    existing_model.update({
                        'description': f'{model_id} model from {provider_name} (chat + embedding)',
                        'dimensions': getattr(model, 'dimensions', None),
                        'truncate': getattr(model, 'truncate', False),
                        'supports_binary': getattr(model, 'supports_binary', False),
                        'supports_text': getattr(model, 'supports_text', False),
                        'embed_batch': hasattr(model, 'embed_batch'),
                        'is_embedding_model': True
                    })
                else:
                    # New embedding-only model
                    discovered_models[model_id] = {
                        'id': model_id,
                        'name': getattr(model, 'model_name', None) or model_id,
                        'provider': provider_name,
                        'description': f'{model_id} embedding model from {provider_name}',
                        'supports_schema': False,
                        'supports_tools': False,
                        'can_stream': False,
                        'vision': False,
                        'attachment_types': [],
                        'dimensions': getattr(model, 'dimensions', None),
                        'truncate': getattr(model, 'truncate', False),
                        'supports_binary': getattr(model, 'supports_binary', False),
                        'supports_text': getattr(model, 'supports_text', False),
                        'embed_batch': hasattr(model, 'embed_batch'),
                        'embedding_model': True,
                        'is_chat_model': False,
                        'is_embedding_model': True
                    }
                
        except Exception as e:
            raise RuntimeError(f"Error discovering models from llm: {str(e)}")
        
        return discovered_models
    
    def _get_provider_from_model(self, model) -> str:
        """Extract provider name from model object."""
        module_name = type(model).__module__
        
        if 'openai' in module_name:
            return 'openai'
        elif 'ollama' in module_name:
            return 'ollama'
        else:
            # Extract provider from module name
            parts = module_name.split('.')
            for part in parts:
                if part not in ['llm', 'default_plugins', 'models']:
                    return part
            return 'unknown'
    
    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Get model information by ID."""
        # First check configured models
        if model_id in self.models:
            return self.models[model_id]
        
        # Then check discovered models
        discovered_models = self.discover_models_from_llm()
        if model_id in discovered_models:
            discovered = discovered_models[model_id]
            return ModelInfo(
                model_id=model_id,
                name=discovered.get('name', model_id),
                provider=discovered.get('provider', 'unknown'),
                description=discovered.get('description', ''),
                context_window_size=None,  # Not available from discovery
                model_settings={},
                default_inference={}
            )
        
        return None
    
    def list_models(self) -> Result[Dict[str, Any]]:
        """List all available models (configured + discovered)."""
        try:
            discovered_models = self.discover_models_from_llm()
            processed_names = set()
            result = {}
            
            # Add configured models first
            for model_id, model_info in self.models.items():
                processed_names.add(model_id)
                
                # Get runtime data from discovery
                discovered_info = discovered_models.get(model_id, {})
                
                result[model_id] = {
                    'id': model_info.model_id,
                    'name': model_info.name,
                    'provider': model_info.provider,
                    'description': model_info.description,
                    'context_window_size': model_info.context_window_size,
                    'model_settings': model_info.model_settings,
                    'default_inference': model_info.default_inference,
                    'configured': True,
                    'supports_schema': discovered_info.get('supports_schema', False),
                    'supports_tools': discovered_info.get('supports_tools', False),
                    'can_stream': discovered_info.get('can_stream', False),
                    'is_chat_model': discovered_info.get('is_chat_model', True),
                    'is_embedding_model': discovered_info.get('is_embedding_model', False)
                }
            
            # Add discovered-only models
            for model_id, discovered_info in discovered_models.items():
                if model_id not in processed_names:
                    result[model_id] = {
                        'id': model_id,
                        'name': discovered_info.get('name', model_id),
                        'provider': discovered_info.get('provider', 'unknown'),
                        'description': discovered_info.get('description', ''),
                        'context_window_size': None,
                        'model_settings': {},
                        'default_inference': {},
                        'configured': False,
                        'supports_schema': discovered_info.get('supports_schema', False),
                        'supports_tools': discovered_info.get('supports_tools', False),
                        'can_stream': discovered_info.get('can_stream', False),
                        'is_chat_model': discovered_info.get('is_chat_model', True),
                        'is_embedding_model': discovered_info.get('is_embedding_model', False)
                    }
            
            return Result(ok=True, value=result)
            
        except Exception as e:
            return Result(ok=False, error=ErrorInfo("models.discovery_error", str(e)))
    
    def resolve(self, model_id: str) -> Result[Dict[str, Any]]:
        """Resolve model configuration by ID."""
        model_info = self.get_model(model_id)
        if not model_info:
            return Result(ok=False, error=ErrorInfo("model.not_found", f"Model '{model_id}' not found"))
        
        return Result(ok=True, value={
            'model_id': model_info.model_id,
            'name': model_info.name,
            'provider': model_info.provider,
            'description': model_info.description,
            'context_window_size': model_info.context_window_size,
            'model_settings': model_info.model_settings,
            'default_inference': model_info.default_inference
        })
