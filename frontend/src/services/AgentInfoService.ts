import { AgentConfig } from '../types';
import { agentsApi } from '../api';

interface AgentInfoCache {
  [agentId: string]: AgentConfig;
}

class AgentInfoService {
  private cache: AgentInfoCache = {};

  /**
   * Get agent information by ID. If not in cache, fetch from backend.
   * Follows fail-fast principle - throws error if agent not found.
   */
  async getAgentInfo(agentId: string): Promise<AgentConfig> {
    // Check cache first
    if (this.cache[agentId]) {
      return this.cache[agentId];
    }

    // Fetch from backend
    try {
      const agentInfo = await agentsApi.getById(agentId);
      
      // Cache the result permanently (agent info is static)
      this.cache[agentId] = agentInfo;
      
      return agentInfo;
    } catch (error) {
      // Fail-fast: throw error immediately if agent not found
      throw new Error(`Agent '${agentId}' not found: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Clear cache for a specific agent (useful when agent is updated)
   */
  clearAgentCache(agentId: string): void {
    delete this.cache[agentId];
  }

  /**
   * Clear entire cache
   */
  clearAllCache(): void {
    this.cache = {};
  }

  /**
   * Check if agent info is cached
   */
  isCached(agentId: string): boolean {
    return this.cache[agentId] !== undefined;
  }
}

// Export singleton instance
export const agentInfoService = new AgentInfoService();
