/**
 * ConnectionManager - Manages both FrontendAPI and BackendAPI WebSocket connections
 * Provides unified interface for dual WebSocket architecture
 */

import { frontendAPIService, FrontendAPIHandlers } from './FrontendAPIService';
import { backendAPIService } from './BackendAPIService';
import { Message } from '../types';

export interface ConnectionStatus {
  frontendAPI: boolean;
  backendAPI: boolean;
  isConnecting: boolean;
  reconnectAttempts: {
    frontendAPI: number;
    backendAPI: number;
  };
}

export interface ConnectionCallbacks {
  onStatusChange?: (status: ConnectionStatus) => void;
  onConnectionLost?: () => void;
  onConnectionRestored?: () => void;
  onError?: (error: string) => void;
}

export class ConnectionManager {
  private callbacks: ConnectionCallbacks = {};
  private status: ConnectionStatus = {
    frontendAPI: false,
    backendAPI: false,
    isConnecting: false,
    reconnectAttempts: {
      frontendAPI: 0,
      backendAPI: 0
    }
  };
  private agents: any[] = [];
  private models: any[] = [];
  private prompts: any[] = [];
  private tools: any[] = [];
  // Persist session per agent across route navigations (in-memory for SPA lifetime)
  private sessionsByAgent: Record<string, string> = {};
  // Cache messages per agent to restore UI on remount
  private messageCacheByAgent: Record<string, Message[]> = {};
  // Cache latest context usage per agent
  private contextByAgent: Record<string, { percentage: number | null; tokensUsed: number | null; contextWindow: number | null }> = {};
  // Optional side channel to hint action type before streaming content materializes
  public _onStreamStartAction?(agentId: string, streamId: string, action?: string): void;

  constructor() {
    this.setupEventListeners();
  }

  private setupEventListeners(): void {
    // Set up periodic status checking
    setInterval(() => {
      this.updateStatus();
    }, 1000); // Check every second
  }

  public async connect(): Promise<void> {
    try {
      this.status.isConnecting = true;
      this.updateStatus();
      
      // Connect to both WebSocket services
      await Promise.all([
        frontendAPIService.connect(),
        backendAPIService.connect()
      ]);
      
      // Give connections time to establish
      setTimeout(() => {
        this.status.isConnecting = false;
        this.updateStatus();
      }, 2000);
      
    } catch (error) {
      console.error('Error connecting to WebSocket services:', error);
      this.status.isConnecting = false;
      this.updateStatus();
      if (this.callbacks.onError) {
        this.callbacks.onError(`Failed to connect to WebSocket services: ${error}`);
      }
    }
  }

  public disconnect(): void {
    frontendAPIService.disconnect();
    backendAPIService.disconnect();
    this.status = {
      frontendAPI: false,
      backendAPI: false,
      isConnecting: false,
      reconnectAttempts: {
        frontendAPI: 0,
        backendAPI: 0
      }
    };
    this.updateStatus();
  }

  public setFrontendAPIHandlers(handlers: FrontendAPIHandlers): void {
    frontendAPIService.setHandlers(handlers);
  }

  public setCallbacks(callbacks: ConnectionCallbacks): void {
    this.callbacks = callbacks;
  }

  public getStatus(): ConnectionStatus {
    return { ...this.status };
  }

  public isConnected(): boolean {
    return this.status.frontendAPI && this.status.backendAPI;
  }

  public isConnecting(): boolean {
    return this.status.isConnecting;
  }

