import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Text, Stack, NavLink, Group, ActionIcon, Tooltip,
  Tabs, Card, ScrollArea, Button, Modal
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
  IconCpu,
  IconCode,
  IconBell,
  IconAlertCircle
} from '@tabler/icons-react';
import { connectionManager } from '../services/ConnectionManager';

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
  const [notifications, setNotifications] = useState<any[]>([]);
  const [notificationModal, setNotificationModal] = useState(false);
  const [checkingHealth, setCheckingHealth] = useState(false);

  // Load agents when component mounts
  useEffect(() => {
    console.log('🔄 [Frontend] Sidebar useEffect() called - setting up WebSocket handlers');
    
    // Set up WebSocket handlers for agent updates and provider updates
    connectionManager.setFrontendAPIHandlers({
      onAgentListUpdateSidebar: (data) => {
        console.log('📥 [Frontend] Sidebar received agent list update:', data);
        
        // Assert that data is properly structured - if not, there's a backend bug
        if (!data) {
          throw new Error('Backend sent undefined data for agent_list_update - this indicates a backend bug');
        }
        if (!data.agents) {
          throw new Error('Backend sent malformed agent_list_update data - missing agents array - this indicates a backend bug');
        }
        
        const agents = data.agents;
        console.log('📥 [Frontend] Sidebar setting agents:', agents);
        setAgents(agents);
        setLoading(false);
        console.log('✅ [Frontend] Sidebar agents updated, loading set to false');
      },
      onProviderUpdate: (data) => {
        console.log('📥 [Frontend] Sidebar received provider update:', data);
        
        // Assert that data is properly structured - if not, there's a backend bug
        if (!data) {
          throw new Error('Backend sent undefined data for provider_update - this indicates a backend bug');
        }
        if (!data.providers) {
          throw new Error('Backend sent malformed provider_update data - missing providers array - this indicates a backend bug');
        }
        
        const providers = data.providers;
        const newNotifications: any[] = [];
        
        // Check for unconfigured providers
        providers.forEach((provider: any) => {
          if (!provider.configured) {
            newNotifications.push({
              id: `provider-${provider.name}`,
              type: 'warning',
              title: 'Provider Not Configured',
              message: `Provider "${provider.display_name}" is detected but not configured. Please configure it in Settings.`,
              timestamp: new Date().toISOString()
            });
          }
        });
        
        setNotifications(newNotifications);
        setCheckingHealth(false);
      },
    });

    // Request agents via WebSocket
    console.log('🔄 [Frontend] Sidebar requesting agents via WebSocket');
    connectionManager.sendGetAgents();
    setLoading(true);
    console.log('🔄 [Frontend] Sidebar loading set to true');
    
    // Request providers via WebSocket
    console.log('🔄 [Frontend] Sidebar requesting providers via WebSocket');
    connectionManager.sendGetProviders();
    setCheckingHealth(true);
  }, []);

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

  const getNotificationIcon = () => {
    if (notifications.length === 0) {
      return <IconBell size={20} />;
    }
    
    const hasErrors = notifications.some(n => n.type === 'error');
    const hasWarnings = notifications.some(n => n.type === 'warning');
    
    if (hasErrors) {
      return <IconAlertCircle size={20} color="red" />;
    } else if (hasWarnings) {
      return <IconAlertCircle size={20} color="orange" />;
    } else {
      return <IconBell size={20} color="blue" />;
    }
  };

  return (
    <div className="sidebar p-4">
      <div className="mb-6">
        <Group justify="space-between" align="center">
          <Text size="lg" fw={700} className="text-dark-primary">
            A-Team
          </Text>
          <Tooltip label={notifications.length > 0 ? `${notifications.length} notification(s)` : 'No notifications'}>
            <ActionIcon
              variant="subtle"
              onClick={() => setNotificationModal(true)}
              disabled={checkingHealth}
              className="relative"
            >
              {getNotificationIcon()}
              {notifications.length > 0 && (
                <div className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full min-w-[20px] h-5 flex items-center justify-center px-1.5">
                  {notifications.length > 99 ? '99+' : notifications.length}
                </div>
              )}
            </ActionIcon>
          </Tooltip>
        </Group>
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
                label="Schemas"
                leftSection={<IconCode size={16} />}
                active={location.pathname === '/settings' && location.search.includes('tab=schemas')}
                onClick={() => handleNavigation('/settings?tab=schemas')}
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

      {/* Notification Modal */}
      <Modal
        opened={notificationModal}
        onClose={() => setNotificationModal(false)}
        title="System Notifications"
        size="lg"
      >
        <Stack gap="md">
          {checkingHealth ? (
            <Text c="dimmed">Checking system health...</Text>
          ) : notifications.length === 0 ? (
            <Text c="dimmed">No notifications. System is healthy!</Text>
          ) : (
            <>
              <Group justify="space-between">
                <Text fw={500}>Found {notifications.length} notification(s)</Text>
                <Button
                  size="xs"
                  variant="light"
                  onClick={() => {
                    setCheckingHealth(true);
                    connectionManager.sendGetProviders();
                  }}
                  loading={checkingHealth}
                >
                  Refresh
                </Button>
              </Group>
              
              <Stack gap="sm">
                {notifications.map((notification) => (
                  <Card key={notification.id} p="sm" withBorder>
                    <Group gap="sm" align="flex-start">
                      <div>
                        {notification.type === 'error' && <IconAlertCircle size={16} color="red" />}
                        {notification.type === 'warning' && <IconAlertCircle size={16} color="orange" />}
                        {notification.type === 'info' && <IconBell size={16} color="blue" />}
                      </div>
                      <div style={{ flex: 1 }}>
                        <Text size="sm" fw={500}>
                          {notification.title}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {notification.message}
                        </Text>
                        <Text size="xs" c="dimmed" mt="xs">
                          {new Date(notification.timestamp).toLocaleString()}
                        </Text>
                      </div>
                    </Group>
                  </Card>
                ))}
              </Stack>
            </>
          )}
        </Stack>
      </Modal>
    </div>
  );
};

export default Sidebar; 