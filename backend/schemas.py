from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import json

class MessageType(str, Enum):
    NORMAL_RESPONSE = "NORMAL_RESPONSE"
    USE_TOOL = "USE_TOOL"
    TOOL_RETURN = "TOOL_RETURN"
    AGENT_CALL = "AGENT_CALL"
    AGENT_RETURN = "AGENT_RETURN"
    REFINEMENT_RESPONSE = "REFINEMENT_RESPONSE"
    SYSTEM = "SYSTEM"

class PromptType(str, Enum):
    SYSTEM = "system"
    SEED = "seed"

class AgentConfig(BaseModel):
    id: str
    name: str
    description: str
    model: str
    prompts: List[str] = []
    tools: List[str] = []
    schema_file: Optional[str] = None
    grammar_file: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    enable_summarization: bool = True
    enable_scratchpad: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ToolConfig(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = {}
    file_path: Optional[str] = None

class PromptConfig(BaseModel):
    name: str
    content: str
    type: PromptType = PromptType.SYSTEM
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class Message(BaseModel):
    id: str
    agent_id: str
    content: str
    message_type: MessageType
    timestamp: str
    metadata: Dict[str, Any] = {}
    
    # For tool calls
    tool_name: Optional[str] = None
    tool_parameters: Optional[Dict[str, Any]] = None
    tool_result: Optional[Any] = None
    
    # For agent calls
    target_agent_id: Optional[str] = None
    agent_result: Optional[str] = None
    
    # For structured responses
    action: Optional[str] = None
    reasoning: Optional[str] = None

class ChatSession(BaseModel):
    id: str
    agent_id: str
    messages: List[Message] = []
    created_at: str
    updated_at: str
    summary: Optional[str] = None

class LLMResponse(BaseModel):
    content: str
    message_type: MessageType
    metadata: Dict[str, Any] = {}
    
    # Structured response fields
    action: Optional[str] = None
    reasoning: Optional[str] = None
    tool_name: Optional[str] = None
    tool_parameters: Optional[Dict[str, Any]] = None
    target_agent_id: Optional[str] = None

class CreateAgentRequest(BaseModel):
    name: str
    description: str
    model: str
    prompts: List[str] = []
    tools: List[str] = []
    schema_file: Optional[str] = None
    grammar_file: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    enable_summarization: bool = True
    enable_scratchpad: bool = True

class CreateToolRequest(BaseModel):
    name: str
    description: str
    code: str
    parameters: Dict[str, Any] = {}

class CreatePromptRequest(BaseModel):
    name: str
    content: str
    type: PromptType = PromptType.SYSTEM

class UpdatePromptRequest(BaseModel):
    name: str
    content: str
    type: PromptType

class SeedMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str

class SeedPromptData(BaseModel):
    messages: List[SeedMessage]

class ChatMessageRequest(BaseModel):
    content: str
    session_id: Optional[str] = None

class ChatMessageResponse(BaseModel):
    message: Message
    session_id: str
    agent_response: LLMResponse 

class ProviderInfo(BaseModel):
    """Provider configuration information stored in YAML"""
    name: str
    display_name: str
    description: str
    api_key_required: bool
    api_key_env_var: Optional[str]
    base_url: Optional[str]

class ProviderInfoView(BaseModel):
    """Provider information returned to frontend (includes runtime data)"""
    # Configuration data from ProviderInfo
    name: str
    display_name: str
    description: str
    api_key_required: bool
    api_key_env_var: Optional[str]
    base_url: Optional[str]
    
    # Runtime data (determined at runtime)
    configured: bool
    chat_models: int
    embedding_models: int

class ModelInfo(BaseModel):
    """Model configuration information stored in YAML"""
    id: str  # model_id from llm package
    name: str  # display name
    provider: str  # provider key from providers.yaml
    description: str
    context_window_size: Optional[int] = None  # Context window size in tokens
    model_settings: Dict[str, Any] = {}  # User preferences for model instance
    default_inference: Dict[str, Any] = {}  # User preferences for inference

class ModelInfoView(BaseModel):
    """Model information returned to frontend (includes runtime data)"""
    # Configuration data from ModelInfo
    id: str
    name: str
    provider: str
    description: str
    context_window_size: Optional[int] = None
    model_settings: Dict[str, Any]
    default_inference: Dict[str, Any]
    
    # Runtime data (from llm package discovery)
    configured: bool
    supports_schema: bool
    supports_tools: bool
    can_stream: bool
    available_settings: Dict[str, Any]  # Schema from model.Options.model_json_schema()
    embedding_model: bool
    
    # Badge attributes
    vision: bool = False
    attachment_types: set = set()
    dimensions: Optional[int] = None
    truncate: bool = False
    supports_binary: bool = False
    supports_text: bool = False
    embed_batch: bool = False 