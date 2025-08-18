
import { AgentCallMessageDisplay } from './AgentCallMessageDisplay';

export class CalledAgentMessageDisplay extends AgentCallMessageDisplay {
  renderCallContent(): JSX.Element {
    const { message } = this.props;
    return (
      <div>
        <div>{message.content}</div>
      </div>
    );
  }
}
