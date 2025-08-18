
import { AgentDelegateMessageDisplay } from './AgentDelegateMessageDisplay';

export class DelegatedAgentMessageDisplay extends AgentDelegateMessageDisplay {
  renderDelegationContent(): JSX.Element {
    const { message } = this.props;
    return (
      <div>
        <div>{message.content}</div>
      </div>
    );
  }

  // No delegation metadata for delegated agent - they don't need the "Delegating to" box
  renderMetadata(): JSX.Element | null {
    return null;
  }
}
