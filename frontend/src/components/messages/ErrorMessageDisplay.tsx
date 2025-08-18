
import { Badge } from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import { BaseMessageDisplay } from './BaseMessageDisplay';

export class ErrorMessageDisplay extends BaseMessageDisplay {
  getIcon(): JSX.Element {
    return <IconAlertTriangle size={16} />;
  }

  getIconTooltip(): string {
    return 'Error';
  }

  getBackgroundColor(): string {
    return 'var(--mantine-color-dark-6)';
  }

  getBorderColor(): string {
    return 'var(--mantine-color-dark-4)';
  }

  protected getIconColor(): string {
    return 'red';
  }

  getBadges(): JSX.Element[] {
    return [
      <Badge key="error" size="xs" variant="light" color="red">
        ERROR
      </Badge>
    ];
  }

  renderContent(): JSX.Element {
    return this.renderMessageContent();
  }

  renderMetadata(): JSX.Element | null {
    return null;
  }
}
