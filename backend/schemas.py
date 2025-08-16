from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union, TYPE_CHECKING
from enum import Enum
import json

if TYPE_CHECKING:
    from agent import Agent

class UnknownActionError(Exception):
    """Raised when an LLM response contains an unknown or illegal action type."""
    pass

class MessageType(str, Enum):
    USER_MESSAGE = "USER_MESSAGE"
    CHAT_RESPONSE = "CHAT_RESPONSE"
    CHAT_RESPONSE_WAIT_USER_INPUT = "CHAT_RESPONSE_WAIT_USER_INPUT"
    CHAT_RESPONSE_CONTINUE_WORK = "CHAT_RESPONSE_CONTINUE_WORK"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RETURN = "TOOL_RETURN"
    AGENT_CALL = "AGENT_CALL"
    AGENT_RETURN = "AGENT_RETURN"
    AGENT_DELEGATE = "AGENT_DELEGATE"
    REFINEMENT_RESPONSE = "REFINEMENT_RESPONSE"
    SYSTEM = "SYSTEM"
    ERROR = "ERROR"

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
    content: str

    def __init__(self, content: str, reasoning: str, agent: 'Agent'):
        self._agent = agent
        self._model = agent.config.model
        self._agent_id = agent.id
        super().__init__(
            action=MessageType.CHAT_RESPONSE.value,
            reasoning=reasoning
        )
        # Set the specific fields after parent constructor
        self.content = content

    def to_ui(self, icon: Optional[MessageIcon] = None) -> 'UIChatResponse':
        """Convert to UI response"""
        return UIChatResponse(self, self._model, self._agent_id, icon)

class ErrorChatResponse(ChatResponse):
    def __init__(self, error: Exception | str, agent: 'Agent'):
        content = f"Error: {str(error)}"
        # Default reasoning per spec
        super().__init__(content=content, reasoning="An error has occurred; details are in the content.", agent=agent)

    def to_ui(self) -> 'UIErrorChatResponse':
        """Convert to UI response"""
        return UIErrorChatResponse(self, self._model, self._agent_id, MessageIcon.ERROR)

class ToolCallResponse(StructuredResponse):
    tool: str
    args: Dict[str, Any]

    def __init__(self, tool: str, args: Dict[str, Any], reasoning: str, agent: 'Agent'):
        self._agent = agent
        self._model = agent.config.model
        self._agent_id = agent.id
        super().__init__(
            action=MessageType.TOOL_CALL.value,
            reasoning=reasoning
        )
        # Set the specific fields after parent constructor
        self.tool = tool
        self.args = args

    def to_ui(self) -> 'UIToolCallResponse':
        """Convert to UI response"""
        return UIToolCallResponse(self, self._model, self._agent_id)

class ToolReturnResponse(StructuredResponse):
    tool: str
    result: str
    success: str = Field(..., pattern="^(True|False)$")

    def __init__(self, tool: str, result: str, success: str, reasoning: str, agent: 'Agent'):
        self._agent = agent
        self._model = agent.config.model
        self._agent_id = agent.id
        super().__init__(
            action=MessageType.TOOL_RETURN.value,
            reasoning=reasoning
        )
        # Set the specific fields after parent constructor
        self.tool = tool
        self.result = result
        self.success = success

    def to_ui(self) -> 'UIToolReturnResponse':
        """Convert to UI response"""
        return UIToolReturnResponse(self, self._model, self._agent_id)

class AgentDelegateResponse(StructuredResponse):
    agent_id: str
    caller_agent_id: str
    user_input: str

    def __init__(self, target_agent: 'Agent', caller_agent: 'Agent', user_input: str, reasoning: str):
        self._caller_agent = caller_agent
        self._model = caller_agent.config.model
        self._agent_id = caller_agent.id
        super().__init__(
            action=MessageType.AGENT_DELEGATE.value,
            reasoning=reasoning
        )
        # Set the specific fields after parent constructor
        self.agent_id = target_agent.id
        self.caller_agent_id = caller_agent.id
        self.user_input = user_input

    def to_ui(self) -> 'UIAgentDelegateResponse':
        """Convert to UI response"""
        return UIAgentDelegateResponse(self, self._model, self._agent_id)

