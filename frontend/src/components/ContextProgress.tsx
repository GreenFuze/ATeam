import React from 'react';
import { Box, Text, RingProgress } from '@mantine/core';

interface ContextProgressProps {
  percentage: number;
  size?: number;
  thickness?: number;
}

const ContextProgress: React.FC<ContextProgressProps> = ({ 
  percentage, 
  size = 40, 
  thickness = 4 
}) => {
  // Ensure percentage is between 0 and 100
  const clampedPercentage = Math.max(0, Math.min(100, percentage));
  
  // Determine color based on percentage
  const getColor = (percent: number) => {
    if (percent < 50) return 'green';
    if (percent < 80) return 'yellow';
    return 'red';
  };

  return (
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
  );
};

export default ContextProgress;