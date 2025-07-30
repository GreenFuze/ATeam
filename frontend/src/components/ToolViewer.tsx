import React from 'react';
import { Modal, Text, Badge, Code, ScrollArea } from '@mantine/core';
import { ToolConfig } from '../types';

interface ToolViewerProps {
  tool: ToolConfig | null;
  isOpen: boolean;
  onClose: () => void;
}

const ToolViewer: React.FC<ToolViewerProps> = ({ tool, isOpen, onClose }) => {
  if (!tool) return null;

  const getToolType = (tool: ToolConfig) => {
    if (tool.is_provider_tool) {
      return 'Provider Tool';
    }
    if (['CreateAgent', 'CreateTool'].includes(tool.name)) {
      return 'System Tool';
    }
    return 'User Tool';
  };

  const getToolTypeColor = (tool: ToolConfig) => {
    if (tool.is_provider_tool) {
      return 'purple';
    }
    if (['CreateAgent', 'CreateTool'].includes(tool.name)) {
      return 'blue';
    }
    return 'green';
  };

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
            <Badge color={getToolTypeColor(tool)}>
              {getToolType(tool)}
            </Badge>
          </div>
          <Text color="dimmed" size="sm">
            {tool.description}
          </Text>
        </div>

        {/* Tool Details */}
        <div className="space-y-4">
          {tool.provider && (
            <div>
              <Text size="sm" fw={500} className="mb-1">
                Provider
              </Text>
              <Text size="sm">{tool.provider}</Text>
            </div>
          )}

          {tool.file_path && (
            <div>
              <Text size="sm" fw={500} className="mb-1">
                File Path
              </Text>
              <Code className="text-xs">{tool.file_path}</Code>
            </div>
          )}

          {/* Parameters */}
          {Object.keys(tool.parameters).length > 0 && (
            <div>
              <Text size="sm" fw={500} className="mb-2">
                Parameters ({Object.keys(tool.parameters).length})
              </Text>
              <div className="space-y-2">
                {Object.entries(tool.parameters).map(([paramName, paramInfo]) => (
                  <div key={paramName} className="bg-gray-50 p-3 rounded">
                    <div className="flex items-center justify-between mb-1">
                      <Text size="sm" fw={500}>
                        {paramName}
                      </Text>
                      {typeof paramInfo === 'object' && paramInfo.required && (
                        <Badge size="xs" color="red">
                          Required
                        </Badge>
                      )}
                    </div>
                    <div className="space-y-1">
                      {typeof paramInfo === 'object' && (
                        <>
                          <Text size="xs" color="dimmed">
                            Type: {paramInfo.type || 'any'}
                          </Text>
                          {paramInfo.description && (
                            <Text size="xs" color="dimmed">
                              {paramInfo.description}
                            </Text>
                          )}
                        </>
                      )}
                      {typeof paramInfo === 'string' && (
                        <Text size="xs" color="dimmed">
                          {paramInfo}
                        </Text>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* JSON View */}
          <div>
            <Text size="sm" fw={500} className="mb-2">
              Tool Configuration
            </Text>
            <ScrollArea h={200}>
              <Code block className="text-xs">
                {JSON.stringify(tool, null, 2)}
              </Code>
            </ScrollArea>
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default ToolViewer; 