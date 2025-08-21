/**
 * StreamingClient - Handles HTTP Server-Sent Events for content streaming
 * Manages concurrent streams with limits and error handling
 */

export interface StreamChunk {
  chunk: string;
  type: 'progress' | 'content' | 'complete' | 'error';
  timestamp: string;
  chunk_id: number;
  error?: string;
}

export interface StreamCallbacks {
  onProgress?: (chunk: StreamChunk) => void;
  onContent?: (chunk: StreamChunk) => void;
  onComplete?: (chunk: StreamChunk) => void;
  onError?: (error: string) => void;
}

export interface StreamState {
  guid: string;
  agentId: string;
  sessionId: string;
  state: 'connecting' | 'streaming' | 'complete' | 'error' | 'cancelled' | 'paused';
  content: string;
  error?: string;
  startTime: number;
  lastActivity: number;
  memoryUsage: number; // Track memory usage in bytes
}

export class StreamingClient {
  private activeStreams: Map<string, StreamState> = new Map();
  private streamCallbacks: Map<string, StreamCallbacks> = new Map();
  private maxConcurrentStreams = 5;
  private streamTimeout = 10000; // 10 seconds
  private baseUrl: string;
  // Chunk buffering for smooth display
  private chunkBuffers: Map<string, string> = new Map();
  private bufferThreshold = 100; // Accumulate chunks < 100 chars before UI update
  private bufferTimeouts: Map<string, NodeJS.Timeout> = new Map();
  // Stream throttling for rapid content delivery
  private lastUpdateTimes: Map<string, number> = new Map();
  private minUpdateInterval = 50; // Minimum 50ms between UI updates

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.startCleanupInterval();
    this.setupTabFocusHandlers();
  }

  /**
   * Start streaming content for a message GUID with priority handling
   */
  public async startStream(
    guid: string,
    agentId: string,
    sessionId: string,
    callbacks: StreamCallbacks,
    priority: 'high' | 'low' = 'low'
  ): Promise<boolean> {
    // Check concurrent stream limit with priority handling
    if (this.activeStreams.size >= this.maxConcurrentStreams) {
      // If this is a high priority stream, try to cancel a low priority one
      if (priority === 'high') {
        const cancelled = this.cancelLowPriorityStream();
        if (!cancelled) {
          console.warn(`Stream limit reached (${this.maxConcurrentStreams}), cannot start high priority stream for ${guid}`);
          callbacks.onError?.('Stream limit reached');
          return false;
        }
      } else {
        console.warn(`Stream limit reached (${this.maxConcurrentStreams}), cannot start stream for ${guid}`);
        callbacks.onError?.('Stream limit reached');
        return false;
      }
    }

    // Check if stream already exists
    if (this.activeStreams.has(guid)) {
      console.warn(`Stream ${guid} already exists`);
      callbacks.onError?.('Stream already exists');
      return false;
    }

    // Create stream state
    const streamState: StreamState = {
      guid,
      agentId,
      sessionId,
      state: 'connecting',
      content: '',
      startTime: Date.now(),
      lastActivity: Date.now(),
      memoryUsage: 0
    };

    this.activeStreams.set(guid, streamState);
    this.streamCallbacks.set(guid, callbacks);

    try {
      // Start HTTP SSE connection
      await this.connectToStream(guid);
      return true;
    } catch (error) {
      console.error(`Failed to start stream ${guid}:`, error);
      this.cleanupStream(guid);
      callbacks.onError?.(`Failed to start stream: ${error}`);
      return false;
    }
  }

  /**
   * Connect to HTTP Server-Sent Events stream
   */
  private async connectToStream(guid: string): Promise<void> {
    const streamState = this.activeStreams.get(guid);
    const callbacks = this.streamCallbacks.get(guid);
    
    if (!streamState || !callbacks) {
      throw new Error(`Stream ${guid} not found`);
    }

    const url = `${this.baseUrl}/api/message/${guid}/content`;
    console.log(`Connecting to stream: ${url}`);

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      // Update stream state
      streamState.state = 'streaming';
      streamState.lastActivity = Date.now();

      // Read the stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            break;
          }

          const chunk = decoder.decode(value, { stream: true });
          this.processStreamChunk(guid, chunk);
        }
      } finally {
        reader.releaseLock();
      }

    } catch (error) {
      console.error(`Stream ${guid} error:`, error);
      streamState.state = 'error';
      streamState.error = error instanceof Error ? error.message : String(error);
      streamState.lastActivity = Date.now();
      
      callbacks.onError?.(streamState.error);
    }
  }

  /**
   * Process incoming stream chunks
   */
  private processStreamChunk(guid: string, chunk: string): void {
    const streamState = this.activeStreams.get(guid);
    const callbacks = this.streamCallbacks.get(guid);
    
    if (!streamState || !callbacks) {
      return;
    }

    // Update last activity
    streamState.lastActivity = Date.now();

    // Parse SSE format: "data: {json}\n\n"
    const lines = chunk.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const jsonData = line.slice(6); // Remove "data: " prefix
          const streamChunk: StreamChunk = JSON.parse(jsonData);
          
          console.log(`Stream ${guid} chunk:`, streamChunk);
          
          // Handle different chunk types
          switch (streamChunk.type) {
            case 'progress':
              callbacks.onProgress?.(streamChunk);
              break;
              
            case 'content':
              // Calculate memory usage (rough estimate: 2 bytes per character for UTF-16)
              const newContentSize = streamChunk.chunk.length * 2;
              const newTotalMemory = streamState.memoryUsage + newContentSize;
              
              // Check if adding this chunk would exceed 1MB limit
              const maxMemoryBytes = 1024 * 1024; // 1MB
              if (newTotalMemory > maxMemoryBytes) {
                // Memory limit exceeded, truncate content and show warning
                const remainingBytes = maxMemoryBytes - streamState.memoryUsage;
                const remainingChars = Math.floor(remainingBytes / 2);
                const truncatedChunk = streamChunk.chunk.substring(0, remainingChars);
                
                streamState.content += truncatedChunk;
                streamState.memoryUsage = maxMemoryBytes;
                
                // Send error callback with memory limit warning
                callbacks.onError?.('Memory limit exceeded (1MB). Content has been truncated.');
                console.warn(`Stream ${guid} exceeded 1MB memory limit, content truncated`);
              } else {
                // Memory usage is within limits
                streamState.content += streamChunk.chunk;
                streamState.memoryUsage = newTotalMemory;
              }
              
              // Implement chunk buffering for smooth display
              const currentBuffer = this.chunkBuffers.get(guid) || '';
              const newBuffer = currentBuffer + streamChunk.chunk;
              
              if (newBuffer.length >= this.bufferThreshold) {
                // Buffer is full, check throttling before sending
                const now = Date.now();
                const lastUpdate = this.lastUpdateTimes.get(guid) || 0;
                
                if (now - lastUpdate >= this.minUpdateInterval) {
                  // Enough time has passed, send immediately
                  this.chunkBuffers.set(guid, '');
                  this.lastUpdateTimes.set(guid, now);
                  callbacks.onContent?.({
                    ...streamChunk,
                    chunk: newBuffer
                  });
                  
                  // Clear any pending timeout
                  const timeout = this.bufferTimeouts.get(guid);
                  if (timeout) {
                    clearTimeout(timeout);
                    this.bufferTimeouts.delete(guid);
                  }
                } else {
                  // Throttled, keep in buffer and set timeout
                  this.chunkBuffers.set(guid, newBuffer);
                  const delay = this.minUpdateInterval - (now - lastUpdate);
                  
                  // Clear existing timeout
                  const existingTimeout = this.bufferTimeouts.get(guid);
                  if (existingTimeout) {
                    clearTimeout(existingTimeout);
                  }
                  
                  // Set new timeout
                  const timeout = setTimeout(() => {
                    const bufferedContent = this.chunkBuffers.get(guid) || '';
                    if (bufferedContent) {
                      this.chunkBuffers.set(guid, '');
                      this.lastUpdateTimes.set(guid, Date.now());
                      callbacks.onContent?.({
                        ...streamChunk,
                        chunk: bufferedContent
                      });
                    }
                    this.bufferTimeouts.delete(guid);
                  }, delay);
                  
                  this.bufferTimeouts.set(guid, timeout);
                }
              } else {
                // Buffer is not full yet, store and set timeout
                this.chunkBuffers.set(guid, newBuffer);
                
                // Clear existing timeout
                const existingTimeout = this.bufferTimeouts.get(guid);
                if (existingTimeout) {
                  clearTimeout(existingTimeout);
                }
                
                // Set new timeout to flush buffer after 50ms
                const timeout = setTimeout(() => {
                  const bufferedContent = this.chunkBuffers.get(guid) || '';
                  if (bufferedContent) {
                    this.chunkBuffers.set(guid, '');
                    callbacks.onContent?.({
                      ...streamChunk,
                      chunk: bufferedContent
                    });
                  }
                  this.bufferTimeouts.delete(guid);
                }, 50);
                
                this.bufferTimeouts.set(guid, timeout);
              }
              break;
              
            case 'complete':
              streamState.state = 'complete';
              streamState.lastActivity = Date.now();
              callbacks.onComplete?.(streamChunk);
              this.cleanupStream(guid);
              break;
              
            case 'error':
              streamState.state = 'error';
              streamState.error = streamChunk.error || 'Stream error';
              streamState.lastActivity = Date.now();
              callbacks.onError?.(streamState.error);
              this.cleanupStream(guid);
              break;
          }
        } catch (error) {
          console.error(`Failed to parse stream chunk for ${guid}:`, error);
        }
      }
    }
  }

  /**
   * Cancel an active stream
   */
  public async cancelStream(guid: string): Promise<boolean> {
    const streamState = this.activeStreams.get(guid);
    
    if (!streamState) {
      return false;
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/message/${guid}/cancel`, {
        method: 'POST'
      });

      if (response.ok) {
        streamState.state = 'cancelled';
        streamState.lastActivity = Date.now();
        this.cleanupStream(guid);
        return true;
      }
    } catch (error) {
      console.error(`Failed to cancel stream ${guid}:`, error);
    }

    return false;
  }

  /**
   * Pause an active stream
   */
  public async pauseStream(guid: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/message/${guid}/pause`, {
        method: 'POST'
      });
      return response.ok;
    } catch (error) {
      console.error(`Failed to pause stream ${guid}:`, error);
      return false;
    }
  }

  /**
   * Resume a paused stream
   */
  public async resumeStream(guid: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/message/${guid}/resume`, {
        method: 'POST'
      });
      return response.ok;
    } catch (error) {
      console.error(`Failed to resume stream ${guid}:`, error);
      return false;
    }
  }

  /**
   * Get stream state
   */
  public getStreamState(guid: string): StreamState | undefined {
    return this.activeStreams.get(guid);
  }

  /**
   * Get all active streams
   */
  public getActiveStreams(): Map<string, StreamState> {
    return new Map(this.activeStreams);
  }

  /**
   * Clean up all streams (for reconnection scenarios)
   */
  public cleanupAllStreams(): void {
    const streamsToRemove = Array.from(this.activeStreams.keys());
    streamsToRemove.forEach(guid => this.cleanupStream(guid));
    console.log(`🧹 [StreamingClient] Cleaned up ${streamsToRemove.length} streams`);
  }

  /**
   * Reconnect to a stream after WebSocket reconnection
   */
  public async reconnectStream(guid: string): Promise<void> {
    const streamState = this.activeStreams.get(guid);
    if (!streamState) {
      throw new Error(`Stream ${guid} not found for reconnection`);
    }

    // Reset stream state for reconnection
    streamState.state = 'connecting';
    streamState.lastActivity = Date.now();
    streamState.error = undefined;

    // Attempt to reconnect to the stream
    await this.connectToStream(guid);
  }

  /**
   * Cancel a low priority stream to make room for high priority streams
   */
  private cancelLowPriorityStream(): boolean {
    // Find the first low priority stream (chat responses) to cancel
    for (const [guid] of this.activeStreams.entries()) {
      // For now, we'll assume all streams are low priority unless specified
      // In a real implementation, you'd track priority per stream
      console.log(`🔄 [StreamingClient] Cancelling low priority stream ${guid} to make room for high priority stream`);
      this.cancelStream(guid);
      return true;
    }
    return false;
  }

  /**
   * Mark a stream as failed (for recovery scenarios)
   */
  public markStreamAsFailed(guid: string, error: string): void {
    const streamState = this.activeStreams.get(guid);
    if (streamState) {
      streamState.state = 'error';
      streamState.error = error;
      streamState.lastActivity = Date.now();
      
      // Call error callback if available
      const callbacks = this.streamCallbacks.get(guid);
      callbacks?.onError?.(error);
      
      // Clean up the failed stream
      this.cleanupStream(guid);
    }
  }

  /**
   * Clean up a stream
   */
  private cleanupStream(guid: string): void {
    this.activeStreams.delete(guid);
    this.streamCallbacks.delete(guid);
    
    // Clean up buffering resources
    this.chunkBuffers.delete(guid);
    const timeout = this.bufferTimeouts.get(guid);
    if (timeout) {
      clearTimeout(timeout);
      this.bufferTimeouts.delete(guid);
    }
    
    // Clean up throttling resources
    this.lastUpdateTimes.delete(guid);
  }

  /**
   * Clean up all streams for an agent
   */
  public cleanupAgentStreams(agentId: string): void {
    const streamsToRemove: string[] = [];
    
    for (const [guid, streamState] of this.activeStreams.entries()) {
      if (streamState.agentId === agentId) {
        streamsToRemove.push(guid);
      }
    }
    
    for (const guid of streamsToRemove) {
      this.cleanupStream(guid);
    }
  }

  /**
   * Start periodic cleanup of expired streams
   */
  private startCleanupInterval(): void {
    setInterval(() => {
      const now = Date.now();
      const streamsToRemove: string[] = [];
      
      for (const [guid, streamState] of this.activeStreams.entries()) {
        if (now - streamState.lastActivity > this.streamTimeout) {
          console.log(`Stream ${guid} expired, cleaning up`);
          streamsToRemove.push(guid);
        }
      }
      
      for (const guid of streamsToRemove) {
        const callbacks = this.streamCallbacks.get(guid);
        callbacks?.onError?.('Stream timeout');
        this.cleanupStream(guid);
      }
    }, 5000); // Check every 5 seconds
  }

  /**
   * Setup browser tab focus/blur handlers for stream management
   */
  private setupTabFocusHandlers(): void {
    // Pause streams when tab loses focus
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.pauseAllStreams();
      } else {
        this.resumeAllStreams();
      }
    });

    // Pause streams when window loses focus
    window.addEventListener('blur', () => {
      this.pauseAllStreams();
    });

    // Resume streams when window gains focus
    window.addEventListener('focus', () => {
      this.resumeAllStreams();
    });
  }

  /**
   * Pause all active streams
   */
  private async pauseAllStreams(): Promise<void> {
    const activeStreams = Array.from(this.activeStreams.keys());
    
    for (const guid of activeStreams) {
      const streamState = this.activeStreams.get(guid);
      if (streamState && streamState.state === 'streaming') {
        try {
          await this.pauseStream(guid);
          streamState.state = 'paused';
          console.log(`⏸️ [StreamingClient] Paused stream ${guid} due to tab/window blur`);
        } catch (error) {
          console.warn(`Failed to pause stream ${guid}:`, error);
        }
      }
    }
  }

  /**
   * Resume all paused streams
   */
  private async resumeAllStreams(): Promise<void> {
    const activeStreams = Array.from(this.activeStreams.keys());
    
    for (const guid of activeStreams) {
      const streamState = this.activeStreams.get(guid);
      if (streamState && streamState.state === 'paused') {
        try {
          await this.resumeStream(guid);
          streamState.state = 'streaming';
          console.log(`▶️ [StreamingClient] Resumed stream ${guid} due to tab/window focus`);
        } catch (error) {
          console.warn(`Failed to resume stream ${guid}:`, error);
        }
      }
    }
  }

  /**
   * Get streaming statistics
   */
  public getStats(): {
    activeStreams: number;
    maxConcurrentStreams: number;
    streamTimeout: number;
    totalMemoryUsage: number;
    averageMemoryPerStream: number;
  } {
    let totalMemory = 0;
    for (const streamState of this.activeStreams.values()) {
      totalMemory += streamState.memoryUsage;
    }
    
    const averageMemory = this.activeStreams.size > 0 ? totalMemory / this.activeStreams.size : 0;
    
    return {
      activeStreams: this.activeStreams.size,
      maxConcurrentStreams: this.maxConcurrentStreams,
      streamTimeout: this.streamTimeout,
      totalMemoryUsage: totalMemory,
      averageMemoryPerStream: averageMemory
    };
  }
}

// Global streaming client instance
export const streamingClient = new StreamingClient();
