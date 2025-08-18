
import { Badge } from '@mantine/core';
import { AgentOrchestrationBaseMessageDisplay } from './AgentOrchestrationBaseMessageDisplay';

export abstract class AgentDelegateMessageDisplay extends AgentOrchestrationBaseMessageDisplay {
  getBadges(): JSX.Element[] {
    return [
      <Badge key="delegate" size="xs" variant="light" color="purple">
        AGENT DELEGATE
      </Badge>
    ];
  }

  // Abstract method for delegation-specific content
  abstract renderDelegationContent(): JSX.Element;

  // Default implementation
  renderOrchestrationContent(): JSX.Element {
    return this.renderDelegationContent();
  }
}
