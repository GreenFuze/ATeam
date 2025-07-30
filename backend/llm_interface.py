import json
import asyncio
from typing import Dict, List, Optional, Any, Union
from models import LLMResponse, MessageType
import os
import yaml
from datetime import datetime

class LLMInterface:
    def __init__(self):
        self.models_config = self._load_models_config()
        self.available_models = self._get_available_models()
        self.model_capabilities = self._get_model_capabilities()
        
    def _load_models_config(self) -> Dict[str, Any]:
        """Load models configuration from models.yaml"""
        config_path = os.path.join(os.path.dirname(__file__), "models.yaml")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: models.yaml not found at {config_path}")
            return {"models": {}, "defaults": {}}
        except Exception as e:
            print(f"Error loading models.yaml: {e}")
            return {"models": {}, "defaults": {}}
        
    def _get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models from configuration"""
        models = []
        for model_id, config in self.models_config.get("models", {}).items():
            models.append({
                "id": model_id,
                "name": config.get("name", model_id),
                "provider": config.get("provider", "unknown"),
                "supports_schema": config.get("supports_schema", False),
                "supports_grammar": config.get("supports_grammar", False),
                "max_tokens": config.get("max_tokens", 4096),
                "description": config.get("description", "")
            })
        return models
    
    def _get_model_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Get model capabilities from configuration"""
        capabilities = {}
        for model_id, config in self.models_config.get("models", {}).items():
            capabilities[model_id] = {
                "supports_schema": config.get("supports_schema", False),
                "supports_grammar": config.get("supports_grammar", False),
                "max_tokens": config.get("max_tokens", 4096)
            }
        return capabilities
    
    def get_model_provider(self, model_id: str) -> Optional[str]:
        """Get the provider for a specific model"""
        model_config = self.models_config.get("models", {}).get(model_id)
        if model_config:
            return model_config.get("provider")
        return None
    
    def get_provider_info(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get provider information from providers.yaml"""
        providers_path = os.path.join(os.path.dirname(__file__), "providers.yaml")
        try:
            with open(providers_path, 'r', encoding='utf-8') as f:
                providers_data = yaml.safe_load(f)
                for provider in providers_data.get("providers", []):
                    if provider.get("name") == provider_name:
                        return {
                            "name": provider.get("name"),
                            "display_name": provider.get("display_name"),
                            "description": provider.get("description"),
                            "api_key_required": provider.get("api_key_required", False),
                            "api_key_env_var": provider.get("api_key_env_var"),
                            "base_url": provider.get("base_url")
                        }
        except Exception as e:
            print(f"Error loading provider info: {e}")
        return None
    
    def supports_schema(self, model_id: str) -> bool:
        """Check if a model supports schema"""
        return self.model_capabilities.get(model_id, {}).get("supports_schema", False)
    
    def supports_grammar(self, model_id: str) -> bool:
        """Check if a model supports grammar"""
        return self.model_capabilities.get(model_id, {}).get("supports_grammar", False)
    
    def get_max_tokens(self, model_id: str) -> int:
        """Get max tokens for a model"""
        return self.model_capabilities.get(model_id, {}).get("max_tokens", 4096)
    
    def get_default_model(self) -> str:
        """Get the default model from configuration"""
        return self.models_config.get("defaults", {}).get("model", "gpt-4")
    
    def get_default_temperature(self) -> float:
        """Get the default temperature from configuration"""
        return self.models_config.get("defaults", {}).get("temperature", 0.7)
    
    def get_default_max_tokens(self) -> int:
        """Get the default max tokens from configuration"""
        return self.models_config.get("defaults", {}).get("max_tokens", 4096)
    
    async def chat(self, 
                  model_id: str, 
                  messages: List[Dict[str, str]], 
                  temperature: float = 0.7,
                  max_tokens: Optional[int] = None,
                  schema: Optional[Dict[str, Any]] = None,
                  grammar: Optional[str] = None,
                  tools: Optional[List[Dict[str, Any]]] = None) -> LLMResponse:
        """
        Chat with an LLM model using the llm package
        
        Args:
            model_id: The model to use
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            schema: JSON schema for structured output
            grammar: Grammar for constrained output
            tools: List of available tools
            
        Returns:
            LLMResponse object
        """
        try:
            # Import llm package
            import llm
            
            # Get the model
            model = llm.get_model(model_id)
            if not model:
                return self._mock_response(messages, model_id)
            
            # Convert messages to prompt
            prompt = self._messages_to_prompt(messages)
            
            # Prepare options
            options: Dict[str, Any] = {}
            if temperature is not None:
                options["temperature"] = temperature
            if max_tokens is not None:
                options["max_tokens"] = max_tokens
            
            # Add schema if supported
            if schema and self.supports_schema(model_id):
                prompt = self.inject_schema_instructions(prompt, model_id)
                options["schema"] = schema
            
            # Add grammar if supported
            if grammar and self.supports_grammar(model_id):
                prompt = self.inject_grammar_instructions(prompt, model_id)
                options["grammar"] = grammar
            
            # Add tools if provided
            if tools:
                tool_schema = self.get_tool_schema(tools)
                if tool_schema:
                    options["schema"] = tool_schema
            
            # Make the request
            response_data = await self._make_llm_request(model, prompt, options)
            
            # Parse the response
            return self._parse_response(response_data, model_id)
            
        except ImportError:
            print("llm package not available, using mock response")
            return self._mock_response(messages, model_id)
        except Exception as e:
            print(f"Error in chat: {e}")
            return self._mock_response(messages, model_id)
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert message list to a single prompt string"""
        prompt_parts = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
            else:
                prompt_parts.append(f"{role.title()}: {content}")
        
        return "\n\n".join(prompt_parts)
    
    async def _make_llm_request(self, model, prompt: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Make the actual request using the llm package"""
        try:
            # Use the model's prompt method (this is synchronous in llm package)
            response = model.prompt(prompt, **options)
            
            # Convert to our expected format
            return {
                "content": response.text(),
                "model": model.model_id,
                "usage": getattr(response, 'usage', {}),
                "metadata": getattr(response, 'metadata', {})
            }
                
        except Exception as e:
            raise Exception(f"LLM request failed: {str(e)}")
    
    def _parse_response(self, response: Dict[str, Any], model_id: str) -> LLMResponse:
        """Parse the LLM response into our format"""
        content = response.get("content", "")
        
        # Try to parse as JSON to detect structured responses
        try:
            parsed = json.loads(content)
            message_type = self._determine_message_type(parsed)
            
            return LLMResponse(
                content=content,
                message_type=message_type,
                metadata={
                    "model": model_id,
                    "parsed": parsed,
                    "usage": response.get("usage", {}),
                    **response.get("metadata", {})
                }
            )
        except json.JSONDecodeError:
            # Not JSON, treat as normal response
            return LLMResponse(
                content=content,
                message_type=MessageType.NORMAL_RESPONSE,
                metadata={
                    "model": model_id,
                    "usage": response.get("usage", {}),
                    **response.get("metadata", {})
                }
            )
    
    def _determine_message_type(self, parsed: Dict[str, Any]) -> MessageType:
        """Determine the message type based on parsed response"""
        action = parsed.get("action", "").upper()
        
        if action == "USE_TOOL":
            return MessageType.USE_TOOL
        elif action == "AGENT_CALL":
            return MessageType.AGENT_CALL
        else:
            return MessageType.NORMAL_RESPONSE
    
    def _mock_response(self, messages: List[Dict[str, str]], model_id: str) -> LLMResponse:
        """Generate a mock response for testing"""
        # Get the last user message
        last_user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break
        
        # Generate a mock response
        mock_content = f"This is a mock response from {model_id}. "
        if last_user_message:
            mock_content += f"You said: '{last_user_message}'. "
        mock_content += "This is a placeholder response since the actual LLM is not available."
        
        return LLMResponse(
            content=mock_content,
            message_type=MessageType.NORMAL_RESPONSE,
            metadata={
                "model": model_id,
                "mock": True,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def inject_schema_instructions(self, prompt: str, model_id: str) -> str:
        """Inject schema instructions into the prompt"""
        if not self.supports_schema(model_id):
            return prompt
        
        schema_instructions = """
IMPORTANT: You must respond with valid JSON that matches the following schema.
Your response should be a JSON object with the specified structure.
"""
        return schema_instructions + "\n\n" + prompt
    
    def inject_grammar_instructions(self, prompt: str, model_id: str) -> str:
        """Inject grammar instructions into the prompt"""
        if not self.supports_grammar(model_id):
            return prompt
        
        grammar_instructions = """
IMPORTANT: You must respond using the specified grammar format.
Follow the grammar rules exactly in your response.
"""
        return grammar_instructions + "\n\n" + prompt
    
    def get_tool_schema(self, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert tools list to JSON schema format"""
        if not tools:
            return {}
        
        tool_schema = {
            "type": "object",
            "properties": {
                "tools": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "parameters": {"type": "object"}
                        },
                        "required": ["name", "parameters"]
                    }
                }
            }
        }
        
        return tool_schema
    
    def call_provider_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call a provider tool using the llm package"""
        try:
            import llm
            
            # Extract the model name from the tool name (e.g., "gpt-4" from "gpt-4_provider")
            model_id = tool_name.replace("_provider", "")
            
            # Get the model
            model = llm.get_model(model_id)
            if not model:
                return {
                    "success": False,
                    "error": f"Model {model_id} not found",
                    "data": {}
                }
            
            # Get the prompt from parameters
            prompt = parameters.get("prompt", "")
            if not prompt:
                return {
                    "success": False,
                    "error": "No prompt provided",
                    "data": {}
                }
            
            # Prepare options
            options = {}
            if "temperature" in parameters:
                options["temperature"] = parameters["temperature"]
            if "max_tokens" in parameters:
                options["max_tokens"] = parameters["max_tokens"]
            
            # Make the request
            response = model.prompt(prompt, **options)
            
            return {
                "success": True,
                "result": response.text(),
                "data": {
                    "model": model_id,
                    "usage": getattr(response, 'usage', {}),
                    "metadata": getattr(response, 'metadata', {})
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": {}
            }
    
    def validate_provider_tool(self, tool_name: str) -> bool:
        """Validate if a provider tool can be used"""
        try:
            import llm
            
            # Extract the model name from the tool name
            model_id = tool_name.replace("_provider", "")
            
            # Check if the model exists
            model = llm.get_model(model_id)
            return model is not None
        except Exception:
            return False 