/**
 * BackendAPIService - Handles WebSocket messages from frontend to backend
 * Manages the WebSocket connection for sending messages to the backend
 */

export interface BackendAPIMessage {
  type: 'chat_message' | 'agent_refresh' | 'session_management' | 'register_agent' | 'get_agents' | 'create_agent' | 'update_agent' | 'delete_agent' | 'get_tools' | 'get_prompts' | 'get_providers' | 'get_models' | 'get_schemas' | 'update_settings' | 'update_provider' | 'update_model' | 'create_schema' | 'update_schema' | 'delete_schema' | 'update_prompt' | 'create_prompt' | 'delete_prompt' | 'get_monitoring_health' | 'get_monitoring_metrics' | 'get_monitoring_errors' | 'save_conversation' | 'list_conversations' | 'load_conversation' | 'get_embedding_models' | 'get_embedding_settings' | 'update_embedding_settings';
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
        console.log('✅ [Frontend] BackendAPI WebSocket connected');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        
        // Send queued messages
        console.log('🔄 [Frontend] Flushing message queue...');
        this.flushMessageQueue();
      };

      this.ws.onclose = () => {
        console.log('BackendAPI WebSocket disconnected');
        this.isConnecting = false;
        this.handleDisconnect();
      };

      this.ws.onerror = (event) => {
        // Extract meaningful error information from WebSocket Event
        const errorDetails = this.extractWebSocketErrorDetails(event);
        console.error('BackendAPI WebSocket error:', errorDetails);
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
    console.log('🔄 [Frontend] flushMessageQueue() called. Queue length:', this.messageQueue.length);
    while (this.messageQueue.length > 0 && this.isConnected()) {
      const message = this.messageQueue.shift();
      if (message) {
        console.log('📤 [Frontend] Sending queued message:', message.type);
        this.sendMessage(message);
      }
    }
    console.log('✅ [Frontend] Message queue flushed');
  }

  private sendMessage(message: BackendAPIMessage): void {
    console.log('📤 [Frontend] sendMessage() called with message type:', message.type);
    if (this.isConnected()) {
      console.log('✅ [Frontend] WebSocket connected, sending message immediately');
      const messageStr = JSON.stringify(message);
      console.log('📤 [Frontend] Sending JSON:', messageStr);
      this.ws!.send(messageStr);
    } else {
      console.log('⏳ [Frontend] WebSocket not connected, queuing message');
      // Queue message for later
      this.messageQueue.push(message);
      console.log('📋 [Frontend] Message queued. Queue length:', this.messageQueue.length);
    }
  }

  public sendChatMessage(agentId: string, sessionId: string, content: string): void {
    const message: BackendAPIMessage = {
      type: 'chat_message',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      agent_id: agentId,
      session_id: sessionId,
      data: { content }
    };
    this.sendMessage(message);
  }

  public sendAgentRefresh(agentId: string, sessionId: string): void {
    const message: BackendAPIMessage = {
      type: 'agent_refresh',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      agent_id: agentId,
      session_id: sessionId,
      data: {}
    };
    this.sendMessage(message);
  }

  public sendSessionManagement(sessionId: string, action: string): void {
    const message: BackendAPIMessage = {
      type: 'session_management',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      session_id: sessionId,
      data: { action }
    };
    this.sendMessage(message);
  }

  public sendRegisterAgent(agentId: string): void {
    const message: BackendAPIMessage = {
      type: 'register_agent',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      agent_id: agentId,
      data: {}
    };
    this.sendMessage(message);
  }

  public sendGetAgents(): void {
    console.log('🔄 [Frontend] sendGetAgents() called');
    const message: BackendAPIMessage = {
      type: 'get_agents',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    };
    console.log('📤 [Frontend] Sending get_agents message:', message);
    this.sendMessage(message);
  }

  public sendCreateAgent(agentData: any): void {
    const message: BackendAPIMessage = {
      type: 'create_agent',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: agentData
    };
    this.sendMessage(message);
  }

  public sendUpdateAgent(agentId: string, agentData: any): void {
    const message: BackendAPIMessage = {
      type: 'update_agent',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      agent_id: agentId,
      data: agentData
    };
    this.sendMessage(message);
  }

  public sendDeleteAgent(agentId: string): void {
    const message: BackendAPIMessage = {
      type: 'delete_agent',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      agent_id: agentId,
      data: {}
    };
    this.sendMessage(message);
  }

  public sendGetTools(): void {
    const message: BackendAPIMessage = {
      type: 'get_tools',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    };
    this.sendMessage(message);
  }

  public sendGetPrompts(): void {
    const message: BackendAPIMessage = {
      type: 'get_prompts',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    };
    this.sendMessage(message);
  }

  public sendGetProviders(): void {
    const message: BackendAPIMessage = {
      type: 'get_providers',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    };
    this.sendMessage(message);
  }

  public sendGetModels(): void {
    const message: BackendAPIMessage = {
      type: 'get_models',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    };
    this.sendMessage(message);
  }

  public sendGetSchemas(): void {
    const message: BackendAPIMessage = {
      type: 'get_schemas',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    };
    this.sendMessage(message);
  }

  public sendSaveConversation(agentId: string, sessionId: string): void {
    const message: BackendAPIMessage = {
      type: 'save_conversation',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      agent_id: agentId,
      session_id: sessionId,
      data: {}
    };
    this.sendMessage(message);
  }

  public sendListConversations(agentId: string): void {
    const message: BackendAPIMessage = {
      type: 'list_conversations',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      agent_id: agentId,
      data: {}
    };
    this.sendMessage(message);
  }

  public sendLoadConversation(agentId: string, sessionId: string): void {
    const message: BackendAPIMessage = {
      type: 'load_conversation',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      agent_id: agentId,
      data: { session_id: sessionId }
    };
    this.sendMessage(message);
  }

  public sendSummarizeRequest(agentId: string, sessionId: string, percentage: number): void {
    const message: BackendAPIMessage = {
      type: 'summarize_request',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      agent_id: agentId,
      session_id: sessionId,
      data: { percentage }
    } as any;
    this.sendMessage(message);
  }

  public sendGetEmbeddingModels(): void {
    const message: BackendAPIMessage = {
      type: 'get_embedding_models',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    };
    this.sendMessage(message);
  }

  public sendGetEmbeddingSettings(): void {
    const message: BackendAPIMessage = {
      type: 'get_embedding_settings',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    };
    this.sendMessage(message);
  }

  public sendUpdateEmbeddingSettings(selected_model: string, max_chunk_size: number): void {
    const message: BackendAPIMessage = {
      type: 'update_embedding_settings',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: { selected_model, max_chunk_size }
    };
    this.sendMessage(message);
  }

  public sendUpdateProvider(providerName: string, providerData: any): void {
    const message: BackendAPIMessage = {
      type: 'update_provider',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: { name: providerName, ...providerData }
    };
    this.sendMessage(message);
  }

  public sendUpdateModel(modelId: string, modelData: any): void {
    const message: BackendAPIMessage = {
      type: 'update_model',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: { id: modelId, ...modelData }
    };
    this.sendMessage(message);
  }

  public sendCreateSchema(schemaData: any): void {
    const message: BackendAPIMessage = {
      type: 'create_schema',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: schemaData
    };
    this.sendMessage(message);
  }

  public sendUpdateSchema(schemaName: string, schemaData: any): void {
    const message: BackendAPIMessage = {
      type: 'update_schema',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: { name: schemaName, ...schemaData }
    };
    this.sendMessage(message);
  }

  public sendDeleteSchema(schemaName: string): void {
    const message: BackendAPIMessage = {
      type: 'delete_schema',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: { name: schemaName }
    };
    this.sendMessage(message);
  }

  public sendUpdatePrompt(promptName: string, promptData: any): void {
    const message: BackendAPIMessage = {
      type: 'update_prompt',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: { name: promptName, ...promptData }
    };
    this.sendMessage(message);
  }

  public sendCreatePrompt(promptData: any): void {
    const message: BackendAPIMessage = {
      type: 'create_prompt',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: promptData
    };
    this.sendMessage(message);
  }

  public sendDeletePrompt(promptName: string): void {
    const message: BackendAPIMessage = {
      type: 'delete_prompt',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: { name: promptName }
    };
    this.sendMessage(message);
  }

  public sendGetMonitoringHealth(): void {
    const message: BackendAPIMessage = {
      type: 'get_monitoring_health',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    };
    this.sendMessage(message);
  }

  public sendGetMonitoringMetrics(): void {
    const message: BackendAPIMessage = {
      type: 'get_monitoring_metrics',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    };
    this.sendMessage(message);
  }

  public sendGetMonitoringErrors(): void {
    const message: BackendAPIMessage = {
      type: 'get_monitoring_errors',
      message_id: this.generateMessageId(),
      timestamp: new Date().toISOString(),
      data: {}
    };
    this.sendMessage(message);
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

  private extractWebSocketErrorDetails(event: Event): { message: string; type: string; details: any } {
    // Extract meaningful information from WebSocket error event
    const details: any = {
      type: event.type,
      timeStamp: event.timeStamp,
      target: {
        readyState: (event.target as WebSocket)?.readyState,
        url: (event.target as WebSocket)?.url,
        protocol: (event.target as WebSocket)?.protocol
      }
    };

    // Determine error message based on WebSocket state
    let message = 'Unknown WebSocket error';
    const target = event.target as WebSocket;
    
    if (target) {
      switch (target.readyState) {
        case WebSocket.CONNECTING:
          message = 'Connection failed - Unable to establish WebSocket connection';
          break;
        case WebSocket.OPEN:
          message = 'Connection error during active session';
          break;
        case WebSocket.CLOSING:
          message = 'Connection error while closing';
          break;
        case WebSocket.CLOSED:
          message = 'Connection lost - WebSocket closed unexpectedly';
          break;
        default:
          message = 'WebSocket in unknown state';
      }

      // Add more specific details
      if (target.url) {
        details.url = target.url;
        message += ` (${target.url})`;
      }
    }

    return {
      message,
      type: event.type,
      details
    };
  }
}

// Global instance
export const backendAPIService = new BackendAPIService(); 