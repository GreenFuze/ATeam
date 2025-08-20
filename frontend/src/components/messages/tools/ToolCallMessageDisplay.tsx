
import { Badge } from '@mantine/core';
import { ToolBaseMessageDisplay } from './ToolBaseMessageDisplay';

export class ToolCallMessageDisplay extends ToolBaseMessageDisplay {
  getBadges(): JSX.Element[] {
    return [
      <Badge key="tool-call" size="xs" variant="light" color="yellow">
        TOOL CALL
      </Badge>
    ];
  }

  renderToolContent(): JSX.Element {
    const { message } = this.props;
    return (
      <div>
        <div>Calling tool {message.tool_name}</div>
        {this.renderToolMetadata()}
      </div>
    );
  }

  renderToolMetadata(): JSX.Element | null {
    const { message } = this.props;
    const metadataItems = [];

    if (message.tool_parameters) {
      metadataItems.push(
        <div key="params" style={{ marginTop: '4px', padding: '8px', backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: '4px' }}>
          <strong>Parameters:</strong> <span style={{ fontFamily: 'Consolas, "Courier New", monospace' }}>{JSON.stringify(message.tool_parameters)}</span>
        </div>
      );
    }

    return metadataItems.length > 0 ? (
      <div style={{ marginTop: '8px' }}>
        {metadataItems}
      </div>
    ) : null;
  }
}
