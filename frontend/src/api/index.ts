import axios, { AxiosResponse } from 'axios';
import {
  AgentConfig,
  ToolConfig,
  PromptConfig,
  PromptType,
  SeedMessage,
  SeedPromptData,
  ChatMessageRequest,
  ChatMessageResponse,
  CreateAgentRequest,
  CreateToolRequest,
  CreatePromptRequest
} from '../types';
import { ErrorHandler } from '../utils/errorHandler';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    // Don't show error here - let individual API calls handle it with proper titles
    return Promise.reject(error);
  }
);

// Wrapper function for API calls with error handling
const apiCall = async <T>(apiFunction: () => Promise<T>, errorTitle: string = 'API Error'): Promise<T> => {
  try {
    return await apiFunction();
  } catch (error) {
    ErrorHandler.showError(error, errorTitle);
    throw error;
  }
};

// Agents API
export const agentsApi = {
  getAll: async (): Promise<AgentConfig[]> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ agents: AgentConfig[] }> = await api.get('/agents');
      return response.data.agents || [];
    }, 'Failed to Load Agents');
  },

  getById: async (id: string): Promise<AgentConfig> => {
    return apiCall(async () => {
      const response: AxiosResponse<AgentConfig> = await api.get(`/agents/${id}`);
      return response.data;
    }, `Failed to Load Agent: ${id}`);
  },

  create: async (agent: CreateAgentRequest): Promise<{ agent_id: string; message: string }> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ agent_id: string; message: string }> = await api.post('/agents', agent);
      return response.data;
    }, 'Failed to Create Agent');
  },

  update: async (id: string, agent: Partial<AgentConfig>): Promise<{ message: string }> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ message: string }> = await api.put(`/agents/${id}`, agent);
      return response.data;
    }, `Failed to Update Agent: ${id}`);
  },

  delete: async (id: string): Promise<{ message: string }> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ message: string }> = await api.delete(`/agents/${id}`);
      return response.data;
    }, `Failed to Delete Agent: ${id}`);
  },

  validate: async (id: string): Promise<{ valid: boolean; error?: string }> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ valid: boolean; error?: string }> = await api.post(`/validate-agent?id=${id}`);
      return response.data;
    }, `Failed to Validate Agent: ${id}`);
  },

  getHistory: async (agentId: string, sessionId?: string): Promise<{ agent_id: string; session_id?: string; messages: any[] }> => {
    return apiCall(async () => {
      const params = sessionId ? { session_id: sessionId } : {};
      const response: AxiosResponse<{ agent_id: string; session_id?: string; messages: any[] }> = await api.get(`/agents/${agentId}/history`, { params });
      return response.data;
    }, `Failed to Load Agent History: ${agentId}`);
  },
};

// Tools API
export const toolsApi = {
  getAll: async (): Promise<ToolConfig[]> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ tools: ToolConfig[] }> = await api.get('/tools');
      return response.data.tools || [];
    }, 'Failed to Load Tools');
  },

  getDirectoryPath: async (): Promise<string> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ path: string }> = await api.get('/tools/directory/path');
      return response.data.path;
    }, 'Failed to Load Tools Directory Path');
  },

  getByName: async (name: string): Promise<ToolConfig> => {
    return apiCall(async () => {
      const response: AxiosResponse<ToolConfig> = await api.get(`/tools/${name}`);
      return response.data;
    }, `Failed to Load Tool: ${name}`);
  },

  create: async (tool: CreateToolRequest): Promise<{ tool_name: string; message: string }> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ tool_name: string; message: string }> = await api.post('/tools', tool);
      return response.data;
    }, 'Failed to Create Tool');
  },
};

// Prompts API
export const promptsApi = {
  getAll: async (): Promise<PromptConfig[]> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ prompts: PromptConfig[] }> = await api.get('/prompts');
      return response.data.prompts || [];
    }, 'Failed to Load Prompts');
  },

  getByName: async (name: string): Promise<PromptConfig> => {
    return apiCall(async () => {
      const response: AxiosResponse<PromptConfig> = await api.get(`/prompts/${name}`);
      return response.data;
    }, `Failed to Load Prompt: ${name}`);
  },

  create: async (prompt: CreatePromptRequest): Promise<{ prompt_name: string; message: string }> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ prompt_name: string; message: string }> = await api.post('/prompts', prompt);
      return response.data;
    }, 'Failed to Create Prompt');
  },

  update: async (name: string, content: string, newName?: string, type?: PromptType): Promise<{ message: string }> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ message: string }> = await api.put(`/prompts/${name}`, { 
        name: newName || name, 
        content, 
        type 
      });
      return response.data;
    }, `Failed to Update Prompt: ${name}`);
  },

  delete: async (name: string): Promise<{ message: string }> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ message: string }> = await api.delete(`/prompts/${name}`);
      return response.data;
    }, `Failed to Delete Prompt: ${name}`);
  },

  getSeedPrompt: async (name: string): Promise<SeedPromptData> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ messages: SeedMessage[] }> = await api.get(`/prompts/${name}/seed`);
      return { messages: response.data.messages };
    }, `Failed to Load Seed Prompt: ${name}`);
  },

  updateSeedPrompt: async (name: string, seedData: SeedPromptData): Promise<{ message: string }> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ message: string }> = await api.put(`/prompts/${name}/seed`, seedData);
      return response.data;
    }, `Failed to Update Seed Prompt: ${name}`);
  },
};

