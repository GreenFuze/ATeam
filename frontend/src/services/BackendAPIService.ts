/**
 * BackendAPIService - Handles WebSocket messages from frontend to backend
 * Manages the WebSocket connection for sending messages to the backend
 */

export interface BackendAPIMessage {
  type: 'chat_message' | 'agent_refresh' | 'session_management' | 'register_agent' | 'get_agents' | 'create_agent' | 'update_agent' | 'delete_agent' | 'get_tools' | 'get_prompts' | 'get_providers' | 'get_models' | 'get_schemas' | 'update_settings';
  message_id: string;
  timestamp: string;
  agent_id?: string;
  session_id?: string;
  data: any; // Structured data per message type
}

export class BackendAPIService {
  private ws: WebSocket | null = null;
  private url: string;
  private connectionId: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private isConnecting = false;
  private messageQueue: BackendAPIMessage[] = [];

  constructor(url: string = 'ws://localhost:8000/ws/backend-api') {
    this.url = url;
    this.connectionId = this.generateConnectionId();
  }

  private generateConnectionId(): string {
    return `backend_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  public async connect(): Promise<void> {
    if (this.isConnecting || this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isConnecting = true;

    try {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('BackendAPI WebSocket connected');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        
        // Send queued messages
        this.flushMessageQueue();
      };

      this.ws.onclose = () => {
        console.log('BackendAPI WebSocket disconnected');
        this.isConnecting = false;
        this.handleDisconnect();
      };

      this.ws.onerror = (error) => {
        console.error('BackendAPI WebSocket error:', error);
        this.isConnecting = false;
      };

    } catch (error) {
      console.error('Error connecting to BackendAPI:', error);
      this.isConnecting = false;
      this.handleDisconnect();
    }
  }

  private handleDisconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`BackendAPI reconnecting... Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
      
      setTimeout(() => {
        this.connect();
      }, this.reconnectDelay);

      // Exponential backoff
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000); // Max 30 seconds
    } else {
      console.error('BackendAPI max reconnection attempts reached');
    }
  }

  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.isConnected()) {
      const message = this.messageQueue.shift();
      if (message) {
        this.sendMessage(message);
      }
    }
  }

  private sendMessage(message: BackendAPIMessage): void {
    if (this.isConnected()) {
      this.ws!.send(JSON.stringify(message));
    } else {
      // Queue message for later
      this.messageQueue.push(message);
    }
  }

  public sendChatMessage(agentId: string, sessionId: string, content: string): void {
    this.sendMessage({
      type: 'chat_message',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      agent_id: agentId,
      session_id: sessionId,
      data: { content }
    });
  }

  public sendAgentRefresh(agentId: string, sessionId: string): void {
    this.sendMessage({
      type: 'agent_refresh',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      agent_id: agentId,
      session_id: sessionId,
      data: {}
    });
  }

  public sendSessionManagement(sessionId: string, action: string): void {
    this.sendMessage({
      type: 'session_management',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      session_id: sessionId,
      data: { action }
    });
  }

  public sendRegisterAgent(agentId: string): void {
    this.sendMessage({
      type: 'register_agent',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      agent_id: agentId,
      data: {}
    });
  }

  public sendGetAgents(): void {
    this.sendMessage({
      type: 'get_agents',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    });
  }

  public sendCreateAgent(agentData: any): void {
    this.sendMessage({
      type: 'create_agent',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: agentData
    });
  }

  public sendUpdateAgent(agentId: string, agentData: any): void {
    this.sendMessage({
      type: 'update_agent',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      agent_id: agentId,
      data: agentData
    });
  }

  public sendDeleteAgent(agentId: string): void {
    this.sendMessage({
      type: 'delete_agent',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      agent_id: agentId,
      data: {}
    });
  }

  public sendGetTools(): void {
    this.sendMessage({
      type: 'get_tools',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    });
  }

  public sendGetPrompts(): void {
    this.sendMessage({
      type: 'get_prompts',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    });
  }

  public sendGetProviders(): void {
    this.sendMessage({
      type: 'get_providers',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    });
  }

  public sendGetModels(): void {
    this.sendMessage({
      type: 'get_models',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    });
  }

  public sendGetSchemas(): void {
    this.sendMessage({
      type: 'get_schemas',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    });
  }

  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
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
export const backendAPIService = new BackendAPIService(); 