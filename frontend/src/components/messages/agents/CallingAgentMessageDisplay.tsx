
import { AgentCallMessageDisplay } from './AgentCallMessageDisplay';

export class CallingAgentMessageDisplay extends AgentCallMessageDisplay {
  renderCallContent(): JSX.Element {
    const { message } = this.props;
    return (
      <div>
        <div>{message.content}</div>
      </div>
    );
  }
}