  private updateStatus(): void {
    const wasConnected = this.isConnected();
    
    // Store previous status for comparison
    const previousStatus = { ...this.status };
    
    this.status.frontendAPI = frontendAPIService.isConnected();
    this.status.backendAPI = backendAPIService.isConnected();
    this.status.isConnecting = this.status.isConnecting && (!this.status.frontendAPI || !this.status.backendAPI);

    const isConnected = this.isConnected();

    // Only notify status change if something actually changed
    const statusChanged = 
      previousStatus.frontendAPI !== this.status.frontendAPI ||
      previousStatus.backendAPI !== this.status.backendAPI ||
      previousStatus.isConnecting !== this.status.isConnecting;

    if (statusChanged && this.callbacks.onStatusChange) {
      this.callbacks.onStatusChange(this.getStatus());
    }

    // Notify connection events
    if (!wasConnected && isConnected && this.callbacks.onConnectionRestored) {
      this.callbacks.onConnectionRestored();
    } else if (wasConnected && !isConnected && this.callbacks.onConnectionLost) {
      this.callbacks.onConnectionLost();
    }
  }

  // Convenience methods for BackendAPI
  public sendChatMessage(agentId: string, sessionId: string, content: string): void {
    backendAPIService.sendChatMessage(agentId, sessionId, content);
  }

  public sendAgentRefresh(agentId: string, sessionId: string): void {
    backendAPIService.sendAgentRefresh(agentId, sessionId);
  }

  public sendSessionManagement(sessionId: string, action: string): void {
    backendAPIService.sendSessionManagement(sessionId, action);
  }

  public sendSubscribe(agentId: string, sessionId: string): void {
    backendAPIService.sendSubscribe(agentId, sessionId);
  }

  public sendUnsubscribe(agentId: string, sessionId: string): void {
    backendAPIService.sendUnsubscribe(agentId, sessionId);
  }

  public sendSaveConversation(agentId: string, sessionId: string): void {
    backendAPIService.sendSaveConversation(agentId, sessionId);
  }

  public sendListConversations(agentId: string): void {
    const sid = this.getSessionId(agentId) || '';
    backendAPIService.sendListConversations(agentId, sid);
  }

  public sendLoadConversation(agentId: string, sessionId: string): void {
    backendAPIService.sendLoadConversation(agentId, sessionId);
  }

  public sendSummarizeRequest(agentId: string, sessionId: string, percentage: number): void {
    // @ts-ignore
    backendAPIService.sendSummarizeRequest(agentId, sessionId, percentage);
  }

  // New methods for replacing REST API calls
  public sendGetAgents(): void {
    backendAPIService.sendGetAgents();
  }

  public getAgents(): any[] {
    console.log('🔄 [Frontend] ConnectionManager.getAgents() called. Current agents:', this.agents);
    return [...this.agents];
  }

  public updateAgents(agents: any[]): void {
    console.log('🔄 [Frontend] ConnectionManager.updateAgents() called with:', agents);
    this.agents = agents;
    console.log('✅ [Frontend] Agents updated in ConnectionManager. Current agents:', this.agents);
  }

  public updateModels(models: any[]): void {
    console.log('🔄 [Frontend] ConnectionManager.updateModels() called with:', models);
    this.models = models;
    console.log('✅ [Frontend] Models updated in ConnectionManager. Current models:', this.models.length);
  }

  public updatePrompts(prompts: any[]): void {
    console.log('🔄 [Frontend] ConnectionManager.updatePrompts() called with:', prompts);
    this.prompts = prompts;
    console.log('✅ [Frontend] Prompts updated in ConnectionManager. Current prompts:', this.prompts.length);
  }

  public updateTools(tools: any[]): void {
    console.log('🔄 [Frontend] ConnectionManager.updateTools() called with:', tools);
    this.tools = tools;
    console.log('✅ [Frontend] Tools updated in ConnectionManager. Current tools:', this.tools.length);
  }

  public getModels(): any[] {
    return this.models;
  }

  public getPrompts(): any[] {
    return this.prompts;
  }

  public getTools(): any[] {
    return this.tools;
  }

  // Session persistence helpers
  public setSessionId(agentId: string, sessionId: string): void {
    this.sessionsByAgent[agentId] = sessionId;
  }

  public getSessionId(agentId: string): string | null {
    return this.sessionsByAgent[agentId] || null;
  }

  public clearSession(agentId: string): void {
    delete this.sessionsByAgent[agentId];
    delete this.messageCacheByAgent[agentId];
    delete this.contextByAgent[agentId];
  }

