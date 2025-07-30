export enum MessageType {
  NORMAL_RESPONSE = "NORMAL_RESPONSE",
  USE_TOOL = "USE_TOOL",
  TOOL_RETURN = "TOOL_RETURN",
  AGENT_CALL = "AGENT_CALL",
  AGENT_RETURN = "AGENT_RETURN",
  REFINEMENT_RESPONSE = "REFINEMENT_RESPONSE",
  SYSTEM = "SYSTEM"
}

export enum PromptType {
  SYSTEM = "system",
  SEED = "seed",
  AGENT = "agent"
}

export interface NavigationItem {
  label: string;
  icon: React.ComponentType<any>;
  path: string;
  onClick: () => void;
}

export interface AgentConfig {
  id: string;
  name: string;
  description: string;
  model: string;
  prompts: string[];
  tools: string[];
  schema_file?: string;
  grammar_file?: string;
  temperature: number;
  max_tokens?: number;
  enable_summarization: boolean;
  enable_scratchpad: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ToolConfig {
  name: string;
  description: string;
  parameters: Record<string, any>;
  is_provider_tool: boolean;
  provider?: string;
  file_path?: string;
}

export interface PromptConfig {
  name: string;
  content: string;
  type: PromptType;
  created_at?: string;
  updated_at?: string;
}

export interface Message {
  id: string;
  agent_id: string;
  content: string;
  message_type: MessageType;
  timestamp: string;
  metadata: Record<string, any>;
  tool_name?: string;
  tool_parameters?: Record<string, any>;
  tool_result?: any;
  target_agent_id?: string;
  agent_result?: string;
  action?: string;
  reasoning?: string;
}

export interface ChatSession {
  id: string;
  agent_id: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
  summary?: string;
}

export interface LLMResponse {
  content: string;
  message_type: MessageType;
  metadata: Record<string, any>;
  action?: string;
  reasoning?: string;
  tool_name?: string;
  tool_parameters?: Record<string, any>;
  target_agent_id?: string;
}

export interface CreateAgentRequest {
  name: string;
  description: string;
  model: string;
  prompts: string[];
  tools: string[];
  schema_file?: string;
  grammar_file?: string;
  temperature: number;
  max_tokens?: number;
  enable_summarization: boolean;
  enable_scratchpad: boolean;
}

export interface CreateToolRequest {
  name: string;
  description: string;
  code: string;
  parameters: Record<string, any>;
}

export interface CreatePromptRequest {
  name: string;
  content: string;
  type: PromptType;
}

export interface ChatMessageRequest {
  content: string;
  session_id?: string;
}

export interface ChatMessageResponse {
  message: Message;
  session_id: string;
  agent_response: LLMResponse;
  context_usage?: number;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  supports_schema: boolean;
  supports_grammar: boolean;
  max_tokens: number;
}

export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  status: number;
}

export interface ChatTab {
  id: string;
  agentId: string;
  agentName: string;
  isActive: boolean;
  sessionId?: string;
}

export interface WebSocketMessage {
  type: 'message' | 'error' | 'status';
  data: any;
  timestamp: string;
}

export interface WebSocketResponse {
  session_id: string;
  agent_response: LLMResponse;
  session: any;
  context_usage?: number;
} 