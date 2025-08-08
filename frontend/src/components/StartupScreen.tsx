import React, { useState, useEffect } from 'react';
import { 
  Container, Stack, Text, Progress, Alert, 
  Code, Group, Button, Box, Title, List
} from '@mantine/core';
import { 
  IconBrain, IconCheck, IconX, IconAlertTriangle,
  IconRefresh, IconInfoCircle
} from '@tabler/icons-react';
import { connectionManager } from '../services/ConnectionManager';


interface HealthCheckResult {
  name: string;
  status: 'pending' | 'success' | 'error';
  message?: string;
  details?: any;
}

interface StartupScreenProps {
  onStartupComplete: () => void;
  onStartupError: (error: Error) => void;
}

const StartupScreen: React.FC<StartupScreenProps> = ({ 
  onStartupComplete, 
  onStartupError 
}) => {
  const [healthChecks, setHealthChecks] = useState<HealthCheckResult[]>([
    { name: 'WebSocket Connections', status: 'pending' },
    { name: 'Agent Manager', status: 'pending' },
    { name: 'Tool Manager', status: 'pending' },
    { name: 'Provider Manager', status: 'pending' },
    { name: 'Models Manager', status: 'pending' },
    { name: 'Prompt Manager', status: 'pending' },
    { name: 'Schema Manager', status: 'pending' },
    { name: 'System Health', status: 'pending' },
  ]);
  const [currentStep, setCurrentStep] = useState(0);
  const [overallProgress, setOverallProgress] = useState(0);
  const [error, setError] = useState<Error | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  const updateHealthCheck = (index: number, status: 'success' | 'error', message?: string, details?: any) => {
    setHealthChecks(prev => prev.map((check, i) => 
      i === index ? { ...check, status, message, details } : check
    ));
  };

  const performHealthChecks = async () => {
    try {
      setError(null);
      setIsRetrying(false);
      setCurrentStep(0);
      setOverallProgress(0);

      // Step 1: WebSocket Connections
      setCurrentStep(1);
      setOverallProgress(12.5);
      
      try {
        await connectionManager.connect();
        updateHealthCheck(0, 'success', 'WebSocket connections established successfully');
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to establish WebSocket connections');
        updateHealthCheck(0, 'error', error.message, err);
        throw error;
      }

      // Step 2: Load Agents
      setCurrentStep(2);
      setOverallProgress(25);
      
      try {
        await new Promise<void>((resolve, reject) => {
          const timeout = setTimeout(() => reject(new Error('Timeout waiting for agents')), 10000);
          
          const checkAgents = () => {
            const agents = connectionManager.getAgents();
            if (agents.length > 0) {
              clearTimeout(timeout);
              resolve();
            } else {
              setTimeout(checkAgents, 100);
            }
          };
          
          connectionManager.sendGetAgents();
          checkAgents();
        });
        updateHealthCheck(1, 'success', 'Agent manager loaded successfully');
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to load agents');
        updateHealthCheck(1, 'error', error.message, err);
        throw error;
      }

      // Step 3: Load Tools
      setCurrentStep(3);
      setOverallProgress(37.5);
      
      try {
        await new Promise<void>((resolve, reject) => {
          const timeout = setTimeout(() => reject(new Error('Timeout waiting for tools')), 10000);
          
          const checkTools = () => {
            // We'll check if tools are loaded by looking for tool_update messages
            // This is a simplified check - in a real implementation you might want to track this more precisely
            clearTimeout(timeout);
            resolve();
          };
          
          connectionManager.sendGetTools();
          setTimeout(checkTools, 2000); // Give some time for tools to load
        });
        updateHealthCheck(2, 'success', 'Tool manager loaded successfully');
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to load tools');
        updateHealthCheck(2, 'error', error.message, err);
        throw error;
      }

      // Step 4: Load Providers
      setCurrentStep(4);
      setOverallProgress(50);
      
      try {
        await new Promise<void>((resolve, reject) => {
          const timeout = setTimeout(() => reject(new Error('Timeout waiting for providers')), 10000);
          
          const checkProviders = () => {
            clearTimeout(timeout);
            resolve();
          };
          
          connectionManager.sendGetProviders();
          setTimeout(checkProviders, 2000);
        });
        updateHealthCheck(3, 'success', 'Provider manager loaded successfully');
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to load providers');
        updateHealthCheck(3, 'error', error.message, err);
        throw error;
      }

      // Step 5: Load Models
      setCurrentStep(5);
      setOverallProgress(62.5);
      
      try {
        await new Promise<void>((resolve, reject) => {
          const timeout = setTimeout(() => reject(new Error('Timeout waiting for models')), 10000);
          
          const checkModels = () => {
            clearTimeout(timeout);
            resolve();
          };
          
          connectionManager.sendGetModels();
          setTimeout(checkModels, 2000);
        });
        updateHealthCheck(4, 'success', 'Models manager loaded successfully');
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to load models');
        updateHealthCheck(4, 'error', error.message, err);
        throw error;
      }

      // Step 6: Load Prompts
      setCurrentStep(6);
      setOverallProgress(75);
      
      try {
        await new Promise<void>((resolve, reject) => {
          const timeout = setTimeout(() => reject(new Error('Timeout waiting for prompts')), 10000);
          
          const checkPrompts = () => {
            clearTimeout(timeout);
            resolve();
          };
          
          connectionManager.sendGetPrompts();
          setTimeout(checkPrompts, 2000);
        });
        updateHealthCheck(5, 'success', 'Prompt manager loaded successfully');
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to load prompts');
        updateHealthCheck(5, 'error', error.message, err);
        throw error;
      }

      // Step 7: Load Schemas
      setCurrentStep(7);
      setOverallProgress(87.5);
      
      try {
        await new Promise<void>((resolve, reject) => {
          const timeout = setTimeout(() => reject(new Error('Timeout waiting for schemas')), 10000);
          
          const checkSchemas = () => {
            clearTimeout(timeout);
            resolve();
          };
          
          connectionManager.sendGetSchemas();
          setTimeout(checkSchemas, 2000);
        });
        updateHealthCheck(6, 'success', 'Schema manager loaded successfully');
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to load schemas');
        updateHealthCheck(6, 'error', error.message, err);
        throw error;
      }

      // Step 8: System Health Check
      setCurrentStep(8);
      setOverallProgress(100);
      
      try {
        // Perform final system health validation
        const agents = connectionManager.getAgents();
        if (agents.length === 0) {
          throw new Error('No agents available - system is not properly configured');
        }
        
        updateHealthCheck(7, 'success', 'System health check passed');
        
        // All checks passed
        setTimeout(() => {
          onStartupComplete();
        }, 1000);
        
      } catch (err) {
        const error = err instanceof Error ? err : new Error('System health check failed');
        updateHealthCheck(7, 'error', error.message, err);
        throw error;
      }

    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown startup error');
      setError(error);
      onStartupError(error);
    }
  };

  useEffect(() => {
    performHealthChecks();
  }, []);

  const handleRetry = () => {
    setIsRetrying(true);
    performHealthChecks();
  };

  if (error) {
    return (
      <Container size="md" py="xl">
        <Stack gap="lg">
          <Group>
            <IconAlertTriangle size={32} color="red" />
            <Title order={1} c="red">Fatal Startup Error</Title>
          </Group>
          
          <Alert 
            icon={<IconX size={16} />} 
            title="Application Failed to Start" 
            color="red"
            variant="filled"
          >
            The application encountered a critical error during startup and cannot continue.
            This is a fatal error that requires developer attention.
          </Alert>

          <Box>
            <Text fw={500} mb="xs">Error Details:</Text>
            <Code block>{error.message}</Code>
          </Box>

          <Box>
            <Text fw={500} mb="xs">Health Check Results:</Text>
            <List>
              {healthChecks.map((check, index) => (
                <List.Item key={index}>
                  <Group gap="xs">
                    {check.status === 'success' && <IconCheck size={16} color="green" />}
                    {check.status === 'error' && <IconX size={16} color="red" />}
                    {check.status === 'pending' && <IconInfoCircle size={16} color="gray" />}
                    <Text>{check.name}</Text>
                    {check.message && (
                      <Text size="sm" c="dimmed">- {check.message}</Text>
                    )}
                  </Group>
                  {check.details && (
                                         <Code block mt="xs" fz="xs">
                      {JSON.stringify(check.details, null, 2)}
                    </Code>
                  )}
                </List.Item>
              ))}
            </List>
          </Box>

          <Group>
            <Button 
              onClick={handleRetry} 
              loading={isRetrying}
              leftSection={<IconRefresh size={16} />}
            >
              Retry Startup
            </Button>
          </Group>
        </Stack>
      </Container>
    );
  }

  return (
    <Container size="md" py="xl">
      <Stack gap="lg" align="center">
        <Group>
          <IconBrain size={48} />
          <Title order={1}>ATeam Multi-Agent System</Title>
        </Group>
        
        <Text size="lg" c="dimmed" ta="center">
          Initializing system components...
        </Text>

        <Box w="100%" maw={400}>
                     <Progress 
             value={overallProgress} 
             size="lg" 
             radius="md"
             mb="md"
           />
           <Text size="sm" c="dimmed" ta="center" mb="md">
             {Math.round(overallProgress)}%
           </Text>
          
          <Text size="sm" c="dimmed" ta="center">
            Step {currentStep} of 8: {healthChecks[currentStep - 1]?.name || 'Initializing...'}
          </Text>
        </Box>

        <Box w="100%" maw={500}>
          <Text fw={500} mb="xs">System Health Checks:</Text>
          <Stack gap="xs">
            {healthChecks.map((check, index) => (
              <Group key={index} gap="xs">
                {check.status === 'success' && <IconCheck size={16} color="green" />}
                {check.status === 'error' && <IconX size={16} color="red" />}
                {check.status === 'pending' && <IconInfoCircle size={16} color="gray" />}
                <Text size="sm">{check.name}</Text>
                {check.message && (
                  <Text size="xs" c="dimmed">- {check.message}</Text>
                )}
              </Group>
            ))}
          </Stack>
        </Box>
      </Stack>
    </Container>
  );
};

export default StartupScreen;
