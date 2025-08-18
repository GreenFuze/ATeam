
import { Badge } from '@mantine/core';
import { IconTool } from '@tabler/icons-react';
import { BaseMessageDisplay } from '../BaseMessageDisplay';

export abstract class ToolBaseMessageDisplay extends BaseMessageDisplay {
  getIcon(): JSX.Element {
    return <IconTool size={16} />;
  }

  getIconTooltip(): string {
    return 'Tool Usage';
  }

  getBackgroundColor(): string {
    return 'var(--mantine-color-dark-6)';
  }

  getBorderColor(): string {
    return 'var(--mantine-color-dark-4)';
  }

  protected getIconColor(): string {
    return 'yellow';
  }

  renderToolMetadata(): JSX.Element | null {
    const { message } = this.props;
    const metadataItems = [];

    if (message.tool_name) {
      metadataItems.push(
        <Badge key="tool" size="xs" variant="light" color="yellow">
          Tool: {message.tool_name}
        </Badge>
      );
    }

    if (message.tool_parameters) {
      metadataItems.push(
        <Badge key="params" size="xs" variant="light" color="yellow">
          Parameters: {JSON.stringify(message.tool_parameters)}
        </Badge>
      );
    }

    return metadataItems.length > 0 ? (
      <div style={{ marginTop: '8px' }}>
        {metadataItems}
      </div>
    ) : null;
  }

  // Abstract method for tool-specific content
  abstract renderToolContent(): JSX.Element;

  // Default implementation - can be overridden
  renderContent(): JSX.Element {
    return this.renderToolContent();
  }

  // Default implementation - can be overridden
  renderMetadata(): JSX.Element | null {
    return this.renderToolMetadata();
  }
}
