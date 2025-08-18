
import { Badge } from '@mantine/core';
import { AgentOrchestrationBaseMessageDisplay } from './AgentOrchestrationBaseMessageDisplay';

export class AgentReturnMessageDisplay extends AgentOrchestrationBaseMessageDisplay {
  getBadges(): JSX.Element[] {
    return [
      <Badge key="return" size="xs" variant="light" color="purple">
        AGENT RETURN
      </Badge>
    ];
  }

  renderOrchestrationContent(): JSX.Element {
    const { message } = this.props;
    return (
      <div>
        <div>{message.content}</div>
      </div>
    );
  }
}
