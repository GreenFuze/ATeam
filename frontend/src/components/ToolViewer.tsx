import React from 'react';
import { Modal, Text, Badge, Code, Group, Tooltip, Card } from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import { ToolConfig } from '../types';

interface ToolViewerProps {
  tool: ToolConfig | null;
  isOpen: boolean;
  onClose: () => void;
}

const ToolViewer: React.FC<ToolViewerProps> = ({ tool, isOpen, onClose }) => {
  if (!tool) return null;

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      title={`Tool: ${tool.name}`}
      size="lg"
      centered
    >
      <div className="space-y-6">
        {/* Basic Information */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <Text size="lg" fw={600}>
              {tool.name}
            </Text>
            <Group gap="xs">
              <Badge color={tool.type === 'function' ? 'blue' : 'green'}>
                {tool.type}
              </Badge>
              {!tool.has_docstring && (
                <Tooltip label="Missing docstring - add a description for this tool">
                  <IconAlertTriangle size={16} color="orange" />
                </Tooltip>
              )}
            </Group>
          </div>
          <Text color="dimmed" size="sm">
            {tool.description || 'No description available'}
          </Text>
        </div>

        {/* Function Signature */}
        {tool.type === 'function' && tool.signature && (
          <div>
            <Text size="sm" fw={500} className="mb-1">
              Signature
            </Text>
            <Code>{tool.name}{tool.signature}</Code>
          </div>
        )}

        {/* Tool Details */}
        <div className="space-y-4">
          <div>
            <Text size="sm" fw={500} className="mb-1">
              File Path
            </Text>
            <Code className="text-xs">{tool.file_path}</Code>
          </div>

          <div>
            <Text size="sm" fw={500} className="mb-1">
              Relative Path
            </Text>
            <Code className="text-xs">{tool.relative_path}</Code>
          </div>

          {/* Methods for classes */}
          {tool.type === 'class' && tool.methods && tool.methods.length > 0 && (
            <div>
              <Text size="sm" fw={500} className="mb-2">
                Methods ({tool.methods.length})
              </Text>
              <div className="space-y-2">
                {tool.methods.map((method, index) => (
                  <Card key={index} p="xs" withBorder>
                    <Group gap="xs" align="flex-start">
                      <Text size="sm" fw={500}>
                        {method.name}
                      </Text>
                      {!method.has_docstring && (
                        <Tooltip label="Missing docstring - add a description for this method">
                          <IconAlertTriangle size={14} color="orange" />
                        </Tooltip>
                      )}
                    </Group>
                    {method.signature && (
                      <Text size="xs" color="dimmed" mt="xs" style={{ fontFamily: 'monospace' }}>
                        {method.name}{method.signature}
                      </Text>
                    )}
                    {method.description && (
                      <Text size="xs" color="dimmed" mt="xs">
                        {method.description}
                      </Text>
                    )}
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
};

export default ToolViewer; 