
import React from 'react';
import { Badge } from '@mantine/core';
import { IconBrain } from '@tabler/icons-react';
import { BaseMessageDisplay } from './BaseMessageDisplay';

class ChatResponseMessageDisplayClass extends BaseMessageDisplay {
  getIcon(): JSX.Element {
    return <IconBrain size={16} />;
  }

  getIconTooltip(): string {
    return 'Chat Response';
  }

  getBackgroundColor(): string {
    return 'var(--mantine-color-dark-6)';
  }

  getBorderColor(): string {
    return 'var(--mantine-color-dark-4)';
  }

  protected getIconColor(): string {
    return 'blue';
  }

  getBadges(): JSX.Element[] {
    const { message } = this.props;
    const badges: JSX.Element[] = [];

    if (message.action === 'CHAT_RESPONSE_CONTINUE_WORK') {
      badges.push(
        <Badge key="cont" size="xs" variant="light" color="blue">
          Continuing work
        </Badge>
      );
    } else if (message.action === 'CHAT_RESPONSE_WAIT_USER_INPUT') {
      badges.push(
        <Badge key="wait" size="xs" variant="light" color="gray">
          Waiting for input
        </Badge>
      );
    }

    // Add streaming badges
    badges.push(...this.getStreamingBadges());

    return badges;
  }

  renderContent(): JSX.Element {
    return this.renderMessageContent();
  }

  renderMetadata(): JSX.Element | null {
    const { message } = this.props;
    if (!message.reasoning || !this.state.showReasoning) return null;

    return (
      <div style={{ marginTop: '8px', padding: '8px', backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: '4px' }}>
        <strong>Reasoning:</strong> {message.reasoning}
      </div>
    );
  }
}

// Memoized export for performance optimization
export const ChatResponseMessageDisplay = React.memo(ChatResponseMessageDisplayClass);