class AgentCallResponse(StructuredResponse):
    agent_id: str
    caller_agent_id: str
    user_input: str

    def __init__(self, target_agent: 'Agent', caller_agent: 'Agent', user_input: str, reasoning: str):
        self._caller_agent = caller_agent
        self._model = caller_agent.config.model
        self._agent_id = caller_agent.id
        super().__init__(
            action=MessageType.AGENT_CALL.value,
            reasoning=reasoning
        )
        # Set the specific fields after parent constructor
        self.agent_id = target_agent.id
        self.caller_agent_id = caller_agent.id
        self.user_input = user_input

    def to_ui(self) -> 'UIAgentCallResponse':
        """Convert to UI response"""
        return UIAgentCallResponse(self, self._model, self._agent_id)

class AgentReturnResponse(StructuredResponse):
    """Response from an agent call"""
    agent: str
    returning_agent: str
    success: str = Field(..., pattern="^(True|False)$")

    def __init__(self, return_to_agent: 'Agent', returning_agent: 'Agent', is_success: bool, reasoning: str):
        self._return_to_agent = return_to_agent
        self._model = return_to_agent.config.model
        self._agent_id = return_to_agent.id
        super().__init__(
            action=MessageType.AGENT_RETURN.value,
            reasoning=reasoning
        )
        # Set the specific fields after parent constructor
        self.agent = return_to_agent.id
        self.returning_agent = returning_agent.id
        self.success = "True" if is_success else "False"

    def to_ui(self) -> 'UIAgentReturnResponse':
        """Convert to UI response"""
        return UIAgentReturnResponse(self, self._model, self._agent_id)

class RefinementChecklist(BaseModel):
    objective: bool
    inputs: bool
    outputs: bool
    constraints: bool

class RefinementResponse(BaseModel):
    action: str = Field(default=MessageType.REFINEMENT_RESPONSE.value)
    new_plan: str
    done: str = Field(..., pattern="^(yes|no)$")
    score: int = Field(..., ge=0, le=100)
    why: str
    checklist: RefinementChecklist
    success: bool

    def to_ui(self, model: str, agent_id: str) -> 'UIRefinementResponse':
        """Convert to UI response"""
        return UIRefinementResponse(self, model, agent_id)

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
    default: bool = False
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

    @classmethod
    def create_user_message(cls, agent_id: str, content: str) -> 'Message':
        """Create a user message for the specified agent"""
        import uuid
        from datetime import datetime
        
        return cls(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            content=content,
            message_type=MessageType.USER_MESSAGE,
            timestamp=datetime.now().isoformat()
        )

class ChatSession(BaseModel):
    id: str
    agent_id: str
    messages: List[Message] = []
    created_at: str
    updated_at: str
    summary: Optional[str] = None

class UILLMResponse(BaseModel):
    """Base class for all UI-specific LLM responses"""
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

    def as_message_to_agent(self, agent_id: str) -> 'Message':
        """Convert this UILLMResponse to a Message for the specified agent"""
        import uuid
        from datetime import datetime
        
        return Message(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            content=self.content,
            message_type=(MessageType.ERROR if self.icon == MessageIcon.ERROR else self.message_type),
            timestamp=datetime.now().isoformat(),
            metadata=self.metadata,
            action=self.action,
            reasoning=self.reasoning,
            tool_name=self.tool_name,
            tool_parameters=self.tool_parameters,
            target_agent_id=self.target_agent_id
        )


class UIChatResponse(UILLMResponse):
    """UI wrapper for ChatResponse"""
    def __init__(self, chat_response: ChatResponse, model: str, agent_id: str, icon: Optional[MessageIcon] = None):
        super().__init__(
            content=chat_response.content,
            message_type=MessageType.CHAT_RESPONSE,
            metadata={
                "model": model,
                "agent_id": agent_id,
                "action": chat_response.action,
            },
            action=chat_response.action,
            reasoning=chat_response.reasoning,
            icon=icon
        )


