import { notifications } from '@mantine/notifications';

export interface NotificationData {
  id: string;
  type: 'error' | 'warning' | 'info';
  title: string;
  message: string;
  details?: string;
  stack_trace?: string;
  context?: Record<string, any>;
  timestamp: string;
}

class NotificationService {
  private errorSocket: WebSocket | null = null;
  private warningSocket: WebSocket | null = null;
  private infoSocket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor() {
    this.connect();
  }

  private connect() {
    this.connectErrorSocket();
    this.connectWarningSocket();
    this.connectInfoSocket();
  }

  private connectErrorSocket() {
    try {
      this.errorSocket = new WebSocket(`ws://${window.location.host}/ws/notifications/errors`);
      
      this.errorSocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'notification') {
            this.showErrorNotification(data.data);
          }
        } catch (error) {
          console.error('Error parsing error notification:', error);
        }
      };

      this.errorSocket.onclose = () => {
        this.handleSocketClose('error');
      };

      this.errorSocket.onerror = (error) => {
        console.error('Error socket error:', error);
      };
    } catch (error) {
      console.error('Failed to connect to error notifications:', error);
    }
  }

  private connectWarningSocket() {
    try {
      this.warningSocket = new WebSocket(`ws://${window.location.host}/ws/notifications/warnings`);
      
      this.warningSocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'notification') {
            this.showWarningNotification(data.data);
          }
        } catch (error) {
          console.error('Error parsing warning notification:', error);
        }
      };

      this.warningSocket.onclose = () => {
        this.handleSocketClose('warning');
      };

      this.warningSocket.onerror = (error) => {
        console.error('Warning socket error:', error);
      };
    } catch (error) {
      console.error('Failed to connect to warning notifications:', error);
    }
  }

  private connectInfoSocket() {
    try {
      this.infoSocket = new WebSocket(`ws://${window.location.host}/ws/notifications/info`);
      
      this.infoSocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'notification') {
            this.showInfoNotification(data.data);
          }
        } catch (error) {
          console.error('Error parsing info notification:', error);
        }
      };

      this.infoSocket.onclose = () => {
        this.handleSocketClose('info');
      };

      this.infoSocket.onerror = (error) => {
        console.error('Info socket error:', error);
      };
    } catch (error) {
      console.error('Failed to connect to info notifications:', error);
    }
  }

  private handleSocketClose(type: 'error' | 'warning' | 'info') {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.reconnectAttempts++;
        if (type === 'error') {
          this.connectErrorSocket();
        } else if (type === 'warning') {
          this.connectWarningSocket();
        } else if (type === 'info') {
          this.connectInfoSocket();
        }
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  private showErrorNotification(data: NotificationData) {
    const message = data.details ? `${data.message}\n\nDetails: ${data.details}` : data.message;
    
    notifications.show({
      id: data.id,
      title: data.title,
      message: message,
      color: 'red',
      autoClose: false,
      withCloseButton: true,
      withBorder: true,
      styles: {
        title: { fontWeight: 'bold' },
        description: { whiteSpace: 'pre-wrap' }
      },
      onClick: () => {
        this.showDetailedErrorDialog(data);
      }
    });
  }

  private showWarningNotification(data: NotificationData) {
    notifications.show({
      id: data.id,
      title: data.title,
      message: data.message,
      color: 'yellow',
      autoClose: 10000,
      withCloseButton: true,
      withBorder: true,
      styles: {
        title: { fontWeight: 'bold' }
      },
      onClick: () => {
        this.showDetailedWarningDialog(data);
      }
    });
  }

  private showInfoNotification(data: NotificationData) {
    notifications.show({
      id: data.id,
      title: data.title,
      message: data.message,
      color: 'blue',
      autoClose: 5000,
      withCloseButton: true,
      withBorder: true,
      styles: {
        title: { fontWeight: 'bold' }
      }
    });
  }

  private showDetailedErrorDialog(data: NotificationData) {
    // Create a modal with detailed error information
    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 10000;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
      background: white;
      padding: 20px;
      border-radius: 8px;
      max-width: 80%;
      max-height: 80%;
      overflow-y: auto;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    `;

    content.innerHTML = `
      <h2 style="color: #e53e3e; margin-top: 0;">${data.title}</h2>
      <p><strong>Message:</strong> ${data.message}</p>
      ${data.details ? `<p><strong>Details:</strong> ${data.details}</p>` : ''}
      ${data.context ? `<p><strong>Context:</strong> <pre>${JSON.stringify(data.context, null, 2)}</pre></p>` : ''}
      ${data.stack_trace ? `<p><strong>Stack Trace:</strong> <pre style="background: #f7fafc; padding: 10px; border-radius: 4px; overflow-x: auto;">${data.stack_trace}</pre></p>` : ''}
      <p><strong>Timestamp:</strong> ${new Date(data.timestamp).toLocaleString()}</p>
      <button onclick="this.closest('div[style*=\"position: fixed\"]').remove()" style="
        background: #e53e3e;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        cursor: pointer;
        margin-top: 10px;
      ">Close</button>
    `;

    modal.appendChild(content);
    document.body.appendChild(modal);

    // Close on background click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    });
  }

  private showDetailedWarningDialog(data: NotificationData) {
    // Create a modal with detailed warning information
    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 10000;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
      background: white;
      padding: 20px;
      border-radius: 8px;
      max-width: 80%;
      max-height: 80%;
      overflow-y: auto;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    `;

    content.innerHTML = `
      <h2 style="color: #d69e2e; margin-top: 0;">${data.title}</h2>
      <p><strong>Message:</strong> ${data.message}</p>
      ${data.context ? `<p><strong>Context:</strong> <pre>${JSON.stringify(data.context, null, 2)}</pre></p>` : ''}
      <p><strong>Timestamp:</strong> ${new Date(data.timestamp).toLocaleString()}</p>
      <button onclick="this.closest('div[style*=\"position: fixed\"]').remove()" style="
        background: #d69e2e;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        cursor: pointer;
        margin-top: 10px;
      ">Close</button>
    `;

    modal.appendChild(content);
    document.body.appendChild(modal);

    // Close on background click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    });
  }

  public disconnect() {
    if (this.errorSocket) {
      this.errorSocket.close();
      this.errorSocket = null;
    }
    if (this.warningSocket) {
      this.warningSocket.close();
      this.warningSocket = null;
    }
    if (this.infoSocket) {
      this.infoSocket.close();
      this.infoSocket = null;
    }
  }
}

// Create and export a singleton instance
export const notificationService = new NotificationService();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  notificationService.disconnect();
}); 