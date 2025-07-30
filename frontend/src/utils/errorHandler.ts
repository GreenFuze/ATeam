import { notifications } from '@mantine/notifications';

export interface ErrorDetails {
  message: string;
  status?: number;
  statusText?: string;
  url?: string;
  method?: string;
  timestamp: string;
  stack?: string;
  response?: any;
  request?: any;
}

export class ErrorHandler {
  static formatError(error: any): ErrorDetails {
    const details: ErrorDetails = {
      message: this.getErrorMessage(error),
      timestamp: new Date().toISOString(),
    };

    if (error.response) {
      // Server responded with error status
      details.status = error.response.status;
      details.statusText = error.response.statusText;
      details.url = error.config?.url;
      details.method = error.config?.method?.toUpperCase();
      details.response = error.response.data;
    } else if (error.request) {
      // Request was made but no response received
      details.message = 'No response received from server';
      details.url = error.config?.url;
      details.method = error.config?.method?.toUpperCase();
      details.request = error.request;
    } else {
      // Something else happened
      details.message = error.message || 'An unexpected error occurred';
      details.stack = error.stack;
    }

    return details;
  }

  private static getErrorMessage(error: any): string {
    if (error.response?.data?.detail) {
      const detail = error.response.data.detail;
      
      // Handle detailed error objects from backend
      if (typeof detail === 'object' && detail.error) {
        let message = detail.error;
        
        // Add ALL fields from the error response (except the main error field)
        const additionalFields = Object.entries(detail)
          .filter(([key, value]) => key !== 'error' && value !== undefined && value !== null)
          .map(([key, value]) => {
            if (Array.isArray(value)) {
              return `${key}: ${value.join(', ')}`;
            } else if (typeof value === 'object') {
              return `${key}: ${JSON.stringify(value, null, 2)}`;
            } else {
              return `${key}: ${value}`;
            }
          });
        
        if (additionalFields.length > 0) {
          message += '\n\n' + additionalFields.join('\n');
        }
        
        return message;
      }
      
      // Handle simple string errors
      return detail;
    }
    if (error.response?.data?.message) {
      return error.response.data.message;
    }
    if (error.message) {
      return error.message;
    }
    return 'An unexpected error occurred';
  }

  static showError(error: any, title: string = 'Error') {
    const details = this.formatError(error);
    
    // Log detailed error to console
    console.group(`🚨 ${title}`);
    console.error('Error Details:', details);
    console.error('Full Error Object:', error);
    console.groupEnd();
    
    // Show notification
    notifications.show({
      title,
      message: details.message,
      color: 'red',
      autoClose: false,
      withCloseButton: true,
    });

    // Show detailed error dialog
    this.showErrorDialog(details, title);
  }

  private static showErrorDialog(details: ErrorDetails, title: string) {
    // Create detailed error information
    const errorInfo = {
      title,
      ...details,
      userAgent: navigator.userAgent,
      url: window.location.href,
    };

    const errorText = JSON.stringify(errorInfo, null, 2);
    
    // Show modal with copy button
    this.showModalWithCopy(title, details.message, errorText);
  }

  private static showModalWithCopy(title: string, message: string, details: string) {
    // Determine if we need a larger dialog based on content length
    const hasStackTrace = message.includes('Full Stack Trace:');
    const isLargeContent = message.length > 1000 || hasStackTrace;
    
    // Create modal element
    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.7);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 10000;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
      background: #1a1a1a;
      border-radius: 8px;
      padding: 24px;
      max-width: ${isLargeContent ? '90%' : '80%'};
      max-height: ${isLargeContent ? '90%' : '80%'};
      overflow-y: auto;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
      border: 1px solid #333;
    `;

    content.innerHTML = `
      <h2 style="margin: 0 0 16px 0; color: #ff6b6b;">${title}</h2>
      <div style="margin: 0 0 16px 0; color: #e0e0e0; white-space: pre-wrap; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 13px; line-height: 1.4;">${message}</div>
      <div style="margin: 16px 0;">
        <button id="copyDetails" style="
          background: #4a9eff;
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 4px;
          cursor: pointer;
          margin-right: 8px;
          font-weight: 500;
        ">Copy Details to Clipboard</button>
        <button id="closeModal" style="
          background: #555;
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 500;
        ">Close</button>
      </div>
      <div style="
        background: #2a2a2a;
        border: 1px solid #444;
        border-radius: 4px;
        padding: 16px;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 11px;
        white-space: pre-wrap;
        max-height: ${isLargeContent ? '400px' : '300px'};
        overflow-y: auto;
        color: #e0e0e0;
        line-height: 1.3;
      ">${details}</div>
    `;

    modal.appendChild(content);
    document.body.appendChild(modal);

    // Add event listeners
    const copyButton = content.querySelector('#copyDetails') as HTMLButtonElement;
    const closeButton = content.querySelector('#closeModal') as HTMLButtonElement;

    copyButton.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(details);
        copyButton.textContent = 'Copied!';
        copyButton.style.background = '#4ade80';
        setTimeout(() => {
          copyButton.textContent = 'Copy Details to Clipboard';
          copyButton.style.background = '#4a9eff';
        }, 2000);
      } catch (err) {
        console.error('Failed to copy to clipboard:', err);
        copyButton.textContent = 'Failed to copy';
        copyButton.style.background = '#ff6b6b';
      }
    });

    closeButton.addEventListener('click', () => {
      document.body.removeChild(modal);
    });

    // Close on outside click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        document.body.removeChild(modal);
      }
    });

    // Close on escape key
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        document.body.removeChild(modal);
        document.removeEventListener('keydown', handleEscape);
      }
    };
    document.addEventListener('keydown', handleEscape);
  }

  static async copyToClipboard(text: string): Promise<boolean> {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
      return false;
    }
  }
}