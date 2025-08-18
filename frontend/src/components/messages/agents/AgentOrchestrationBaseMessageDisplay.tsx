
import { Badge } from '@mantine/core';
import { IconBrain } from '@tabler/icons-react';
import { BaseMessageDisplay } from '../BaseMessageDisplay';

export abstract class AgentOrchestrationBaseMessageDisplay extends BaseMessageDisplay {
  getIcon(): JSX.Element {
    return <IconBrain size={16} />;
  }

  getIconTooltip(): string {
    return 'Agent Orchestration';
  }

  getBackgroundColor(): string {
    return 'var(--mantine-color-dark-6)';
  }

  getBorderColor(): string {
    return 'var(--mantine-color-dark-4)';
  }

  protected getIconColor(): string {
    return 'purple';
  }

  renderOrchestrationMetadata(): JSX.Element | null {
    const { message } = this.props;
    const metadataItems = [];

    if (message.target_agent_id) {
      metadataItems.push(
        <Badge key="target" size="xs" variant="light" color="purple">
          Target: {message.target_agent_id}
        </Badge>
      );
    }

    if (message.reasoning && this.state.showReasoning) {
      metadataItems.push(
        <Badge key="reasoning" size="xs" variant="light" color="purple">
          Reasoning: {message.reasoning}
        </Badge>
      );
    }

    return metadataItems.length > 0 ? (
      <div style={{ marginTop: '8px' }}>
        {metadataItems}
      </div>
    ) : null;
  }

  // Abstract method for orchestration-specific content
  abstract renderOrchestrationContent(): JSX.Element;

  // Default implementation - can be overridden
  renderContent(): JSX.Element {
    return this.renderOrchestrationContent();
  }

  // Default implementation - can be overridden
  renderMetadata(): JSX.Element | null {
    return this.renderOrchestrationMetadata();
  }
}
