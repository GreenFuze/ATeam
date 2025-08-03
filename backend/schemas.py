from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import json

class MessageType(str, Enum):
    CHAT_RESPONSE = "CHAT_RESPONSE"
    USE_TOOL = "USE_TOOL"
    TOOL_RETURN = "TOOL_RETURN"
    AGENT_CALL = "AGENT_CALL"
    AGENT_RETURN = "AGENT_RETURN"
    AGENT_DELEGATE = "AGENT_DELEGATE"
    REFINEMENT_RESPONSE = "REFINEMENT_RESPONSE"
    SYSTEM = "SYSTEM"

class MessageIcon(str, Enum):
    CHAT = "chat"
    TOOL = "tool"
    AGENT = "agent"
    ERROR = "error"
    WARNING = "warning"
    SUCCESS = "success"
    INFO = "info"

class PromptType(str, Enum):
    SYSTEM = "system"
    SEED = "seed"

# Base class for all structured responses
class StructuredResponse(BaseModel):
    action: str
    reasoning: str

# Specific response classes
class ChatResponse(StructuredResponse):
    action: str = Field(default="CHAT_RESPONSE")
    content: str
    icon: Optional[MessageIcon] = None

class ToolCallResponse(StructuredResponse):
    action: str = Field(default="USE_TOOL")
    tool: str
    args: Dict[str, Any]

class ToolReturnResponse(BaseModel):
    action: str = Field(default="TOOL_RETURN")
    tool: str
    result: str
    success: str = Field(..., pattern="^(True|False)$")

class AgentDelegateResponse(StructuredResponse):
    action: str = Field(default="AGENT_DELEGATE")
    agent: str
    caller_agent: str
    user_input: str

class AgentCallResponse(StructuredResponse):
    action: str = Field(default="AGENT_CALL")
    agent: str
    caller_agent: str
    user_input: str

class AgentReturnResponse(StructuredResponse):
    action: str = Field(default="AGENT_RETURN")
    agent: str
    returning_agent: str
    success: str = Field(..., pattern="^(True|False)$")

class RefinementChecklist(BaseModel):
    objective: bool
    inputs: bool
    outputs: bool
    constraints: bool

class RefinementResponse(BaseModel):
    action: str = Field(default="REFINEMENT_RESPONSE")
    new_plan: str
    done: str = Field(..., pattern="^(yes|no)$")
    score: int = Field(..., ge=0, le=100)
    why: str
    checklist: RefinementChecklist
    success: bool

# Union type for all possible responses
StructuredResponseType = Union[
    ChatResponse,
    ToolCallResponse,
    ToolReturnResponse,
    AgentDelegateResponse,
    AgentCallResponse,
    AgentReturnResponse,
    RefinementResponse
]

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
    icon: Optional[MessageIcon] = None
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

class ContextUsageData(BaseModel):
    """Context usage information for a conversation"""
    percentage: float = Field(ge=0.0, le=100.0, description="Percentage of context window used")
    tokens_used: int = Field(ge=0, description="Number of tokens used in conversation")
    context_window: Optional[int] = Field(None, ge=0, description="Total context window size in tokens")

class ConversationResponseData(BaseModel):
    """Response data for conversation processing"""
    session_id: str
    agent_response: LLMResponse
    session: ChatSession
    context_usage: float = Field(ge=0.0, le=100.0, description="Percentage of context window used")
    tokens_used: Optional[int] = Field(None, ge=0, description="Number of tokens used")
    context_window: Optional[int] = Field(None, ge=0, description="Total context window size")
    messages_to_send: List[LLMResponse] = Field(default_factory=list, description="Messages to send to frontend")

class AgentInfo(BaseModel):
    """Agent information returned by Agent class"""
    id: str
    name: str
    description: str
    model: str
    tools: List[str] = Field(default_factory=list, description="List of tool names")
    conversation_initialized: bool = False

class ConversationData(BaseModel):
    """Conversation data for persistence"""
    session_id: str
    agent_id: str
    agent_name: str
    model: str
    created_at: str
    responses: List[Dict[str, Any]] = Field(default_factory=list, description="List of conversation responses")

 