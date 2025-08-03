import React from 'react';
import { Box, Text, RingProgress, Tooltip } from '@mantine/core';

interface ContextProgressProps {
  percentage: number | null;
  size?: number;
  thickness?: number;
  tokensUsed?: number | null;
  contextWindow?: number | null;
}

const ContextProgress: React.FC<ContextProgressProps> = ({ 
  percentage, 
  size = 40, 
  thickness = 4,
  tokensUsed,
  contextWindow
}) => {
  // Check if context window is not set (N/A)
  if (percentage === null || percentage === 0) {
    return (
      <Tooltip label="Context window size not configured">
        <Box style={{ position: 'relative', display: 'inline-block' }}>
          <RingProgress
            size={size}
            thickness={thickness}
            sections={[{ value: 0, color: 'gray' }]}
            rootColor="var(--mantine-color-gray-3)"
          />
          <Text
            size="xs"
            fw={600}
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              color: 'var(--mantine-color-gray-5)'
            }}
          >
            N/A
          </Text>
        </Box>
      </Tooltip>
    );
  }
  
  // Ensure percentage is between 0 and 100
  const clampedPercentage = Math.max(0, Math.min(100, percentage));
  
  // Determine color based on percentage
  const getColor = (percent: number) => {
    if (percent < 50) return 'green';
    if (percent < 80) return 'yellow';
    return 'red';
  };

  // Create tooltip text
  const tooltipText = tokensUsed && contextWindow 
    ? `${tokensUsed.toLocaleString()}/${contextWindow.toLocaleString()} tokens`
    : `${Math.round(clampedPercentage)}% used`;

  return (
    <Tooltip label={tooltipText}>
      <Box style={{ position: 'relative', display: 'inline-block' }}>
        <RingProgress
          size={size}
          thickness={thickness}
          sections={[{ value: clampedPercentage, color: getColor(clampedPercentage) }]}
          rootColor="var(--mantine-color-gray-3)"
        />
        <Text
          size="xs"
          fw={600}
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            color: 'var(--mantine-color-text)'
          }}
        >
          {Math.round(clampedPercentage)}%
        </Text>
      </Box>
    </Tooltip>
  );
};

export default ContextProgress;