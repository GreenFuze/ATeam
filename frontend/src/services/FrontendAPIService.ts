/**
 * FrontendAPIService - Handles WebSocket messages from backend to frontend
 * Manages the WebSocket connection for receiving messages from the backend
 */

import { connectionManager } from './ConnectionManager';

export interface FrontendAPIMessage {
  type: 'system_message' | 'agent_response' | 'seed_message' | 'error' | 'context_update' | 'notification' | 'agent_list_update' | 'tool_update' | 'prompt_update' | 'provider_update' | 'model_update' | 'schema_update' | 'session_created';
  message_id: string;
  timestamp: string;
  agent_id?: string;
  session_id?: string;
  data: any; // Structured data per message type
  error?: {
    code: string;
    message: string;
    details?: any;
  };
}

export interface FrontendAPIHandlers {
  onSystemMessage?: (agentId: string, sessionId: string, data: any) => void;
  onAgentResponse?: (agentId: string, sessionId: string, data: any) => void;
  onSeedMessage?: (agentId: string, sessionId: string, data: any) => void;
  onError?: (agentId: string, sessionId: string, error: any) => void;
  onContextUpdate?: (agentId: string, sessionId: string, data: any) => void;
  onNotification?: (type: string, message: string) => void;
  onAgentListUpdate?: (data: any) => void;
  onToolUpdate?: (data: any) => void;
  onPromptUpdate?: (data: any) => void;
  onProviderUpdate?: (data: any) => void;
  onModelUpdate?: (data: any) => void;
  onSchemaUpdate?: (data: any) => void;
  onSessionCreated?: (agentId: string, sessionId: string, data: any) => void;
}

export class FrontendAPIService {
  private ws: WebSocket | null = null;
  private url: string;
  private connectionId: string;
  private handlers: FrontendAPIHandlers = {};
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private isConnecting = false;

  constructor(url: string = 'ws://localhost:8000/ws/frontend-api') {
    this.url = url;
    this.connectionId = this.generateConnectionId();
  }

  private generateConnectionId(): string {
    return `frontend_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  public setHandlers(handlers: FrontendAPIHandlers): void {
    this.handlers = handlers;
  }

  public async connect(): Promise<void> {
    if (this.isConnecting || this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isConnecting = true;

    try {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('FrontendAPI WebSocket connected');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
      };

      this.ws.onmessage = (event) => {
        try {
          const message: FrontendAPIMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Error parsing FrontendAPI message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('FrontendAPI WebSocket disconnected');
        this.isConnecting = false;
        this.handleDisconnect();
      };

      this.ws.onerror = (error) => {
        console.error('FrontendAPI WebSocket error:', error);
        this.isConnecting = false;
      };

    } catch (error) {
      console.error('Error connecting to FrontendAPI:', error);
      this.isConnecting = false;
      this.handleDisconnect();
    }
  }

  private handleMessage(message: FrontendAPIMessage): void {
    const sessionId = message.session_id || '';
    
    switch (message.type) {
      case 'system_message':
        if (this.handlers.onSystemMessage && message.agent_id) {
          this.handlers.onSystemMessage(message.agent_id, sessionId, message.data);
        }
        break;

      case 'agent_response':
        if (this.handlers.onAgentResponse && message.agent_id) {
          this.handlers.onAgentResponse(message.agent_id, sessionId, message.data);
        }
        break;

      case 'seed_message':
        if (this.handlers.onSeedMessage && message.agent_id) {
          this.handlers.onSeedMessage(message.agent_id, sessionId, message.data);
        }
        break;

      case 'error':
        if (this.handlers.onError && message.agent_id) {
          this.handlers.onError(message.agent_id, sessionId, message.error || { code: 'unknown', message: 'Unknown error' });
        }
        break;

      case 'context_update':
        if (this.handlers.onContextUpdate && message.agent_id) {
          this.handlers.onContextUpdate(message.agent_id, sessionId, message.data);
        }
        break;

      case 'notification':
        if (this.handlers.onNotification && message.data) {
          this.handlers.onNotification(message.data.type || 'info', message.data.message || '');
        }
        break;

      case 'agent_list_update':
        // Store agents in ConnectionManager for global access
        if (message.data && message.data.agents) {
          connectionManager.updateAgents(message.data.agents);
        }
        if (this.handlers.onAgentListUpdate) {
          this.handlers.onAgentListUpdate(message.data);
        }
        break;

      case 'tool_update':
        if (this.handlers.onToolUpdate) {
          this.handlers.onToolUpdate(message.data);
        }
        break;

      case 'prompt_update':
        if (this.handlers.onPromptUpdate) {
          this.handlers.onPromptUpdate(message.data);
        }
        break;

      case 'provider_update':
        if (this.handlers.onProviderUpdate) {
          this.handlers.onProviderUpdate(message.data);
        }
        break;

      case 'model_update':
        if (this.handlers.onModelUpdate) {
          this.handlers.onModelUpdate(message.data);
        }
        break;

      case 'schema_update':
        if (this.handlers.onSchemaUpdate) {
          this.handlers.onSchemaUpdate(message.data);
        }
        break;

      case 'session_created':
        if (this.handlers.onSessionCreated && message.agent_id) {
          this.handlers.onSessionCreated(message.agent_id, message.session_id || '', message.data);
        }
        break;

      default:
        console.warn('Unknown FrontendAPI message type:', message.type);
    }
  }

  private handleDisconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`FrontendAPI reconnecting... Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
      
      setTimeout(() => {
        this.connect();
      }, this.reconnectDelay);

      // Exponential backoff
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000); // Max 30 seconds
    } else {
      console.error('FrontendAPI max reconnection attempts reached');
    }
  }

  public disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnecting = false;
  }

  public isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  public getConnectionId(): string {
    return this.connectionId;
  }
}

// Global instance
export const frontendAPIService = new FrontendAPIService(); 