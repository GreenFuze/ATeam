import os
import yaml
from typing import Dict, List, Optional, Any
from schemas import ModelInfo, ModelInfoView
import llm
from notification_utils import log_error, log_warning, log_info

class ModelsManager:
    """Manages LLM model configurations and dynamic discovery"""
    
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
        """Load models from YAML configuration file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file)
                    models_data = data.get("models", {})
                    
                    for model_id, config in models_data.items():
                        model_info = ModelInfo(
                            id=model_id,
                            name=config.get("name", model_id),
                            provider=config.get("provider", "unknown"),
                            description=config.get("description", ""),
                            context_window_size=config.get("context_window_size"),
                            model_settings=config.get("model_settings", {}),
                            default_inference=config.get("default_inference", {})
                        )
                        self.models[model_id] = model_info
            else:
                log_warning("ModelsManager", f"models.yaml not found at {self.config_path}", {"config_path": self.config_path})
        except Exception as e:
            raise RuntimeError(f"Error loading models.yaml from {self.config_path}: {str(e)}")
    
    def save_models(self) -> None:
        """Save models to YAML configuration file"""
        # Only create directory if there's a directory path (not empty)
        dir_path = os.path.dirname(self.config_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # Convert ModelInfo objects to dictionaries for YAML serialization
        config_models = {}
        for model_id, model in self.models.items():
            config_models[model_id] = model.model_dump()
        
        data = {
            "models": config_models
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as file:
            yaml.dump(data, file, default_flow_style=False, indent=2)
    
    def discover_models_from_llm(self) -> Dict[str, Any]:
        """Discover models from llm package without loading them"""
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
        """Extract provider name from model object"""
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
    
    def get_all_option_fields(self, options_cls):
        """Get all option fields with their types from a model's Options class"""
        fields = {}
        for cls in options_cls.__mro__:
            if hasattr(cls, "__annotations__"):
                fields.update(cls.__annotations__)
        return fields

    def get_provider_model_schema(self, provider_name: str, is_embedding_model: bool = False) -> Dict[str, Any]:
        """Get schema for a provider's models without loading any models"""
        if provider_name == 'openai':
            try:
                if is_embedding_model:
                    # For embedding models, try to get embedding-specific options
                    import llm.default_plugins.openai_models
                    # Check if there's an Embedding class with Options
                    if hasattr(llm.default_plugins.openai_models, 'Embedding'):
                        Embedding = llm.default_plugins.openai_models.Embedding  # type: ignore[attr-defined]
                        schema = Embedding.Options.model_json_schema()  # type: ignore[attr-defined]
                        # Enhance with type information
                        type_fields = self.get_all_option_fields(Embedding.Options)
                        schema = self._enhance_schema_with_types(schema, type_fields)
                        return schema
                    else:
                        # Fallback to minimal embedding options
                        return {
                            "type": "object",
                            "properties": {
                                "model": {"type": "string"},
                                "encoding_format": {"type": "string", "enum": ["float", "base64"]}
                            }
                        }
                else:
                    # For chat models, get Chat options
                    import llm.default_plugins.openai_models
                    Chat = llm.default_plugins.openai_models.Chat
                    schema = Chat.Options.model_json_schema()
                    # Enhance with type information
                    type_fields = self.get_all_option_fields(Chat.Options)
                    schema = self._enhance_schema_with_types(schema, type_fields)
                    return schema
            except Exception as e:
                log_error("ModelsManager", "Error loading OpenAI schema", e, {"provider": "openai", "is_embedding": is_embedding_model})
        elif provider_name == 'ollama':
            try:
                if is_embedding_model:
                    # For embedding models, try to get embedding-specific options
                    import llm_ollama
                    # Check if there's an embedding-specific class
                    if hasattr(llm_ollama, 'Embedding'):
                        Embedding = llm_ollama.Embedding  # type: ignore[attr-defined]
                        schema = Embedding.Options.model_json_schema()  # type: ignore[attr-defined]
                        # Enhance with type information
                        type_fields = self.get_all_option_fields(Embedding.Options)
                        schema = self._enhance_schema_with_types(schema, type_fields)
                        return schema
                    else:
                        # Fallback to minimal embedding options for Ollama
                        return {
                            "type": "object",
                            "properties": {
                                "model": {"type": "string"},
                                "options": {"type": "object"}
                            }
                        }
                else:
                    # For chat models, get Ollama options
                    import llm_ollama
                    Ollama = llm_ollama.Ollama
                    schema = Ollama.Options.model_json_schema()
                    # Enhance with type information
                    type_fields = self.get_all_option_fields(Ollama.Options)
                    schema = self._enhance_schema_with_types(schema, type_fields)
                    return schema
            except Exception as e:
                log_error("ModelsManager", "Error loading Ollama schema", e, {"provider": "ollama", "is_embedding": is_embedding_model})
        else:
            log_error("ModelsManager", f"Unknown provider: {provider_name}", None, {"provider": provider_name, "is_embedding": is_embedding_model})
        
        return {}

    def _enhance_schema_with_types(self, schema: Dict[str, Any], type_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance JSON schema with proper type information from Python annotations"""
        if not schema.get('properties'):
            return schema
        
        enhanced_schema = schema.copy()
        enhanced_schema['properties'] = enhanced_schema['properties'].copy()
        
        for field_name, field_type in type_fields.items():
            if field_name in enhanced_schema['properties']:
                prop = enhanced_schema['properties'][field_name]
                
                # Convert Python type hints to JSON schema types
                type_str = str(field_type)
                
                if 'int' in type_str:
                    prop['type'] = 'integer'
                    prop['python_type'] = 'int'
                elif 'float' in type_str:
                    prop['type'] = 'number'
                    prop['python_type'] = 'float'
                elif 'bool' in type_str:
                    prop['type'] = 'boolean'
                    prop['python_type'] = 'bool'
                elif 'str' in type_str:
                    prop['type'] = 'string'
                    prop['python_type'] = 'str'
                elif 'Union' in type_str or 'Optional' in type_str:
                    # For Union types, default to string
                    prop['type'] = 'string'
                    prop['python_type'] = 'union'
                else:
                    # Default to string for unknown types
                    prop['type'] = 'string'
                    prop['python_type'] = 'unknown'
        
        return enhanced_schema
    
    def get_all_models_with_discovery(self) -> List[ModelInfoView]:
        """Get all models (configured + discovered) with runtime data"""
        discovered_models = self.discover_models_from_llm()
        processed_names = set()
        result = []
        
        # Add configured models first
        for model_id, model_info in self.models.items():
            processed_names.add(model_id)
            
            # Get runtime data from discovery
            discovered_info = discovered_models.get(model_id, {})
            
            # Get available settings schema
            available_settings = self.get_provider_model_schema(model_info.provider, discovered_info.get('embedding_model', False))
            
            model_view = ModelInfoView(
                id=model_info.id,
                name=model_info.name,
                provider=model_info.provider,
                description=model_info.description,
                context_window_size=model_info.context_window_size,
                model_settings=model_info.model_settings,
                default_inference=model_info.default_inference,
                configured=True,
                supports_schema=discovered_info.get('supports_schema', False),
                supports_tools=discovered_info.get('supports_tools', False),
                can_stream=discovered_info.get('can_stream', False),
                available_settings=available_settings,
                embedding_model=discovered_info.get('embedding_model', False),
                vision=discovered_info.get('vision', False),
                attachment_types=list(discovered_info.get('attachment_types', set())),
                dimensions=discovered_info.get('dimensions', None),
                truncate=discovered_info.get('truncate', False),
                supports_binary=discovered_info.get('supports_binary', False),
                supports_text=discovered_info.get('supports_text', False),
                embed_batch=discovered_info.get('embed_batch', False)
            )
            result.append(model_view)
        
        # Add discovered models that aren't configured
        for model_id, discovered_info in discovered_models.items():
            if model_id not in processed_names:
                # Check if this model supports both chat and embedding
                is_dual_capability = discovered_info.get('is_chat_model', False) and discovered_info.get('is_embedding_model', False)
                
                if is_dual_capability:
                    # Create two entries for the same model - one for chat, one for embedding
                    
                    # Chat model entry (same ID, embedding_model=False)
                    chat_available_settings = self.get_provider_model_schema(discovered_info['provider'], False)
                    chat_model_view = ModelInfoView(
                        id=discovered_info['id'],  # Use original ID
                        name=discovered_info['name'],  # Use original name
                        provider=discovered_info['provider'],
                        description=discovered_info['description'],
                        context_window_size=None,
                        model_settings={},
                        default_inference={},
                        configured=False,
                        supports_schema=discovered_info.get('supports_schema', False),
                        supports_tools=discovered_info.get('supports_tools', False),
                        can_stream=discovered_info.get('can_stream', False),
                        available_settings=chat_available_settings,
                        embedding_model=False,  # This makes it appear in chat models section
                        vision=discovered_info.get('vision', False),
                        attachment_types=list(discovered_info.get('attachment_types', set())),
                        dimensions=None,
                        truncate=False,
                        supports_binary=False,
                        supports_text=False,
                        embed_batch=False
                    )
                    result.append(chat_model_view)
                    
                    # Embedding model entry (same ID, embedding_model=True)
                    embedding_available_settings = self.get_provider_model_schema(discovered_info['provider'], True)
                    embedding_model_view = ModelInfoView(
                        id=discovered_info['id'],  # Use original ID
                        name=discovered_info['name'],  # Use original name
                        provider=discovered_info['provider'],
                        description=discovered_info['description'],
                        context_window_size=None,
                        model_settings={},
                        default_inference={},
                        configured=False,
                        supports_schema=False,
                        supports_tools=False,
                        can_stream=False,
                        available_settings=embedding_available_settings,
                        embedding_model=True,  # This makes it appear in embedding models section
                        vision=False,
                        attachment_types=[],
                        dimensions=discovered_info.get('dimensions', None),
                        truncate=discovered_info.get('truncate', False),
                        supports_binary=discovered_info.get('supports_binary', False),
                        supports_text=discovered_info.get('supports_text', False),
                        embed_batch=discovered_info.get('embed_batch', False)
                    )
                    result.append(embedding_model_view)
                else:
                    # Single capability model
                    available_settings = self.get_provider_model_schema(discovered_info['provider'], discovered_info.get('embedding_model', False))
                    
                    model_view = ModelInfoView(
                        id=discovered_info['id'],
                        name=discovered_info['name'],
                        provider=discovered_info['provider'],
                        description=discovered_info['description'],
                        context_window_size=None,
                        model_settings={},
                        default_inference={},
                        configured=False,
                        supports_schema=discovered_info.get('supports_schema', False),
                        supports_tools=discovered_info.get('supports_tools', False),
                        can_stream=discovered_info.get('can_stream', False),
                        available_settings=available_settings,
                        embedding_model=discovered_info.get('embedding_model', False),
                        vision=discovered_info.get('vision', False),
                        attachment_types=list(discovered_info.get('attachment_types', set())),
                        dimensions=discovered_info.get('dimensions', None),
                        truncate=discovered_info.get('truncate', False),
                        supports_binary=discovered_info.get('supports_binary', False),
                        supports_text=discovered_info.get('supports_text', False),
                        embed_batch=discovered_info.get('embed_batch', False)
                    )
                    result.append(model_view)
        
        return result

    def get_embedding_models(self) -> List[ModelInfoView]:
        """Return only embedding-capable models as ModelInfoView entries."""
        discovered = self.discover_models_from_llm()
        result: List[ModelInfoView] = []

        for model_id, info in discovered.items():
            if info.get('is_embedding_model') or info.get('embedding_model'):
                available_settings = self.get_provider_model_schema(info.get('provider', 'unknown'), True)
                view = ModelInfoView(
                    id=info['id'],
                    name=info.get('name', info['id']),
                    provider=info.get('provider', 'unknown'),
                    description=info.get('description', ''),
                    context_window_size=None,
                    model_settings={},
                    default_inference={},
                    configured=(info['id'] in self.models),
                    supports_schema=False,
                    supports_tools=False,
                    can_stream=False,
                    available_settings=available_settings,
                    embedding_model=True,
                    vision=False,
                    attachment_types=[],
                    dimensions=info.get('dimensions'),
                    truncate=info.get('truncate', False),
                    supports_binary=info.get('supports_binary', False),
                    supports_text=info.get('supports_text', False),
                    embed_batch=info.get('embed_batch', False)
                )
                result.append(view)

        return result
    
    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Get a specific model configuration"""
        return self.models.get(model_id)
    
    def create_model(self, model_config: Dict[str, Any]) -> str:
        """Create a new model configuration"""
        model_id = model_config['id']
        
        if model_id in self.models:
            raise ValueError(f"Model '{model_id}' already exists")
        
        model_info = ModelInfo(**model_config)
        self.models[model_id] = model_info
        self.save_models()
        
        return model_id
    
    def update_model(self, model_id: str, model_config: Dict[str, Any]) -> None:
        """Update an existing model configuration or create a new one if it's discovered"""
        if model_id not in self.models:
            # Check if this is a discovered model that needs to be created
            discovered_models = self.discover_models_from_llm()
            
            # Check if it's a regular discovered model
            if model_id in discovered_models:
                discovered_info = discovered_models[model_id]
                
                # Create new model configuration
                new_model_config = {
                    'id': model_id,
                    'name': model_config.get('name', discovered_info['name']),
                    'provider': discovered_info['provider'],
                    'description': model_config.get('description', discovered_info['description']),
                    'context_window_size': model_config.get('context_window_size'),
                    'model_settings': model_config.get('model_settings', {}),
                    'default_inference': model_config.get('default_inference', {})
                }
                
                # Create the model
                self.create_model(new_model_config)
            else:
                raise ValueError(f"Model '{model_id}' not found and not discovered")

        
        # Update the model (now it exists in self.models)
        current_model = self.models[model_id]
        for key, value in model_config.items():
            if hasattr(current_model, key):
                setattr(current_model, key, value)
        
        self.save_models()
    
    def delete_model(self, model_id: str) -> None:
        """Delete a model configuration"""
        if model_id not in self.models:
            raise ValueError(f"Model '{model_id}' not found")
        
        del self.models[model_id]
        self.save_models()
    
    def get_model_settings_schema(self, model_id: str) -> Dict[str, Any]:
        """Get settings schema for a model without loading it"""
        # First check if it's a configured model
        model_info = self.models.get(model_id)
        if model_info:
            # Get discovered info to determine if it's an embedding model
            discovered_models = self.discover_models_from_llm()
            discovered_info = discovered_models.get(model_id, {})
            return self.get_provider_model_schema(model_info.provider, discovered_info.get('embedding_model', False))
        
        # If not configured, check discovered models
        discovered_models = self.discover_models_from_llm()
        discovered_info = discovered_models.get(model_id)
        if discovered_info:
            return self.get_provider_model_schema(discovered_info['provider'], discovered_info.get('embedding_model', False))
        
        return {}
    
    def get_available_settings_for_provider(self, provider_name: str) -> List[str]:
        """Get list of available settings for a provider"""
        schema = self.get_provider_model_schema(provider_name)
        return list(schema.get('properties', {}).keys()) 