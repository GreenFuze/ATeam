import React, { useState, useEffect } from 'react';
import { Modal, Text, Button, Group, Stack, Progress, Alert } from '@mantine/core';
import { IconAlertCircle, IconCheck, IconX, IconRefresh } from '@tabler/icons-react';
import { ConnectionStatus } from '../services/ConnectionManager';

interface ConnectionDialogProps {
  isOpen: boolean;
  onClose: () => void;
  status: ConnectionStatus;
  onRetry: () => void;
}

export const ConnectionDialog: React.FC<ConnectionDialogProps> = ({
  isOpen,
  onClose,
  status,
  onRetry
}) => {
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    if (status.isConnecting) {
      setRetryCount(prev => prev + 1);
    }
  }, [status.isConnecting]);

  const getStatusIcon = (isConnected: boolean) => {
    return isConnected ? <IconCheck size={16} color="green" /> : <IconX size={16} color="red" />;
  };

  const getStatusText = (isConnected: boolean, serviceName: string) => {
    return isConnected ? `${serviceName} Connected` : `${serviceName} Disconnected`;
  };

  const isFullyConnected = status.frontendAPI && status.backendAPI;
  const isPartiallyConnected = status.frontendAPI || status.backendAPI;
  const maxReconnectAttempts = 5;

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      title="Connection Status"
      size="md"
      centered
    >
      <Stack gap="md">
        {isFullyConnected ? (
          <Alert
            icon={<IconCheck size={16} />}
            title="All Connections Restored"
            color="green"
          >
            Both FrontendAPI and BackendAPI connections are now active.
          </Alert>
        ) : isPartiallyConnected ? (
          <Alert
            icon={<IconAlertCircle size={16} />}
            title="Partial Connection"
            color="yellow"
          >
            One or more connections are still establishing. Please wait or retry.
          </Alert>
        ) : (
          <Alert
            icon={<IconX size={16} />}
            title="Connection Lost"
            color="red"
          >
            All WebSocket connections have been lost. Please check your network connection.
          </Alert>
        )}

        <Stack gap="sm">
          <Group justify="space-between">
            <Group gap="xs">
              {getStatusIcon(status.frontendAPI)}
              <Text size="sm">{getStatusText(status.frontendAPI, 'FrontendAPI')}</Text>
            </Group>
            {!status.frontendAPI && (
              <Text size="xs" c="dimmed">
                Attempts: {status.reconnectAttempts.frontendAPI}/{maxReconnectAttempts}
              </Text>
            )}
          </Group>

          <Group justify="space-between">
            <Group gap="xs">
              {getStatusIcon(status.backendAPI)}
              <Text size="sm">{getStatusText(status.backendAPI, 'BackendAPI')}</Text>
            </Group>
            {!status.backendAPI && (
              <Text size="xs" c="dimmed">
                Attempts: {status.reconnectAttempts.backendAPI}/{maxReconnectAttempts}
              </Text>
            )}
          </Group>
        </Stack>

        {status.isConnecting && (
          <Stack gap="xs">
            <Text size="sm" fw={500}>Reconnecting...</Text>
            <Progress 
              value={(retryCount / maxReconnectAttempts) * 100} 
              size="sm" 
              color="blue"
            />
            <Text size="xs" c="dimmed">
              Retry attempt {retryCount} of {maxReconnectAttempts}
            </Text>
          </Stack>
        )}

        <Group justify="flex-end" gap="sm">
          {!isFullyConnected && (
            <Button
              leftSection={<IconRefresh size={16} />}
              onClick={onRetry}
              loading={status.isConnecting}
              disabled={status.isConnecting}
            >
              Retry Connection
            </Button>
          )}
          <Button variant="outline" onClick={onClose}>
            {isFullyConnected ? 'Close' : 'Dismiss'}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}; 