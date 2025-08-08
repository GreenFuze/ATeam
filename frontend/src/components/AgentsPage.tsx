import React, { useState, useEffect } from 'react';
import {
  Container, Title, Card, Text, Group, Button, Badge,
  Stack, Grid
} from '@mantine/core';
import {
  IconMessageCircle, IconSettings, IconBrain
} from '@tabler/icons-react';
import { AgentConfig } from '../types';
import AgentChat from './AgentChat';
import AgentSettingsModal from './AgentSettingsModal';
import { connectionManager } from '../services/ConnectionManager';

interface AgentsPageProps {
  onAgentSelect: (agentId: string) => void;
}

const AgentsPage: React.FC<AgentsPageProps> = ({ onAgentSelect }) => {
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<AgentConfig | null>(null);

  useEffect(() => {
    // Set up WebSocket handlers for agent updates
    connectionManager.setFrontendAPIHandlers({
      onAgentListUpdateAgentsPage: (data: any) => {
        // Assert that data is properly structured - if not, there's a backend bug
        if (!data) {
          throw new Error('Backend sent undefined data for agent_list_update - this indicates a backend bug');
        }
        if (!data.agents) {
          throw new Error('Backend sent malformed agent_list_update data - missing agents array - this indicates a backend bug');
        }
        
        setAgents(data.agents);
        setLoading(false);
      },
    });

    // Load initial data via WebSocket
    if (connectionManager.isConnected()) {
      connectionManager.sendGetAgents();
    } else {
      // Wait for connection to be established
      const checkConnection = setInterval(() => {
        if (connectionManager.isConnected()) {
          connectionManager.sendGetAgents();
          clearInterval(checkConnection);
        }
      }, 1000);
    }
  }, []);

  const handleAgentSelect = (agentId: string) => {
    setSelectedAgentId(agentId);
    onAgentSelect(agentId);
  };

  const handleAgentSettings = (agentId: string) => {
    const agent = agents.find(a => a.id === agentId);
    if (agent) {
      setEditingAgent(agent);
      setSettingsModalOpen(true);
    }
  };

  const handleAddAgent = () => {
    setEditingAgent(null);
    setSettingsModalOpen(true);
  };

  const handleSettingsSuccess = () => {
    // Refresh agents list via WebSocket
    connectionManager.sendGetAgents();
  };

  if (loading) {
    return (
      <Container size="lg" py="xl">
        <Text>Loading agents...</Text>
      </Container>
    );
  }

  // If an agent is selected, show the chat interface
  if (selectedAgentId) {
    return (
      <div className="h-full">
        <AgentChat agentId={selectedAgentId} />
      </div>
    );
  }

  // Default view - show agent list
  return (
    <Container size="lg" py="xl">
      <Group justify="space-between" mb="xl">
        <Title order={1}>Agents</Title>
        <Button
          leftSection={<IconBrain size={16} />}
          onClick={handleAddAgent}
        >
          Create Agent
        </Button>
      </Group>

      <Grid>
        {agents.map((agent) => (
          <Grid.Col key={agent.id} span={{ base: 12, sm: 6, lg: 4 }}>
            <Card shadow="sm" padding="lg" radius="md" withBorder>
              <Group justify="space-between" mb="xs">
                <Title order={3}>{agent.name}</Title>
                <Badge variant="light" color="blue">
                  {agent.model}
                </Badge>
              </Group>

              <Text size="sm" c="dimmed" mb="md" lineClamp={3}>
                {agent.description}
              </Text>

              <Group gap="xs" mb="md">
                {agent.tools.length > 0 && (
                  <Badge size="sm" variant="outline">
                    {agent.tools.length} Tools
                  </Badge>
                )}
                {agent.prompts.length > 0 && (
                  <Badge size="sm" variant="outline">
                    {agent.prompts.length} Prompts
                  </Badge>
                )}
                {agent.enable_summarization && (
                  <Badge size="sm" color="green" variant="light">
                    Summarization
                  </Badge>
                )}
              </Group>

              <Group gap="xs">
                <Button
                  size="sm"
                  leftSection={<IconMessageCircle size={14} />}
                  onClick={() => handleAgentSelect(agent.id)}
                  className="flex-1"
                >
                  Chat
                </Button>
                <Button
                  size="sm"
                  variant="light"
                  leftSection={<IconSettings size={14} />}
                  onClick={() => handleAgentSettings(agent.id)}
                >
                  Settings
                </Button>
              </Group>
            </Card>
          </Grid.Col>
        ))}
      </Grid>

      {agents.length === 0 && (
        <Card shadow="sm" padding="xl" radius="md" withBorder>
          <Stack align="center" gap="md">
            <IconBrain size={48} style={{ opacity: 0.5 }} />
            <Title order={3}>No agents created yet</Title>
            <Text size="lg" c="dimmed" ta="center">
              Create your first agent to start chatting with AI assistants
            </Text>
            <Text size="sm" c="dimmed" ta="center">
              Agents are AI assistants that can use tools, follow prompts, and help you with various tasks.
            </Text>
            <Button 
              leftSection={<IconBrain size={16} />}
              onClick={handleAddAgent}
              size="lg"
            >
              Create Your First Agent
            </Button>
          </Stack>
        </Card>
      )}

      {/* Agent Settings Modal */}
      <AgentSettingsModal
        opened={settingsModalOpen}
        onClose={() => setSettingsModalOpen(false)}
        agent={editingAgent}
        onSuccess={handleSettingsSuccess}
      />
    </Container>
  );
};

export default AgentsPage;