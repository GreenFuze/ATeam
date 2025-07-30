import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Text, Stack, NavLink, Group, ActionIcon, Tooltip,
  Tabs, Card, ScrollArea, Button
} from '@mantine/core';
import {
  IconBrain,
  IconMessageCircle,
  IconSettings,
  IconTools,
  IconFileText,
  IconActivity,
  IconUsers,
  IconPlus,
  IconCpu
} from '@tabler/icons-react';

interface SidebarProps {
  onAgentSelect: (agentId: string) => void;
  selectedAgentId?: string | null;
  onAddAgent: () => void;
  onAgentSettings: (agentId: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  onAgentSelect,
  selectedAgentId,
  onAddAgent,
  onAgentSettings,
}) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<string | null>('agents');
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // Load agents when component mounts
  React.useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/agents');
      const data = await response.json();
      setAgents(data.agents || []);
    } catch (error) {
      console.error('Failed to load agents:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleNavigation = (path: string) => {
    navigate(path);
  };

  const handleAgentSelect = (agentId: string) => {
    onAgentSelect(agentId);
    setActiveTab('agents');
  };

  const handleAgentSettings = (agentId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    onAgentSettings(agentId);
  };

  return (
    <div className="sidebar p-4">
      <div className="mb-6">
        <Text size="lg" fw={700} className="text-dark-primary">
          ATeam
        </Text>
      </div>

      <Tabs value={activeTab} onChange={setActiveTab} className="flex-1">
        <Tabs.List className="mb-4">
          <Tabs.Tab 
            value="agents" 
            leftSection={<IconBrain size={16} />}
            className="flex-1"
          >
            Agents
          </Tabs.Tab>
          <Tabs.Tab 
            value="settings" 
            leftSection={<IconSettings size={16} />}
            className="flex-1"
          >
            Settings
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="agents" className="flex-1">
          <ScrollArea className="h-full">
            <Stack gap="xs">
              {loading ? (
                <Text size="sm" c="dimmed">Loading agents...</Text>
              ) : agents.length === 0 ? (
                <Text size="sm" c="dimmed">No agents found</Text>
              ) : (
                agents.map((agent) => (
                  <Card 
                    key={agent.id} 
                    p="xs" 
                    className={`cursor-pointer transition-colors ${
                      selectedAgentId === agent.id 
                        ? 'bg-blue-600/20 border-blue-500/50' 
                        : 'hover:bg-dark-7'
                    }`}
                    onClick={() => handleAgentSelect(agent.id)}
                  >
                    <Group justify="space-between" align="center">
                      <div className="flex-1 min-w-0">
                        <Text size="sm" fw={500} truncate>
                          {agent.name}
                        </Text>
                        <Text size="xs" c="dimmed" lineClamp={2}>
                          {agent.description}
                        </Text>
                      </div>
                      <Group gap="xs">
                        <Tooltip label="Chat">
                          <ActionIcon 
                            size="sm" 
                            variant="subtle"
                            onClick={() => handleAgentSelect(agent.id)}
                          >
                            <IconMessageCircle size={14} />
                          </ActionIcon>
                        </Tooltip>
                        <Tooltip label="Settings">
                          <ActionIcon 
                            size="sm" 
                            variant="subtle"
                            onClick={(e) => handleAgentSettings(agent.id, e)}
                          >
                            <IconSettings size={14} />
                          </ActionIcon>
                        </Tooltip>
                      </Group>
                    </Group>
                  </Card>
                ))
              )}
              
              {/* Add Agent Button */}
              <Button
                variant="light"
                color="blue"
                leftSection={<IconPlus size={16} />}
                onClick={onAddAgent}
                className="mt-2"
                fullWidth
              >
                Add Agent
              </Button>
            </Stack>
          </ScrollArea>
        </Tabs.Panel>

        <Tabs.Panel value="settings" className="flex-1">
          <ScrollArea className="h-full">
            <Stack gap="xs">
              <NavLink
                label="Tools"
                leftSection={<IconTools size={16} />}
                active={location.pathname === '/settings' && location.search.includes('tab=tools')}
                onClick={() => handleNavigation('/settings?tab=tools')}
                className="text-dark-primary hover:bg-dark-7"
              />
              <NavLink
                label="Models"
                leftSection={<IconCpu size={16} />}
                active={location.pathname === '/settings' && location.search.includes('tab=models')}
                onClick={() => handleNavigation('/settings?tab=models')}
                className="text-dark-primary hover:bg-dark-7"
              />
              <NavLink
                label="Providers"
                leftSection={<IconUsers size={16} />}
                active={location.pathname === '/settings' && location.search.includes('tab=providers')}
                onClick={() => handleNavigation('/settings?tab=providers')}
                className="text-dark-primary hover:bg-dark-7"
              />
              <NavLink
                label="Prompts"
                leftSection={<IconFileText size={16} />}
                active={location.pathname === '/settings' && location.search.includes('tab=prompts')}
                onClick={() => handleNavigation('/settings?tab=prompts')}
                className="text-dark-primary hover:bg-dark-7"
              />
              <NavLink
                label="Monitoring"
                leftSection={<IconActivity size={16} />}
                active={location.pathname === '/settings' && location.search.includes('tab=monitoring')}
                onClick={() => handleNavigation('/settings?tab=monitoring')}
                className="text-dark-primary hover:bg-dark-7"
              />
            </Stack>
          </ScrollArea>
        </Tabs.Panel>
      </Tabs>
    </div>
  );
};

export default Sidebar; 