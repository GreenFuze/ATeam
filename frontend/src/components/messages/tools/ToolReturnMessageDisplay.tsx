
import { Badge } from '@mantine/core';
import { ToolBaseMessageDisplay } from './ToolBaseMessageDisplay';

export class ToolReturnMessageDisplay extends ToolBaseMessageDisplay {
  getBadges(): JSX.Element[] {
    return [
      <Badge key="tool-return" size="xs" variant="light" color="yellow">
        TOOL RETURN
      </Badge>
    ];
  }

  renderToolContent(): JSX.Element {
    const { message } = this.props;
    return (
      <div>
        <div>Tool {message.tool_name} returned result</div>
        {this.renderToolMetadata()}
      </div>
    );
  }

  renderToolMetadata(): JSX.Element | null {
    const { message } = this.props;
    const metadataItems = [];


    if (message.tool_result) {
      metadataItems.push(
        <div key="result" style={{ marginTop: '4px', padding: '8px', backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: '4px' }}>
          <strong>Result:</strong> <span style={{ fontFamily: 'Consolas, "Courier New", monospace' }}>{JSON.stringify(message.tool_result)}</span>
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