// Models API
export const modelsApi = {
  getAll: async (): Promise<any[]> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ models: any[] }> = await api.get('/models');
      return response.data.models || [];
    }, 'Failed to Load Models');
  },

  get: async (modelId: string): Promise<any> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ model: any }> = await api.get(`/models/${modelId}`);
      return response.data.model;
    }, `Failed to Load Model: ${modelId}`);
  },

  update: async (modelId: string, modelConfig: any): Promise<any> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ message: string }> = await api.put(`/models/${modelId}`, modelConfig);
      return response.data;
    }, `Failed to Update Model: ${modelId}`);
  },

  delete: async (modelId: string): Promise<any> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ message: string }> = await api.delete(`/models/${modelId}`);
      return response.data;
    }, `Failed to Delete Model: ${modelId}`);
  },

  getSettings: async (modelId: string): Promise<any> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ schema: any }> = await api.get(`/models/${modelId}/settings`);
      return response.data;
    }, `Failed to Load Model Settings: ${modelId}`);
  }
};

// Schemas API
export const schemasApi = {
  getAll: async (): Promise<any[]> => {
    return apiCall(async () => {
      const response: AxiosResponse<{ schemas: any[] }> = await api.get('/schemas');
      return response.data.schemas || [];
    }, 'Failed to Load Schemas');
  },

  get: async (schemaName: string): Promise<any> => {
    return apiCall(async () => {
      const response: AxiosResponse<any> = await api.get(`/schemas/${schemaName}`);
      return response.data;
    }, `Failed to Load Schema: ${schemaName}`);
  },

  create: async (schemaConfig: { name: string; content: any }): Promise<any> => {
    return apiCall(async () => {
      const response: AxiosResponse<any> = await api.post('/schemas', schemaConfig);
      return response.data;
    }, 'Failed to Create Schema');
  },

  update: async (schemaName: string, schemaConfig: { content: any }): Promise<any> => {
    return apiCall(async () => {
      const response: AxiosResponse<any> = await api.put(`/schemas/${schemaName}`, schemaConfig);
      return response.data;
    }, `Failed to Update Schema: ${schemaName}`);
  },

  delete: async (schemaName: string): Promise<any> => {
    return apiCall(async () => {
      const response: AxiosResponse<any> = await api.delete(`/schemas/${schemaName}`);
      return response.data;
    }, `Failed to Delete Schema: ${schemaName}`);
  }
};

// Chat API
export const chatApi = {
  sendMessage: async (agentId: string, message: ChatMessageRequest): Promise<ChatMessageResponse> => {
    return apiCall(async () => {
      const response: AxiosResponse<ChatMessageResponse> = await api.post(`/chat/${agentId}`, message);
      return response.data;
    }, `Failed to Send Message to Agent: ${agentId}`);
  },
};

// WebSocket connection for real-time chat
export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private listeners: Map<string, (data: any) => void> = new Map();

  connect(agentId: string): Promise<void> {
    console.log('🔍 DEBUG: WebSocketService.connect called for agent:', agentId);
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `ws://${window.location.host}/ws/chat/${agentId}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('🔍 DEBUG: WebSocket connection opened');
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          console.log('🔍 DEBUG: WebSocketService received raw message:', event.data);
          try {
            const data = JSON.parse(event.data);
            this.notifyListeners('message', data);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.ws.onerror = (event) => {
          // Extract meaningful error information from WebSocket Event
          const target = event.target as WebSocket;
          const errorMsg = target ? `WebSocket connection failed for agent ${agentId} (${target.url})` : `WebSocket connection failed for agent ${agentId}`;
          console.error('WebSocket error:', { event, target, readyState: target?.readyState });
          const wsError = new Error(errorMsg);
          reject(wsError);
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected');
          if (event.code !== 1000) { // Not a normal closure
            const closeError = new Error(`WebSocket connection closed unexpectedly (code: ${event.code})`);
            reject(closeError);
          }
          this.attemptReconnect(agentId);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  private attemptReconnect(agentId: string) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.connect(agentId).catch(console.error);
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  sendMessage(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  addListener(event: string, callback: (data: any) => void) {
    this.listeners.set(event, callback);
  }

  removeListener(event: string) {
    this.listeners.delete(event);
  }

  private notifyListeners(event: string, data: any) {
    const callback = this.listeners.get(event);
    if (callback) {
      callback(data);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export default api; 