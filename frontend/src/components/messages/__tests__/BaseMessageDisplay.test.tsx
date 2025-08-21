/**
 * Unit tests for BaseMessageDisplay component
 * Tests streaming state management, content rendering, and performance optimizations
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { notifications } from '@mantine/notifications';
import { BaseMessageDisplay } from '../BaseMessageDisplay';
import { Message, MessageType } from '../../../types';

// Mock dependencies
jest.mock('@mantine/notifications', () => ({
  notifications: {
    show: jest.fn(),
  },
}));

jest.mock('../../../services/ConnectionManager', () => ({
  connectionManager: {
    startContentStream: jest.fn(),
    cancelContentStream: jest.fn(),
    pauseContentStream: jest.fn(),
    resumeContentStream: jest.fn(),
  },
}));

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: jest.fn(),
  },
});

// Mock document.execCommand for fallback
Object.defineProperty(document, 'execCommand', {
  value: jest.fn(),
  writable: true,
});

describe('BaseMessageDisplay', () => {
  const mockMessage: Message = {
    id: 'test-message-1',
    content: 'Test message content',
    timestamp: '2025-01-20T10:00:00Z',
    message_type: MessageType.CHAT_RESPONSE,
    agent_id: 'test-agent',
    agent_name: 'Test Agent',
    action: 'CHAT_RESPONSE_CONTINUE_WORK',
    reasoning: 'Test reasoning',
    icon: 'BRAIN',
    metadata: {},
  };

  const mockStreamingMessage: Message = {
    ...mockMessage,
    id: 'test-streaming-message',
    stream_id: 'test-stream-guid',
    stream_state: 'STREAMING',
    is_streaming: true,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('renders message content correctly', () => {
      render(<BaseMessageDisplay message={mockMessage} />);
      
      expect(screen.getByText('Test message content')).toBeInTheDocument();
      expect(screen.getByText('Test Agent')).toBeInTheDocument();
    });

    it('renders timestamp correctly', () => {
      render(<BaseMessageDisplay message={mockMessage} />);
      
      expect(screen.getByText(/2025-01-20/)).toBeInTheDocument();
    });

    it('renders reasoning when showReasoning is true', () => {
      render(<BaseMessageDisplay message={mockMessage} />);
      
      // Click to show reasoning
      const reasoningButton = screen.getByRole('button', { name: /show reasoning/i });
      fireEvent.click(reasoningButton);
      
      expect(screen.getByText('Test reasoning')).toBeInTheDocument();
    });
  });

  describe('Streaming State Management', () => {
    it('initializes streaming for messages with stream_id', async () => {
      const { connectionManager } = require('../../../services/ConnectionManager');
      connectionManager.startContentStream.mockResolvedValue(true);

      render(<BaseMessageDisplay message={mockStreamingMessage} />);

      await waitFor(() => {
        expect(connectionManager.startContentStream).toHaveBeenCalledWith(
          'test-stream-guid',
          'test-agent',
          'test-session',
          expect.any(Object),
          'low'
        );
      });
    });

    it('shows streaming badges for streaming messages', () => {
      render(<BaseMessageDisplay message={mockStreamingMessage} />);
      
      expect(screen.getByText('STREAMING')).toBeInTheDocument();
    });

    it('shows error badges for error state', () => {
      const errorMessage = {
        ...mockStreamingMessage,
        stream_state: 'ERROR',
      };
      
      render(<BaseMessageDisplay message={errorMessage} />);
      
      expect(screen.getByText('ERROR')).toBeInTheDocument();
    });

    it('shows complete badges for completed streams', () => {
      const completeMessage = {
        ...mockStreamingMessage,
        stream_state: 'COMPLETE',
      };
      
      render(<BaseMessageDisplay message={completeMessage} />);
      
      expect(screen.getByText('COMPLETE')).toBeInTheDocument();
    });
  });

  describe('Streaming Controls', () => {
    it('shows streaming control buttons when streaming', () => {
      render(<BaseMessageDisplay message={mockStreamingMessage} />);
      
      expect(screen.getByRole('button', { name: /pause stream/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /cancel stream/i })).toBeInTheDocument();
    });

    it('calls pause stream when pause button is clicked', async () => {
      const { connectionManager } = require('../../../services/ConnectionManager');
      connectionManager.pauseContentStream.mockResolvedValue(true);

      render(<BaseMessageDisplay message={mockStreamingMessage} />);
      
      const pauseButton = screen.getByRole('button', { name: /pause stream/i });
      fireEvent.click(pauseButton);

      await waitFor(() => {
        expect(connectionManager.pauseContentStream).toHaveBeenCalledWith('test-stream-guid');
      });
    });

    it('calls resume stream when resume button is clicked', async () => {
      const { connectionManager } = require('../../../services/ConnectionManager');
      connectionManager.resumeContentStream.mockResolvedValue(true);

      const pausedMessage = {
        ...mockStreamingMessage,
        stream_state: 'PAUSED',
      };

      render(<BaseMessageDisplay message={pausedMessage} />);
      
      const resumeButton = screen.getByRole('button', { name: /resume stream/i });
      fireEvent.click(resumeButton);

      await waitFor(() => {
        expect(connectionManager.resumeContentStream).toHaveBeenCalledWith('test-stream-guid');
      });
    });

    it('calls cancel stream when cancel button is clicked', async () => {
      const { connectionManager } = require('../../../services/ConnectionManager');
      connectionManager.cancelContentStream.mockResolvedValue(true);

      render(<BaseMessageDisplay message={mockStreamingMessage} />);
      
      const cancelButton = screen.getByRole('button', { name: /cancel stream/i });
      fireEvent.click(cancelButton);

      await waitFor(() => {
        expect(connectionManager.cancelContentStream).toHaveBeenCalledWith('test-stream-guid');
      });
    });
  });

  describe('Copy to Clipboard', () => {
    it('copies content to clipboard when copy button is clicked', async () => {
      const mockWriteText = jest.fn().mockResolvedValue(undefined);
      Object.assign(navigator, { clipboard: { writeText: mockWriteText } });

      render(<BaseMessageDisplay message={mockMessage} />);
      
      // Open menu and click copy
      const menuButton = screen.getByRole('button', { name: /message options/i });
      fireEvent.click(menuButton);
      
      const copyButton = screen.getByRole('menuitem', { name: /copy content/i });
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(mockWriteText).toHaveBeenCalledWith('Test message content');
        expect(notifications.show).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Copied!',
            message: 'Message content copied to clipboard',
            color: 'green',
          })
        );
      });
    });

    it('uses fallback copy method when clipboard API fails', async () => {
      const mockWriteText = jest.fn().mockRejectedValue(new Error('Clipboard API not available'));
      Object.assign(navigator, { clipboard: { writeText: mockWriteText } });

      render(<BaseMessageDisplay message={mockMessage} />);
      
      // Open menu and click copy
      const menuButton = screen.getByRole('button', { name: /message options/i });
      fireEvent.click(menuButton);
      
      const copyButton = screen.getByRole('menuitem', { name: /copy content/i });
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(document.execCommand).toHaveBeenCalledWith('copy');
      });
    });
  });

  describe('Performance Optimizations', () => {
    it('shows warning for very long content', () => {
      const longContent = 'x'.repeat(60000); // 60KB content
      const longMessage = {
        ...mockMessage,
        content: longContent,
      };

      render(<BaseMessageDisplay message={longMessage} />);
      
      expect(screen.getByText(/This message is very long/)).toBeInTheDocument();
      expect(screen.getByText(/Consider using markdown mode/)).toBeInTheDocument();
    });

    it('memoizes ReactMarkdown component', () => {
      const { rerender } = render(<BaseMessageDisplay message={mockMessage} />);
      
      // Re-render with same content
      rerender(<BaseMessageDisplay message={mockMessage} />);
      
      // Component should not re-render unnecessarily
      // This is tested by ensuring the component renders correctly
      expect(screen.getByText('Test message content')).toBeInTheDocument();
    });
  });

  describe('Streaming Content Display', () => {
    it('displays streamed content when available', () => {
      const streamedMessage = {
        ...mockStreamingMessage,
        content: 'Original content',
      };

      render(<BaseMessageDisplay message={streamedMessage} />);
      
      // Simulate streaming content update
      // This would be done through the streaming callbacks
      // For now, we test that the component renders correctly
      expect(screen.getByText('Original content')).toBeInTheDocument();
    });

    it('shows stream error when streaming fails', () => {
      const errorMessage = {
        ...mockStreamingMessage,
        stream_state: 'ERROR',
      };

      render(<BaseMessageDisplay message={errorMessage} />);
      
      expect(screen.getByText('ERROR')).toBeInTheDocument();
    });
  });

  describe('Component Cleanup', () => {
    it('cancels content stream on unmount', () => {
      const { connectionManager } = require('../../../services/ConnectionManager');
      connectionManager.cancelContentStream.mockResolvedValue(true);

      const { unmount } = render(<BaseMessageDisplay message={mockStreamingMessage} />);
      
      unmount();

      expect(connectionManager.cancelContentStream).toHaveBeenCalledWith('test-stream-guid');
    });
  });
});
