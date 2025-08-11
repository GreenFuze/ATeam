export enum MessageType {
  CHAT_RESPONSE = "CHAT_RESPONSE",
  TOOL_CALL = "TOOL_CALL",
  TOOL_RETURN = "TOOL_RETURN",
  AGENT_CALL = "AGENT_CALL",
  AGENT_RETURN = "AGENT_RETURN",
  AGENT_DELEGATE = "AGENT_DELEGATE",
  REFINEMENT_RESPONSE = "REFINEMENT_RESPONSE",
  SYSTEM = "SYSTEM",
  ERROR = "ERROR"
}

export enum PromptType {
  SYSTEM = "system",
  SEED = "seed"
}

// Structured response interfaces
export interface StructuredResponse {
  action: string;
  reasoning: string;
}

export interface ChatResponse extends StructuredResponse {
  action: "CHAT_RESPONSE";
  content: string;
}

export interface ToolCallResponse extends StructuredResponse {
  action: "TOOL_CALL";
  tool: string;
  args: Record<string, any>;
}

export interface ToolReturnResponse {
  action: "TOOL_RETURN";
  tool: string;
  result: string;
  success: "True" | "False";
}

export interface AgentDelegateResponse extends StructuredResponse {
  action: "AGENT_DELEGATE";
  agent: string;
  caller_agent: string;
  user_input: string;
}

export interface AgentCallResponse extends StructuredResponse {
  action: "AGENT_CALL";
  agent: string;
  caller_agent: string;
  user_input: string;
}

export interface AgentReturnResponse extends StructuredResponse {
  action: "AGENT_RETURN";
  agent: string;
  returning_agent: string;
  success: "True" | "False";
}

export interface RefinementChecklist {
  objective: boolean;
  inputs: boolean;
  outputs: boolean;
  constraints: boolean;
}

export interface RefinementResponse {
  action: "REFINEMENT_RESPONSE";
  new_plan: string;
  done: "yes" | "no";
  score: number;
  why: string;
  checklist: RefinementChecklist;
  success: boolean;
}

export type StructuredResponseType = 
  | ChatResponse
  | ToolCallResponse
  | ToolReturnResponse
  | AgentDelegateResponse
  | AgentCallResponse
  | AgentReturnResponse
  | RefinementResponse;

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

export interface ToolMethod {
  name: string;
  description?: string;
  has_docstring: boolean;
  signature: string;
}

export interface ToolConfig {
  name: string;
  type: 'function' | 'class';
  description?: string;
  file_path: string;
  relative_path: string;
  has_docstring: boolean;
  signature?: string;
  methods?: ToolMethod[];
}

export interface PromptConfig {
  name: string;
  content: string;
  type: PromptType;
  created_at?: string;
  updated_at?: string;
}

export interface SeedMessage {
  role: string; // "user", "assistant", "system"
  content: string;
}

export interface SeedPromptData {
  messages: SeedMessage[];
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
  id?: string;
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
  tokens_used?: number;
  context_window?: number;
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
  tokens_used?: number;
  context_window?: number;
} 