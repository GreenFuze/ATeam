
import { IconSettings } from '@tabler/icons-react';
import { BaseMessageDisplay } from './BaseMessageDisplay';

export class SystemMessageDisplay extends BaseMessageDisplay {
  getIcon(): JSX.Element {
    return <IconSettings size={16} />;
  }

  getIconTooltip(): string {
    return 'System Message';
  }

  getBackgroundColor(): string {
    return '#3a2f2a'; // Warm brown for system messages
  }

  getBorderColor(): string {
    return '#5a4a42';
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