class UIErrorChatResponse(UILLMResponse):
    """UI wrapper for ErrorChatResponse"""
    def __init__(self, error_response: ErrorChatResponse, model: str, agent_id: str, icon: Optional[MessageIcon] = None):
        super().__init__(
            content=error_response.content,
            message_type=MessageType.ERROR,
            metadata={
                "model": model,
                "agent_id": agent_id,
                "action": error_response.action,
            },
            action=error_response.action,
            reasoning=error_response.reasoning,
            icon=icon
        )


class UIToolCallResponse(UILLMResponse):
    """UI wrapper for ToolCallResponse"""
    def __init__(self, tool_call: ToolCallResponse, model: str, agent_id: str):
        super().__init__(
            content=f"Calling tool {tool_call.tool}",
            message_type=MessageType.TOOL_CALL,
            metadata={
                "model": model,
                "agent_id": agent_id,
                "action": tool_call.action,
                "tool": tool_call.tool,
                "args": tool_call.args,
            },
            action=tool_call.action,
            reasoning=tool_call.reasoning,
            tool_name=tool_call.tool,
            tool_parameters=tool_call.args
        )


class UIToolReturnResponse(UILLMResponse):
    """UI wrapper for ToolReturnResponse"""
    def __init__(self, tool_return: ToolReturnResponse, model: str, agent_id: str):
        super().__init__(
            content=tool_return.result,
            message_type=MessageType.TOOL_RETURN,
            metadata={
                "model": model,
                "agent_id": agent_id,
                "action": tool_return.action,
                "tool": tool_return.tool,
                "success": tool_return.success,
            },
            action=tool_return.action,
            tool_name=tool_return.tool
        )


class UIAgentDelegateResponse(UILLMResponse):
    """UI wrapper for AgentDelegateResponse"""
    def __init__(self, agent_delegate: AgentDelegateResponse, model: str, agent_id: str):
        super().__init__(
            content=f"Delegating to agent {agent_delegate.agent_id}",
            message_type=MessageType.AGENT_DELEGATE,
            metadata={
                "model": model,
                "agent_id": agent_id,
                "action": agent_delegate.action,
                "target_agent": agent_delegate.agent_id,
                "caller_agent": agent_delegate.caller_agent_id,
            },
            action=agent_delegate.action,
            reasoning=agent_delegate.reasoning,
            target_agent_id=agent_delegate.agent_id
        )


class UIAgentCallResponse(UILLMResponse):
    """UI wrapper for AgentCallResponse"""
    def __init__(self, agent_call: AgentCallResponse, model: str, agent_id: str):
        super().__init__(
            content=f"Calling agent {agent_call.agent_id}",
            message_type=MessageType.AGENT_CALL,
            metadata={
                "model": model,
                "agent_id": agent_id,
                "action": agent_call.action,
                "target_agent": agent_call.agent_id,
                "caller_agent": agent_call.caller_agent_id,
            },
            action=agent_call.action,
            reasoning=agent_call.reasoning,
            target_agent_id=agent_call.agent_id
        )


class UIAgentReturnResponse(UILLMResponse):
    """UI wrapper for AgentReturnResponse"""
    def __init__(self, agent_return: AgentReturnResponse, model: str, agent_id: str):
        super().__init__(
            content=f"Return from agent {agent_return.returning_agent}",
            message_type=MessageType.AGENT_RETURN,
            metadata={
                "model": model,
                "agent_id": agent_id,
                "action": agent_return.action,
                "returning_agent": agent_return.returning_agent,
                "success": agent_return.success,
            },
            action=agent_return.action,
            reasoning=agent_return.reasoning,
            target_agent_id=agent_return.returning_agent
        )


class UIRefinementResponse(UILLMResponse):
    """UI wrapper for RefinementResponse"""
    def __init__(self, refinement: RefinementResponse, model: str, agent_id: str):
        super().__init__(
            content=f"Refinement: {refinement.new_plan}",
            message_type=MessageType.REFINEMENT_RESPONSE,
            metadata={
                "model": model,
                "agent_id": agent_id,
                "action": refinement.action,
                "done": refinement.done,
                "score": refinement.score,
                "success": refinement.success,
            },
            action=refinement.action,
            reasoning=refinement.why
        )

