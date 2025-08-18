
import { Text, Paper } from '@mantine/core';
import { AgentDelegateMessageDisplay } from './AgentDelegateMessageDisplay';

export class DelegatingAgentMessageDisplay extends AgentDelegateMessageDisplay {
  renderDelegationContent(): JSX.Element {
    const { message } = this.props;
    return (
      <div>
        <div>{message.content}</div>
        {this.renderDelegationMetadata()}
      </div>
    );
  }

  renderDelegationMetadata(): JSX.Element | null {
    const { message } = this.props;
    if (!message.target_agent_id) return null;

    return (
      <Paper p="xs" bg="purple.9" withBorder style={{ marginTop: '8px' }}>
        <Text size="xs" fw={600} c="purple.3">
          {message.reasoning}
        </Text>
      </Paper>
    );
  }

  renderMetadata(): JSX.Element | null {
    return this.renderDelegationMetadata();
  }
}
