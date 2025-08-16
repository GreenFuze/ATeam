/**
 * FrontendAPIService - Handles WebSocket messages from backend to frontend
 * Manages the WebSocket connection for receiving messages from the backend
 */

import { connectionManager } from './ConnectionManager';

export interface FrontendAPIMessage {
  type: 'system_message' | 'agent_response' | 'agent_stream_start' | 'agent_stream' | 'seed_message' | 'error' | 'context_update' | 'notification' | 'agent_call_announcement' | 'agent_list_update' | 'tool_update' | 'prompt_update' | 'provider_update' | 'model_update' | 'schema_update' | 'session_created' | 'conversation_snapshot' | 'conversation_list' | 'monitoring_health' | 'monitoring_metrics' | 'monitoring_errors';
  message_id: string;
  timestamp: string;
  agent_id?: string;
  agent_name?: string;
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
  onAgentStream?: (agentId: string, sessionId: string, data: { delta: string; message_id?: string }) => void;
  onSeedMessage?: (agentId: string, sessionId: string, data: any) => void;
  onError?: (agentId: string, sessionId: string, error: any) => void;
  onContextUpdate?: (agentId: string, sessionId: string, data: any) => void;
  onNotification?: (type: string, message: string) => void;
  onAgentCallAnnouncement?: (agentId: string, sessionId: string, data: any) => void;
  onAgentListUpdate?: (data: any) => void;
  onAgentListUpdateSidebar?: (data: any) => void;
  onAgentListUpdateAgentsPage?: (data: any) => void;
  onAgentListUpdateAgentChat?: (data: any) => void;
  onToolUpdate?: (data: any) => void;
  onPromptUpdate?: (data: any) => void;
  onProviderUpdate?: (data: any) => void;
  onModelUpdate?: (data: any) => void;
  onSchemaUpdate?: (data: any) => void;
  onSessionCreated?: (agentId: string, sessionId: string, data: any) => void;
  onConversationSnapshot?: (agentId: string, sessionId: string, data: { session_id: string; messages: any[] }) => void;
  onConversationList?: (agentId: string, data: { sessions: Array<{ session_id: string; modified_at: string; file_path: string }> }) => void;
  onMonitoringHealth?: (data: any) => void;
  onMonitoringMetrics?: (data: any) => void;
  onMonitoringErrors?: (data: any) => void;
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
    // Merge handlers so multiple components can subscribe concurrently (Sidebar, AgentChat, etc.)
    this.handlers = { ...this.handlers, ...handlers };
    console.log('🔄 [Frontend] FrontendAPI handlers updated:', Object.keys(this.handlers).filter(key => this.handlers[key as keyof FrontendAPIHandlers]));
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
        console.log('📥 [Frontend] FrontendAPI received message:', event.data);
        try {
          const message: FrontendAPIMessage = JSON.parse(event.data);
          console.log('📥 [Frontend] Parsed FrontendAPI message:', message);
          this.handleMessage(message);
        } catch (error) {
          console.error('❌ [Frontend] Error parsing FrontendAPI message:', error);
          // Trigger global error handler
          if (this.handlers.onError) {
            this.handlers.onError('', '', { code: 'parse_error', message: `Failed to parse FrontendAPI message: ${error}` });
          }
        }
      };

      this.ws.onclose = () => {
        console.log('FrontendAPI WebSocket disconnected');
        this.isConnecting = false;
        this.handleDisconnect();
      };

      this.ws.onerror = (event) => {
        // Extract meaningful error information from WebSocket Event
        const errorDetails = this.extractWebSocketErrorDetails(event);
        console.error('FrontendAPI WebSocket error:', errorDetails);
        this.isConnecting = false;
        
        // Trigger global error handler with proper error message
        if (this.handlers.onError) {
          this.handlers.onError('', '', { 
            code: 'websocket_error', 
            message: `FrontendAPI WebSocket error: ${errorDetails.message}`,
            details: errorDetails
          });
        }
      };

    } catch (error) {
      console.error('Error connecting to FrontendAPI:', error);
      this.isConnecting = false;
      this.handleDisconnect();
      // Trigger global error handler
      if (this.handlers.onError) {
        this.handlers.onError('', '', { code: 'connection_error', message: `Failed to connect to FrontendAPI: ${error}` });
      }
    }
  }

  private handleMessage(message: FrontendAPIMessage): void {
    console.log('🔄 [Frontend] handleMessage() called with type:', message.type);
    const sessionId = message.session_id || '';
    
    switch (message.type) {
      case 'system_message':
        console.log('📥 [Frontend] Processing system_message for agent:', message.agent_id);
        if (this.handlers.onSystemMessage && message.agent_id) {
          this.handlers.onSystemMessage(message.agent_id, sessionId, message.data);
        }
        break;

      case 'agent_response':
        console.log('📥 [Frontend] Processing agent_response for agent:', message.agent_id);
        if (this.handlers.onAgentResponse && message.agent_id) {
          // Include message_id for deduplication on the UI side
          const payload = { ...message.data, message_id: message.message_id };
          this.handlers.onAgentResponse(message.agent_id, sessionId, payload);
        }
        break;

      case 'agent_stream':
        console.log('📥 [Frontend] Processing agent_stream for agent:', message.agent_id);
        if (this.handlers.onAgentStream && message.agent_id) {
          this.handlers.onAgentStream(message.agent_id, sessionId, message.data);
        }
        break;

      case 'agent_stream_start':
        console.log('📥 [Frontend] Processing agent_stream_start for agent:', message.agent_id);
        if (this.handlers.onAgentStream && message.agent_id) {
          // Pass a minimal delta and reuse message_id. The action is signaled by an empty delta; the component will read action from this branch.
          // We can't extend the type here; instead we forward via a side channel in ConnectionManager if needed. For now, emit an empty delta to trigger stream start.
          this.handlers.onAgentStream(message.agent_id, sessionId, { delta: '', message_id: message.data?.message_id });
          // Also notify ConnectionManager (optional):
          try {
            // @ts-ignore: allow side channel for action hint
            (message.data && (connectionManager as any)._onStreamStartAction) && (connectionManager as any)._onStreamStartAction(message.agent_id, message.data?.message_id, message.data?.action);
          } catch {}
        }
        break;

      case 'seed_message':
        console.log('📥 [Frontend] Processing seed_message for agent:', message.agent_id);
        if (this.handlers.onSeedMessage && message.agent_id) {
          this.handlers.onSeedMessage(message.agent_id, sessionId, message.data);
        }
        break;

      case 'error':
        console.log('❌ [Frontend] Processing error for agent:', message.agent_id);
        if (this.handlers.onError && message.agent_id) {
          this.handlers.onError(message.agent_id, sessionId, message.error || { code: 'unknown', message: 'Unknown error' });
        }
        break;

      case 'session_created':
        console.log('📥 [Frontend] Processing session_created for agent:', message.agent_id);
        if (this.handlers.onSessionCreated && message.agent_id) {
          this.handlers.onSessionCreated(message.agent_id, message.data.session_id || '', message.data);
        }
        break;

      case 'conversation_snapshot':
        console.log('📥 [Frontend] Processing conversation_snapshot for agent:', message.agent_id);
        if (this.handlers.onConversationSnapshot && message.agent_id) {
          this.handlers.onConversationSnapshot(message.agent_id, message.data.session_id, message.data);
        }
        break;

      case 'conversation_list':
        console.log('📥 [Frontend] Processing conversation_list for agent:', message.agent_id);
        if (this.handlers.onConversationList && message.agent_id) {
          this.handlers.onConversationList(message.agent_id, message.data);
        }
        break;

      case 'context_update':
        console.log('📥 [Frontend] Processing context_update for agent:', message.agent_id);
        if (this.handlers.onContextUpdate && message.agent_id) {
          this.handlers.onContextUpdate(message.agent_id, sessionId, message.data);
        }
        break;

      case 'agent_call_announcement':
        console.log('📥 [Frontend] Processing agent_call_announcement for agent:', message.agent_id);
        if (this.handlers.onAgentCallAnnouncement && message.agent_id) {
          this.handlers.onAgentCallAnnouncement(message.agent_id, sessionId, message.data);
        }
        break;

      case 'notification':
        console.log('📥 [Frontend] Processing notification:', message.data);
        if (this.handlers.onNotification && message.data) {
          this.handlers.onNotification(message.data.type || 'info', message.data.message || '');
        }
        break;

      case 'agent_list_update':
        console.log('📥 [Frontend] Processing agent_list_update:', message.data);
        // Store agents in ConnectionManager for global access
        if (message.data && message.data.agents) {
          console.log('📥 [Frontend] Updating agents in ConnectionManager:', message.data.agents);
          connectionManager.updateAgents(message.data.agents);
        }
        
        // Call all agent list update handlers
        if (this.handlers.onAgentListUpdate) {
          console.log('📥 [Frontend] Calling onAgentListUpdate handler');
          this.handlers.onAgentListUpdate(message.data);
        }
        if (this.handlers.onAgentListUpdateSidebar) {
          console.log('📥 [Frontend] Calling onAgentListUpdateSidebar handler');
          this.handlers.onAgentListUpdateSidebar(message.data);
        }
        if (this.handlers.onAgentListUpdateAgentsPage) {
          console.log('📥 [Frontend] Calling onAgentListUpdateAgentsPage handler');
          this.handlers.onAgentListUpdateAgentsPage(message.data);
        }
        if (this.handlers.onAgentListUpdateAgentChat) {
          console.log('📥 [Frontend] Calling onAgentListUpdateAgentChat handler');
          this.handlers.onAgentListUpdateAgentChat(message.data);
        }
        
        if (!this.handlers.onAgentListUpdate && !this.handlers.onAgentListUpdateSidebar && 
            !this.handlers.onAgentListUpdateAgentsPage && !this.handlers.onAgentListUpdateAgentChat) {
          console.warn('⚠️ [Frontend] No agent list update handlers registered');
        }
        break;

      case 'tool_update':
        console.log('📥 [Frontend] Processing tool_update:', message.data);
        if (!message.data || !Array.isArray(message.data.tools)) {
          throw new Error('Backend sent malformed tool_update data - missing tools array');
        }
        console.log('📥 [Frontend] Updating tools in ConnectionManager:', message.data.tools);
        connectionManager.updateTools(message.data.tools);
        if (this.handlers.onToolUpdate) {
          this.handlers.onToolUpdate(message.data);
        }
        break;

      case 'prompt_update':
        console.log('📥 [Frontend] Processing prompt_update:', message.data);
        if (!message.data || !Array.isArray(message.data.prompts)) {
          throw new Error('Backend sent malformed prompt_update data - missing prompts array');
        }
        console.log('📥 [Frontend] Updating prompts in ConnectionManager:', message.data.prompts);
        connectionManager.updatePrompts(message.data.prompts);
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
        console.log('📥 [Frontend] Processing model_update:', message.data);
        if (!message.data || !Array.isArray(message.data.models)) {
          throw new Error('Backend sent malformed model_update data - missing models array');
        }
        console.log('📥 [Frontend] Updating models in ConnectionManager:', message.data.models);
        connectionManager.updateModels(message.data.models);
        if (this.handlers.onModelUpdate) {
          this.handlers.onModelUpdate(message.data);
        }
        break;

      case 'schema_update':
        if (this.handlers.onSchemaUpdate) {
          this.handlers.onSchemaUpdate(message.data);
        }
        break;



      case 'monitoring_health':
        if (this.handlers.onMonitoringHealth) {
          this.handlers.onMonitoringHealth(message.data);
        }
        break;

      case 'monitoring_metrics':
        if (this.handlers.onMonitoringMetrics) {
          this.handlers.onMonitoringMetrics(message.data);
        }
        break;

      case 'monitoring_errors':
        if (this.handlers.onMonitoringErrors) {
          this.handlers.onMonitoringErrors(message.data);
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
export const frontendAPIService = new FrontendAPIService(); 