import React, { useState, useEffect } from 'react';
import {
  Card,
  Text,
  Group,
  Badge,
  Progress,
  Stack,
  Grid,
  Title,
  Paper,
  List,
  ThemeIcon,
} from '@mantine/core';
import { IconActivity, IconAlertTriangle, IconCheck, IconX } from '@tabler/icons-react';
import { connectionManager } from '../services/ConnectionManager';

interface SystemHealth {
  system: {
    status: string;
    cpu_percent: number;
    memory_percent: number;
    disk_percent: number;
    network_connections: number;
  };
  llm: {
    status: string;
    message?: string;
    error?: string;
  };
}

interface PerformanceMetrics {
  [key: string]: Array<{
    timestamp: string;
    value: number;
    tags: Record<string, string>;
  }>;
}

interface ErrorSummary {
  total_errors: number;
  error_types: Record<string, number>;
  recent_errors: Array<{
    timestamp: string;
    error_type: string;
    error_message: string;
  }>;
}

const MonitoringDashboard: React.FC = () => {
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics>({});
  const [errorSummary, setErrorSummary] = useState<ErrorSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Set up WebSocket handlers for monitoring data
    connectionManager.setFrontendAPIHandlers({
      onMonitoringHealth: (data: any) => {
        console.log('Received monitoring health:', data);
        setSystemHealth(data);
        setLoading(false);
      },
      onMonitoringMetrics: (data: any) => {
        console.log('Received monitoring metrics:', data);
        setPerformanceMetrics(data);
        setLoading(false);
      },
      onMonitoringErrors: (data: any) => {
        console.log('Received monitoring errors:', data);
        setErrorSummary(data);
        setLoading(false);
      },
    });

    // Load initial data via WebSocket
    setLoading(true);
    connectionManager.sendGetMonitoringHealth();
    connectionManager.sendGetMonitoringMetrics();
    connectionManager.sendGetMonitoringErrors();
    
    // Refresh data every 30 seconds
    const interval = setInterval(() => {
      connectionManager.sendGetMonitoringHealth();
      connectionManager.sendGetMonitoringMetrics();
      connectionManager.sendGetMonitoringErrors();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'green';
      case 'unhealthy':
        return 'red';
      case 'warning':
        return 'yellow';
      default:
        return 'gray';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <IconCheck size={16} />;
      case 'unhealthy':
        return <IconX size={16} />;
      case 'warning':
        return <IconAlertTriangle size={16} />;
      default:
        return <IconActivity size={16} />;
    }
  };

  if (loading) {
    return (
      <Card p="md">
        <Text>Loading monitoring data...</Text>
      </Card>
    );
  }

  return (
    <Stack gap="md">
      <Title order={2}>System Monitoring</Title>
      
      {/* System Health Overview */}
      {systemHealth && (
        <Grid>
          <Grid.Col span={{ base: 12, md: 6, lg: 3 }}>
            <Card p="md">
              <Group justify="space-between" mb="xs">
                <Text size="sm" fw={500}>CPU Usage</Text>
                <Badge color={getStatusColor(systemHealth.system.status)}>
                  {systemHealth.system.cpu_percent.toFixed(1)}%
                </Badge>
              </Group>
              <Progress 
                value={systemHealth.system.cpu_percent} 
                color={systemHealth.system.cpu_percent > 80 ? 'red' : 'blue'}
                size="sm"
              />
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 6, lg: 3 }}>
            <Card p="md">
              <Group justify="space-between" mb="xs">
                <Text size="sm" fw={500}>Memory Usage</Text>
                <Badge color={getStatusColor(systemHealth.system.status)}>
                  {systemHealth.system.memory_percent.toFixed(1)}%
                </Badge>
              </Group>
              <Progress 
                value={systemHealth.system.memory_percent} 
                color={systemHealth.system.memory_percent > 80 ? 'red' : 'green'}
                size="sm"
              />
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 6, lg: 3 }}>
            <Card p="md">
              <Group justify="space-between" mb="xs">
                <Text size="sm" fw={500}>Disk Usage</Text>
                <Badge color={getStatusColor(systemHealth.system.status)}>
                  {systemHealth.system.disk_percent.toFixed(1)}%
                </Badge>
              </Group>
              <Progress 
                value={systemHealth.system.disk_percent} 
                color={systemHealth.system.disk_percent > 80 ? 'red' : 'orange'}
                size="sm"
              />
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 6, lg: 3 }}>
            <Card p="md">
              <Group justify="space-between" mb="xs">
                <Text size="sm" fw={500}>Network Connections</Text>
                <Badge color="blue">{systemHealth.system.network_connections}</Badge>
              </Group>
              <Text size="xs" c="dimmed">Active connections</Text>
            </Card>
          </Grid.Col>
        </Grid>
      )}

      {/* Service Status */}
      {systemHealth && (
        <Card p="md">
          <Title order={3} mb="md">Service Status</Title>
          <Grid>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Group>
                <ThemeIcon 
                  color={getStatusColor(systemHealth.llm.status)} 
                  variant="light"
                >
                  {getStatusIcon(systemHealth.llm.status)}
                </ThemeIcon>
                <div>
                  <Text fw={500}>LLM Service</Text>
                  <Text size="sm" c="dimmed">
                    {systemHealth.llm.message || systemHealth.llm.error || 'No status message'}
                  </Text>
                </div>
              </Group>
            </Grid.Col>
          </Grid>
        </Card>
      )}

      {/* Performance Metrics */}
      {Object.keys(performanceMetrics).length > 0 && (
        <Card p="md">
          <Title order={3} mb="md">Performance Metrics</Title>
          <Grid>
            {Object.entries(performanceMetrics).slice(0, 6).map(([metricName, data]) => {
              // Assert that data is properly structured - if not, there's a backend bug
              if (!data || data.length === 0) {
                throw new Error(`Backend sent malformed performance metrics data for ${metricName} - empty or missing data array - this indicates a backend bug`);
              }
              
              const latestValue = data[data.length - 1]?.value || 0;
              const avgValue = data.reduce((sum, item) => sum + item.value, 0) / data.length || 0;
              
              return (
                <Grid.Col key={metricName} span={{ base: 12, md: 6, lg: 4 }}>
                  <Paper p="xs" withBorder>
                    <Text size="sm" fw={500} mb="xs">{metricName}</Text>
                    <Group justify="space-between">
                      <Text size="xs" c="dimmed">Latest: {latestValue.toFixed(3)}s</Text>
                      <Text size="xs" c="dimmed">Avg: {avgValue.toFixed(3)}s</Text>
                    </Group>
                  </Paper>
                </Grid.Col>
              );
            })}
          </Grid>
        </Card>
      )}

      {/* Error Summary */}
      {errorSummary && (
        <Card p="md">
          <Title order={3} mb="md">Error Summary (Last 24h)</Title>
          <Group mb="md">
            <Badge color="red" size="lg">
              {errorSummary.total_errors} Total Errors
            </Badge>
          </Group>
          
          {errorSummary.recent_errors.length > 0 && (
            <div>
              <Text size="sm" fw={500} mb="xs">Recent Errors:</Text>
              <List size="sm">
                {errorSummary.recent_errors.slice(0, 5).map((error, index) => (
                  <List.Item key={index}>
                    <Text size="xs" fw={500}>{error.error_type}</Text>
                    <Text size="xs" c="dimmed">{error.error_message}</Text>
                    <Text size="xs" c="dimmed">{new Date(error.timestamp).toLocaleString()}</Text>
                  </List.Item>
                ))}
              </List>
            </div>
          )}
        </Card>
      )}
    </Stack>
  );
};

export default MonitoringDashboard;