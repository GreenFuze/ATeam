/**
 * ConnectionManager - Manages both FrontendAPI and BackendAPI WebSocket connections
 * Provides unified interface for dual WebSocket architecture
 */

import { frontendAPIService, FrontendAPIHandlers } from './FrontendAPIService';
import { backendAPIService } from './BackendAPIService';

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
    
    this.status.frontendAPI = frontendAPIService.isConnected();
    this.status.backendAPI = backendAPIService.isConnected();
    this.status.isConnecting = this.status.isConnecting && (!this.status.frontendAPI || !this.status.backendAPI);

    const isConnected = this.isConnected();

    // Notify status change
    if (this.callbacks.onStatusChange) {
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

  public sendRegisterAgent(agentId: string): void {
    backendAPIService.sendRegisterAgent(agentId);
  }

  // New methods for replacing REST API calls
  public sendGetAgents(): void {
    backendAPIService.sendGetAgents();
  }

  public getAgents(): any[] {
    return [...this.agents];
  }

  public updateAgents(agents: any[]): void {
    this.agents = agents;
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

  public getFrontendAPIConnectionId(): string {
    return frontendAPIService.getConnectionId();
  }

  public getBackendAPIConnectionId(): string {
    return backendAPIService.getConnectionId();
  }
}

// Global instance
export const connectionManager = new ConnectionManager(); 