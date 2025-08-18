import { Message } from '../../types';

export interface BaseMessageDisplayProps {
  message: Message;
  editable?: boolean;
  defaultDisplayMode?: 'markdown' | 'text' | 'raw';
  defaultEditMode?: boolean;
  isCollapsible?: boolean;
  isCollapsed?: boolean;
  onSave?: (content: string) => void;
  onCancel?: () => void;
}

export interface MessageDisplayComponent {
  renderContent(): JSX.Element;
  renderMetadata(): JSX.Element | null;
  getIcon(): JSX.Element;
  getBadges(): JSX.Element[];
  getBackgroundColor(): string;
  getBorderColor(): string;
  getIconTooltip(): string;
}

export type DisplayMode = 'markdown' | 'text' | 'raw';