  // Message cache helpers (per agent)
  public appendMessage(agentId: string, message: Message): void {
    if (!this.messageCacheByAgent[agentId]) {
      this.messageCacheByAgent[agentId] = [];
    }
    this.messageCacheByAgent[agentId].push(message);
  }

  public getMessages(agentId: string): Message[] {
    return this.messageCacheByAgent[agentId] ? [...this.messageCacheByAgent[agentId]] : [];
  }

  public clearMessages(agentId: string): void {
    this.messageCacheByAgent[agentId] = [];
  }

  // Context cache helpers
  public setContext(
    agentId: string,
    percentage: number | null,
    tokensUsed: number | null,
    contextWindow: number | null
  ): void {
    this.contextByAgent[agentId] = { percentage, tokensUsed, contextWindow };
  }

  public getContext(agentId: string): { percentage: number | null; tokensUsed: number | null; contextWindow: number | null } | null {
    return this.contextByAgent[agentId] || null;
  }

  public clearContext(agentId: string): void {
    delete this.contextByAgent[agentId];
  }

  public sendCreateAgent(agentData: any): void {
    backendAPIService.sendCreateAgent(agentData);
  }

  public sendUpdateAgent(agentId: string, agentData: any): void {
    backendAPIService.sendUpdateAgent(agentId, agentData);
  }

  public sendDeleteAgent(agentId: string): void {
    backendAPIService.sendDeleteAgent(agentId);
  }

  public sendGetTools(): void {
    backendAPIService.sendGetTools();
  }

  public sendGetPrompts(): void {
    backendAPIService.sendGetPrompts();
  }

  public sendGetProviders(): void {
    backendAPIService.sendGetProviders();
  }

  public sendGetModels(): void {
    backendAPIService.sendGetModels();
  }

  public sendGetSchemas(): void {
    backendAPIService.sendGetSchemas();
  }

  // Embedding settings WS helpers
  public sendGetEmbeddingModels(): void {
    backendAPIService.sendGetEmbeddingModels();
  }

  public sendGetEmbeddingSettings(): void {
    backendAPIService.sendGetEmbeddingSettings();
  }

  public sendUpdateEmbeddingSettings(selected_model: string, max_chunk_size: number): void {
    backendAPIService.sendUpdateEmbeddingSettings(selected_model, max_chunk_size);
  }

  public sendUpdateProvider(providerName: string, providerData: any): void {
    backendAPIService.sendUpdateProvider(providerName, providerData);
  }

  public sendUpdateModel(modelId: string, modelData: any): void {
    backendAPIService.sendUpdateModel(modelId, modelData);
  }

  public sendCreateSchema(schemaData: any): void {
    backendAPIService.sendCreateSchema(schemaData);
  }

  public sendUpdateSchema(schemaName: string, schemaData: any): void {
    backendAPIService.sendUpdateSchema(schemaName, schemaData);
  }

  public sendDeleteSchema(schemaName: string): void {
    backendAPIService.sendDeleteSchema(schemaName);
  }

  public sendUpdatePrompt(promptName: string, promptData: any): void {
    backendAPIService.sendUpdatePrompt(promptName, promptData);
  }

  public sendCreatePrompt(promptData: any): void {
    backendAPIService.sendCreatePrompt(promptData);
  }

  public sendDeletePrompt(promptName: string): void {
    backendAPIService.sendDeletePrompt(promptName);
  }

  public sendGetMonitoringHealth(): void {
    backendAPIService.sendGetMonitoringHealth();
  }

  public sendGetMonitoringMetrics(): void {
    backendAPIService.sendGetMonitoringMetrics();
  }

  public sendGetMonitoringErrors(): void {
    backendAPIService.sendGetMonitoringErrors();
  }

  public getFrontendAPIConnectionId(): string {
    return frontendAPIService.getConnectionId();
  }

  public getBackendAPIConnectionId(): string {
    return backendAPIService.getConnectionId();
  }
}

// Global instance
export const connectionManager = new ConnectionManager(); 