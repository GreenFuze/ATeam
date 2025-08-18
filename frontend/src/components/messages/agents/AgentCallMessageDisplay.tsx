
import { Badge } from '@mantine/core';
import { AgentOrchestrationBaseMessageDisplay } from './AgentOrchestrationBaseMessageDisplay';

export abstract class AgentCallMessageDisplay extends AgentOrchestrationBaseMessageDisplay {
  getBadges(): JSX.Element[] {
    return [
      <Badge key="call" size="xs" variant="light" color="purple">
        AGENT CALL
      </Badge>
    ];
  }

  // Abstract method for call-specific content
  abstract renderCallContent(): JSX.Element;

  // Default implementation
  renderOrchestrationContent(): JSX.Element {
    return this.renderCallContent();
  }
}