class SessionRef(BaseModel):
    agent_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)



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
    agent_response: UILLMResponse 

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
    attachment_types: List[str] = Field(default_factory=list)
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
    agent_response: UILLMResponse
    session: ChatSession
    context_usage: float = Field(ge=0.0, le=100.0, description="Percentage of context window used")
    tokens_used: Optional[int] = Field(None, ge=0, description="Number of tokens used")
    context_window: Optional[int] = Field(None, ge=0, description="Total context window size")
    messages_to_send: List[UILLMResponse] = Field(default_factory=list, description="Messages to send to frontend")

class ConversationData(BaseModel):
    """Conversation data for persistence"""
    session_id: str
    agent_id: str
    agent_name: str
    model: str
    created_at: str
    responses: List[Dict[str, Any]] = Field(default_factory=list, description="List of conversation responses")

class SafeList:
    """Thread-safe list wrapper with proper locking for all operations"""
    
    def __init__(self):
        import threading
        self._list = []
        self._lock = threading.RLock()
    
    def append(self, item) -> None:
        """Thread-safe append"""
        with self._lock:
            self._list.append(item)
    
    def clear(self) -> None:
        """Thread-safe clear"""
        with self._lock:
            self._list.clear()
    
    def copy(self) -> list:
        """Thread-safe copy"""
        with self._lock:
            return self._list.copy()
    
    def __len__(self) -> int:
        """Thread-safe length"""
        with self._lock:
            return len(self._list)
    
    def __iter__(self):
        """Thread-safe iteration (returns a copy to avoid holding lock during iteration)"""
        with self._lock:
            return iter(self._list.copy())
    
    def __getitem__(self, index):
        """Thread-safe indexing"""
        with self._lock:
            return self._list[index]
    
    def __setitem__(self, index, value):
        """Thread-safe assignment"""
        with self._lock:
            self._list[index] = value
    
    def extend(self, items) -> None:
        """Thread-safe extend"""
        with self._lock:
            self._list.extend(items)
    
    def insert(self, index, item) -> None:
        """Thread-safe insert"""
        with self._lock:
            self._list.insert(index, item)
    
    def pop(self, index=-1):
        """Thread-safe pop"""
        with self._lock:
            return self._list.pop(index)
    
    def remove(self, item) -> None:
        """Thread-safe remove"""
        with self._lock:
            self._list.remove(item)
    
    def reverse(self) -> None:
        """Thread-safe reverse"""
        with self._lock:
            self._list.reverse()
    
    def sort(self, key=None, reverse=False) -> None:
        """Thread-safe sort"""
        with self._lock:
            self._list.sort(key=key, reverse=reverse)

class MessageHistory:
    """Thread-safe conversation history management"""
    
    def __init__(self, agent_id: str):
        self._messages = SafeList()
        self._agent_id = agent_id
    
    def append_llm_response(self, llm_response: 'UILLMResponse') -> None:
        """Append LLM response as message"""
        message = llm_response.as_message_to_agent(self._agent_id)
        self._messages.append(message)
    
    def append_user_message(self, content: str) -> None:
        """Append user message"""
        message = Message.create_user_message(self._agent_id, content)
        self._messages.append(message)
    
    def append_existing_message(self, message: 'Message') -> None:
        """Append an existing message (for loading from history)"""
        self._messages.append(message)
    
    def get_messages(self) -> List['Message']:
        """Get copy of all messages"""
        return self._messages.copy()
    
    def clear(self) -> None:
        """Clear all messages"""
        self._messages.clear()
    
    def __len__(self) -> int:
        return len(self._messages)
    
    def __iter__(self):
        return iter(self._messages)
    
    def pop(self, index: int) -> 'Message':
        """Remove and return message at index"""
        return self._messages.pop(index)
    
    def insert(self, index: int, message: 'Message') -> None:
        """Insert message at index"""
        self._messages.insert(index, message)

# Type alias for all structured response types
StructuredResponseType = Union[ChatResponse, ErrorChatResponse, ToolCallResponse, ToolReturnResponse, 
                              AgentDelegateResponse, AgentCallResponse, AgentReturnResponse, RefinementResponse]

 