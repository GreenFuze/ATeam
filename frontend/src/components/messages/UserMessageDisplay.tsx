
import { IconUser } from '@tabler/icons-react';
import { BaseMessageDisplay } from './BaseMessageDisplay';

export class UserMessageDisplay extends BaseMessageDisplay {
  getIcon(): JSX.Element {
    return <IconUser size={20} />;
  }

  getIconTooltip(): string {
    return 'User response';
  }

  getBackgroundColor(): string {
    return 'var(--mantine-color-blue-9)';
  }

  getBorderColor(): string {
    return 'var(--mantine-color-blue-6)';
  }

  protected getIconColor(): string {
    return 'var(--mantine-color-white)';
  }

  getBadges(): JSX.Element[] {
    return [];
  }

  renderContent(): JSX.Element {
    return this.renderMessageContent();
  }

  renderMetadata(): JSX.Element | null {
    return null;
  }
}
